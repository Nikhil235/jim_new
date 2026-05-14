"""
Phase 5: Backtester - Realistic Execution Simulator

This module simulates realistic order execution with:
- Bid-ask spread slippage
- Commission calculations
- Latency simulation
- Partial fill handling
- Liquidity constraints

This is critical for realistic backtesting - without proper execution simulation,
backtest results will be overly optimistic.
"""

import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Tuple
from enum import Enum

from loguru import logger

from .events import (
    MarketEvent, OrderEvent, FillEvent, StatusEvent,
    Direction, OrderType, OrderStatus, EventType
)


class SlippageModel(Enum):
    """Slippage model types."""
    FIXED = "fixed"           # Fixed slippage in dollars
    SPREAD_BASED = "spread"   # Based on bid-ask spread
    MARKET_IMPACT = "impact"  # Based on order size vs liquidity


@dataclass
class ExecutionConfig:
    """Execution simulator configuration."""
    # Commission model
    commission_per_trade: float = 1.0   # $ per trade (flat)
    commission_pct: float = 0.0001       # % of order value (0.01 basis points)
    
    # Slippage model
    slippage_model: SlippageModel = SlippageModel.SPREAD_BASED
    slippage_pct: float = 0.5            # % of spread (0.5 = half spread)
    fixed_slippage: float = 0.0          # Fixed slippage if FIXED model
    
    # Latency
    latency_ms_mean: float = 100         # Mean latency (ms)
    latency_ms_std: float = 30           # Std dev latency (ms)
    
    # Liquidity
    max_order_pct: float = 0.10          # Max 10% of bid/ask volume
    partial_fill_enabled: bool = True    # Allow partial fills


