"""
Phase 5: Tests for Validation Framework

Tests for:
- Walk-Forward Analysis
- Deflated Sharpe Ratio
- CPCV
- Metrics Calculation
- Report Generation
"""

import pytest
import numpy as np
from datetime import datetime, timedelta
import pytz

from src.backtesting.walk_forward import WalkForwardAnalyzer, WalkForwardResult
from src.backtesting.deflated_sharpe import DeflatedSharpeCalculator
from src.backtesting.metrics import MetricsCalculator, PerformanceMetrics
from src.backtesting.cpcv import CPCVAnalyzer
from src.backtesting.report_generator import BacktestReportGenerator


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_dates():
    """Generate sample dates."""
    start = datetime(2020, 1, 1, tzinfo=pytz.UTC)
    dates = [start + timedelta(days=i) for i in range(1000)]
    return dates


@pytest.fixture
def sample_returns():
    """Generate sample daily returns."""
    np.random.seed(42)
    # Slightly positive drift with volatility
    returns = np.random.normal(0.0005, 0.01, 1000)
    return returns.tolist()


@pytest.fixture
def sample_equity_curve():
    """Generate sample equity curve."""
    initial = 100000
    returns = np.random.normal(0.0005, 0.01, 500)
    equity = [initial]
    for ret in returns:
        equity.append(equity[-1] * (1 + ret))
    return equity


@pytest.fixture
def sample_trades():
    """Generate sample trade results."""
    trades = [
        {"pnl": 1000, "duration_hours": 2},
        {"pnl": 1500, "duration_hours": 4},
        {"pnl": -500, "duration_hours": 1},
        {"pnl": 2000, "duration_hours": 8},
        {"pnl": -800, "duration_hours": 3},
    ]
    return trades


# ============================================================================
# Walk-Forward Tests
# ============================================================================

class TestWalkForwardAnalyzer:
    """Test walk-forward analysis."""
    
    def test_generate_periods(self, sample_dates):
        """Generate walk-forward periods."""
        analyzer = WalkForwardAnalyzer(
            train_days=300,
            test_days=100,
            step_days=400,  # Non-overlapping steps
        )
        
        periods = analyzer.generate_periods(sample_dates[0], sample_dates[-1])
        
        assert len(periods) > 0
        assert all(p.train_days == 300 for p in periods)
        assert all(p.test_days == 100 for p in periods)
        
        # Check non-overlapping
        for i in range(len(periods) - 1):
            assert periods[i].test_end <= periods[i+1].train_start
    
    def test_period_boundaries(self, sample_dates):
        """Check period boundaries are correct."""
        analyzer = WalkForwardAnalyzer(train_days=300, test_days=100, step_days=100)
        periods = analyzer.generate_periods(sample_dates[0], sample_dates[-1])
        
        for period in periods:
            # Train end should be test start
            assert period.train_end == period.test_start
            # Test span should be test_days
            assert (period.test_end - period.test_start).days == period.test_days


# ============================================================================
# Metrics Tests
# ============================================================================

class TestMetricsCalculator:
    """Test performance metrics calculation."""
    
    def test_calculate_metrics(self, sample_equity_curve, sample_trades):
        """Calculate complete metrics set."""
        dates = [datetime(2020, 1, 1) + timedelta(days=i) for i in range(len(sample_equity_curve))]
        
        metrics = MetricsCalculator.calculate(
            equity_curve=sample_equity_curve,
            trades=sample_trades,
            dates=dates,
            initial_capital=100000.0,
        )
        
        assert isinstance(metrics, PerformanceMetrics)
        assert metrics.total_trades == len(sample_trades)
        assert metrics.winning_trades == 3  # 1000, 1500, 2000
        assert metrics.losing_trades == 2  # -500, -800
        assert metrics.win_rate == pytest.approx(0.6, abs=0.01)
    
    def test_sharpe_ratio(self, sample_equity_curve):
        """Calculate Sharpe ratio."""
        dates = [datetime(2020, 1, 1) + timedelta(days=i) for i in range(len(sample_equity_curve))]
        
        metrics = MetricsCalculator.calculate(
            equity_curve=sample_equity_curve,
            trades=[],
            dates=dates,
        )
        
        assert metrics.sharpe_ratio is not None
        assert isinstance(metrics.sharpe_ratio, float)
    
    def test_max_drawdown(self, sample_equity_curve):
        """Calculate max drawdown."""
        dates = [datetime(2020, 1, 1) + timedelta(days=i) for i in range(len(sample_equity_curve))]
        
        metrics = MetricsCalculator.calculate(
            equity_curve=sample_equity_curve,
            trades=[],
            dates=dates,
        )
        
        assert metrics.max_drawdown < 0  # Should be negative
        assert metrics.max_drawdown > -0.5  # Reasonable range


