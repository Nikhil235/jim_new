"""
Risk Management for Paper Trading
==================================
Enforces trading limits, circuit breakers, and position constraints.

Controls:
- Maximum position size (% of capital)
- Maximum leverage ratio
- Daily loss limits (circuit breaker)
- Model concentration limits
- Consecutive loss limits
- Sector exposure limits
"""

from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from dataclasses import dataclass
from loguru import logger

from src.paper_trading.engine import TradeExecution, TradeStatus


@dataclass
class RiskLimits:
    """Risk management constraints."""
    max_position_pct: float = 0.10          # Max position as % of capital
    max_leverage: float = 1.0               # Maximum leverage ratio
    max_daily_loss_pct: float = 0.02        # Max daily loss as % of capital
    max_drawdown_pct: float = 0.15          # Max drawdown from peak
    max_model_concentration: float = 0.50   # Max concentration in one model
    max_consecutive_losses: int = 3         # Max consecutive losing trades
    max_trades_per_day: int = 10            # Max trades per day


class RiskManager:
    """
    Risk management system for paper trading.
    
    Tracks:
    - Current positions and exposures
    - Daily P&L and loss limits
    - Model concentration
    - Drawdown from peak
    - Consecutive losses
    """
    
    def __init__(self, initial_capital: float, limits: RiskLimits = None):
        """Initialize risk manager."""
        self.initial_capital = initial_capital
        self.limits = limits or RiskLimits()
        
        # State tracking
        self.peak_equity = initial_capital
        self.daily_start_equity = initial_capital
        self.day_started_at = datetime.now()
        
        # Trade tracking
        self.open_positions: Dict[str, TradeExecution] = {}
        self.daily_trades: List[TradeExecution] = []
        self.consecutive_losses = 0
        
        # Model tracking
        self.model_exposure: Dict[str, float] = {}  # model_name -> total exposure %
        
        logger.info(f"Risk Manager initialized with limits: {self.limits}")
    
    def check_can_trade(self, model_name: str, position_value: float, current_equity: float) -> Tuple[bool, str]:
        """
        Check if a trade is allowed based on risk constraints.
        
        Args:
            model_name: Model generating the signal
            position_value: Value of the position to open
            current_equity: Current portfolio equity
            
        Returns:
            (can_trade, reason) tuple
        """
        reasons = []
        
        # Check daily loss limit
        daily_loss = current_equity - self.daily_start_equity
        if daily_loss < -self.initial_capital * self.limits.max_daily_loss_pct:
            reasons.append(f"Daily loss limit exceeded: ${daily_loss:.2f}")
        
        # Check maximum drawdown
        drawdown = (current_equity - self.peak_equity) / self.peak_equity
        if drawdown < -self.limits.max_drawdown_pct:
            reasons.append(f"Drawdown limit exceeded: {drawdown*100:.2f}%")
        
        # Check position size
        position_pct = position_value / current_equity if current_equity > 0 else 0
        if position_pct > self.limits.max_position_pct:
            reasons.append(f"Position too large: {position_pct*100:.2f}% > {self.limits.max_position_pct*100:.2f}%")
        
        # Check trades per day
        if len(self.daily_trades) >= self.limits.max_trades_per_day:
            reasons.append(f"Max trades per day exceeded: {len(self.daily_trades)} >= {self.limits.max_trades_per_day}")
        
        # Check model concentration
        model_exposure = self.model_exposure.get(model_name, 0.0) + position_pct
        if model_exposure > self.limits.max_model_concentration:
            reasons.append(f"{model_name} concentration too high: {model_exposure*100:.2f}%")
        
        # Check consecutive losses
        if self.consecutive_losses >= self.limits.max_consecutive_losses:
            reasons.append(f"Max consecutive losses reached: {self.consecutive_losses}")
        
        can_trade = len(reasons) == 0
        reason = " | ".join(reasons) if reasons else "OK"
        
        return can_trade, reason
    
    def record_trade(self, trade: TradeExecution, current_equity: float):
        """
        Record a new trade.
        
        Args:
            trade: TradeExecution to record
            current_equity: Current portfolio equity
        """
        if trade.status == TradeStatus.OPEN:
            self.open_positions[trade.trade_id] = trade
            self.daily_trades.append(trade)
            
            # Update model exposure
            exposure_pct = trade.position_value / current_equity if current_equity > 0 else 0
            self.model_exposure[trade.model_name] = self.model_exposure.get(trade.model_name, 0) + exposure_pct
            
            logger.debug(f"Trade recorded: {trade.trade_id} ({trade.model_name})")
    
    def close_trade(self, trade: TradeExecution, current_equity: float):
        """
        Record a closed trade and update consecutive loss tracking.
        
        Args:
            trade: TradeExecution to close
            current_equity: Current portfolio equity
        """
        if trade.trade_id in self.open_positions:
            del self.open_positions[trade.trade_id]
        
        # Update consecutive losses
        if trade.pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0
        
        # Update peak equity
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
            self.consecutive_losses = 0  # Reset consecutive losses on new high
        
        logger.debug(f"Trade closed: {trade.trade_id} | P&L: ${trade.pnl:.2f}")
    
    def update_daily_state(self, current_equity: float):
        """
        Update daily state (call at market open each day).
        
        Args:
            current_equity: Current portfolio equity
        """
        self.daily_start_equity = current_equity
        self.daily_trades = []
        self.model_exposure = {}
        self.day_started_at = datetime.now()
        
        logger.info(f"Daily state updated: equity=${current_equity:.2f}, peak=${self.peak_equity:.2f}")
    
    def get_current_risk(self) -> Dict:
        """Get current risk metrics."""
        return {
            "open_positions": len(self.open_positions),
            "daily_trades": len(self.daily_trades),
            "consecutive_losses": self.consecutive_losses,
            "model_exposure": self.model_exposure,
            "peak_equity": self.peak_equity,
        }
    
    def get_risk_report(self, current_equity: float, daily_pnl: float) -> Dict:
        """Generate comprehensive risk report."""
        drawdown = (current_equity - self.peak_equity) / self.peak_equity
        daily_loss_pct = daily_pnl / self.daily_start_equity if self.daily_start_equity > 0 else 0
        
        return {
            "current_equity": current_equity,
            "peak_equity": self.peak_equity,
            "drawdown_pct": drawdown * 100,
            "daily_pnl": daily_pnl,
            "daily_loss_pct": daily_loss_pct * 100,
            "open_positions": len(self.open_positions),
            "daily_trades": len(self.daily_trades),
            "consecutive_losses": self.consecutive_losses,
            "model_concentration": self.model_exposure,
            "risk_limits": {
                "max_position_pct": self.limits.max_position_pct * 100,
                "max_daily_loss_pct": self.limits.max_daily_loss_pct * 100,
                "max_drawdown_pct": self.limits.max_drawdown_pct * 100,
                "max_consecutive_losses": self.limits.max_consecutive_losses,
            },
            "violations": self._check_violations(current_equity, daily_pnl),
        }
    
    def _check_violations(self, current_equity: float, daily_pnl: float) -> List[str]:
        """Check for any risk limit violations."""
        violations = []
        
        drawdown = (current_equity - self.peak_equity) / self.peak_equity
        if drawdown < -self.limits.max_drawdown_pct:
            violations.append(f"Drawdown violation: {drawdown*100:.2f}%")
        
        daily_loss_pct = daily_pnl / self.daily_start_equity
        if daily_loss_pct < -self.limits.max_daily_loss_pct:
            violations.append(f"Daily loss violation: {daily_loss_pct*100:.2f}%")
        
        if self.consecutive_losses >= self.limits.max_consecutive_losses:
            violations.append(f"Consecutive losses: {self.consecutive_losses}")
        
        return violations
