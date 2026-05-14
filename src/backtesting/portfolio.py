"""
Phase 5: Backtester - Portfolio Tracker

This module tracks:
- Open and closed positions
- Real-time P&L calculations
- Equity and drawdown
- Trade statistics (win rate, profit factor, etc.)
- Rolling performance metrics
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from enum import Enum

from loguru import logger

from .events import Direction, FillEvent


class PositionStatus(Enum):
    """Position status."""
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CLOSING = "CLOSING"


@dataclass
class Trade:
    """Single completed trade record."""
    position_id: str
    entry_time: datetime
    exit_time: datetime
    direction: Direction
    entry_price: float
    exit_price: float
    size: int
    pnl: float
    pnl_pct: float
    duration_hours: float
    entry_commission: float
    exit_commission: float
    entry_slippage: float
    exit_slippage: float
    regime_entry: str = "NORMAL"
    regime_exit: str = "NORMAL"

    @property
    def gross_pnl(self) -> float:
        """P&L before commissions and slippage."""
        if self.direction == Direction.LONG:
            return (self.exit_price - self.entry_price) * self.size
        else:
            return (self.entry_price - self.exit_price) * self.size

    @property
    def net_pnl(self) -> float:
        """P&L after all costs."""
        return self.pnl

    @property
    def is_winning_trade(self) -> bool:
        """Whether trade made profit."""
        return self.pnl > 0

    @property
    def win_loss_ratio(self) -> float:
        """Ratio of win to loss size."""
        if self.is_winning_trade:
            return 1.0
        else:
            return -1.0


@dataclass
class OpenPosition:
    """Open position tracking."""
    position_id: str
    symbol: str
    direction: Direction
    size: int
    entry_time: datetime
    entry_price: float
    current_price: float = 0.0
    
    # Costs
    entry_commission: float = 0.0
    entry_slippage: float = 0.0
    
    # P&L
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0
    
    # Stops and targets
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    
    # Metadata
    regime: str = "NORMAL"
    trades_closed: int = 0

    @property
    def status(self) -> PositionStatus:
        return PositionStatus.OPEN

    def update_price(self, new_price: float):
        """Update position with new market price."""
        self.current_price = new_price
        
        if self.direction == Direction.LONG:
            gross_pnl = (new_price - self.entry_price) * self.size
        else:
            gross_pnl = (self.entry_price - new_price) * self.size
        
        # Subtract costs
        total_costs = self.entry_commission + self.entry_slippage
        self.unrealized_pnl = gross_pnl - total_costs
        self.unrealized_pnl_pct = self.unrealized_pnl / (self.entry_price * self.size) if self.entry_price > 0 else 0

    @property
    def max_profit_potential(self) -> float:
        """Current unrealized profit if we close now."""
        return max(0, self.unrealized_pnl)

    @property
    def max_loss(self) -> float:
        """Current unrealized loss if we close now."""
        return min(0, self.unrealized_pnl)


class PortfolioTracker:
    """
    Tracks complete portfolio state during backtest.
    
    Maintains:
    - Initial and current equity
    - Open and closed positions
    - Trade history
    - Performance statistics
    - Drawdown tracking
    """

    def __init__(self, initial_capital: float):
        """Initialize portfolio tracker."""
        self.initial_capital = initial_capital
        self.current_cash = initial_capital
        self.current_equity = initial_capital
        self.peak_equity = initial_capital
        
        self.open_positions: Dict[str, OpenPosition] = {}
        self.closed_trades: List[Trade] = []
        
        self.total_commission_paid = 0.0
        self.total_slippage_paid = 0.0
        
        logger.info(f"Portfolio tracker initialized: ${initial_capital:.2f}")

    def update_equity(self, current_prices: Dict[str, float]):
        """Update total portfolio equity based on current market prices."""
        # Cash position
        equity = self.current_cash
        
        # Open positions value
        for pos in self.open_positions.values():
            pos.update_price(current_prices.get(pos.symbol, pos.entry_price))
            if pos.direction == Direction.LONG:
                equity += pos.size * pos.current_price + pos.unrealized_pnl
            else:
                equity += -pos.size * pos.current_price + pos.unrealized_pnl
        
        self.current_equity = equity
        
        # Track peak for drawdown
        self.peak_equity = max(self.peak_equity, self.current_equity)

    @property
    def current_drawdown(self) -> float:
        """Current drawdown from peak equity."""
        if self.peak_equity == 0:
            return 0.0
        return (self.current_equity - self.peak_equity) / self.peak_equity

    @property
    def current_drawdown_dollars(self) -> float:
        """Current drawdown in dollars."""
        return self.peak_equity - self.current_equity

    @property
    def max_drawdown_ever(self) -> float:
        """Maximum drawdown experienced (trough from peak)."""
        if not self.closed_trades:
            return self.current_drawdown
        
        # Calculate drawdown at each trade close
        max_dd = 0.0
        peak = self.initial_capital
        
        for trade in self.closed_trades:
            equity_after = self.initial_capital
            for closed_trade in self.closed_trades[:self.closed_trades.index(trade) + 1]:
                equity_after += closed_trade.net_pnl
            
            peak = max(peak, equity_after)
            dd = (equity_after - peak) / peak if peak > 0 else 0
            max_dd = min(max_dd, dd)
        
        return max_dd

    def open_position(
        self,
        position_id: str,
        fill: FillEvent,
    ):
        """Record position opening (buy/sell)."""
        pos = OpenPosition(
            position_id=position_id,
            symbol=fill.symbol,
            direction=fill.direction,
            size=fill.size,
            entry_time=fill.timestamp,
            entry_price=fill.fill_price,
            entry_commission=fill.commission,
            entry_slippage=fill.slippage,
        )
        
        self.open_positions[position_id] = pos
        
        # Deduct from cash
        notional = fill.size * fill.fill_price
        self.current_cash -= notional + fill.commission + fill.slippage
        self.total_commission_paid += fill.commission
        self.total_slippage_paid += fill.slippage
        
        logger.info(f"Position opened: {position_id} {fill.direction.name} {fill.size}oz @ ${fill.fill_price:.2f}")

    def close_position(
        self,
        position_id: str,
        fill: FillEvent,
    ) -> Optional[Trade]:
        """Record position closing and create Trade record."""
        if position_id not in self.open_positions:
            logger.warning(f"Attempted to close non-existent position: {position_id}")
            return None
        
        open_pos = self.open_positions[position_id]
        
        # Calculate P&L
        if open_pos.direction == Direction.LONG:
            gross_pnl = (fill.fill_price - open_pos.entry_price) * fill.size
        else:
            gross_pnl = (open_pos.entry_price - fill.fill_price) * fill.size
        
        total_costs = open_pos.entry_commission + open_pos.entry_slippage + fill.commission + fill.slippage
        net_pnl = gross_pnl - total_costs
        net_pnl_pct = net_pnl / (open_pos.entry_price * fill.size) if open_pos.entry_price > 0 else 0
        
        # Create trade record
        trade = Trade(
            position_id=position_id,
            entry_time=open_pos.entry_time,
            exit_time=fill.timestamp,
            direction=open_pos.direction,
            entry_price=open_pos.entry_price,
            exit_price=fill.fill_price,
            size=fill.size,
            pnl=net_pnl,
            pnl_pct=net_pnl_pct,
            duration_hours=(fill.timestamp - open_pos.entry_time).total_seconds() / 3600,
            entry_commission=open_pos.entry_commission,
            exit_commission=fill.commission,
            entry_slippage=open_pos.entry_slippage,
            exit_slippage=fill.slippage,
        )
        
        self.closed_trades.append(trade)
        
        # Remove from open positions
        del self.open_positions[position_id]
        
        # Update cash (add back notional + P&L)
        notional = fill.size * fill.fill_price
        self.current_cash += notional + net_pnl - fill.commission - fill.slippage
        self.total_commission_paid += fill.commission
        self.total_slippage_paid += fill.slippage
        
        # Log trade
        status = "WIN" if trade.is_winning_trade else "LOSS"
        logger.info(
            f"Position closed: {position_id} {status} ${net_pnl:.2f} "
            f"({net_pnl_pct*100:.2f}%) in {trade.duration_hours:.1f}h"
        )
        
        return trade

    # Statistics methods
    
    @property
    def total_trades(self) -> int:
        """Total completed trades."""
        return len(self.closed_trades)

    @property
    def winning_trades(self) -> int:
        """Number of winning trades."""
        return sum(1 for t in self.closed_trades if t.is_winning_trade)

    @property
    def losing_trades(self) -> int:
        """Number of losing trades."""
        return sum(1 for t in self.closed_trades if not t.is_winning_trade)

    @property
    def win_rate(self) -> float:
        """Win rate as percentage."""
        if self.total_trades == 0:
            return 0.0
        return self.winning_trades / self.total_trades

    @property
    def total_pnl(self) -> float:
        """Total P&L from all trades."""
        return sum(t.net_pnl for t in self.closed_trades)

    @property
    def total_pnl_pct(self) -> float:
        """Total P&L as % of initial capital."""
        return self.total_pnl / self.initial_capital if self.initial_capital > 0 else 0

    @property
    def avg_trade_pnl(self) -> float:
        """Average P&L per trade."""
        return self.total_pnl / self.total_trades if self.total_trades > 0 else 0

    @property
    def avg_winning_trade(self) -> float:
        """Average P&L of winning trades."""
        winning = [t.net_pnl for t in self.closed_trades if t.is_winning_trade]
        return sum(winning) / len(winning) if winning else 0

    @property
    def avg_losing_trade(self) -> float:
        """Average P&L of losing trades."""
        losing = [t.net_pnl for t in self.closed_trades if not t.is_winning_trade]
        return sum(losing) / len(losing) if losing else 0

    @property
    def profit_factor(self) -> float:
        """Profit factor: (sum of wins) / (abs sum of losses)."""
        wins = sum(t.net_pnl for t in self.closed_trades if t.is_winning_trade)
        losses = abs(sum(t.net_pnl for t in self.closed_trades if not t.is_winning_trade))
        return wins / losses if losses > 0 else float('inf')

    @property
    def avg_trade_duration_hours(self) -> float:
        """Average trade duration in hours."""
        if not self.closed_trades:
            return 0
        return sum(t.duration_hours for t in self.closed_trades) / len(self.closed_trades)

    def get_stats(self) -> Dict:
        """Get complete portfolio statistics."""
        return {
            "initial_capital": self.initial_capital,
            "current_equity": self.current_equity,
            "total_pnl": self.total_pnl,
            "total_pnl_pct": self.total_pnl_pct,
            "current_drawdown": self.current_drawdown,
            "max_drawdown": self.max_drawdown_ever,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": self.win_rate,
            "avg_trade_pnl": self.avg_trade_pnl,
            "profit_factor": self.profit_factor,
            "avg_trade_duration": self.avg_trade_duration_hours,
            "total_commission": self.total_commission_paid,
            "total_slippage": self.total_slippage_paid,
            "open_positions": len(self.open_positions),
        }
