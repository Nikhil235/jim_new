"""
Pipeline Orchestrator
=====================
Central coordinator for the Phase 2 data acquisition pipeline.

Workflow:
  Step 1: Fetch gold price data (multiple symbols)
  Step 2: Fetch macro-correlate data (Yahoo + FRED)
  Step 3: Fetch alternative data (COT, sentiment, ETF flows)
  Step 4: Validate all data quality
  Step 5: Write to QuestDB (or parquet fallback)
  Step 6: Generate 200+ features
  Step 7: Store features (Redis + parquet)
  Step 8: Report pipeline health

Each step is independently retriable with exponential backoff.
"""

import time
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any

import pandas as pd
from loguru import logger

from src.utils.config import get_config
from src.ingestion.gold_fetcher import GoldDataFetcher
from src.ingestion.macro_fetcher import MacroFetcher
from src.ingestion.alternative_data import AlternativeDataManager
from src.ingestion.questdb_writer import QuestDBWriter
from src.ingestion.schema_manager import SchemaManager
from src.ingestion.data_quality import DataQualityMonitor
from src.ingestion.metrics_exporter import MetricsExporter
from src.features.engine import FeatureEngine
from src.features.feature_store import FeatureStore


@dataclass
class StepResult:
    """Result of a single pipeline step."""
    name: str
    status: str        # "success", "failed", "skipped"
    rows: int = 0
    duration_sec: float = 0.0
    error: Optional[str] = None
    details: dict = field(default_factory=dict)


@dataclass
class PipelineReport:
    """Full pipeline execution report."""
    mode: str
    start_time: str
    end_time: str = ""
    duration_sec: float = 0.0
    overall_status: str = "unknown"
    steps: List[StepResult] = field(default_factory=list)
    total_rows_ingested: int = 0
    feature_count: int = 0
    data_quality_status: str = "unknown"


