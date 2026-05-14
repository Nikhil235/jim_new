"""
Unit Tests: Position Manager
=============================
Tests position lifecycle management.
"""

import pytest
from datetime import datetime, timedelta
from src.risk.position_manager import (
    PositionManager,
    Position,
    ExecutionSignal,
)


class TestPositionManager:
    """Test suite for PositionManager."""

    @pytest.fixture
    def manager(self):
        """Create a PositionManager instance."""
        config = {
            "position_manager": {
                "max_positions": 5,
                "max_position_days": 10,
                "trailing_stop_pct": 0.02,
                "time_stop_hours": 24,
                "profit_target_pct": 0.05,
            }
        }
        return PositionManager(config)

    def test_initialization(self, manager):
        """Test PositionManager initialization."""
        assert manager.max_positions == 5
        assert manager.max_position_days == 10
        assert manager.trailing_stop_pct == 0.02
        assert manager.time_stop_hours == 24
        assert manager.profit_target_pct == 0.05
        assert len(manager.positions) == 0
        assert len(manager.closed_positions) == 0

    def test_open_position_long(self, manager):
        """Test opening a long position."""
        signal = manager.open_position(
            direction=1,
            size=100,
            entry_price=2000,
            trader_confidence=0.75,
            critic_confidence=0.72,
            kelly_fraction=0.02,
            reason="Test long entry",
        )
        
        assert signal.approved == True
        assert signal.direction == 1
        assert signal.size == 100
        assert len(manager.positions) == 1

    def test_open_position_short(self, manager):
        """Test opening a short position."""
        signal = manager.open_position(
            direction=-1,
            size=50,
            entry_price=2000,
            trader_confidence=0.80,
            critic_confidence=0.78,
            kelly_fraction=0.015,
            reason="Test short entry",
        )
        
        assert signal.approved == True
        assert signal.direction == -1
        assert signal.size == 50

    def test_open_position_max_limit(self, manager):
        """Test max positions limit."""
        # Open max_positions
        for i in range(manager.max_positions):
            signal = manager.open_position(
                direction=1,
                size=10 + i,
                entry_price=2000,
                trader_confidence=0.75,
                critic_confidence=0.72,
                kelly_fraction=0.01,
                reason=f"Position {i}",
            )
            assert signal.approved == True

        # Try to exceed limit
        signal_excess = manager.open_position(
            direction=1,
            size=100,
            entry_price=2000,
            trader_confidence=0.75,
            critic_confidence=0.72,
            kelly_fraction=0.01,
            reason="Should fail",
        )
        
        assert signal_excess.approved == False

    def test_position_ids_unique(self, manager):
        """Test that position IDs are unique."""
        ids = []
        for i in range(3):
            signal = manager.open_position(
                direction=1,
                size=10,
                entry_price=2000,
                trader_confidence=0.75,
                critic_confidence=0.72,
                kelly_fraction=0.01,
            )
            ids.append(signal.position_id)
        
        assert len(set(ids)) == 3  # All unique

    def test_update_position_profit(self, manager):
        """Test position update with profit."""
        signal = manager.open_position(
            direction=1,
            size=100,
            entry_price=2000,
            trader_confidence=0.75,
            critic_confidence=0.72,
            kelly_fraction=0.02,
        )
        
        # Price goes up (but not to target)
        exit_condition = manager.update_position(signal.position_id, 2020)
        
        assert exit_condition is None  # No exit condition yet
        
        pos = manager.positions[0]
        assert pos.pnl == 2000  # 100 units × $20 profit
        assert pos.pnl_pct > 0

    def test_update_position_loss(self, manager):
        """Test position update with loss."""
        signal = manager.open_position(
            direction=1,
            size=100,
            entry_price=2000,
            trader_confidence=0.75,
            critic_confidence=0.72,
            kelly_fraction=0.02,
        )
        
        # Price goes down slightly (but above trailing stop)
        exit_condition = manager.update_position(signal.position_id, 1990)
        
        assert exit_condition is None  # No exit yet (stop is at 1960)
        
        pos = manager.positions[0]
        assert pos.pnl == -1000  # 100 units × -$10 loss
        assert pos.pnl_pct < 0

    def test_trailing_stop_long(self, manager):
        """Test trailing stop on long position."""
        signal = manager.open_position(
            direction=1,
            size=100,
            entry_price=2000,
            trader_confidence=0.75,
            critic_confidence=0.72,
            kelly_fraction=0.02,
        )
        
        pos_id = signal.position_id
        pos = manager.positions[0]
        
        # Price goes up to 2100
        manager.update_position(pos_id, 2100)
        expected_stop = 2100 * (1 - manager.trailing_stop_pct)  # 2058
        assert pos.trailing_stop_price == expected_stop
        
        # Price goes up more to 2150
        manager.update_position(pos_id, 2150)
        expected_stop_2 = 2150 * (1 - manager.trailing_stop_pct)  # 2107
        assert pos.trailing_stop_price == expected_stop_2

    def test_trailing_stop_hit_long(self, manager):
        """Test trailing stop triggers on long position."""
        signal = manager.open_position(
            direction=1,
            size=100,
            entry_price=2000,
            trader_confidence=0.75,
            critic_confidence=0.72,
            kelly_fraction=0.02,
        )
        
        pos_id = signal.position_id
        
        # Price goes up then down below stop
        manager.update_position(pos_id, 2100)  # Trailing stop set
        exit_cond = manager.update_position(pos_id, 2050)  # Below stop
        
        assert exit_cond is not None
        assert exit_cond[0] == "trailing_stop_hit"

    def test_profit_target_long(self, manager):
        """Test profit target triggers."""
        signal = manager.open_position(
            direction=1,
            size=100,
            entry_price=2000,
            trader_confidence=0.75,
            critic_confidence=0.72,
            kelly_fraction=0.02,
        )
        
        pos_id = signal.position_id
        pos = manager.positions[0]
        
        # Check target price set correctly
        expected_target = 2000 * (1 + manager.profit_target_pct)  # 2100
        assert pos.target_price == expected_target
        
        # Price hits target
        exit_cond = manager.update_position(pos_id, 2100)
        
        assert exit_cond is not None
        assert exit_cond[0] == "profit_target_hit"

    def test_time_stop(self, manager):
        """Test time-based position exit."""
        signal = manager.open_position(
            direction=1,
            size=100,
            entry_price=2000,
            trader_confidence=0.75,
            critic_confidence=0.72,
            kelly_fraction=0.02,
        )
        
        pos_id = signal.position_id
        pos = manager.positions[0]
        
        # Manually set entry time to 25 hours ago
        pos.entry_time = datetime.utcnow() - timedelta(hours=25)
        
        # Update position
        exit_cond = manager.update_position(pos_id, 2050)
        
        assert exit_cond is not None
        assert exit_cond[0] == "time_stop_hit"

    def test_close_position(self, manager):
        """Test closing a position."""
        signal = manager.open_position(
            direction=1,
            size=100,
            entry_price=2000,
            trader_confidence=0.75,
            critic_confidence=0.72,
            kelly_fraction=0.02,
        )
        
        pos_id = signal.position_id
        
        # Update P&L first
        manager.update_position(pos_id, 2050)
        
        # Close position
        closed_pos = manager.close_position(pos_id, 2050, reason="Test close")
        
        assert closed_pos is not None
        assert closed_pos.status == "CLOSED"
        assert closed_pos.pnl == 5000  # 100 × 50
        assert len(manager.positions) == 0
        assert len(manager.closed_positions) == 1

    def test_close_position_not_found(self, manager):
        """Test closing non-existent position."""
        closed_pos = manager.close_position("POS_99999", 2000)
        
        assert closed_pos is None

    def test_short_position_trailing_stop(self, manager):
        """Test trailing stop on short position."""
        signal = manager.open_position(
            direction=-1,
            size=100,
            entry_price=2000,
            trader_confidence=0.75,
            critic_confidence=0.72,
            kelly_fraction=0.02,
        )
        
        pos_id = signal.position_id
        pos = manager.positions[0]
        
        # For short: stop should be above entry
        expected_initial_stop = 2000 * (1 + manager.trailing_stop_pct)
        assert pos.trailing_stop_price == expected_initial_stop
        
        # Price goes down (good for short)
        manager.update_position(pos_id, 1950)
        expected_stop_2 = 1950 * (1 + manager.trailing_stop_pct)
        assert pos.trailing_stop_price == expected_stop_2

    def test_get_position_stats(self, manager):
        """Test position statistics."""
        # Open and close a profitable trade
        signal = manager.open_position(
            direction=1,
            size=100,
            entry_price=2000,
            trader_confidence=0.75,
            critic_confidence=0.72,
            kelly_fraction=0.02,
        )
        
        manager.close_position(signal.position_id, 2050, reason="Test profit")
        
        stats = manager.get_position_stats()
        
        assert stats["total_closed"] == 1
        assert stats["win_rate"] == 1.0  # 100% win rate
        assert stats["total_pnl"] == 5000
        assert stats["open_positions"] == 0

    def test_win_rate_calculation(self, manager):
        """Test win rate calculation."""
        # Open and close 3 trades: 2 wins, 1 loss
        for i, exit_price in enumerate([2050, 2100, 1950]):  # 2 wins, 1 loss
            signal = manager.open_position(
                direction=1,
                size=100,
                entry_price=2000,
                trader_confidence=0.75,
                critic_confidence=0.72,
                kelly_fraction=0.02,
            )
            
            manager.close_position(signal.position_id, exit_price)
        
        stats = manager.get_position_stats()
        
        assert stats["total_closed"] == 3
        assert stats["win_rate"] == 2/3
        assert stats["total_pnl"] == 5000 + 10000 - 5000

    def test_profit_factor(self, manager):
        """Test profit factor calculation."""
        # Open/close: +1000, +2000, -500 → PF = (1000+2000)/500 = 6
        exit_prices = [2005, 2010, 1997.5]
        
        for exit_price in exit_prices:
            signal = manager.open_position(
                direction=1,
                size=100,
                entry_price=2000,
                trader_confidence=0.75,
                critic_confidence=0.72,
                kelly_fraction=0.02,
            )
            
            manager.close_position(signal.position_id, exit_price)
        
        stats = manager.get_position_stats()
        
        assert stats["total_closed"] == 3
        expected_pf = 3000 / 500  # 6
        assert abs(stats["profit_factor"] - expected_pf) < 0.1


class TestPosition:
    """Test Position dataclass."""

    def test_creation(self):
        """Test Position creation."""
        pos = Position(
            position_id="POS_00001",
            direction=1,
            size=100,
            entry_price=2000,
            entry_time=datetime.utcnow(),
        )
        
        assert pos.position_id == "POS_00001"
        assert pos.direction == 1
        assert pos.size == 100
        assert pos.status == "OPEN"
        assert pos.pnl == 0.0


class TestExecutionSignal:
    """Test ExecutionSignal dataclass."""

    def test_approval(self):
        """Test ExecutionSignal approval."""
        signal = ExecutionSignal(
            position_id="POS_00001",
            direction=1,
            size=100,
            entry_price=2000,
            reason="Test",
            trader_confidence=0.75,
            critic_confidence=0.72,
            kelly_fraction=0.02,
            approved=True,
        )
        
        assert signal.approved == True

    def test_rejection(self):
        """Test ExecutionSignal rejection."""
        signal = ExecutionSignal(
            position_id="",
            direction=1,
            size=100,
            entry_price=2000,
            reason="Max positions reached",
            trader_confidence=0.75,
            critic_confidence=0.72,
            kelly_fraction=0.02,
            approved=False,
        )
        
        assert signal.approved == False
