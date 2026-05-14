"""
Phase 5: Performance Metrics Calculation

Standard metrics for strategy evaluation:
- Sharpe Ratio: Return per unit of volatility
- Sortino Ratio: Return per unit of downside volatility
- Calmar Ratio: Return per unit of max drawdown
- Profit Factor: Gross profit / gross loss
- Win Rate: Winning trades / total trades
- etc.
"""

from dataclasses import dataclass
from typing import List, Optional
import numpy as np
from scipy import stats

from loguru import logger


@dataclass
class PerformanceMetrics:
    """Complete performance metrics for a backtest."""
    
    # Returns
    total_return: float = 0.0          # Total return %
    annual_return: float = 0.0         # Annualized return
    
    # Volatility
    volatility: float = 0.0            # Return volatility
    annual_volatility: float = 0.0     # Annualized volatility
    
    # Risk metrics
    max_drawdown: float = 0.0          # Peak-to-trough drawdown
    sharpe_ratio: float = 0.0          # Return per vol
    sortino_ratio: float = 0.0         # Return per downside vol
    calmar_ratio: float = 0.0          # Return per max dd
    
    # Trade metrics
    total_trades: int = 0              # Number of trades
    winning_trades: int = 0            # Winning trades
    losing_trades: int = 0             # Losing trades
    win_rate: float = 0.0              # Win rate %
    profit_factor: float = 0.0         # Wins / losses
    avg_win: float = 0.0               # Average winning trade
    avg_loss: float = 0.0              # Average losing trade
    avg_trade_duration: float = 0.0    # Hours
    
    # Risk-adjusted
    recovery_factor: float = 0.0       # Total return / max dd
    risk_reward_ratio: float = 0.0     # Avg win / avg loss
    
    # Drawdown
    avg_drawdown: float = 0.0
    avg_drawdown_duration: float = 0.0 # Days
    
    # Additional
    skewness: float = 0.0              # Return distribution skew
    kurtosis: float = 0.0              # Return distribution tail weight
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "total_return": self.total_return,
            "annual_return": self.annual_return,
            "volatility": self.volatility,
            "annual_volatility": self.annual_volatility,
            "max_drawdown": self.max_drawdown,
            "sharpe_ratio": self.sharpe_ratio,
            "sortino_ratio": self.sortino_ratio,
            "calmar_ratio": self.calmar_ratio,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "avg_win": self.avg_win,
            "avg_loss": self.avg_loss,
            "avg_trade_duration": self.avg_trade_duration,
            "recovery_factor": self.recovery_factor,
            "risk_reward_ratio": self.risk_reward_ratio,
            "skewness": self.skewness,
            "kurtosis": self.kurtosis,
        }


class MetricsCalculator:
    """
    Calculate performance metrics from backtest results.
    """

    @staticmethod
    def calculate(
        equity_curve: List[float],
        trades: List[dict],
        dates: List,
        initial_capital: float = 100000.0,
        risk_free_rate: float = 0.02,   # 2% annual
        trading_days_per_year: int = 252,
    ) -> PerformanceMetrics:
        """
        Calculate all performance metrics.
        
        Args:
            equity_curve: Daily equity values
            trades: List of trade results (with pnl)
            dates: Corresponding dates
            initial_capital: Starting capital
            risk_free_rate: Risk-free rate for Sharpe/Sortino
            trading_days_per_year: Days per year for annualization
            
        Returns:
            PerformanceMetrics object
        """
        metrics = PerformanceMetrics()
        
        if not equity_curve or len(equity_curve) < 2:
            return metrics
        
        # Calculate returns
        equity_array = np.array(equity_curve)
        daily_returns = np.diff(equity_array) / equity_array[:-1]
        
        # Basic metrics
        metrics.total_return = (equity_curve[-1] - initial_capital) / initial_capital
        metrics.annual_return = (1 + metrics.total_return) ** (trading_days_per_year / len(daily_returns)) - 1 if len(daily_returns) > 0 else 0
        
        # Volatility
        metrics.volatility = np.std(daily_returns)
        metrics.annual_volatility = metrics.volatility * np.sqrt(trading_days_per_year)
        
        # Sharpe Ratio
        daily_rf_rate = (1 + risk_free_rate) ** (1 / trading_days_per_year) - 1
        sharpe_daily = (np.mean(daily_returns) - daily_rf_rate) / metrics.volatility if metrics.volatility > 0 else 0
        metrics.sharpe_ratio = sharpe_daily * np.sqrt(trading_days_per_year)
        
        # Sortino Ratio (downside volatility only)
        downside_returns = np.minimum(daily_returns, 0)
        downside_vol = np.std(downside_returns)
        sortino_daily = (np.mean(daily_returns) - daily_rf_rate) / downside_vol if downside_vol > 0 else 0
        metrics.sortino_ratio = sortino_daily * np.sqrt(trading_days_per_year)
        
        # Max Drawdown
        cummax = np.maximum.accumulate(equity_array)
        drawdowns = (equity_array - cummax) / cummax
        metrics.max_drawdown = np.min(drawdowns)
        
        # Calmar Ratio
        metrics.calmar_ratio = metrics.annual_return / abs(metrics.max_drawdown) if metrics.max_drawdown != 0 else 0
        
        # Trade metrics
        if trades:
            metrics.total_trades = len(trades)
            pnls = [t.get('pnl', 0) for t in trades]
            winning = [p for p in pnls if p > 0]
            losing = [p for p in pnls if p < 0]
            
            metrics.winning_trades = len(winning)
            metrics.losing_trades = len(losing)
            metrics.win_rate = metrics.winning_trades / metrics.total_trades if metrics.total_trades > 0 else 0
            
            metrics.avg_win = np.mean(winning) if winning else 0
            metrics.avg_loss = np.mean(losing) if losing else 0
            
            gross_profit = sum(winning)
            gross_loss = abs(sum(losing))
            metrics.profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
            
            metrics.risk_reward_ratio = abs(metrics.avg_win / metrics.avg_loss) if metrics.avg_loss != 0 else 0
            
            # Trade duration
            durations = [t.get('duration_hours', 0) for t in trades]
            metrics.avg_trade_duration = np.mean(durations) if durations else 0
        
        # Recovery Factor
        total_loss = abs(metrics.max_drawdown * initial_capital)
        metrics.recovery_factor = metrics.total_return / abs(metrics.max_drawdown) if metrics.max_drawdown != 0 else 0
        
        # Distribution metrics
        metrics.skewness = float(stats.skew(daily_returns)) if len(daily_returns) > 2 else 0
        metrics.kurtosis = float(stats.kurtosis(daily_returns)) if len(daily_returns) > 2 else 0
        
        return metrics

    @staticmethod
    def format_metrics(metrics: PerformanceMetrics) -> str:
        """Format metrics for display."""
        lines = [
            f"Total Return:          {metrics.total_return:>10.2%}",
            f"Annual Return:         {metrics.annual_return:>10.2%}",
            f"Volatility:            {metrics.annual_volatility:>10.2%}",
            f"Sharpe Ratio:          {metrics.sharpe_ratio:>10.2f}",
            f"Sortino Ratio:         {metrics.sortino_ratio:>10.2f}",
            f"Max Drawdown:          {metrics.max_drawdown:>10.2%}",
            f"Calmar Ratio:          {metrics.calmar_ratio:>10.2f}",
            f"Win Rate:              {metrics.win_rate:>10.2%}",
            f"Profit Factor:         {metrics.profit_factor:>10.2f}",
            f"Total Trades:          {metrics.total_trades:>10}",
        ]
        return "\n".join(lines)
