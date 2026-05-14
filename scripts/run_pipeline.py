"""
Pipeline Runner — CLI Entry Point
==================================
Run the Phase 2 data acquisition pipeline.

Usage:
    python scripts/run_pipeline.py --mode full
    python scripts/run_pipeline.py --mode gold-only
    python scripts/run_pipeline.py --mode incremental
    python scripts/run_pipeline.py --mode features-only
    python scripts/run_pipeline.py --report
"""

import sys
import os

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import click
from loguru import logger

from src.utils.config import load_config
from src.utils.logger import setup_logger


@click.command()
@click.option("--mode", default="full",
              type=click.Choice(["full", "gold-only", "macro-only", "features-only", "incremental"]),
              help="Pipeline execution mode")
@click.option("--config", default=None, help="Path to config YAML")
@click.option("--report", is_flag=True, help="Show data catalog report only (no fetching)")
@click.option("--dry-run", is_flag=True, help="Show what would be done without executing")
def main(mode: str, config: str, report: bool, dry_run: bool):
    """Mini-Medallion Data Pipeline Runner."""

    cfg = load_config(config)
    log_cfg = cfg.get("logging", {})
    setup_logger(level=log_cfg.get("level", "INFO"), log_file=log_cfg.get("file", "logs/pipeline.log"))

    logger.info("=" * 60)
    logger.info("  MINI-MEDALLION DATA PIPELINE")
    logger.info("=" * 60)

    if report:
        _show_report(cfg)
        return

    if dry_run:
        _show_dry_run(mode)
        return

    # Run pipeline
    from src.ingestion.pipeline_orchestrator import PipelineOrchestrator
    orchestrator = PipelineOrchestrator(cfg)
    pipeline_report = orchestrator.run(mode=mode)

    # Exit code based on result
    if pipeline_report.overall_status == "FAILED":
        sys.exit(1)
    elif pipeline_report.overall_status == "PARTIAL":
        sys.exit(2)
    sys.exit(0)


def _show_report(cfg):
    """Show current data catalog and pipeline health."""
    from src.ingestion.questdb_writer import QuestDBWriter
    from src.features.feature_store import FeatureStore
    from pathlib import Path

    logger.info("\n--- DATA CATALOG ---")

    writer = QuestDBWriter(cfg)
    catalog = writer.get_data_catalog()
    logger.info(f"QuestDB available: {catalog['questdb_available']}")

    for name, info in catalog.get("tables", {}).items():
        logger.info(f"  📦 {name}: {info.get('rows', '?')} rows | {info.get('first_date', '?')} → {info.get('last_date', '?')}")

    logger.info("\n--- FEATURE STORE ---")
    fs = FeatureStore(cfg)
    meta = fs.get_metadata()
    logger.info(f"Redis available: {meta['redis_available']}")
    logger.info(f"Parquet files: {meta['parquet_files']} ({meta['total_parquet_size_mb']} MB)")

    # Check raw data files
    raw_dir = Path(cfg.get("_project_root", ".")) / "data" / "raw"
    if raw_dir.exists():
        logger.info("\n--- RAW DATA FILES ---")
        for f in sorted(raw_dir.glob("*.parquet")):
            size_mb = f.stat().st_size / 1_048_576
            logger.info(f"  📄 {f.name}: {size_mb:.2f} MB")


def _show_dry_run(mode):
    """Show what the pipeline would do without executing."""
    steps = {
        "full": [
            "1. Ensure QuestDB schemas (10 tables)",
            "2. Fetch gold data (GC=F, 10 years daily)",
            "3. Fetch macro data (DXY, VIX, TLT, TIP, Silver, Oil, CNY)",
            "4. Fetch FRED data (DFF, DFII10, T10Y2Y, DTWEXBGS)",
            "5. Fetch alternative data (COT, sentiment, ETF flows)",
            "6. Validate data quality (all sources)",
            "7. Write to QuestDB (or parquet fallback)",
            "8. Generate 200+ features",
            "9. Store features (Redis + parquet)",
        ],
        "gold-only": [
            "1. Ensure QuestDB schemas",
            "2. Fetch gold data (GC=F, 10 years daily)",
            "3. Validate data quality",
            "4. Write to QuestDB",
        ],
        "macro-only": [
            "1. Ensure QuestDB schemas",
            "2. Fetch macro data (7 Yahoo feeds)",
            "3. Fetch FRED data (4 series)",
            "4. Validate data quality",
            "5. Write to QuestDB",
        ],
        "features-only": [
            "1. Load existing gold data from parquet",
            "2. Load existing macro data from parquet",
            "3. Generate 200+ features",
            "4. Store features (Redis + parquet)",
        ],
        "incremental": [
            "1. Ensure QuestDB schemas",
            "2. Fetch new gold data since last run",
            "3. Validate data quality",
            "4. Write to QuestDB",
            "5. Regenerate features",
            "6. Update feature store",
        ],
    }

    logger.info(f"\nDRY RUN — Mode: {mode}")
    logger.info("Steps that would execute:")
    for step in steps.get(mode, []):
        logger.info(f"  {step}")
    logger.info("\nRun without --dry-run to execute.")


if __name__ == "__main__":
    main()
