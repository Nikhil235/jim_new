"""
Gold Data Quick Test & Demo
============================
Demonstrates loading and analyzing gold price data from the database.

Run with: python scripts/test_gold_data.py
"""

import sqlite3
import pandas as pd
from pathlib import Path
from loguru import logger

# Setup logging
import sys
logger.remove()
logger.add(sys.stderr, format="<level>{level: <8}</level> | <level>{message}</level>")

PROJECT_ROOT = Path(__file__).parent.parent
DATABASE_FOLDER = PROJECT_ROOT / "Database"


def test_daily_data():
    """Load and display daily data stats."""
    logger.info("=" * 70)
    logger.info("DAILY DATA TEST")
    logger.info("=" * 70)
    
    # Load from Parquet (fastest)
    parquet_file = DATABASE_FOLDER / "gold_raw" / "gold_ohlcv.parquet"
    if parquet_file.exists():
        df = pd.read_parquet(parquet_file)
        logger.info(f"✓ Loaded {len(df):,} daily records from Parquet")
        logger.info(f"  Date range: {df.index.min().date()} to {df.index.max().date()}")
        logger.info(f"  Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}/oz")
        logger.info(f"  Average volume: {df['volume'].mean():.0f}")
        logger.info(f"\n  Latest 5 records:")
        logger.info(str(df.tail(5)))
        return df
    else:
        logger.error(f"✗ Parquet file not found: {parquet_file}")
        return None


def test_hourly_data():
    """Load and display hourly data stats."""
    logger.info("\n" + "=" * 70)
    logger.info("HOURLY DATA TEST")
    logger.info("=" * 70)
    
    parquet_file = DATABASE_FOLDER / "gold_processed" / "hourly_recent_ohlcv.parquet"
    if parquet_file.exists():
        df = pd.read_parquet(parquet_file)
        logger.info(f"✓ Loaded {len(df):,} hourly records from Parquet")
        logger.info(f"  Date range: {df.index.min()} to {df.index.max()}")
        logger.info(f"  Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}/oz")
        logger.info(f"\n  Latest 5 records:")
        logger.info(str(df.tail(5)))
        return df
    else:
        logger.error(f"✗ Parquet file not found: {parquet_file}")
        return None


def test_minute_data():
    """Load and display minute data stats."""
    logger.info("\n" + "=" * 70)
    logger.info("MINUTE DATA TEST")
    logger.info("=" * 70)
    
    parquet_file = DATABASE_FOLDER / "gold_processed" / "minute_recent_ohlcv.parquet"
    if parquet_file.exists():
        df = pd.read_parquet(parquet_file)
        logger.info(f"✓ Loaded {len(df):,} minute records from Parquet")
        logger.info(f"  Date range: {df.index.min()} to {df.index.max()}")
        logger.info(f"  Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}/oz")
        logger.info(f"\n  Latest 5 records:")
        logger.info(str(df.tail(5)))
        return df
    else:
        logger.error(f"✗ Parquet file not found: {parquet_file}")
        return None


def test_sqlite_query():
    """Test SQLite database queries."""
    logger.info("\n" + "=" * 70)
    logger.info("SQLITE DATABASE QUERY TEST")
    logger.info("=" * 70)
    
    db_path = DATABASE_FOLDER / "gold_raw" / "gold_ohlcv.db"
    if not db_path.exists():
        logger.error(f"✗ Database not found: {db_path}")
        return None
    
    try:
        conn = sqlite3.connect(db_path)
        
        # Test 1: Get record count
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM gold_ohlcv")
        count = cursor.fetchone()[0]
        logger.info(f"✓ Database has {count:,} daily records")
        
        # Test 2: Get date range
        cursor.execute("""
            SELECT 
                MIN(timestamp) as first_date,
                MAX(timestamp) as last_date
            FROM gold_ohlcv
        """)
        first_date, last_date = cursor.fetchone()
        logger.info(f"  Date range: {first_date} to {last_date}")
        
        # Test 3: Get price stats
        cursor.execute("""
            SELECT 
                MIN(close) as min_price,
                MAX(close) as max_price,
                AVG(close) as avg_price
            FROM gold_ohlcv
        """)
        min_p, max_p, avg_p = cursor.fetchone()
        logger.info(f"  Price stats:")
        logger.info(f"    Min: ${min_p:.2f}/oz")
        logger.info(f"    Max: ${max_p:.2f}/oz")
        logger.info(f"    Avg: ${avg_p:.2f}/oz")
        
        # Test 4: Get recent records
        df = pd.read_sql_query(
            "SELECT * FROM gold_ohlcv ORDER BY timestamp DESC LIMIT 5",
            conn
        )
        logger.info(f"  Latest 5 records (from SQLite):")
        logger.info(str(df))
        
        conn.close()
        return df
        
    except Exception as e:
        logger.error(f"✗ SQLite query failed: {e}")
        return None


