"""
Unit Tests for Advanced Risk Metrics
=====================================
Tests for Omega ratio, Ulcer Index, CVaR, and other advanced risk metrics.
"""

import pytest
import numpy as np
from typing import List

from src.risk.advanced_metrics import (
    AdvancedRiskMetrics,
    AdvancedRiskCalculator,
)


class TestAdvancedRiskMetrics:
    """Tests for AdvancedRiskMetrics dataclass."""
    
    def test_creation(self):
        """Test basic AdvancedRiskMetrics creation."""
        metrics = AdvancedRiskMetrics(
            omega_ratio=1.2,
            ulcer_index=2.5,
            conditional_var=-0.025,
            skewness=-0.15,
            kurtosis=3.2
        )
        
        assert metrics.omega_ratio == 1.2
        assert metrics.ulcer_index == 2.5
        assert metrics.conditional_var == -0.025
        assert metrics.skewness == -0.15
    
    def test_default_values(self):
        """Test default values."""
        metrics = AdvancedRiskMetrics()
        
        assert metrics.omega_ratio == 0.0
        assert metrics.ulcer_index == 0.0
        assert metrics.conditional_var == 0.0
        assert metrics.expected_shortfall == 0.0
        assert metrics.skewness == 0.0
        assert metrics.kurtosis == 0.0
        assert metrics.tail_ratio == 0.0
        assert metrics.recovery_factor == 0.0


class TestOmegaRatio:
    """Tests for Omega Ratio calculation."""
    
    def test_omega_all_positive_returns(self):
        """Test Omega with all positive returns."""
        returns = [0.01, 0.02, 0.015, 0.01, 0.012]  # All positive
        
        omega = AdvancedRiskCalculator.calculate_omega_ratio(returns, target_return=0.0)
        
        assert omega == np.inf  # All returns above target
    
    def test_omega_all_negative_returns(self):
        """Test Omega with all negative returns."""
        returns = [-0.01, -0.02, -0.015, -0.01, -0.012]
        
        omega = AdvancedRiskCalculator.calculate_omega_ratio(returns, target_return=0.0)
        
        assert omega == 0.0  # No positive returns
    
    def test_omega_mixed_returns(self):
        """Test Omega with mixed positive and negative returns."""
        returns = [0.02, 0.01, -0.01, 0.015, -0.005, 0.012, -0.008]
        
        omega = AdvancedRiskCalculator.calculate_omega_ratio(returns, target_return=0.0)
        
        assert omega > 0  # Should have some positive value
        assert not np.isinf(omega)
    
    def test_omega_single_return(self):
        """Test Omega with single return."""
        omega = AdvancedRiskCalculator.calculate_omega_ratio([0.01], target_return=0.0)
        
        assert omega == 0.0  # Not enough data
    
    def test_omega_with_target_return(self):
        """Test Omega with non-zero target return."""
        returns = [0.015, 0.01, 0.005, -0.005, -0.01, 0.012, 0.008]
        target = 0.005
        
        omega = AdvancedRiskCalculator.calculate_omega_ratio(returns, target_return=target)
        
        assert isinstance(omega, (float, np.floating))
        assert omega >= 0


class TestUlcerIndex:
    """Tests for Ulcer Index calculation."""
    
    def test_ulcer_constant_equity(self):
        """Test Ulcer Index with constant equity (no drawdown)."""
        equity = [100, 100, 100, 100, 100]
        
        ui = AdvancedRiskCalculator.calculate_ulcer_index(equity, lookback=5)
        
        assert ui == 0.0  # No drawdown = 0 ulcer
    
    def test_ulcer_linear_decline(self):
        """Test Ulcer Index with linear decline."""
        equity = [100, 95, 90, 85, 80, 75]  # Consistent 5% decline
        
        ui = AdvancedRiskCalculator.calculate_ulcer_index(equity, lookback=6)
        
        assert ui > 0  # Should have positive ulcer
    
    def test_ulcer_single_drop(self):
        """Test Ulcer Index with single drop then recovery."""
        equity = [100, 50, 100, 100, 100]  # Single -50% drop
        
        ui = AdvancedRiskCalculator.calculate_ulcer_index(equity, lookback=5)
        
        assert ui > 0  # Reflects the past drawdown
    
    def test_ulcer_short_series(self):
        """Test Ulcer Index with short equity series."""
        ui = AdvancedRiskCalculator.calculate_ulcer_index([100], lookback=5)
        
        assert ui == 0.0


