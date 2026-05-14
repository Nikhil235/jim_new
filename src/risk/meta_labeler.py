"""
Meta-Labeler (Critic Model)
============================
Two-model system: Trader makes signals, Critic decides if Trader is right.

The Simons insight: "We don't predict the market, we predict our own accuracy."

Reference: López de Prado, "Advances in Financial Machine Learning", Chapter 6
"""

import numpy as np
from typing import Tuple, Optional
from loguru import logger
from dataclasses import dataclass

try:
    from xgboost import XGBClassifier
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False


@dataclass
class TraderSignal:
    """Output from the Trader (ensemble of models)."""
    direction: int  # -1 (short), 0 (flat), 1 (long)
    confidence: float  # 0.0 to 1.0 from ensemble agreement
    raw_scores: dict  # Individual model scores (for Critic input)


@dataclass
class CriticInput:
    """Input features for the Critic model."""
    # Trader info
    trader_signal: int  # -1, 0, 1
    trader_confidence: float  # Ensemble agreement strength
    trader_raw_scores: np.ndarray  # Individual model outputs
    
    # Market state
    current_regime: str  # "GROWTH", "NORMAL", "CRISIS"
    regime_probability: float  # 0.0 to 1.0
    volatility: float  # Current vol vs historical (ratio)
    spread_pct: float  # Bid-ask spread as % of mid
    
    # Temporal
    hour_of_day: int  # 0-23
    day_of_week: int  # 0-6 (0=Monday)
    
    # Historical
    trader_recent_accuracy: float  # Win rate on last 20 trades
    trader_recent_profit_factor: float  # Total wins / total losses
    regime_in_sample_accuracy: float  # Model accuracy in THIS regime
    
    # Liquidity
    liquidity_score: float  # 0.0 to 1.0 (higher = better liquidity)


class MetaLabeler:
    """
    Critic model that predicts if the Trader's signal is correct.
    
    Binary classification:
    - 1: Trader is right → EXECUTE
    - 0: Trader is wrong → SKIP
    """
    
    def __init__(self, threshold: float = 0.65, use_gpu: bool = False):
        """
        Args:
            threshold: Confidence threshold to execute (0.0 to 1.0).
            use_gpu: Whether to use GPU-accelerated inference (future).
        """
        self.threshold = threshold
        self.use_gpu = use_gpu
        self.is_trained = False
        
        if HAS_XGBOOST:
            self.model = XGBClassifier(
                max_depth=5,
                n_estimators=100,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                verbosity=0,
            )
            logger.info(f"MetaLabeler initialized | threshold={threshold:.2%}")
        else:
            logger.warning("XGBoost not installed. Falling back to simple confidence threshold.")
            self.model = None
    
    def should_trade(
        self,
        trader_signal: TraderSignal,
        critic_input: CriticInput,
    ) -> Tuple[bool, float]:
        """
        Decide if we should execute the Trader's signal.
        
        Args:
            trader_signal: Output from Trader model.
            critic_input: Features for the Critic.
        
        Returns:
            Tuple of (execute: bool, confidence: float)
        """
        if not self.is_trained and self.model is not None:
            logger.warning("Critic not trained yet — using simple threshold fallback")
            return trader_signal.confidence > self.threshold, trader_signal.confidence
        
        if self.model is None:
            # Simple fallback: just use trader confidence
            return trader_signal.confidence > self.threshold, trader_signal.confidence
        
        # Build feature vector from CriticInput
        features = self._build_features(trader_signal, critic_input)
        
        # Predict
        try:
            prob = self.model.predict_proba(features.reshape(1, -1))[0][1]
        except Exception as e:
            logger.error(f"Critic prediction failed: {e} — falling back to threshold")
            prob = trader_signal.confidence
        
        execute = prob > self.threshold
        
        logger.debug(
            f"Critic Decision: signal={trader_signal.direction:+d} "
            f"trader_conf={trader_signal.confidence:.2%} "
            f"critic_conf={prob:.2%} execute={execute} "
            f"regime={critic_input.current_regime}"
        )
        
        return execute, prob
    
    def _build_features(
        self,
        trader_signal: TraderSignal,
        critic_input: CriticInput,
    ) -> np.ndarray:
        """Convert CriticInput to feature vector."""
        features = [
            # Trader signal features
            critic_input.trader_signal,
            critic_input.trader_confidence,
            
            # Market state
            self._regime_to_numeric(critic_input.current_regime),
            critic_input.regime_probability,
            critic_input.volatility,
            critic_input.spread_pct,
            
            # Temporal (one-hot encode)
            np.sin(2 * np.pi * critic_input.hour_of_day / 24),
            np.cos(2 * np.pi * critic_input.hour_of_day / 24),
            np.sin(2 * np.pi * critic_input.day_of_week / 7),
            np.cos(2 * np.pi * critic_input.day_of_week / 7),
            
            # Historical accuracy
            critic_input.trader_recent_accuracy,
            critic_input.trader_recent_profit_factor,
            critic_input.regime_in_sample_accuracy,
            
            # Liquidity
            critic_input.liquidity_score,
        ]
        
        return np.array(features, dtype=np.float32)
    
    @staticmethod
    def _regime_to_numeric(regime: str) -> float:
        """Convert regime string to numeric."""
        mapping = {"GROWTH": 1.0, "NORMAL": 0.0, "CRISIS": -1.0}
        return mapping.get(regime, 0.0)
    
    def train(
        self,
        X: np.ndarray,
        y: np.ndarray,
        validation_split: float = 0.2,
    ) -> dict:
        """
        Train the Critic model on historical data.
        
        Args:
            X: Feature matrix (n_samples, n_features).
            y: Binary labels (1 = Trader was right, 0 = Trader was wrong).
            validation_split: Fraction of data to use for validation.
        
        Returns:
            Training metrics dictionary.
        """
        if self.model is None:
            logger.error("XGBoost not available — cannot train Critic")
            return {}
        
        n = len(X)
        split_idx = int(n * (1 - validation_split))
        
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]
        
        self.model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            verbose=False,
        )
        
        # Evaluate
        train_acc = self.model.score(X_train, y_train)
        val_acc = self.model.score(X_val, y_val)
        
        self.is_trained = True
        
        metrics = {
            "train_accuracy": train_acc,
            "val_accuracy": val_acc,
            "n_samples": n,
            "n_features": X.shape[1],
        }
        
        logger.info(
            f"Critic trained: train_acc={train_acc:.2%} val_acc={val_acc:.2%}"
        )
        
        return metrics
    
    def feature_importance(self) -> dict:
        """Get feature importance from the trained model."""
        if self.model is None or not self.is_trained:
            return {}
        
        feature_names = [
            "trader_signal", "trader_confidence", "regime", "regime_prob",
            "volatility", "spread_pct", "hour_sin", "hour_cos",
            "dow_sin", "dow_cos", "recent_accuracy", "profit_factor",
            "regime_accuracy", "liquidity"
        ]
        
        importances = self.model.feature_importances_
        
        return dict(zip(feature_names, importances))
