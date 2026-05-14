"""
Phase 5 Week 3: Strategy Runner - Orchestrates Model Backtesting

This module runs backtests for all Phase 3 models and generates
comprehensive validation reports with DSR and walk-forward analysis.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Tuple
import numpy as np
import pytz
from dataclasses import dataclass, field

from loguru import logger

from .backtester import Backtester, BacktestConfig
from .data_handler import DataHandler
from .metrics import MetricsCalculator, PerformanceMetrics
from .deflated_sharpe import DeflatedSharpeCalculator, DSRResult
from .walk_forward import WalkForwardAnalyzer, WalkForwardResult
from .report_generator import BacktestReportGenerator
from .events import MarketEvent, Direction


@dataclass
class BacktestResult:
    """Complete backtest result for one model."""
    model_name: str
    strategy_name: str
    version: str
    
    # Backtest metrics
    metrics: PerformanceMetrics = None
    equity_curve: List[float] = field(default_factory=list)
    trades: List[dict] = field(default_factory=list)
    dates: List[datetime] = field(default_factory=list)
    
    # Statistical validation
    dsr_result: Optional[DSRResult] = None
    walk_forward_results: Optional[List[WalkForwardResult]] = None
    
    # Results
    passed_validation: bool = False
    recommendation: str = "PENDING"
    
    def __post_init__(self):
        if self.metrics is None:
            self.metrics = PerformanceMetrics()


class StrategyRunner:
    """
    Orchestrates backtesting of multiple strategies/models.
    
    Workflow:
    1. Load or generate market data
    2. Create strategy instances
    3. Run backtests with metrics calculation
    4. Perform statistical validation (DSR, walk-forward)
    5. Generate comprehensive reports
    """
    
    def __init__(
        self,
        initial_capital: float = 100000.0,
        kelly_fraction: float = 0.5,
        num_strategies_tested: int = 10,  # For DSR multiple testing correction
    ):
        """Initialize strategy runner."""
        self.initial_capital = initial_capital
        self.kelly_fraction = kelly_fraction
        self.num_strategies_tested = num_strategies_tested
        self.results: Dict[str, BacktestResult] = {}
        
        logger.info(f"StrategyRunner initialized with ${initial_capital:.2f} capital")
    
    def run_backtest(
        self,
        strategy_name: str,
        strategy_fn: Callable,
        market_data: List[MarketEvent],
        model_name: str = "unknown",
        version: str = "1.0",
    ) -> BacktestResult:
        """
        Run single backtest.
        
        Args:
            strategy_name: Name of strategy
            strategy_fn: Strategy function (market, portfolio) -> signal or None
            market_data: List of MarketEvent objects in chronological order
            model_name: Underlying model name
            version: Strategy version
            
        Returns:
            BacktestResult with metrics and validation
        """
        logger.info(f"Running backtest: {strategy_name}")
        
        # Initialize backtester
        config = BacktestConfig(
            initial_capital=self.initial_capital,
            kelly_fraction=self.kelly_fraction,
        )
        backtester = Backtester(config=config)
        backtester.set_strategy(strategy_fn)
        
        # Simulate running through market data
        equity_curve = [self.initial_capital]
        trades = []
        dates = []
        
        for market_event in market_data:
            # Update portfolio
            current_prices = {pid: market_event.close_price 
                            for pid in backtester.portfolio.open_positions.keys()}
            backtester.portfolio.update_equity(current_prices)
            
            equity_curve.append(backtester.portfolio.current_equity)
            dates.append(market_event.timestamp)
            
            # Call strategy
            signal = strategy_fn(market_event, backtester.portfolio)
            
            if signal:
                # Create order and execute
                from .execution import ExecutionSimulator
                executor = backtester.execution
                
                # Simple order execution
                from .events import OrderEvent, OrderType, EventType
                order = OrderEvent(
                    event_type=EventType.ORDER,
                    timestamp=market_event.timestamp,
                    order_id=f"order_{len(trades)}",
                    position_id=f"pos_{len(trades)}",
                    symbol=market_event.symbol,
                    direction=signal.get('direction', Direction.LONG),
                    size=int(signal.get('size', 10)),
                    order_type=OrderType.MARKET,
                )
                
                fill, status = executor.execute_order(order, market_event)
                if fill:
                    backtester.portfolio.open_position(order.position_id, fill)
                    trades.append({
                        'entry_price': fill.fill_price,
                        'exit_price': None,
                        'pnl': 0,
                        'duration_hours': 0,
                    })
        
        # Calculate metrics
        metrics = MetricsCalculator.calculate(
            equity_curve=equity_curve,
            trades=backtester.portfolio.closed_trades,
            dates=dates,
            initial_capital=self.initial_capital,
        )
        
        # Create result
        result = BacktestResult(
            model_name=model_name,
            strategy_name=strategy_name,
            version=version,
            metrics=metrics,
            equity_curve=equity_curve,
            trades=backtester.portfolio.closed_trades,
            dates=dates,
        )
        
        # Perform DSR validation
        dsr_result = DeflatedSharpeCalculator.calculate(
            returns=[equity_curve[i] / equity_curve[i-1] - 1 for i in range(1, len(equity_curve))],
            sharpe_ratio=metrics.sharpe_ratio,
            num_strategies=self.num_strategies_tested,
        )
        result.dsr_result = dsr_result
        
        # Determine if passed validation
        result.passed_validation = (
            metrics.sharpe_ratio > 1.0 and
            metrics.max_drawdown > -0.15 and
            metrics.win_rate > 0.50 and
            dsr_result.is_significant
        )
        
        if result.passed_validation:
            result.recommendation = "PASS - Ready for paper trading"
        elif metrics.sharpe_ratio < 0.5:
            result.recommendation = "FAIL - Sharpe too low"
        elif dsr_result.p_value >= 0.05:
            result.recommendation = "FAIL - Not statistically significant"
        else:
            result.recommendation = "REVIEW - Needs investigation"
        
        self.results[strategy_name] = result
        logger.info(f"Backtest complete: {strategy_name} | Sharpe={metrics.sharpe_ratio:.2f} | DSR p={dsr_result.p_value:.4f}")
        
        return result
    
    def generate_all_reports(self, output_dir: str = "backtest_reports") -> Dict[str, str]:
        """
        Generate reports for all completed backtests.
        
        Args:
            output_dir: Directory to save reports
            
        Returns:
            Dictionary mapping strategy names to report text
        """
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        reports = {}
        
        for strategy_name, result in self.results.items():
            backtest_results = {
                "initial_capital": self.initial_capital,
                "final_equity": result.equity_curve[-1] if result.equity_curve else self.initial_capital,
                "period_start": result.dates[0].isoformat() if result.dates else "N/A",
                "period_end": result.dates[-1].isoformat() if result.dates else "N/A",
                "market_events": len(result.dates),
                "signals_generated": len(result.trades),
            }
            
            report = BacktestReportGenerator.generate_markdown(
                strategy_name=strategy_name,
                version=result.version,
                backtest_results=backtest_results,
                metrics=result.metrics,
                dsr_result=result.dsr_result,
            )
            
            reports[strategy_name] = report
            
            # Save report
            filename = f"{output_dir}/{result.model_name}_v{result.version}_{datetime.now().strftime('%Y%m%d')}.md"
            BacktestReportGenerator.save_report(report, filename)
        
        return reports
    
    def summary(self) -> str:
        """Generate summary of all results."""
        lines = [
            "# BACKTEST SUMMARY",
            "",
            "| Strategy | Sharpe | DSR | P-Value | Status |",
            "|----------|--------|-----|---------|--------|",
        ]
        
        passed = 0
        failed = 0
        
        for strategy_name, result in self.results.items():
            status = "PASS ✓" if result.passed_validation else "FAIL ✗"
            if result.passed_validation:
                passed += 1
            else:
                failed += 1
            
            lines.append(
                f"| {strategy_name:20} | {result.metrics.sharpe_ratio:6.2f} | "
                f"{result.dsr_result.deflated_sharpe_ratio:5.2f} | "
                f"{result.dsr_result.p_value:7.4f} | {status:8} |"
            )
        
        lines.append("")
        lines.append(f"**Results**: {passed} PASSED, {failed} FAILED out of {len(self.results)} total")
        
        return "\n".join(lines)

