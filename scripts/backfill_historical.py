"""
Historical Data Backfill Script
=================================
One-time script to download and persist 10+ years of historical data
into QuestDB (if available) and parquet files.

Downloads:
  - Gold: GC=F, XAUUSD=X, GLD, IAU (10 years daily)
  - Macro: DXY, VIX, TLT, TIP, Silver, Oil, CNY (10 years daily)
  - FRED: Fed Funds, Real Yields, Yield Curve, Trade-Weighted USD
  - COT: CFTC Commitments of Traders (3 years weekly)
  - ETF: GLD/IAU volume and flow proxy (5 years)

Usage:
    python scripts/backfill_historical.py              # Full backfill
    python scripts/backfill_historical.py --gold-only  # Just gold data
    python scripts/backfill_historical.py --dry-run    # Show what would be done
"""

import sys
import os
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import click
from loguru import logger

from src.utils.config import load_config, PROJECT_ROOT
from src.utils.logger import setup_logger


def _check_existing_data(raw_dir: Path) -> dict:
    """Check what data already exists locally."""
    existing = {}
    for f in raw_dir.glob("*.parquet"):
        try:
            import pandas as pd
            df = pd.read_parquet(f)
            existing[f.stem] = {
                "rows": len(df),
                "start": str(df.index[0]) if len(df) > 0 else None,
                "end": str(df.index[-1]) if len(df) > 0 else None,
                "size_mb": round(f.stat().st_size / 1_048_576, 2),
            }
        except Exception:
            existing[f.stem] = {"rows": 0, "error": "unreadable"}
    return existing


