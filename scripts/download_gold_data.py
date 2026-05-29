"""
Gold Price Data Downloader
===========================
Downloads gold (XAU/USD) OHLCV data from year 2000 onwards.

NOTE: 1-minute data limitations:
- Yahoo Finance: ~60 days of 1-minute data max (most recent data only)
- For historical data (2000-present), we use daily data and provide hourly where available
- For recent data, we fetch 1-minute candles

This script saves data in multiple formats:
1. CSV files (by year)
2. Parquet (compressed, queryable)
3. SQLite database (for efficient querying)
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from loguru import logger
import yfinance as yf
import sqlite3

# Setup logging
logger.remove()
logger.add(sys.stderr, format="<level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>")

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATABASE_FOLDER = PROJECT_ROOT / "Database"
DATABASE_FOLDER.mkdir(parents=True, exist_ok=True)

GOLD_RAW = DATABASE_FOLDER / "gold_raw"
GOLD_RAW.mkdir(parents=True, exist_ok=True)

GOLD_PROCESSED = DATABASE_FOLDER / "gold_processed"
GOLD_PROCESSED.mkdir(parents=True, exist_ok=True)

logger.info(f"Database folder: {DATABASE_FOLDER}")
logger.info(f"Raw data: {GOLD_RAW}")
logger.info(f"Processed data: {GOLD_PROCESSED}")


class GoldDataDownloader:
    """Download and save gold price data from 2000 onwards."""

    def __init__(self):
        self.symbol = "GC=F"  # Gold Futures (CME) - most liquid
        self.symbol_spot = "XAUUSD=X"  # Alternative: spot price
        self.start_year = 2000
        self.end_year = datetime.now().year

    def download_daily_historical(self) -> pd.DataFrame:
        """
        Download daily gold data from 2000 to present.
        
        Yahoo Finance reliably provides daily data going back decades.
        """
        logger.info("Downloading daily historical data (2000-present)...")
        
        try:
            ticker = yf.Ticker(self.symbol)
            df = ticker.history(
                start=f"{self.start_year}-01-01",
                end=datetime.now().strftime("%Y-%m-%d"),
                interval="1d"
            )
            
            if df.empty:
                logger.warning(f"No daily data for {self.symbol}, trying {self.symbol_spot}...")
                ticker = yf.Ticker(self.symbol_spot)
                df = ticker.history(
                    start=f"{self.start_year}-01-01",
                    end=datetime.now().strftime("%Y-%m-%d"),
                    interval="1d"
                )
            
            # Standardize columns
            df.columns = [col.lower().replace(" ", "_") for col in df.columns]
            df.index.name = "timestamp"
            
            # Remove unwanted columns
            unwanted = ["dividends", "stock_splits", "capital_gains"]
            df = df[[col for col in df.columns if col not in unwanted]]
            
            # Calculate returns
            df["returns"] = df["close"].pct_change()
            
            logger.info(f"Downloaded {len(df)} daily candles from {df.index[0]} to {df.index[-1]}")
            logger.info(f"Date range: {df.index.min()} to {df.index.max()}")
            logger.info(f"Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to download daily data: {e}")
            return pd.DataFrame()

    def download_minute_recent(self, days: int = 60) -> pd.DataFrame:
        """
        Download recent 1-minute data (last ~60 days of available data).
        
        Yahoo Finance typically has ~60 days of 1-minute resolution data.
        """
        logger.info(f"Downloading 1-minute data for last {days} days...")
        
        try:
            ticker = yf.Ticker(self.symbol)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            df = ticker.history(
                start=start_date.strftime("%Y-%m-%d"),
                end=end_date.strftime("%Y-%m-%d"),
                interval="1m"
            )
            
            if df.empty:
                logger.warning(f"No 1-minute data for {self.symbol}, trying {self.symbol_spot}...")
                ticker = yf.Ticker(self.symbol_spot)
                df = ticker.history(
                    start=start_date.strftime("%Y-%m-%d"),
                    end=end_date.strftime("%Y-%m-%d"),
                    interval="1m"
                )
            
            if df.empty:
                logger.warning("No 1-minute data available")
                return pd.DataFrame()
            
            # Standardize columns
            df.columns = [col.lower().replace(" ", "_") for col in df.columns]
            df.index.name = "timestamp"
            
            # Remove unwanted columns
            unwanted = ["dividends", "stock_splits", "capital_gains"]
            df = df[[col for col in df.columns if col not in unwanted]]
            
            logger.info(f"Downloaded {len(df)} 1-minute candles from {df.index[0]} to {df.index[-1]}")
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to download 1-minute data: {e}")
            return pd.DataFrame()

    def download_hourly_recent(self, months: int = 12) -> pd.DataFrame:
        """
        Download recent hourly data (last 12 months).
        
        Hourly data is more reliable than 1-minute for historical periods.
        """
        logger.info(f"Downloading 1-hour data for last {months} months...")
        
        try:
            ticker = yf.Ticker(self.symbol)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=months*30)
            
            df = ticker.history(
                start=start_date.strftime("%Y-%m-%d"),
                end=end_date.strftime("%Y-%m-%d"),
                interval="1h"
            )
            
            if df.empty:
                logger.warning(f"No hourly data for {self.symbol}")
                return pd.DataFrame()
            
            # Standardize columns
            df.columns = [col.lower().replace(" ", "_") for col in df.columns]
            df.index.name = "timestamp"
            
            # Remove unwanted columns
            unwanted = ["dividends", "stock_splits", "capital_gains"]
            df = df[[col for col in df.columns if col not in unwanted]]
            
            logger.info(f"Downloaded {len(df)} hourly candles from {df.index[0]} to {df.index[-1]}")
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to download hourly data: {e}")
            return pd.DataFrame()

    def save_csv_by_year(self, df: pd.DataFrame, folder: Path, prefix: str = "gold"):
        """Save data split by year into separate CSV files."""
        logger.info(f"Saving {prefix} data by year to CSV...")
        
        if df.empty:
            logger.warning("No data to save")
            return
        
        df["year"] = df.index.year
        
        for year in sorted(df["year"].unique()):
            year_df = df[df["year"] == year].drop("year", axis=1)
            filename = folder / f"{prefix}_{year}_ohlcv.csv"
            year_df.to_csv(filename)
            logger.info(f"  Saved {len(year_df)} records to {filename.name}")
        
        logger.info(f"Saved {len(df['year'].unique())} year files")

    def save_parquet(self, df: pd.DataFrame, folder: Path, filename: str = "gold_ohlcv.parquet"):
        """Save data to Parquet format (compressed, queryable)."""
        logger.info("Saving data to Parquet...")
        
        if df.empty:
            logger.warning("No data to save")
            return
        
        output_file = folder / filename
        df.to_parquet(output_file, compression="snappy", index=True)
        file_size_mb = output_file.stat().st_size / (1024 * 1024)
        logger.info(f"  Saved {len(df)} records to {filename} ({file_size_mb:.2f} MB)")

    def save_sqlite(self, df: pd.DataFrame, db_path: Path, table_name: str = "gold_ohlcv"):
        """Save data to SQLite database."""
        logger.info("Saving data to SQLite database...")
        
        if df.empty:
            logger.warning("No data to save")
            return
        
        # Reset index to make timestamp a column
        df_reset = df.reset_index()
        
        conn = sqlite3.connect(db_path)
        
        # Drop table if exists
        conn.execute(f"DROP TABLE IF EXISTS {table_name}")
        
        # Create table and insert data
        df_reset.to_sql(table_name, conn, if_exists="replace", index=False)
        
        # Create index on timestamp for faster queries
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_timestamp ON {table_name}(timestamp)")
        conn.commit()
        
        # Check record count
        cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        
        file_size_mb = db_path.stat().st_size / (1024 * 1024)
        logger.info(f"  Saved {count} records to SQLite ({file_size_mb:.2f} MB)")
        
        conn.close()

    def create_summary_report(self):
        """Create a summary report of downloaded data."""
        logger.info("Creating summary report...")
        
        report_path = DATABASE_FOLDER / "DATA_SUMMARY.txt"
        
        with open(report_path, "w") as f:
            f.write("=" * 80 + "\n")
            f.write("GOLD PRICE DATA SUMMARY\n")
            f.write("=" * 80 + "\n\n")
            
            f.write("DATA SOURCES:\n")
            f.write(f"- Primary: {self.symbol} (Gold Futures, CME)\n")
            f.write(f"- Fallback: {self.symbol_spot} (XAU/USD Spot)\n\n")
            
            f.write("DATA COVERAGE:\n")
            f.write(f"- Daily Data: {self.start_year}-present (fully available)\n")
            f.write(f"- Hourly Data: ~12 months (available)\n")
            f.write(f"- 1-Minute Data: ~60 days most recent (available)\n\n")
            
            f.write("FOLDER STRUCTURE:\n")
            f.write(f"Database/\n")
            f.write(f"├── gold_raw/\n")
            f.write(f"│   ├── daily_ohlcv.csv (all daily data combined)\n")
            f.write(f"│   ├── gold_YYYY_ohlcv.csv (yearly split)\n")
            f.write(f"│   ├── gold_ohlcv.parquet (compressed format)\n")
            f.write(f"│   └── gold_ohlcv.db (SQLite database)\n")
            f.write(f"├── gold_processed/\n")
            f.write(f"│   ├── hourly_recent_ohlcv.csv\n")
            f.write(f"│   ├── minute_recent_ohlcv.csv\n")
            f.write(f"│   └── minute_recent_ohlcv.db\n")
            f.write(f"└── DATA_SUMMARY.txt (this file)\n\n")
            
            f.write("HOW TO USE:\n")
            f.write("1. Load daily data:\n")
            f.write("   df = pd.read_parquet('Database/gold_raw/gold_ohlcv.parquet')\n\n")
            
            f.write("2. Query SQLite:\n")
            f.write("   conn = sqlite3.connect('Database/gold_raw/gold_ohlcv.db')\n")
            f.write("   df = pd.read_sql_query('SELECT * FROM gold_ohlcv WHERE timestamp > \"2020-01-01\"', conn)\n\n")
            
            f.write("3. Load 1-minute data:\n")
            f.write("   df = pd.read_csv('Database/gold_processed/minute_recent_ohlcv.csv', index_col='timestamp')\n")
            f.write("   df.index = pd.to_datetime(df.index)\n\n")
            
            f.write("NOTES:\n")
            f.write("- All prices are in USD per ounce ($/oz)\n")
            f.write("- OHLCV = Open, High, Low, Close, Volume\n")
            f.write("- Daily data: 2000-present (~6500+ candles)\n")
            f.write("- Hourly data: ~12 months (~8500+ candles)\n")
            f.write("- 1-minute data: ~60 days (~50,000+ candles)\n")
            f.write("- All timestamps are UTC\n\n")
            
            f.write("GENERATED: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n")
        
        logger.info(f"Summary report saved to {report_path}")

    def run(self):
        """Execute full download pipeline."""
        logger.info("=" * 80)
        logger.info("GOLD PRICE DATA DOWNLOAD PIPELINE")
        logger.info("=" * 80)
        
        # Download daily historical data
        daily_df = self.download_daily_historical()
        if not daily_df.empty:
            self.save_csv_by_year(daily_df, GOLD_RAW, prefix="gold")
            self.save_parquet(daily_df, GOLD_RAW, "gold_ohlcv.parquet")
            self.save_sqlite(daily_df, GOLD_RAW / "gold_ohlcv.db", "gold_ohlcv")
            
            # Combined daily CSV
            daily_df.to_csv(GOLD_RAW / "daily_ohlcv.csv")
            logger.info(f"Saved combined daily CSV to {GOLD_RAW / 'daily_ohlcv.csv'}")
        
        # Download hourly recent data
        hourly_df = self.download_hourly_recent(months=12)
        if not hourly_df.empty:
            hourly_df.to_csv(GOLD_PROCESSED / "hourly_recent_ohlcv.csv")
            self.save_parquet(hourly_df, GOLD_PROCESSED, "hourly_recent_ohlcv.parquet")
            self.save_sqlite(hourly_df, GOLD_PROCESSED / "hourly_recent_ohlcv.db", "gold_hourly")
            logger.info(f"Saved hourly data to {GOLD_PROCESSED / 'hourly_recent_ohlcv.csv'}")
        
        # Download 1-minute recent data
        minute_df = self.download_minute_recent(days=60)
        if not minute_df.empty:
            minute_df.to_csv(GOLD_PROCESSED / "minute_recent_ohlcv.csv")
            self.save_parquet(minute_df, GOLD_PROCESSED, "minute_recent_ohlcv.parquet")
            self.save_sqlite(minute_df, GOLD_PROCESSED / "minute_recent_ohlcv.db", "gold_minute")
            logger.info(f"Saved 1-minute data to {GOLD_PROCESSED / 'minute_recent_ohlcv.csv'}")
        
        # Create summary report
        self.create_summary_report()
        
        logger.info("=" * 80)
        logger.info("DOWNLOAD COMPLETE")
        logger.info("=" * 80)
        logger.info(f"\nData saved to: {DATABASE_FOLDER}")
        logger.info(f"Check DATA_SUMMARY.txt for details")


if __name__ == "__main__":
    downloader = GoldDataDownloader()
    downloader.run()
