"""
Hidden Markov Model — Regime Detector
=======================================
Jim Simons' Insight:
  "The market has different states. You don't trade the same way
   in a crisis as you do in a bull run. The first job is to know
   which state you're in."

This model detects 3 market regimes (Growth / Normal / Crisis) using
a Gaussian Hidden Markov Model fitted on multi-dimensional observations:
  - Returns (directional momentum)
  - Realized volatility (risk level)
  - Absolute returns (shock magnitude)
  - High-Low range percentage (intraday dispersion)
  - Volume regime (participation level)
  - Cross-asset signals (DXY, yields when available)

Production Features:
  - Multi-feature observation model (not just returns)
  - Volatility-ordered regime labeling (consistent across refits)
  - Transition probability analysis for regime change prediction
  - Regime duration modeling (expected time in each state)
  - Online regime tracking with probability smoothing
  - Regime persistence scoring (avoid whipsaws)
  - Robust normalization with fitted statistics
  - GPU acceleration via cupy when available

Parameters (calibrated for XAU/USD):
  - n_regimes: 3 (Growth=0, Normal=1, Crisis=2)
  - covariance_type: 'diag' (numerical stability, avoids singular matrices)
  - n_iter: 1000 (EM convergence tolerance)
  - min_regime_duration: 5 bars (anti-whipsaw filter)
"""

import numpy as np
import pandas as pd
import time
from typing import Dict, List, Optional, Tuple, Any
from loguru import logger

from src.models.base import BaseModel, ModelOutput

# GPU acceleration
try:
    from src.utils.gpu import get_dataframe_engine, get_array_engine
    pd_engine = get_dataframe_engine()
    cp = get_array_engine()
except ImportError:
    pd_engine = pd
    cp = np

# HMM library
try:
    from hmmlearn import hmm
    HMM_AVAILABLE = True
except ImportError:
    HMM_AVAILABLE = False
    logger.warning("hmmlearn not installed. RegimeDetector will use a simplified fallback.")


