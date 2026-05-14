"""
Phase 5: Unit Tests for Core Backtester

Tests for:
- Event creation and validation
- Execution simulator (slippage, commission, fills)
- Portfolio tracking (P&L, statistics)
- Data handler
"""

import pytest
from datetime import datetime, timedelta
import pytz

from src.backtesting.events import (
    EventType, MarketEvent, SignalEvent, OrderEvent, FillEvent, StatusEvent,
    Direction, OrderType, OrderStatus
)
from src.backtesting.execution import ExecutionSimulator, ExecutionConfig, SlippageModel
from src.backtesting.portfolio import PortfolioTracker, OpenPosition, Trade
from src.backtesting.data_handler import DataHandler


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def utc_now():
    """Current UTC time."""
    return datetime.now(pytz.UTC)


@pytest.fixture
def market_event(utc_now):
    """Sample market event (gold at $2000)."""
    return MarketEvent(
        event_type=EventType.MARKET,
        timestamp=utc_now,
        symbol="XAU",
        open_price=1995.0,
        high_price=2005.0,
        low_price=1990.0,
        close_price=2000.0,
        volume=100000,
        bid_price=1999.5,
        ask_price=2000.5,
        bid_volume=5000,
        ask_volume=5000,
        regime="NORMAL",
    )


@pytest.fixture
def signal_event(utc_now):
    """Sample trading signal."""
    return SignalEvent(
        event_type=EventType.SIGNAL,
        timestamp=utc_now,
        signal_id="SIG001",
        direction=Direction.LONG,
        size=100,
        entry_price=2000.0,
        trader_confidence=0.75,
        critic_confidence=0.80,
        model_name="TestModel",
    )


@pytest.fixture
def order_event(utc_now):
    """Sample order event."""
    return OrderEvent(
        event_type=EventType.ORDER,
        timestamp=utc_now,
        order_id="ORD001",
        position_id="POS001",
        symbol="XAU",
        direction=Direction.LONG,
        size=100,
        order_type=OrderType.MARKET,
        commission=1.0,
    )


@pytest.fixture
def execution_simulator():
    """Execution simulator with default config."""
    config = ExecutionConfig(
        commission_per_trade=1.0,
        commission_pct=0.0001,
        slippage_model=SlippageModel.SPREAD_BASED,
        slippage_pct=0.5,
    )
    return ExecutionSimulator(config)


@pytest.fixture
def portfolio():
    """Portfolio tracker with $100k capital."""
    return PortfolioTracker(initial_capital=100000.0)


# ============================================================================
# Event Tests
# ============================================================================

class TestMarketEvent:
    """Test MarketEvent creation and validation."""
    
    def test_create_valid_market_event(self, market_event):
        """Create valid market event."""
        assert market_event.symbol == "XAU"
        assert market_event.close_price == 2000.0
        assert market_event.bid_price < market_event.ask_price
    
    def test_market_event_spread(self, market_event):
        """Calculate bid-ask spread."""
        spread = market_event.spread
        assert spread == pytest.approx(1.0, abs=0.01)
        
        spread_bps = market_event.spread_bps
        assert spread_bps == pytest.approx(5.0, abs=0.1)  # 1.0 / 2000 * 10000
    
    def test_market_event_invalid_price(self, utc_now):
        """Reject invalid prices."""
        with pytest.raises(ValueError):
            MarketEvent(
                event_type=EventType.MARKET,
                timestamp=utc_now,
                symbol="XAU",
                open_price=-100,
                high_price=0,
                low_price=0,
                close_price=0,
                volume=0,
                bid_price=0,
                ask_price=0,
            )
    
    def test_market_event_invalid_bid_ask(self, utc_now):
        """Reject invalid bid/ask."""
        with pytest.raises(ValueError):
            MarketEvent(
                event_type=EventType.MARKET,
                timestamp=utc_now,
                symbol="XAU",
                open_price=2000,
                high_price=2000,
                low_price=2000,
                close_price=2000,
                volume=100000,
                bid_price=2001,  # Bid > Ask (invalid)
                ask_price=2000,
            )