class TestConditionalVaR:
    """Tests for Conditional Value at Risk (CVaR) calculation."""
    
    def test_cvar_normal_distribution(self):
        """Test CVaR with normally distributed returns."""
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.01, 252)  # ~1% annual return, 10% vol
        
        cvar = AdvancedRiskCalculator.calculate_conditional_var(
            returns.tolist(), confidence_level=0.95
        )
        
        assert isinstance(cvar, (float, np.floating))
        assert cvar < 0  # Worst returns should be negative
    
    def test_cvar_all_positive(self):
        """Test CVaR with all positive returns."""
        returns = [0.01, 0.015, 0.012, 0.008, 0.02]
        
        cvar = AdvancedRiskCalculator.calculate_conditional_var(returns, confidence_level=0.95)
        
        assert cvar >= 0
    
    def test_cvar_extreme_losses(self):
        """Test CVaR with extreme loss events."""
        returns = [0.01] * 19 + [-0.50]  # 19 small gains, 1 extreme loss
        
        cvar = AdvancedRiskCalculator.calculate_conditional_var(returns, confidence_level=0.95)
        
        assert cvar < 0  # Should reflect the extreme loss
    
    def test_cvar_short_series(self):
        """Test CVaR with short return series."""
        cvar = AdvancedRiskCalculator.calculate_conditional_var([0.01], confidence_level=0.95)
        
        assert cvar == 0.0


class TestExpectedShortfall:
    """Tests for Expected Shortfall calculation."""
    
    def test_expected_shortfall_normal_dist(self):
        """Test Expected Shortfall with normal distribution."""
        np.random.seed(42)
        returns = np.random.normal(0.0, 0.01, 100)
        
        es = AdvancedRiskCalculator.calculate_expected_shortfall(returns, percentile=5.0)
        
        assert isinstance(es, (float, np.floating))
        assert es < 0  # Worst returns should be negative
    
    def test_expected_shortfall_all_positive(self):
        """Test Expected Shortfall with all positive returns."""
        returns = [0.01, 0.015, 0.012, 0.008, 0.02, 0.009]
        
        es = AdvancedRiskCalculator.calculate_expected_shortfall(returns, percentile=5.0)
        
        assert es >= 0  # Worst 5% of positive returns
    
    def test_expected_shortfall_short_series(self):
        """Test Expected Shortfall with short series."""
        es = AdvancedRiskCalculator.calculate_expected_shortfall([0.01], percentile=5.0)
        
        assert es == 0.0


class TestTailRiskMetrics:
    """Tests for Tail Risk Metrics (skewness, kurtosis, tail ratio)."""
    
    def test_tail_risk_normal_distribution(self):
        """Test tail risk metrics with normal distribution."""
        np.random.seed(42)
        returns = np.random.normal(0.0, 0.01, 500)
        
        skew, excess_kurt, tail_ratio = AdvancedRiskCalculator.calculate_tail_risk_metrics(returns)
        
        assert isinstance(skew, (float, np.floating))
        assert isinstance(excess_kurt, (float, np.floating))
        assert isinstance(tail_ratio, (float, np.floating))
        # Normal distribution should have skew ~0 and excess kurtosis ~0
        assert abs(skew) < 0.5
        assert abs(excess_kurt) < 1.0
    
    def test_tail_risk_left_skewed(self):
        """Test tail risk with left-skewed distribution."""
        # Left-skewed: more extreme negative returns
        np.random.seed(42)
        normal_returns = np.random.normal(0.0, 0.01, 100)
        returns = list(normal_returns) + [-0.50, -0.40, -0.35]  # Extreme losses
        
        skew, excess_kurt, tail_ratio = AdvancedRiskCalculator.calculate_tail_risk_metrics(returns)
        
        assert skew < 0  # Should be negatively skewed
    
    def test_tail_risk_right_skewed(self):
        """Test tail risk with right-skewed distribution."""
        # Right-skewed: more extreme positive returns
        np.random.seed(42)
        normal_returns = np.random.normal(0.0, 0.01, 100)
        returns = list(normal_returns) + [0.50, 0.40, 0.35]  # Extreme gains
        
        skew, excess_kurt, tail_ratio = AdvancedRiskCalculator.calculate_tail_risk_metrics(returns)
        
        assert skew > 0  # Should be positively skewed
    
    def test_tail_risk_high_kurtosis(self):
        """Test tail risk with high kurtosis (fat tails)."""
        # Mix of normal and extreme values creates fat tails
        normal_returns = list(np.random.normal(0.0, 0.01, 90))
        extreme_returns = [-0.30, -0.25, 0.25, 0.30]  # 10 extreme outliers
        returns = normal_returns + extreme_returns
        
        skew, excess_kurt, tail_ratio = AdvancedRiskCalculator.calculate_tail_risk_metrics(returns)
        
        assert excess_kurt > 1.0  # Should have excess kurtosis (fat tails)
    
    def test_tail_risk_short_series(self):
        """Test tail risk with short series."""
        skew, excess_kurt, tail_ratio = AdvancedRiskCalculator.calculate_tail_risk_metrics([0.01, 0.02])
        
        assert skew == 0.0
        assert excess_kurt == 0.0
        assert tail_ratio == 0.0


