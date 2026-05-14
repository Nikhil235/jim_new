"""
Phase 5: Walk-Forward Analysis

Walk-forward analysis ensures out-of-sample validation by:
1. Training on historical data (in-sample)
2. Testing on future unseen data (out-of-sample)
3. Rolling window approach with non-overlapping test periods
4. Comparing in-sample vs out-of-sample performance

This prevents overfitting by testing on data the model never saw.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional, Tuple
import numpy as np

from loguru import logger


@dataclass
class WalkForwardPeriod:
    """Single walk-forward period."""
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime
    train_days: int
    test_days: int

    @property
    def train_period(self) -> Tuple[datetime, datetime]:
        return (self.train_start, self.train_end)

    @property
    def test_period(self) -> Tuple[datetime, datetime]:
        return (self.test_start, self.test_end)


@dataclass
class WalkForwardResult:
    """Results for single walk-forward period."""
    period: WalkForwardPeriod
    
    # In-sample metrics
    is_return: float = 0.0
    is_sharpe: float = 0.0
    is_max_dd: float = 0.0
    is_win_rate: float = 0.0
    
    # Out-of-sample metrics
    oos_return: float = 0.0
    oos_sharpe: float = 0.0
    oos_max_dd: float = 0.0
    oos_win_rate: float = 0.0
    
    # Degradation (IS - OOS)
    return_degradation: float = 0.0
    sharpe_degradation: float = 0.0
    dd_degradation: float = 0.0

    @property
    def overfitting_ratio(self) -> float:
        """Ratio of IS/OOS Sharpe (should be close to 1.0)."""
        if self.oos_sharpe <= 0:
            return float('inf')
        return self.is_sharpe / self.oos_sharpe

    def is_overfit(self, threshold: float = 1.5) -> bool:
        """Check if results indicate overfitting."""
        return self.overfitting_ratio > threshold


class WalkForwardAnalyzer:
    """
    Walk-forward analysis framework.
    
    Splits data into non-overlapping train/test periods and runs
    strategy on each period to validate out-of-sample performance.
    """

    def __init__(
        self,
        train_days: int = 1000,      # ~3 years
        test_days: int = 250,        # ~1 year
        step_days: int = 250,        # Non-overlapping test periods
    ):
        """
        Initialize walk-forward analyzer.
        
        Args:
            train_days: Training period length
            test_days: Testing period length
            step_days: Days to step forward (non-overlapping)
        """
        self.train_days = train_days
        self.test_days = test_days
        self.step_days = step_days
        
        logger.info(f"Walk-forward analyzer: {train_days}d train, {test_days}d test, {step_days}d steps")

    def generate_periods(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> List[WalkForwardPeriod]:
        """
        Generate walk-forward periods for date range.
        
        Returns:
            List of non-overlapping train/test periods
        """
        periods = []
        
        current_train_start = start_date
        
        while current_train_start + timedelta(days=self.train_days + self.test_days) <= end_date:
            # Calculate period boundaries
            train_start = current_train_start
            train_end = train_start + timedelta(days=self.train_days)
            test_start = train_end
            test_end = test_start + timedelta(days=self.test_days)
            
            if test_end > end_date:
                break
            
            period = WalkForwardPeriod(
                train_start=train_start,
                train_end=train_end,
                test_start=test_start,
                test_end=test_end,
                train_days=self.train_days,
                test_days=self.test_days,
            )
            
            periods.append(period)
            
            # Move forward by step_days
            current_train_start += timedelta(days=self.step_days)
        
        logger.info(f"Generated {len(periods)} walk-forward periods")
        return periods

    def run(
        self,
        periods: List[WalkForwardPeriod],
        strategy_fn: Callable,
        data_source,
    ) -> List[WalkForwardResult]:
        """
        Run walk-forward analysis.
        
        Args:
            periods: Walk-forward periods
            strategy_fn: Function(data_source, start, end) -> backtest_results
            data_source: Data provider (backtester, etc.)
            
        Returns:
            List of WalkForwardResult for each period
        """
        results = []
        
        for i, period in enumerate(periods):
            logger.info(f"Running WF period {i+1}/{len(periods)}: {period.train_start.date()} -> {period.test_end.date()}")
            
            # Run in-sample (training period)
            is_results = strategy_fn(data_source, period.train_start, period.train_end)
            
            # Run out-of-sample (testing period)
            oos_results = strategy_fn(data_source, period.test_start, period.test_end)
            
            # Create result
            wf_result = WalkForwardResult(
                period=period,
                is_return=is_results.get('total_return', 0),
                is_sharpe=is_results.get('sharpe_ratio', 0),
                is_max_dd=is_results.get('max_drawdown', 0),
                is_win_rate=is_results.get('win_rate', 0),
                oos_return=oos_results.get('total_return', 0),
                oos_sharpe=oos_results.get('sharpe_ratio', 0),
                oos_max_dd=oos_results.get('max_drawdown', 0),
                oos_win_rate=oos_results.get('win_rate', 0),
            )
            
            # Calculate degradation
            wf_result.return_degradation = wf_result.is_return - wf_result.oos_return
            wf_result.sharpe_degradation = wf_result.is_sharpe - wf_result.oos_sharpe
            wf_result.dd_degradation = wf_result.is_max_dd - wf_result.oos_max_dd
            
            results.append(wf_result)
        
        return results

    def summarize(self, results: List[WalkForwardResult]) -> Dict:
        """
        Summarize walk-forward results.
        
        Returns:
            Dictionary with aggregate metrics
        """
        if not results:
            return {}
        
        is_returns = [r.is_return for r in results]
        oos_returns = [r.oos_return for r in results]
        is_sharpes = [r.is_sharpe for r in results]
        oos_sharpes = [r.oos_sharpe for r in results]
        max_dds = [r.oos_max_dd for r in results]
        
        overfit_ratio = np.mean([r.overfitting_ratio for r in results if r.oos_sharpe > 0])
        
        return {
            "num_periods": len(results),
            "avg_is_return": np.mean(is_returns),
            "avg_oos_return": np.mean(oos_returns),
            "std_oos_return": np.std(oos_returns),
            "avg_is_sharpe": np.mean(is_sharpes),
            "avg_oos_sharpe": np.mean(oos_sharpes),
            "std_oos_sharpe": np.std(oos_sharpes),
            "avg_oos_max_dd": np.mean(max_dds),
            "avg_overfitting_ratio": overfit_ratio,
            "return_degradation": np.mean(is_returns) - np.mean(oos_returns),
            "sharpe_degradation": np.mean(is_sharpes) - np.mean(oos_sharpes),
            "num_overfit": sum(1 for r in results if r.is_overfit()),
        }