@click.command()
@click.option("--gold-only", is_flag=True, help="Only backfill gold data")
@click.option("--macro-only", is_flag=True, help="Only backfill macro data")
@click.option("--alt-only", is_flag=True, help="Only backfill alternative data")
@click.option("--dry-run", is_flag=True, help="Show what would be done")
@click.option("--force", is_flag=True, help="Re-download even if data exists")
@click.option("--config", default=None, help="Path to config YAML")
def main(gold_only: bool, macro_only: bool, alt_only: bool, dry_run: bool, force: bool, config: str):
    """Backfill historical data for the Mini-Medallion pipeline."""

    cfg = load_config(config)
    log_cfg = cfg.get("logging", {})
    setup_logger(level=log_cfg.get("level", "INFO"), log_file=log_cfg.get("file", "logs/backfill.log"))

    raw_dir = PROJECT_ROOT / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 60)
    logger.info("  HISTORICAL DATA BACKFILL")
    logger.info(f"  Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    logger.info("=" * 60)

    # Check existing data
    existing = _check_existing_data(raw_dir)
    if existing:
        logger.info(f"\nExisting data files: {len(existing)}")
        for name, info in existing.items():
            logger.info(f"  📦 {name}: {info.get('rows', '?')} rows | {info.get('start', '?')} → {info.get('end', '?')} ({info.get('size_mb', '?')} MB)")
        if not force:
            logger.info("\n  Use --force to re-download existing data")

    if dry_run:
        _show_dry_run(gold_only, macro_only, alt_only)
        return

    # Determine what to backfill
    do_all = not (gold_only or macro_only or alt_only)
    results = {}
    start_time = time.time()

    # ── Gold Data ──
    if do_all or gold_only:
        results.update(_backfill_gold(cfg, raw_dir, existing, force))

    # ── Macro Data ──
    if do_all or macro_only:
        results.update(_backfill_macro(cfg, raw_dir, existing, force))

    # ── Alternative Data ──
    if do_all or alt_only:
        results.update(_backfill_alternative(cfg, raw_dir, existing, force))

    # ── Write to QuestDB ──
    if do_all or gold_only:
        _write_to_questdb(cfg, raw_dir)

    # ── Generate Features ──
    if do_all:
        _generate_features(cfg, raw_dir)

    # Report
    duration = round(time.time() - start_time, 1)
    total_rows = sum(v for v in results.values() if isinstance(v, int))

    logger.info("")
    logger.info("=" * 60)
    logger.info("  BACKFILL COMPLETE")
    logger.info("=" * 60)
    logger.info(f"  Duration:    {duration}s")
    logger.info(f"  Total rows:  {total_rows:,}")
    logger.info(f"  Sources:     {len(results)}")
    logger.info("")

    for source, count in results.items():
        icon = "✅" if count > 0 else "❌"
        logger.info(f"  {icon} {source:30s} {count:>10,} rows")

    logger.info("=" * 60)


def _backfill_gold(cfg, raw_dir, existing, force) -> dict:
    """Download gold price data."""
    from src.ingestion.gold_fetcher import GoldDataFetcher

    logger.info("\n--- GOLD DATA BACKFILL ---")
    fetcher = GoldDataFetcher(cfg)
    results = {}

    # Multi-symbol fetch
    for name, symbol in fetcher.GOLD_SYMBOLS.items():
        parquet_name = f"gold_{symbol.replace('=', '_').replace('^', '')}"

        if parquet_name in existing and existing[parquet_name].get("rows", 0) > 100 and not force:
            logger.info(f"  ⏭️ {name} ({symbol}): already have {existing[parquet_name]['rows']} rows — skipping")
            results[name] = existing[parquet_name]["rows"]
            continue

        try:
            df = fetcher.fetch_historical(symbol=symbol, period="max", interval="1d")
            if not df.empty:
                fetcher.save_to_parquet(df, parquet_name)
                results[name] = len(df)
                logger.info(f"  ✅ {name} ({symbol}): {len(df)} bars | {df.index[0]} → {df.index[-1]}")
            else:
                results[name] = 0
                logger.warning(f"  ⚠️ {name} ({symbol}): empty result")
        except Exception as e:
            results[name] = 0
            logger.error(f"  ❌ {name} ({symbol}): {e}")

    # Save primary gold data
    primary_name = "gold_primary"
    if primary_name not in existing or force:
        try:
            df = fetcher.fetch_historical(period="max", interval="1d")
            if not df.empty:
                fetcher.save_to_parquet(df, primary_name)
                results["gold_primary"] = len(df)
        except Exception as e:
            logger.error(f"  ❌ gold_primary: {e}")
            results["gold_primary"] = 0

    return results


def _backfill_macro(cfg, raw_dir, existing, force) -> dict:
    """Download macro-correlate data."""
    from src.ingestion.macro_fetcher import MacroFetcher

    logger.info("\n--- MACRO DATA BACKFILL ---")
    macro = MacroFetcher(cfg)
    results = {}

    # Yahoo Finance macro feeds
    yahoo_data = macro.fetch_all_yahoo_macro(period="max")
    if yahoo_data:
        macro.save_macro_to_parquet(yahoo_data)
        for name, df in yahoo_data.items():
            results[f"macro_{name}"] = len(df)

    # FRED data
    logger.info("\n  Fetching FRED economic data...")
    fred_raw = macro.fetch_fred_data()
    if fred_raw:
        fred_df = macro.fred_to_dataframe(fred_raw)
        macro.save_fred_to_parquet(fred_df)
        results["fred"] = len(fred_df)
        for series_id, data in fred_raw.items():
            logger.info(f"  ✅ FRED {series_id}: {len(data)} observations")
    else:
        results["fred"] = 0
        logger.warning("  ⚠️ FRED data not fetched (API key may not be configured)")

    return results


def _backfill_alternative(cfg, raw_dir, existing, force) -> dict:
    """Download alternative data sources."""
    from src.ingestion.alternative_data import AlternativeDataManager

    logger.info("\n--- ALTERNATIVE DATA BACKFILL ---")
    alt = AlternativeDataManager(cfg)
    results = {}

    try:
        alt_data = alt.fetch_all()
        for name, df in alt_data.items():
            results[f"alt_{name}"] = len(df)
    except Exception as e:
        logger.error(f"Alternative data fetch failed: {e}")

    return results


def _write_to_questdb(cfg, raw_dir) -> None:
    """Write all parquet data to QuestDB if available."""
    from src.ingestion.questdb_writer import QuestDBWriter
    from src.ingestion.schema_manager import SchemaManager
    import pandas as pd

    writer = QuestDBWriter(cfg)
    if not writer.is_available():
        logger.info("\n  QuestDB not available — data persisted to parquet only")
        return

    logger.info("\n--- QUESTDB INGESTION ---")

    # Ensure schemas exist
    schema_mgr = SchemaManager(cfg)
    schema_mgr.ensure_all_tables()

    # Write gold data
    gold_file = raw_dir / "gold_primary.parquet"
    if gold_file.exists():
        try:
            gold_df = pd.read_parquet(gold_file)
            count = writer.write_ohlcv(gold_df, "gold_1d", "XAUUSD")
            logger.info(f"  ✅ gold_1d: {count} rows written")
        except Exception as e:
            logger.error(f"  ❌ gold_1d: {e}")

    # Write macro data
    for f in sorted(raw_dir.glob("macro_*.parquet")):
        try:
            df = pd.read_parquet(f)
            symbol = f.stem.replace("macro_", "").upper()
            count = writer.write_ohlcv(df, "macro_daily", symbol)
            logger.info(f"  ✅ macro_daily/{symbol}: {count} rows written")
        except Exception as e:
            logger.error(f"  ❌ {f.stem}: {e}")

    # Write FRED data
    fred_file = raw_dir / "fred_data.parquet"
    if fred_file.exists():
        try:
            fred_df = pd.read_parquet(fred_file)
            count = writer.write_fred(fred_df)
            logger.info(f"  ✅ fred_daily: {count} rows written")
        except Exception as e:
            logger.error(f"  ❌ fred_daily: {e}")

    # Write COT data
    cot_file = raw_dir / "cot_gold.parquet"
    if cot_file.exists():
        try:
            cot_df = pd.read_parquet(cot_file)
            count = writer.write_cot(cot_df)
            logger.info(f"  ✅ cot_weekly: {count} rows written")
        except Exception as e:
            logger.error(f"  ❌ cot_weekly: {e}")


def _generate_features(cfg, raw_dir) -> None:
    """Generate features from backfilled data."""
    import pandas as pd
    from src.features.engine import FeatureEngine
    from src.features.feature_store import FeatureStore
    from src.ingestion.macro_fetcher import MacroFetcher

    logger.info("\n--- FEATURE GENERATION ---")

    gold_file = raw_dir / "gold_primary.parquet"
    if not gold_file.exists():
        logger.warning("No gold data for feature generation")
        return

    gold_df = pd.read_parquet(gold_file)

    # Load macro data
    macro = MacroFetcher(cfg)
    macro_data = macro.get_all_macro_data()

    # Load alternative data for extended features
    alt_data = {}
    for f in raw_dir.glob("*.parquet"):
        if f.stem.startswith("cot_") or f.stem.startswith("sentiment_") or f.stem.startswith("etf_"):
            try:
                alt_data[f.stem] = pd.read_parquet(f)
            except Exception:
                pass

    # Generate features
    engine = FeatureEngine(cfg)
    features_df = engine.generate_all(gold_df, macro_data or None, alt_data or None)

    feat_names = engine.get_feature_names(features_df)
    logger.info(f"  Generated {len(feat_names)} features from {len(features_df)} rows")

    # Store features
    store = FeatureStore(cfg)
    store.store_features_batch(features_df)
    logger.info(f"  ✅ Features stored to {'Redis + parquet' if store.is_available() else 'parquet'}")


def _show_dry_run(gold_only, macro_only, alt_only):
    """Show what would be downloaded."""
    do_all = not (gold_only or macro_only or alt_only)

    logger.info("\nDRY RUN — The following data would be downloaded:")
    logger.info("")

    if do_all or gold_only:
        logger.info("  📊 GOLD DATA:")
        logger.info("     - GC=F (Gold Futures):    ~10 years daily")
        logger.info("     - XAUUSD=X (Gold Spot):   ~10 years daily")
        logger.info("     - GLD (SPDR Gold ETF):    ~10 years daily")
        logger.info("     - IAU (iShares Gold):     ~10 years daily")

    if do_all or macro_only:
        logger.info("  📈 MACRO DATA:")
        logger.info("     - DXY (USD Index):        ~10 years daily")
        logger.info("     - VIX:                    ~10 years daily")
        logger.info("     - TLT (Treasury ETF):     ~10 years daily")
        logger.info("     - TIP (TIPS ETF):         ~10 years daily")
        logger.info("     - SI=F (Silver):          ~10 years daily")
        logger.info("     - CL=F (Crude Oil):       ~10 years daily")
        logger.info("     - CNY=X (CNY/USD):        ~10 years daily")
        logger.info("  📉 FRED DATA:")
        logger.info("     - DFF (Fed Funds Rate):   full history")
        logger.info("     - DFII10 (Real Yield):    full history")
        logger.info("     - T10Y2Y (Yield Curve):   full history")
        logger.info("     - DTWEXBGS (Trade-W USD):  full history")

    if do_all or alt_only:
        logger.info("  📰 ALTERNATIVE DATA:")
        logger.info("     - COT Reports (CFTC):     ~3 years weekly")
        logger.info("     - News Sentiment:         ~1 year daily (or synthetic)")
        logger.info("     - ETF Flows (GLD/IAU):    ~5 years daily")

    logger.info("\n  Run without --dry-run to execute.")


if __name__ == "__main__":
    main()
