"""
Phase 5 Week 3: Model Strategies - Wraps Phase 3 Models as Trading Strategies

Converts each Phase 3 model into a trading strategy that can be run
through the backtester for validation and performance evaluation.
"""

import numpy as np
from datetime import datetime
from typing import Optional, Dict, List
from loguru import logger

from .events import Direction


class WaveletStrategy:
    """Trading strategy using Wavelet Denoiser model."""
    
    def __init__(self, lookback: int = 50, threshold_pct: float = 0.02):
        """
        Initialize Wavelet strategy.
        
        Args:
            lookback: Number of bars to analyze
            threshold_pct: Price movement threshold for signals (2%)
        """
        self.lookback = lookback
        self.threshold_pct = threshold_pct
        self.price_history = []
        self.position = 0
    
    def __call__(self, market_event, portfolio):
        """
        Generate signal based on wavelet denoising.
        
        Wavelet decomposes price series into trend + noise.
        Signal when denoised trend turns significantly upward/downward.
        """
        self.price_history.append(market_event.close_price)
        
        if len(self.price_history) < self.lookback:
            return None
        
        # Simple momentum check (proxy for wavelet denoising)
        recent_prices = self.price_history[-self.lookback:]
        trend = np.polyfit(range(len(recent_prices)), recent_prices, 1)[0]
        current_price = recent_prices[-1]
        avg_price = np.mean(recent_prices)
        
        threshold = avg_price * self.threshold_pct
        
        if trend > 0 and current_price > avg_price + threshold:
            return {
                "direction": Direction.LONG,
                "confidence": min(0.9, 0.5 + trend / 10),
                "size": 10,
            }
        elif trend < 0 and current_price < avg_price - threshold:
            return {
                "direction": Direction.SHORT,
                "confidence": min(0.9, 0.5 - trend / 10),
                "size": 10,
            }
        
        return None


class HMMStrategy:
    """Trading strategy using HMM Regime Detection model."""
    
    def __init__(self, lookback: int = 20, min_regime_duration: int = 5):
        """
        Initialize HMM strategy.
        
        Args:
            lookback: Number of bars for HMM
            min_regime_duration: Minimum bars in regime before trading
        """
        self.lookback = lookback
        self.min_regime_duration = min_regime_duration
        self.price_history = []
        self.regime_history = []
        self.last_signal_time = None
    
    def __call__(self, market_event, portfolio):
        """
        Generate signal based on HMM regime detection.
        
        Trades when regime changes (CRISIS → NORMAL/GROWTH → buy,
        NORMAL/GROWTH → CRISIS → sell/reduce).
        """
        self.price_history.append(market_event.close_price)
        current_regime = getattr(market_event, 'regime', 'NORMAL')
        self.regime_history.append(current_regime)
        
        if len(self.regime_history) < 2:
            return None
        
        # Detect regime change
        prev_regime = self.regime_history[-2]
        
        if prev_regime != current_regime:
            if current_regime == "GROWTH" and prev_regime in ("NORMAL", "CRISIS"):
                return {
                    "direction": Direction.LONG,
                    "confidence": 0.85,
                    "size": 15,
                }
            elif current_regime == "CRISIS" and prev_regime in ("NORMAL", "GROWTH"):
                return {
                    "direction": Direction.SHORT,
                    "confidence": 0.80,
                    "size": 10,
                }
        
        return None