class TestSignalEvent:
    """Test SignalEvent creation and validation."""
    
    def test_create_valid_signal(self, signal_event):
        """Create valid signal."""
        assert signal_event.signal_id == "SIG001"
        assert signal_event.direction == Direction.LONG
        assert signal_event.trader_confidence == 0.75
    
    def test_signal_confidence_property(self, signal_event):
        """Combined confidence = trader × critic."""
        expected = 0.75 * 0.80
        assert signal_event.confidence == pytest.approx(expected)
    
    def test_signal_invalid_confidence(self, utc_now):
        """Reject invalid confidence values."""
        with pytest.raises(ValueError):
            SignalEvent(
                event_type=EventType.SIGNAL,
                timestamp=utc_now,
                signal_id="SIG",
                direction=Direction.LONG,
                size=100,
                entry_price=2000.0,
                trader_confidence=1.5,  # > 1.0 (invalid)
                critic_confidence=0.8,
            )


# ============================================================================
# Execution Simulator Tests
# ============================================================================

class TestExecutionSimulator:
    """Test order execution and fill generation."""
    
    def test_execute_order_long(self, execution_simulator, order_event, market_event):
        """Execute long order."""
        fill, status = execution_simulator.execute_order(order_event, market_event)
        
        assert fill is not None
        assert fill.direction == Direction.LONG
        assert fill.size == 100
        assert fill.fill_price > market_event.ask_price  # Due to slippage
        assert fill.commission > 0
        assert fill.slippage > 0
    
    def test_execute_order_short(self, execution_simulator, market_event):
        """Execute short order."""
        order = OrderEvent(
            event_type=EventType.ORDER,
            timestamp=market_event.timestamp,
            order_id="ORD002",
            position_id="POS002",
            symbol="XAU",
            direction=Direction.SHORT,
            size=100,
        )
        
        fill, status = execution_simulator.execute_order(order, market_event)
        
        assert fill.direction == Direction.SHORT
        assert fill.fill_price < market_event.bid_price  # Due to slippage
    
    def test_slippage_spread_based(self, execution_simulator, order_event, market_event):
        """Calculate spread-based slippage."""
        fill, _ = execution_simulator.execute_order(order_event, market_event)
        
        # Slippage should be fraction of spread
        spread = market_event.spread
        expected_slippage_per_unit = spread * 0.005  # 0.5% of spread
        actual_slippage_per_unit = fill.slippage / fill.size
        
        assert actual_slippage_per_unit == pytest.approx(expected_slippage_per_unit, rel=0.1)
    
    def test_commission_calculation(self, execution_simulator, order_event, market_event):
        """Calculate commission correctly."""
        fill, _ = execution_simulator.execute_order(order_event, market_event)
        
        # Commission = flat + pct
        flat = 1.0
        notional = order_event.size * fill.fill_price
        pct_comm = notional * 0.0001
        expected = flat + pct_comm
        
        assert fill.commission == pytest.approx(expected, rel=0.01)
    
    def test_partial_fill_on_low_liquidity(self, market_event):
        """Partial fill when liquidity insufficient."""
        config = ExecutionConfig(
            max_order_pct=0.05,  # Max 5% of available
            partial_fill_enabled=True,
        )
        simulator = ExecutionSimulator(config)
        
        # Order larger than max allowed
        large_order = OrderEvent(
            event_type=EventType.ORDER,
            timestamp=market_event.timestamp,
            order_id="ORD_LARGE",
            position_id="POS_LARGE",
            symbol="XAU",
            direction=Direction.LONG,
            size=500,  # Very large
        )
        
        fill, status = simulator.execute_order(large_order, market_event)
        
        # Should be partial fill
        assert fill.size < large_order.size
        assert fill.status == OrderStatus.PARTIALLY_FILLED


# ============================================================================
# Portfolio Tests
# ============================================================================

