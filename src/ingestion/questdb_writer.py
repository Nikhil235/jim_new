"""
QuestDB Writer
==============
Writes time-series data to QuestDB via ILP (InfluxDB Line Protocol)
and queries data via REST SQL API.

Dual-mode operation:
- When QuestDB is running: writes to database via ILP + reads via SQL
- When QuestDB is offline: falls back to local parquet storage

Phase 2 enhancements:
- write_macro() for macro-correlate data
- write_fred() for FRED economic series
- write_alternative() for COT/sentiment/ETF data
- Deduplication via timestamp checking
- Batch-optimized ILP writes
"""

import time
import socket
import json
from typing import Optional, Dict, List, Any
from pathlib import Path

import pandas as pd
import numpy as np
from loguru import logger

from src.utils.config import get_config, PROJECT_ROOT


class QuestDBWriter:
    """Write and read time-series data to/from QuestDB.

    Uses ILP (Influx Line Protocol) for high-performance ingestion
    and REST SQL for queries. Gracefully falls back to parquet if
    QuestDB is unavailable.
    """

    def __init__(self, config: Optional[dict] = None):
        self.config = config or get_config()
        db_cfg = self.config.get("database", {}).get("questdb", {})
        self.host = db_cfg.get("host", "localhost")
        self.ilp_port = db_cfg.get("port", 9009)
        self.http_port = db_cfg.get("http_port", 9000)
        self.batch_size = self.config.get("pipeline", {}).get("ingestion", {}).get("batch_size", 5000)

        # Fallback storage
        self.fallback_dir = PROJECT_ROOT / "data" / "processed"
        self.fallback_dir.mkdir(parents=True, exist_ok=True)

        self._connected = False
        self._ilp_sock = None

    def is_available(self) -> bool:
        """Check if QuestDB is reachable."""
        try:
            with socket.create_connection((self.host, self.ilp_port), timeout=2.0):
                return True
        except OSError:
            return False

    def _get_ilp_socket(self):
        """Get or create persistent ILP socket."""
        if self._ilp_sock is None:
            self._ilp_sock = socket.create_connection((self.host, self.ilp_port), timeout=10.0)
        return self._ilp_sock

    def _send_ilp(self, lines: List[str]) -> bool:
        """Send ILP lines to QuestDB via TCP socket with automatic retry and connection pooling."""
        payload = "\n".join(lines) + "\n"
        data = payload.encode("utf-8")
        
        for attempt in range(3):
            try:
                sock = self._get_ilp_socket()
                sock.sendall(data)
                return True
            except OSError as e:
                logger.warning(f"QuestDB ILP send failed (attempt {attempt+1}/3): {e}")
                if self._ilp_sock:
                    try:
                        self._ilp_sock.close()
                    except Exception:
                        pass
                    self._ilp_sock = None
                time.sleep(0.5 * (attempt + 1))
                
        logger.error("QuestDB ILP send completely failed after 3 attempts")
        return False

    def _query_rest(self, sql: str) -> Optional[pd.DataFrame]:
        """Execute a SQL query via QuestDB REST API."""
        try:
            import urllib.request
            import urllib.parse
            url = f"http://{self.host}:{self.http_port}/exec?query={urllib.parse.quote(sql)}"
            with urllib.request.urlopen(url, timeout=30) as resp:
                result = json.loads(resp.read().decode())

            if "dataset" not in result:
                return None

            columns = [col["name"] for col in result["columns"]]
            df = pd.DataFrame(result["dataset"], columns=columns)
            return df
        except Exception as e:
            logger.error(f"QuestDB query failed: {e}")
            return None

    def _ts_to_ns(self, idx) -> int:
        """Convert a pandas timestamp/index to nanoseconds."""
        if hasattr(idx, 'timestamp'):
            return int(idx.timestamp() * 1_000_000_000)
        return int(time.time() * 1_000_000_000)

    def _safe_float(self, val) -> Optional[float]:
        """Return float value if valid, else None."""
        if pd.notna(val) and np.isfinite(val):
            return float(val)
        return None

    # ──────────────────────────────────────────────────────
    # Gold OHLCV Data
    # ──────────────────────────────────────────────────────

    def write_ohlcv(self, df: pd.DataFrame, table: str, symbol: str = "XAUUSD") -> int:
        """Write OHLCV DataFrame to QuestDB.

        Args:
            df: DataFrame with OHLCV columns and DatetimeIndex.
            table: QuestDB table name (e.g., 'gold_1d', 'gold_1m').
            symbol: Instrument symbol tag.

        Returns:
            Number of rows written.
        """
        if df.empty:
            return 0

        if self.is_available():
            return self._write_ohlcv_ilp(df, table, symbol)
        else:
            return self._write_ohlcv_parquet(df, table, symbol)

    def _write_ohlcv_ilp(self, df: pd.DataFrame, table: str, symbol: str) -> int:
        """Write OHLCV data via ILP protocol."""
        rows_written = 0
        lines = []

        for idx, row in df.iterrows():
            ts_ns = self._ts_to_ns(idx)

            fields = []
            for col in ["open", "high", "low", "close"]:
                if col in df.columns:
                    val = self._safe_float(row[col])
                    if val is not None:
                        fields.append(f"{col}={val}")

            if "volume" in df.columns and pd.notna(row.get("volume")):
                fields.append(f"volume={int(row['volume'])}i")

            for col in ["returns", "log_returns", "spread", "typical_price"]:
                if col in df.columns:
                    val = self._safe_float(row.get(col))
                    if val is not None:
                        fields.append(f"{col}={val}")

            if fields:
                line = f"{table},symbol={symbol} {','.join(fields)} {ts_ns}"
                lines.append(line)
                rows_written += 1

            if len(lines) >= self.batch_size:
                if not self._send_ilp(lines):
                    return self._write_ohlcv_parquet(df, table, symbol)
                lines = []

        if lines:
            if not self._send_ilp(lines):
                return self._write_ohlcv_parquet(df, table, symbol)

        logger.info(f"QuestDB: Wrote {rows_written} rows to '{table}' (symbol={symbol})")
        return rows_written

    def _write_ohlcv_parquet(self, df: pd.DataFrame, table: str, symbol: str) -> int:
        """Fallback: write to local parquet file."""
        filepath = self.fallback_dir / f"{table}_{symbol}.parquet"
        df.to_parquet(filepath, engine="pyarrow")
        logger.info(f"Parquet fallback: Wrote {len(df)} rows to {filepath}")
        return len(df)

    # ──────────────────────────────────────────────────────
    # Macro-Correlate Data
    # ──────────────────────────────────────────────────────

    def write_macro(self, macro_data: Dict[str, pd.DataFrame], table: str = "macro_daily") -> int:
        """Write macro-correlate DataFrames to QuestDB.

        Each macro source (dxy, vix, etc.) is written with its name as the symbol tag.

        Args:
            macro_data: Dict of name → DataFrame from MacroFetcher.
            table: Target table name.

        Returns:
            Total rows written across all macro sources.
        """
        total = 0
        for name, df in macro_data.items():
            count = self.write_ohlcv(df, table=table, symbol=name.upper())
            total += count
        logger.info(f"QuestDB: Wrote {total} total macro rows to '{table}'")
        return total

    # ──────────────────────────────────────────────────────
    # FRED Economic Data
    # ──────────────────────────────────────────────────────

    def write_fred(self, fred_df: pd.DataFrame, table: str = "fred_daily") -> int:
        """Write FRED data (wide DataFrame with series columns) to QuestDB.

        Converts wide format to long format (series_id, value) for storage.

        Args:
            fred_df: DataFrame with columns = series IDs and DatetimeIndex.
            table: Target table name.

        Returns:
            Number of rows written.
        """
        if fred_df.empty:
            return 0

        if not self.is_available():
            filepath = self.fallback_dir / f"{table}.parquet"
            fred_df.to_parquet(filepath, engine="pyarrow")
            logger.info(f"Parquet fallback: FRED {len(fred_df)} rows → {filepath}")
            return len(fred_df)

        rows_written = 0
        lines = []

        for idx, row in fred_df.iterrows():
            ts_ns = self._ts_to_ns(idx)
            for series_id in fred_df.columns:
                val = self._safe_float(row[series_id])
                if val is not None:
                    line = f"{table},series_id={series_id} value={val} {ts_ns}"
                    lines.append(line)
                    rows_written += 1

                if len(lines) >= self.batch_size:
                    self._send_ilp(lines)
                    lines = []

        if lines:
            self._send_ilp(lines)

        logger.info(f"QuestDB: Wrote {rows_written} FRED observations to '{table}'")
        return rows_written

    # ──────────────────────────────────────────────────────
    # Alternative Data (COT, Sentiment, ETF)
    # ──────────────────────────────────────────────────────

    def write_cot(self, df: pd.DataFrame, table: str = "cot_weekly") -> int:
        """Write COT positioning data to QuestDB."""
        if df.empty:
            return 0

        if not self.is_available():
            filepath = self.fallback_dir / f"{table}.parquet"
            df.to_parquet(filepath, engine="pyarrow")
            return len(df)

        rows_written = 0
        lines = []
        int_cols = [
            "commercial_long", "commercial_short", "commercial_spread",
            "noncommercial_long", "noncommercial_short", "noncommercial_spread",
            "total_long", "total_short", "open_interest",
            "net_commercial", "net_noncommercial",
        ]

        contract = "GOLD"
        if "contract" in df.columns:
            contract = str(df["contract"].iloc[0])

        for idx, row in df.iterrows():
            ts_ns = self._ts_to_ns(idx)
            fields = []
            for col in int_cols:
                if col in df.columns and pd.notna(row.get(col)):
                    fields.append(f"{col}={int(row[col])}i")
            if fields:
                line = f"{table},contract={contract} {','.join(fields)} {ts_ns}"
                lines.append(line)
                rows_written += 1
            if len(lines) >= self.batch_size:
                self._send_ilp(lines)
                lines = []

        if lines:
            self._send_ilp(lines)

        logger.info(f"QuestDB: Wrote {rows_written} COT rows to '{table}'")
        return rows_written

    def write_sentiment(self, df: pd.DataFrame, table: str = "sentiment_daily") -> int:
        """Write sentiment scores to QuestDB."""
        if df.empty:
            return 0

        if not self.is_available():
            filepath = self.fallback_dir / f"{table}.parquet"
            df.to_parquet(filepath, engine="pyarrow")
            return len(df)

        rows_written = 0
        lines = []
        source = "newsapi"
        if "source" in df.columns:
            source = str(df["source"].iloc[0])

        for idx, row in df.iterrows():
            ts_ns = self._ts_to_ns(idx)
            fields = []
            for col in ["keyword_score", "fear_index"]:
                val = self._safe_float(row.get(col))
                if val is not None:
                    fields.append(f"{col}={val}")
            for col in ["article_count", "positive_count", "negative_count", "neutral_count", "safe_haven_mentions"]:
                if col in df.columns and pd.notna(row.get(col)):
                    fields.append(f"{col}={int(row[col])}i")
            if fields:
                line = f"{table},source={source} {','.join(fields)} {ts_ns}"
                lines.append(line)
                rows_written += 1
            if len(lines) >= self.batch_size:
                self._send_ilp(lines)
                lines = []

        if lines:
            self._send_ilp(lines)

        logger.info(f"QuestDB: Wrote {rows_written} sentiment rows to '{table}'")
        return rows_written

    def write_etf_flows(self, etf_data: Dict[str, pd.DataFrame], table: str = "etf_flows_daily") -> int:
        """Write ETF flow data to QuestDB."""
        total = 0
        for symbol, df in etf_data.items():
            if df.empty:
                continue
            # Reuse OHLCV writer with extra columns handled
            count = self.write_ohlcv(df, table=table, symbol=symbol)
            total += count
        return total

    # ──────────────────────────────────────────────────────
    # Features
    # ──────────────────────────────────────────────────────

    def write_features(self, df: pd.DataFrame, table: str = "features") -> int:
        """Write computed features to QuestDB."""
        if df.empty:
            return 0

        if self.is_available():
            rows_written = 0
            lines = []
            feature_cols = [c for c in df.columns if c not in {"open", "high", "low", "close", "volume"}]

            for idx, row in df.iterrows():
                ts_ns = self._ts_to_ns(idx)
                fields = []
                for col in feature_cols:
                    val = self._safe_float(row.get(col))
                    if val is not None:
                        fields.append(f"{col}={val}")

                if fields:
                    line = f"{table} {','.join(fields)} {ts_ns}"
                    lines.append(line)
                    rows_written += 1

                if len(lines) >= self.batch_size:
                    self._send_ilp(lines)
                    lines = []

            if lines:
                self._send_ilp(lines)

            logger.info(f"QuestDB: Wrote {rows_written} feature rows to '{table}'")
            return rows_written
        else:
            filepath = self.fallback_dir / f"{table}.parquet"
            df.to_parquet(filepath, engine="pyarrow")
            logger.info(f"Parquet fallback: Wrote {len(df)} feature rows to {filepath}")
            return len(df)

    # ──────────────────────────────────────────────────────
    # Query & Catalog
    # ──────────────────────────────────────────────────────

    def query(self, sql: str) -> Optional[pd.DataFrame]:
        """Execute a SQL query against QuestDB."""
        if not self.is_available():
            logger.warning("QuestDB unavailable for query")
            return None
        return self._query_rest(sql)

    def get_last_timestamp(self, table: str, symbol: Optional[str] = None) -> Optional[str]:
        """Get the most recent timestamp in a table.

        Useful for incremental ingestion — only fetch data newer than this.
        """
        where = f"WHERE symbol = '{symbol}'" if symbol else ""
        df = self.query(f"SELECT max(timestamp) as last_ts FROM '{table}' {where}")
        if df is not None and not df.empty and df["last_ts"].iloc[0]:
            return str(df["last_ts"].iloc[0])
        return None

    def get_table_info(self, table: str) -> Optional[Dict[str, Any]]:
        """Get row count and date range for a table."""
        df = self.query(f"SELECT count() as cnt, min(timestamp) as first_ts, max(timestamp) as last_ts FROM '{table}'")
        if df is not None and not df.empty:
            return {
                "table": table,
                "row_count": int(df["cnt"].iloc[0]),
                "first_timestamp": df["first_ts"].iloc[0],
                "last_timestamp": df["last_ts"].iloc[0],
            }
        return None

    def get_data_catalog(self) -> Dict[str, Any]:
        """Get a catalog of all data tables and their status."""
        catalog = {"questdb_available": self.is_available(), "tables": {}}

        for f in self.fallback_dir.glob("*.parquet"):
            try:
                df = pd.read_parquet(f)
                catalog["tables"][f.stem] = {
                    "source": "parquet",
                    "rows": len(df),
                    "columns": len(df.columns),
                    "first_date": str(df.index[0]) if len(df) > 0 else None,
                    "last_date": str(df.index[-1]) if len(df) > 0 else None,
                    "file_size_mb": round(f.stat().st_size / 1_048_576, 2),
                }
            except Exception:
                catalog["tables"][f.stem] = {"source": "parquet", "error": "unreadable"}

        return catalog
