"""Paper trading package - Real-time trading simulation."""

from .engine import (
    PaperTradingEngine,
    PaperTradingConfig,
    TradeExecution,
    ModelSignal,
    PortfolioSnapshot,
    SignalType,
    TradeStatus,
)

from .dynamic_weights import (
    DynamicWeightAdjuster,
    get_weight_adjuster,
    REGIME_BASE_WEIGHTS,
)

__all__ = [
    "PaperTradingEngine",
    "PaperTradingConfig",
    "TradeExecution",
    "ModelSignal",
    "PortfolioSnapshot",
    "SignalType",
    "TradeStatus",
    "DynamicWeightAdjuster",
    "get_weight_adjuster",
    "REGIME_BASE_WEIGHTS",
]
