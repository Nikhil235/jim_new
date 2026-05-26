"""
adx_regime_detector.py
======================
Drop-in ADX-based market regime detector for Gold/Silver trading.

Usage:
    from adx_regime_detector import RegimeDetector, trend_filter

    detector = RegimeDetector(df)
    regime   = detector.detect()          # "TRENDING" | "RANGING" | "NEUTRAL"
    size_mul = detector.position_multiplier()  # 0.0 – 1.0

    ok = trend_filter(df, ai_confidence=0.62)  # True / False
"""

import pandas as pd
import numpy as np


# ─────────────────────────────────────────────
#  Core indicator helpers
# ─────────────────────────────────────────────

def compute_ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range — measures raw volatility."""
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)

    tr = pd.concat(
        [high - low,
         (high - prev_close).abs(),
         (low  - prev_close).abs()],
        axis=1
    ).max(axis=1)

    return tr.ewm(span=period, adjust=False).mean()


def compute_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Average Directional Index (Wilder smoothing).
    Returns a Series aligned with df.index.
    Values:
        ADX > 25  → strong trend
        ADX 20-25 → weak / developing trend
        ADX < 20  → ranging / choppy
    """
    high  = df["high"]
    low   = df["low"]
    close = df["close"]

    # Directional movement
    up_move   = high.diff()
    down_move = -low.diff()

    plus_dm  = np.where((up_move > down_move) & (up_move > 0), up_move,   0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    plus_dm  = pd.Series(plus_dm,  index=df.index)
    minus_dm = pd.Series(minus_dm, index=df.index)

    atr = compute_atr(df, period)

    # Smooth with Wilder EMA (equivalent to RMA)
    alpha = 1 / period
    plus_di  = 100 * plus_dm.ewm(alpha=alpha,  adjust=False).mean() / atr
    minus_di = 100 * minus_dm.ewm(alpha=alpha, adjust=False).mean() / atr

    dx = (100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)).fillna(0)
    adx = dx.ewm(alpha=alpha, adjust=False).mean()

    return adx


# ─────────────────────────────────────────────
#  Regime Detector class
# ─────────────────────────────────────────────

class RegimeDetector:
    """
    Detects whether the market is in a TRENDING, NEUTRAL, or RANGING regime
    using ADX and ATR normalised volatility.

    Parameters
    ----------
    df            : DataFrame with columns [open, high, low, close, volume]
    adx_period    : Lookback for ADX calculation (default 14)
    atr_period    : Lookback for ATR calculation (default 14)
    trend_thresh  : ADX level above which we call it a trend  (default 25)
    range_thresh  : ADX level below which we call it ranging  (default 20)
    """

    def __init__(
        self,
        df: pd.DataFrame,
        adx_period: int   = 14,
        atr_period: int   = 14,
        trend_thresh: int = 25,
        range_thresh: int = 20,
    ):
        self.df           = df.copy()
        self.adx_period   = adx_period
        self.atr_period   = atr_period
        self.trend_thresh = trend_thresh
        self.range_thresh = range_thresh

        # Pre-compute indicators
        self.df["ema50"]  = compute_ema(df["close"], 50)
        self.df["ema200"] = compute_ema(df["close"], 200)
        self.df["adx"]    = compute_adx(df, adx_period)
        self.df["atr"]    = compute_atr(df, atr_period)

    # ── Latest snapshot values ──────────────────
    @property
    def latest(self) -> pd.Series:
        return self.df.iloc[-1]

    @property
    def adx_value(self) -> float:
        return float(self.latest["adx"])

    @property
    def atr_normalised(self) -> float:
        """ATR as a fraction of price — useful for cross-asset comparison."""
        return float(self.latest["atr"] / self.latest["close"])

    # ── Regime classification ────────────────────
    def detect(self) -> str:
        """
        Returns
        -------
        "TRENDING"  — strong directional move, use trend-following rules
        "NEUTRAL"   — transitional, trade cautiously with higher confidence bar
        "RANGING"   — choppy, skip trend trades or flip to mean-reversion
        """
        adx = self.adx_value

        if adx >= self.trend_thresh:
            return "TRENDING"
        elif adx <= self.range_thresh:
            return "RANGING"
        else:
            return "NEUTRAL"

    # ── Regime-aware position size multiplier ────
    def position_multiplier(self) -> float:
        """
        Returns a scalar 0.0–1.0 to multiply your base lot size by.

        TRENDING  → 1.0  (full size)
        NEUTRAL   → 0.65 (reduced)
        RANGING   → 0.0  (skip trade entirely in trend systems)

        Also scales down when ATR is abnormally high (e.g. news spike).
        """
        regime = self.detect()
        base   = {"TRENDING": 1.0, "NEUTRAL": 0.65, "RANGING": 0.0}[regime]

        # Volatility overlay — shrink size when ATR is spiking
        atr_n = self.atr_normalised
        if atr_n > 0.010:        # very high vol (news, spike)
            vol_scalar = 0.40
        elif atr_n > 0.006:      # elevated vol
            vol_scalar = 0.70
        else:                    # normal
            vol_scalar = 1.0

        return round(base * vol_scalar, 2)

    # ── Human-readable summary ───────────────────
    def summary(self) -> dict:
        return {
            "regime"             : self.detect(),
            "adx"                : round(self.adx_value, 2),
            "atr_normalised_pct" : round(self.atr_normalised * 100, 4),
            "position_multiplier": self.position_multiplier(),
            "ema50"              : round(float(self.latest["ema50"]),  2),
            "ema200"             : round(float(self.latest["ema200"]), 2),
            "price"              : round(float(self.latest["close"]),  2),
        }


