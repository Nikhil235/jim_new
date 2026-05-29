"""
Gold Data Manager - Incremental Data Download & Management
===========================================================
Handles incremental updates, metadata tracking, and automatic data synchronization.

This module:
1. Tracks last downloaded timestamps in a metadata file
2. Checks existing database for latest data
3. Downloads only missing data
4. Automatically invoked on application startup
"""

import os
import sys
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta, timezone
import pandas as pd
from loguru import logger
import yfinance as yf

# Setup logging
logger.remove()
logger.add(
    sys.stderr,
    format="<level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
)

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATABASE_FOLDER = PROJECT_ROOT / "Database"
DATABASE_FOLDER.mkdir(parents=True, exist_ok=True)

GOLD_RAW = DATABASE_FOLDER / "gold_raw"
GOLD_RAW.mkdir(parents=True, exist_ok=True)

GOLD_PROCESSED = DATABASE_FOLDER / "gold_processed"
GOLD_PROCESSED.mkdir(parents=True, exist_ok=True)

# Metadata file to track download history
METADATA_FILE = DATABASE_FOLDER / "gold_metadata.json"


class GoldDataManager:
    """Manages incremental gold data downloads and updates."""

    def __init__(self):
        self.symbol = "GC=F"  # Gold Futures
        self.symbol_spot = "XAUUSD=X"  # Fallback: Spot price
        self.start_year = 2000
        self.end_year = datetime.now().year
        self.metadata = self._load_metadata()

    def _load_metadata(self) -> dict:
        """Load metadata about previous downloads."""
        if METADATA_FILE.exists():
            try:
                with open(METADATA_FILE, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load metadata: {e}")
        
        # Default metadata
        return {
            "created": datetime.now(timezone.utc).isoformat(),
            "last_daily_update": None,
            "last_minute_update": None,
            "last_hourly_update": None,
            "daily_data_count": 0,
            "minute_data_count": 0,
            "hourly_data_count": 0,
            "daily_end_date": None,
            "minute_end_date": None,
            "hourly_end_date": None,
        }

    def _save_metadata(self):
        """Save metadata to JSON file."""
        try:
            with open(METADATA_FILE, "w") as f:
                json.dump(self.metadata, f, indent=2)
            logger.info(f"Metadata saved to {METADATA_FILE}")
        except Exception as e:
            logger.error(f"Failed to save metadata: {e}")

    def _get_last_timestamp_in_db(self, db_path: Path, table_name: str) -> datetime:
        """Get the last timestamp stored in the database."""
        try:
            if not db_path.exists():
                return None
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check if table exists
            cursor.execute(
                f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'"
            )
            if not cursor.fetchone():
                conn.close()
                return None
            
            # Get last timestamp
            cursor.execute(f"SELECT MAX(timestamp) FROM {table_name}")
            result = cursor.fetchone()
            conn.close()
            
            if result and result[0]:
                return pd.to_datetime(result[0])
            return None
            
        except Exception as e:
            logger.warning(f"Error querying database: {e}")
            return None

    def _download_and_merge(self, start_date: datetime, end_date: datetime, 
                           interval: str, db_path: Path, table_name: str) -> pd.DataFrame:
        """Download data for date range and merge with existing data."""
        logger.info(
            f"Downloading {interval} data from {start_date.date()} to {end_date.date()}..."
        )
        
        try:
            ticker = yf.Ticker(self.symbol)
            df = ticker.history(
                start=start_date,
                end=end_date,
                interval=interval
            )
            
            if df.empty:
                logger.warning(f"No data for {self.symbol}, trying {self.symbol_spot}...")
                ticker = yf.Ticker(self.symbol_spot)
                df = ticker.history(
                    start=start_date,
                    end=end_date,
                    interval=interval
                )
            
            if df.empty:
                logger.warning(f"No {interval} data available for date range")
                return df
            
            # Standardize columns
            df.columns = [col.lower().replace(" ", "_") for col in df.columns]
            df.index.name = "timestamp"
            
            # Remove unwanted columns
            unwanted = ["dividends", "stock_splits", "capital_gains"]
            df = df[[col for col in df.columns if col not in unwanted]]
            
            logger.info(f"Downloaded {len(df)} {interval} candles")
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to download {interval} data: {e}")
            return pd.DataFrame()

    def _append_to_sqlite(self, df: pd.DataFrame, db_path: Path, table_name: str):
        """Append new data to SQLite database (avoid duplicates)."""
        if df.empty:
            return
        
        try:
            df_reset = df.reset_index()
            
            # Convert timestamp to string for SQLite compatibility
            if 'timestamp' in df_reset.columns:
                df_reset['timestamp'] = df_reset['timestamp'].astype(str)
            
            conn = sqlite3.connect(db_path)
            
            # Check if table exists
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'"
            )
            table_exists = cursor.fetchone() is not None
            
            if table_exists:
                # Remove duplicates (data that already exists)
                min_timestamp = df_reset["timestamp"].min()
                conn.execute(f"DELETE FROM {table_name} WHERE timestamp >= ?", (min_timestamp,))
                logger.info(f"Removed overlapping data from {table_name}")
            
            # Insert new data
            df_reset.to_sql(table_name, conn, if_exists="append", index=False)
            
            # Create index if not exists
            conn.execute(f"CREATE INDEX IF NOT EXISTS idx_timestamp ON {table_name}(timestamp)")
            conn.commit()
            
            # Check count
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            
            logger.info(f"Table {table_name} now has {count} records")
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to append to database: {e}")

    def update_daily_data(self, force_full_update: bool = False) -> bool:
        """
        Update daily gold data. Downloads missing data from last stored date to today.
        
        Args:
            force_full_update: If True, re-download all historical data
        
        Returns:
            bool: True if update successful
        """
        logger.info("=" * 60)
        logger.info("UPDATING DAILY DATA")
        logger.info("=" * 60)
        
        db_path = GOLD_RAW / "gold_ohlcv.db"
        table_name = "gold_ohlcv"
        
        try:
            if force_full_update:
                logger.warning("FORCE FULL UPDATE MODE - Re-downloading all historical data")
                start_date = datetime(self.start_year, 1, 1)
            else:
                # Get last timestamp from database
                last_ts = self._get_last_timestamp_in_db(db_path, table_name)
                
                if last_ts:
                    logger.info(f"Last data in database: {last_ts}")
                    # Start from day after last timestamp
                    start_date = (last_ts + timedelta(days=1)).replace(hour=0, minute=0, second=0)
                else:
                    logger.info("No existing data found, starting from 2000")
                    start_date = datetime(self.start_year, 1, 1)
            
            end_date = datetime.now()
            
            # Skip if we're already up-to-date (within 1 day)
            if start_date.date() >= (end_date - timedelta(days=1)).date() and not force_full_update:
                logger.info("Daily data is already up-to-date")
                return True
            
            # Download data
            df = self._download_and_merge(start_date, end_date, "1d", db_path, table_name)
            
            if df.empty:
                logger.warning("No new daily data to save")
                return False
            
            # Append to database
            self._append_to_sqlite(df, db_path, table_name)
            
            # Also save combined CSV and Parquet
            self._save_combined_formats(db_path, table_name)
            
            # Update metadata
            self.metadata["last_daily_update"] = datetime.now(timezone.utc).isoformat()
            self.metadata["daily_end_date"] = df.index.max().isoformat()
            
            # Get total count
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            self.metadata["daily_data_count"] = cursor.fetchone()[0]
            conn.close()
            
            self._save_metadata()
            
            logger.info("✓ Daily data update complete")
            return True
            
        except Exception as e:
            logger.error(f"Daily update failed: {e}")
            return False

    def update_minute_data(self, days: int = 60, force_update: bool = False) -> bool:
        """
        Update 1-minute recent data. Yahoo Finance typically has ~8 days max per request.
        
        Args:
            days: Number of days to look back (will be fetched in 8-day chunks)
            force_update: If True, re-download even if recently updated
        
        Returns:
            bool: True if update successful
        """
        logger.info("=" * 60)
        logger.info("UPDATING 1-MINUTE DATA")
        logger.info("=" * 60)
        
        db_path = GOLD_PROCESSED / "minute_recent_ohlcv.db"
        table_name = "gold_minute"
        
        try:
            # Check if we should update (skip if updated in last hour)
            if not force_update and self.metadata.get("last_minute_update"):
                last_update = datetime.fromisoformat(self.metadata["last_minute_update"])
                if datetime.now(timezone.utc) - last_update < timedelta(hours=1):
                    logger.info("1-minute data was recently updated, skipping")
                    return True
            
            end_date = datetime.now()
            # Yahoo Finance limitation: only 8 days of 1-minute data per request
            # Fetch most recent 8 days available
            start_date = end_date - timedelta(days=8)
            
            logger.warning(
                f"Note: Yahoo Finance 1-minute data limited to ~8 days. "
                f"Fetching {(end_date - start_date).days} days of most recent data."
            )
            
            # Download data
            df = self._download_and_merge(start_date, end_date, "1m", db_path, table_name)
            
            if df.empty:
                logger.warning("No 1-minute data available")
                return False
            
            # Save the data
            self._append_to_sqlite(df, db_path, table_name)
            
            # Also save CSV and Parquet
            df.to_csv(GOLD_PROCESSED / "minute_recent_ohlcv.csv")
            self._save_parquet(df, GOLD_PROCESSED, "minute_recent_ohlcv.parquet")
            
            # Update metadata
            self.metadata["last_minute_update"] = datetime.now(timezone.utc).isoformat()
            self.metadata["minute_end_date"] = df.index.max().isoformat()
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            self.metadata["minute_data_count"] = cursor.fetchone()[0]
            conn.close()
            
            self._save_metadata()
            
            logger.info("✓ 1-minute data update complete")
            return True
            
        except Exception as e:
            logger.error(f"1-minute update failed: {e}")
            return False

    def update_hourly_data(self, months: int = 12, force_update: bool = False) -> bool:
        """
        Update hourly data. Yahoo Finance typically has ~1 year.
        
        Args:
            months: Number of months to look back
            force_update: If True, re-download even if recently updated
        
        Returns:
            bool: True if update successful
        """
        logger.info("=" * 60)
        logger.info("UPDATING HOURLY DATA")
        logger.info("=" * 60)
        
        db_path = GOLD_PROCESSED / "hourly_recent_ohlcv.db"
        table_name = "gold_hourly"
        
        try:
            # Check if we should update (skip if updated in last 2 hours)
            if not force_update and self.metadata.get("last_hourly_update"):
                last_update = datetime.fromisoformat(self.metadata["last_hourly_update"])
                if datetime.now(timezone.utc) - last_update < timedelta(hours=2):
                    logger.info("Hourly data was recently updated, skipping")
                    return True
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=months * 30)
            
            # Download data
            df = self._download_and_merge(start_date, end_date, "1h", db_path, table_name)
            
            if df.empty:
                logger.warning("No hourly data available")
                return False
            
            # Save the data
            self._append_to_sqlite(df, db_path, table_name)
            
            # Also save CSV and Parquet
            df.to_csv(GOLD_PROCESSED / "hourly_recent_ohlcv.csv")
            self._save_parquet(df, GOLD_PROCESSED, "hourly_recent_ohlcv.parquet")
            
            # Update metadata
            self.metadata["last_hourly_update"] = datetime.now(timezone.utc).isoformat()
            self.metadata["hourly_end_date"] = df.index.max().isoformat()
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            self.metadata["hourly_data_count"] = cursor.fetchone()[0]
            conn.close()
            
            self._save_metadata()
            
            logger.info("✓ Hourly data update complete")
            return True
            
        except Exception as e:
            logger.error(f"Hourly update failed: {e}")
            return False

    def _save_parquet(self, df: pd.DataFrame, folder: Path, filename: str):
        """Save data to Parquet format."""
        try:
            output_file = folder / filename
            df.to_parquet(output_file, compression="snappy", index=True)
            file_size_mb = output_file.stat().st_size / (1024 * 1024)
            logger.info(f"Saved {len(df)} records to {filename} ({file_size_mb:.2f} MB)")
        except Exception as e:
            logger.warning(f"Failed to save Parquet: {e}")

    def _save_combined_formats(self, db_path: Path, table_name: str):
        """Save combined data from database to CSV and Parquet."""
        try:
            conn = sqlite3.connect(db_path)
            df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
            conn.close()
            
            if not df.empty:
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                df = df.set_index("timestamp").sort_index()
                
                # Save CSV
                csv_path = GOLD_RAW / "daily_ohlcv.csv"
                df.to_csv(csv_path)
                logger.info(f"Saved combined daily CSV ({len(df)} records)")
                
                # Save Parquet
                self._save_parquet(df, GOLD_RAW, "gold_ohlcv.parquet")
                
        except Exception as e:
            logger.warning(f"Failed to save combined formats: {e}")

    def get_status(self) -> dict:
        """Get current data status."""
        status = {
            "daily": {
                "count": self.metadata.get("daily_data_count", 0),
                "last_update": self.metadata.get("last_daily_update"),
                "last_date": self.metadata.get("daily_end_date"),
            },
            "hourly": {
                "count": self.metadata.get("hourly_data_count", 0),
                "last_update": self.metadata.get("last_hourly_update"),
                "last_date": self.metadata.get("hourly_end_date"),
            },
            "minute": {
                "count": self.metadata.get("minute_data_count", 0),
                "last_update": self.metadata.get("last_minute_update"),
                "last_date": self.metadata.get("minute_end_date"),
            },
        }
        return status

    def run_incremental_update(self, force_daily: bool = False) -> bool:
        """
        Run incremental update of all data types.
        
        This is the main method called on application startup.
        
        Args:
            force_daily: If True, force re-download of all daily historical data
        
        Returns:
            bool: True if all updates successful
        """
        logger.info("=" * 80)
        logger.info("GOLD DATA INCREMENTAL UPDATE")
        logger.info("=" * 80)
        
        results = {
            "daily": False,
            "hourly": False,
            "minute": False,
        }
        
        # Update daily data (with longer gaps tolerance)
        try:
            results["daily"] = self.update_daily_data(force_full_update=force_daily)
        except Exception as e:
            logger.error(f"Daily update error: {e}")
        
        # Update hourly data
        try:
            results["hourly"] = self.update_hourly_data()
        except Exception as e:
            logger.error(f"Hourly update error: {e}")
        
        # Update 1-minute data
        try:
            results["minute"] = self.update_minute_data()
        except Exception as e:
            logger.error(f"Minute update error: {e}")
        
        logger.info("=" * 80)
        logger.info("UPDATE SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Daily:  {'✓' if results['daily'] else '✗'}")
        logger.info(f"Hourly: {'✓' if results['hourly'] else '✗'}")
        logger.info(f"Minute: {'✓' if results['minute'] else '✗'}")
        
        # Print status
        status = self.get_status()
        logger.info("\nDATA STATUS:")
        logger.info(f"  Daily:  {status['daily']['count']:,} records (last: {status['daily']['last_date']})")
        logger.info(f"  Hourly: {status['hourly']['count']:,} records (last: {status['hourly']['last_date']})")
        logger.info(f"  Minute: {status['minute']['count']:,} records (last: {status['minute']['last_date']})")
        
        logger.info("=" * 80)
        
        return all(results.values())


if __name__ == "__main__":
    manager = GoldDataManager()
    manager.run_incremental_update(force_daily=False)
