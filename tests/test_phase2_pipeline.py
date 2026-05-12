"""
Phase 2 Pipeline Tests
======================
Comprehensive test suite for data acquisition and feature generation.
Tests work WITHOUT Docker/QuestDB/Redis (pure parquet fallback mode).
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock


# ──────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────

@pytest.fixture
def sample_gold_df():
    """Generate realistic synthetic gold OHLCV data."""
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", periods=500, freq="B")
    price = 1800 + np.cumsum(np.random.randn(500) * 10)
    df = pd.DataFrame({
        "open": price + np.random.randn(500) * 2,
        "high": price + abs(np.random.randn(500) * 5),
        "low": price - abs(np.random.randn(500) * 5),
        "close": price,
        "volume": np.random.randint(10000, 100000, 500).astype(float),
    }, index=dates)
    df.index.name = "timestamp"
    df["returns"] = df["close"].pct_change()
    df["log_returns"] = np.log(df["close"] / df["close"].shift(1))
    df["spread"] = df["high"] - df["low"]
    df["typical_price"] = (df["high"] + df["low"] + df["close"]) / 3
    return df


@pytest.fixture
def sample_macro_data():
    """Generate synthetic macro data dict."""
    np.random.seed(123)
    dates = pd.date_range("2020-01-01", periods=500, freq="B")
    macro = {}
    for name, base in [("dxy", 100), ("vix", 20), ("tlt", 130), ("silver", 25)]:
        price = base + np.cumsum(np.random.randn(500) * 0.5)
        df = pd.DataFrame({
            "open": price, "high": price + 0.5, "low": price - 0.5,
            "close": price, "volume": np.random.randint(1000, 50000, 500).astype(float),
        }, index=dates)
        df.index.name = "timestamp"
        df["returns"] = df["close"].pct_change()
        macro[name] = df
    return macro


@pytest.fixture
def config():
    """Load test config."""
    from src.utils.config import load_config
    return load_config()


# ──────────────────────────────────────────────────────────
# Test: Feature Engine (200+ features)
# ──────────────────────────────────────────────────────────

class TestFeatureEngine:
    def test_feature_count_without_macro(self, sample_gold_df):
        """Feature engine should produce 150+ features from OHLCV alone."""
        from src.features.engine import FeatureEngine
        engine = FeatureEngine()
        features = engine.generate_all(sample_gold_df)
        feat_names = engine.get_feature_names(features)
        assert len(feat_names) >= 150, f"Only {len(feat_names)} features — need 150+"

    def test_feature_count_with_macro(self, sample_gold_df, sample_macro_data):
        """With macro data, should exceed 200 features."""
        from src.features.engine import FeatureEngine
        engine = FeatureEngine()
        features = engine.generate_all(sample_gold_df, sample_macro_data)
        feat_names = engine.get_feature_names(features)
        assert len(feat_names) >= 200, f"Only {len(feat_names)} features — need 200+"

    def test_no_inf_values(self, sample_gold_df):
        """Features should have no infinite values after dropna."""
        from src.features.engine import FeatureEngine
        engine = FeatureEngine()
        features = engine.generate_all(sample_gold_df)
        inf_count = np.isinf(features.select_dtypes(include=[np.number])).sum().sum()
        assert inf_count == 0, f"Found {inf_count} infinite values"

    def test_temporal_features_present(self, sample_gold_df):
        """Cyclical temporal features should be present."""
        from src.features.engine import FeatureEngine
        engine = FeatureEngine()
        features = engine.generate_all(sample_gold_df)
        for col in ["dow_sin", "dow_cos", "month_sin", "month_cos"]:
            assert col in features.columns, f"Missing temporal feature: {col}"

    def test_lag_features_present(self, sample_gold_df):
        """Lag features should be present."""
        from src.features.engine import FeatureEngine
        engine = FeatureEngine()
        features = engine.generate_all(sample_gold_df)
        for lag in [1, 2, 3, 5]:
            assert f"return_lag_{lag}" in features.columns

    def test_regime_features_present(self, sample_gold_df):
        """Regime detection proxies should be present."""
        from src.features.engine import FeatureEngine
        engine = FeatureEngine()
        features = engine.generate_all(sample_gold_df)
        assert "adx_14" in features.columns
        assert "zscore_20" in features.columns

    def test_microstructure_proxies(self, sample_gold_df):
        """Microstructure proxy features should be present."""
        from src.features.engine import FeatureEngine
        engine = FeatureEngine()
        features = engine.generate_all(sample_gold_df)
        assert "amihud" in features.columns
        assert "close_location" in features.columns

    def test_event_proximity(self, sample_gold_df):
        """Event proximity features should be present."""
        from src.features.engine import FeatureEngine
        engine = FeatureEngine()
        features = engine.generate_all(sample_gold_df)
        assert "fomc_proximity" in features.columns
        assert "nfp_proximity" in features.columns


# ──────────────────────────────────────────────────────────
# Test: Data Quality Monitor
# ──────────────────────────────────────────────────────────

class TestDataQuality:
    def test_validate_good_data(self, sample_gold_df):
        """Good data should pass validation."""
        from src.ingestion.data_quality import DataQualityMonitor
        monitor = DataQualityMonitor()
        report = monitor.validate_ohlcv(sample_gold_df, "test_gold")
        assert report["overall_status"] in ("PASS", "WARNING")

    def test_detect_empty_data(self):
        """Empty DataFrame should trigger FAIL."""
        from src.ingestion.data_quality import DataQualityMonitor
        monitor = DataQualityMonitor()
        report = monitor.validate_ohlcv(pd.DataFrame(), "empty")
        assert report["overall_status"] == "FAIL"

    def test_detect_missing_columns(self):
        """Missing OHLC columns should trigger alert."""
        from src.ingestion.data_quality import DataQualityMonitor
        monitor = DataQualityMonitor()
        df = pd.DataFrame({"price": [1, 2, 3]}, index=pd.date_range("2024-01-01", periods=3))
        report = monitor.validate_ohlcv(df, "bad_cols")
        assert report["overall_status"] == "FAIL"

    def test_detect_high_low_inversion(self):
        """high < low should be detected."""
        from src.ingestion.data_quality import DataQualityMonitor
        monitor = DataQualityMonitor()
        df = pd.DataFrame({
            "open": [100], "high": [95], "low": [105], "close": [100],
        }, index=pd.date_range("2024-01-01", periods=1))
        report = monitor.validate_ohlcv(df, "inverted")
        assert report["checks"]["ohlc_sanity"]["sanity_issues"] > 0

    def test_cross_source_alignment(self, sample_gold_df, sample_macro_data):
        """Cross-source alignment check should work."""
        from src.ingestion.data_quality import DataQualityMonitor
        monitor = DataQualityMonitor()
        sources = {"gold": sample_gold_df, **sample_macro_data}
        result = monitor.check_cross_source_alignment(sources)
        assert result["status"] in ("aligned", "misaligned")

    def test_staleness_check(self):
        """Staleness check should detect old data."""
        from src.ingestion.data_quality import DataQualityMonitor
        monitor = DataQualityMonitor()
        old_time = datetime.utcnow() - timedelta(hours=1)
        result = monitor.check_staleness("test", old_time)
        assert result["status"] == "stale"


# ──────────────────────────────────────────────────────────
# Test: QuestDB Writer (Parquet Fallback)
# ──────────────────────────────────────────────────────────

class TestQuestDBWriter:
    def test_parquet_fallback(self, sample_gold_df, tmp_path):
        """Writer should fall back to parquet when QuestDB is offline."""
        from src.ingestion.questdb_writer import QuestDBWriter
        writer = QuestDBWriter()
        writer.host = "127.0.0.1"
        writer.ilp_port = 59999  # Force offline
        writer.fallback_dir = tmp_path
        rows = writer.write_ohlcv(sample_gold_df, "gold_test", "XAUUSD")
        assert rows == len(sample_gold_df)
        assert (tmp_path / "gold_test_XAUUSD.parquet").exists()

    def test_data_catalog(self, sample_gold_df, tmp_path):
        """Data catalog should list parquet files."""
        from src.ingestion.questdb_writer import QuestDBWriter
        writer = QuestDBWriter()
        writer.host = "127.0.0.1"
        writer.ilp_port = 59999  # Force offline
        writer.fallback_dir = tmp_path
        writer.write_ohlcv(sample_gold_df, "gold_test", "XAUUSD")
        catalog = writer.get_data_catalog()
        assert "gold_test_XAUUSD" in catalog["tables"]


# ──────────────────────────────────────────────────────────
# Test: Feature Store (Parquet Fallback)
# ──────────────────────────────────────────────────────────

class TestFeatureStore:
    def test_store_and_retrieve(self, sample_gold_df, tmp_path):
        """Features should round-trip through parquet store."""
        from src.features.engine import FeatureEngine
        from src.features.feature_store import FeatureStore
        engine = FeatureEngine()
        features = engine.generate_all(sample_gold_df)

        store = FeatureStore()
        store._fallback_dir = tmp_path
        store._redis = None
        count = store.store_features(features, "TEST")
        assert count > 0

        latest = store.get_latest_features("TEST")
        assert latest is not None
        assert len(latest) > 50

    def test_feature_drift_report(self, sample_gold_df, tmp_path):
        """Drift report should work on stored features."""
        from src.features.engine import FeatureEngine
        from src.features.feature_store import FeatureStore
        engine = FeatureEngine()
        features = engine.generate_all(sample_gold_df)

        store = FeatureStore()
        store._fallback_dir = tmp_path
        store._redis = False  # Sentinel: prevents reconnection attempts
        store._redis_host = "127.0.0.1"
        store._redis_port = 59999  # Unreachable
        store.store_features(features, "DRIFT_TEST")

        drift = store.get_feature_drift_report("DRIFT_TEST")
        assert drift is not None
        assert drift["status"] in ("stable", "drift_detected")


# ──────────────────────────────────────────────────────────
# Test: Schema Manager
# ──────────────────────────────────────────────────────────

class TestSchemaManager:
    def test_schema_names_defined(self):
        """All expected tables should be defined in SCHEMAS."""
        from src.ingestion.schema_manager import SchemaManager, SCHEMAS
        expected = ["gold_1d", "gold_1h", "macro_daily", "fred_daily",
                     "cot_weekly", "sentiment_daily", "etf_flows_daily"]
        for table in expected:
            assert table in SCHEMAS, f"Missing schema: {table}"


# ──────────────────────────────────────────────────────────
# Test: Gold Fetcher
# ──────────────────────────────────────────────────────────

class TestGoldFetcher:
    def test_gold_symbols_defined(self):
        """All gold instruments should be defined."""
        from src.ingestion.gold_fetcher import GoldDataFetcher
        fetcher = GoldDataFetcher()
        assert "gold_futures" in fetcher.GOLD_SYMBOLS
        assert "gold_spot" in fetcher.GOLD_SYMBOLS

    def test_save_load_parquet(self, sample_gold_df, tmp_path):
        """Save and load should round-trip."""
        from src.ingestion.gold_fetcher import GoldDataFetcher
        fetcher = GoldDataFetcher()
        fetcher.raw_dir = tmp_path
        fetcher.save_to_parquet(sample_gold_df, "test_gold")
        loaded = fetcher.load_from_parquet("test_gold")
        assert len(loaded) == len(sample_gold_df)


# ──────────────────────────────────────────────────────────
# Test: Macro Fetcher
# ──────────────────────────────────────────────────────────

class TestMacroFetcher:
    def test_yahoo_symbols_defined(self):
        """All macro symbols should be defined."""
        from src.ingestion.macro_fetcher import MacroFetcher
        fetcher = MacroFetcher()
        expected = ["dxy", "vix", "tlt", "tip", "silver", "oil", "cny"]
        for name in expected:
            assert name in fetcher.YAHOO_SYMBOLS

    def test_compute_ratios(self, sample_gold_df, sample_macro_data):
        """Cross-asset ratios should compute without error."""
        from src.ingestion.macro_fetcher import MacroFetcher
        fetcher = MacroFetcher()
        ratios = fetcher.compute_ratios(sample_gold_df, sample_macro_data)
        assert "gold_silver_ratio" in ratios.columns

    def test_fred_to_dataframe(self):
        """FRED series should convert to aligned DataFrame."""
        from src.ingestion.macro_fetcher import MacroFetcher
        fetcher = MacroFetcher()
        dates = pd.date_range("2024-01-01", periods=10)
        fred_data = {
            "DFF": pd.Series(np.random.rand(10), index=dates),
            "DFII10": pd.Series(np.random.rand(10), index=dates),
        }
        df = fetcher.fred_to_dataframe(fred_data)
        assert len(df) == 10
        assert "DFF" in df.columns


# ──────────────────────────────────────────────────────────
# Test: Alternative Data
# ──────────────────────────────────────────────────────────

class TestAlternativeData:
    def test_cot_synthetic(self):
        """Synthetic COT data should be valid."""
        from src.ingestion.alternative_data import COTParser
        parser = COTParser()
        df = parser._generate_synthetic_cot()
        assert len(df) > 100
        assert "net_commercial" in df.columns
        assert "net_noncommercial" in df.columns

    def test_sentiment_scoring(self):
        """Sentiment scorer should produce valid scores."""
        from src.ingestion.alternative_data import SentimentScorer
        scorer = SentimentScorer()
        headlines = [
            "Gold rallies on safe haven demand",
            "Strong dollar pushes gold lower",
            "Markets calm, gold trades flat",
        ]
        result = scorer.score_headlines(headlines)
        assert -1 <= result["keyword_score"] <= 1
        assert result["article_count"] == 3

    def test_synthetic_sentiment(self):
        """Synthetic sentiment should generate valid data."""
        from src.ingestion.alternative_data import SentimentScorer
        scorer = SentimentScorer()
        df = scorer.generate_synthetic_sentiment(days=100)
        assert len(df) == 100
        assert "keyword_score" in df.columns


# ──────────────────────────────────────────────────────────
# Test: Pipeline Orchestrator (Offline Mode)
# ──────────────────────────────────────────────────────────

class TestPipelineOrchestrator:
    def test_valid_modes(self):
        """All expected modes should be valid."""
        from src.ingestion.pipeline_orchestrator import PipelineOrchestrator
        assert "full" in PipelineOrchestrator.MODES
        assert "incremental" in PipelineOrchestrator.MODES
        assert "features-only" in PipelineOrchestrator.MODES

    def test_invalid_mode_raises(self):
        """Invalid mode should raise ValueError."""
        from src.ingestion.pipeline_orchestrator import PipelineOrchestrator
        orch = PipelineOrchestrator()
        with pytest.raises(ValueError):
            orch.run(mode="invalid_mode")