class ExecutionSimulator:
    """
    Simulates realistic order execution.
    
    Key features:
    - Slippage calculated from bid-ask spread
    - Commission based on trade size and value
    - Latency between signal and actual fill
    - Partial fills when liquidity insufficient
    - Realistic fills prevent overfitting to backtest data
    """

    def __init__(self, config: Optional[ExecutionConfig] = None):
        """Initialize execution simulator."""
        self.config = config or ExecutionConfig()
        logger.info(f"Execution simulator initialized with {self.config.slippage_model.value} slippage model")

    def execute_order(
        self,
        order: OrderEvent,
        market: MarketEvent,
    ) -> Tuple[FillEvent, Optional[StatusEvent]]:
        """
        Execute an order against current market conditions.
        
        Returns:
            Tuple of (FillEvent, StatusEvent or None)
            StatusEvent is set if order was rejected/modified
        """
        # Check liquidity constraints
        status = self._check_liquidity(order, market)
        if status:
            return None, status
        
        # Calculate execution price with slippage
        fill_price, slippage = self._calculate_fill_price(order, market)
        
        # Calculate commission
        commission = self._calculate_commission(order, fill_price)
        
        # Calculate latency
        latency = self._calculate_latency()
        
        # Determine fill size (may be partial)
        fill_size = self._calculate_fill_size(order, market)
        
        # Create fill event
        fill = FillEvent(
            event_type=EventType.FILL,
            timestamp=market.timestamp + timedelta(milliseconds=latency),
            order_id=order.order_id,
            position_id=order.position_id,
            symbol=order.symbol,
            direction=order.direction,
            size=fill_size,
            fill_price=fill_price,
            commission=commission,
            slippage=slippage,
            fill_type=order.order_type.value,
            status=OrderStatus.FILLED if fill_size == order.size else OrderStatus.PARTIALLY_FILLED,
        )
        
        # Log execution
        if fill_size < order.size:
            logger.warning(
                f"Partial fill: {fill_size}/{order.size} oz at ${fill_price:.2f} "
                f"(slippage: ${slippage:.2f}, commission: ${commission:.2f})"
            )
        else:
            logger.debug(
                f"Order filled: {fill_size} oz at ${fill_price:.2f} "
                f"(slippage: ${slippage:.2f}, commission: ${commission:.2f})"
            )
        
        return fill, None

    def _check_liquidity(
        self,
        order: OrderEvent,
        market: MarketEvent,
    ) -> Optional[StatusEvent]:
        """Check if order can be filled with available liquidity."""
        available_volume = market.bid_volume if order.direction == Direction.LONG else market.ask_volume
        
        # Check max order size constraint
        max_order_size = int(available_volume * self.config.max_order_pct)
        
        if order.size > max_order_size:
            if not self.config.partial_fill_enabled:
                # Reject order
                return StatusEvent(
                    event_type=EventType.STATUS,
                    timestamp=market.timestamp,
                    status_type="WARNING",
                    message=f"Order rejected: insufficient liquidity",
                    details={
                        "requested": order.size,
                        "available": max_order_size,
                        "reason": "Order size exceeds 10% of available volume",
                    }
                )
        
        return None

    def _calculate_fill_price(
        self,
        order: OrderEvent,
        market: MarketEvent,
    ) -> Tuple[float, float]:
        """Calculate fill price and slippage cost."""
        if order.direction == Direction.LONG:
            # Buy: use ask price
            base_price = market.ask_price
        else:
            # Sell: use bid price
            base_price = market.bid_price
        
        # Calculate slippage
        slippage_amount = self._calculate_slippage_amount(order, market)
        
        # Adjust price based on direction
        if order.direction == Direction.LONG:
            fill_price = base_price + slippage_amount
        else:
            fill_price = base_price - slippage_amount
        
        return fill_price, slippage_amount * order.size

    def _calculate_slippage_amount(
        self,
        order: OrderEvent,
        market: MarketEvent,
    ) -> float:
        """Calculate slippage per unit."""
        if self.config.slippage_model == SlippageModel.FIXED:
            # Fixed slippage
            return self.config.fixed_slippage
        
        elif self.config.slippage_model == SlippageModel.SPREAD_BASED:
            # Slippage is a % of bid-ask spread
            spread = market.spread
            return spread * (self.config.slippage_pct / 100)
        
        elif self.config.slippage_model == SlippageModel.MARKET_IMPACT:
            # Slippage based on order size relative to liquidity
            available_volume = market.bid_volume if order.direction == Direction.LONG else market.ask_volume
            order_pct = order.size / available_volume
            
            # Impact increases with order size: impact = spread * order_pct
            spread = market.spread
            return spread * order_pct * (self.config.slippage_pct / 100)
        
        else:
            return 0.0

    def _calculate_commission(
        self,
        order: OrderEvent,
        fill_price: float,
    ) -> float:
        """Calculate total commission."""
        # Flat commission per trade
        flat_comm = self.config.commission_per_trade
        
        # Percentage-based commission
        notional = order.size * fill_price
        pct_comm = notional * self.config.commission_pct
        
        return flat_comm + pct_comm

    def _calculate_latency(self) -> float:
        """Simulate order latency (milliseconds)."""
        # Normal distribution: mean ~100ms, std ~30ms
        latency = random.gauss(
            self.config.latency_ms_mean,
            self.config.latency_ms_std,
        )
        # Ensure non-negative
        return max(0, latency)

    def _calculate_fill_size(
        self,
        order: OrderEvent,
        market: MarketEvent,
    ) -> int:
        """Calculate actual fill size (may be less than order due to liquidity)."""
        available_volume = market.bid_volume if order.direction == Direction.LONG else market.ask_volume
        max_order_size = int(available_volume * self.config.max_order_pct)
        
        if order.size <= max_order_size:
            return order.size
        
        if self.config.partial_fill_enabled:
            # Partial fill at max available
            return max_order_size
        else:
            # This shouldn't happen if liquidity check passed
            return 0

    def simulate_market_impact(
        self,
        order_size: int,
        available_liquidity: int,
        spread: float,
    ) -> float:
        """
        Calculate market impact of large orders.
        
        For backtesting, we use a simplified model:
        impact = spread * (order_size / available_liquidity)
        """
        impact = spread * (order_size / available_liquidity)
        return impact