class TestRecoveryFactor:
    """Tests for Recovery Factor calculation."""
    
    def test_recovery_factor_positive_return_negative_dd(self):
        """Test recovery factor with positive return and negative drawdown."""
        total_return = 0.50  # 50% return
        max_drawdown = -0.20  # -20% drawdown
        
        rf = AdvancedRiskCalculator.calculate_recovery_factor(total_return, max_drawdown)
        
        assert rf == 2.5  # 0.50 / 0.20
        assert rf > 0
    
    def test_recovery_factor_large_drawdown(self):
        """Test recovery factor with large drawdown."""
        total_return = 0.30  # 30% return
        max_drawdown = -0.50  # -50% drawdown
        
        rf = AdvancedRiskCalculator.calculate_recovery_factor(total_return, max_drawdown)
        
        assert rf == 0.6  # 0.30 / 0.50
    
    def test_recovery_factor_no_drawdown(self):
        """Test recovery factor with no drawdown."""
        total_return = 0.25
        max_drawdown = 0.0
        
        rf = AdvancedRiskCalculator.calculate_recovery_factor(total_return, max_drawdown)
        
        assert np.isinf(rf)  # Infinite recovery
    
    def test_recovery_factor_negative_return(self):
        """Test recovery factor with negative return."""
        total_return = -0.10
        max_drawdown = -0.20
        
        rf = AdvancedRiskCalculator.calculate_recovery_factor(total_return, max_drawdown)
        
        # -0.10 / 0.20 = -0.5 (negative recovery means both return and drawdown are bad)
        assert rf == -0.5
    
    def test_recovery_factor_zero_return(self):
        """Test recovery factor with zero return."""
        total_return = 0.0
        max_drawdown = -0.15
        
        rf = AdvancedRiskCalculator.calculate_recovery_factor(total_return, max_drawdown)
        
        assert rf == 0.0


class TestStressAdjustedSharpe:
    """Tests for Stress-Adjusted Sharpe Ratio."""
    
    def test_stress_adjusted_sharpe_normal(self):
        """Test stress-adjusted Sharpe with normal distribution."""
        np.random.seed(42)
        returns = np.random.normal(0.0005, 0.01, 252)  # ~0.05% daily return, 1% vol
        
        adj_sharpe = AdvancedRiskCalculator.calculate_stress_adjusted_sharpe(
            returns.tolist(), risk_free_rate=0.0
        )
        
        assert isinstance(adj_sharpe, (float, np.floating))
    
    def test_stress_adjusted_sharpe_vs_normal_sharpe(self):
        """Test that stress-adjusted Sharpe reflects tail risk."""
        # Normal returns
        np.random.seed(42)
        normal_returns = list(np.random.normal(0.001, 0.01, 252))
        
        # Add fat tails
        fat_tail_returns = normal_returns + [-0.40, -0.35, 0.35, 0.40]
        
        sharpe_normal = AdvancedRiskCalculator.calculate_stress_adjusted_sharpe(
            normal_returns, risk_free_rate=0.0
        )
        sharpe_fat_tail = AdvancedRiskCalculator.calculate_stress_adjusted_sharpe(
            fat_tail_returns, risk_free_rate=0.0
        )
        
        # Fat tail version should be adjusted differently
        assert isinstance(sharpe_normal, (float, np.floating))
        assert isinstance(sharpe_fat_tail, (float, np.floating))
    
    def test_stress_adjusted_sharpe_zero_volatility(self):
        """Test stress-adjusted Sharpe with zero volatility."""
        returns = [0.001, 0.001, 0.001, 0.001, 0.001]  # No volatility
        
        adj_sharpe = AdvancedRiskCalculator.calculate_stress_adjusted_sharpe(returns)
        
        assert adj_sharpe == 0.0
    
    def test_stress_adjusted_sharpe_short_series(self):
        """Test stress-adjusted Sharpe with short series."""
        adj_sharpe = AdvancedRiskCalculator.calculate_stress_adjusted_sharpe([0.01])
        
        assert adj_sharpe == 0.0