class PipelineOrchestrator:
    """Orchestrates the full data acquisition and feature generation pipeline.

    Modes:
        full       — Run all steps (gold + macro + alt + features)
        gold-only  — Only fetch gold price data
        macro-only — Only fetch macro + FRED data
        features   — Only regenerate features from existing data
        incremental — Only fetch new data since last run
    """

    MODES = {"full", "gold-only", "macro-only", "features-only", "incremental"}

    def __init__(self, config: Optional[dict] = None):
        self.config = config or get_config()
        pipeline_cfg = self.config.get("pipeline", {}).get("orchestrator", {})
        self.max_retries = pipeline_cfg.get("max_retries", 3)

        # Initialize all components
        self.gold_fetcher = GoldDataFetcher(self.config)
        self.macro_fetcher = MacroFetcher(self.config)
        self.alt_data = AlternativeDataManager(self.config)
        self.writer = QuestDBWriter(self.config)
        self.schema_mgr = SchemaManager(self.config)
        self.quality = DataQualityMonitor(self.config)
        self.feature_engine = FeatureEngine(self.config)
        self.feature_store = FeatureStore(self.config)

        # Data storage between steps
        self._gold_df: Optional[pd.DataFrame] = None
        self._gold_multi: Dict[str, pd.DataFrame] = {}
        self._macro_data: Dict[str, pd.DataFrame] = {}
        self._fred_df: Optional[pd.DataFrame] = None
        self._alt_data: Dict[str, pd.DataFrame] = {}
        self._features_df: Optional[pd.DataFrame] = None

    def run(self, mode: str = "full") -> PipelineReport:
        """Execute the pipeline in the specified mode.

        Args:
            mode: One of 'full', 'gold-only', 'macro-only', 'features-only', 'incremental'.

        Returns:
            PipelineReport with per-step status and overall health.
        """
        if mode not in self.MODES:
            raise ValueError(f"Unknown mode: {mode}. Valid: {self.MODES}")

        report = PipelineReport(mode=mode, start_time=datetime.utcnow().isoformat())
        pipeline_start = time.time()

        logger.info("=" * 60)
        logger.info(f"  PIPELINE ORCHESTRATOR — Mode: {mode.upper()}")
        logger.info("=" * 60)

        # Step 0: Ensure QuestDB tables exist
        if mode != "features-only":
            report.steps.append(self._run_step("ensure_schemas", self._step_ensure_schemas))

        # Step 1: Fetch gold data
        if mode in {"full", "gold-only", "incremental"}:
            report.steps.append(self._run_step("fetch_gold", self._step_fetch_gold, mode=mode))

        # Step 2: Fetch macro data
        if mode in {"full", "macro-only"}:
            report.steps.append(self._run_step("fetch_macro", self._step_fetch_macro))
            report.steps.append(self._run_step("fetch_fred", self._step_fetch_fred))

        # Step 3: Fetch alternative data
        if mode == "full":
            report.steps.append(self._run_step("fetch_alt", self._step_fetch_alt))

        # Step 4: Data quality validation
        if mode != "features-only":
            report.steps.append(self._run_step("validate_quality", self._step_validate_quality))

        # Step 5: Write to QuestDB
        if mode != "features-only":
            report.steps.append(self._run_step("write_storage", self._step_write_storage))

        # Step 6: Generate features
        if mode in {"full", "features-only", "incremental"}:
            report.steps.append(self._run_step("generate_features", self._step_generate_features))

        # Step 7: Store features
        if mode in {"full", "features-only", "incremental"}:
            report.steps.append(self._run_step("store_features", self._step_store_features))

        # Finalize report
        report.end_time = datetime.utcnow().isoformat()
        report.duration_sec = round(time.time() - pipeline_start, 2)
        report.total_rows_ingested = sum(s.rows for s in report.steps)
        report.feature_count = self._features_df.shape[1] if self._features_df is not None else 0

        failed = [s for s in report.steps if s.status == "failed"]
        if failed:
            report.overall_status = "PARTIAL" if len(failed) < len(report.steps) else "FAILED"
        else:
            report.overall_status = "SUCCESS"

        self._print_report(report)
        return report

    def _run_step(self, name: str, func, **kwargs) -> StepResult:
        """Run a pipeline step with retry logic."""
        start = time.time()
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"\n--- Step: {name} (attempt {attempt}/{self.max_retries}) ---")
                rows, details = func(**kwargs)
                duration = round(time.time() - start, 2)
                logger.info(f"  ✅ {name}: {rows} rows in {duration}s")
                return StepResult(name=name, status="success", rows=rows, duration_sec=duration, details=details)
            except Exception as e:
                logger.error(f"  ❌ {name} attempt {attempt} failed: {e}")
                if attempt < self.max_retries:
                    wait = 2 ** attempt
                    logger.info(f"  Retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    duration = round(time.time() - start, 2)
                    return StepResult(name=name, status="failed", duration_sec=duration, error=str(e))

    # ──────────────────────────────────────────────────────
    # Pipeline Steps
    # ──────────────────────────────────────────────────────

    def _step_ensure_schemas(self) -> tuple:
        results = self.schema_mgr.ensure_all_tables()
        created = sum(1 for v in results.values() if v)
        return created, {"tables": results}

    def _step_fetch_gold(self, mode="full") -> tuple:
        if mode == "incremental":
            self._gold_df = self.gold_fetcher.fetch_incremental()
        else:
            self._gold_df = self.gold_fetcher.fetch_historical(period="10y", interval="1d")

        # Also save to parquet
        if self._gold_df is not None and not self._gold_df.empty:
            self.gold_fetcher.save_to_parquet(self._gold_df, "gold_primary")
            rows = len(self._gold_df)
        else:
            rows = 0

        return rows, {"symbol": self.gold_fetcher.data_config.get("symbol", "GC=F")}

    def _step_fetch_macro(self) -> tuple:
        self._macro_data = self.macro_fetcher.fetch_all_yahoo_macro(period="10y")
        self.macro_fetcher.save_macro_to_parquet(self._macro_data)

        # Compute Gold/Silver, Gold/Oil, Gold/DXY ratios
        if self._gold_df is not None and not self._gold_df.empty and self._macro_data:
            ratios = self.macro_fetcher.compute_ratios(self._gold_df, self._macro_data)
            if not ratios.empty:
                # Merge ratios into gold_df for feature engineering
                for col in ratios.columns:
                    self._gold_df[col] = ratios[col]
                logger.info(f"  Computed {len(ratios.columns)} cross-asset ratios")

        total = sum(len(df) for df in self._macro_data.values())
        return total, {"feeds": list(self._macro_data.keys())}

    def _step_fetch_fred(self) -> tuple:
        fred_raw = self.macro_fetcher.fetch_fred_data()
        if fred_raw:
            self._fred_df = self.macro_fetcher.fred_to_dataframe(fred_raw)
            self.macro_fetcher.save_fred_to_parquet(self._fred_df)
            return len(self._fred_df), {"series": list(fred_raw.keys())}
        return 0, {"series": [], "note": "FRED API key not set or no data"}

    def _step_fetch_alt(self) -> tuple:
        self._alt_data = self.alt_data.fetch_all()
        total = sum(len(df) for df in self._alt_data.values())
        return total, {"sources": list(self._alt_data.keys())}

    def _step_validate_quality(self) -> tuple:
        reports = {}
        if self._gold_df is not None and not self._gold_df.empty:
            reports["gold"] = self.quality.validate_ohlcv(self._gold_df, "gold_primary")
        for name, df in self._macro_data.items():
            reports[name] = self.quality.validate_ohlcv(df, f"macro_{name}")

        consolidated = self.quality.generate_report(reports)
        self.data_quality_status = consolidated["overall_health"]
        return consolidated["total_rows"], {"health": consolidated["overall_health"], "alerts": consolidated["total_alerts"]}

    def _step_write_storage(self) -> tuple:
        total = 0
        # Gold data
        if self._gold_df is not None and not self._gold_df.empty:
            total += self.writer.write_ohlcv(self._gold_df, "gold_1d", "XAUUSD")

        # Macro data
        if self._macro_data:
            total += self.writer.write_macro(self._macro_data)

        # FRED data
        if self._fred_df is not None and not self._fred_df.empty:
            total += self.writer.write_fred(self._fred_df)

        # Alternative data
        if "cot" in self._alt_data:
            total += self.writer.write_cot(self._alt_data["cot"])
        if "sentiment" in self._alt_data:
            total += self.writer.write_sentiment(self._alt_data["sentiment"])

        etf_data = {k.replace("etf_", ""): v for k, v in self._alt_data.items() if k.startswith("etf_")}
        if etf_data:
            total += self.writer.write_etf_flows(etf_data)

        return total, {"questdb_available": self.writer.is_available()}

    def _step_generate_features(self) -> tuple:
        # Load gold data if not in memory
        if self._gold_df is None or self._gold_df.empty:
            try:
                self._gold_df = self.gold_fetcher.load_from_parquet("gold_primary")
            except FileNotFoundError:
                raise RuntimeError("No gold data available for feature generation")

        # Load macro if not in memory
        if not self._macro_data:
            self._macro_data = self.macro_fetcher.load_macro_from_parquet()

        # Build alt_data dict from stored alternative data
        alt_data_for_features = {}
        if self._alt_data:
            alt_data_for_features = self._alt_data

        self._features_df = self.feature_engine.generate_all(
            self._gold_df,
            self._macro_data or None,
            alt_data_for_features or None,
        )
        feat_count = self.feature_engine.get_feature_count(self._features_df)
        return len(self._features_df), {"feature_count": feat_count}

    def _step_store_features(self) -> tuple:
        if self._features_df is None or self._features_df.empty:
            return 0, {"note": "No features to store"}
        count = self.feature_store.store_features_batch(self._features_df)
        return count, {"storage": "redis+parquet" if self.feature_store.is_available() else "parquet"}

    # ──────────────────────────────────────────────────────
    # Reporting
    # ──────────────────────────────────────────────────────

    def _print_report(self, report: PipelineReport):
        logger.info("")
        logger.info("=" * 60)
        logger.info(f"  PIPELINE REPORT — {report.overall_status}")
        logger.info("=" * 60)
        logger.info(f"  Mode:       {report.mode}")
        logger.info(f"  Duration:   {report.duration_sec}s")
        logger.info(f"  Rows:       {report.total_rows_ingested:,}")
        logger.info(f"  Features:   {report.feature_count}")
        logger.info("")

        for step in report.steps:
            icon = "✅" if step.status == "success" else "❌" if step.status == "failed" else "⏭️"
            logger.info(f"  {icon} {step.name}: {step.rows:,} rows ({step.duration_sec}s)")
            if step.error:
                logger.info(f"     Error: {step.error}")

        logger.info("=" * 60)
