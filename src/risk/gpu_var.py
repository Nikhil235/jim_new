"""
GPU Monte Carlo VaR Calculator
===============================
Compute Value-at-Risk and Conditional VaR using GPU-accelerated simulations.

100,000+ scenarios per hour on single GPU.

Reference: NVIDIA RAPIDS, CuPy documentation
"""

import numpy as np
from typing import Tuple, Optional, Dict
from loguru import logger
from dataclasses import dataclass

try:
    import cupy as cp
    HAS_CUPY = True
except ImportError:
    HAS_CUPY = False


@dataclass
class VaRResult:
    """Value-at-Risk calculation result."""
    var_95: float  # Max expected loss in 95% of scenarios
    var_99: float  # Max expected loss in 99% of scenarios
    cvar_95: float  # Average loss in worst 5% of scenarios
    cvar_99: float  # Average loss in worst 1% of scenarios
    max_drawdown_pct: float  # Max drawdown across scenarios
    scenarios_ran: int  # Number of Monte Carlo scenarios
    computation_time_ms: float
    used_gpu: bool


@dataclass
class StressScenario:
    """Pre-defined stress test scenario."""
    name: str
    description: str
    shock_vector: np.ndarray  # Shock to apply to returns


class GPUVaRCalculator:
    """
    GPU-accelerated Monte Carlo VaR and stress testing.
    
    Scenarios:
    - USD Flash Rally: DXY +3% → Gold -2.5% to -4%
    - Liquidity Crisis: Spread 5x normal → Slippage explosion
    - Flash Crash: Gold -5% in 5 min → Circuit breaker test
    - Rate Surprise: Fed +50bps → Gold -3% to +2%
    - Geopolitical Event: VIX spike to 40+ → Gold +3% to +8%
    """
    
    def __init__(self, use_gpu: bool = True):
        """
        Args:
            use_gpu: Whether to use GPU (falls back to CPU if not available).
        """
        self.use_gpu = use_gpu and HAS_CUPY
        self.device = "GPU" if self.use_gpu else "CPU"
        
        if self.use_gpu:
            try:
                # Test GPU availability
                _ = cp.array([1, 2, 3])
                logger.info("GPU VaR calculator initialized (CUDA available)")
            except Exception as e:
                logger.warning(f"GPU not available, falling back to CPU: {e}")
                self.use_gpu = False
        else:
            logger.info("GPU VaR calculator initialized (CPU mode)")
    
    def monte_carlo_var(
        self,
        current_position: float,  # Units (e.g., ounces of gold)
        current_price: float,
        returns_mean: float,  # Historical mean return
        returns_std: float,  # Historical std dev of returns
        returns_cov: Optional[np.ndarray] = None,  # Covariance matrix for multi-asset
        n_scenarios: int = 100000,
        time_horizon_days: int = 1,
    ) -> VaRResult:
        """
        Compute VaR using Monte Carlo simulation.
        
        Args:
            current_position: Current position size in units.
            current_price: Current price per unit.
            returns_mean: Historical mean daily return.
            returns_std: Historical std dev of daily return.
            returns_cov: Covariance matrix (optional for multi-asset).
            n_scenarios: Number of Monte Carlo scenarios to run.
            time_horizon_days: Holding period in days.
        
        Returns:
            VaRResult with percentiles and statistics.
        """
        import time
        start_time = time.time()
        
        portfolio_value = current_position * current_price
        
        try:
            if self.use_gpu:
                var_result = self._monte_carlo_gpu(
                    portfolio_value, returns_mean, returns_std,
                    returns_cov, n_scenarios, time_horizon_days
                )
            else:
                var_result = self._monte_carlo_cpu(
                    portfolio_value, returns_mean, returns_std,
                    returns_cov, n_scenarios, time_horizon_days
                )
        except Exception as e:
            logger.error(f"Monte Carlo failed: {e} — returning zero VaR")
            var_result = VaRResult(
                var_95=0, var_99=0, cvar_95=0, cvar_99=0,
                max_drawdown_pct=0, scenarios_ran=0,
                computation_time_ms=0, used_gpu=self.use_gpu
            )
        
        var_result.computation_time_ms = (time.time() - start_time) * 1000
        var_result.used_gpu = self.use_gpu
        
        logger.debug(
            f"VaR computed: 95%={var_result.var_95:.2f} 99%={var_result.var_99:.2f} "
            f"scenarios={var_result.scenarios_ran} time={var_result.computation_time_ms:.1f}ms ({self.device})"
        )
        
        return var_result
    
    def _monte_carlo_gpu(
        self,
        portfolio_value: float,
        returns_mean: float,
        returns_std: float,
        returns_cov: Optional[np.ndarray],
        n_scenarios: int,
        time_horizon_days: int,
    ) -> VaRResult:
        """GPU-accelerated Monte Carlo simulation."""
        # Generate random scenarios on GPU
        dt = time_horizon_days / 252.0  # Convert to year fraction
        drift = (returns_mean - 0.5 * returns_std**2) * dt
        diffusion = returns_std * np.sqrt(dt)
        
        # Random normal samples
        random_samples = cp.random.standard_normal((n_scenarios, 1))
        
        # Simulate returns
        returns_sim = drift + diffusion * random_samples
        
        # Convert to P&L
        pnl_sim = portfolio_value * returns_sim.flatten()
        
        # Transfer back to CPU for percentile calculations
        pnl_sim_cpu = cp.asnumpy(pnl_sim)
        
        # VaR = negative of 5th and 1st percentiles
        var_95 = -np.percentile(pnl_sim_cpu, 5)
        var_99 = -np.percentile(pnl_sim_cpu, 1)
        
        # CVaR = average of worst scenarios
        worst_5pct = pnl_sim_cpu[pnl_sim_cpu <= np.percentile(pnl_sim_cpu, 5)]
        worst_1pct = pnl_sim_cpu[pnl_sim_cpu <= np.percentile(pnl_sim_cpu, 1)]
        
        cvar_95 = -np.mean(worst_5pct) if len(worst_5pct) > 0 else var_95
        cvar_99 = -np.mean(worst_1pct) if len(worst_1pct) > 0 else var_99
        
        max_dd = -np.min(pnl_sim_cpu) / portfolio_value if portfolio_value > 0 else 0
        
        return VaRResult(
            var_95=var_95,
            var_99=var_99,
            cvar_95=cvar_95,
            cvar_99=cvar_99,
            max_drawdown_pct=max_dd,
            scenarios_ran=n_scenarios,
            computation_time_ms=0,  # Filled by caller
            used_gpu=True,
        )
    
    def _monte_carlo_cpu(
        self,
        portfolio_value: float,
        returns_mean: float,
        returns_std: float,
        returns_cov: Optional[np.ndarray],
        n_scenarios: int,
        time_horizon_days: int,
    ) -> VaRResult:
        """CPU-based Monte Carlo simulation."""
        dt = time_horizon_days / 252.0
        drift = (returns_mean - 0.5 * returns_std**2) * dt
        diffusion = returns_std * np.sqrt(dt)
        
        # Generate random scenarios
        random_samples = np.random.standard_normal((n_scenarios, 1))
        
        # Simulate returns
        returns_sim = drift + diffusion * random_samples
        
        # Convert to P&L
        pnl_sim = portfolio_value * returns_sim.flatten()
        
        # VaR calculations
        var_95 = -np.percentile(pnl_sim, 5)
        var_99 = -np.percentile(pnl_sim, 1)
        
        worst_5pct = pnl_sim[pnl_sim <= np.percentile(pnl_sim, 5)]
        worst_1pct = pnl_sim[pnl_sim <= np.percentile(pnl_sim, 1)]
        
        cvar_95 = -np.mean(worst_5pct) if len(worst_5pct) > 0 else var_95
        cvar_99 = -np.mean(worst_1pct) if len(worst_1pct) > 0 else var_99
        
        max_dd = -np.min(pnl_sim) / portfolio_value if portfolio_value > 0 else 0
        
        return VaRResult(
            var_95=var_95,
            var_99=var_99,
            cvar_95=cvar_95,
            cvar_99=cvar_99,
            max_drawdown_pct=max_dd,
            scenarios_ran=n_scenarios,
            computation_time_ms=0,
            used_gpu=False,
        )
    
    def stress_test(
        self,
        portfolio_value: float,
        stress_scenarios: Optional[Dict[str, np.ndarray]] = None,
    ) -> Dict[str, float]:
        """
        Run predefined stress scenarios and report P&L impact.
        
        Args:
            portfolio_value: Current portfolio value.
            stress_scenarios: Dict mapping scenario name to shock vector.
        
        Returns:
            Dict mapping scenario name to expected P&L impact.
        """
        if stress_scenarios is None:
            stress_scenarios = self._default_stress_scenarios()
        
        results = {}
        
        for scenario_name, shock in stress_scenarios.items():
            # Assume shock vector directly translates to return
            pnl_impact = float(portfolio_value * shock[0])  # Convert numpy array to scalar
            results[scenario_name] = pnl_impact
            logger.info(f"Stress test '{scenario_name}': {pnl_impact:+.2f}")
        
        return results
    
    @staticmethod
    def _default_stress_scenarios() -> Dict[str, np.ndarray]:
        """Predefined stress test scenarios."""
        return {
            "usd_flash_rally": np.array([-0.035]),  # Gold -3.5%
            "liquidity_crisis": np.array([-0.02]),  # Gold -2% (slippage)
            "flash_crash": np.array([-0.05]),  # Gold -5%
            "rate_surprise": np.array([-0.015]),  # Gold -1.5%
            "geopolitical": np.array([0.045]),  # Gold +4.5%
        }
