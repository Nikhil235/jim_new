"""
Phase 5: Backtester - Main Event Loop Orchestrator

This is the heart of the backtesting system. It:
1. Loads historical data
2. Generates trading signals from strategies
3. Applies risk management (Kelly sizing, circuit breakers)
4. Executes orders realistically
5. Tracks portfolio performance
6. Processes events in strict chronological order (prevents lookahead bias)
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass

import numpy as np
from loguru import logger

from .events import (
    EventType, MarketEvent, SignalEvent, OrderEvent, FillEvent, StatusEvent,
    Direction, OrderType, OrderStatus
)
from .data_handler import DataHandler
from .execution import ExecutionSimulator, ExecutionConfig
from .portfolio import PortfolioTracker, PositionStatus

# Integration: Performance and Risk Monitoring (Phase 6)
# Lazy imports to avoid circular dependencies
ModelPerformanceMonitor = None
AdvancedRiskCalculator = None


@dataclass
class BacktestConfig:
    """Backtester configuration."""
    initial_capital: float = 100000.0      # Starting capital ($)
    kelly_fraction: float = 0.5             # Kelly criterion fraction
    max_position_pct: float = 0.05         # Max position size
    risk_per_trade: float = 0.02           # Risk per trade (2%)
    
    # Execution
    commission_per_trade: float = 1.0
    commission_pct: float = 0.0001
    slippage_model: str = "spread"         # 'fixed', 'spread', 'impact'
    slippage_pct: float = 0.5
    
    # Circuit breakers
    daily_loss_limit: float = 0.05         # Max daily loss %
    max_drawdown_limit: float = 0.15       # Max drawdown %
    consecutive_loss_limit: int = 3        # Max consecutive losses


class Backtester:
    """
    Event-driven backtester.
    
    Processes events in strict chronological order:
    1. MarketEvent arrives
    2. Strategy generates SignalEvent
    3. Risk manager checks (Kelly, circuit breakers)
    4. ExecutionSimulator fills order
    5. PortfolioTracker updates position
    
    This sequential processing prevents lookahead bias.
    """

    def __init__(
        self,
        config: Optional[BacktestConfig] = None,
        data_handler: Optional[DataHandler] = None,
    ):
        """Initialize backtester."""
        self.config = config or BacktestConfig()
        self.data_handler = data_handler
        
        # Core components
        self.portfolio = PortfolioTracker(self.config.initial_capital)
        exec_config = ExecutionConfig(
            commission_per_trade=self.config.commission_per_trade,
            commission_pct=self.config.commission_pct,
            slippage_pct=self.config.slippage_pct,
        )
        self.execution = ExecutionSimulator(exec_config)
        
        # State tracking
        self.current_market: Optional[MarketEvent] = None
        self.market_history: List[MarketEvent] = []
        self.signals_generated: List[SignalEvent] = []
        self.orders_placed: List[OrderEvent] = []
        self.fills_executed: List[FillEvent] = []
        self.status_events: List[StatusEvent] = []
        
        # Strategy callback
        self.strategy_fn: Optional[Callable] = None
        
        # Circuit breaker state
        self.daily_pnl = 0.0
        self.daily_reset_time = None
        self.consecutive_losses = 0
        
        # Integration: Performance monitoring for Phase 6 (lazy load to avoid circular imports)
        self.performance_monitor = None
        try:
            from src.models.performance_monitor import ModelPerformanceMonitor as PerfMon
            self.performance_monitor = PerfMon()
        except Exception as e:
            logger.debug(f"Performance monitor not available: {e}")
        
        logger.info(f"Backtester initialized with ${self.config.initial_capital:.2f} capital")

    def set_strategy(self, strategy_fn: Callable):
        """
        Set the strategy function.
        
        Args:
            strategy_fn: Function that takes (backtester, market_event) 
                        and returns list of SignalEvent objects
        """
        self.strategy_fn = strategy_fn
        strategy_name = getattr(strategy_fn, '__name__', type(strategy_fn).__name__)
        logger.info(f"Strategy set: {strategy_name}")

    def run(
        self,
        start_date: datetime,
        end_date: datetime,
        data_handler: Optional[DataHandler] = None,
    ) -> Dict:
        """
        Run backtest for date range.
        
        Args:
            start_date: Backtest start
            end_date: Backtest end
            data_handler: Data source (uses self.data_handler if None)
            
        Returns:
            Backtest results dictionary
        """
        if not self.strategy_fn:
            raise ValueError("Strategy not set. Call set_strategy() first.")
        
        data_handler = data_handler or self.data_handler
        if not data_handler:
            logger.error("No data handler available")
            return {}
        
        logger.info(f"Starting backtest: {start_date} to {end_date}")
        
        try:
            # Process market data stream
            for market_event in data_handler.load_data(start_date, end_date):
                self._process_market_event(market_event)
            
            # Close any remaining open positions at end of backtest
            self._liquidate_at_end(market_event)
            
            # Generate results
            results = self._generate_results(end_date)
            
            logger.info(f"Backtest complete: {results['total_trades']} trades")
            
            return results
            
        except Exception as e:
            logger.error(f"Backtest failed: {e}")
            raise

    def _process_market_event(self, market_event: MarketEvent):
        """Process new market data."""
        # Update current market
        self.current_market = market_event
        self.market_history.append(market_event)
        
        # Update portfolio equity
        self.portfolio.update_equity({market_event.symbol: market_event.close_price})
        
        # Check circuit breakers
        if not self._check_circuit_breakers():
            return
        
        # Reset daily P&L if new day
        self._reset_daily_pnl_if_needed(market_event.timestamp)
        
        # Generate signals from strategy
        if self.strategy_fn:
            signals = self.strategy_fn(self, market_event)
            if signals:
                for signal in signals:
                    self._process_signal(signal, market_event)

    def _process_signal(self, signal: SignalEvent, market: MarketEvent):
        """Process trading signal."""
        self.signals_generated.append(signal)
        
        # Skip if signal is neutral (flat)
        if signal.direction == Direction.FLAT:
            return
        
        # Check if we already have a position
        if any(p.direction == signal.direction for p in self.portfolio.open_positions.values()):
            logger.debug("Already have position in this direction, skipping")
            return
        
        # Calculate Kelly-sized position
        order_size = self._calculate_kelly_size(signal, market)
        if order_size == 0:
            logger.debug(f"Kelly size is zero, skipping signal")
            return
        
        # Create order
        order = self._create_order(signal, order_size, market)
        self.orders_placed.append(order)
        
        # Execute order
        fill, status = self.execution.execute_order(order, market)
        
        if status:
            # Order rejected or modified
            self.status_events.append(status)
            logger.warning(f"Order rejected: {status.message}")
            return
        
        # Record fill
        self.fills_executed.append(fill)
        self.portfolio.open_position(order.position_id, fill)

    def _calculate_kelly_size(self, signal: SignalEvent, market: MarketEvent) -> int:
        """
        Calculate position size using Kelly Criterion.
        
        Kelly formula: f* = (p*b - q) / b
        where:
            p = win probability
            b = win/loss ratio
            q = 1 - p
        
        We use historical win rate as approximation for p.
        """
        if self.portfolio.total_trades < 10:
            # Use default kelly fraction if not enough history
            kelly_size = int(self.config.initial_capital * self.config.kelly_fraction / market.close_price)
        else:
            # Calculate from portfolio stats
            win_rate = self.portfolio.win_rate
            avg_win = self.portfolio.avg_winning_trade
            avg_loss = abs(self.portfolio.avg_losing_trade)
            
            if avg_loss == 0:
                kelly_fraction = self.config.kelly_fraction
            else:
                win_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 1.0
                kelly_fraction = (win_rate * win_loss_ratio - (1 - win_rate)) / win_loss_ratio
                kelly_fraction = max(0, min(kelly_fraction, 1.0))  # Clip to [0, 1]
            
            kelly_size = int(self.config.initial_capital * kelly_fraction / market.close_price)
        
        # Apply position size limit
        max_position_size = int(self.portfolio.current_equity * self.config.max_position_pct / market.close_price)
        kelly_size = min(kelly_size, max_position_size)
        
        return kelly_size

    def _create_order(self, signal: SignalEvent, size: int, market: MarketEvent) -> OrderEvent:
        """Create order from signal."""
        position_id = str(uuid.uuid4())[:8]
        order_id = str(uuid.uuid4())[:8]
        
        return OrderEvent(
            event_type=EventType.ORDER,
            timestamp=market.timestamp,
            order_id=order_id,
            position_id=position_id,
            symbol=market.symbol,
            direction=signal.direction,
            size=size,
            order_type=OrderType.MARKET,
            commission=self.config.commission_per_trade,
            kelly_fraction=self.config.kelly_fraction,
            reason=f"Signal from {signal.model_name}",
        )

    def _check_circuit_breakers(self) -> bool:
        """
        Check if any circuit breaker is triggered.
        
        Returns:
            True if trading should continue, False if halted
        """
        # Check max drawdown
        if self.portfolio.current_drawdown < -self.config.max_drawdown_limit:
            logger.error(f"Circuit breaker: Max drawdown limit exceeded ({self.portfolio.current_drawdown:.2%})")
            return False
        
        # Check daily loss
        daily_pnl = self._calculate_daily_pnl()
        if daily_pnl < -self.config.initial_capital * self.config.daily_loss_limit:
            logger.error(f"Circuit breaker: Daily loss limit exceeded (${daily_pnl:.2f})")
            return False
        
        # Check consecutive losses
        if self.consecutive_losses >= self.config.consecutive_loss_limit:
            logger.error(f"Circuit breaker: {self.consecutive_losses} consecutive losses")
            return False
        
        return True

    def _reset_daily_pnl_if_needed(self, current_time: datetime):
        """Reset daily P&L tracking if new day."""
        if self.daily_reset_time is None:
            self.daily_reset_time = current_time.date()
            self.daily_pnl = 0.0
        elif current_time.date() > self.daily_reset_time:
            # New day - reset tracking
            self.daily_reset_time = current_time.date()
            self.daily_pnl = 0.0
            self.consecutive_losses = 0

    def _calculate_daily_pnl(self) -> float:
        """Calculate today's P&L from closed trades."""
        if not self.daily_reset_time:
            return 0.0
        
        today = self.current_market.timestamp.date()
        daily_trades = [
            t for t in self.portfolio.closed_trades
            if t.exit_time.date() == today
        ]
        
        return sum(t.net_pnl for t in daily_trades)

    def _liquidate_at_end(self, market_event: MarketEvent):
        """Close all remaining open positions at end of backtest."""
        if not market_event:
            return
        
        for pos_id, position in list(self.portfolio.open_positions.items()):
            # Create closing fill at market price
            closing_fill = FillEvent(
                event_type=EventType.FILL,
                timestamp=market_event.timestamp,
                order_id=str(uuid.uuid4())[:8],
                position_id=pos_id,
                symbol=market_event.symbol,
                direction=position.direction,
                size=position.size,
                fill_price=market_event.close_price,
                commission=self.config.commission_per_trade,
                slippage=0,
                status=OrderStatus.FILLED,
            )
            
            self.portfolio.close_position(pos_id, closing_fill)
            logger.info(f"Liquidated position {pos_id} at close")

    def _generate_results(self, end_date: datetime) -> Dict:
        """Generate backtest results including advanced metrics (Phase 6)."""
        stats = self.portfolio.get_stats()
        
        # Base results
        results = {
            "period_start": self.market_history[0].timestamp if self.market_history else None,
            "period_end": end_date,
            "market_events": len(self.market_history),
            "signals_generated": len(self.signals_generated),
            "orders_placed": len(self.orders_placed),
            "fills_executed": len(self.fills_executed),
            
            # Performance
            "initial_capital": stats["initial_capital"],
            "final_equity": stats["current_equity"],
            "total_return": stats["total_pnl_pct"],
            "total_pnl": stats["total_pnl"],
            "max_drawdown": stats["max_drawdown"],
            
            # Trade stats
            "total_trades": stats["total_trades"],
            "winning_trades": stats["winning_trades"],
            "losing_trades": stats["losing_trades"],
            "win_rate": stats["win_rate"],
            "profit_factor": stats["profit_factor"],
            "avg_trade_duration": stats["avg_trade_duration"],
            
            # Costs
            "total_commission": stats["total_commission"],
            "total_slippage": stats["total_slippage"],
            
            # Portfolio state
            "open_positions": stats["open_positions"],
        }
        
        # Integration: Calculate advanced risk metrics (Phase 6 - lazy load to avoid circular imports)
        try:
            from src.risk.advanced_metrics import AdvancedRiskCalculator
            
            if len(self.portfolio.equity_curve) > 1:
                returns = np.diff(self.portfolio.equity_curve) / self.portfolio.equity_curve[:-1]
                
                # Calculate advanced metrics
                omega = AdvancedRiskCalculator.calculate_omega_ratio(returns)
                ulcer = AdvancedRiskCalculator.calculate_ulcer_index(self.portfolio.equity_curve)
                cvar = AdvancedRiskCalculator.calculate_conditional_var(returns)
                es = AdvancedRiskCalculator.calculate_expected_shortfall(returns)
                skew, kurt, tail = AdvancedRiskCalculator.calculate_tail_risk_metrics(returns)
                recovery = AdvancedRiskCalculator.calculate_recovery_factor(
                    stats["total_pnl_pct"], 
                    stats["max_drawdown"]
                )
                
                # Add to results
                results["advanced_metrics"] = {
                    "omega_ratio": omega,
                    "ulcer_index": ulcer,
                    "conditional_var_95": cvar,
                    "expected_shortfall": es,
                    "skewness": skew,
                    "kurtosis": kurt,
                    "tail_ratio": tail,
                    "recovery_factor": recovery,
                }
                
                logger.info(f"Advanced metrics calculated: Omega={omega:.2f}, Recovery={recovery:.2f}")
        except Exception as e:
            logger.debug(f"Advanced metrics calculation failed: {e}")
            results["advanced_metrics"] = {}
        
        return results
