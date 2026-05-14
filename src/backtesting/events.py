"""
Phase 5: Event-Driven Backtester - Event Definitions

This module defines all event types used in the backtesting system:
- MarketEvent: New market data (OHLCV + bid/ask)
- SignalEvent: Trading signal from strategy
- OrderEvent: Order placement request
- FillEvent: Actual execution fill
- StatusEvent: Informational events (errors, warnings)

Events are processed in strict chronological order to prevent lookahead bias.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class EventType(Enum):
    """Event type enumeration."""
    MARKET = "MARKET"      # Historical OHLCV bar arrived
    SIGNAL = "SIGNAL"      # Trading signal generated
    ORDER = "ORDER"        # Order placed
    FILL = "FILL"          # Order filled
    STATUS = "STATUS"      # Informational event


class OrderType(Enum):
    """Order type enumeration."""
    MARKET = "MARKET"      # Immediate execution
    LIMIT = "LIMIT"        # Execute at price or better
    STOP = "STOP"          # Execute if price crosses stop


class OrderStatus(Enum):
    """Order status enumeration."""
    PENDING = "PENDING"    # Awaiting fill
    FILLED = "FILLED"      # Fully filled
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    REJECTED = "REJECTED"  # Insufficient liquidity or risk
    CANCELLED = "CANCELLED"


class Direction(Enum):
    """Trade direction."""
    LONG = 1               # Buy / go long
    SHORT = -1             # Sell / go short
    FLAT = 0               # No position


@dataclass
class BaseEvent:
    """Base event class (abstract)."""
    event_type: EventType
    timestamp: datetime

    def __post_init__(self):
        """Validate timestamp is timezone-aware."""
        if self.timestamp.tzinfo is None:
            raise ValueError("Event timestamp must be timezone-aware")


@dataclass
class MarketEvent(BaseEvent):
    """
    Market event: New OHLCV bar with bid/ask quotes.
    
    This event is generated when a new bar (candle) arrives from the historical data feed.
    All backtester logic processes market events in chronological order.
    """
    symbol: str                    # 'XAU' for gold
    open_price: float             # Opening price
    high_price: float             # High price
    low_price: float              # Low price
    close_price: float            # Closing price
    volume: int                   # Volume in oz
    bid_price: float              # Bid quote
    ask_price: float              # Ask quote
    bid_volume: int = 1000        # Bid liquidity (oz)
    ask_volume: int = 1000        # Ask liquidity (oz)
    regime: str = "NORMAL"        # Market regime (NORMAL, GROWTH, CRISIS)

    def __post_init__(self):
        super().__post_init__()
        if self.close_price <= 0:
            raise ValueError("Price must be positive")
        if self.bid_price > self.ask_price:
            raise ValueError("Bid price cannot exceed ask price")

    @property
    def spread(self) -> float:
        """Bid-ask spread in dollars."""
        return self.ask_price - self.bid_price

    @property
    def spread_bps(self) -> float:
        """Bid-ask spread in basis points."""
        return (self.spread / self.close_price) * 10000


@dataclass
class SignalEvent(BaseEvent):
    """
    Signal event: Trading signal from strategy.
    
    A signal is generated when the strategy determines an entry opportunity.
    The signal contains direction, confidence, and raw model scores.
    Note: This signal does NOT guarantee execution (risk manager may reject).
    """
    signal_id: str                # Unique signal identifier
    direction: Direction          # Long (1), Short (-1), or Flat (0)
    size: int                     # Position size (oz for gold)
    entry_price: float            # Recommended entry price
    
    # Confidence scores from models
    trader_confidence: float      # Main model confidence [0.0-1.0]
    critic_confidence: float      # Critic model approval [0.0-1.0]
    raw_scores: dict = field(default_factory=dict)  # Raw model outputs
    
    # Optional metadata
    model_name: str = ""          # Name of model generating signal
    reasoning: str = ""           # Brief explanation

    def __post_init__(self):
        super().__post_init__()
        if not (0.0 <= self.trader_confidence <= 1.0):
            raise ValueError("Trader confidence must be in [0, 1]")
        if not (0.0 <= self.critic_confidence <= 1.0):
            raise ValueError("Critic confidence must be in [0, 1]")
        if self.size <= 0:
            raise ValueError("Position size must be positive")
        if self.entry_price <= 0:
            raise ValueError("Entry price must be positive")

    @property
    def confidence(self) -> float:
        """Combined confidence score: trader × critic."""
        return self.trader_confidence * self.critic_confidence


@dataclass
class OrderEvent(BaseEvent):
    """
    Order event: Request to place an order.
    
    Created by position manager after risk checks (Kelly sizing, circuit breakers).
    Contains order details: symbol, side, size, type, and prices.
    """
    order_id: str                 # Unique order identifier
    position_id: str              # Associated position ID
    symbol: str                   # 'XAU'
    direction: Direction          # Long or Short
    size: int                     # Order size (oz)
    order_type: OrderType = OrderType.MARKET  # Market, Limit, or Stop
    limit_price: Optional[float] = None       # Limit price if applicable
    stop_price: Optional[float] = None        # Stop price if applicable
    commission: float = 1.0       # Expected commission ($)
    kelly_fraction: float = 0.5   # Kelly fraction used for sizing
    reason: str = ""              # Why order was generated

    def __post_init__(self):
        super().__post_init__()
        if self.size <= 0:
            raise ValueError("Order size must be positive")
        if self.limit_price is not None and self.limit_price <= 0:
            raise ValueError("Limit price must be positive")
        if self.stop_price is not None and self.stop_price <= 0:
            raise ValueError("Stop price must be positive")


@dataclass
class FillEvent(BaseEvent):
    """
    Fill event: Order execution confirmation.
    
    Generated by execution simulator after realistic slippage/commission calculation.
    Contains actual execution price, slippage, and commission paid.
    """
    order_id: str                 # Matches OrderEvent.order_id
    position_id: str              # Position filled
    symbol: str                   # 'XAU'
    direction: Direction          # Long or Short
    size: int                     # Actual filled size (oz) - may be less than order if partial
    fill_price: float             # Actual execution price
    commission: float             # Commission paid ($)
    slippage: float = 0.0         # Slippage cost ($)
    fill_type: str = "MARKET"     # 'MARKET', 'LIMIT', or 'STOP'
    status: OrderStatus = OrderStatus.FILLED

    def __post_init__(self):
        super().__post_init__()
        if self.size <= 0:
            raise ValueError("Fill size must be positive")
        if self.fill_price <= 0:
            raise ValueError("Fill price must be positive")
        if self.commission < 0:
            raise ValueError("Commission cannot be negative")
        if self.slippage < 0:
            raise ValueError("Slippage cannot be negative")

    @property
    def total_cost(self) -> float:
        """Total transaction cost: slippage + commission."""
        return self.slippage + self.commission

    @property
    def effective_price(self) -> float:
        """Effective price including all costs."""
        if self.direction == Direction.LONG:
            return self.fill_price + (self.total_cost / self.size)
        else:
            return self.fill_price - (self.total_cost / self.size)


@dataclass
class StatusEvent(BaseEvent):
    """
    Status event: Informational message (warnings, errors, etc.).
    
    Used for logging important events like circuit breaker triggers,
    risk manager rejections, data issues, etc.
    """
    status_type: str              # 'INFO', 'WARNING', 'ERROR'
    message: str                  # Human-readable message
    details: dict = field(default_factory=dict)  # Additional context

    def __post_init__(self):
        super().__post_init__()
        valid_types = ['INFO', 'WARNING', 'ERROR']
        if self.status_type not in valid_types:
            raise ValueError(f"Status type must be one of {valid_types}")
