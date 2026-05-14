"""
Unit Tests: Meta-Labeler (Critic Model)
========================================
Tests the two-model system's Critic component.
"""

import pytest
import numpy as np
from src.risk.meta_labeler import (
    MetaLabeler,
    TraderSignal,
    CriticInput,
)


class TestMetaLabeler:
    """Test suite for MetaLabeler class."""

    @pytest.fixture
    def labeler(self):
        """Create a MetaLabeler instance."""
        return MetaLabeler(threshold=0.65)

    @pytest.fixture
    def trader_signal(self):
        """Create a sample TraderSignal."""
        return TraderSignal(
            direction=1,
            confidence=0.75,
            raw_scores={"model_a": 0.8, "model_b": 0.7},
        )

    @pytest.fixture
    def critic_input(self):
        """Create a sample CriticInput."""
        return CriticInput(
            trader_signal=1,
            trader_confidence=0.75,
            trader_raw_scores=np.array([0.8, 0.7]),
            current_regime="NORMAL",
            regime_probability=0.85,
            volatility=1.2,
            spread_pct=0.0015,
            hour_of_day=10,
            day_of_week=2,
            trader_recent_accuracy=0.55,
            trader_recent_profit_factor=1.2,
            regime_in_sample_accuracy=0.58,
            liquidity_score=0.8,
        )

    def test_initialization(self, labeler):
        """Test MetaLabeler initialization."""
        assert labeler.threshold == 0.65
        assert labeler.is_trained == False
        assert labeler.use_gpu == False

    def test_should_trade_untrained_fallback(self, labeler, trader_signal, critic_input):
        """Test fallback behavior when model not trained."""
        # Should use trader confidence when not trained
        execute, confidence = labeler.should_trade(trader_signal, critic_input)
        
        # Trader confidence (0.75) > threshold (0.65) → execute
        assert execute == True
        assert confidence == trader_signal.confidence

    def test_build_features(self, labeler, trader_signal, critic_input):
        """Test feature vector construction."""
        features = labeler._build_features(trader_signal, critic_input)
        
        # Should have 14 features
        assert len(features) == 14
        assert features.dtype == np.float32

    def test_regime_to_numeric(self):
        """Test regime encoding."""
        assert MetaLabeler._regime_to_numeric("GROWTH") == 1.0
        assert MetaLabeler._regime_to_numeric("NORMAL") == 0.0
        assert MetaLabeler._regime_to_numeric("CRISIS") == -1.0
        assert MetaLabeler._regime_to_numeric("UNKNOWN") == 0.0

    def test_threshold_effect(self, trader_signal, critic_input):
        """Test different thresholds affect decision."""
        labeler_high = MetaLabeler(threshold=0.99)
        labeler_low = MetaLabeler(threshold=0.01)
        
        execute_high, _ = labeler_high.should_trade(trader_signal, critic_input)
        execute_low, _ = labeler_low.should_trade(trader_signal, critic_input)
        
        # High threshold should require higher confidence
        # Both fall back to trader confidence in untrained state
        assert execute_low == True  # 0.75 > 0.01
        assert execute_high == False  # 0.75 < 0.99

    def test_regime_variations(self, labeler, trader_signal):
        """Test with different regimes."""
        regimes = ["GROWTH", "NORMAL", "CRISIS"]
        
        for regime in regimes:
            critic_input = CriticInput(
                trader_signal=1,
                trader_confidence=0.75,
                trader_raw_scores=np.array([0.8, 0.7]),
                current_regime=regime,
                regime_probability=0.85,
                volatility=1.2,
                spread_pct=0.0015,
                hour_of_day=10,
                day_of_week=2,
                trader_recent_accuracy=0.55,
                trader_recent_profit_factor=1.2,
                regime_in_sample_accuracy=0.58,
                liquidity_score=0.8,
            )
            
            execute, confidence = labeler.should_trade(trader_signal, critic_input)
            assert isinstance(execute, (bool, np.bool_))
            assert 0 <= confidence <= 1

    def test_temporal_features(self, labeler, trader_signal):
        """Test temporal encoding (hour + day of week)."""
        for hour in [0, 6, 12, 18, 23]:
            for dow in [0, 3, 6]:
                critic_input = CriticInput(
                    trader_signal=1,
                    trader_confidence=0.75,
                    trader_raw_scores=np.array([0.8, 0.7]),
                    current_regime="NORMAL",
                    regime_probability=0.85,
                    volatility=1.2,
                    spread_pct=0.0015,
                    hour_of_day=hour,
                    day_of_week=dow,
                    trader_recent_accuracy=0.55,
                    trader_recent_profit_factor=1.2,
                    regime_in_sample_accuracy=0.58,
                    liquidity_score=0.8,
                )
                
                execute, confidence = labeler.should_trade(trader_signal, critic_input)
                assert isinstance(execute, bool)

    def test_trader_signal_variations(self, labeler, critic_input):
        """Test with different trader signals."""
        for direction in [-1, 0, 1]:
            for confidence in [0.3, 0.5, 0.75, 0.95]:
                signal = TraderSignal(
                    direction=direction,
                    confidence=confidence,
                    raw_scores={"model_a": 0.5},
                )
                
                execute, critic_conf = labeler.should_trade(signal, critic_input)
                assert isinstance(execute, (bool, np.bool_))
                assert 0 <= critic_conf <= 1

    def test_low_accuracy_trader(self, labeler, trader_signal):
        """Test when trader has low recent accuracy."""
        critic_input = CriticInput(
            trader_signal=1,
            trader_confidence=0.75,
            trader_raw_scores=np.array([0.8, 0.7]),
            current_regime="NORMAL",
            regime_probability=0.85,
            volatility=1.2,
            spread_pct=0.0015,
            hour_of_day=10,
            day_of_week=2,
            trader_recent_accuracy=0.40,  # Low accuracy
            trader_recent_profit_factor=0.5,  # Bad profit factor
            regime_in_sample_accuracy=0.45,
            liquidity_score=0.3,  # Low liquidity
        )
        
        execute, confidence = labeler.should_trade(trader_signal, critic_input)
        # Still uses trader confidence since model not trained
        assert execute == True

    def test_crisis_regime(self, labeler, trader_signal):
        """Test in crisis regime."""
        critic_input = CriticInput(
            trader_signal=1,
            trader_confidence=0.75,
            trader_raw_scores=np.array([0.8, 0.7]),
            current_regime="CRISIS",
            regime_probability=0.95,  # High certainty of crisis
            volatility=3.5,  # High volatility
            spread_pct=0.005,  # Wide spread
            hour_of_day=10,
            day_of_week=2,
            trader_recent_accuracy=0.50,
            trader_recent_profit_factor=0.8,
            regime_in_sample_accuracy=0.45,  # Low accuracy in crisis
            liquidity_score=0.4,  # Low liquidity
        )
        
        execute, confidence = labeler.should_trade(trader_signal, critic_input)
        assert isinstance(execute, bool)