# ─────────────────────────────────────────────
#  Drop-in trend_filter function
# ─────────────────────────────────────────────

def trend_filter(
    df: pd.DataFrame,
    ai_confidence: float,
    base_threshold: float = 0.55,
    adx_period: int       = 14,
) -> bool:
    """
    Regime-aware trend filter — replaces the static EMA check in
    best_hybrid_run.py.

    Parameters
    ----------
    df             : OHLCV DataFrame (needs at least 200 rows for ema200)
    ai_confidence  : model output confidence score  (0.0 – 1.0)
    base_threshold : minimum confidence to allow a trade (default 0.55)
    adx_period     : ADX calculation period (default 14)

    Returns
    -------
    True  → trade is allowed
    False → trade is blocked
    """
    detector = RegimeDetector(df, adx_period=adx_period)
    regime   = detector.detect()
    row      = detector.latest

    price  = float(row["close"])
    ema50  = float(row["ema50"])
    ema200 = float(row["ema200"])

    if regime == "TRENDING":
        # Strict: full EMA stack must align
        structure_ok = (price > ema50) and (ema50 > ema200)
        conf_ok      = ai_confidence >= base_threshold
        return structure_ok and conf_ok

    elif regime == "NEUTRAL":
        # Relaxed: only price > ema50, but higher confidence bar
        structure_ok = price > ema50
        conf_ok      = ai_confidence >= (base_threshold + 0.10)
        return structure_ok and conf_ok

    else:  # RANGING
        # Skip trend trades entirely — avoids whipsaws in chop
        return False


# ─────────────────────────────────────────────
#  Quick smoke-test
# ─────────────────────────────────────────────

if __name__ == "__main__":
    # Generate synthetic OHLCV data to verify the module runs
    np.random.seed(42)
    n = 300
    close = 4500 + np.cumsum(np.random.randn(n) * 8)
    df_test = pd.DataFrame({
        "open"  : close - np.random.uniform(1, 5, n),
        "high"  : close + np.random.uniform(2, 10, n),
        "low"   : close - np.random.uniform(2, 10, n),
        "close" : close,
        "volume": np.random.randint(100, 1000, n),
    })

    detector = RegimeDetector(df_test)
    print("=== Regime Detector Summary ===")
    for k, v in detector.summary().items():
        print(f"  {k:<25} {v}")

    allowed = trend_filter(df_test, ai_confidence=0.62)
    print(f"\n  trend_filter(confidence=0.62) → {'ALLOW TRADE ✓' if allowed else 'BLOCK TRADE ✗'}")
