"""
Hidden Markov Model — Regime Detector
======================================
Identifies the current market "state" (Crisis / Normal / Growth).
The algorithm adapts its strategy based on which regime we're in.
"""

import numpy as np
import pandas as pd
from typing import Optional, Tuple, List
from loguru import logger
from hmmlearn import hmm

from src.models.base import BaseModel


class RegimeDetector(BaseModel):
    """
    HMM-based market regime detector for gold.

    Detects 3 regimes:
      0 = Low Volatility (Growth/Range) → Mean Reversion strategy
      1 = Medium Volatility (Normal)    → Balanced strategy
      2 = High Volatility (Crisis)      → Trend Following strategy
    """

    REGIME_NAMES = {0: "GROWTH", 1: "NORMAL", 2: "CRISIS"}

    def __init__(
        self,
        n_regimes: int = 3,
        covariance_type: str = "diag",
        n_iter: int = 1000,
        version: str = "1.0",
    ):
        super().__init__(name="RegimeDetector", version=version)
        self.n_regimes = n_regimes
        # Use diagonal covariance for numerical stability (avoids singular matrix issues)
        self.model = hmm.GaussianHMM(
            n_components=n_regimes,
            covariance_type=covariance_type,
            n_iter=n_iter,
            random_state=42,
        )
        self.metadata = {
            "n_regimes": n_regimes,
            "covariance_type": covariance_type,
        }
        self._regime_order = None  # Maps HMM states to vol-ordered regimes
        self._feature_mean = None  # For normalization
        self._feature_std = None

    def prepare_features(self, df: pd.DataFrame, fit: bool = False) -> np.ndarray:
        """
        Prepare observation features for HMM.

        Uses: returns, volatility, and (optionally) macro correlations.
        Features are normalized for numerical stability.
        
        Args:
            df: Price DataFrame with at least 'close' column.
            fit: If True, fit the normalizer on this data (used during training).
        """
        features = pd.DataFrame(index=df.index)

        # Returns
        features["returns"] = df["close"].pct_change()

        # Realized volatility (20-day)
        features["volatility"] = features["returns"].rolling(20).std()

        # Absolute returns (regime indicator)
        features["abs_returns"] = features["returns"].abs()

        # Range (high-low) as % of close
        if "high" in df.columns and "low" in df.columns:
            features["range_pct"] = (df["high"] - df["low"]) / df["close"]

        features = features.dropna()
        X = features.values
        
        # Normalize features (standardize to mean=0, std=1)
        if fit:
            # Fit normalizer on training data
            self._feature_mean = X.mean(axis=0)
            self._feature_std = X.std(axis=0) + 1e-8  # Avoid division by zero
        
        if self._feature_mean is not None and self._feature_std is not None:
            X = (X - self._feature_mean) / self._feature_std
        
        return X, features.index

    def train(self, X: pd.DataFrame, y=None) -> dict:
        """
        Train HMM on historical data.

        Args:
            X: DataFrame with at least 'close' column.

        Returns:
            Training metrics including regime statistics.
        """
        obs, idx = self.prepare_features(X, fit=True)  # fit=True to normalize
        logger.info(f"Training HMM with {len(obs)} observations, {self.n_regimes} regimes")
        logger.info(f"  Feature mean: {self._feature_mean}")
        logger.info(f"  Feature std: {self._feature_std}")

        self.model.fit(obs)

        # Decode states
        states = self.model.predict(obs)

        # Order regimes by volatility (0=lowest vol, 2=highest vol)
        vol_by_state = {}
        for s in range(self.n_regimes):
            mask = states == s
            vol_by_state[s] = np.std(obs[mask, 0]) if mask.any() else 0

        sorted_states = sorted(vol_by_state, key=vol_by_state.get)
        self._regime_order = {old: new for new, old in enumerate(sorted_states)}

        # Compute regime statistics
        ordered_states = np.array([self._regime_order[s] for s in states])
        metrics = {"regimes": {}}
        for regime_id in range(self.n_regimes):
            mask = ordered_states == regime_id
            regime_name = self.REGIME_NAMES.get(regime_id, f"REGIME_{regime_id}")
            metrics["regimes"][regime_name] = {
                "pct_time": float(mask.mean()),
                "mean_return": float(obs[mask, 0].mean()) if mask.any() else 0,
                "volatility": float(obs[mask, 0].std()) if mask.any() else 0,
                "count": int(mask.sum()),
            }
            logger.info(
                f"  {regime_name}: {mask.mean():.1%} of time | "
                f"vol={obs[mask, 0].std():.4f}"
            )

        self.is_trained = True
        metrics["transition_matrix"] = self.model.transmat_.tolist()
        return metrics

    def predict(self, X: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Predict current regime.

        Returns:
            Tuple of (regime_ids, confidences)
        """
        if not self.is_trained:
            raise RuntimeError("Model not trained. Call train() first.")

        obs, idx = self.prepare_features(X)
        raw_states = self.model.predict(obs)
        probs = self.model.predict_proba(obs)

        # Reorder to volatility-based regime IDs
        ordered_states = np.array([self._regime_order[s] for s in raw_states])
        confidences = np.max(probs, axis=1)

        return ordered_states, confidences

    def get_current_regime(self, X: pd.DataFrame) -> Tuple[str, float]:
        """
        Get the current (latest) regime as a human-readable string.

        Returns:
            Tuple of (regime_name, confidence)
        """
        states, confs = self.predict(X)
        current_state = int(states[-1])
        current_conf = float(confs[-1])
        regime_name = self.REGIME_NAMES.get(current_state, f"UNKNOWN_{current_state}")
        return regime_name, current_conf

    def save(self, path: str) -> None:
        import joblib
        joblib.dump({
            "model": self.model,
            "regime_order": self._regime_order,
            "metadata": self.metadata,
        }, path)
        logger.info(f"RegimeDetector saved to {path}")

    def load(self, path: str) -> None:
        import joblib
        state = joblib.load(path)
        self.model = state["model"]
        self._regime_order = state["regime_order"]
        self.metadata = state["metadata"]
        self.is_trained = True
        logger.info(f"RegimeDetector loaded from {path}")
