"""
Prometheus Metrics Exporter
============================
Exposes pipeline health metrics for Prometheus scraping.

Metrics:
  - medallion_data_rows_total{source}         — Row count per data source
  - medallion_data_staleness_seconds{source}   — Seconds since last update
  - medallion_data_quality_alerts{source,severity} — Alert counts
  - medallion_pipeline_duration_seconds{mode}  — Pipeline run duration
  - medallion_pipeline_status{mode}            — 0=success, 1=partial, 2=failed
  - medallion_feature_count                    — Total engineered features
  - medallion_feature_drift{symbol}            — Feature drift detected (0/1)

Usage:
    # Start as a background thread (non-blocking)
    exporter = MetricsExporter(port=8000)
    exporter.start()

    # Update after pipeline run
    exporter.update_from_pipeline_report(report)
"""

import time
import threading
from typing import Optional, Dict, Any
from loguru import logger

try:
    from prometheus_client import (
        Gauge, Counter, CollectorRegistry, start_http_server,
        generate_latest, CONTENT_TYPE_LATEST,
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.debug("prometheus_client not installed — metrics exporter disabled")


class MetricsExporter:
    """Exposes Mini-Medallion pipeline metrics for Prometheus.

    Starts an HTTP server on the configured port that Prometheus
    can scrape. Metrics are updated after each pipeline run.
    """

    def __init__(self, port: int = 8000, config: Optional[dict] = None):
        self.port = port
        self._started = False
        self._registry = None

        if not PROMETHEUS_AVAILABLE:
            logger.warning("Prometheus client not available — metrics will be logged only")
            return

        self._registry = CollectorRegistry()

        # --- Data source metrics ---
        self.data_rows = Gauge(
            "medallion_data_rows_total",
            "Total rows per data source",
            ["source"],
            registry=self._registry,
        )

        self.data_staleness = Gauge(
            "medallion_data_staleness_seconds",
            "Seconds since last data update per source",
            ["source"],
            registry=self._registry,
        )

        self.data_quality_alerts = Gauge(
            "medallion_data_quality_alerts",
            "Number of data quality alerts per source and severity",
            ["source", "severity"],
            registry=self._registry,
        )

        # --- Pipeline metrics ---
        self.pipeline_duration = Gauge(
            "medallion_pipeline_duration_seconds",
            "Duration of last pipeline run in seconds",
            ["mode"],
            registry=self._registry,
        )

        self.pipeline_status = Gauge(
            "medallion_pipeline_status",
            "Status of last pipeline run (0=success, 1=partial, 2=failed)",
            ["mode"],
            registry=self._registry,
        )

        self.pipeline_step_duration = Gauge(
            "medallion_pipeline_step_duration_seconds",
            "Duration of each pipeline step",
            ["step"],
            registry=self._registry,
        )

        self.pipeline_step_rows = Gauge(
            "medallion_pipeline_step_rows",
            "Rows processed by each pipeline step",
            ["step"],
            registry=self._registry,
        )

        # --- Feature metrics ---
        self.feature_count = Gauge(
            "medallion_feature_count",
            "Total number of engineered features",
            registry=self._registry,
        )

        self.feature_drift = Gauge(
            "medallion_feature_drift_detected",
            "Whether feature drift is detected (0=stable, 1=drifted)",
            ["symbol"],
            registry=self._registry,
        )

        # --- Heartbeat ---
        self.last_update_time = Gauge(
            "medallion_metrics_last_update_timestamp",
            "Unix timestamp of last metrics update",
            registry=self._registry,
        )

    def start(self):
        """Start the Prometheus HTTP metrics server in a background thread."""
        if not PROMETHEUS_AVAILABLE or self._registry is None:
            logger.info("Prometheus exporter not started (client unavailable)")
            return

        if self._started:
            logger.debug("Metrics exporter already running")
            return

        try:
            start_http_server(self.port, registry=self._registry)
            self._started = True
            logger.info(f"📊 Prometheus metrics exporter started on port {self.port}")
        except OSError as e:
            logger.warning(f"Could not start metrics server on port {self.port}: {e}")

    def update_from_pipeline_report(self, report) -> None:
        """Update all metrics from a PipelineReport dataclass.

        Args:
            report: PipelineReport from PipelineOrchestrator.run()
        """
        if not PROMETHEUS_AVAILABLE or self._registry is None:
            self._log_report_summary(report)
            return

        # Pipeline-level metrics
        status_map = {"SUCCESS": 0, "PARTIAL": 1, "FAILED": 2}
        self.pipeline_status.labels(mode=report.mode).set(
            status_map.get(report.overall_status, 2)
        )
        self.pipeline_duration.labels(mode=report.mode).set(report.duration_sec)
        self.feature_count.set(report.feature_count)

        # Per-step metrics
        for step in report.steps:
            self.pipeline_step_duration.labels(step=step.name).set(step.duration_sec)
            self.pipeline_step_rows.labels(step=step.name).set(step.rows)

        self.last_update_time.set(time.time())
        logger.info(f"Prometheus metrics updated: {report.overall_status} ({report.duration_sec}s)")

    def update_data_quality(self, quality_report: Dict[str, Any]) -> None:
        """Update data quality metrics from a consolidated quality report.

        Args:
            quality_report: Output of DataQualityMonitor.generate_report()
        """
        if not PROMETHEUS_AVAILABLE or self._registry is None:
            return

        for source, report in quality_report.get("per_source", {}).items():
            self.data_rows.labels(source=source).set(report.get("total_rows", 0))

            # Count alerts by severity
            alerts = report.get("alerts", [])
            for severity in ["critical", "warning", "info"]:
                count = sum(1 for a in alerts if a.get("severity") == severity)
                self.data_quality_alerts.labels(source=source, severity=severity).set(count)

        self.last_update_time.set(time.time())

    def update_staleness(self, source: str, last_update_ts: float) -> None:
        """Update staleness for a data source.

        Args:
            source: Name of the data source (e.g., 'gold', 'dxy').
            last_update_ts: Unix timestamp of the last data point.
        """
        if not PROMETHEUS_AVAILABLE or self._registry is None:
            return
        staleness = time.time() - last_update_ts
        self.data_staleness.labels(source=source).set(staleness)

    def update_feature_drift(self, symbol: str, drifted: bool) -> None:
        """Update feature drift status for a symbol."""
        if not PROMETHEUS_AVAILABLE or self._registry is None:
            return
        self.feature_drift.labels(symbol=symbol).set(1.0 if drifted else 0.0)

    def _log_report_summary(self, report) -> None:
        """Fallback: log metrics when Prometheus is unavailable."""
        logger.info(
            f"Pipeline metrics (log-only): status={report.overall_status} "
            f"duration={report.duration_sec}s rows={report.total_rows_ingested} "
            f"features={report.feature_count}"
        )

    def is_running(self) -> bool:
        """Check if the metrics server is running."""
        return self._started
