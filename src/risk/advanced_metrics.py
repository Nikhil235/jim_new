"""
Advanced Risk Metrics
=====================
Extended risk metrics beyond standard Sharpe/Sortino including:
- Omega Ratio: Probability-weighted returns above/below target
- Ulcer Index: Chronic drawdown stress measure
- Conditional VaR (CVaR): Expected shortfall at tail
- Expected Shortfall: Mean return below percentile
- Tail Risk Metrics: Skewness, kurtosis, fat-tail adjustment
"""

import numpy as np
from typing import List, Tuple, Optional
from scipy import stats
from dataclasses import dataclass
from loguru import logger


@dataclass
class AdvancedRiskMetrics:
    """Container for advanced risk metrics."""
    omega_ratio: float = 0.0
    ulcer_index: float = 0.0
    conditional_var: float = 0.0  # CVaR at 95%
    expected_shortfall: float = 0.0
    skewness: float = 0.0
    kurtosis: float = 0.0
    tail_ratio: float = 0.0  # Right tail / Left tail
    recovery_factor: float = 0.0  # Total return / Max drawdown


class AdvancedRiskCalculator:
    """
    Calculate advanced risk metrics for strategy evaluation.
    """
    
    @staticmethod
    def calculate_omega_ratio(
        returns: List[float],
        target_return: float = 0.0,
        periods_per_year: int = 252
    ) -> float:
        """
        Calculate Omega Ratio: probability-weighted ratio of gains to losses vs target.
        
        Omega = P(R > target) * E[R | R > target] / (P(R < target) * E[|R| | R < target])
        
        Args:
            returns: List of period returns
            target_return: Target return threshold (daily)
            periods_per_year: Periods per year (252 for daily data)
            
        Returns:
            Omega ratio (values > 1 are good)
        """
        if len(returns) < 2:
            return 0.0
        
        returns = np.array(returns)
        excess_returns = returns - target_return
        
        # Split returns
        gains = excess_returns[excess_returns > 0]
        losses = excess_returns[excess_returns < 0]
        
        if len(losses) == 0:
            return np.inf  # All returns above target
        
        prob_gain = len(gains) / len(returns)
        prob_loss = len(losses) / len(returns)
        
        avg_gain = np.mean(gains) if len(gains) > 0 else 0
        avg_loss = abs(np.mean(losses))
        
        if avg_loss == 0:
            return np.inf
        
        omega = (prob_gain * avg_gain) / (prob_loss * avg_loss)
        return float(omega)
    
    @staticmethod
    def calculate_ulcer_index(
        equity_curve: List[float],
        lookback: int = 252
    ) -> float:
        """
        Calculate Ulcer Index: square root of mean squared drawdowns.
        Focuses on chronic (sustained) drawdown stress.
        
        UI = sqrt(mean((DD_i)^2)) where DD_i = max drawdown at time i
        
        Args:
            equity_curve: List of equity values
            lookback: Lookback window
            
        Returns:
            Ulcer Index (lower is better, typically 0-10)
        """
        if len(equity_curve) < 2:
            return 0.0
        
        equity = np.array(equity_curve)
        running_max = np.maximum.accumulate(equity)
        drawdowns = (equity - running_max) / running_max * 100  # Convert to %
        
        # Only consider last lookback periods
        dd_subset = drawdowns[-lookback:] if len(drawdowns) > lookback else drawdowns
        
        # Calculate UI
        ui = np.sqrt(np.mean(dd_subset ** 2))
        return float(ui)
    
    @staticmethod
    def calculate_conditional_var(
        returns: List[float],
        confidence_level: float = 0.95,
        periods_per_year: int = 252
    ) -> float:
        """
        Calculate Conditional Value at Risk (CVaR) / Expected Shortfall.
        Expected loss when returns fall below VaR.
        
        Args:
            returns: List of period returns (as decimals, e.g., 0.01 = 1%)
            confidence_level: Confidence level (0.95 = 95%)
            periods_per_year: Periods per year
            
        Returns:
            CVaR (annualized, in percent)
        """
        if len(returns) < 2:
            return 0.0
        
        returns = np.array(returns)
        
        # Calculate VaR first
        var = np.percentile(returns, (1 - confidence_level) * 100)
        
        # CVaR is mean of returns worse than VaR
        worst_returns = returns[returns <= var]
        if len(worst_returns) == 0:
            worst_returns = returns[returns <= np.min(returns)]
        
        cvar = np.mean(worst_returns)
        
        # Annualize
        annual_cvar = cvar * np.sqrt(periods_per_year) * 100  # Convert to percent
        
        return float(annual_cvar)
    
    @staticmethod
    def calculate_expected_shortfall(
        returns: List[float],
        percentile: float = 5.0
    ) -> float:
        """
        Calculate Expected Shortfall: mean return below percentile.
        
        Args:
            returns: List of period returns
            percentile: Percentile threshold (e.g., 5 = 5th percentile)
            
        Returns:
            Expected shortfall
        """
        if len(returns) < 2:
            return 0.0
        
        returns = np.array(returns)
        threshold = np.percentile(returns, percentile)
        
        # Mean of returns below threshold
        es = np.mean(returns[returns <= threshold])
        
        return float(es)
    
    @staticmethod
    def calculate_tail_risk_metrics(
        returns: List[float]
    ) -> Tuple[float, float, float]:
        """
        Calculate tail risk metrics: skewness, kurtosis, tail ratio.
        
        Args:
            returns: List of period returns
            
        Returns:
            Tuple of (skewness, excess_kurtosis, tail_ratio)
        """
        if len(returns) < 3:
            return 0.0, 0.0, 0.0
        
        returns = np.array(returns)
        
        # Skewness
        skew = float(stats.skew(returns))
        
        # Excess kurtosis (kurtosis - 3)
        excess_kurt = float(stats.kurtosis(returns, fisher=True))
        
        # Tail ratio: ratio of right tail to left tail
        # Split at median
        median_return = np.median(returns)
        right_tail = returns[returns > median_return]
        left_tail = returns[returns < median_return]
        
        right_std = np.std(right_tail) if len(right_tail) > 0 else 0
        left_std = np.std(left_tail) if len(left_tail) > 0 else 1
        
        tail_ratio = right_std / left_std if left_std > 0 else 0
        
        return skew, excess_kurt, float(tail_ratio)
    
    @staticmethod
    def calculate_recovery_factor(
        total_return: float,
        max_drawdown: float
    ) -> float:
        """
        Calculate Recovery Factor: total return / max drawdown.
        Higher is better (shows how much profit for each unit of loss).
        
        Args:
            total_return: Total return (as decimal, e.g., 0.25 = 25%)
            max_drawdown: Maximum drawdown (as decimal, negative, e.g., -0.15 = -15%)
            
        Returns:
            Recovery factor
        """
        if max_drawdown == 0 or max_drawdown >= 0:
            return float('inf') if total_return >= 0 else 0.0
        
        recovery = total_return / abs(max_drawdown)
        return float(recovery)
    
    @staticmethod
    def calculate_stress_adjusted_sharpe(
        returns: List[float],
        risk_free_rate: float = 0.0,
        periods_per_year: int = 252
    ) -> float:
        """
        Calculate Sharpe Ratio adjusted for non-normal distribution (stress).
        Includes adjustment for skewness and excess kurtosis.
        
        Adjusted SR = SR * (1 - S^3/(24*T) - K/(24*sqrt(T)))
        where S = skewness, K = excess kurtosis, T = number of periods
        
        Args:
            returns: List of period returns
            risk_free_rate: Risk-free rate (daily)
            periods_per_year: Periods per year
            
        Returns:
            Stress-adjusted Sharpe ratio
        """
        if len(returns) < 2:
            return 0.0
        
        returns = np.array(returns)
        
        # Calculate standard Sharpe
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        if std_return == 0:
            return 0.0
        
        sharpe = (mean_return - risk_free_rate) / std_return
        
        # Annualize
        annual_sharpe = sharpe * np.sqrt(periods_per_year)
        
        # Get tail risk metrics
        skew, excess_kurt, _ = AdvancedRiskCalculator.calculate_tail_risk_metrics(returns)
        
        # Apply stress adjustment
        T = len(returns)
        adjustment = 1 - (skew ** 3) / (24 * T) - excess_kurt / (24 * np.sqrt(T))
        
        stress_adjusted_sharpe = annual_sharpe * adjustment
        
        return float(stress_adjusted_sharpe)
    
    @staticmethod
    def generate_risk_report(
        equity_curve: List[float],
        returns: List[float],
        total_return: float,
        max_drawdown: float,
        sharpe_ratio: float,
        risk_free_rate: float = 0.0
    ) -> str:
        """
        Generate comprehensive risk metrics report.
        
        Args:
            equity_curve: List of equity values
            returns: List of period returns
            total_return: Total return
            max_drawdown: Maximum drawdown
            sharpe_ratio: Sharpe ratio
            risk_free_rate: Risk-free rate
            
        Returns:
            Formatted report
        """
        report = []
        report.append("=" * 60)
        report.append("ADVANCED RISK METRICS REPORT")
        report.append("=" * 60)
        report.append("")
        
        # Standard metrics
        report.append("Standard Metrics:")
        report.append(f"  Total Return: {total_return:.2%}")
        report.append(f"  Max Drawdown: {max_drawdown:.2%}")
        report.append(f"  Sharpe Ratio: {sharpe_ratio:.2f}")
        report.append("")
        
        # Advanced metrics
        omega = AdvancedRiskCalculator.calculate_omega_ratio(returns, 0.0)
        ulcer = AdvancedRiskCalculator.calculate_ulcer_index(equity_curve)
        cvar = AdvancedRiskCalculator.calculate_conditional_var(returns)
        es = AdvancedRiskCalculator.calculate_expected_shortfall(returns)
        skew, kurt, tail = AdvancedRiskCalculator.calculate_tail_risk_metrics(returns)
        recovery = AdvancedRiskCalculator.calculate_recovery_factor(total_return, max_drawdown)
        stress_sharpe = AdvancedRiskCalculator.calculate_stress_adjusted_sharpe(returns, risk_free_rate)
        
        report.append("Advanced Metrics:")
        report.append(f"  Omega Ratio: {omega:.2f} (>1 is good)")
        report.append(f"  Ulcer Index: {ulcer:.2f} (lower is better)")
        report.append(f"  Conditional VaR (95%): {cvar:.2%} (annualized)")
        report.append(f"  Expected Shortfall: {es:.4f}")
        report.append(f"  Recovery Factor: {recovery:.2f}")
        report.append("")
        
        report.append("Tail Risk Metrics:")
        report.append(f"  Skewness: {skew:.2f} (>0 = right-skewed, better)")
        report.append(f"  Excess Kurtosis: {kurt:.2f} (>0 = fat tails, worse)")
        report.append(f"  Tail Ratio: {tail:.2f} (right/left tail std dev)")
        report.append(f"  Stress-Adjusted Sharpe: {stress_sharpe:.2f}")
        report.append("")
        
        # Risk assessment
        report.append("Risk Assessment:")
        if omega > 1.5:
            report.append("  ✓ Strong omega ratio (good risk/reward)")
        elif omega > 1.0:
            report.append("  ~ Acceptable omega ratio")
        else:
            report.append("  ✗ Weak omega ratio")
        
        if ulcer < 5:
            report.append("  ✓ Low chronic drawdown stress")
        elif ulcer < 10:
            report.append("  ~ Moderate drawdown stress")
        else:
            report.append("  ✗ High drawdown stress")
        
        if skew > 0.5:
            report.append("  ✓ Right-skewed returns (good)")
        elif skew > -0.5:
            report.append("  ~ Symmetric returns")
        else:
            report.append("  ✗ Left-skewed returns (bad)")
        
        report.append("=" * 60)
        
        return "\n".join(report)