class TestPortfolioTracker:
    """Test portfolio tracking and statistics."""
    
    def test_portfolio_initialization(self, portfolio):
        """Initialize with starting capital."""
        assert portfolio.initial_capital == 100000.0
        assert portfolio.current_equity == 100000.0
        assert portfolio.current_cash == 100000.0
        assert portfolio.current_drawdown == 0.0
    
    def test_open_position(self, portfolio, market_event):
        """Open a position."""
        fill = FillEvent(
            event_type=EventType.FILL,
            timestamp=market_event.timestamp,
            order_id="ORD001",
            position_id="POS001",
            symbol="XAU",
            direction=Direction.LONG,
            size=100,
            fill_price=2000.0,
            commission=1.0,
            slippage=0.5,
        )
        
        portfolio.open_position("POS001", fill)
        
        assert len(portfolio.open_positions) == 1
        pos = portfolio.open_positions["POS001"]
        assert pos.size == 100
        assert pos.entry_price == 2000.0
    
    def test_close_position_profit(self, portfolio, market_event):
        """Close position with profit."""
        # Open
        entry_fill = FillEvent(
            event_type=EventType.FILL,
            timestamp=market_event.timestamp,
            order_id="ORD001",
            position_id="POS001",
            symbol="XAU",
            direction=Direction.LONG,
            size=100,
            fill_price=2000.0,
            commission=1.0,
            slippage=0.5,
        )
        
        portfolio.open_position("POS001", entry_fill)
        
        # Close at profit
        exit_fill = FillEvent(
            event_type=EventType.FILL,
            timestamp=market_event.timestamp + timedelta(hours=1),
            order_id="ORD002",
            position_id="POS001",
            symbol="XAU",
            direction=Direction.SHORT,  # Closing long
            size=100,
            fill_price=2050.0,  # $50 profit
            commission=1.0,
            slippage=0.5,
        )
        
        trade = portfolio.close_position("POS001", exit_fill)
        
        assert trade is not None
        assert trade.is_winning_trade
        assert trade.pnl > 0
        assert len(portfolio.closed_trades) == 1
    
    def test_portfolio_statistics(self, portfolio, market_event):
        """Calculate portfolio statistics correctly."""
        # Execute 3 trades: win, win, loss
        timestamps = [
            market_event.timestamp,
            market_event.timestamp + timedelta(hours=1),
            market_event.timestamp + timedelta(hours=2),
        ]
        
        prices = [2050.0, 2100.0, 1950.0]  # Profit $50, $100, Loss $50
        
        for i, (price, ts) in enumerate(zip(prices, timestamps)):
            # Open
            entry_fill = FillEvent(
                event_type=EventType.FILL,
                timestamp=ts,
                order_id=f"ORD_OPEN_{i}",
                position_id=f"POS_{i}",
                symbol="XAU",
                direction=Direction.LONG,
                size=100,
                fill_price=2000.0,
                commission=1.0,
                slippage=0.0,
            )
            
            portfolio.open_position(f"POS_{i}", entry_fill)
            
            # Close
            exit_fill = FillEvent(
                event_type=EventType.FILL,
                timestamp=ts + timedelta(hours=0.5),
                order_id=f"ORD_CLOSE_{i}",
                position_id=f"POS_{i}",
                symbol="XAU",
                direction=Direction.SHORT,
                size=100,
                fill_price=price,
                commission=1.0,
                slippage=0.0,
            )
            
            portfolio.close_position(f"POS_{i}", exit_fill)
        
        # Check statistics: 2 wins (50 + 100 = 150 profit), 1 loss (50 loss)
        assert portfolio.total_trades == 3
        assert portfolio.winning_trades == 2
        assert portfolio.losing_trades == 1
        assert portfolio.win_rate == pytest.approx(2/3)
        assert portfolio.profit_factor > 1.0


# ============================================================================
# Integration Tests
# ============================================================================

class TestBacktesterIntegration:
    """Integration tests for complete backtest flow."""
    
    def test_data_handler_generates_data(self):
        """Data handler can generate mock data."""
        handler = DataHandler()
        
        start = datetime.now(pytz.UTC)
        end = start + timedelta(days=5)
        
        events = list(handler.load_data(start, end))
        
        assert len(events) >= 5
        assert all(isinstance(e, MarketEvent) for e in events)
        
        # Check chronological order
        for i in range(len(events) - 1):
            assert events[i].timestamp <= events[i+1].timestamp


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
