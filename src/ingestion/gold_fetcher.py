"""
Gold Data Fetcher
=================
Fetches historical and live gold price data from multiple sources.
Follows the Simons principle: more data = more signal.

Phase 2 enhancements:
- Multi-symbol batch fetching (GC=F, XAUUSD=X, GLD, IAU)
- Incremental ingestion (only new data since last fetch)
- Gold/Silver & Gold/Oil ratio computation
- Retry logic for flaky API calls
"""

import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict
from loguru import logger

from src.utils.config import get_config, PROJECT_ROOT

from src.utils.resilience import retry


class GoldDataFetcher:
    """
    Fetches gold price data from Yahoo Finance (dev) and
    premium feeds (production).

    Supports multiple gold instruments:
      - GC=F     → Gold Futures (CME)
      - XAUUSD=X → XAU/USD Spot
      - GLD      → SPDR Gold Shares ETF
      - IAU      → iShares Gold Trust ETF
    """

    # All gold-related symbols we track
    GOLD_SYMBOLS = {
        "gold_futures": "GC=F",
        "gold_spot": "XAUUSD=X",
        "gld_etf": "GLD",
        "iau_etf": "IAU",
    }

    def __init__(self, config: Optional[dict] = None):
        self.config = config or get_config()
        self.data_config = self.config["data"]["gold"]
        self.raw_dir = PROJECT_ROOT / "data" / "raw"
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    @retry(max_attempts=3, backoff_multiplier=2.0)
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

        # Drop non-OHLCV metadata columns
        for drop_col in ["dividends", "stock_splits", "capital_gains"]:
            if drop_col in df.columns:
                df = df.drop(columns=[drop_col])

        # Add derived columns
        df["returns"] = df["close"].pct_change()
        df["log_returns"] = np.log(df["close"] / df["close"].shift(1))
        df["spread"] = df["high"] - df["low"]
        df["typical_price"] = (df["high"] + df["low"] + df["close"]) / 3

        # Phase 6: Automatic Outlier Correction & Gap Imputation
        df = self._clean_and_impute(df)

        logger.info(
            f"Fetched {len(df)} bars | "
            f"{df.index[0]} to {df.index[-1]} | "
            f"Symbol: {symbol}"
        )

        return df

    def _clean_and_impute(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Phase 6: Data Quality & Imputation Engine.
        Automatically repairs missing data gaps and clips extreme outliers.
        """
        if df.empty:
            return df
            
        initial_len = len(df)
        
        # 1. Impute small gaps (up to 3 consecutive periods) with forward fill
        df = df.ffill(limit=3)
        
        # 2. Interpolate larger gaps linearly (up to 7 periods)
        df = df.interpolate(method='linear', limit=7)
        
        # 3. Outlier Correction (Clip extreme price spikes > 4 rolling std deviations)
        if len(df) > 30:
            rolling_median = df["close"].rolling(window=20, min_periods=5).median()
            rolling_std = df["close"].rolling(window=20, min_periods=5).std().bfill()
            
            # Identify extreme price spikes
            price_outliers = (df["close"] > rolling_median + 4*rolling_std) | (df["close"] < rolling_median - 4*rolling_std)
            if price_outliers.any():
                logger.info(f"Corrected {price_outliers.sum()} extreme price outliers via median substitution")
                # Fix OHLC prices
                for col in ["open", "high", "low", "close"]:
                    if col in df.columns:
                        df.loc[price_outliers, col] = rolling_median[price_outliers]
                
                # Recalculate derived columns
                df["returns"] = df["close"].pct_change()
                df["log_returns"] = np.log(df["close"] / df["close"].shift(1))
                df["spread"] = df["high"] - df["low"]
                df["typical_price"] = (df["high"] + df["low"] + df["close"]) / 3
        
        # 4. Drop remaining NaNs (unrecoverable gaps at the start or > 10 periods)
        df = df.dropna()
        
        if len(df) < initial_len:
            logger.info(f"Dropped {initial_len - len(df)} unrecoverable bad data rows")
            
        return df

    def fetch_multiple_symbols(
        self,
        period: str = "10y",
        interval: str = "1d",
    ) -> Dict[str, pd.DataFrame]:
        """Fetch all gold-related symbols in batch.

        Returns:
            Dict of name → DataFrame for each gold instrument.
        """
        logger.info(f"Batch fetching {len(self.GOLD_SYMBOLS)} gold instruments...")
        results = {}

        for name, symbol in self.GOLD_SYMBOLS.items():
            try:
                df = self.fetch_historical(symbol=symbol, period=period, interval=interval)
                if not df.empty:
                    results[name] = df
                    logger.info(f"  ✅ {name} ({symbol}): {len(df)} bars")
                else:
                    logger.warning(f"  ⚠️  {name} ({symbol}): empty")
            except Exception as e:
                logger.error(f"  ❌ {name} ({symbol}): {e}")

        logger.info(f"Gold batch: {len(results)}/{len(self.GOLD_SYMBOLS)} instruments fetched")
        return results

    @retry(max_attempts=3, backoff_multiplier=2.0)
    def fetch_historical_bulk(self, symbols: List[str], years: int = 10, interval: str = "1d") -> Dict[str, pd.DataFrame]:
        """Fetch multi-year data for multiple symbols efficiently in 1-year chunks."""
        import yfinance as yf
        results = {}
        current_year = datetime.now().year
        
        for symbol in symbols:
            logger.info(f"Bulk fetching {symbol} for {years} years...")
            chunks = []
            for year in range(current_year - years, current_year + 1):
                start = f"{year}-01-01"
                end = f"{year}-12-31"
                try:
                    ticker = yf.Ticker(symbol)
                    df = ticker.history(start=start, end=end, interval=interval)
                    if not df.empty:
                        chunks.append(df)
                        logger.info(f"  {symbol}: Fetched {year} ({len(df)} bars)")
                except Exception as e:
                    logger.warning(f"  {symbol}: Failed to fetch {year}: {e}")
                time.sleep(1) # Rate limiting
                
            if chunks:
                full_df = pd.concat(chunks)
                # Standardize columns
                full_df.columns = [c.lower().replace(" ", "_") for c in full_df.columns]
                full_df.index.name = "timestamp"
                for drop_col in ["dividends", "stock_splits", "capital_gains"]:
                    if drop_col in full_df.columns:
                        full_df = full_df.drop(columns=[drop_col])
                
                full_df["returns"] = full_df["close"].pct_change()
                results[symbol] = full_df
                logger.info(f"Completed {symbol}: {len(full_df)} total bars")
            else:
                logger.error(f"Failed to fetch any data for {symbol}")
                
        return results

    def fetch_incremental(
        self,
        symbol: Optional[str] = None,
        last_timestamp: Optional[datetime] = None,
        interval: str = "1d",
    ) -> pd.DataFrame:
        """Fetch only new data since last_timestamp.

        Args:
            symbol: Ticker symbol.
            last_timestamp: Fetch data after this timestamp.
            interval: Bar interval.

        Returns:
            DataFrame with only new bars.
        """
        symbol = symbol or self.data_config["symbol"]

        if last_timestamp is None:
            # Check parquet for last saved timestamp
            parquet_file = self.raw_dir / f"gold_{symbol.replace('=', '_')}.parquet"
            if parquet_file.exists():
                existing = pd.read_parquet(parquet_file)
                if not existing.empty:
                    last_timestamp = existing.index[-1]
                    if hasattr(last_timestamp, 'to_pydatetime'):
                        last_timestamp = last_timestamp.to_pydatetime()

        if last_timestamp is not None:
            start = (last_timestamp - timedelta(days=1)).strftime("%Y-%m-%d")
            end = datetime.now().strftime("%Y-%m-%d")
            logger.info(f"Incremental fetch for {symbol}: {start} → {end}")
            df = self.fetch_historical(symbol=symbol, start=start, end=end, interval=interval)
        else:
            logger.info(f"No prior data found — doing full fetch for {symbol}")
            df = self.fetch_historical(symbol=symbol, period="10y", interval=interval)

        return df

    def fetch_macro_data(self) -> dict:
        """
        Fetch macro-correlate data (DXY, VIX, TLT, TIP).
        Delegates to MacroFetcher for enhanced version.

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
        Delegates to MacroFetcher for enhanced version.

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

    def get_data_summary(self) -> Dict[str, dict]:
        """Get summary of all locally cached gold data."""
        summary = {}
        for f in self.raw_dir.glob("gold_*.parquet"):
            try:
                df = pd.read_parquet(f)
                summary[f.stem] = {
                    "rows": len(df),
                    "columns": list(df.columns),
                    "start": str(df.index[0]) if len(df) > 0 else None,
                    "end": str(df.index[-1]) if len(df) > 0 else None,
                    "size_mb": round(f.stat().st_size / 1_048_576, 2),
                }
            except Exception:
                summary[f.stem] = {"error": "unreadable"}
        return summary