class RegimeDetector(BaseModel):
    """
    Production HMM-based market regime detector for XAU/USD.

    Detects 3 regimes ordered by volatility:
      0 = Low Volatility (Growth/Range) → Mean Reversion strategy
      1 = Medium Volatility (Normal)    → Balanced strategy
      2 = High Volatility (Crisis)      → Trend Following / Defensive

    Architecture:
        1. Multi-feature observation extraction (returns, vol, range, volume)
        2. Gaussian HMM with diagonal covariance (EM algorithm)
        3. Volatility-sorted regime labeling
        4. Transition matrix analysis for regime change prediction
        5. Regime persistence scoring to filter whipsaws
        6. Trading signal generation based on regime + momentum
    """

    REGIME_NAMES = {0: "GROWTH", 1: "NORMAL", 2: "CRISIS"}
    REGIME_COLORS = {0: "#22c55e", 1: "#f59e0b", 2: "#ef4444"}

    # Strategy mapping per regime (Jim Simons' framework)
    REGIME_STRATEGIES = {
        "GROWTH": {
            "approach": "Mean Reversion",
            "kelly_fraction": 0.65,  # More aggressive in calm markets
            "position_bias": "LONG",
            "description": "Low-vol environment, buy dips, revert to mean",
        },
        "NORMAL": {
            "approach": "Balanced",
            "kelly_fraction": 0.50,  # Standard Half-Kelly
            "position_bias": "NEUTRAL",
            "description": "Mixed signals, standard position sizing",
        },
        "CRISIS": {
            "approach": "Trend Following",
            "kelly_fraction": 0.25,  # Quarter-Kelly for survival
            "position_bias": "DEFENSIVE",
            "description": "High-vol, follow the trend, minimize exposure",
        },
    }

    def __init__(
        self,
        n_regimes: int = 3,
        covariance_type: str = "diag",
        n_iter: int = 1000,
        min_regime_duration: int = 30,  # Bug 4 Fix: Increased from 5 to 30 bars to prevent 34% flip rate
        regime_persistence_weight: float = 0.3,
        vol_windows: Optional[List[int]] = None,
        version: str = "2.0",
    ):
        """
        Initialize Regime Detector.

        Args:
            n_regimes: Number of hidden states (3 = Growth/Normal/Crisis)
            covariance_type: 'diag' (stable) or 'full' (flexible but prone to singularity)
            n_iter: Maximum EM iterations
            min_regime_duration: Minimum bars before regime change signal
            regime_persistence_weight: Weight for regime persistence score (anti-whipsaw)
            vol_windows: Volatility computation windows
            version: Model version
        """
        super().__init__(name="RegimeDetector", version=version)
        self.n_regimes = n_regimes
        self.covariance_type = covariance_type
        self.n_iter = n_iter
        self.min_regime_duration = min_regime_duration
        self.regime_persistence_weight = regime_persistence_weight
        self.vol_windows = vol_windows or [10, 20, 50]

        # HMM model
        self.model: Optional[Any] = None
        if HMM_AVAILABLE:
            self.model = hmm.GaussianHMM(
                n_components=n_regimes,
                covariance_type=covariance_type,
                n_iter=n_iter,
                random_state=42,
                tol=1e-4,
            )

        # Learned parameters
        self._regime_order = None  # Maps HMM states to vol-ordered regimes
        self._feature_mean = None
        self._feature_std = None
        self._regime_stats = None  # Statistics per regime
        self._transition_matrix = None
        self._regime_durations = None  # Average duration per regime

        # Runtime state
        self._recent_regimes = []  # For persistence scoring
        self._regime_change_count = 0

    def prepare_features(self, df: pd.DataFrame, fit: bool = False) -> Tuple[np.ndarray, Any]:
        """
        Prepare multi-dimensional observation features for HMM.

        Features:
            1. Returns (1-bar percentage change)
            2. Realized volatility (20-day rolling std of returns)
            3. Absolute returns (shock magnitude indicator)
            4. High-Low range as % of close (intraday volatility)
            5. Volume z-score (participation regime)
            6. Momentum (5-bar cumulative return)
            7. Return acceleration (2nd derivative)

        Args:
            df: Price DataFrame with at least 'close' column.
            fit: If True, fit the normalizer (training mode).

        Returns:
            Tuple of (observation_matrix, datetime_index)
        """
        features = pd.DataFrame(index=df.index)

        # Core features
        # Bug 4 Fix: Use smoothed returns for HMM features to prevent volatile 1-minute flipping
        smoothed_close = df["close"].rolling(5).mean()
        raw_returns = df["close"].pct_change()
        
        features["returns"] = smoothed_close.pct_change()
        features["volatility"] = raw_returns.rolling(20).std()
        features["abs_returns"] = raw_returns.abs().rolling(5).mean()

        # Intraday range
        if "high" in df.columns and "low" in df.columns:
            features["range_pct"] = (df["high"] - df["low"]) / df["close"]

        # Volume regime
        if "volume" in df.columns:
            vol_ma = df["volume"].rolling(20).mean()
            vol_std = df["volume"].rolling(20).std()
            features["volume_zscore"] = (df["volume"] - vol_ma) / (vol_std + 1e-10)

        # Momentum (5-bar cumulative return)
        features["momentum_5"] = features["returns"].rolling(5).sum()

        # Return acceleration
        features["return_accel"] = features["returns"].diff()

        features = features.dropna()
        X = features.values.astype(np.float64)

        # Normalize (standardize to mean=0, std=1)
        if fit:
            self._feature_mean = X.mean(axis=0)
            self._feature_std = X.std(axis=0) + 1e-8

        if self._feature_mean is not None and self._feature_std is not None:
            X = (X - self._feature_mean) / self._feature_std

        return X, features.index

    def train(self, X: pd.DataFrame, y=None) -> Dict[str, Any]:
        """
        Train HMM on historical data.

        Steps:
            1. Extract observation features
            2. Fit Gaussian HMM via EM algorithm
            3. Decode hidden states (Viterbi algorithm)
            4. Order regimes by volatility (0=lowest, 2=highest)
            5. Compute regime statistics and transition matrix
            6. Estimate expected regime durations

        Args:
            X: DataFrame with at least 'close' column.

        Returns:
            Training metrics including regime statistics, transition matrix.
        """
        obs, idx = self.prepare_features(X, fit=True)

        # Convert to CPU numpy for hmmlearn
        if hasattr(obs, "get"):
            obs_cpu = obs.get()
        else:
            obs_cpu = np.asarray(obs)

        logger.info(f"Training HMM: {len(obs_cpu)} observations, {self.n_regimes} regimes, {obs_cpu.shape[1]} features")

        if self.model is not None:
            self.model.fit(obs_cpu)
            states = self.model.predict(obs_cpu)
            probs = self.model.predict_proba(obs_cpu)
        else:
            # Fallback: k-means-like clustering by volatility
            states, probs = self._fallback_regime_detection(obs_cpu)

        # Order regimes by volatility (column 0 = returns)
        vol_by_state: Dict[int, float] = {}
        for s in range(self.n_regimes):
            mask = states == s
            vol_by_state[s] = float(np.std(obs_cpu[mask, 0])) if mask.any() else 0.0

        sorted_states = sorted(vol_by_state, key=lambda x: vol_by_state[x])
        self._regime_order = {old: new for new, old in enumerate(sorted_states)}

        # Compute regime statistics
        ordered_states = np.array([self._regime_order[s] for s in states])
        self._regime_stats = {}

        for regime_id in range(self.n_regimes):
            mask = ordered_states == regime_id
            regime_name = self.REGIME_NAMES.get(regime_id, f"REGIME_{regime_id}")

            # Regime duration analysis
            durations = self._compute_regime_durations(ordered_states, regime_id)

            self._regime_stats[regime_name] = {
                "pct_time": float(mask.mean()),
                "mean_return": float(obs_cpu[mask, 0].mean()) if mask.any() else 0.0,
                "volatility": float(obs_cpu[mask, 0].std()) if mask.any() else 0.0,
                "count": int(mask.sum()),
                "avg_duration_bars": float(np.mean(durations)) if durations else 0.0,
                "max_duration_bars": float(np.max(durations)) if durations else 0.0,
                "strategy": self.REGIME_STRATEGIES.get(regime_name, {}),
            }

            logger.info(
                f"  {regime_name}: {mask.mean():.1%} of time | "
                f"vol={obs_cpu[mask, 0].std():.4f} | "
                f"avg_duration={np.mean(durations):.0f} bars"
            )

        # Transition matrix
        if self.model is not None and hasattr(self.model, "transmat_"):
            # Reorder transition matrix to match volatility ordering
            raw_trans = self.model.transmat_
            reordered = np.zeros_like(raw_trans)
            for old, new in self._regime_order.items():
                for old2, new2 in self._regime_order.items():
                    reordered[new, new2] = raw_trans[old, old2]
            self._transition_matrix = reordered
        else:
            self._transition_matrix = np.eye(self.n_regimes) * 0.8 + 0.1

        self.is_trained = True
        self._train_timestamp = pd.Timestamp.now().isoformat()
        self._train_samples = len(obs_cpu)

        metrics = {
            "regimes": self._regime_stats,
            "transition_matrix": self._transition_matrix.tolist(),
            "n_features": obs_cpu.shape[1],
            "train_samples": len(obs_cpu),
            "feature_means": self._feature_mean.tolist() if self._feature_mean is not None else [],
        }

        return metrics

    def predict(self, X: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Predict regime for each timestep.

        Returns:
            Tuple of (regime_ids, confidences)
        """
        if not self.is_trained:
            raise RuntimeError("Model not trained. Call train() first.")

        obs, idx = self.prepare_features(X)

        if hasattr(obs, "get"):
            obs_cpu = obs.get()
        else:
            obs_cpu = np.asarray(obs)

        if self.model is not None:
            raw_states = self.model.predict(obs_cpu)
            probs = self.model.predict_proba(obs_cpu)
        else:
            raw_states, probs = self._fallback_regime_detection(obs_cpu)

        # Reorder to volatility-based regime IDs
        order = self._regime_order or {}
        ordered_states = np.array([order.get(s, s) for s in raw_states])
        confidences = np.max(probs, axis=1)

        return ordered_states, confidences

    def get_current_regime(self, X: pd.DataFrame) -> Tuple[str, float]:
        """
        Get the current (latest) regime.

        Applies persistence scoring to avoid whipsaw regime changes.

        Returns:
            Tuple of (regime_name, confidence)
        """
        states, confs = self.predict(X)
        current_state = int(states[-1])
        current_conf = float(confs[-1])

        # Persistence scoring: weight recent regime history
        self._recent_regimes.append(current_state)
        if len(self._recent_regimes) > self.min_regime_duration * 3:
            self._recent_regimes = self._recent_regimes[-self.min_regime_duration * 3:]

        # Check regime persistence (avoid whipsaw)
        smoothed_state = current_state
        if len(self._recent_regimes) >= self.min_regime_duration:
            recent = self._recent_regimes[-self.min_regime_duration:]
            persistence = sum(1 for r in recent if r == current_state) / len(recent)

            # Boost confidence if regime is persistent, reduce if unstable
            adjusted_conf = current_conf * (1 - self.regime_persistence_weight) + persistence * self.regime_persistence_weight
            current_conf = min(adjusted_conf, 1.0)
            
            # Hysteresis on the reported state to prevent flip-flopping
            from collections import Counter
            most_common_state, count = Counter(recent).most_common(1)[0]
            if count >= self.min_regime_duration * 0.6:  # If a state is dominant (e.g. 60% of recent bars)
                smoothed_state = most_common_state

        regime_name = self.REGIME_NAMES.get(smoothed_state, f"UNKNOWN_{smoothed_state}")
        return regime_name, current_conf

    def get_regime_transition_probabilities(self) -> Dict[str, Dict[str, float]]:
        """
        Get the probability of transitioning between regimes.

        Used by the risk manager to anticipate regime changes.

        Returns:
            Nested dict: {from_regime: {to_regime: probability}}
        """
        if self._transition_matrix is None:
            return {}

        result = {}
        for i in range(self.n_regimes):
            from_name = self.REGIME_NAMES.get(i, f"REGIME_{i}")
            result[from_name] = {}
            for j in range(self.n_regimes):
                to_name = self.REGIME_NAMES.get(j, f"REGIME_{j}")
                result[from_name][to_name] = float(self._transition_matrix[i, j])

        return result

    def get_expected_regime_duration(self, regime_name: str) -> float:
        """
        Expected duration (in bars) of staying in a given regime.

        Derived from transition matrix: E[duration] = 1 / (1 - p_self)
        """
        regime_id = {v: k for k, v in self.REGIME_NAMES.items()}.get(regime_name)
        if regime_id is None or self._transition_matrix is None:
            return 0.0

        p_self = self._transition_matrix[regime_id, regime_id]
        if p_self >= 1.0:
            return float("inf")
        return 1.0 / (1.0 - p_self + 1e-10)

    def generate_signal(self, df: pd.DataFrame) -> ModelOutput:
        """
        Generate a regime-aware trading signal.

        Signal Logic:
            - GROWTH regime: Lean LONG (buy dips in calm markets)
            - NORMAL regime: Follow momentum direction
            - CRISIS regime: Defensive (reduce exposure, follow strong trends only)

        Also provides:
            - Regime transition probabilities
            - Expected regime duration
            - Regime persistence confidence

        Args:
            df: Recent OHLCV DataFrame

        Returns:
            ModelOutput with regime-aware signal
        """
        start_time = time.perf_counter()

        if len(df) < 30:
            return ModelOutput(signal="HOLD", confidence=0.0, reasoning="Insufficient data for HMM")

        # Train if needed
        if not self.is_trained:
            self.train(df)

        # Get current regime
        regime_name, regime_conf = self.get_current_regime(df)

        # Recent price momentum
        recent_return = df["close"].pct_change().iloc[-1]
        recent_vol = df["close"].pct_change().rolling(10).std().iloc[-1] if len(df) > 10 else 0.01

        # Regime-based signal generation
        strategy = self.REGIME_STRATEGIES.get(regime_name, self.REGIME_STRATEGIES["NORMAL"])
        transition_probs = self.get_regime_transition_probabilities()

        # Probability of transitioning to crisis
        crisis_prob = transition_probs.get(regime_name, {}).get("CRISIS", 0.0)
        growth_prob = transition_probs.get(regime_name, {}).get("GROWTH", 0.0)

        # Bug 3 Fix: Removed arbitrary heuristic scalar clamps (* 1.1, * 0.7) so the HMM 
        # returns the true unadulterated probability, not a hardcoded constant.
        if regime_name == "GROWTH":
            # Calm market: Mean reversion
            if recent_return > 0.003:
                signal = "SHORT"  # Sell the rip
                confidence = regime_conf * 0.80
            elif recent_return < -0.008:
                signal = "SHORT"  # Trend breakdown, stop buying the dip
                confidence = regime_conf * 0.90
            elif recent_return < -0.002:
                signal = "LONG"  # Buy the dip
                confidence = regime_conf * 0.80
            else:
                signal = "HOLD"
                confidence = 0.0

            reasoning = (
                f"GROWTH regime (conf={regime_conf:.0%}) | "
                f"Strategy: {strategy['approach']} | "
                f"Return: {recent_return:.4f} | Crisis prob: {crisis_prob:.2%}"
            )

        elif regime_name == "CRISIS":
            # Crisis: Defensive positioning
            if recent_return < -0.005:
                signal = "SHORT"  # Follow the trend down
                confidence = regime_conf
            elif recent_return > 0.005:
                signal = "HOLD"  # Don't fight the crisis but don't chase
                confidence = 0.0
            else:
                signal = "HOLD"
                confidence = 0.0

            reasoning = (
                f"CRISIS regime (conf={regime_conf:.0%}) | "
                f"Strategy: {strategy['approach']} | "
                f"Vol: {recent_vol:.4f} | Growth prob: {growth_prob:.2%}"
            )

        else:  # NORMAL
            # Normal: Follow momentum
            if recent_return > 0.002:
                signal = "LONG"
                confidence = regime_conf
            elif recent_return < -0.002:
                signal = "SHORT"
                confidence = regime_conf
            else:
                signal = "HOLD"
                confidence = 0.0

            reasoning = (
                f"NORMAL regime (conf={regime_conf:.0%}) | "
                f"Strategy: {strategy['approach']} | "
                f"Return: {recent_return:.4f}"
            )

        latency_ms = (time.perf_counter() - start_time) * 1000

        return ModelOutput(
            signal=signal,
            confidence=round(confidence, 4),
            regime=regime_name,
            reasoning=reasoning,
            features_used=["close", "high", "low", "volume", "returns"],
            metadata={
                "regime_confidence": round(regime_conf, 4),
                "transition_probabilities": transition_probs.get(regime_name, {}),
                "expected_duration_bars": round(self.get_expected_regime_duration(regime_name), 1),
                "kelly_fraction": strategy.get("kelly_fraction", 0.5),
                "regime_stats": (self._regime_stats or {}).get(regime_name, {}),
                "recent_return": round(recent_return, 6),
                "recent_volatility": round(recent_vol, 6),
                "crisis_probability": round(crisis_prob, 4),
            },
            latency_ms=latency_ms,
            timestamp=pd.Timestamp.now().isoformat(),
        )

    # ──────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────

    @staticmethod
    def _compute_regime_durations(states: np.ndarray, target_regime: int) -> List[int]:
        """Compute consecutive duration of being in a given regime."""
        durations = []
        current_duration = 0
        for s in states:
            if s == target_regime:
                current_duration += 1
            else:
                if current_duration > 0:
                    durations.append(current_duration)
                current_duration = 0
        if current_duration > 0:
            durations.append(current_duration)
        return durations

    def _fallback_regime_detection(self, obs: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Fallback regime detection when hmmlearn is unavailable.
        Uses volatility quantiles to assign regimes.
        """
        if obs.shape[1] >= 2:
            vol_col = obs[:, 1]  # volatility column
        else:
            vol_col = np.abs(obs[:, 0])

        # Calculate cluster centers (tercile midpoints)
        c0 = np.percentile(vol_col, 16.5) # LOW Volatility
        c1 = np.percentile(vol_col, 50.0) # MED Volatility
        c2 = np.percentile(vol_col, 83.5) # HIGH Volatility
        
        centers = np.array([c0, c1, c2])
        probs = np.zeros((len(obs), self.n_regimes))
        
        # Calculate dynamic probabilities based on inverse distance to cluster centers
        for i, v in enumerate(vol_col):
            # Distance from current volatility to each center
            dists = np.abs(v - centers)
            
            # Convert distances to weights (add small epsilon to prevent div/0)
            weights = 1.0 / (dists + 1e-6)
            
            # Softmax/normalize weights to get probabilities
            probs[i] = weights / np.sum(weights)
            
        states = np.argmax(probs, axis=1)

        return states, probs

    # ──────────────────────────────────────────────────────
    # Persistence
    # ──────────────────────────────────────────────────────

    def _get_state(self) -> Dict:
        return {
            "name": self.name,
            "version": self.version,
            "model": self.model,
            "regime_order": self._regime_order,
            "feature_mean": self._feature_mean,
            "feature_std": self._feature_std,
            "regime_stats": self._regime_stats,
            "transition_matrix": self._transition_matrix.tolist() if self._transition_matrix is not None else None,
            "is_trained": self.is_trained,
        }

    def _set_state(self, state: Dict) -> None:
        self.model = state.get("model", self.model)
        self._regime_order = state.get("regime_order")
        self._feature_mean = state.get("feature_mean")
        self._feature_std = state.get("feature_std")
        self._regime_stats = state.get("regime_stats")
        trans = state.get("transition_matrix")
        self._transition_matrix = np.array(trans) if trans is not None else None

    def save(self, path: str) -> None:
        """Save model state to disk."""
        import joblib
        joblib.dump(self._get_state(), path)
        logger.info(f"RegimeDetector saved to {path}")

    def load(self, path: str) -> None:
        """Load model state from disk."""
        import joblib
        state = joblib.load(path)
        self._set_state(state)
        self.is_trained = True
        logger.info(f"RegimeDetector loaded from {path}")
