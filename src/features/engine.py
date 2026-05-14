"""
Feature Engineering Pipeline
=============================
Generates 200+ features from raw gold price and macro data.
Every feature is a potential "invariant" — a pattern the models can exploit.

Phase 2 expansion:
- Microstructure proxies (order flow, Kyle's Lambda, Amihud)
- Event proximity flags (FOMC, NFP, London Fix)
- Distribution features (skew, kurtosis, Hurst exponent)
- Cross-asset enhanced (Gold/Silver, Gold/Oil, macro z-scores)
- Regime features (ADX proxy, trend strength, mean-reversion score)
- Lag features (autocorrelation, lagged returns/vol)
"""

from src.utils.gpu import get_dataframe_engine
pd = get_dataframe_engine()
import numpy as np
from typing import List, Optional
from loguru import logger


class FeatureEngine:
    """Transforms raw OHLCV data into a rich feature matrix.
    All features are computed without lookahead bias."""

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

    def generate_all(
        self,
        df: pd.DataFrame,
        macro: Optional[dict] = None,
        alt_data: Optional[dict] = None,
    ) -> pd.DataFrame:
        """Generate all features from raw data.

        Args:
            df: Gold OHLCV DataFrame with 'close', 'high', 'low', 'volume' columns.
            macro: Optional dict of macro DataFrames (dxy, vix, etc.).
            alt_data: Optional dict of alternative data DataFrames
                      (cot_gold, sentiment_daily, etf_gld, etf_iau, google_trends, etc.).

        Returns:
            DataFrame with all engineered features (NaN rows dropped).
        """
        logger.info(f"Generating features from {len(df)} bars...")
        features = df.copy()

        # Ensure returns column exists
        if "returns" not in features.columns:
            features["returns"] = features["close"].pct_change()

        # --- Core feature groups ---
        features = self._add_return_features(features)
        features = self._add_volatility_features(features)
        features = self._add_momentum_features(features)
        features = self._add_price_level_features(features)

        # Volume-based features
        if "volume" in features.columns:
            features = self._add_volume_features(features)

        # --- Phase 2 new feature groups ---
        features = self._add_temporal_features(features)
        features = self._add_lag_features(features)
        features = self._add_distribution_features(features)
        features = self._add_microstructure_proxies(features)
        features = self._add_regime_features(features)
        features = self._add_event_proximity_features(features)

        # Cross-asset features (if macro data available)
        if macro:
            features = self._add_cross_asset_features(features, macro)
            features = self._add_cross_asset_enhanced(features, macro)

        # Alternative data features
        if alt_data:
            features = self._add_etf_flow_features(features, alt_data)
            features = self._add_cot_features(features, alt_data)
            features = self._add_google_trends_features(features, alt_data)

        # Smart NaN handling: don't let alt data (shorter history) eliminate all rows
        # 1. Forward-fill alt data columns (COT, ETF, trends) — they are weekly/sparse
        alt_prefixes = ("cot_", "etf_", "trends_", "google_")
        alt_cols = [c for c in features.columns if any(c.startswith(p) for p in alt_prefixes)]
        core_cols = [c for c in features.columns if c not in alt_cols]

        # 2. Drop rows only where core features have NaN (from lookback windows)
        initial_len = len(features)
        if core_cols:
            features = features.dropna(subset=core_cols)

        # 3. Forward-fill remaining NaN in alt data columns
        if alt_cols:
            features[alt_cols] = features[alt_cols].ffill()

        feat_names = self.get_feature_names(features)
        logger.info(
            f"Features generated: {len(feat_names)} features | "
            f"{initial_len - len(features)} rows dropped (NaN in core) | "
            f"{len(features)} rows remaining"
        )
        return features

    # ──────────────────────────────────────────────────────
    # Core features (from Phase 1)
    # ──────────────────────────────────────────────────────

    def _add_return_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Multi-horizon returns."""
        for w in self.lookback_windows:
            df[f"return_{w}"] = df["close"].pct_change(w)
            df[f"log_return_{w}"] = np.log(df["close"] / df["close"].shift(w))
        return df

    def _add_volatility_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Realized volatility at multiple scales."""
        for w in self.vol_windows:
            df[f"volatility_{w}"] = df["returns"].rolling(w).std()
            hl_ratio = np.log(df["high"] / df["low"])
            df[f"parkinson_vol_{w}"] = hl_ratio.rolling(w).apply(
                lambda x: np.sqrt(np.sum(x**2) / (4 * len(x) * np.log(2))), raw=True
            )
            if w > self.vol_windows[0]:
                df[f"vol_ratio_{self.vol_windows[0]}_{w}"] = (
                    df[f"volatility_{self.vol_windows[0]}"] / df[f"volatility_{w}"]
                )
        return df

    def _add_momentum_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Momentum and mean-reversion signals."""
        for w in self.lookback_windows:
            sma = df["close"].rolling(w).mean()
            df[f"sma_dist_{w}"] = (df["close"] - sma) / sma
            ema = df["close"].ewm(span=w).mean()
            df[f"ema_dist_{w}"] = (df["close"] - ema) / ema
            df[f"roc_{w}"] = df["close"].pct_change(w)
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

        for w in [14, 20]:
            high_low = df["high"] - df["low"]
            high_close = (df["high"] - df["close"].shift(1)).abs()
            low_close = (df["low"] - df["close"].shift(1)).abs()
            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            df[f"atr_{w}"] = true_range.rolling(w).mean()
            df[f"atr_pct_{w}"] = df[f"atr_{w}"] / df["close"]
        return df

    def _add_volume_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Volume-based features: OBV, VWAP, volume ratios, divergence."""
        obv_dir = np.where(df["close"] > df["close"].shift(1), 1,
                           np.where(df["close"] < df["close"].shift(1), -1, 0))
        df["obv"] = (df["volume"] * obv_dir).cumsum()
        df["obv_change"] = df["obv"].pct_change(5)

        for w in [10, 20, 50]:
            vol_ma = df["volume"].rolling(w).mean()
            df[f"volume_ratio_{w}"] = df["volume"] / vol_ma.replace(0, np.nan)

        tp = (df["high"] + df["low"] + df["close"]) / 3
        for w in [10, 20]:
            tp_vol = tp * df["volume"]
            vwap = tp_vol.rolling(w).sum() / df["volume"].rolling(w).sum().replace(0, np.nan)
            df[f"vwap_{w}"] = vwap
            df[f"vwap_dist_{w}"] = (df["close"] - vwap) / vwap

        for w in [10, 20]:
            price_slope = df["close"].rolling(w).apply(
                lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) > 1 else 0, raw=False
            )
            vol_slope = df["volume"].rolling(w).apply(
                lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) > 1 else 0, raw=False
            )
            df[f"vol_price_divergence_{w}"] = np.sign(price_slope) * np.sign(vol_slope) * -1

        df["returns_squared"] = df["returns"] ** 2
        for w in [10, 20, 50]:
            df[f"returns_squared_ma_{w}"] = df["returns_squared"].rolling(w).mean()

        for w in [20, 50]:
            df[f"return_skew_{w}"] = df["returns"].rolling(w).skew()
            df[f"return_kurt_{w}"] = df["returns"].rolling(w).kurt()
        return df

    # ──────────────────────────────────────────────────────
    # Phase 2: New feature groups
    # ──────────────────────────────────────────────────────

    def _add_temporal_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Time-based cyclical features (no lookahead)."""
        if hasattr(df.index, "hour"):
            df["hour_sin"] = np.sin(2 * np.pi * df.index.hour / 24)
            df["hour_cos"] = np.cos(2 * np.pi * df.index.hour / 24)
        if hasattr(df.index, "dayofweek"):
            df["dow_sin"] = np.sin(2 * np.pi * df.index.dayofweek / 7)
            df["dow_cos"] = np.cos(2 * np.pi * df.index.dayofweek / 7)
        if hasattr(df.index, "month"):
            df["month_sin"] = np.sin(2 * np.pi * df.index.month / 12)
            df["month_cos"] = np.cos(2 * np.pi * df.index.month / 12)
        if hasattr(df.index, "day"):
            df["dom_sin"] = np.sin(2 * np.pi * df.index.day / 31)
            df["dom_cos"] = np.cos(2 * np.pi * df.index.day / 31)
        if hasattr(df.index, "dayofyear"):
            df["doy_sin"] = np.sin(2 * np.pi * df.index.dayofyear / 365)
            df["doy_cos"] = np.cos(2 * np.pi * df.index.dayofyear / 365)
        return df

    def _add_lag_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Lagged returns and autocorrelation features."""
        # Lagged returns
        for lag in [1, 2, 3, 5, 10, 21]:
            df[f"return_lag_{lag}"] = df["returns"].shift(lag)

        # Lagged volatility
        if "volatility_20" in df.columns:
            for lag in [1, 5, 10]:
                df[f"vol20_lag_{lag}"] = df["volatility_20"].shift(lag)

        # Autocorrelation at various lags
        for w in [20, 50]:
            for lag in [1, 5, 10]:
                df[f"autocorr_{w}_lag{lag}"] = df["returns"].rolling(w).apply(
                    lambda x: pd.Series(x).autocorr(lag=min(lag, len(x) - 1)), raw=False
                )
        return df

    def _add_distribution_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Return distribution shape features."""
        for w in [10, 20, 50, 100]:
            df[f"skew_{w}"] = df["returns"].rolling(w).skew()
            df[f"kurtosis_{w}"] = df["returns"].rolling(w).kurt()
            # Min/max return in window
            df[f"max_return_{w}"] = df["returns"].rolling(w).max()
            df[f"min_return_{w}"] = df["returns"].rolling(w).min()
            # Return range
            df[f"return_range_{w}"] = df[f"max_return_{w}"] - df[f"min_return_{w}"]
            # Percentage of positive returns
            df[f"pct_positive_{w}"] = df["returns"].rolling(w).apply(
                lambda x: (x > 0).sum() / len(x), raw=True
            )

        # Hurst exponent proxy (simplified R/S analysis)
        for w in [50, 100]:
            df[f"hurst_proxy_{w}"] = df["returns"].rolling(w).apply(
                self._hurst_rs, raw=True
            )
        return df

    @staticmethod
    def _hurst_rs(x):
        """Simplified Hurst exponent via rescaled range."""
        n = len(x)
        if n < 20:
            return 0.5
        mean = np.mean(x)
        y = np.cumsum(x - mean)
        r = np.max(y) - np.min(y)
        s = np.std(x, ddof=1)
        if s == 0:
            return 0.5
        rs = r / s
        if rs <= 0:
            return 0.5
        return np.log(rs) / np.log(n)

    def _add_microstructure_proxies(self, df: pd.DataFrame) -> pd.DataFrame:
        """Microstructure feature proxies from OHLCV data.
        
        Real microstructure needs L2/L3 data; these are OHLCV proxies.
        """
        # Spread proxy: high-low range normalized by close
        df["spread_proxy"] = (df["high"] - df["low"]) / df["close"]
        for w in [5, 10, 20]:
            df[f"spread_proxy_ma_{w}"] = df["spread_proxy"].rolling(w).mean()
            df[f"spread_proxy_ratio_{w}"] = df["spread_proxy"] / df[f"spread_proxy_ma_{w}"].replace(0, np.nan)

        # Amihud illiquidity measure proxy: |return| / volume
        if "volume" in df.columns:
            df["amihud"] = df["returns"].abs() / (df["volume"].replace(0, np.nan) / 1e6)
            for w in [10, 20]:
                df[f"amihud_ma_{w}"] = df["amihud"].rolling(w).mean()

            # Kyle's Lambda proxy: price impact = |close-open| / volume
            df["kyle_lambda"] = (df["close"] - df["open"]).abs() / (df["volume"].replace(0, np.nan) / 1e6)
            for w in [10, 20]:
                df[f"kyle_lambda_ma_{w}"] = df["kyle_lambda"].rolling(w).mean()

            # Trade intensity proxy: volume / range
            hl_range = (df["high"] - df["low"]).replace(0, np.nan)
            df["trade_intensity"] = df["volume"] / hl_range
            for w in [10, 20]:
                df[f"trade_intensity_ma_{w}"] = df["trade_intensity"].rolling(w).mean()

        # Close location value: where close is in the day's range
        hl = (df["high"] - df["low"]).replace(0, np.nan)
        df["close_location"] = (df["close"] - df["low"]) / hl
        return df

    def _add_regime_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Regime-detection proxy features."""
        # ADX proxy (trend strength)
        for w in [14, 20]:
            plus_dm = df["high"].diff()
            minus_dm = -df["low"].diff()
            plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
            minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)

            atr = df.get(f"atr_{w}")
            if atr is None:
                tr = pd.concat([
                    df["high"] - df["low"],
                    (df["high"] - df["close"].shift(1)).abs(),
                    (df["low"] - df["close"].shift(1)).abs()
                ], axis=1).max(axis=1)
                atr = tr.rolling(w).mean()

            plus_di = 100 * (plus_dm.rolling(w).mean() / atr.replace(0, np.nan))
            minus_di = 100 * (minus_dm.rolling(w).mean() / atr.replace(0, np.nan))
            dx = (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan) * 100
            df[f"adx_{w}"] = dx.rolling(w).mean()
            df[f"plus_di_{w}"] = plus_di
            df[f"minus_di_{w}"] = minus_di

        # Mean reversion score: z-score of price vs SMA
        for w in [20, 50, 100]:
            sma = df["close"].rolling(w).mean()
            std = df["close"].rolling(w).std()
            df[f"zscore_{w}"] = (df["close"] - sma) / std.replace(0, np.nan)

        # Trend consistency: fraction of last N bars in same direction
        for w in [5, 10, 20]:
            df[f"trend_consistency_{w}"] = df["returns"].rolling(w).apply(
                lambda x: (x > 0).sum() / len(x) if len(x) > 0 else 0.5, raw=True
            )

        # Volatility regime: current vol vs long-term
        if "volatility_20" in df.columns and "volatility_50" in df.columns:
            df["vol_regime"] = df["volatility_20"] / df["volatility_50"].replace(0, np.nan)
        return df

    def _add_event_proximity_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Event proximity flags and timing features.
        
        Uses day-of-month heuristics for FOMC/NFP since
        actual calendars would require external data.
        """
        if not hasattr(df.index, "day"):
            return df

        # FOMC meeting proximity (typically Tue-Wed around mid-month, 8 times/year)
        # Approximate: flag days 13-15 of months 1,3,5,6,7,9,11,12
        fomc_months = {1, 3, 5, 6, 7, 9, 11, 12}
        is_fomc_week = pd.Series(
            [(idx.month in fomc_months and 12 <= idx.day <= 16) for idx in df.index],
            index=df.index, dtype=float
        )
        df["fomc_proximity"] = is_fomc_week

        # NFP proximity (first Friday of month)
        is_nfp_week = pd.Series(
            [(idx.day <= 7 and idx.weekday() <= 4) for idx in df.index],
            index=df.index, dtype=float
        )
        df["nfp_proximity"] = is_nfp_week

        # Month-end effect (last 3 trading days)
        df["month_end"] = pd.Series(
            [1.0 if idx.day >= 27 else 0.0 for idx in df.index],
            index=df.index
        )

        # Quarter-end effect
        df["quarter_end"] = pd.Series(
            [1.0 if (idx.month in {3, 6, 9, 12} and idx.day >= 25) else 0.0
             for idx in df.index],
            index=df.index
        )

        # Year-end effect
        df["year_end"] = pd.Series(
            [1.0 if (idx.month == 12 and idx.day >= 20) else 0.0
             for idx in df.index],
            index=df.index
        )
        return df

    def _add_cross_asset_features(self, df: pd.DataFrame, macro: dict) -> pd.DataFrame:
        """Cross-asset correlation and spread features."""
        for name, macro_df in macro.items():
            if "close" not in macro_df.columns:
                continue
            macro_close = macro_df["close"].reindex(df.index, method="ffill")
            macro_returns = macro_close.pct_change()

            if "returns" in df.columns:
                for w in self.corr_windows:
                    df[f"corr_{name}_{w}"] = df["returns"].rolling(w).corr(macro_returns)

            df[f"{name}_return"] = macro_returns
            df[f"spread_vs_{name}"] = df.get("returns", df["close"].pct_change()) - macro_returns
        return df

    def _add_cross_asset_enhanced(self, df: pd.DataFrame, macro: dict) -> pd.DataFrame:
        """Enhanced cross-asset features: ratios, betas, z-scores."""
        for name, macro_df in macro.items():
            if "close" not in macro_df.columns:
                continue
            macro_close = macro_df["close"].reindex(df.index, method="ffill")

            # Price ratio
            df[f"ratio_{name}"] = df["close"] / macro_close.replace(0, np.nan)

            # Rolling beta (gold vs macro)
            macro_ret = macro_close.pct_change()
            for w in [20, 50]:
                cov = df["returns"].rolling(w).cov(macro_ret)
                var = macro_ret.rolling(w).var()
                df[f"beta_{name}_{w}"] = cov / var.replace(0, np.nan)

            # Macro z-score (how extreme is current macro level)
            for w in [50, 100]:
                ma = macro_close.rolling(w).mean()
                std = macro_close.rolling(w).std()
                df[f"{name}_zscore_{w}"] = (macro_close - ma) / std.replace(0, np.nan)
        return df

    # ──────────────────────────────────────────────────────
    # Phase 2: Alternative Data Features
    # ──────────────────────────────────────────────────────

    @staticmethod
    def _tz_naive_series(series: pd.Series, target_index: pd.Index) -> pd.Series:
        """Reindex a series to target_index, handling timezone mismatches.

        Strips timezone info from the series index before reindexing,
        since gold data (from yfinance) can be tz-naive while
        ETF/macro data may be tz-aware (America/New_York).
        """
        if series.index.tz is not None:
            series = series.copy()
            series.index = series.index.tz_localize(None)
        # Also strip target if needed
        if target_index.tz is not None:
            target_index = target_index.tz_localize(None)
        return series.reindex(target_index, method="ffill")

    def _add_etf_flow_features(self, df: pd.DataFrame, alt_data: dict) -> pd.DataFrame:
        """ETF flow features from GLD/IAU volume data.

        Generates:
          - Dollar volume and rolling changes
          - Flow proxy (volume_ratio × price_direction)
          - Cross-ETF divergence (GLD vs IAU)
          - Volume surprise (current vs 20-day MA)
        """
        etf_keys = [k for k in alt_data.keys() if k.startswith("etf_")]
        if not etf_keys:
            return df

        for key in etf_keys:
            etf_df = alt_data[key]
            etf_name = key.replace("etf_", "").lower()

            if "close" not in etf_df.columns or "volume" not in etf_df.columns:
                continue

            # Align ETF data to gold index (handle timezone mismatch)
            etf_close = self._tz_naive_series(etf_df["close"], df.index)
            etf_volume = self._tz_naive_series(etf_df["volume"], df.index)

            # Dollar volume
            dollar_vol = etf_close * etf_volume
            df[f"etf_{etf_name}_dollar_vol"] = dollar_vol

            # Dollar volume rolling change (5-day and 20-day)
            for w in [5, 20]:
                dv_ma = dollar_vol.rolling(w).mean()
                df[f"etf_{etf_name}_dollar_vol_change_{w}"] = dollar_vol / dv_ma.replace(0, np.nan) - 1

            # Volume surprise: how unusual is today's volume
            vol_ma20 = etf_volume.rolling(20).mean()
            vol_std20 = etf_volume.rolling(20).std()
            df[f"etf_{etf_name}_vol_zscore"] = (
                (etf_volume - vol_ma20) / vol_std20.replace(0, np.nan)
            )

            # Flow proxy: volume_ratio × price_direction
            if "flow_proxy" in etf_df.columns:
                flow = self._tz_naive_series(etf_df["flow_proxy"], df.index)
                df[f"etf_{etf_name}_flow_proxy"] = flow
                # Rolling flow momentum
                for w in [5, 10, 20]:
                    df[f"etf_{etf_name}_flow_ma_{w}"] = flow.rolling(w).mean()

            # ETF return (for correlation with gold)
            etf_ret = etf_close.pct_change()
            df[f"etf_{etf_name}_return"] = etf_ret

        # Cross-ETF divergence: GLD vs IAU volume ratio
        if "etf_GLD" in alt_data and "etf_IAU" in alt_data:
            gld_vol = self._tz_naive_series(alt_data["etf_GLD"]["volume"], df.index)
            iau_vol = self._tz_naive_series(alt_data["etf_IAU"]["volume"], df.index)
            df["etf_gld_iau_vol_ratio"] = gld_vol / iau_vol.replace(0, np.nan)

            gld_ret = self._tz_naive_series(alt_data["etf_GLD"]["close"], df.index).pct_change()
            iau_ret = self._tz_naive_series(alt_data["etf_IAU"]["close"], df.index).pct_change()
            df["etf_gld_iau_return_spread"] = gld_ret - iau_ret

        return df

    def _add_cot_features(self, df: pd.DataFrame, alt_data: dict) -> pd.DataFrame:
        """COT positioning features from CFTC data.

        Generates:
          - Net commercial/non-commercial position levels
          - Week-over-week position changes
          - Commercial hedger ratio
          - Speculator crowding indicator
          - Open interest momentum
        """
        cot_key = None
        for k in alt_data.keys():
            if "cot" in k.lower():
                cot_key = k
                break

        if cot_key is None:
            return df

        cot_df = alt_data[cot_key]

        # Align weekly COT to daily gold index (forward-fill, handle tz)
        for col in ["net_commercial", "net_noncommercial", "open_interest",
                    "commercial_long", "commercial_short",
                    "noncommercial_long", "noncommercial_short"]:
            if col in cot_df.columns:
                aligned = self._tz_naive_series(cot_df[col], df.index)
                df[f"cot_{col}"] = aligned

        # Net position changes (week-over-week, resampled to daily fill)
        if "net_noncommercial" in cot_df.columns:
            nc_net = self._tz_naive_series(cot_df["net_noncommercial"], df.index)
            df["cot_nc_net_change"] = nc_net.diff()
            # Speculator sentiment: z-score of net non-commercial
            for w in [26, 52]:  # 6-month and 1-year windows (in weekly terms)
                daily_w = w * 5  # Convert to daily
                ma = nc_net.rolling(daily_w).mean()
                std = nc_net.rolling(daily_w).std()
                df[f"cot_nc_zscore_{w}w"] = (nc_net - ma) / std.replace(0, np.nan)

        if "net_commercial" in cot_df.columns:
            c_net = self._tz_naive_series(cot_df["net_commercial"], df.index)
            df["cot_c_net_change"] = c_net.diff()

        # Commercial hedger ratio: commercial_long / (commercial_long + commercial_short)
        if "commercial_long" in cot_df.columns and "commercial_short" in cot_df.columns:
            c_long = self._tz_naive_series(cot_df["commercial_long"], df.index)
            c_short = self._tz_naive_series(cot_df["commercial_short"], df.index)
            total = (c_long + c_short).replace(0, np.nan)
            df["cot_commercial_ratio"] = c_long / total

        # Open interest momentum
        if "open_interest" in cot_df.columns:
            oi = self._tz_naive_series(cot_df["open_interest"], df.index)
            df["cot_oi_change"] = oi.pct_change(5)  # 1-week change
            df["cot_oi_change_20"] = oi.pct_change(20)  # ~1-month change

        # Speculator crowding: |net_noncommercial| / open_interest
        if "net_noncommercial" in cot_df.columns and "open_interest" in cot_df.columns:
            nc_net = self._tz_naive_series(cot_df["net_noncommercial"], df.index).abs()
            oi = self._tz_naive_series(cot_df["open_interest"], df.index).replace(0, np.nan)
            df["cot_crowding"] = nc_net / oi

        return df

    def _add_google_trends_features(self, df: pd.DataFrame, alt_data: dict) -> pd.DataFrame:
        """Google Trends interest features.

        Generates:
          - Interest level for each keyword (aligned to daily)
          - Interest momentum (week-over-week change)
          - Combined gold interest index
        """
        trends_key = None
        for k in alt_data.keys():
            if "trends" in k.lower() or "google" in k.lower():
                trends_key = k
                break

        if trends_key is None:
            return df

        trends_df = alt_data[trends_key]

        for col in trends_df.columns:
            if trends_df[col].dtype in [np.float64, np.float32, np.int64, np.int32]:
                # Align weekly trends to daily (handle tz)
                aligned = self._tz_naive_series(trends_df[col], df.index)
                safe_col = col.replace(" ", "_").replace("/", "_").lower()
                df[f"trends_{safe_col}"] = aligned

                # Interest momentum
                df[f"trends_{safe_col}_change"] = aligned.pct_change(7)  # Week-over-week

        # Combined gold interest index (mean of all keyword columns)
        trends_cols = [c for c in df.columns if c.startswith("trends_") and not c.endswith("_change")]
        if trends_cols:
            df["trends_gold_index"] = df[trends_cols].mean(axis=1)
            df["trends_gold_index_zscore"] = (
                (df["trends_gold_index"] - df["trends_gold_index"].rolling(52).mean())
                / df["trends_gold_index"].rolling(52).std().replace(0, np.nan)
            )

        return df

    # ──────────────────────────────────────────────────────
    # Utility
    # ──────────────────────────────────────────────────────

    def get_feature_names(self, df: pd.DataFrame) -> List[str]:
        """Get list of engineered feature column names (exclude raw OHLCV)."""
        raw_cols = {"open", "high", "low", "close", "volume", "dividends", "stock_splits",
                    "returns", "log_returns", "spread", "typical_price"}
        return [c for c in df.columns if c not in raw_cols]

    def get_feature_count(self, df: pd.DataFrame) -> int:
        """Get count of engineered features."""
        return len(self.get_feature_names(df))
