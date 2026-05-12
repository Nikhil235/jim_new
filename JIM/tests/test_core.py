"""
Unit tests for core components.
Run: pytest tests/test_core.py -v
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta


class TestWaveletDenoiser:
    """Tests for the wavelet de-noising model."""

    def setup_method(self):
        from src.models.wavelet import WaveletDenoiser
        self.model = WaveletDenoiser(wavelet="db4", levels=5)

    def test_denoise_reduces_variance(self):
        """De-noised signal should have less variance than original."""
        np.random.seed(42)
        # Create signal: trend + noise
        t = np.linspace(0, 10, 1000)
        trend = 1800 + 50 * np.sin(t)
        noise = np.random.randn(1000) * 20
        signal = trend + noise

        denoised = self.model.denoise(signal)

        assert len(denoised) == len(signal)
        assert np.std(denoised) < np.std(signal)

    def test_denoise_preserves_trend(self):
        """De-noised signal should follow the general trend."""
        np.random.seed(42)
        t = np.linspace(0, 4, 500)
        trend = 1800 + 100 * t  # Clear uptrend
        signal = trend + np.random.randn(500) * 10

        denoised = self.model.denoise(signal)

        # Correlation between denoised and trend should be very high
        corr = np.corrcoef(denoised, trend)[0, 1]
        assert corr > 0.95

    def test_frequency_bands(self):
        """Should decompose into named frequency bands."""
        np.random.seed(42)
        signal = np.random.randn(500) + 1800

        bands = self.model.get_frequency_bands(signal)

        assert "noise" in bands
        assert "trend" in bands
        for name, band in bands.items():
            assert len(band) == len(signal)

    def test_generate_signal_output_format(self):
        """Signal should be -1, 0, or 1 with confidence 0-1."""
        np.random.seed(42)
        prices = 1800 + np.cumsum(np.random.randn(300) * 5)

        signal, confidence = self.model.generate_signal(prices)

        assert signal in [-1, 0, 1]
        assert 0.0 <= confidence <= 1.0


class TestRegimeDetector:
    """Tests for the HMM regime detector."""

    def _make_sample_data(self, n=500):
        """Create sample gold-like data."""
        np.random.seed(42)
        dates = pd.date_range("2022-01-01", periods=n, freq="B")
        price = 1800 + np.cumsum(np.random.randn(n) * 10)
        return pd.DataFrame({
            "open": price + np.random.randn(n) * 2,
            "high": price + abs(np.random.randn(n) * 5),
            "low": price - abs(np.random.randn(n) * 5),
            "close": price,
            "volume": np.random.randint(10000, 100000, n),
        }, index=dates)

    def test_train_and_predict(self):
        """Should train and produce regime predictions."""
        from src.models.hmm_regime import RegimeDetector
        model = RegimeDetector(n_regimes=3, n_iter=100)
        df = self._make_sample_data()

        metrics = model.train(df)
        assert model.is_trained
        assert "regimes" in metrics

        states, confs = model.predict(df)
        assert len(states) > 0
        assert all(s in [0, 1, 2] for s in states)
        assert all(0 <= c <= 1 for c in confs)

    def test_get_current_regime(self):
        """Should return a named regime with confidence."""
        from src.models.hmm_regime import RegimeDetector
        model = RegimeDetector(n_regimes=3, n_iter=100)
        df = self._make_sample_data()
        model.train(df)

        regime, conf = model.get_current_regime(df)
        assert regime in ["GROWTH", "NORMAL", "CRISIS"]
        assert 0 <= conf <= 1


class TestRiskManager:
    """Tests for the risk management system."""

    def setup_method(self):
        from src.risk.manager import RiskManager
        self.rm = RiskManager()

    def test_kelly_positive_edge(self):
        """Positive edge should give positive position size."""
        size = self.rm.calculate_kelly_size(
            win_prob=0.55, avg_win=100, avg_loss=90,
            portfolio_value=100000, regime="NORMAL"
        )
        assert size > 0

    def test_kelly_no_edge(self):
        """No edge should give zero position size."""
        size = self.rm.calculate_kelly_size(
            win_prob=0.40, avg_win=100, avg_loss=100,
            portfolio_value=100000, regime="NORMAL"
        )
        assert size == 0

    def test_kelly_crisis_reduces_size(self):
        """Crisis regime should produce smaller position than normal."""
        normal = self.rm.calculate_kelly_size(
            win_prob=0.55, avg_win=100, avg_loss=90,
            portfolio_value=100000, regime="NORMAL"
        )
        crisis = self.rm.calculate_kelly_size(
            win_prob=0.55, avg_win=100, avg_loss=90,
            portfolio_value=100000, regime="CRISIS"
        )
        assert crisis < normal

    def test_kelly_max_cap(self):
        """Position should never exceed max_position_pct."""
        size = self.rm.calculate_kelly_size(
            win_prob=0.95, avg_win=1000, avg_loss=10,
            portfolio_value=100000, regime="NORMAL"
        )
        assert size <= 100000 * self.rm.max_position_pct

    def test_circuit_breaker_daily_loss(self):
        """Should halt after hitting daily loss limit."""
        self.rm.risk_state.daily_pnl = -2500  # -2.5% on 100K
        can_trade, reason = self.rm.check_circuit_breakers(100000)
        assert not can_trade
        assert "Daily loss" in reason

    def test_circuit_breaker_drawdown(self):
        """Should halt after hitting max drawdown."""
        self.rm.risk_state.current_drawdown = 0.11  # 11%
        can_trade, reason = self.rm.check_circuit_breakers(100000)
        assert not can_trade
        assert "drawdown" in reason.lower()

    def test_daily_reset(self):
        """Should clear daily counters."""
        self.rm.risk_state.daily_pnl = -1000
        self.rm.risk_state.is_halted = True
        self.rm.reset_daily()
        assert self.rm.risk_state.daily_pnl == 0
        assert not self.rm.risk_state.is_halted


class TestFeatureEngine:
    """Tests for the feature engineering pipeline."""

    def _make_sample_data(self, n=300):
        np.random.seed(42)
        dates = pd.date_range("2022-01-01", periods=n, freq="B")
        price = 1800 + np.cumsum(np.random.randn(n) * 10)
        return pd.DataFrame({
            "open": price + np.random.randn(n) * 2,
            "high": price + abs(np.random.randn(n) * 5),
            "low": price - abs(np.random.randn(n) * 5),
            "close": price,
            "volume": np.random.randint(10000, 100000, n),
        }, index=dates)

    def test_generates_features(self):
        """Should produce a DataFrame with many more columns."""
        from src.features.engine import FeatureEngine
        engine = FeatureEngine()
        df = self._make_sample_data()

        result = engine.generate_all(df)

        assert len(result.columns) > len(df.columns)
        assert len(result) > 0
        assert not result.isnull().any().any()

    def test_no_lookahead(self):
        """Feature values should not depend on future data."""
        from src.features.engine import FeatureEngine
        engine = FeatureEngine()
        df = self._make_sample_data(500)

        full_features = engine.generate_all(df)
        partial_features = engine.generate_all(df.iloc[:400])

        # The 399th row (0-indexed) should be identical in both
        common_cols = set(full_features.columns) & set(partial_features.columns)
        last_partial_idx = partial_features.index[-1]

        if last_partial_idx in full_features.index:
            for col in list(common_cols)[:10]:  # Check first 10 features
                val_full = full_features.loc[last_partial_idx, col]
                val_partial = partial_features.loc[last_partial_idx, col]
                if not np.isnan(val_full) and not np.isnan(val_partial):
                    assert abs(val_full - val_partial) < 1e-10, f"Lookahead in {col}"