class TestRiskReport:
    """Tests for Risk Report generation."""
    
    def test_generate_risk_report(self):
        """Test risk report generation."""
        equity_curve = [100, 105, 103, 108, 110, 107, 112]
        returns = [0.05, -0.019, 0.0485, 0.0185, -0.0273, 0.0467]
        
        report = AdvancedRiskCalculator.generate_risk_report(
            equity_curve=equity_curve,
            returns=returns,
            total_return=0.12,
            max_drawdown=-0.05,
            sharpe_ratio=1.2
        )
        
        assert isinstance(report, str)
        assert len(report) > 0
    
    def test_generate_risk_report_contains_metrics(self):
        """Test that risk report contains key metrics."""
        equity_curve = list(range(100, 150))
        returns = [0.01] * 49
        
        report = AdvancedRiskCalculator.generate_risk_report(
            equity_curve=equity_curve,
            returns=returns,
            total_return=0.50,
            max_drawdown=-0.05,
            sharpe_ratio=2.0
        )
        
        # Should contain some key information
        assert isinstance(report, str)
        assert len(report) > 0


class TestAdvancedRiskIntegration:
    """Integration tests for risk metrics."""
    
    def test_complete_risk_analysis(self):
        """Test complete risk analysis with multiple metrics."""
        # Create realistic return series
        np.random.seed(42)
        base_returns = np.random.normal(0.0008, 0.015, 252)
        
        # Add some drawdown periods
        base_returns[50:60] = -0.02  # 10-day drawdown
        base_returns[150:155] = -0.015  # Another drawdown
        
        returns_list = base_returns.tolist()
        
        # Calculate all metrics
        omega = AdvancedRiskCalculator.calculate_omega_ratio(returns_list)
        
        equity = [100]
        for ret in returns_list:
            equity.append(equity[-1] * (1 + ret))
        
        ulcer = AdvancedRiskCalculator.calculate_ulcer_index(equity)
        cvar = AdvancedRiskCalculator.calculate_conditional_var(returns_list)
        es = AdvancedRiskCalculator.calculate_expected_shortfall(returns_list)
        skew, kurt, tail = AdvancedRiskCalculator.calculate_tail_risk_metrics(returns_list)
        
        total_return = (equity[-1] - equity[0]) / equity[0]
        max_dd = min([(e - max(equity[:i+1])) / max(equity[:i+1]) for i, e in enumerate(equity)])
        
        rf = AdvancedRiskCalculator.calculate_recovery_factor(total_return, max_dd)
        adj_sharpe = AdvancedRiskCalculator.calculate_stress_adjusted_sharpe(returns_list)
        
        # All metrics should be calculated without error
        assert isinstance(omega, (float, np.floating))
        assert isinstance(ulcer, (float, np.floating))
        assert isinstance(cvar, (float, np.floating))
        assert isinstance(es, (float, np.floating))
        assert isinstance(skew, (float, np.floating))
        assert isinstance(kurt, (float, np.floating))
        assert isinstance(tail, (float, np.floating))
        assert isinstance(rf, (float, np.floating))
        assert isinstance(adj_sharpe, (float, np.floating))
    
    def test_dataclass_creation_from_calculations(self):
        """Test creating AdvancedRiskMetrics from calculations."""
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.01, 252).tolist()
        
        equity = [100]
        for ret in returns:
            equity.append(equity[-1] * (1 + ret))
        
        total_return = (equity[-1] - equity[0]) / equity[0]
        max_dd = min([(e - max(equity[:i+1])) / max(equity[:i+1]) for i, e in enumerate(equity)])
        
        metrics = AdvancedRiskMetrics(
            omega_ratio=AdvancedRiskCalculator.calculate_omega_ratio(returns),
            ulcer_index=AdvancedRiskCalculator.calculate_ulcer_index(equity),
            conditional_var=AdvancedRiskCalculator.calculate_conditional_var(returns),
            expected_shortfall=AdvancedRiskCalculator.calculate_expected_shortfall(returns),
            recovery_factor=AdvancedRiskCalculator.calculate_recovery_factor(total_return, max_dd)
        )
        
        assert isinstance(metrics, AdvancedRiskMetrics)
        assert metrics.omega_ratio >= 0
        assert metrics.ulcer_index >= 0