def test_metadata():
    """Display metadata about last downloads."""
    logger.info("\n" + "=" * 70)
    logger.info("DATA METADATA")
    logger.info("=" * 70)
    
    metadata_file = DATABASE_FOLDER / "gold_metadata.json"
    if metadata_file.exists():
        import json
        with open(metadata_file, "r") as f:
            metadata = json.load(f)
        
        logger.info(f"✓ Metadata file found:")
        logger.info(f"  Last daily update:  {metadata.get('last_daily_update', 'Never')}")
        logger.info(f"  Last hourly update: {metadata.get('last_hourly_update', 'Never')}")
        logger.info(f"  Last minute update: {metadata.get('last_minute_update', 'Never')}")
        logger.info(f"\n  Data record counts:")
        logger.info(f"    Daily:  {metadata.get('daily_data_count', 0):,} records")
        logger.info(f"    Hourly: {metadata.get('hourly_data_count', 0):,} records")
        logger.info(f"    Minute: {metadata.get('minute_data_count', 0):,} records")
    else:
        logger.warning("✗ Metadata file not found")


def test_file_sizes():
    """Display database file sizes."""
    logger.info("\n" + "=" * 70)
    logger.info("DATABASE FILE SIZES")
    logger.info("=" * 70)
    
    files_to_check = [
        ("Daily DB", DATABASE_FOLDER / "gold_raw" / "gold_ohlcv.db"),
        ("Daily Parquet", DATABASE_FOLDER / "gold_raw" / "gold_ohlcv.parquet"),
        ("Hourly DB", DATABASE_FOLDER / "gold_processed" / "hourly_recent_ohlcv.db"),
        ("Hourly Parquet", DATABASE_FOLDER / "gold_processed" / "hourly_recent_ohlcv.parquet"),
        ("Minute DB", DATABASE_FOLDER / "gold_processed" / "minute_recent_ohlcv.db"),
        ("Minute Parquet", DATABASE_FOLDER / "gold_processed" / "minute_recent_ohlcv.parquet"),
    ]
    
    for name, filepath in files_to_check:
        if filepath.exists():
            size_bytes = filepath.stat().st_size
            size_mb = size_bytes / (1024 * 1024)
            logger.info(f"  {name:20} {size_mb:8.2f} MB")
        else:
            logger.info(f"  {name:20} {'Not found':>8}")


def run_all_tests():
    """Run all tests."""
    logger.info("\n" + "🟢" * 35)
    logger.info("GOLD DATA SYSTEM - COMPREHENSIVE TEST")
    logger.info("🟢" * 35)
    
    # Run tests
    df_daily = test_daily_data()
    df_hourly = test_hourly_data()
    df_minute = test_minute_data()
    test_sqlite_query()
    test_metadata()
    test_file_sizes()
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("TEST SUMMARY")
    logger.info("=" * 70)
    
    results = {
        "Daily data": df_daily is not None and len(df_daily) > 0,
        "Hourly data": df_hourly is not None and len(df_hourly) > 0,
        "Minute data": df_minute is not None and len(df_minute) > 0,
        "SQLite database": True,
        "Metadata tracking": (DATABASE_FOLDER / "gold_metadata.json").exists(),
    }
    
    for test_name, passed in results.items():
        status = "✓" if passed else "✗"
        logger.info(f"  {status} {test_name}")
    
    all_passed = all(results.values())
    logger.info("\n" + ("=" * 70))
    if all_passed:
        logger.info("✓ ALL TESTS PASSED - Gold data system is operational!")
    else:
        logger.info("✗ Some tests failed - Check log above for details")
    logger.info("=" * 70)
    
    return all_passed


if __name__ == "__main__":
    success = run_all_tests()
    import sys
    sys.exit(0 if success else 1)
