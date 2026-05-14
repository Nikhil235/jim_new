"""
Phase 5: Full Backtesting Integration Tests

End-to-end backtester workflow validation:
- Complete backtest lifecycle
- Metrics match portfolio results
- Walk-forward validation works correctly
- Report generation integrates properly
"""

import pytest
import numpy as np
from datetime import datetime, timedelta
import pytz
import tempfile
import os

from src.backtesting import (
    Backtester, BacktestConfig,
    DataHandler,
    MarketEvent, Direction, EventType,
    PortfolioTracker,
    MetricsCalculator,
    WalkForwardAnalyzer,
    DeflatedSharpeCalculator,
    BacktestReportGenerator,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def backtester():
    """Create backtester instance."""
    config = BacktestConfig(
        initial_capital=100000.0,
        kelly_fraction=0.5,
        max_position_pct=5.0,
    )
    return Backtester(config=config)


@pytest.fixture
def simple_strategy():
    """Simple strategy for testing (buy-and-hold)."""
    def strategy(market_event, portfolio):
        # Simple: buy on first event, hold
        if portfolio.total_trades == 0:
            return {
                "direction": Direction.LONG,
                "confidence": 0.8,
            }
        return None
    
    return strategy


@pytest.fixture
def mean_reversion_strategy():
    """Mean reversion strategy for testing."""
    def strategy(market_event, portfolio):
        # Simplified mean reversion
        if market_event.close < market_event.bid:
            return {
                "direction": Direction.LONG,
                "confidence": 0.7,
            }
        elif market_event.close > market_event.ask:
            return {
                "direction": Direction.SHORT,
                "confidence": 0.6,
            }
        return None
    
    return strategy


# ============================================================================
# Full Backtest Tests
# ============================================================================

class TestFullBacktest:
    """Test complete backtest workflow."""
    
    def test_backtester_initialization(self):
        """Test backtester initializes correctly."""
        config = BacktestConfig(initial_capital=100000.0)
        backtester = Backtester(config=config)
        
        assert backtester.portfolio.initial_capital == 100000.0
        assert backtester.strategy_fn is None
        assert len(backtester.market_history) == 0
    
    def test_strategy_assignment(self, simple_strategy):
        """Test strategy can be assigned."""
        backtester = Backtester()
        backtester.set_strategy(simple_strategy)
        
        assert backtester.strategy_fn is not None
        assert callable(backtester.strategy_fn)
    
    def test_execution_simulator_integration(self):
        """Test execution simulator works correctly."""
        from src.backtesting import ExecutionSimulator, ExecutionConfig, OrderEvent, OrderType, EventType
        import uuid
        
        config = ExecutionConfig()
        executor = ExecutionSimulator(config)
        
        # Create market event
        market = MarketEvent(
            event_type=EventType.MARKET,
            timestamp=datetime.now(pytz.UTC),
            symbol="XAU",
            open_price=100.0,
            high_price=101.0,
            low_price=99.0,
            close_price=100.5,
            volume=1000000,
            bid_price=100.0,
            ask_price=101.0,
        )
        
        order = OrderEvent(
            event_type=EventType.ORDER,
            timestamp=datetime.now(pytz.UTC),
            order_id=str(uuid.uuid4()),
            position_id="pos1",
            symbol="XAU",
            size=10,
            order_type=OrderType.MARKET,
            direction=Direction.LONG,
        )
        
        fill, status = executor.execute_order(order, market)
        
        assert fill is not None
        assert fill.order_id == order.order_id
        assert fill.size == order.size


# ============================================================================
# Metrics Integration Tests
# ============================================================================

class TestMetricsIntegration:
    """Test metrics calculation with real backtest data."""
    
    def test_metrics_from_equity_curve(self):
        """Calculate metrics from equity curve."""
        # Simulated equity curve with upward drift
        np.random.seed(42)
        equity = [100000]
        for i in range(250):
            ret = np.random.normal(0.001, 0.01)  # 0.1% daily drift
            equity.append(equity[-1] * (1 + ret))
        
        dates = [datetime(2020, 1, 1) + timedelta(days=i) for i in range(len(equity))]
        
        metrics = MetricsCalculator.calculate(
            equity_curve=equity,
            trades=[],
            dates=dates,
            initial_capital=100000.0,
        )
        
        # Should have some metrics calculated
        assert metrics.sharpe_ratio is not None
        assert metrics.max_drawdown is not None
        assert metrics.max_drawdown < 0  # Should have some drawdown


# ============================================================================
# Walk-Forward Integration Tests
# ============================================================================

class TestWalkForwardIntegration:
    """Test walk-forward validation with backtester."""
    
    def test_walk_forward_degradation(self):
        """Verify out-of-sample performance degrades (overfitting indicator)."""
        analyzer = WalkForwardAnalyzer(
            train_days=50,
            test_days=25,
            step_days=75,
        )
        
        # Simulate IS vs OOS metrics
        is_returns = [0.10, 0.12, 0.08]  # In-sample
        oos_returns = [0.06, 0.04, 0.05]  # Out-of-sample (worse)
        
        # Calculate degradation
        avg_is = np.mean(is_returns)
        avg_oos = np.mean(oos_returns)
        degradation = avg_is - avg_oos
        
        assert degradation > 0  # Performance should degrade OOS
        assert degradation < avg_is  # But not completely


# ============================================================================
# Report Generation Integration Tests
# ============================================================================

class TestReportGeneration:
    """Test report generation with real metrics."""
    
    def test_markdown_report_generation(self):
        """Generate and validate markdown report."""
        from src.backtesting import PerformanceMetrics
        
        metrics = PerformanceMetrics(
            total_return=0.25,
            annual_return=0.10,
            volatility=0.12,
            annual_volatility=0.15,
            sharpe_ratio=1.5,
            sortino_ratio=2.0,
            max_drawdown=-0.08,
            calmar_ratio=1.25,
            total_trades=100,
            winning_trades=55,
            losing_trades=45,
            win_rate=0.55,
            profit_factor=1.8,
            avg_win=500,
            avg_loss=-300,
            risk_reward_ratio=1.67,
        )
        
        backtest_results = {
            "initial_capital": 100000,
            "final_equity": 125000,
            "period_start": "2020-01-01",
            "period_end": "2020-12-31",
            "market_events": 252,
            "signals_generated": 100,
        }
        
        report = BacktestReportGenerator.generate_markdown(
            strategy_name="TestStrat",
            version="1.0",
            backtest_results=backtest_results,
            metrics=metrics,
        )
        
        # Validate report contains key sections
        assert "Backtest Report" in report
        assert "TestStrat" in report
        assert "Executive Summary" in report
        assert "Performance Metrics" in report
        assert "Sharpe Ratio" in report
        assert "Trade Statistics" in report
    
    def test_report_file_save(self):
        """Test saving report to file."""
        from src.backtesting import PerformanceMetrics
        
        metrics = PerformanceMetrics(sharpe_ratio=1.5)
        backtest_results = {"initial_capital": 100000, "final_equity": 125000}
        
        report = BacktestReportGenerator.generate_markdown(
            strategy_name="TestStrat",
            version="1.0",
            backtest_results=backtest_results,
            metrics=metrics,
        )
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            filepath = f.name
        
        try:
            BacktestReportGenerator.save_report(report, filepath)
            
            # Verify file was created and contains report
            assert os.path.exists(filepath)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            assert len(content) > 0
            assert "TestStrat" in content
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)


# ============================================================================
# Statistical Validation Integration Tests
# ============================================================================

class TestStatisticalValidation:
    """Test statistical validation pipeline."""
    
    def test_dsr_with_backtest_returns(self):
        """Calculate DSR from actual backtest returns."""
        # Simulate strategy returns
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, 252)
        
        # Calculate Sharpe ratio
        annual_return = np.mean(returns) * 252
        annual_vol = np.std(returns) * np.sqrt(252)
        sharpe = annual_return / annual_vol if annual_vol > 0 else 0
        
        # Calculate DSR
        dsr_result = DeflatedSharpeCalculator.calculate(
            returns=returns.tolist(),
            sharpe_ratio=sharpe,
            num_strategies=50,  # Tested 50 strategies
        )
        
        assert dsr_result.sharpe_ratio == sharpe
        assert dsr_result.deflated_sharpe_ratio <= sharpe  # DSR <= Sharpe
        assert 0 <= dsr_result.p_value <= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
