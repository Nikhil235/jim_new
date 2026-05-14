"""
Risk Manager
=============
Implements Kelly Criterion, circuit breakers, and position management.
"Simons was right 50.75% of the time — but he MANAGED that edge perfectly."

Phase 1 enhancements:
- Model disagreement circuit breaker
- Max latency circuit breaker
- Consecutive loss circuit breaker
- Growth regime Kelly adjustment
- Trade history with win rate tracking
"""

import numpy as np
from typing import Optional, Tuple, List
from loguru import logger
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class PositionState:
    """Current state of a position."""
    direction: int = 0           # -1 short, 0 flat, 1 long
    size: float = 0.0            # Position size in units
    entry_price: float = 0.0
    entry_time: Optional[datetime] = None
    unrealized_pnl: float = 0.0
    peak_equity: float = 0.0
    current_equity: float = 0.0


@dataclass
class RiskState:
    """Current state of risk metrics."""
    daily_pnl: float = 0.0
    peak_equity: float = 0.0
    current_drawdown: float = 0.0
    is_halted: bool = False
    halt_reason: str = ""
    trades_today: int = 0
    wins_today: int = 0
    losses_today: int = 0
    consecutive_losses: int = 0
    last_trade_pnls: list = field(default_factory=list)


class RiskManager:
    """
    Central risk management system.

    Enforces:
    - Kelly Criterion position sizing (dynamic, regime-aware)
    - Circuit breakers (daily loss, drawdown, latency, model disagreement, consecutive loss)
    - Maximum position limits
    - Growth regime adjustment (larger Kelly fraction in calm markets)
    """

    def __init__(self, config: Optional[dict] = None):
        if config:
            risk_cfg = config.get("risk", {})
            kelly_cfg = risk_cfg.get("kelly", {})
            cb_cfg = risk_cfg.get("circuit_breakers", {})
        else:
            kelly_cfg = {}
            cb_cfg = {}

        # Kelly parameters
        self.kelly_fraction = kelly_cfg.get("fraction", 0.5)
        self.max_position_pct = kelly_cfg.get("max_position_pct", 0.05)
        self.crisis_fraction = kelly_cfg.get("crisis_fraction", 0.25)
        self.growth_fraction = kelly_cfg.get("growth_fraction", 0.65)

        # Circuit breaker thresholds
        self.daily_loss_limit = cb_cfg.get("daily_loss_limit", 0.02)
        self.drawdown_reduce = cb_cfg.get("drawdown_reduce", 0.05)
        self.drawdown_stop = cb_cfg.get("drawdown_stop", 0.10)
        self.model_disagreement_threshold = cb_cfg.get("model_disagreement", 0.70)
        self.max_latency_ms = cb_cfg.get("max_latency_ms", 500)
        self.consecutive_loss_limit = cb_cfg.get("consecutive_loss_limit", 3)
        self.consecutive_loss_reduction = cb_cfg.get("consecutive_loss_reduction", 0.25)

        # State
        self.risk_state = RiskState()
        self.position = PositionState()

        logger.info(
            f"RiskManager initialized | Kelly={self.kelly_fraction} | "
            f"MaxPos={self.max_position_pct} | DD_Stop={self.drawdown_stop} | "
            f"MaxLatency={self.max_latency_ms}ms | ConsecLossLimit={self.consecutive_loss_limit}"
        )

    def calculate_kelly_size(
        self,
        win_prob: float,
        avg_win: float,
        avg_loss: float,
        portfolio_value: float,
        regime: str = "NORMAL",
    ) -> float:
        """
        Calculate position size using Dynamic Kelly Criterion.

        f* = (p * b - q) / b  (then apply Half-Kelly and caps)

        Regime-aware adjustments:
        - GROWTH: 65% Kelly (calm markets → slightly larger positions)
        - NORMAL: 50% Kelly (standard Half-Kelly)
        - CRISIS: 25% Kelly (Quarter-Kelly in volatile markets)

        Args:
            win_prob: Probability of winning (from Meta-Label Critic).
            avg_win: Average win amount.
            avg_loss: Average loss amount (positive number).
            portfolio_value: Current portfolio value.
            regime: Current market regime (GROWTH/NORMAL/CRISIS).

        Returns:
            Position size in dollars.
        """
        if avg_loss == 0 or win_prob <= 0:
            return 0.0

        b = avg_win / avg_loss  # Win/loss ratio
        p = win_prob
        q = 1 - p

        # Raw Kelly fraction
        kelly_f = (p * b - q) / b

        if kelly_f <= 0:
            logger.debug(f"Kelly negative ({kelly_f:.4f}) — no edge, skip trade")
            return 0.0

        # Apply regime-specific Kelly fraction
        if regime == "CRISIS":
            adjusted_f = kelly_f * self.crisis_fraction
        elif regime == "GROWTH":
            adjusted_f = kelly_f * self.growth_fraction
        else:
            adjusted_f = kelly_f * self.kelly_fraction

        # Reduce further if consecutive losses
        if self.risk_state.consecutive_losses >= self.consecutive_loss_limit:
            adjusted_f *= (1.0 - self.consecutive_loss_reduction)
            logger.debug(
                f"Kelly reduced by {self.consecutive_loss_reduction:.0%} "
                f"due to {self.risk_state.consecutive_losses} consecutive losses"
            )

        # Cap at max position percentage
        final_f = min(adjusted_f, self.max_position_pct)

        position_size = portfolio_value * final_f

        logger.debug(
            f"Kelly: p={p:.3f} b={b:.2f} raw_f={kelly_f:.4f} "
            f"adj_f={adjusted_f:.4f} final_f={final_f:.4f} "
            f"size=${position_size:.2f} regime={regime}"
        )

        return position_size

    def check_circuit_breakers(
        self,
        portfolio_value: float,
        model_disagreement: float = 0.0,
        data_latency_ms: float = 0.0,
    ) -> Tuple[bool, str]:
        """
        Check all circuit breakers.

        Args:
            portfolio_value: Current portfolio value.
            model_disagreement: Fraction of models that disagree (0.0 to 1.0).
            data_latency_ms: Current data feed latency in milliseconds.

        Returns:
            Tuple of (can_trade, reason_if_blocked)
        """
        # Already halted?
        if self.risk_state.is_halted:
            return False, f"HALTED: {self.risk_state.halt_reason}"

        # Daily loss limit
        daily_loss_pct = abs(self.risk_state.daily_pnl) / portfolio_value if portfolio_value > 0 else 0
        if self.risk_state.daily_pnl < 0 and daily_loss_pct >= self.daily_loss_limit:
            self.risk_state.is_halted = True
            self.risk_state.halt_reason = (
                f"Daily loss limit hit: {daily_loss_pct:.2%} >= {self.daily_loss_limit:.2%}"
            )
            logger.warning(f"🚨 CIRCUIT BREAKER: {self.risk_state.halt_reason}")
            return False, self.risk_state.halt_reason

        # Drawdown stop
        if self.risk_state.current_drawdown >= self.drawdown_stop:
            self.risk_state.is_halted = True
            self.risk_state.halt_reason = (
                f"Max drawdown hit: {self.risk_state.current_drawdown:.2%} >= {self.drawdown_stop:.2%}"
            )
            logger.warning(f"🚨 CIRCUIT BREAKER: {self.risk_state.halt_reason}")
            return False, self.risk_state.halt_reason

        # Max latency breaker
        if data_latency_ms > 0 and data_latency_ms >= self.max_latency_ms:
            self.risk_state.is_halted = True
            self.risk_state.halt_reason = (
                f"Data feed latency too high: {data_latency_ms:.0f}ms >= {self.max_latency_ms}ms"
            )
            logger.warning(f"🚨 CIRCUIT BREAKER: {self.risk_state.halt_reason}")
            return False, self.risk_state.halt_reason

        # Model disagreement breaker
        if model_disagreement > 0 and model_disagreement >= self.model_disagreement_threshold:
            logger.warning(
                f"⚠️  Model disagreement {model_disagreement:.2%} >= "
                f"{self.model_disagreement_threshold:.2%} — minimum position only"
            )
            return True, "MIN_POSITION"

        # Drawdown reduce (not halted, but reduce size)
        if self.risk_state.current_drawdown >= self.drawdown_reduce:
            logger.warning(
                f"⚠️  Drawdown {self.risk_state.current_drawdown:.2%} > "
                f"{self.drawdown_reduce:.2%} — position sizes reduced by 50%"
            )
            return True, "REDUCE_SIZE"

        # Consecutive loss reduction (not halted, but reduce size)
        if self.risk_state.consecutive_losses >= self.consecutive_loss_limit:
            logger.warning(
                f"⚠️  {self.risk_state.consecutive_losses} consecutive losses — "
                f"reducing position sizes by {self.consecutive_loss_reduction:.0%}"
            )
            return True, "REDUCE_SIZE"

        return True, "OK"

    def update_equity(self, current_equity: float) -> None:
        """Update equity tracking for drawdown calculations."""
        self.risk_state.peak_equity = max(self.risk_state.peak_equity, current_equity)
        if self.risk_state.peak_equity > 0:
            self.risk_state.current_drawdown = (
                1 - current_equity / self.risk_state.peak_equity
            )

    def reset_daily(self) -> None:
        """Reset daily counters (call at start of each trading day)."""
        self.risk_state.daily_pnl = 0.0
        self.risk_state.is_halted = False
        self.risk_state.halt_reason = ""
        self.risk_state.trades_today = 0
        self.risk_state.wins_today = 0
        self.risk_state.losses_today = 0
        logger.info("Daily risk counters reset")

    def record_trade(self, pnl: float) -> None:
        """Record a completed trade and update consecutive loss tracking."""
        self.risk_state.daily_pnl += pnl
        self.risk_state.trades_today += 1
        self.risk_state.last_trade_pnls.append(pnl)

        # Keep last 100 trades for rolling stats
        if len(self.risk_state.last_trade_pnls) > 100:
            self.risk_state.last_trade_pnls = self.risk_state.last_trade_pnls[-100:]

        if pnl >= 0:
            self.risk_state.wins_today += 1
            self.risk_state.consecutive_losses = 0  # Reset streak
        else:
            self.risk_state.losses_today += 1
            self.risk_state.consecutive_losses += 1

    def get_rolling_stats(self) -> dict:
        """Get rolling trade statistics from recent trade history."""
        pnls = self.risk_state.last_trade_pnls
        if not pnls:
            return {"win_rate": 0.0, "avg_win": 0.0, "avg_loss": 0.0, "profit_factor": 0.0, "trade_count": 0}

        wins = [p for p in pnls if p >= 0]
        losses = [p for p in pnls if p < 0]
        total_wins = sum(wins) if wins else 0
        total_losses = abs(sum(losses)) if losses else 0

        return {
            "win_rate": len(wins) / len(pnls),
            "avg_win": np.mean(wins) if wins else 0.0,
            "avg_loss": abs(np.mean(losses)) if losses else 0.0,
            "profit_factor": total_wins / total_losses if total_losses > 0 else float("inf"),
            "trade_count": len(pnls),
            "consecutive_losses": self.risk_state.consecutive_losses,
        }

    def get_status(self) -> dict:
        """Get current risk status summary."""
        return {
            "daily_pnl": self.risk_state.daily_pnl,
            "drawdown": self.risk_state.current_drawdown,
            "is_halted": self.risk_state.is_halted,
            "halt_reason": self.risk_state.halt_reason,
            "trades_today": self.risk_state.trades_today,
            "win_rate_today": (
                self.risk_state.wins_today / max(self.risk_state.trades_today, 1)
            ),
            "consecutive_losses": self.risk_state.consecutive_losses,
            "rolling_stats": self.get_rolling_stats(),
        }