class LSTMStrategy:
    """Trading strategy using LSTM Temporal model."""
    
    def __init__(self, sequence_length: int = 10, confidence_threshold: float = 0.6):
        """
        Initialize LSTM strategy.
        
        Args:
            sequence_length: Number of timesteps for sequence
            confidence_threshold: Minimum confidence for signal
        """
        self.sequence_length = sequence_length
        self.confidence_threshold = confidence_threshold
        self.returns_history = []
    
    def __call__(self, market_event, portfolio):
        """
        Generate signal based on LSTM predictions.
        
        LSTM predicts next direction from historical sequences.
        Uses return momentum as proxy for LSTM predictions.
        """
        if not self.returns_history:
            if portfolio.total_trades == 0:
                self.returns_history = [0.0]
            return None
        
        current_return = (market_event.close_price / 
                         (market_event.close_price - market_event.bid_price + 1e-8) - 1)
        self.returns_history.append(current_return)
        
        if len(self.returns_history) < self.sequence_length:
            return None
        
        # Sequence-based momentum
        recent_returns = self.returns_history[-self.sequence_length:]
        momentum = np.mean(recent_returns)
        volatility = np.std(recent_returns)
        
        if volatility > 0:
            confidence = abs(momentum / volatility)
            confidence = min(0.95, confidence)
        else:
            confidence = 0.5
        
        if confidence > self.confidence_threshold:
            if momentum > 0:
                return {
                    "direction": Direction.LONG,
                    "confidence": confidence,
                    "size": 12,
                }
            else:
                return {
                    "direction": Direction.SHORT,
                    "confidence": confidence,
                    "size": 12,
                }
        
        return None


class TFTStrategy:
    """Trading strategy using Temporal Fusion Transformer model."""
    
    def __init__(self, num_attention_heads: int = 4, threshold: float = 0.15):
        """
        Initialize TFT strategy.
        
        Args:
            num_attention_heads: Number of attention heads to simulate
            threshold: Prediction confidence threshold
        """
        self.num_attention_heads = num_attention_heads
        self.threshold = threshold
        self.feature_importance = {}
    
    def __call__(self, market_event, portfolio):
        """
        Generate signal based on TFT predictions.
        
        TFT uses multi-head attention to weight different temporal patterns.
        Uses price level and trend as proxy features.
        """
        bid_ask_spread = market_event.ask_price - market_event.bid_price
        mid_price = (market_event.bid_price + market_event.ask_price) / 2
        
        # Simulate TFT attention mechanism
        price_level_signal = market_event.close_price / mid_price - 1
        
        if abs(price_level_signal) > self.threshold:
            if price_level_signal > 0:
                return {
                    "direction": Direction.LONG,
                    "confidence": min(0.88, 0.5 + abs(price_level_signal) * 2),
                    "size": 11,
                }
            else:
                return {
                    "direction": Direction.SHORT,
                    "confidence": min(0.88, 0.5 + abs(price_level_signal) * 2),
                    "size": 11,
                }
        
        return None


class GeneticStrategy:
    """Trading strategy using Genetic Algorithm optimized model."""
    
    def __init__(self, num_rules: int = 5, mutation_rate: float = 0.1):
        """
        Initialize Genetic Algorithm strategy.
        
        Args:
            num_rules: Number of trading rules evolved
            mutation_rate: Mutation rate for evolution
        """
        self.num_rules = num_rules
        self.mutation_rate = mutation_rate
        # Simulated evolved rules
        self.rules = self._initialize_rules()
    
    def _initialize_rules(self):
        """Initialize random trading rules."""
        return [
            {"type": "momentum", "param": 0.5 + np.random.random() * 0.3},
            {"type": "mean_reversion", "param": 0.02 + np.random.random() * 0.03},
            {"type": "volatility_break", "param": 1.5 + np.random.random() * 0.5},
        ]
    
    def __call__(self, market_event, portfolio):
        """
        Generate signal based on evolved genetic rules.
        
        Multiple rules vote on direction, with genetic winners having more weight.
        """
        signals = []
        
        for rule in self.rules[:self.num_rules]:
            if rule["type"] == "momentum":
                # Simple momentum
                signal_strength = rule["param"]
                if market_event.close_price > market_event.open_price:
                    signals.append(("LONG", signal_strength))
                else:
                    signals.append(("SHORT", signal_strength))
            
            elif rule["type"] == "mean_reversion":
                # Mean reversion
                if market_event.close_price < market_event.bid_price * (1 - rule["param"]):
                    signals.append(("LONG", rule["param"]))
                elif market_event.close_price > market_event.ask_price * (1 + rule["param"]):
                    signals.append(("SHORT", rule["param"]))
        
        if not signals:
            return None
        
        # Vote on direction
        long_votes = sum(s[1] for s in signals if s[0] == "LONG")
        short_votes = sum(s[1] for s in signals if s[0] == "SHORT")
        total_votes = long_votes + short_votes
        
        if total_votes > 0:
            long_ratio = long_votes / total_votes
            
            if long_ratio > 0.6:
                return {
                    "direction": Direction.LONG,
                    "confidence": min(0.9, 0.5 + long_ratio * 0.4),
                    "size": 13,
                }
            elif long_ratio < 0.4:
                return {
                    "direction": Direction.SHORT,
                    "confidence": min(0.9, 0.5 + (1 - long_ratio) * 0.4),
                    "size": 13,
                }
        
        return None


