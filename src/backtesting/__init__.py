"""
Phase 5: Backtesting & Validation Module

Event-driven backtester with anti-overfitting validation.
"""

from .events import (
    EventType, OrderType, OrderStatus, Direction,
    BaseEvent, MarketEvent, SignalEvent, OrderEvent, FillEvent, StatusEvent,
)
from .data_handler import DataHandler
from .execution import ExecutionSimulator, ExecutionConfig, SlippageModel
from .portfolio import (
    PortfolioTracker, OpenPosition, Trade, PositionStatus
)
from .backtester import Backtester, BacktestConfig
from .walk_forward import WalkForwardAnalyzer, WalkForwardPeriod, WalkForwardResult
from .metrics import PerformanceMetrics, MetricsCalculator
from .deflated_sharpe import DeflatedSharpeCalculator, DSRResult
from .cpcv import CPCVAnalyzer, CPCVFold, CPCVResult
from .report_generator import BacktestReportGenerator
from .strategy_runner import StrategyRunner, BacktestResult
from .model_strategies import (
    create_strategy,
    WaveletStrategy, HMMStrategy, LSTMStrategy, TFTStrategy,
    GeneticStrategy, EnsembleStrategy,
)

__all__ = [
    # Events
    "EventType", "OrderType", "OrderStatus", "Direction",
    "BaseEvent", "MarketEvent", "SignalEvent", "OrderEvent", "FillEvent", "StatusEvent",
    
    # Data
    "DataHandler",
    
    # Execution
    "ExecutionSimulator", "ExecutionConfig", "SlippageModel",
    
    # Portfolio
    "PortfolioTracker", "OpenPosition", "Trade", "PositionStatus",
    
    # Backtester
    "Backtester", "BacktestConfig",
    
    # Validation Framework
    "WalkForwardAnalyzer", "WalkForwardPeriod", "WalkForwardResult",
    "PerformanceMetrics", "MetricsCalculator",
    "DeflatedSharpeCalculator", "DSRResult",
    "CPCVAnalyzer", "CPCVFold", "CPCVResult",
    "BacktestReportGenerator",
    
    # Strategy Running & Model Strategies
    "StrategyRunner", "BacktestResult",
    "create_strategy",
    "WaveletStrategy", "HMMStrategy", "LSTMStrategy", "TFTStrategy",
    "GeneticStrategy", "EnsembleStrategy",
]
