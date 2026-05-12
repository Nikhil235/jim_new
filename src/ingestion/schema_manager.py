"""
QuestDB Schema Manager
======================
Auto-creates and manages all QuestDB tables for the Mini-Medallion pipeline.
Ensures tables exist before any data ingestion begins.

Tables created:
  - gold_1d, gold_1h, gold_1m     → Gold OHLCV at multiple resolutions
  - macro_daily                    → DXY, VIX, TLT, TIP, Silver, Oil, CNY
  - fred_daily                     → Fed Funds, TIPS, Yield Curve
  - cot_weekly                     → CFTC Commitments of Traders
  - sentiment_daily                → News sentiment scores
  - features_daily, features_1h    → Computed features
"""

import socket
import json
import urllib.request
import urllib.parse
from typing import Optional, List, Dict
from loguru import logger

from src.utils.config import get_config


# ──────────────────────────────────────────────────────────────
# Table Definitions — ILP auto-creates columns on first write,
# but we define schemas here for documentation & validation.
# ──────────────────────────────────────────────────────────────

SCHEMAS: Dict[str, str] = {
    # Gold OHLCV — Daily
    "gold_1d": """
        CREATE TABLE IF NOT EXISTS gold_1d (
            timestamp TIMESTAMP,
            symbol SYMBOL,
            open DOUBLE,
            high DOUBLE,
            low DOUBLE,
            close DOUBLE,
            volume LONG,
            returns DOUBLE,
            log_returns DOUBLE,
            spread DOUBLE,
            typical_price DOUBLE
        ) timestamp(timestamp) PARTITION BY MONTH WAL
            DEDUP UPSERT KEYS(timestamp, symbol);
    """,

    # Gold OHLCV — Hourly
    "gold_1h": """
        CREATE TABLE IF NOT EXISTS gold_1h (
            timestamp TIMESTAMP,
            symbol SYMBOL,
            open DOUBLE,
            high DOUBLE,
            low DOUBLE,
            close DOUBLE,
            volume LONG,
            returns DOUBLE,
            log_returns DOUBLE,
            spread DOUBLE,
            typical_price DOUBLE
        ) timestamp(timestamp) PARTITION BY WEEK WAL
            DEDUP UPSERT KEYS(timestamp, symbol);
    """,

    # Gold OHLCV — Minute
    "gold_1m": """
        CREATE TABLE IF NOT EXISTS gold_1m (
            timestamp TIMESTAMP,
            symbol SYMBOL,
            open DOUBLE,
            high DOUBLE,
            low DOUBLE,
            close DOUBLE,
            volume LONG,
            returns DOUBLE,
            log_returns DOUBLE,
            spread DOUBLE,
            typical_price DOUBLE
        ) timestamp(timestamp) PARTITION BY DAY WAL
            DEDUP UPSERT KEYS(timestamp, symbol);
    """,

    # Gold Ticks (from Phase 1 spec)
    "gold_ticks": """
        CREATE TABLE IF NOT EXISTS gold_ticks (
            timestamp TIMESTAMP,
            bid DOUBLE,
            ask DOUBLE,
            bid_size DOUBLE,
            ask_size DOUBLE,
            trade_price DOUBLE,
            trade_size DOUBLE,
            source SYMBOL
        ) timestamp(timestamp) PARTITION BY DAY WAL;
    """,

    # Macro-correlate data (all in one wide table)
    "macro_daily": """
        CREATE TABLE IF NOT EXISTS macro_daily (
            timestamp TIMESTAMP,
            symbol SYMBOL,
            open DOUBLE,
            high DOUBLE,
            low DOUBLE,
            close DOUBLE,
            volume LONG,
            returns DOUBLE
        ) timestamp(timestamp) PARTITION BY MONTH WAL
            DEDUP UPSERT KEYS(timestamp, symbol);
    """,

    # FRED economic data (long format)
    "fred_daily": """
        CREATE TABLE IF NOT EXISTS fred_daily (
            timestamp TIMESTAMP,
            series_id SYMBOL,
            value DOUBLE
        ) timestamp(timestamp) PARTITION BY YEAR WAL
            DEDUP UPSERT KEYS(timestamp, series_id);
    """,

    # CFTC Commitments of Traders (weekly)
    "cot_weekly": """
        CREATE TABLE IF NOT EXISTS cot_weekly (
            timestamp TIMESTAMP,
            contract SYMBOL,
            commercial_long LONG,
            commercial_short LONG,
            commercial_spread LONG,
            noncommercial_long LONG,
            noncommercial_short LONG,
            noncommercial_spread LONG,
            total_long LONG,
            total_short LONG,
            open_interest LONG,
            net_commercial LONG,
            net_noncommercial LONG
        ) timestamp(timestamp) PARTITION BY YEAR WAL
            DEDUP UPSERT KEYS(timestamp, contract);
    """,

    # News / alternative sentiment (daily)
    "sentiment_daily": """
        CREATE TABLE IF NOT EXISTS sentiment_daily (
            timestamp TIMESTAMP,
            source SYMBOL,
            keyword_score DOUBLE,
            article_count LONG,
            positive_count LONG,
            negative_count LONG,
            neutral_count LONG,
            safe_haven_mentions LONG,
            fear_index DOUBLE
        ) timestamp(timestamp) PARTITION BY MONTH WAL
            DEDUP UPSERT KEYS(timestamp, source);
    """,

    # ETF flows
    "etf_flows_daily": """
        CREATE TABLE IF NOT EXISTS etf_flows_daily (
            timestamp TIMESTAMP,
            symbol SYMBOL,
            close DOUBLE,
            volume LONG,
            volume_ma20 DOUBLE,
            volume_ratio DOUBLE,
            flow_proxy DOUBLE
        ) timestamp(timestamp) PARTITION BY MONTH WAL
            DEDUP UPSERT KEYS(timestamp, symbol);
    """,
}


