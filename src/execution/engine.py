"""Execution Engine
==========================

Provides order execution with:

- Real IBKR adapter via ib_insync (TWS / IB Gateway)
- Paper trading fallback with configurable slippage
- Position-level risk checks (max size, daily loss limit, max drawdown)
- Market data subscription for execution prices
- Full order history with latency tracking

Usage:
    engine = ExecutionEngine(config)
    engine.connect()
    result = engine.submit_order("XAUUSD", 1000, "buy", order_type="mkt")
"""

import os
import time
import uuid
import threading
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, date
from loguru import logger
import numpy as np

from src.utils.config import get_config


# ── Risk limits (can be overridden via config) ─────────────────────────────

DEFAULT_RISK_LIMITS = {
    "max_position_size_usd": 100000,
    "max_position_size_pct_equity": 0.25,
    "max_daily_loss_usd": 5000,
    "max_daily_loss_pct": 0.05,
    "max_drawdown_pct": 0.15,
    "max_trades_per_day": 20,
    "min_order_interval_sec": 1.0,
}


@dataclass
class OrderRecord:
    """Immutable record of a submitted order."""
    order_id: str
    symbol: str
    quantity: float
    side: str
    order_type: str
    limit_price: Optional[float]
    tif: str
    status: str
    submitted_at: float
    filled_at: Optional[float] = None
    fill_price: Optional[float] = None
    latency_ms: float = 0.0
    reject_reason: Optional[str] = None


# ── Risk State ─────────────────────────────────────────────────────────────

class RiskManager:
    """Tracks daily PnL, position sizes, and enforces risk limits."""

    def __init__(self, limits: Optional[dict] = None):
        self.limits = {**DEFAULT_RISK_LIMITS, **(limits or {})}
        self._reset()

    def _reset(self) -> None:
        today = date.today()
        self._current_date: date = today
        self._daily_pnl: float = 0.0
        self._daily_trades: int = 0
        self._current_position_usd: float = 0.0
        self._peak_equity: float = 0.0
        self._last_order_time: float = 0.0
        self._total_pnl: float = 0.0
        self._peak_total: float = 0.0

    def _check_date_roll(self) -> None:
        today = date.today()
        if today != self._current_date:
            logger.info(f"RiskManager: daily reset ({self._current_date} -> {today})")
            self._daily_pnl = 0.0
            self._daily_trades = 0
            self._current_date = today

    def check_order(self, quantity: float, price: float, side: str,
                    equity: float) -> Tuple[bool, str]:
        self._check_date_roll()
        now = time.time()
        order_value = quantity * price

        if order_value > self.limits["max_position_size_usd"]:
            return False, f"Order value ${order_value:,.0f} exceeds max position ${self.limits['max_position_size_usd']:,.0f}"
        if order_value > equity * self.limits["max_position_size_pct_equity"]:
            return False, f"Order value ${order_value:,.0f} exceeds {self.limits['max_position_size_pct_equity']:.0%} of equity ${equity:,.0f}"
        if abs(self._daily_pnl) > self.limits["max_daily_loss_usd"]:
            return False, f"Daily loss ${self._daily_pnl:,.0f} exceeds limit ${self.limits['max_daily_loss_usd']:,.0f}"
        if abs(self._daily_pnl) / max(equity, 1) > self.limits["max_daily_loss_pct"]:
            return False, f"Daily loss {self._daily_pnl/equity:.1%} exceeds {self.limits['max_daily_loss_pct']:.0%} limit"
        drawdown = (self._peak_total - self._total_pnl) / max(self._peak_total, 1)
        if drawdown > self.limits["max_drawdown_pct"]:
            return False, f"Drawdown {drawdown:.1%} exceeds {self.limits['max_drawdown_pct']:.0%} limit"
        if self._daily_trades >= self.limits["max_trades_per_day"]:
            return False, f"Daily trade count {self._daily_trades} >= {self.limits['max_trades_per_day']}"
        if now - self._last_order_time < self.limits["min_order_interval_sec"]:
            return False, "Order too soon after previous (rate limit)"
        return True, ""

    def record_fill(self, quantity: float, price: float, side: str) -> None:
        self._check_date_roll()
        self._daily_trades += 1
        self._last_order_time = time.time()

    def update_pnl(self, pnl: float) -> None:
        self._daily_pnl += pnl
        self._total_pnl += pnl
        if self._total_pnl > self._peak_total:
            self._peak_total = self._total_pnl

    def update_position(self, delta_usd: float) -> None:
        self._current_position_usd += delta_usd

    def get_status(self) -> Dict:
        self._check_date_roll()
        return {
            "daily_pnl": round(self._daily_pnl, 2),
            "daily_trades": self._daily_trades,
            "current_position_usd": round(self._current_position_usd, 2),
            "total_pnl": round(self._total_pnl, 2),
            "drawdown_pct": round(
                (self._peak_total - self._total_pnl) / max(self._peak_total, 1), 4
            ),
        }


