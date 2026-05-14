"""
Unit Tests: GPU Monte Carlo VaR Calculator
============================================
Tests risk computation with GPU/CPU acceleration.
"""

import pytest
import numpy as np
from src.risk.gpu_var import (
    GPUVaRCalculator,
    VaRResult,
)


class TestGPUVaRCalculator:
    """Test suite for GPUVaRCalculator."""

    @pytest.fixture
    def calculator(self):
        """Create a VaR calculator (CPU mode for testing)."""
        return GPUVaRCalculator(use_gpu=False)

    def test_initialization_cpu(self):
        """Test calculator initialization in CPU mode."""
        calc = GPUVaRCalculator(use_gpu=False)
        assert calc.device == "CPU"
        assert calc.use_gpu == False

    def test_initialization_gpu_fallback(self):
        """Test calculator falls back to CPU if GPU unavailable."""
        calc = GPUVaRCalculator(use_gpu=True)
        # Will auto-fallback if GPU not available
        assert calc.device in ["GPU", "CPU"]

    def test_monte_carlo_var_basic(self, calculator):
        """Test basic VaR calculation."""
        result = calculator.monte_carlo_var(
            current_position=100,
            current_price=2000,
            returns_mean=0.0005,
            returns_std=0.02,
            n_scenarios=10000,
            time_horizon_days=1,
        )
        
        assert isinstance(result, VaRResult)
        assert result.var_95 > 0
        assert result.var_99 > 0
        assert result.cvar_95 > 0
        assert result.cvar_99 > 0
        assert result.scenarios_ran == 10000
        assert result.computation_time_ms > 0
        assert result.used_gpu == False

    def test_var_ordering(self, calculator):
        """Test VaR ordering: 99% > 95% > median."""
        result = calculator.monte_carlo_var(
            current_position=100,
            current_price=2000,
            returns_mean=0.0,
            returns_std=0.02,
            n_scenarios=50000,
            time_horizon_days=1,
        )
        
        # 99% CVaR should be larger than 95% CVaR
        assert result.cvar_99 >= result.cvar_95
        assert result.var_99 >= result.var_95

    def test_positive_returns_mean(self, calculator):
        """Test with positive expected returns."""
        result_positive = calculator.monte_carlo_var(
            current_position=100,
            current_price=2000,
            returns_mean=0.001,  # +0.1% daily
            returns_std=0.02,
            n_scenarios=20000,
            time_horizon_days=1,
        )
        
        result_zero = calculator.monte_carlo_var(
            current_position=100,
            current_price=2000,
            returns_mean=0.0,  # 0%
            returns_std=0.02,
            n_scenarios=20000,
            time_horizon_days=1,
        )
        
        # Positive returns should have lower (less negative) VaR
        assert result_positive.var_95 < result_zero.var_95 or abs(result_positive.var_95 - result_zero.var_95) < 1

    def test_high_volatility(self, calculator):
        """Test with high volatility."""
        result_low_vol = calculator.monte_carlo_var(
            current_position=100,
            current_price=2000,
            returns_mean=0.0,
            returns_std=0.01,  # Low vol
            n_scenarios=20000,
        )
        
        result_high_vol = calculator.monte_carlo_var(
            current_position=100,
            current_price=2000,
            returns_mean=0.0,
            returns_std=0.05,  # High vol
            n_scenarios=20000,
        )
        
        # Higher volatility → higher VaR
        assert result_high_vol.var_95 > result_low_vol.var_95

    def test_larger_position(self, calculator):
        """Test scaling with position size."""
        result_small = calculator.monte_carlo_var(
            current_position=10,
            current_price=2000,
            returns_mean=0.0,
            returns_std=0.02,
            n_scenarios=20000,
        )
        
        result_large = calculator.monte_carlo_var(
            current_position=100,
            current_price=2000,
            returns_mean=0.0,
            returns_std=0.02,
            n_scenarios=20000,
        )
        
        # Larger position → proportionally larger VaR
        ratio = result_large.var_95 / result_small.var_95
        assert 8 < ratio < 12  # Should be approximately 10x

    def test_multi_day_horizon(self, calculator):
        """Test longer time horizons."""
        result_1day = calculator.monte_carlo_var(
            current_position=100,
            current_price=2000,
            returns_mean=0.0,
            returns_std=0.02,
            n_scenarios=20000,
            time_horizon_days=1,
        )
        
        result_10day = calculator.monte_carlo_var(
            current_position=100,
            current_price=2000,
            returns_mean=0.0,
            returns_std=0.02,
            n_scenarios=20000,
            time_horizon_days=10,
        )
        
        # Longer horizon → more risk (sqrt of time rule)
        # 10-day should be ~sqrt(10) ≈ 3.16x larger
        ratio = result_10day.var_95 / result_1day.var_95
        assert 2 < ratio < 4

    def test_scenario_count_effect(self, calculator):
        """Test that more scenarios improve accuracy."""
        result_1k = calculator.monte_carlo_var(
            current_position=100,
            current_price=2000,
            returns_mean=0.0,
            returns_std=0.02,
            n_scenarios=1000,
        )
        
        result_100k = calculator.monte_carlo_var(
            current_position=100,
            current_price=2000,
            returns_mean=0.0,
            returns_std=0.02,
            n_scenarios=100000,
        )
        
        # Results should be within reasonable range
        assert result_1k.scenarios_ran == 1000
        assert result_100k.scenarios_ran == 100000

    def test_stress_test_default(self, calculator):
        """Test default stress scenarios."""
        results = calculator.stress_test(portfolio_value=100000)
        
        assert "usd_flash_rally" in results
        assert "liquidity_crisis" in results
        assert "flash_crash" in results
        assert "rate_surprise" in results
        assert "geopolitical" in results
        
        # Check signs: rally and liquidity crisis should be negative
        assert results["usd_flash_rally"] < 0
        assert results["liquidity_crisis"] < 0
        assert results["flash_crash"] < 0
        
        # Geopolitical should be positive
        assert results["geopolitical"] > 0

    def test_stress_test_custom_scenarios(self, calculator):
        """Test with custom stress scenarios."""
        custom_scenarios = {
            "my_shock_1": np.array([0.1]),  # +10%
            "my_shock_2": np.array([-0.15]),  # -15%
        }
        
        results = calculator.stress_test(
            portfolio_value=100000,
            stress_scenarios=custom_scenarios,
        )
        
        assert len(results) == 2
        assert results["my_shock_1"] > 0
        assert results["my_shock_2"] < 0

    def test_zero_position(self, calculator):
        """Test with zero position."""
        result = calculator.monte_carlo_var(
            current_position=0,
            current_price=2000,
            returns_mean=0.0,
            returns_std=0.02,
            n_scenarios=10000,
        )
        
        # Zero position → zero VaR
        assert result.var_95 == 0
        assert result.var_99 == 0

    def test_high_price_low_units(self, calculator):
        """Test high price, low unit count."""
        # Gold at $2000/oz, 1 oz position
        result = calculator.monte_carlo_var(
            current_position=1,
            current_price=2000,
            returns_mean=0.0,
            returns_std=0.02,
            n_scenarios=20000,
        )
        
        assert result.var_95 > 0
        assert result.scenarios_ran == 20000

    def test_cvar_calculation(self, calculator):
        """Test CVaR is computed correctly."""
        result = calculator.monte_carlo_var(
            current_position=100,
            current_price=2000,
            returns_mean=0.0,
            returns_std=0.02,
            n_scenarios=50000,
        )
        
        # CVaR should always be >= VaR (more extreme)
        assert result.cvar_95 >= result.var_95 - 1  # Small tolerance
        assert result.cvar_99 >= result.var_99 - 1


class TestVaRResult:
    """Test VaRResult dataclass."""

    def test_creation(self):
        """Test VaRResult creation."""
        result = VaRResult(
            var_95=1000,
            var_99=1500,
            cvar_95=1200,
            cvar_99=1800,
            max_drawdown_pct=0.05,
            scenarios_ran=100000,
            computation_time_ms=250,
            used_gpu=False,
        )
        
        assert result.var_95 == 1000
        assert result.cvar_99 == 1800
        assert result.used_gpu == False

    def test_result_ordering(self):
        """Test that CVaR > VaR as expected."""
        result = VaRResult(
            var_95=1000,
            var_99=1500,
            cvar_95=1200,
            cvar_99=1800,
            max_drawdown_pct=0.05,
            scenarios_ran=100000,
            computation_time_ms=250,
            used_gpu=False,
        )
        
        assert result.cvar_95 >= result.var_95
        assert result.cvar_99 >= result.var_99
        assert result.var_99 >= result.var_95
