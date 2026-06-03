"""
ASCENDING TRIANGLE PATTERN RECOGNITION FOR GOLD
Detects swing highs/lows and ascending triangle breakout patterns.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from scipy.signal import find_peaks
from loguru import logger


@dataclass
class PivotPoint:
    index: int
    price: float
    pivot_type: str
    strength: int = 1


@dataclass
class TrianglePattern:
    resistance_level: float
    support_level: float
    resistance_touches: List[int]
    support_touches: List[int]
    breakout_price: float
    pattern_start: int
    pattern_end: int
    confidence: float
    valid: bool = True


class AscendingTriangleDetector:
    """
    Detect Ascending Triangle Patterns in Gold Charts.

    - Resistance: flat horizontal line (>= 2 touches)
    - Support: rising trendline (>= 2 higher lows)
    - Breakout: price closes above resistance
    """

    def __init__(
        self,
        min_touches: int = 2,
        tolerance_pct: float = 0.005,
        lookback: int = 50,
    ):
        self.min_touches = min_touches
        self.tolerance_pct = tolerance_pct
        self.lookback = lookback

    def detect_pivot_points(self, data: pd.DataFrame, window: int = 5) -> pd.DataFrame:
        df = data.copy()
        high_col = "High" if "High" in df.columns else "high"
        low_col = "Low" if "Low" in df.columns else "low"

        high_peaks, _ = find_peaks(df[high_col].values, distance=2 * window + 1, prominence=0.001)
        df["swing_high"] = False
        df.iloc[high_peaks, df.columns.get_loc("swing_high")] = True

        low_valleys, _ = find_peaks(-df[low_col].values, distance=2 * window + 1, prominence=0.001)
        df["swing_low"] = False
        df.iloc[low_valleys, df.columns.get_loc("swing_low")] = True

        return df

    def _find_resistance(self, df: pd.DataFrame, start_idx: int, end_idx: int) -> Optional[Tuple[float, np.ndarray]]:
        high_col = "High" if "High" in df.columns else "high"
        segment = df.iloc[start_idx:end_idx + 1]
        swing = segment[segment["swing_high"]]
        if len(swing) < self.min_touches:
            return None
        prices = swing[high_col].values
        indices = swing.index.values
        resistance = float(np.median(prices))
        if np.std(prices) / resistance > self.tolerance_pct:
            return None
        touches = indices[np.abs(prices - resistance) < (resistance * self.tolerance_pct)]
        if len(touches) < self.min_touches:
            return None
        return resistance, touches

    def _find_support(self, df: pd.DataFrame, start_idx: int, end_idx: int, resistance: float) -> Optional[Tuple[float, List[int]]]:
        low_col = "Low" if "Low" in df.columns else "low"
        segment = df.iloc[start_idx:end_idx + 1]
        swing = segment[
            (segment["swing_low"])
            & (segment[low_col] < resistance * 0.98)
        ]
        if len(swing) < self.min_touches:
            return None
        prices = swing[low_col].values
        indices = swing.index.values
        if prices[-1] <= prices[0]:
            return None
        support = float(prices[-1])
        touches = indices[np.abs(prices - support) < (support * self.tolerance_pct * 2)]
        return support, touches.tolist()

    def detect_triangle(self, df: pd.DataFrame, idx: int) -> Optional[TrianglePattern]:
        start_idx = max(0, idx - self.lookback)
        high_col = "High" if "High" in df.columns else "high"
        low_col = "Low" if "Low" in df.columns else "low"
        close_col = "Close" if "Close" in df.columns else "close"

        res = self._find_resistance(df, start_idx, idx)
        if res is None:
            return None
        resistance, res_touches = res

        sup = self._find_support(df, start_idx, idx, resistance)
        if sup is None:
            return None
        support, sup_touches = sup

        confidence = self._calculate_confidence(df, resistance, support, res_touches, sup_touches, idx)

        breakout = df.loc[idx, close_col] > resistance
        prev = df.loc[idx - 1, close_col] if idx > 0 else resistance
        breakout_confirmed = bool(breakout and (prev <= resistance))

        return TrianglePattern(
            resistance_level=resistance,
            support_level=support,
            resistance_touches=res_touches.tolist(),
            support_touches=sup_touches,
            breakout_price=resistance,
            pattern_start=start_idx,
            pattern_end=idx,
            confidence=min(confidence, 1.0),
            valid=breakout_confirmed,
        )

    def _calculate_confidence(self, df: pd.DataFrame, resistance: float, support: float,
                              res_touches: np.ndarray, sup_touches: List[int], idx: int) -> float:
        high_col = "High" if "High" in df.columns else "high"
        low_col = "Low" if "Low" in df.columns else "low"
        vol_col = "Volume" if "Volume" in df.columns else "volume"

        c = 0.5
        c += min(0.2, (len(res_touches) - 2) * 0.05)

        swings = df[df["swing_high"]][high_col].values
        if len(swings) > 0:
            variation = np.std(swings[-len(res_touches):]) / resistance if len(res_touches) <= len(swings) else 0
            c += max(0, 0.2 - variation * 10)

        if len(sup_touches) >= 2:
            support_prices = df.loc[sup_touches, low_col].values
            rise = (support_prices[-1] - support_prices[0]) / support_prices[0]
            c += min(0.1, rise * 2)

        if idx < len(df) and vol_col in df.columns:
            cv = df.loc[idx, vol_col]
            av = df[vol_col].rolling(20).mean().iloc[idx]
            if av > 0 and cv > av * 1.5:
                c += 0.1

        return min(c, 1.0)

    def detect_all_triangles(self, data: pd.DataFrame, min_confidence: float = 0.7) -> List[TrianglePattern]:
        df = self.detect_pivot_points(data, window=5)
        patterns: List[TrianglePattern] = []
        for idx in range(self.lookback, len(df)):
            pattern = self.detect_triangle(df, idx)
            if pattern and pattern.confidence >= min_confidence:
                dup = False
                for existing in patterns:
                    if abs(existing.resistance_level - pattern.resistance_level) < 0.001:
                        dup = True
                        break
                if not dup:
                    patterns.append(pattern)
        return patterns

    def generate_signals(self, data: pd.DataFrame, min_confidence: float = 0.7) -> pd.DataFrame:
        df = data.copy()
        close_col = "Close" if "Close" in df.columns else "close"
        low_col = "Low" if "Low" in df.columns else "low"
        df["triangle_signal"] = 0
        df["confidence"] = 0.0
        df["entry_price"] = np.nan
        df["stop_loss"] = np.nan
        df["take_profit"] = np.nan

        patterns = self.detect_all_triangles(data, min_confidence)
        for p in patterns:
            if p.valid:
                df.loc[p.pattern_end, "triangle_signal"] = 1
                df.loc[p.pattern_end, "confidence"] = p.confidence
                df.loc[p.pattern_end, "entry_price"] = p.resistance_level
                df.loc[p.pattern_end, "stop_loss"] = p.support_level
                df.loc[p.pattern_end, "take_profit"] = p.resistance_level + (p.resistance_level - p.support_level)

        return df
