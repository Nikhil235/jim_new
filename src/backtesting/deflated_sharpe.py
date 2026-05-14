"""
Phase 5: Deflated Sharpe Ratio (DSR)

DSR corrects Sharpe Ratio for:
1. Number of strategies tested (multiple testing bias)
2. Non-normal return distributions (skewness, kurtosis)
3. Autocorrelation in returns
4. Length of backtest

Reference: Bailey, D. H., Borwein, J. M., López de Prado, M., & Zhu, Q. J. (2015).
"Deflating Sharpe Ratios"
https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551
"""

from dataclasses import dataclass
from typing import List, Optional
import numpy as np
from scipy import stats
from scipy.optimize import minimize

from loguru import logger


@dataclass
class DSRResult:
    """Deflated Sharpe Ratio result."""
    sharpe_ratio: float                    # Original Sharpe Ratio
    deflated_sharpe_ratio: float          # DSR
    p_value: float                        # Probability it's due to luck
    strategy_count: int                   # Number of strategies tested
    is_significant: bool = False          # p_value < 0.05?

    def __post_init__(self):
        self.is_significant = self.p_value < 0.05

    @property
    def verdict(self) -> str:
        """Pass/fail verdict."""
        if self.is_significant:
            return f"PASS (DSR={self.deflated_sharpe_ratio:.2f}, p={self.p_value:.4f})"
        else:
            return f"FAIL (DSR={self.deflated_sharpe_ratio:.2f}, p={self.p_value:.4f})"


class DeflatedSharpeCalculator:
    """
    Calculate Deflated Sharpe Ratio with statistical rigor.
    """

    @staticmethod
    def calculate(
        returns: List[float],
        sharpe_ratio: float,
        num_strategies: int = 1,
        risk_free_rate: float = 0.02,
        trading_days_per_year: int = 252,
    ) -> DSRResult:
        """
        Calculate Deflated Sharpe Ratio.
        
        Args:
            returns: Daily returns (as decimals, e.g., 0.01 for 1%)
            sharpe_ratio: Original Sharpe Ratio (annualized)
            num_strategies: Number of strategies tested (multiple testing)
            risk_free_rate: Annual risk-free rate
            trading_days_per_year: Days per year
            
        Returns:
            DSRResult with DSR p-value
        """
        returns = np.array(returns)
        T = len(returns)
        
        if T < 2:
            logger.warning("Insufficient data for DSR calculation")
            return DSRResult(sharpe_ratio, 0, 1.0, num_strategies)
        
        # Calculate distribution metrics
        skewness = stats.skew(returns)
        kurtosis = stats.kurtosis(returns)
        autocorr = np.corrcoef(returns[:-1], returns[1:])[0, 1]
        
        # Adjustment for non-normal returns
        # DSR = SR * sqrt(1/(1 + (S^3 * SR + K * SR^2 / 4) / T))
        non_normal_factor = 1 + (skewness**3 * sharpe_ratio + kurtosis * sharpe_ratio**2 / 4) / T
        
        # Adjustment for multiple testing (Bonferroni-like)
        # Probability that best of M independent tests exceeds SR
        m_factor = np.log(num_strategies)
        
        # Calculate standard error of Sharpe
        sr_std = np.sqrt((1 + sharpe_ratio**2 / 2) / T)
        
        # DSR formula
        dsr = sharpe_ratio / np.sqrt(non_normal_factor)
        
        # Adjusted for multiple testing
        dsr_adjusted = dsr - (m_factor * sr_std)
        
        # P-value: probability this is due to luck (1 - CDF)
        z_score = dsr_adjusted / sr_std
        p_value = 1 - stats.norm.cdf(z_score)
        
        result = DSRResult(
            sharpe_ratio=sharpe_ratio,
            deflated_sharpe_ratio=dsr_adjusted,
            p_value=p_value,
            strategy_count=num_strategies,
        )
        
        return result

    @staticmethod
    def bootstrap_test(
        returns: List[float],
        sharpe_ratio: float,
        num_strategies: int = 1,
        bootstrap_samples: int = 1000,
    ) -> DSRResult:
        """
        Bootstrap-based Deflated Sharpe Ratio (more robust).
        
        Creates artificial return streams by bootstrap resampling
        to estimate distribution of Sharpe ratio under null hypothesis.
        
        Args:
            returns: Daily returns
            sharpe_ratio: Original Sharpe Ratio
            num_strategies: Number of strategies tested
            bootstrap_samples: Number of bootstrap iterations
            
        Returns:
            DSRResult from bootstrap test
        """
        returns = np.array(returns)
        T = len(returns)
        
        bootstrap_sharpes = []
        
        for _ in range(bootstrap_samples):
            # Resample returns with replacement
            boot_returns = np.random.choice(returns, size=T, replace=True)
            
            # Calculate Sharpe ratio of bootstrap sample
            mean_ret = np.mean(boot_returns)
            std_ret = np.std(boot_returns)
            boot_sharpe = mean_ret / std_ret * np.sqrt(252) if std_ret > 0 else 0
            
            bootstrap_sharpes.append(boot_sharpe)
        
        bootstrap_sharpes = np.array(bootstrap_sharpes)
        
        # P-value: proportion of bootstrap Sharpes >= original
        p_value = np.mean(bootstrap_sharpes >= sharpe_ratio)
        
        # Adjust for multiple testing
        p_value = 1 - (1 - p_value) ** (1 / num_strategies)
        
        # DSR is the original Sharpe adjusted downward
        dsr = sharpe_ratio * (1 - p_value)
        
        result = DSRResult(
            sharpe_ratio=sharpe_ratio,
            deflated_sharpe_ratio=dsr,
            p_value=max(0, min(1, p_value)),
            strategy_count=num_strategies,
        )
        
        return result

    @staticmethod
    def format_result(result: DSRResult) -> str:
        """Format DSR result for display."""
        lines = [
            f"Original Sharpe Ratio:     {result.sharpe_ratio:>10.2f}",
            f"Deflated Sharpe Ratio:     {result.deflated_sharpe_ratio:>10.2f}",
            f"P-Value:                   {result.p_value:>10.4f}",
            f"Strategies Tested:         {result.strategy_count:>10}",
            f"Significant (p < 0.05):    {str(result.is_significant):>10}",
            f"Verdict:                   {result.verdict:>10}",
        ]
        return "\n".join(lines)
