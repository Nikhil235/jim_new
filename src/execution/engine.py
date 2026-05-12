"""Execution Engine
==========================

Provides a lightweight order execution interface and placeholder broker adapters.
This is the Phase 1 execution skeleton that can be extended into a real C++/Rust engine.

Phase 1 enhancements:
- Order ID tracking with UUID generation
- Complete order history with fill records
- Latency measurement on every order submission
- Simulated paper trading fills with configurable slippage
"""

import time
import uuid
from typing import Any, Dict, List, Optional
from loguru import logger
from dataclasses import dataclass, field
from datetime import datetime

from src.utils.config import get_config


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


class ExecutionEngine:
    """Execution engine abstraction for paper and live modes.

    Tracks all orders with unique IDs, records fill latency,
    and maintains a full order history for backtesting analysis.
    """

    def __init__(self, config: Optional[dict] = None):
        self.config = config or get_config()
        self.execution_cfg = self.config.get("execution", {})
        self.broker = self.execution_cfg.get("broker", "ibkr")
        self.slippage_bps = self.execution_cfg.get("max_slippage_bps", 1.0)
        self.connection = None
        self.is_connected = False

        # Order tracking
        self._orders: Dict[str, OrderRecord] = {}
        self._order_history: List[OrderRecord] = []
        self._latency_samples: List[float] = []

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
        logger.info("Execution engine connected")

    def _connect_ibkr(self) -> None:
        ibkr_cfg = self.execution_cfg.get("ibkr", {})
        host = ibkr_cfg.get("host", "127.0.0.1")
        port = ibkr_cfg.get("port", 7497)
        client_id = ibkr_cfg.get("client_id", 1)
        logger.info(f"IBKR adapter placeholder connecting to {host}:{port} client_id={client_id}")
        self.connection = {
            "provider": "ibkr",
            "host": host,
            "port": port,
            "client_id": client_id,
        }

    def _connect_cqg(self) -> None:
        logger.info("CQG adapter placeholder - connection logic not implemented yet")
        self.connection = {"provider": "cqg"}

    def _connect_paper(self) -> None:
        """Paper trading mode — all orders are simulated locally."""
        logger.info("Paper trading adapter connected (all fills simulated)")
        self.connection = {"provider": "paper", "mode": "simulation"}

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

        Generates a unique order ID, measures submission latency,
        and records the fill in order history.

        Returns:
            Dict with order details including order_id, status, and latency_ms.
        """
        if not self.is_connected:
            raise RuntimeError("Execution engine not connected")

        order_id = str(uuid.uuid4())[:12]
        submit_time = time.perf_counter()

        # Simulate fill with slippage
        if limit_price is not None:
            slippage = limit_price * (self.slippage_bps / 10000.0)
            if side.lower() == "buy":
                fill_price = limit_price + slippage
            else:
                fill_price = limit_price - slippage
        else:
            fill_price = None

        fill_time = time.perf_counter()
        latency_ms = (fill_time - submit_time) * 1000

        record = OrderRecord(
            order_id=order_id,
            symbol=symbol,
            quantity=quantity,
            side=side.lower(),
            order_type=order_type.lower(),
            limit_price=limit_price,
            tif=tif,
            status="filled" if fill_price else "pending",
            submitted_at=time.time(),
            filled_at=time.time() if fill_price else None,
            fill_price=fill_price,
            latency_ms=latency_ms,
        )

        self._orders[order_id] = record
        self._order_history.append(record)
        self._latency_samples.append(latency_ms)

        logger.info(
            f"[EXECUTION] Order {order_id}: {side.upper()} {quantity} {symbol} "
            f"@ {fill_price:.2f} | latency={latency_ms:.3f}ms"
            if fill_price else
            f"[EXECUTION] Order {order_id}: {side.upper()} {quantity} {symbol} | PENDING"
        )

        return {
            "order_id": order_id,
            "symbol": symbol,
            "quantity": quantity,
            "side": side.lower(),
            "order_type": order_type.lower(),
            "limit_price": limit_price,
            "fill_price": fill_price,
            "tif": tif,
            "status": record.status,
            "latency_ms": latency_ms,
            "submitted_at": record.submitted_at,
            "filled_at": record.filled_at,
        }

    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel an existing order."""
        if order_id in self._orders:
            self._orders[order_id].status = "cancelled"
            logger.info(f"Order {order_id} cancelled")
            return {"order_id": order_id, "status": "cancelled"}
        logger.warning(f"Cancel request for unknown order_id={order_id}")
        return {"order_id": order_id, "status": "not_found"}

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Return the current order status."""
        if order_id in self._orders:
            rec = self._orders[order_id]
            return {
                "order_id": order_id,
                "status": rec.status,
                "fill_price": rec.fill_price,
                "latency_ms": rec.latency_ms,
            }
        return {"order_id": order_id, "status": "not_found"}

    def get_order_history(self) -> List[Dict[str, Any]]:
        """Return full order history as list of dicts."""
        return [
            {
                "order_id": r.order_id,
                "symbol": r.symbol,
                "side": r.side,
                "quantity": r.quantity,
                "fill_price": r.fill_price,
                "status": r.status,
                "latency_ms": r.latency_ms,
            }
            for r in self._order_history
        ]

    def get_latency_stats(self) -> Dict[str, float]:
        """Return latency statistics (p50, p95, p99)."""
        import numpy as np
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

    def health_check(self) -> Dict[str, Any]:
        """Return execution engine health info including latency stats."""
        return {
            "broker": self.broker,
            "connected": self.is_connected,
            "adapter": self.connection,
            "total_orders": len(self._order_history),
            "latency": self.get_latency_stats(),
        }
