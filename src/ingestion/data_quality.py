"""
Data Quality Monitor
====================
Validates data integrity across all ingested feeds.
"Bad data in → bad signals out → bad trades → blown account."

Phase 2 enhancements:
- Staleness monitoring (last update timestamp per source)
- Cross-source timestamp alignment checks
- Correlation break detection (Gold/DXY vs historical)
- Prometheus metrics exposure
- Auto-recovery recommendations
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from loguru import logger

from src.utils.config import get_config


@dataclass
class QualityAlert:
    """A data quality issue found during validation."""
    severity: str          # "critical", "warning", "info"
    source: str            # Data source name
    check_type: str        # "gap", "outlier", "stale", "completeness"
    message: str           # Human-readable description
    timestamp: datetime = field(default_factory=datetime.utcnow)
    details: dict = field(default_factory=dict)


class DataQualityMonitor:
    """Monitor and validate data quality across all feeds."""

    def __init__(self, config: Optional[dict] = None):
        self.config = config or get_config()
        dq_cfg = self.config.get("pipeline", {}).get("data_quality", {})

        self.max_gap_hours = dq_cfg.get("max_gap_hours", 1)
        self.stale_threshold_min = dq_cfg.get("stale_threshold_minutes", 5)
        self.outlier_zscore = dq_cfg.get("outlier_zscore", 5.0)
        self.min_bars_per_day = dq_cfg.get("min_bars_per_day", 300)

        self._alerts: List[QualityAlert] = []
        self._source_timestamps: Dict[str, datetime] = {}
        self._metrics: Dict[str, float] = {}

    def validate_ohlcv(self, df: pd.DataFrame, source: str = "unknown") -> Dict[str, any]:
        """Run all quality checks on an OHLCV DataFrame."""
        self._alerts = []

        report = {
            "source": source, "total_rows": len(df),
            "date_range": {
                "start": str(df.index[0]) if len(df) > 0 else None,
                "end": str(df.index[-1]) if len(df) > 0 else None,
            },
            "checks": {}, "alerts": [], "overall_status": "PASS",
        }

        if df.empty:
            self._add_alert("critical", source, "completeness", "DataFrame is empty")
            report["overall_status"] = "FAIL"
            report["alerts"] = [a.__dict__ for a in self._alerts]
            return report

        # Track last update
        if len(df) > 0:
            last_ts = df.index[-1]
            if hasattr(last_ts, 'to_pydatetime'):
                self._source_timestamps[source] = last_ts.to_pydatetime()

        # Run all checks
        report["checks"]["completeness"] = self._check_completeness(df, source)
        report["checks"]["gaps"] = self._check_gaps(df, source)
        report["checks"]["outliers"] = self._check_outliers(df, source)
        report["checks"]["ohlc_sanity"] = self._check_ohlc_sanity(df, source)
        report["checks"]["nulls"] = self._check_nulls(df, source)

        report["alerts"] = [
            {"severity": a.severity, "source": a.source, "type": a.check_type, "message": a.message}
            for a in self._alerts
        ]
        critical_count = sum(1 for a in self._alerts if a.severity == "critical")
        warning_count = sum(1 for a in self._alerts if a.severity == "warning")

        if critical_count > 0:
            report["overall_status"] = "FAIL"
        elif warning_count > 0:
            report["overall_status"] = "WARNING"

        # Update Prometheus-style metrics
        self._metrics[f"dq_{source}_rows"] = len(df)
        self._metrics[f"dq_{source}_alerts"] = len(self._alerts)
        self._metrics[f"dq_{source}_status"] = 0 if report["overall_status"] == "PASS" else 1

        logger.info(
            f"Data quality [{source}]: {report['overall_status']} | "
            f"{len(df)} rows | {critical_count} critical, {warning_count} warnings"
        )
        return report

    def _check_completeness(self, df, source):
        required_cols = {"open", "high", "low", "close"}
        missing = required_cols - set(df.columns)
        if missing:
            self._add_alert("critical", source, "completeness", f"Missing columns: {missing}")
        result = {
            "required_columns_present": len(missing) == 0,
            "missing_columns": list(missing),
            "has_volume": "volume" in df.columns,
            "total_rows": len(df),
        }
        if len(df) < 100:
            self._add_alert("warning", source, "completeness", f"Only {len(df)} rows")
        return result

    def _check_gaps(self, df, source):
        if len(df) < 2:
            return {"gaps_found": 0, "max_gap": None}
        time_diffs = df.index.to_series().diff().dropna()
        median_diff = time_diffs.median()
        median_seconds = median_diff.total_seconds() if hasattr(median_diff, 'total_seconds') else float(median_diff)

        gap_threshold = pd.Timedelta(hours=self.max_gap_hours)
        gaps = time_diffs[time_diffs > gap_threshold]

        trading_gaps = []
        for gap_idx, gap_val in gaps.items():
            if hasattr(gap_idx, 'weekday'):
                prev_loc = df.index.get_loc(gap_idx)
                if prev_loc > 0:
                    prev_idx = df.index[prev_loc - 1]
                    if hasattr(prev_idx, 'weekday') and prev_idx.weekday() == 4:
                        continue
            trading_gaps.append({"timestamp": str(gap_idx), "gap_hours": gap_val.total_seconds() / 3600})

        if trading_gaps:
            self._add_alert("warning", source, "gap",
                            f"{len(trading_gaps)} gap(s) > {self.max_gap_hours}h in trading hours")

        return {"gaps_found": len(trading_gaps), "trading_gaps": trading_gaps[:10], "median_interval_seconds": median_seconds}

    def _check_outliers(self, df, source):
        if "close" not in df.columns or len(df) < 20:
            return {"outliers_found": 0}
        returns = df["close"].pct_change().dropna()
        if len(returns) == 0:
            return {"outliers_found": 0}
        mean, std = returns.mean(), returns.std()
        if std == 0 or np.isnan(std):
            return {"outliers_found": 0, "note": "Zero variance"}
        z_scores = (returns - mean) / std
        outliers = z_scores[z_scores.abs() > self.outlier_zscore]
        if len(outliers) > 0:
            self._add_alert("warning", source, "outlier", f"{len(outliers)} outlier(s) |Z| > {self.outlier_zscore}")
        return {
            "outliers_found": len(outliers), "threshold_zscore": self.outlier_zscore,
            "return_stats": {
                "mean": float(mean), "std": float(std),
                "min": float(returns.min()), "max": float(returns.max()),
                "skew": float(returns.skew()), "kurtosis": float(returns.kurtosis()),
            },
            "outlier_dates": [str(idx) for idx in outliers.index[:5]],
        }

    def _check_ohlc_sanity(self, df, source):
        issues = 0
        if "high" in df.columns and "low" in df.columns:
            inverted = df["high"] < df["low"]
            if inverted.any():
                count = int(inverted.sum())
                issues += count
                self._add_alert("critical", source, "ohlc_sanity", f"{count} bars have high < low")
        if "close" in df.columns and "high" in df.columns:
            issues += int((df["close"] > df["high"] * 1.001).sum())
        if "close" in df.columns and "low" in df.columns:
            issues += int((df["close"] < df["low"] * 0.999).sum())
        return {"sanity_issues": issues, "pass": issues == 0}

    def _check_nulls(self, df, source):
        null_counts = {}
        for col in ["open", "high", "low", "close"]:
            if col in df.columns:
                nc = int(df[col].isna().sum())
                null_counts[col] = nc
                if nc > 0:
                    pct = nc / len(df) * 100
                    sev = "critical" if pct > 5 else "warning" if pct > 1 else "info"
                    if sev != "info":
                        self._add_alert(sev, source, "nulls", f"{col}: {nc} nulls ({pct:.1f}%)")
        return {"null_counts": null_counts}

    # ──────────────────────────────────────────────────────
    # Phase 2: New checks
    # ──────────────────────────────────────────────────────

    def check_staleness(self, source: str, last_update: Optional[datetime] = None) -> Dict[str, any]:
        """Check if a data source is stale (hasn't updated recently)."""
        if last_update is None:
            last_update = self._source_timestamps.get(source)
        if last_update is None:
            return {"source": source, "status": "unknown", "last_update": None}

        now = datetime.utcnow()
        age_minutes = (now - last_update).total_seconds() / 60

        status = "fresh"
        if age_minutes > self.stale_threshold_min:
            status = "stale"
            self._add_alert("warning", source, "stale",
                            f"Data is {age_minutes:.0f} min old (threshold: {self.stale_threshold_min} min)")

        return {"source": source, "status": status, "age_minutes": round(age_minutes, 1),
                "last_update": str(last_update), "threshold_minutes": self.stale_threshold_min}

    def check_cross_source_alignment(
        self, sources: Dict[str, pd.DataFrame], max_drift_hours: float = 24
    ) -> Dict[str, any]:
        """Verify timestamp alignment across multiple data sources."""
        if len(sources) < 2:
            return {"status": "insufficient_sources", "sources": len(sources)}

        last_timestamps = {}
        for name, df in sources.items():
            if not df.empty:
                last_timestamps[name] = df.index[-1]

        if len(last_timestamps) < 2:
            return {"status": "insufficient_data"}

        max_ts = max(last_timestamps.values())
        min_ts = min(last_timestamps.values())
        drift = (max_ts - min_ts)
        drift_hours = drift.total_seconds() / 3600

        misaligned = []
        for name, ts in last_timestamps.items():
            lag = (max_ts - ts).total_seconds() / 3600
            if lag > max_drift_hours:
                misaligned.append({"source": name, "lag_hours": round(lag, 1)})

        if misaligned:
            self._add_alert("warning", "cross_source", "alignment",
                            f"{len(misaligned)} source(s) lagging > {max_drift_hours}h")

        return {
            "status": "aligned" if not misaligned else "misaligned",
            "max_drift_hours": round(drift_hours, 1),
            "sources": {k: str(v) for k, v in last_timestamps.items()},
            "misaligned": misaligned,
        }

    def check_correlation_breaks(
        self, gold_df: pd.DataFrame, macro_df: pd.DataFrame,
        expected_corr: float = -0.5, window: int = 60, threshold_std: float = 2.0,
        name: str = "dxy"
    ) -> Dict[str, any]:
        """Monitor if Gold/Macro correlation deviates from historical."""
        if "close" not in gold_df.columns or "close" not in macro_df.columns:
            return {"status": "missing_data"}

        gold_ret = gold_df["close"].pct_change().dropna()
        macro_close = macro_df["close"].reindex(gold_df.index, method="ffill")
        macro_ret = macro_close.pct_change().dropna()

        # Align
        common = gold_ret.index.intersection(macro_ret.index)
        if len(common) < window:
            return {"status": "insufficient_overlap"}

        gold_ret = gold_ret.loc[common]
        macro_ret = macro_ret.loc[common]

        rolling_corr = gold_ret.rolling(window).corr(macro_ret).dropna()
        if len(rolling_corr) < 10:
            return {"status": "insufficient_history"}

        current = float(rolling_corr.iloc[-1])
        hist_mean = float(rolling_corr.mean())
        hist_std = float(rolling_corr.std())

        deviation = abs(current - hist_mean) / hist_std if hist_std > 0 else 0

        if deviation > threshold_std:
            self._add_alert("warning", f"gold_{name}_corr", "correlation_break",
                            f"Gold/{name} corr = {current:.2f} ({deviation:.1f}σ from mean {hist_mean:.2f})")

        return {
            "pair": f"gold_{name}", "current_corr": round(current, 3),
            "historical_mean": round(hist_mean, 3), "historical_std": round(hist_std, 3),
            "deviation_sigma": round(deviation, 2),
            "status": "break" if deviation > threshold_std else "normal",
        }

    def _add_alert(self, severity, source, check_type, message):
        alert = QualityAlert(severity=severity, source=source, check_type=check_type, message=message)
        self._alerts.append(alert)
        if severity == "critical":
            logger.error(f"🚨 DQ [{source}]: {message}")
        elif severity == "warning":
            logger.warning(f"⚠️  DQ [{source}]: {message}")

    def get_alerts(self) -> List[QualityAlert]:
        return self._alerts.copy()

    def get_metrics(self) -> Dict[str, float]:
        """Get Prometheus-compatible metrics dict."""
        return self._metrics.copy()

    def generate_report(self, reports: Dict[str, dict]) -> dict:
        """Generate consolidated quality report across all sources."""
        total_sources = len(reports)
        passing = sum(1 for r in reports.values() if r.get("overall_status") == "PASS")
        warnings = sum(1 for r in reports.values() if r.get("overall_status") == "WARNING")
        failing = sum(1 for r in reports.values() if r.get("overall_status") == "FAIL")
        total_rows = sum(r.get("total_rows", 0) for r in reports.values())
        total_alerts = sum(len(r.get("alerts", [])) for r in reports.values())

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total_sources": total_sources, "passing": passing,
            "warnings": warnings, "failing": failing,
            "total_rows": total_rows, "total_alerts": total_alerts,
            "overall_health": "HEALTHY" if failing == 0 else "DEGRADED" if failing < total_sources else "CRITICAL",
            "per_source": reports,
        }

    def check_all_sources(self, data_dir=None) -> dict:
        """Validate all locally cached parquet data files.

        Scans the raw data directory for parquet files and runs
        quality checks on each one. Useful for post-pipeline health checks.

        Args:
            data_dir: Path to scan for parquet files. Defaults to data/raw.

        Returns:
            Consolidated quality report across all sources.
        """
        import pandas as pd
        from pathlib import Path

        if data_dir is None:
            from src.utils.config import PROJECT_ROOT
            data_dir = PROJECT_ROOT / "data" / "raw"
        else:
            data_dir = Path(data_dir)

        if not data_dir.exists():
            return {"status": "no_data_dir", "path": str(data_dir)}

        reports = {}
        for f in sorted(data_dir.glob("*.parquet")):
            try:
                df = pd.read_parquet(f, engine="pyarrow")
                source_name = f.stem
                report = self.validate_ohlcv(df, source_name)
                reports[source_name] = report
            except Exception as e:
                reports[f.stem] = {
                    "overall_status": "FAIL",
                    "error": str(e),
                    "total_rows": 0,
                }

        consolidated = self.generate_report(reports)
        logger.info(
            f"Data quality check: {consolidated['passing']}/{consolidated['total_sources']} PASS, "
            f"{consolidated['total_alerts']} alerts, health={consolidated['overall_health']}"
        )
        return consolidated

    def export_prometheus_metrics(self, exporter=None) -> None:
        """Push current metrics to a MetricsExporter instance.

        Args:
            exporter: MetricsExporter instance. If None, logs metrics instead.
        """
        if exporter is None:
            logger.debug(f"Data quality metrics (log-only): {self._metrics}")
            return

        try:
            # Push source-level metrics
            for key, value in self._metrics.items():
                if key.startswith("dq_") and key.endswith("_rows"):
                    source = key.replace("dq_", "").replace("_rows", "")
                    exporter.data_rows.labels(source=source).set(value)

            # Push staleness metrics
            for source, ts in self._source_timestamps.items():
                if hasattr(ts, 'timestamp'):
                    exporter.update_staleness(source, ts.timestamp())
        except Exception as e:
            logger.debug(f"Failed to export metrics: {e}")