class SchemaManager:
    """Manages QuestDB table creation and schema validation.

    Call `ensure_all_tables()` at pipeline startup to guarantee
    all required tables exist before ingestion begins.
    """

    def __init__(self, config: Optional[dict] = None):
        self.config = config or get_config()
        db_cfg = self.config.get("database", {}).get("questdb", {})
        self.host = db_cfg.get("host", "localhost")
        self.http_port = db_cfg.get("http_port", 9000)
        self.ilp_port = db_cfg.get("port", 9009)

    def is_available(self) -> bool:
        """Check if QuestDB is reachable."""
        try:
            with socket.create_connection((self.host, self.ilp_port), timeout=2.0):
                return True
        except OSError:
            return False

    def _exec_sql(self, sql: str) -> Optional[dict]:
        """Execute SQL via QuestDB HTTP API."""
        try:
            url = f"http://{self.host}:{self.http_port}/exec?query={urllib.parse.quote(sql.strip())}"
            with urllib.request.urlopen(url, timeout=15) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            logger.error(f"QuestDB SQL exec failed: {e}")
            return None

    def ensure_table(self, table_name: str) -> bool:
        """Create a single table if it doesn't exist.

        Args:
            table_name: Must match a key in SCHEMAS.

        Returns:
            True if table exists or was created successfully.
        """
        if table_name not in SCHEMAS:
            logger.warning(f"Unknown table: {table_name} — no schema defined")
            return False

        if not self.is_available():
            logger.warning("QuestDB unavailable — skipping table creation")
            return False

        sql = SCHEMAS[table_name]
        result = self._exec_sql(sql)
        if result is not None:
            logger.info(f"✅ Table '{table_name}' ensured")
            return True
        else:
            logger.error(f"❌ Failed to create table '{table_name}'")
            return False

    def ensure_all_tables(self) -> Dict[str, bool]:
        """Create all tables defined in SCHEMAS.

        Returns:
            Dict of table_name → success boolean.
        """
        if not self.is_available():
            logger.warning("QuestDB unavailable — skipping all table creation")
            return {name: False for name in SCHEMAS}

        results = {}
        for table_name in SCHEMAS:
            results[table_name] = self.ensure_table(table_name)

        created = sum(1 for v in results.values() if v)
        total = len(results)
        logger.info(f"Schema init: {created}/{total} tables ensured")
        return results

    def list_tables(self) -> Optional[List[str]]:
        """List all tables in QuestDB."""
        if not self.is_available():
            return None
        result = self._exec_sql("SHOW TABLES;")
        if result and "dataset" in result:
            return [row[0] for row in result["dataset"]]
        return None

    def get_table_row_counts(self) -> Dict[str, int]:
        """Get row counts for all known tables."""
        counts = {}
        if not self.is_available():
            return counts

        for table_name in SCHEMAS:
            result = self._exec_sql(f"SELECT count() as cnt FROM '{table_name}';")
            if result and "dataset" in result and result["dataset"]:
                counts[table_name] = int(result["dataset"][0][0])
            else:
                counts[table_name] = 0

        return counts

    def get_schema_names(self) -> List[str]:
        """Get list of all defined table names."""
        return list(SCHEMAS.keys())
