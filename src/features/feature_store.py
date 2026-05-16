"""
Redis Feature Store
===================
Real-time feature serving layer for ML model input.
Stores computed feature vectors in Redis for low-latency retrieval.

Phase 2 enhancements:
- Batch-optimized store_features_batch()
- Feature drift detection via get_feature_drift_report()
- Feature metadata and importance tracking
"""

import json
import time
from typing import Optional, Dict, List, Any
from pathlib import Path

import pandas as pd
import numpy as np
from loguru import logger

from src.utils.config import get_config, PROJECT_ROOT


class FeatureStore:
    """Redis-backed feature store for real-time model serving.

    Dual-mode: Redis for production, parquet for development.
    """

    def __init__(self, config: Optional[dict] = None):
        self.config = config or get_config()
        fs_cfg = self.config.get("pipeline", {}).get("feature_store", {})
        redis_cfg = self.config.get("database", {}).get("redis", {})

        self.prefix = fs_cfg.get("redis_prefix", "feature")
        self.ttl_days = fs_cfg.get("ttl_days", 30)
        self.archive_to_parquet = fs_cfg.get("archive_to_parquet", True)

        self._redis_host = redis_cfg.get("host", "localhost")
        self._redis_port = redis_cfg.get("port", 6379)
        self._redis_db = redis_cfg.get("db", 0)
        self._redis_password = redis_cfg.get("password", "") or None

        self._redis = None
        self._fallback_dir = PROJECT_ROOT / "data" / "features"
        self._fallback_dir.mkdir(parents=True, exist_ok=True)
        self._feature_metadata: Dict[str, Any] = {}

    def _get_redis(self):
        """Lazy-connect to Redis."""
        if self._redis is False:
            return None  # Sentinel: explicitly disabled
        if self._redis is not None:
            return self._redis
        try:
            from src.utils.redis_client import get_redis_client
            self._redis = get_redis_client()
            self._redis.ping()
            logger.debug(f"Redis connected: {self._redis_host}:{self._redis_port}")
            return self._redis
        except Exception as e:
            logger.debug(f"Redis unavailable ({e}), using parquet fallback")
            self._redis = None
            return None

    def is_available(self) -> bool:
        """Check if Redis is reachable."""
        r = self._get_redis()
        if r is None:
            return False
        try:
            r.ping()
            return True
        except Exception:
            self._redis = None
            return False

    def store_features(self, df: pd.DataFrame, symbol: str = "XAUUSD") -> int:
        """Store a DataFrame of features."""
        if df.empty:
            return 0
        r = self._get_redis()
        if r is not None:
            return self._store_redis(df, symbol, r)
        return self._store_parquet(df, symbol)

    def store_features_batch(self, df: pd.DataFrame, symbol: str = "XAUUSD", chunk_size: int = 5000) -> int:
        """Batch-optimized feature storage.

        Splits large DataFrames into chunks for memory efficiency.
        Always archives to parquet for bulk historical access.
        """
        if df.empty:
            return 0

        # Always save to parquet (fast bulk reads for training)
        parquet_count = self._store_parquet(df, symbol)

        # Also store in Redis if available (for real-time serving)
        r = self._get_redis()
        if r is not None:
            total = 0
            for start in range(0, len(df), chunk_size):
                chunk = df.iloc[start:start + chunk_size]
                total += self._store_redis(chunk, symbol, r)
            logger.info(f"FeatureStore batch: {total} vectors → Redis + parquet")
            return total

        return parquet_count

    def _store_redis(self, df: pd.DataFrame, symbol: str, r) -> int:
        stored = 0
        ttl_seconds = self.ttl_days * 86400
        pipe = r.pipeline()

        for idx, row in df.iterrows():
            ts_str = str(idx)
            key = f"{self.prefix}:{symbol}:{ts_str}"
            feature_dict = {}
            for col, val in row.items():
                if pd.notna(val) and np.isfinite(val):
                    feature_dict[col] = str(float(val))
            if feature_dict:
                pipe.hset(key, mapping=feature_dict)
                pipe.expire(key, ttl_seconds)
                stored += 1
            if stored % 1000 == 0 and stored > 0:
                pipe.execute()
                pipe = r.pipeline()

        if stored % 1000 != 0:
            pipe.execute()

        if len(df) > 0:
            r.set(f"{self.prefix}:{symbol}:latest_ts", str(df.index[-1]), ex=ttl_seconds)
            r.set(f"{self.prefix}:{symbol}:feature_count", str(len(df.columns)), ex=ttl_seconds)

        self._feature_metadata[symbol] = {
            "feature_names": list(df.columns), "last_stored": str(df.index[-1]) if len(df) > 0 else None,
            "row_count": stored, "storage": "redis",
        }
        logger.info(f"FeatureStore: {stored} vectors for {symbol} → Redis ({len(df.columns)} features each)")
        return stored

    def _store_parquet(self, df: pd.DataFrame, symbol: str) -> int:
        filepath = self._fallback_dir / f"{self.prefix}_{symbol}.parquet"
        df.to_parquet(filepath, engine="pyarrow")
        self._feature_metadata[symbol] = {
            "feature_names": list(df.columns), "last_stored": str(df.index[-1]) if len(df) > 0 else None,
            "row_count": len(df), "storage": "parquet", "path": str(filepath),
        }
        logger.info(f"FeatureStore: {len(df)} vectors for {symbol} → parquet ({filepath.name})")
        return len(df)

    def get_latest_features(self, symbol: str = "XAUUSD") -> Optional[Dict[str, float]]:
        """Get the most recent feature vector for a symbol."""
        r = self._get_redis()
        if r is not None:
            try:
                latest_ts = r.get(f"{self.prefix}:{symbol}:latest_ts")
                if latest_ts:
                    features = r.hgetall(f"{self.prefix}:{symbol}:{latest_ts}")
                    if features:
                        return {k: float(v) for k, v in features.items()}
            except Exception as e:
                logger.debug(f"Redis get_latest failed: {e}")

        filepath = self._fallback_dir / f"{self.prefix}_{symbol}.parquet"
        if filepath.exists():
            try:
                df = pd.read_parquet(filepath)
                if not df.empty:
                    return {col: float(val) for col, val in df.iloc[-1].items() if pd.notna(val)}
            except Exception:
                pass
        return None

    def get_feature_history(self, symbol: str = "XAUUSD", n_rows: int = 100) -> Optional[pd.DataFrame]:
        """Get recent feature history as a DataFrame."""
        filepath = self._fallback_dir / f"{self.prefix}_{symbol}.parquet"
        if filepath.exists():
            try:
                df = pd.read_parquet(filepath)
                return df.tail(n_rows)
            except Exception:
                pass

        r = self._get_redis()
        if r is not None:
            try:
                pattern = f"{self.prefix}:{symbol}:2*"
                keys = sorted(list(r.scan_iter(match=pattern, count=1000)))
                keys = keys[-n_rows:]
                rows = []
                for key in keys:
                    features = r.hgetall(key)
                    if features:
                        ts = key.split(":", 2)[-1]
                        row = {k: float(v) for k, v in features.items()}
                        row["_timestamp"] = ts
                        rows.append(row)
                if rows:
                    df = pd.DataFrame(rows)
                    if "_timestamp" in df.columns:
                        df.index = pd.to_datetime(df["_timestamp"])
                        df = df.drop(columns=["_timestamp"])
                    return df
            except Exception as e:
                logger.debug(f"Redis history failed: {e}")
        return None

    def get_feature_drift_report(self, symbol: str = "XAUUSD", baseline_pct: float = 0.5) -> Optional[Dict[str, Any]]:
        """Detect feature drift by comparing recent vs historical distributions.

        Splits the stored features into baseline (first half) and recent (last 20%),
        then computes mean/std shift per feature.

        Returns:
            Dict with per-feature drift scores and overall drift flag.
        """
        filepath = self._fallback_dir / f"{self.prefix}_{symbol}.parquet"
        if not filepath.exists():
            return None

        try:
            df = pd.read_parquet(filepath)
            if len(df) < 100:
                return {"status": "insufficient_data", "rows": len(df)}

            split = int(len(df) * baseline_pct)
            baseline = df.iloc[:split]
            recent = df.iloc[-int(len(df) * 0.2):]

            drift_scores = {}
            for col in df.columns:
                if df[col].dtype not in [np.float64, np.float32, np.int64]:
                    continue
                b_mean, b_std = baseline[col].mean(), baseline[col].std()
                r_mean = recent[col].mean()
                if b_std > 0:
                    drift = abs(r_mean - b_mean) / b_std
                else:
                    drift = 0.0
                drift_scores[col] = round(float(drift), 3)

            drifted = {k: v for k, v in drift_scores.items() if v > 2.0}
            return {
                "status": "drift_detected" if drifted else "stable",
                "total_features": len(drift_scores),
                "drifted_features": len(drifted),
                "top_drifted": dict(sorted(drifted.items(), key=lambda x: -x[1])[:10]),
                "drift_threshold": 2.0,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_metadata(self) -> Dict[str, Any]:
        """Get feature store metadata."""
        result = {
            "redis_available": self.is_available(),
            "symbols": self._feature_metadata.copy(),
            "fallback_dir": str(self._fallback_dir),
        }
        parquet_files = list(self._fallback_dir.glob("*.parquet"))
        result["parquet_files"] = len(parquet_files)
        result["total_parquet_size_mb"] = round(
            sum(f.stat().st_size for f in parquet_files) / 1_048_576, 2
        )
        return result