# ============================================================================
# Deflated Sharpe Tests
# ============================================================================

class TestDeflatedSharpeCalculator:
    """Test DSR calculation."""
    
    def test_calculate_dsr(self, sample_returns):
        """Calculate Deflated Sharpe Ratio."""
        sharpe = 1.5
        
        result = DeflatedSharpeCalculator.calculate(
            returns=sample_returns,
            sharpe_ratio=sharpe,
            num_strategies=100,
        )
        
        assert result.sharpe_ratio == sharpe
        assert result.deflated_sharpe_ratio < sharpe  # DSR should be lower
        assert 0 <= result.p_value <= 1
        assert result.strategy_count == 100
    
    def test_dsr_significant(self, sample_returns):
        """Test DSR significance."""
        # High Sharpe should be more likely to be significant (lower p-value)
        result_high = DeflatedSharpeCalculator.calculate(
            returns=sample_returns,
            sharpe_ratio=3.0,
            num_strategies=10,
        )
        
        # Low Sharpe should be less likely (higher p-value)
        result_low = DeflatedSharpeCalculator.calculate(
            returns=sample_returns,
            sharpe_ratio=0.5,
            num_strategies=10,
        )
        
        # High Sharpe should have lower DSR degradation
        assert result_high.deflated_sharpe_ratio > result_low.deflated_sharpe_ratio
    
    def test_bootstrap_dsr(self, sample_returns):
        """Test bootstrap DSR calculation."""
        result = DeflatedSharpeCalculator.bootstrap_test(
            returns=sample_returns,
            sharpe_ratio=1.5,
            num_strategies=10,
            bootstrap_samples=100,
        )
        
        assert result.sharpe_ratio == 1.5
        assert 0 <= result.p_value <= 1
        assert result.deflated_sharpe_ratio is not None


# ============================================================================
# CPCV Tests
# ============================================================================

class TestCPCVAnalyzer:
    """Test CPCV."""
    
    def test_generate_folds(self, sample_dates):
        """Generate CPCV folds."""
        analyzer = CPCVAnalyzer(embargo_pct=0.05, min_train_size=0.3)
        
        folds = analyzer.generate_folds(sample_dates, n_splits=5)
        
        assert len(folds) > 0
        
        # Check train/test don't overlap
        for fold in folds:
            assert len(np.intersect1d(fold.train_indices, fold.test_indices)) == 0
    
    def test_fold_embargo(self, sample_dates):
        """Check embargo is applied."""
        analyzer = CPCVAnalyzer(embargo_pct=0.05)
        
        folds = analyzer.generate_folds(sample_dates, n_splits=5)
        
        for fold in folds:
            # Test and embargo should not overlap
            if fold.embargo_indices is not None and len(fold.embargo_indices) > 0:
                assert len(np.intersect1d(fold.test_indices, fold.embargo_indices)) == 0


# ============================================================================
# Report Generation Tests
# ============================================================================

class TestBacktestReportGenerator:
    """Test report generation."""
    
    def test_generate_markdown_report(self, sample_equity_curve, sample_trades):
        """Generate markdown report."""
        metrics = PerformanceMetrics(
            total_return=0.25,
            annual_return=0.05,
            volatility=0.15,
            annual_volatility=0.18,
            sharpe_ratio=1.2,
            max_drawdown=-0.10,
            total_trades=100,
            winning_trades=60,
            win_rate=0.60,
            profit_factor=2.0,
        )
        
        backtest_results = {
            "initial_capital": 100000.0,
            "final_equity": 125000.0,
            "period_start": "2020-01-01",
            "period_end": "2020-12-31",
            "market_events": 252,
            "signals_generated": 100,
            "total_commission": 500,
            "total_slippage": 200,
        }
        
        report = BacktestReportGenerator.generate_markdown(
            strategy_name="TestStrategy",
            version="1.0",
            backtest_results=backtest_results,
            metrics=metrics,
        )
        
        assert "TestStrategy" in report
        assert "Executive Summary" in report
        assert "Performance Metrics" in report
        assert "Trade Statistics" in report


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
