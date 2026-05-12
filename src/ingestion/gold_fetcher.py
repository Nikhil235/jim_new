"""
Gold Data Fetcher
=================
Fetches historical and live gold price data from multiple sources.
Follows the Simons principle: more data = more signal.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List
from loguru import logger

from src.utils.config import get_config, PROJECT_ROOT


class GoldDataFetcher:
    """
    Fetches gold price data from Yahoo Finance (dev) and 
    premium feeds (production).
    """

    def __init__(self, config: Optional[dict] = None):
        self.config = config or get_config()
        self.data_config = self.config["data"]["gold"]
        self.raw_dir = PROJECT_ROOT / "data" / "raw"
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    def fetch_historical(
        self,
        symbol: Optional[str] = None,
        period: str = "max",
        interval: str = "1d",
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Fetch historical gold data.

        Args:
            symbol: Ticker symbol. Defaults to config.
            period: Data period (e.g., "max", "10y", "1y").
            interval: Bar interval (e.g., "1d", "1h", "1m").
            start: Start date (YYYY-MM-DD).
            end: End date (YYYY-MM-DD).

        Returns:
            DataFrame with OHLCV data.
        """
        import yfinance as yf

        symbol = symbol or self.data_config["symbol"]
        logger.info(f"Fetching historical data: {symbol} | interval={interval}")

        ticker = yf.Ticker(symbol)

        if start and end:
            df = ticker.history(start=start, end=end, interval=interval)
        else:
            df = ticker.history(period=period, interval=interval)

        if df.empty:
            logger.error(f"No data returned for {symbol}")
            return df

        # Standardize column names
        df.columns = [c.lower().replace(" ", "_") for c in df.columns]
        df.index.name = "timestamp"

        # Add derived columns
        df["returns"] = df["close"].pct_change()
        df["log_returns"] = np.log(df["close"] / df["close"].shift(1))
        df["spread"] = df["high"] - df["low"]
        df["typical_price"] = (df["high"] + df["low"] + df["close"]) / 3

        logger.info(
            f"Fetched {len(df)} bars | "
            f"{df.index[0]} to {df.index[-1]} | "
            f"Symbol: {symbol}"
        )

        return df

    def fetch_macro_data(self) -> dict:
        """
        Fetch macro-correlate data (DXY, VIX, TLT, TIP).

        Returns:
            Dict of DataFrames keyed by symbol name.
        """
        import yfinance as yf

        macro_config = self.config["data"]["macro"]
        macro_data = {}

        symbols = {
            "dxy": macro_config["dxy_symbol"],
            "vix": macro_config["vix_symbol"],
            "tlt": macro_config["tlt_symbol"],
            "tips": macro_config["tips_symbol"],
        }

        for name, symbol in symbols.items():
            logger.info(f"Fetching macro data: {name} ({symbol})")
            try:
                ticker = yf.Ticker(symbol)
                df = ticker.history(period="10y", interval="1d")
                df.columns = [c.lower().replace(" ", "_") for c in df.columns]
                df.index.name = "timestamp"
                df["returns"] = df["close"].pct_change()
                macro_data[name] = df
                logger.info(f"  {name}: {len(df)} bars fetched")
            except Exception as e:
                logger.error(f"  Failed to fetch {name}: {e}")

        return macro_data

    def fetch_fred_data(self) -> dict:
        """
        Fetch Federal Reserve Economic Data (FRED) series.

        Returns:
            Dict of Series keyed by series ID.
        """
        fred_config = self.config["data"]["fred"]
        api_key = fred_config.get("api_key", "")

        if not api_key or api_key == "your_fred_api_key_here":
            logger.warning("FRED API key not set — skipping FRED data")
            return {}

        from fredapi import Fred
        fred = Fred(api_key=api_key)
        fred_data = {}

        for series_id in fred_config["series"]:
            try:
                data = fred.get_series(series_id)
                fred_data[series_id] = data
                logger.info(f"FRED {series_id}: {len(data)} observations")
            except Exception as e:
                logger.error(f"Failed to fetch FRED {series_id}: {e}")

        return fred_data

    def save_to_parquet(self, df: pd.DataFrame, filename: str) -> Path:
        """Save DataFrame to parquet in the raw data directory."""
        filepath = self.raw_dir / f"{filename}.parquet"
        df.to_parquet(filepath, engine="pyarrow")
        logger.info(f"Saved {len(df)} rows to {filepath}")
        return filepath

    def load_from_parquet(self, filename: str) -> pd.DataFrame:
        """Load DataFrame from parquet."""
        filepath = self.raw_dir / f"{filename}.parquet"
        if not filepath.exists():
            raise FileNotFoundError(f"Data file not found: {filepath}")
        df = pd.read_parquet(filepath, engine="pyarrow")
        logger.info(f"Loaded {len(df)} rows from {filepath}")
        return df
