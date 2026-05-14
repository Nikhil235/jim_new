"""
Phase 5: Backtest Report Generator

Generates standardized reports for backtest results with:
- Summary statistics
- Performance metrics
- Risk analysis
- Trade-by-trade results
- Regime performance breakdown
- Statistical significance testing
"""

from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import asdict

from loguru import logger

from .metrics import PerformanceMetrics, MetricsCalculator
from .deflated_sharpe import DSRResult
from .walk_forward import WalkForwardResult


class BacktestReportGenerator:
    """Generate standardized backtest reports."""

    @staticmethod
    def generate_markdown(
        strategy_name: str,
        version: str,
        backtest_results: Dict,
        metrics: PerformanceMetrics,
        dsr_result: Optional[DSRResult] = None,
        walk_forward_results: Optional[List[WalkForwardResult]] = None,
    ) -> str:
        """
        Generate markdown report.
        
        Args:
            strategy_name: Name of strategy
            version: Strategy version
            backtest_results: Results from backtester
            metrics: Calculated metrics
            dsr_result: DSR validation result
            walk_forward_results: Walk-forward analysis results
            
        Returns:
            Markdown report string
        """
        report = []
        
        # Header
        report.append(f"# Backtest Report: {strategy_name} v{version}")
        report.append(f"\n**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        
        # Summary
        report.append("## Executive Summary\n")
        report.append(f"- **Period**: {backtest_results.get('period_start', 'N/A')} to {backtest_results.get('period_end', 'N/A')}")
        report.append(f"- **Market Events**: {backtest_results.get('market_events', 0):,}")
        report.append(f"- **Signals Generated**: {backtest_results.get('signals_generated', 0):,}")
        report.append(f"- **Total Trades**: {metrics.total_trades}")
        report.append(f"- **Initial Capital**: ${backtest_results.get('initial_capital', 0):,.2f}")
        report.append(f"- **Final Equity**: ${backtest_results.get('final_equity', 0):,.2f}\n")
        
        # Performance Metrics
        report.append("## Performance Metrics\n")
        report.append("| Metric | Value |")
        report.append("|--------|-------|")
        report.append(f"| Total Return | {metrics.total_return:.2%} |")
        report.append(f"| Annual Return | {metrics.annual_return:.2%} |")
        report.append(f"| Volatility (Annual) | {metrics.annual_volatility:.2%} |")
        report.append(f"| Sharpe Ratio | {metrics.sharpe_ratio:.2f} |")
        report.append(f"| Sortino Ratio | {metrics.sortino_ratio:.2f} |")
        report.append(f"| Max Drawdown | {metrics.max_drawdown:.2%} |")
        report.append(f"| Calmar Ratio | {metrics.calmar_ratio:.2f} |")
        report.append(f"| Recovery Factor | {metrics.recovery_factor:.2f} |\n")
        
        # Trade Statistics
        report.append("## Trade Statistics\n")
        report.append("| Metric | Value |")
        report.append("|--------|-------|")
        report.append(f"| Total Trades | {metrics.total_trades} |")
        report.append(f"| Winning Trades | {metrics.winning_trades} ({metrics.win_rate:.1%}) |")
        report.append(f"| Losing Trades | {metrics.losing_trades} ({1-metrics.win_rate:.1%}) |")
        report.append(f"| Profit Factor | {metrics.profit_factor:.2f} |")
        report.append(f"| Avg Winning Trade | ${metrics.avg_win:,.2f} |")
        report.append(f"| Avg Losing Trade | ${metrics.avg_loss:,.2f} |")
        report.append(f"| Risk/Reward Ratio | {metrics.risk_reward_ratio:.2f} |")
        report.append(f"| Avg Trade Duration | {metrics.avg_trade_duration:.1f} hours |\n")
        
        # Risk Management
        report.append("## Risk Management\n")
        report.append("| Metric | Value |")
        report.append("|--------|-------|")
        report.append(f"| Max Drawdown | {metrics.max_drawdown:.2%} |")
        report.append(f"| Avg Drawdown | {metrics.avg_drawdown:.2%} |")
        report.append(f"| Return / Max DD | {metrics.recovery_factor:.2f} |")
        report.append(f"| Total Commission | ${backtest_results.get('total_commission', 0):,.2f} |")
        report.append(f"| Total Slippage | ${backtest_results.get('total_slippage', 0):,.2f} |\n")
        
        # DSR Validation
        if dsr_result:
            report.append("## Statistical Significance (DSR)\n")
            report.append("| Metric | Value |")
            report.append("|--------|-------|")
            report.append(f"| Original Sharpe | {dsr_result.sharpe_ratio:.2f} |")
            report.append(f"| Deflated Sharpe | {dsr_result.deflated_sharpe_ratio:.2f} |")
            report.append(f"| P-Value | {dsr_result.p_value:.4f} |")
            report.append(f"| Significant (p<0.05) | {'YES' if dsr_result.is_significant else 'NO'} |")
            report.append(f"| Strategies Tested | {dsr_result.strategy_count} |\n")
            
            if dsr_result.is_significant:
                report.append("✅ **PASS**: Results are statistically significant.\n")
            else:
                report.append("❌ **FAIL**: Results not statistically significant. May be due to luck.\n")
        
        # Walk-Forward Analysis
        if walk_forward_results:
            report.append("## Walk-Forward Analysis\n")
            report.append("| Period | IS Return | OOS Return | IS Sharpe | OOS Sharpe | Overfit |")
            report.append("|--------|-----------|------------|-----------|------------|---------|")
            
            for i, wf_result in enumerate(walk_forward_results):
                overfit = "YES" if wf_result.is_overfit() else "NO"
                report.append(
                    f"| {i+1} | {wf_result.is_return:.2%} | {wf_result.oos_return:.2%} | "
                    f"{wf_result.is_sharpe:.2f} | {wf_result.oos_sharpe:.2f} | {overfit} |"
                )
            
            report.append()
            
            # WF Summary
            avg_is_return = sum(r.is_return for r in walk_forward_results) / len(walk_forward_results)
            avg_oos_return = sum(r.oos_return for r in walk_forward_results) / len(walk_forward_results)
            avg_is_sharpe = sum(r.is_sharpe for r in walk_forward_results) / len(walk_forward_results)
            avg_oos_sharpe = sum(r.oos_sharpe for r in walk_forward_results) / len(walk_forward_results)
            
            report.append("\n**Summary**\n")
            report.append(f"- Avg IS Return: {avg_is_return:.2%}")
            report.append(f"- Avg OOS Return: {avg_oos_return:.2%}")
            report.append(f"- Avg IS Sharpe: {avg_is_sharpe:.2f}")
            report.append(f"- Avg OOS Sharpe: {avg_oos_sharpe:.2f}")
            report.append(f"- Return Degradation: {avg_is_return - avg_oos_return:.2%}\n")
        
        # Distribution
        report.append("## Return Distribution\n")
        report.append("| Metric | Value |")
        report.append("|--------|-------|")
        report.append(f"| Skewness | {metrics.skewness:.2f} |")
        report.append(f"| Kurtosis | {metrics.kurtosis:.2f} |\n")
        
        # Verdict
        report.append("## Verdict\n\n")
        
        verdict_passed = []
        verdict_failed = []
        
        if metrics.sharpe_ratio > 1.0:
            verdict_passed.append("[PASS] Sharpe Ratio > 1.0")
        else:
            verdict_failed.append("[FAIL] Sharpe Ratio < 1.0")
        
        if metrics.max_drawdown > -0.15:
            verdict_passed.append("[PASS] Max Drawdown < 15%")
        else:
            verdict_failed.append("[FAIL] Max Drawdown > 15%")
        
        if metrics.win_rate > 0.50:
            verdict_passed.append("[PASS] Win Rate > 50%")
        else:
            verdict_failed.append("[FAIL] Win Rate < 50%")
        
        if dsr_result and dsr_result.is_significant:
            verdict_passed.append("[PASS] DSR Significant (p < 0.05)")
        else:
            verdict_failed.append("[NOTE] DSR Not Significant")
        
        if verdict_passed:
            report.append("\n".join(verdict_passed))
        
        if verdict_failed:
            report.append("\n\n".join(verdict_failed))
        
        if not verdict_failed and dsr_result and dsr_result.is_significant:
            report.append("\n\n[RECOMMENDATION] PASS - Ready for paper trading\n")
        elif len(verdict_failed) <= 2:
            report.append("\n\n[RECOMMENDATION] NEEDS REVIEW - Some metrics need improvement\n")
        else:
            report.append("\n\n[RECOMMENDATION] FAIL - Does not meet deployment criteria\n")
        
        return "\n".join(report)

    @staticmethod
    def save_report(
        report_text: str,
        filepath: str,
    ):
        """Save report to file."""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report_text)
        logger.info(f"Report saved to {filepath}")