class TestTraderSignal:
    """Test TraderSignal dataclass."""

    def test_creation(self):
        """Test TraderSignal creation."""
        signal = TraderSignal(
            direction=1,
            confidence=0.85,
            raw_scores={"model_a": 0.8, "model_b": 0.9},
        )
        
        assert signal.direction == 1
        assert signal.confidence == 0.85
        assert signal.raw_scores["model_a"] == 0.8

    def test_invalid_direction(self):
        """Test invalid direction values."""
        # Should not validate — dataclass is flexible
        signal = TraderSignal(
            direction=2,  # Invalid but allowed
            confidence=0.5,
            raw_scores={},
        )
        assert signal.direction == 2


class TestCriticInput:
    """Test CriticInput dataclass."""

    def test_creation(self):
        """Test CriticInput creation."""
        input_data = CriticInput(
            trader_signal=1,
            trader_confidence=0.75,
            trader_raw_scores=np.array([0.8, 0.7]),
            current_regime="NORMAL",
            regime_probability=0.85,
            volatility=1.2,
            spread_pct=0.0015,
            hour_of_day=10,
            day_of_week=2,
            trader_recent_accuracy=0.55,
            trader_recent_profit_factor=1.2,
            regime_in_sample_accuracy=0.58,
            liquidity_score=0.8,
        )
        
        assert input_data.current_regime == "NORMAL"
        assert input_data.volatility == 1.2
        assert len(input_data.trader_raw_scores) == 2
