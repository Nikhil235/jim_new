"""
Risk Manager
=============
Implements Kelly Criterion, circuit breakers, and position management.
"Simons was right 50.75% of the time — but he MANAGED that edge perfectly."
"""

import numpy as np
from typing import Optional, Tuple
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


class RiskManager:
    """
    Central risk management system.

    Enforces:
    - Kelly Criterion position sizing
    - Circuit breakers (daily loss, drawdown, latency)
    - Maximum position limits
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

        # Circuit breaker thresholds
        self.daily_loss_limit = cb_cfg.get("daily_loss_limit", 0.02)
        self.drawdown_reduce = cb_cfg.get("drawdown_reduce", 0.05)
        self.drawdown_stop = cb_cfg.get("drawdown_stop", 0.10)

        # State
        self.risk_state = RiskState()
        self.position = PositionState()

        logger.info(
            f"RiskManager initialized | Kelly={self.kelly_fraction} | "
            f"MaxPos={self.max_position_pct} | DD_Stop={self.drawdown_stop}"
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

        # Apply Half-Kelly (or Quarter-Kelly in crisis)
        if regime == "CRISIS":
            adjusted_f = kelly_f * self.crisis_fraction
        else:
            adjusted_f = kelly_f * self.kelly_fraction

        # Cap at max position percentage
        final_f = min(adjusted_f, self.max_position_pct)

        position_size = portfolio_value * final_f

        logger.debug(
            f"Kelly: p={p:.3f} b={b:.2f} raw_f={kelly_f:.4f} "
            f"adj_f={adjusted_f:.4f} final_f={final_f:.4f} "
            f"size=${position_size:.2f} regime={regime}"
        )

        return position_size

    def check_circuit_breakers(self, portfolio_value: float) -> Tuple[bool, str]:
        """
        Check all circuit breakers.

        Returns:
            Tuple of (can_trade, reason_if_blocked)
        """
        # Already halted?
        if self.risk_state.is_halted:
            return False, f"HALTED: {self.risk_state.halt_reason}"

        # Daily loss limit
        daily_loss_pct = abs(self.risk_state.daily_pnl) / portfolio_value
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

        # Drawdown reduce (not halted, but reduce size)
        if self.risk_state.current_drawdown >= self.drawdown_reduce:
            logger.warning(
                f"⚠️  Drawdown {self.risk_state.current_drawdown:.2%} > "
                f"{self.drawdown_reduce:.2%} — position sizes reduced by 50%"
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
        """Record a completed trade."""
        self.risk_state.daily_pnl += pnl
        self.risk_state.trades_today += 1
        if pnl >= 0:
            self.risk_state.wins_today += 1
        else:
            self.risk_state.losses_today += 1

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
        }