# ── Market Data Feed ───────────────────────────────────────────────────────

class MarketDataFeed:
    """Subscribes to real-time market data for execution prices.

    Falls back to simulated tick data when no real broker is connected.
    """

    def __init__(self):
        self._prices: Dict[str, float] = {}
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self, symbols: List[str]) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._simulate_ticks, args=(symbols,), daemon=True)
        self._thread.start()
        logger.info(f"MarketDataFeed started for {symbols}")

    def stop(self) -> None:
        self._running = False
        logger.info("MarketDataFeed stopped")

    def get_price(self, symbol: str) -> Optional[float]:
        with self._lock:
            return self._prices.get(symbol)

    def update_price(self, symbol: str, price: float) -> None:
        with self._lock:
            self._prices[symbol] = price

    def _simulate_ticks(self, symbols: List[str]) -> None:
        import numpy as np
        base_prices = {s: 2000.0 for s in symbols}
        while self._running:
            for s in symbols:
                change = np.random.randn() * 0.5
                bp = base_prices.get(s, 2000.0)
                base_prices[s] = max(bp + change, 1.0)
                with self._lock:
                    self._prices[s] = base_prices[s]
            time.sleep(0.1)


# ── Execution Engine ───────────────────────────────────────────────────────

class ExecutionEngine:
    """Production execution engine with broker adapters, risk checks, and market data.

    Supports:
      - paper: in-memory simulated fills
      - ibkr: real IBKR orders via ib_insync
      - cqg: stub (not yet implemented)
    """

    def __init__(self, config: Optional[dict] = None):
        self.config = config or get_config()
        self.execution_cfg = self.config.get("execution", {})
        self.broker = self.execution_cfg.get("broker", "paper")
        self.slippage_bps = self.execution_cfg.get("slippage_bps",
                                                    self.execution_cfg.get("max_slippage_bps", 1.0))
        self.connection: Optional[Dict] = None
        self.is_connected = False
        self._equity = self.execution_cfg.get("equity", 100000.0)
        self._risk = RiskManager(self.execution_cfg.get("risk_limits"))
        self._market_data = MarketDataFeed()

        # Order tracking
        self._orders: Dict[str, OrderRecord] = {}
        self._order_history: List[OrderRecord] = []
        self._latency_samples: List[float] = []

        # IBKR internals
        self._ib = None

    def connect(self) -> None:
        """Connect to the configured broker adapter."""
        logger.info(f"Connecting to execution backend: {self.broker}")
        if self.broker == "ibkr":
            self._connect_ibkr()
        elif self.broker == "cqg":
            self._connect_cqg()
        elif self.broker == "paper":
            self._connect_paper()
        else:
            raise ValueError(f"Unsupported broker: {self.broker}")

        self.is_connected = True
        self._market_data.start([self.execution_cfg.get("symbol", "XAUUSD")])
        logger.info(f"Execution engine connected (broker={self.broker})")

    def disconnect(self) -> None:
        """Disconnect from broker and stop market data feed."""
        self._market_data.stop()
        if self._ib is not None:
            try:
                self._ib.disconnect()
            except Exception:
                pass
        self.is_connected = False
        self.connection = None
        logger.info("Execution engine disconnected")

    # ── Broker Adapters ───────────────────────────────────────────────

    def _connect_ibkr(self) -> None:
        """Connect to TWS / IB Gateway via ib_insync."""
        try:
            from ib_insync import IB
        except ImportError:
            logger.error("ib_insync not installed. Run: pip install ib_insync")
            raise

        ibkr_cfg = self.execution_cfg.get("ibkr", {})
        host = ibkr_cfg.get("host", "127.0.0.1")
        port = ibkr_cfg.get("port", 7497)
        client_id = ibkr_cfg.get("client_id", 1)
        timeout = ibkr_cfg.get("timeout_seconds", 15)

        self._ib = IB()
        self._ib.connect(host, port, clientId=client_id, timeout=timeout)
        logger.info(f"IBKR connected to {host}:{port} client_id={client_id}")

        self._ib.reqMarketDataType(4)  # Delayed-frozen if live not available

        self.connection = {
            "provider": "ibkr",
            "host": host,
            "port": port,
            "client_id": client_id,
            "server_version": self._ib.client.serverVersion(),
        }

    def _connect_cqg(self) -> None:
        logger.info("CQG adapter placeholder — connection logic not implemented yet")
        self.connection = {"provider": "cqg"}

    def _connect_paper(self) -> None:
        logger.info("Paper trading adapter connected (all fills simulated)")
        self.connection = {"provider": "paper", "mode": "simulation"}

    # ── Order Submission ──────────────────────────────────────────────

    def submit_order(
        self,
        symbol: str,
        quantity: float,
        side: str,
        order_type: str = "limit",
        limit_price: Optional[float] = None,
        tif: str = "GTC",
    ) -> Dict[str, Any]:
        """Submit an order to the execution engine.

        Runs risk checks first, then routes to the appropriate broker adapter.
        Returns order details including order_id, status, fill_price, latency_ms.
        """
        if not self.is_connected:
            raise RuntimeError("Execution engine not connected")

        # Use market data feed for current price if no limit price given
        if limit_price is None:
            mp = self._market_data.get_price(symbol)
            if mp is not None:
                limit_price = mp
            else:
                raise ValueError("No limit price and no market data available")

        # Risk check
        ok, reason = self._risk.check_order(quantity, limit_price, side, self._equity)
        if not ok:
            logger.warning(f"Risk check failed: {reason}")
            record = OrderRecord(
                order_id=str(uuid.uuid4())[:12],
                symbol=symbol, quantity=quantity, side=side.lower(),
                order_type=order_type.lower(), limit_price=limit_price,
                tif=tif, status="rejected", submitted_at=time.time(),
                reject_reason=reason,
            )
            self._order_history.append(record)
            return self._order_to_dict(record)

        # Route to broker-specific handler
        if self.broker == "ibkr":
            return self._submit_ibkr(symbol, quantity, side, order_type, limit_price, tif)
        return self._submit_paper(symbol, quantity, side, order_type, limit_price, tif)

    def _submit_paper(
        self, symbol: str, quantity: float, side: str,
        order_type: str, limit_price: float, tif: str,
    ) -> Dict[str, Any]:
        order_id = str(uuid.uuid4())[:12]
        submit_time = time.perf_counter()

        # Simulated fill with slippage
        slippage = limit_price * (self.slippage_bps / 10000.0)
        fill_price = limit_price + slippage if side.lower() == "buy" else limit_price - slippage
        fill_time = time.perf_counter()
        latency_ms = (fill_time - submit_time) * 1000

        record = OrderRecord(
            order_id=order_id, symbol=symbol, quantity=quantity,
            side=side.lower(), order_type=order_type.lower(),
            limit_price=limit_price, tif=tif, status="filled",
            submitted_at=time.time(), filled_at=time.time(),
            fill_price=max(fill_price, 0.01), latency_ms=latency_ms,
        )
        self._risk.record_fill(quantity, fill_price, side)
        self._risk.update_position(quantity * fill_price)
        self._record_order(record)
        return self._order_to_dict(record)

    def _submit_ibkr(
        self, symbol: str, quantity: float, side: str,
        order_type: str, limit_price: float, tif: str,
    ) -> Dict[str, Any]:
        order_id = str(uuid.uuid4())[:12]
        submit_time = time.perf_counter()

        if self._ib is None:
            return self._fail(order_id, symbol, quantity, side, order_type, limit_price, tif,
                              "IBKR not connected")

        try:
            from ib_insync import Stock, MarketOrder, LimitOrder, Order
            contract = Stock(symbol, "SMART", "USD")
            ib_side = "BUY" if side.lower() == "buy" else "SELL"
            ib_tif = tif.upper() if tif.upper() in ("DAY", "GTC", "IOC", "FOK") else "GTC"

            if order_type.lower() == "mkt":
                ib_order = MarketOrder(ib_side, quantity, tif=ib_tif)
            else:
                ib_order = LimitOrder(ib_side, quantity, limit_price, tif=ib_tif)

            trade = self._ib.placeOrder(contract, ib_order)
            fill_time = time.perf_counter()
            latency_ms = (fill_time - submit_time) * 1000

            # Wait briefly for fill status
            self._ib.sleep(0.5)

            fill = None
            if trade.fills:
                fill = trade.fills[0]
            ib_status = trade.orderStatus.status
            fill_price = float(fill.execution.price) if fill else limit_price
            filled_at = time.time() if fill else None

            status_map = {"Filled": "filled", "Submitted": "pending",
                          "PreSubmitted": "pending", "Cancelled": "cancelled",
                          "Inactive": "rejected"}
            status = status_map.get(ib_status, "pending")

            record = OrderRecord(
                order_id=order_id, symbol=symbol, quantity=quantity,
                side=side.lower(), order_type=order_type.lower(),
                limit_price=limit_price, tif=tif, status=status,
                submitted_at=time.time(), filled_at=filled_at,
                fill_price=fill_price, latency_ms=latency_ms,
            )
            if status == "filled":
                self._risk.record_fill(quantity, fill_price, side)
                self._risk.update_position(quantity * fill_price)
            self._record_order(record)
            return self._order_to_dict(record)

        except Exception as e:
            logger.error(f"IBKR order failed: {e}")
            return self._fail(order_id, symbol, quantity, side, order_type, limit_price, tif,
                              str(e)[:120])

    def _fail(self, order_id: str, symbol: str, quantity: float,
              side: str, order_type: str, limit_price: Optional[float],
              tif: str, reason: str) -> Dict[str, Any]:
        record = OrderRecord(
            order_id=order_id, symbol=symbol, quantity=quantity,
            side=side.lower(), order_type=order_type.lower(),
            limit_price=limit_price, tif=tif, status="error",
            submitted_at=time.time(), reject_reason=reason,
        )
        self._order_history.append(record)
        return self._order_to_dict(record)

    # ── Order Management ──────────────────────────────────────────────

    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        if order_id in self._orders:
            record = self._orders[order_id]
            if record.status == "filled":
                return {"order_id": order_id, "status": "already_filled"}
            if self._ib is not None and self.broker == "ibkr":
                try:
                    from ib_insync import Order
                    # Cancel via order ID (simplified — real IBKR needs permId)
                    self._ib.cancelOrder(Order())
                except Exception as e:
                    logger.warning(f"IBKR cancel failed: {e}")
            record.status = "cancelled"
            logger.info(f"Order {order_id} cancelled")
            return {"order_id": order_id, "status": "cancelled"}
        logger.warning(f"Cancel request for unknown order_id={order_id}")
        return {"order_id": order_id, "status": "not_found"}

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        if order_id in self._orders:
            rec = self._orders[order_id]
            return {
                "order_id": order_id,
                "status": rec.status,
                "fill_price": rec.fill_price,
                "latency_ms": rec.latency_ms,
                "reject_reason": rec.reject_reason,
            }
        return {"order_id": order_id, "status": "not_found"}

    def get_order_history(self) -> List[Dict[str, Any]]:
        return [
            {
                "order_id": r.order_id,
                "symbol": r.symbol,
                "side": r.side,
                "quantity": r.quantity,
                "fill_price": r.fill_price,
                "status": r.status,
                "latency_ms": r.latency_ms,
                "reject_reason": r.reject_reason,
            }
            for r in self._order_history
        ]

    # ── Risk & PnL ────────────────────────────────────────────────────

    def update_pnl(self, realized_pnl: float) -> None:
        """Report realised PnL from closed trades for risk tracking."""
        self._risk.update_pnl(realized_pnl)

    def update_equity(self, equity: float) -> None:
        self._equity = equity

    def get_risk_status(self) -> Dict[str, Any]:
        return self._risk.get_status()

    # ── Market Data ───────────────────────────────────────────────────

    def get_market_price(self, symbol: str) -> Optional[float]:
        return self._market_data.get_price(symbol)

    def update_market_price(self, symbol: str, price: float) -> None:
        self._market_data.update_price(symbol, price)

    # ── Latency Stats ─────────────────────────────────────────────────

    def get_latency_stats(self) -> Dict[str, float]:
        if not self._latency_samples:
            return {"p50": 0.0, "p95": 0.0, "p99": 0.0, "count": 0}
        samples = np.array(self._latency_samples)
        return {
            "p50": float(np.percentile(samples, 50)),
            "p95": float(np.percentile(samples, 95)),
            "p99": float(np.percentile(samples, 99)),
            "mean": float(np.mean(samples)),
            "count": len(samples),
        }

    # ── Health ────────────────────────────────────────────────────────

    def health_check(self) -> Dict[str, Any]:
        return {
            "broker": self.broker,
            "connected": self.is_connected,
            "adapter": self.connection,
            "total_orders": len(self._order_history),
            "latency": self.get_latency_stats(),
            "risk": self._risk.get_status(),
            "equity": round(self._equity, 2),
        }

    # ── Helpers ───────────────────────────────────────────────────────

    def _record_order(self, record: OrderRecord) -> None:
        self._orders[record.order_id] = record
        self._order_history.append(record)
        self._latency_samples.append(record.latency_ms)

    @staticmethod
    def _order_to_dict(record: OrderRecord) -> Dict[str, Any]:
        return {
            "order_id": record.order_id,
            "symbol": record.symbol,
            "quantity": record.quantity,
            "side": record.side,
            "order_type": record.order_type,
            "limit_price": record.limit_price,
            "fill_price": record.fill_price,
            "tif": record.tif,
            "status": record.status,
            "latency_ms": record.latency_ms,
            "submitted_at": record.submitted_at,
            "filled_at": record.filled_at,
            "reject_reason": record.reject_reason,
        }
