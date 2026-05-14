"""
Position Manager
================
Manages the complete position lifecycle:
- Signal generation → Meta-label check → Kelly sizing → Execution
- Real-time monitoring → Exit (signal/stop/target)

Integrates: Models, Critic, Risk Manager, Execution Engine
"""

import numpy as np
from typing import Optional, Tuple, List
from loguru import logger
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class Position:
    """Active trading position."""
    position_id: str
    direction: int  # -1, 0, 1
    size: float  # Quantity
    entry_price: float
    entry_time: datetime
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    pnl: float = 0.0
    pnl_pct: float = 0.0
    trailing_stop_price: Optional[float] = None
    target_price: Optional[float] = None
    max_profit: float = 0.0
    status: str = "OPEN"  # OPEN, CLOSED, CANCELLED


@dataclass
class ExecutionSignal:
    """Signal ready for execution after all checks."""
    position_id: str
    direction: int
    size: float
    entry_price: float
    reason: str  # Why we're entering
    trader_confidence: float
    critic_confidence: float
    kelly_fraction: float
    approved: bool


class PositionManager:
    """
    Position lifecycle manager.
    
    Workflow:
    1. Signal from models → CriticInput
    2. Meta-label check (Critic predicts accuracy)
    3. Kelly sizing (based on Critic confidence)
    4. Risk checks (VaR, circuit breakers)
    5. Execute (TWAP/VWAP for larger orders)
    6. Monitor (trailing stop + time stop)
    7. Exit (reversal signal / stop / target)
    """
    
    def __init__(self, config: Optional[dict] = None):
        """
        Args:
            config: Configuration dict with position manager settings.
        """
        if config:
            pm_cfg = config.get("position_manager", {})
        else:
            pm_cfg = {}
        
        # Position limits
        self.max_positions = pm_cfg.get("max_positions", 5)
        self.max_position_days = pm_cfg.get("max_position_days", 10)
        
        # Stops and targets
        self.trailing_stop_pct = pm_cfg.get("trailing_stop_pct", 0.02)  # 2%
        self.time_stop_hours = pm_cfg.get("time_stop_hours", 24)
        self.profit_target_pct = pm_cfg.get("profit_target_pct", 0.05)  # 5%
        
        # State
        self.positions: List[Position] = []
        self.closed_positions: List[Position] = []
        self.position_counter = 0
        
        logger.info(
            f"PositionManager initialized | max_pos={self.max_positions} | "
            f"max_days={self.max_position_days} | trailing_stop={self.trailing_stop_pct:.2%}"
        )
    
    def open_position(
        self,
        direction: int,
        size: float,
        entry_price: float,
        trader_confidence: float,
        critic_confidence: float,
        kelly_fraction: float,
        reason: str = "",
    ) -> ExecutionSignal:
        """
        Open a new position after all checks pass.
        
        Args:
            direction: -1 (short), 1 (long)
            size: Position size (units)
            entry_price: Entry price
            trader_confidence: Model ensemble confidence
            critic_confidence: Meta-labeler confidence
            kelly_fraction: Kelly fraction used for sizing
            reason: Description of reason for entry
        
        Returns:
            ExecutionSignal with approved=True/False
        """
        # Check position limits
        if len(self.positions) >= self.max_positions:
            logger.warning(f"Max positions ({self.max_positions}) reached — rejecting new entry")
            return ExecutionSignal(
                position_id="", direction=direction, size=size, entry_price=entry_price,
                reason=reason, trader_confidence=trader_confidence,
                critic_confidence=critic_confidence, kelly_fraction=kelly_fraction,
                approved=False,
            )
        
        # Generate position ID
        self.position_counter += 1
        position_id = f"POS_{self.position_counter:05d}"
        
        # Create position
        position = Position(
            position_id=position_id,
            direction=direction,
            size=size,
            entry_price=entry_price,
            entry_time=datetime.utcnow(),
            trailing_stop_price=entry_price * (1 - self.trailing_stop_pct * np.sign(direction)),
            target_price=entry_price * (1 + self.profit_target_pct * direction),
        )
        
        self.positions.append(position)
        
        logger.info(
            f"Position opened: {position_id} {direction:+d} × {size:.2f} @ {entry_price:.2f} | "
            f"Reason: {reason} | Critic: {critic_confidence:.2%}"
        )
        
        return ExecutionSignal(
            position_id=position_id,
            direction=direction,
            size=size,
            entry_price=entry_price,
            reason=reason,
            trader_confidence=trader_confidence,
            critic_confidence=critic_confidence,
            kelly_fraction=kelly_fraction,
            approved=True,
        )
    
    def update_position(
        self,
        position_id: str,
        current_price: float,
    ) -> Optional[Tuple[str, float]]:
        """
        Update position P&L and check exit conditions.
        
        Returns:
            Tuple of (exit_reason, exit_price) if position should close, else None.
        """
        position = self._get_position(position_id)
        if not position:
            return None
        
        # Update P&L
        price_move = current_price - position.entry_price
        position.pnl = position.direction * price_move * position.size
        position.pnl_pct = price_move / position.entry_price if position.entry_price > 0 else 0
        
        # Track max profit
        if position.direction > 0:
            position.max_profit = max(position.max_profit, position.pnl)
        else:
            position.max_profit = max(position.max_profit, -position.pnl)
        
        # Check trailing stop
        if position.direction > 0 and current_price < position.trailing_stop_price:
            return "trailing_stop_hit", current_price
        elif position.direction < 0 and current_price > position.trailing_stop_price:
            return "trailing_stop_hit", current_price
        
        # Update trailing stop
        if position.direction > 0 and current_price > position.entry_price:
            position.trailing_stop_price = max(
                position.trailing_stop_price,
                current_price * (1 - self.trailing_stop_pct),
            )
        elif position.direction < 0 and current_price < position.entry_price:
            position.trailing_stop_price = min(
                position.trailing_stop_price,
                current_price * (1 + self.trailing_stop_pct),
            )
        
        # Check profit target
        if position.direction > 0 and current_price >= position.target_price:
            return "profit_target_hit", current_price
        elif position.direction < 0 and current_price <= position.target_price:
            return "profit_target_hit", current_price
        
        # Check time stop
        if datetime.utcnow() - position.entry_time > timedelta(hours=self.time_stop_hours):
            return "time_stop_hit", current_price
        
        return None
    
    def close_position(
        self,
        position_id: str,
        exit_price: float,
        reason: str = "",
    ) -> Optional[Position]:
        """
        Close an open position.
        
        Returns:
            Closed Position, or None if not found.
        """
        position = self._get_position(position_id)
        if not position:
            return None
        
        position.exit_price = exit_price
        position.exit_time = datetime.utcnow()
        position.pnl = position.direction * (exit_price - position.entry_price) * position.size
        position.pnl_pct = (exit_price - position.entry_price) / position.entry_price
        position.status = "CLOSED"
        
        self.positions.remove(position)
        self.closed_positions.append(position)
        
        holding_time = (position.exit_time - position.entry_time).total_seconds() / 3600
        
        logger.info(
            f"Position closed: {position_id} | P&L: {position.pnl:+.2f} ({position.pnl_pct:+.2%}) | "
            f"Held: {holding_time:.1f}h | Reason: {reason}"
        )
        
        return position
    
    def get_open_positions(self) -> List[Position]:
        """Get all open positions."""
        return self.positions.copy()
    
    def get_position_stats(self) -> dict:
        """Get statistics on position history."""
        if not self.closed_positions:
            return {
                "total_closed": 0,
                "win_rate": 0.0,
                "avg_pnl": 0.0,
                "total_pnl": 0.0,
                "profit_factor": 0.0,
            }
        
        pnls = [p.pnl for p in self.closed_positions]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]
        
        total_wins = sum(wins) if wins else 0
        total_losses = abs(sum(losses)) if losses else 0
        
        return {
            "total_closed": len(self.closed_positions),
            "win_rate": len(wins) / len(pnls) if pnls else 0.0,
            "avg_pnl": np.mean(pnls) if pnls else 0.0,
            "total_pnl": sum(pnls),
            "profit_factor": total_wins / total_losses if total_losses > 0 else float("inf"),
            "open_positions": len(self.positions),
        }
    
    def _get_position(self, position_id: str) -> Optional[Position]:
        """Find a position by ID."""
        for pos in self.positions:
            if pos.position_id == position_id:
                return pos
        return None
