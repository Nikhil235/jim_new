"""
Feature Engineering Pipeline
=============================
Generates 200+ features from raw gold price and macro data.
Every feature is a potential "invariant" — a pattern the models can exploit.
"""

import pandas as pd
import numpy as np
from typing import List, Optional
from loguru import logger


class FeatureEngine:
    """
    Transforms raw OHLCV data into a rich feature matrix.
    All features are computed without lookahead bias.
    """

    def __init__(self, config: Optional[dict] = None):
        if config:
            feat_config = config.get("features", {})
            self.lookback_windows = feat_config.get("lookback_windows", [5, 10, 20, 50, 100, 200])
            self.vol_windows = feat_config.get("volatility_windows", [10, 20, 50])
            self.corr_windows = feat_config.get("correlation_windows", [20, 50, 100])
        else:
            self.lookback_windows = [5, 10, 20, 50, 100, 200]
            self.vol_windows = [10, 20, 50]
            self.corr_windows = [20, 50, 100]

    def generate_all(self, df: pd.DataFrame, macro: Optional[dict] = None) -> pd.DataFrame:
        """
        Generate all features from raw data.

        Args:
            df: Gold OHLCV DataFrame with 'close', 'high', 'low', 'volume' columns.
            macro: Optional dict of macro DataFrames (dxy, vix, etc.).

        Returns:
            DataFrame with all engineered features (NaN rows dropped).
        """
        logger.info(f"Generating features from {len(df)} bars...")
        features = df.copy()

        # Price-based features
        features = self._add_return_features(features)
        features = self._add_volatility_features(features)
        features = self._add_momentum_features(features)
        features = self._add_price_level_features(features)

        # Temporal features
        features = self._add_temporal_features(features)

        # Cross-asset features (if macro data available)
        if macro:
            features = self._add_cross_asset_features(features, macro)

        # Drop rows with NaN (from lookback calculations)
        initial_len = len(features)
        features = features.dropna()
        logger.info(
            f"Features generated: {len(features.columns)} columns | "
            f"{initial_len - len(features)} rows dropped (NaN from lookbacks) | "
            f"{len(features)} rows remaining"
        )

        return features

    def _add_return_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Multi-horizon returns."""
        for w in self.lookback_windows:
            df[f"return_{w}"] = df["close"].pct_change(w)
            df[f"log_return_{w}"] = np.log(df["close"] / df["close"].shift(w))
        return df

    def _add_volatility_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Realized volatility at multiple scales."""
        if "returns" not in df.columns:
            df["returns"] = df["close"].pct_change()

        for w in self.vol_windows:
            # Realized volatility (std of returns)
            df[f"volatility_{w}"] = df["returns"].rolling(w).std()
            # Parkinson volatility (uses high-low range — more efficient estimator)
            hl_ratio = np.log(df["high"] / df["low"])
            df[f"parkinson_vol_{w}"] = hl_ratio.rolling(w).apply(
                lambda x: np.sqrt(np.sum(x**2) / (4 * len(x) * np.log(2)))
            )
            # Volatility ratio (current vs longer-term)
            if w > self.vol_windows[0]:
                df[f"vol_ratio_{self.vol_windows[0]}_{w}"] = (
                    df[f"volatility_{self.vol_windows[0]}"] / df[f"volatility_{w}"]
                )
        return df

    def _add_momentum_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Momentum and mean-reversion signals."""
        for w in self.lookback_windows:
            # Simple Moving Average distance
            sma = df["close"].rolling(w).mean()
            df[f"sma_dist_{w}"] = (df["close"] - sma) / sma

            # Exponential Moving Average distance
            ema = df["close"].ewm(span=w).mean()
            df[f"ema_dist_{w}"] = (df["close"] - ema) / ema

            # Rate of Change
            df[f"roc_{w}"] = df["close"].pct_change(w)

            # RSI (Relative Strength Index)
            if w >= 5:
                delta = df["close"].diff()
                gain = delta.where(delta > 0, 0).rolling(w).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(w).mean()
                rs = gain / loss.replace(0, np.nan)
                df[f"rsi_{w}"] = 100 - (100 / (1 + rs))

        # MACD
        ema12 = df["close"].ewm(span=12).mean()
        ema26 = df["close"].ewm(span=26).mean()
        df["macd"] = ema12 - ema26
        df["macd_signal"] = df["macd"].ewm(span=9).mean()
        df["macd_hist"] = df["macd"] - df["macd_signal"]

        return df

    def _add_price_level_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Support/resistance and range features."""
        for w in [10, 20, 50]:
            df[f"high_{w}"] = df["high"].rolling(w).max()
            df[f"low_{w}"] = df["low"].rolling(w).min()
            df[f"range_{w}"] = (df[f"high_{w}"] - df[f"low_{w}"]) / df["close"]
            df[f"position_in_range_{w}"] = (
                (df["close"] - df[f"low_{w}"]) / (df[f"high_{w}"] - df[f"low_{w}"])
            ).replace([np.inf, -np.inf], np.nan)

        # ATR (Average True Range)
        for w in [14, 20]:
            high_low = df["high"] - df["low"]
            high_close = (df["high"] - df["close"].shift(1)).abs()
            low_close = (df["low"] - df["close"].shift(1)).abs()
            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            df[f"atr_{w}"] = true_range.rolling(w).mean()
            df[f"atr_pct_{w}"] = df[f"atr_{w}"] / df["close"]

        return df

    def _add_temporal_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Time-based cyclical features (no lookahead)."""
        if hasattr(df.index, "hour"):
            # Cyclical encoding (sin/cos) — better than one-hot for models
            df["hour_sin"] = np.sin(2 * np.pi * df.index.hour / 24)
            df["hour_cos"] = np.cos(2 * np.pi * df.index.hour / 24)

        if hasattr(df.index, "dayofweek"):
            df["dow_sin"] = np.sin(2 * np.pi * df.index.dayofweek / 7)
            df["dow_cos"] = np.cos(2 * np.pi * df.index.dayofweek / 7)

        if hasattr(df.index, "month"):
            df["month_sin"] = np.sin(2 * np.pi * df.index.month / 12)
            df["month_cos"] = np.cos(2 * np.pi * df.index.month / 12)

        return df

    def _add_cross_asset_features(self, df: pd.DataFrame, macro: dict) -> pd.DataFrame:
        """Cross-asset correlation and spread features."""
        for name, macro_df in macro.items():
            if "close" not in macro_df.columns:
                continue

            # Align dates
            macro_close = macro_df["close"].reindex(df.index, method="ffill")
            macro_returns = macro_close.pct_change()

            # Rolling correlation
            if "returns" in df.columns:
                for w in self.corr_windows:
                    df[f"corr_{name}_{w}"] = (
                        df["returns"].rolling(w).corr(macro_returns)
                    )

            # Spread (normalized)
            df[f"{name}_return"] = macro_returns
            df[f"spread_vs_{name}"] = df.get("returns", df["close"].pct_change()) - macro_returns

        return df

    def get_feature_names(self, df: pd.DataFrame) -> List[str]:
        """Get list of engineered feature column names (exclude raw OHLCV)."""
        raw_cols = {"open", "high", "low", "close", "volume", "dividends", "stock_splits",
                    "returns", "log_returns", "spread", "typical_price"}
        return [c for c in df.columns if c not in raw_cols]
