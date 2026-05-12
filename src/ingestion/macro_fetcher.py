"""
Macro-Correlate Data Fetcher
=============================
Fetches all macro variables that influence gold prices.
Sources: Yahoo Finance (yfinance) for market data, FRED API for economic data.
"""

import time
import pandas as pd
import numpy as np
from typing import Optional, Dict
from pathlib import Path
from loguru import logger

from src.utils.config import get_config, PROJECT_ROOT


def _retry(max_attempts=3, backoff=2.0):
    """Simple retry decorator with exponential backoff."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_err = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_err = e
                    if attempt < max_attempts:
                        wait = backoff ** attempt
                        logger.warning(f"  {func.__name__} attempt {attempt} failed: {e} — retry in {wait:.0f}s")
                        time.sleep(wait)
            raise last_err
        return wrapper
    return decorator


class MacroFetcher:
    """Fetches macro-correlate data from Yahoo Finance and FRED."""

    YAHOO_SYMBOLS = {
        "dxy": "DX-Y.NYB", "vix": "^VIX", "tlt": "TLT",
        "tip": "TIP", "silver": "SI=F", "oil": "CL=F", "cny": "CNY=X",
    }

    FRED_SERIES = {
        "DFF": "Fed Funds Rate", "DFII10": "10Y Real Yield",
        "T10Y2Y": "Yield Curve", "DTWEXBGS": "Trade-Weighted USD",
    }

    def __init__(self, config: Optional[dict] = None):
        self.config = config or get_config()
        self.data_config = self.config.get("data", {})
        self.macro_config = self.data_config.get("macro", {})
        self.fred_config = self.data_config.get("fred", {})
        self.raw_dir = PROJECT_ROOT / "data" / "raw"
        self.raw_dir.mkdir(parents=True, exist_ok=True)

        if self.macro_config:
            self.YAHOO_SYMBOLS = {
                "dxy": self.macro_config.get("dxy_symbol", "DX-Y.NYB"),
                "vix": self.macro_config.get("vix_symbol", "^VIX"),
                "tlt": self.macro_config.get("tlt_symbol", "TLT"),
                "tip": self.macro_config.get("tips_symbol", "TIP"),
                "silver": self.macro_config.get("silver_symbol", "SI=F"),
                "oil": self.macro_config.get("oil_symbol", "CL=F"),
                "cny": self.macro_config.get("cny_symbol", "CNY=X"),
            }

    def fetch_all_yahoo_macro(self, period="10y", interval="1d") -> Dict[str, pd.DataFrame]:
        """Fetch all macro-correlate data from Yahoo Finance."""
        import yfinance as yf
        logger.info(f"Fetching {len(self.YAHOO_SYMBOLS)} macro feeds from Yahoo Finance...")
        macro_data = {}
        for name, symbol in self.YAHOO_SYMBOLS.items():
            try:
                df = self._fetch_single_yahoo(symbol, period, interval)
                if df is not None and not df.empty:
                    macro_data[name] = df
                    logger.info(f"  ✅ {name} ({symbol}): {len(df)} bars")
                else:
                    logger.warning(f"  ⚠️  {name} ({symbol}): No data returned")
            except Exception as e:
                logger.error(f"  ❌ {name} ({symbol}): {e}")
        logger.info(f"Yahoo macro: {len(macro_data)}/{len(self.YAHOO_SYMBOLS)} feeds fetched")
        return macro_data

    @_retry(max_attempts=3, backoff=2.0)
    def _fetch_single_yahoo(self, symbol, period, interval) -> Optional[pd.DataFrame]:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)
        if df.empty:
            return None
        df.columns = [c.lower().replace(" ", "_") for c in df.columns]
        df.index.name = "timestamp"
        df["returns"] = df["close"].pct_change()
        df["log_returns"] = np.log(df["close"] / df["close"].shift(1))
        for drop_col in ["dividends", "stock_splits", "capital_gains"]:
            if drop_col in df.columns:
                df = df.drop(columns=[drop_col])
        return df

    def fetch_single_macro(self, name, period="10y", interval="1d") -> Optional[pd.DataFrame]:
        """Fetch a single macro feed by name (e.g., 'dxy', 'vix')."""
        symbol = self.YAHOO_SYMBOLS.get(name)
        if not symbol:
            logger.error(f"Unknown macro name: {name}")
            return None
        return self._fetch_single_yahoo(symbol, period, interval)

    def fetch_fred_data(self) -> Dict[str, pd.Series]:
        """Fetch Federal Reserve Economic Data (FRED)."""
        api_key = self.fred_config.get("api_key", "")
        series_list = self.fred_config.get("series", list(self.FRED_SERIES.keys()))
        if not api_key or api_key in ("", "${FRED_API_KEY}", "your_fred_api_key_here"):
            logger.warning("FRED API key not configured — skipping FRED data")
            return {}
        try:
            from fredapi import Fred
        except ImportError:
            logger.warning("fredapi not installed — pip install fredapi")
            return {}
        fred = Fred(api_key=api_key)
        fred_data = {}
        logger.info(f"Fetching {len(series_list)} series from FRED...")
        for series_id in series_list:
            try:
                data = fred.get_series(series_id)
                if data is not None and len(data) > 0:
                    fred_data[series_id] = data
                    logger.info(f"  ✅ {series_id}: {len(data)} observations")
            except Exception as e:
                logger.error(f"  ❌ {series_id}: {e}")
        return fred_data

    def fred_to_dataframe(self, fred_data: Dict[str, pd.Series]) -> pd.DataFrame:
        """Convert FRED series dict to aligned DataFrame, forward-filled."""
        if not fred_data:
            return pd.DataFrame()
        df = pd.DataFrame(fred_data)
        df.index.name = "timestamp"
        df = df.sort_index().ffill()
        return df

    def compute_ratios(self, gold_df, macro_data) -> pd.DataFrame:
        """Compute gold-relative ratios (Gold/Silver, Gold/Oil, Gold/DXY)."""
        ratios = pd.DataFrame(index=gold_df.index)
        for macro_name, col_name in [("silver", "gold_silver_ratio"), ("oil", "gold_oil_ratio"), ("dxy", "gold_dxy_ratio")]:
            if macro_name in macro_data and "close" in macro_data[macro_name].columns:
                aligned = macro_data[macro_name]["close"].reindex(gold_df.index, method="ffill")
                ratios[col_name] = gold_df["close"] / aligned.replace(0, np.nan)
        return ratios

    def save_macro_to_parquet(self, macro_data) -> Dict[str, Path]:
        paths = {}
        for name, df in macro_data.items():
            fp = self.raw_dir / f"macro_{name}.parquet"
            df.to_parquet(fp, engine="pyarrow")
            paths[name] = fp
        return paths

    def load_macro_from_parquet(self) -> Dict[str, pd.DataFrame]:
        macro_data = {}
        for name in self.YAHOO_SYMBOLS:
            fp = self.raw_dir / f"macro_{name}.parquet"
            if fp.exists():
                macro_data[name] = pd.read_parquet(fp, engine="pyarrow")
        return macro_data

    def save_fred_to_parquet(self, fred_df) -> Path:
        fp = self.raw_dir / "fred_data.parquet"
        fred_df.to_parquet(fp, engine="pyarrow")
        return fp

    def load_fred_from_parquet(self) -> Optional[pd.DataFrame]:
        fp = self.raw_dir / "fred_data.parquet"
        return pd.read_parquet(fp, engine="pyarrow") if fp.exists() else None
