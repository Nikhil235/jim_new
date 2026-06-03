"""
A/B TESTING FRAMEWORK FOR TRADING STRATEGIES
Compare with vs without filters automatically.
"""

import json
import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime
from loguru import logger


@dataclass
class ABTestConfig:
    test_name: str
    control_config: Dict
    treatment_config: Dict
    metrics: List[str]
    split_ratio: float = 0.5


@dataclass
class ABTestResult:
    test_name: str
    control_metrics: Dict
    treatment_metrics: Dict
    improvement_pct: Dict
    statistical_significance: bool
    p_value: float
    winner: str


class ABTestFramework:
    """
    A/B Testing Framework for Trading Strategies.

    1. Define control (without filter) and treatment (with filter)
    2. Run backtest on both
    3. Compare metrics
    4. Get statistical significance
    """

    def __init__(self, results_dir: str = "ab_test_results"):
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def run_test(
        self,
        test_name: str,
        control_data: pd.DataFrame,
        treatment_data: pd.DataFrame,
        filter_name: str = "",
        metrics: Optional[List[str]] = None,
    ) -> ABTestResult:
        if metrics is None:
            metrics = ["sharpe_ratio", "total_return", "max_drawdown", "win_rate", "profit_factor", "avg_trade_pnl", "num_trades"]

        control_metrics = self._calc_metrics(control_data)
        treatment_metrics = self._calc_metrics(treatment_data)

        improvement = {}
        for m in metrics:
            if m in control_metrics and m in treatment_metrics:
                cv = control_metrics[m]
                tv = treatment_metrics[m]
                if m == "max_drawdown":
                    improvement[m] = (cv - tv) / abs(cv) * 100 if cv != 0 else 0
                else:
                    improvement[m] = (tv - cv) / cv * 100 if cv != 0 else 0

        pnl_col = "pnl" if "pnl" in control_data.columns else "PnL" if "PnL" in control_data.columns else None
        if pnl_col:
            p_value = self._p_value(control_data[pnl_col].dropna(), treatment_data[pnl_col].dropna())
        else:
            p_value = 1.0
        significant = p_value < 0.05
        winner = "treatment" if improvement.get("sharpe_ratio", 0) > 0 else "control"

        result = ABTestResult(
            test_name=test_name,
            control_metrics=control_metrics,
            treatment_metrics=treatment_metrics,
            improvement_pct=improvement,
            statistical_significance=significant,
            p_value=p_value,
            winner=winner,
        )

        self._save(result)
        return result

    def _calc_metrics(self, data: pd.DataFrame) -> Dict:
        pnl_col = "pnl" if "pnl" in data.columns else "PnL" if "PnL" in data.columns else "returns" if "returns" in data.columns else None
        metrics: Dict = {}

        if pnl_col is None or data[pnl_col].dropna().empty:
            return {"total_return": 0, "sharpe_ratio": 0, "max_drawdown": 0, "win_rate": 0, "profit_factor": 0, "avg_trade_pnl": 0, "num_trades": 0}

        pnl = data[pnl_col].dropna()
        metrics["total_return"] = float(pnl.sum())

        daily_returns = pnl.pct_change().dropna()
        if daily_returns.std() > 0:
            metrics["sharpe_ratio"] = float((daily_returns.mean() / daily_returns.std()) * np.sqrt(252))
        else:
            metrics["sharpe_ratio"] = 0.0

        cum = pnl.cumsum()
        cumulative = (1 + cum / cum.abs().max()).cumprod() if cum.abs().max() > 0 else pd.Series(1.0, index=cum.index)
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max
        metrics["max_drawdown"] = float(drawdown.min())

        wins = pnl[pnl > 0]
        metrics["win_rate"] = float(len(wins) / len(pnl)) if len(pnl) > 0 else 0.0

        gross_profit = pnl[pnl > 0].sum()
        gross_loss = abs(pnl[pnl < 0].sum())
        metrics["profit_factor"] = float(gross_profit / gross_loss) if gross_loss > 0 else 0.0 if gross_profit == 0 else float("inf")

        metrics["avg_trade_pnl"] = float(pnl.mean())
        metrics["num_trades"] = int(len(pnl))

        return metrics

    def _p_value(self, a: pd.Series, b: pd.Series) -> float:
        from scipy import stats
        if len(a) < 2 or len(b) < 2:
            return 1.0
        _, p = stats.ttest_ind(a, b)
        return float(p)

    def _save(self, result: ABTestResult):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self.results_dir / f"{result.test_name}_{ts}.json"
        path.write_text(json.dumps(asdict(result), indent=2, default=str))
        logger.info(f"A/B test saved to {path}")

    def compare_tests(self) -> pd.DataFrame:
        records = []
        for f in sorted(self.results_dir.glob("*.json")):
            records.append(json.loads(f.read_text()))
        return pd.DataFrame(records) if records else pd.DataFrame()


def test_rsi_gate(
    with_rsi_path: str = "backtest_with_rsi.csv",
    without_rsi_path: str = "backtest_without_rsi.csv",
    rsi_threshold: float = 75.0,
) -> ABTestResult:
    """
    A/B test: RSI filter impact on strategy performance.

    Args:
        with_rsi_path: path to CSV with RSI filter enabled
        without_rsi_path: path to CSV without RSI filter
        rsi_threshold: RSI threshold used in the filter

    Returns:
        ABTestResult with comparison metrics
    """
    framework = ABTestFramework(results_dir="ab_test_results")

    try:
        with_rsi = pd.read_csv(with_rsi_path)
        without_rsi = pd.read_csv(without_rsi_path)
    except FileNotFoundError as e:
        logger.warning(f"RSI A/B test data not found: {e}. Run backtests first.")
        return ABTestResult(
            test_name=f"RSI_Gate_{rsi_threshold}",
            control_metrics={},
            treatment_metrics={},
            improvement_pct={},
            statistical_significance=False,
            p_value=1.0,
            winner="unknown",
        )

    result = framework.run_test(
        test_name=f"RSI_Gate_{rsi_threshold}",
        control_data=without_rsi,
        treatment_data=with_rsi,
        filter_name=f"RSI < {rsi_threshold} for LONG",
    )

    sharpe_imp = result.improvement_pct.get("sharpe_ratio", 0)
    logger.info("RSI Gate Impact (threshold={}):", rsi_threshold)
    logger.info("  Sharpe with RSI:    {:.2f}", result.treatment_metrics.get("sharpe_ratio", 0))
    logger.info("  Sharpe without RSI: {:.2f}", result.control_metrics.get("sharpe_ratio", 0))
    logger.info("  Improvement: {:.1f}%", sharpe_imp)
    logger.info("  Winner: {}", result.winner)

    if sharpe_imp < 0:
        logger.warning("RSI gate reduces performance — consider disabling")
    elif sharpe_imp > 5:
        logger.info("RSI gate improves performance — keep enabled")

    return result