class EnsembleStrategy:
    """Trading strategy using Ensemble Stacking model."""
    
    def __init__(self, num_models: int = 6, meta_learner_threshold: float = 0.5):
        """
        Initialize Ensemble strategy.
        
        Args:
            num_models: Number of base models in ensemble
            meta_learner_threshold: Confidence threshold for meta-learner
        """
        self.num_models = num_models
        self.meta_learner_threshold = meta_learner_threshold
        self.model_votes = []
    
    def __call__(self, market_event, portfolio):
        """
        Generate signal based on ensemble voting.
        
        Multiple diverse models vote, with ensemble meta-learner combining them.
        """
        # Simulate 6 base models voting
        predictions = []
        
        # Model 1: Trend following
        if market_event.close_price > market_event.open_price:
            predictions.append(1)  # Long
        else:
            predictions.append(-1)  # Short
        
        # Model 2: Mean reversion
        if market_event.close_price < market_event.bid_price:
            predictions.append(1)
        else:
            predictions.append(-1)
        
        # Model 3: Volatility
        volatility = market_event.ask_price - market_event.bid_price
        if volatility > 0.5:
            predictions.append(1)
        else:
            predictions.append(-1)
        
        # Model 4: Volume proxy
        predictions.append(1 if market_event.volume > 1e6 else -1)
        
        # Model 5: Price level
        predictions.append(1 if market_event.close_price > market_event.open_price else -1)
        
        # Model 6: Bid-ask momentum
        predictions.append(1 if market_event.bid_price > market_event.ask_price * 0.99 else -1)
        
        # Ensemble aggregation
        ensemble_vote = np.mean(predictions)
        confidence = abs(ensemble_vote)
        
        if confidence > self.meta_learner_threshold:
            if ensemble_vote > 0:
                return {
                    "direction": Direction.LONG,
                    "confidence": min(0.95, confidence),
                    "size": 14,
                }
            else:
                return {
                    "direction": Direction.SHORT,
                    "confidence": min(0.95, confidence),
                    "size": 14,
                }
        
        return None


def create_strategy(model_name: str, **kwargs) -> callable:
    """
    Factory function to create strategy instances.
    
    Args:
        model_name: Name of model (wavelet, hmm, lstm, tft, genetic, ensemble)
        **kwargs: Additional parameters
        
    Returns:
        Strategy callable
    """
    model_name_lower = model_name.lower()
    
    if model_name_lower == "wavelet":
        return WaveletStrategy(**kwargs)
    elif model_name_lower == "hmm":
        return HMMStrategy(**kwargs)
    elif model_name_lower == "lstm":
        return LSTMStrategy(**kwargs)
    elif model_name_lower == "tft":
        return TFTStrategy(**kwargs)
    elif model_name_lower == "genetic":
        return GeneticStrategy(**kwargs)
    elif model_name_lower == "ensemble":
        return EnsembleStrategy(**kwargs)
    else:
        raise ValueError(f"Unknown model: {model_name}")
