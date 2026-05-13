"""
Daily Ingestion Scheduler
==========================
Automated pipeline runner that executes the data pipeline on a schedule.

Jobs:
  06:00 UTC — Gold + Yahoo macro data fetch (before London open)
  14:00 UTC — FRED + alternative data update (after US market open)
  14:30 UTC — Feature regeneration (after all data is fresh)

Usage:
    python scripts/daily_scheduler.py                  # Run as daemon
    python scripts/daily_scheduler.py --once           # Run once and exit
    python scripts/daily_scheduler.py --once --mode gold-only  # Single mode
    python scripts/daily_scheduler.py --status         # Show last run status
"""

import sys
import os
import json
import signal
import time
from datetime import datetime
from pathlib import Path

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import click
import schedule
from loguru import logger

from src.utils.config import load_config, PROJECT_ROOT
from src.utils.logger import setup_logger


# Health file for tracking pipeline status
HEALTH_FILE = PROJECT_ROOT / "data" / "pipeline_health.json"


class PipelineScheduler:
    """Schedules and runs the data pipeline on a configurable cadence.

    Uses the `schedule` library for lightweight, reliable job scheduling.
    Each job delegates to PipelineOrchestrator with the appropriate mode.
    """

    def __init__(self, config: dict):
        self.config = config
        self._running = True
        self._metrics_exporter = None
        self._last_report = None

        # Read schedule config
        sched_cfg = config.get("pipeline", {}).get("schedule", {})
        self.daily_time = sched_cfg.get("daily_update_time", "06:00")
        self.macro_time = sched_cfg.get("macro_update_time", "14:00")

        # Feature regen 30 min after macro update
        hour, minute = self.macro_time.split(":")
        feat_minute = int(minute) + 30
        feat_hour = int(hour) + (feat_minute // 60)
        feat_minute = feat_minute % 60
        self.feature_time = f"{feat_hour:02d}:{feat_minute:02d}"

        logger.info(f"Scheduler configured:")
        logger.info(f"  Gold + Yahoo macro: {self.daily_time} UTC")
        logger.info(f"  FRED + alt data:    {self.macro_time} UTC")
        logger.info(f"  Feature regen:      {self.feature_time} UTC")

    def _init_metrics(self):
        """Initialize Prometheus metrics exporter if available."""
        try:
            from src.ingestion.metrics_exporter import MetricsExporter
            self._metrics_exporter = MetricsExporter(port=8000, config=self.config)
            self._metrics_exporter.start()
        except Exception as e:
            logger.debug(f"Metrics exporter not started: {e}")

    def _run_pipeline(self, mode: str) -> None:
        """Execute a pipeline run and save the report."""
        from src.ingestion.pipeline_orchestrator import PipelineOrchestrator

        logger.info(f"\n{'='*60}")
        logger.info(f"  SCHEDULED RUN — Mode: {mode.upper()}")
        logger.info(f"  Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        logger.info(f"{'='*60}")

        try:
            orchestrator = PipelineOrchestrator(self.config)
            report = orchestrator.run(mode=mode)
            self._last_report = report

            # Save health report
            self._save_health(report)

            # Update Prometheus metrics
            if self._metrics_exporter:
                self._metrics_exporter.update_from_pipeline_report(report)

            logger.info(f"Pipeline {mode} completed: {report.overall_status}")

        except Exception as e:
            logger.error(f"Pipeline {mode} CRASHED: {e}")
            self._save_health_error(mode, str(e))

    def _save_health(self, report) -> None:
        """Persist pipeline health to JSON for status queries."""
        try:
            HEALTH_FILE.parent.mkdir(parents=True, exist_ok=True)

            # Load existing health data
            health = {}
            if HEALTH_FILE.exists():
                try:
                    health = json.loads(HEALTH_FILE.read_text())
                except (json.JSONDecodeError, OSError):
                    health = {}

            # Update with latest run
            health[report.mode] = {
                "status": report.overall_status,
                "start_time": report.start_time,
                "end_time": report.end_time,
                "duration_sec": report.duration_sec,
                "total_rows": report.total_rows_ingested,
                "feature_count": report.feature_count,
                "steps": [
                    {
                        "name": s.name,
                        "status": s.status,
                        "rows": s.rows,
                        "duration": s.duration_sec,
                        "error": s.error,
                    }
                    for s in report.steps
                ],
            }
            health["last_updated"] = datetime.utcnow().isoformat()

            HEALTH_FILE.write_text(json.dumps(health, indent=2))
            logger.debug(f"Health saved to {HEALTH_FILE}")
        except Exception as e:
            logger.warning(f"Failed to save health file: {e}")

    def _save_health_error(self, mode: str, error: str) -> None:
        """Save error state to health file."""
        try:
            HEALTH_FILE.parent.mkdir(parents=True, exist_ok=True)
            health = {}
            if HEALTH_FILE.exists():
                try:
                    health = json.loads(HEALTH_FILE.read_text())
                except (json.JSONDecodeError, OSError):
                    health = {}

            health[mode] = {
                "status": "CRASHED",
                "error": error,
                "timestamp": datetime.utcnow().isoformat(),
            }
            health["last_updated"] = datetime.utcnow().isoformat()
            HEALTH_FILE.write_text(json.dumps(health, indent=2))
        except Exception:
            pass

    def run_once(self, mode: str = "full") -> None:
        """Execute a single pipeline run and exit."""
        self._init_metrics()
        self._run_pipeline(mode)

    def run_daemon(self) -> None:
        """Start the scheduler daemon. Runs until SIGINT/SIGTERM."""
        self._init_metrics()

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # Schedule jobs
        schedule.every().day.at(self.daily_time).do(
            self._run_pipeline, mode="full"
        )
        schedule.every().day.at(self.macro_time).do(
            self._run_pipeline, mode="macro-only"
        )
        schedule.every().day.at(self.feature_time).do(
            self._run_pipeline, mode="features-only"
        )

        logger.info("=" * 60)
        logger.info("  PIPELINE SCHEDULER STARTED")
        logger.info(f"  Pending jobs: {len(schedule.get_jobs())}")
        logger.info("  Press Ctrl+C to stop")
        logger.info("=" * 60)

        # Heartbeat loop
        heartbeat_interval = 60  # seconds
        last_heartbeat = 0

        while self._running:
            schedule.run_pending()

            now = time.time()
            if now - last_heartbeat >= heartbeat_interval:
                next_run = schedule.idle_seconds()
                if next_run is not None and next_run > 0:
                    hours = int(next_run // 3600)
                    minutes = int((next_run % 3600) // 60)
                    logger.debug(f"💓 Scheduler alive | Next job in {hours}h {minutes}m")
                last_heartbeat = now

            time.sleep(1)

        logger.info("Scheduler stopped gracefully")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self._running = False


def _show_status():
    """Display the last pipeline run status from the health file."""
    if not HEALTH_FILE.exists():
        logger.info("No pipeline health data found. Run the pipeline first.")
        return

    try:
        health = json.loads(HEALTH_FILE.read_text())
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"Failed to read health file: {e}")
        return

    logger.info("\n" + "=" * 60)
    logger.info("  PIPELINE HEALTH STATUS")
    logger.info("=" * 60)
    logger.info(f"  Last updated: {health.get('last_updated', 'unknown')}")
    logger.info("")

    for mode in ["full", "gold-only", "macro-only", "features-only", "incremental"]:
        if mode not in health:
            continue
        run = health[mode]
        status = run.get("status", "unknown")
        icon = "✅" if status == "SUCCESS" else "⚠️" if status == "PARTIAL" else "❌"
        logger.info(f"  {icon} {mode:16s} | {status:8s} | {run.get('duration_sec', '?')}s | {run.get('total_rows', '?')} rows")

        if run.get("steps"):
            for step in run["steps"]:
                s_icon = "✅" if step["status"] == "success" else "❌"
                logger.info(f"     {s_icon} {step['name']:25s} {step['rows']:>8,} rows  ({step['duration']:.1f}s)")
                if step.get("error"):
                    logger.info(f"        Error: {step['error'][:80]}")

    logger.info("=" * 60)


@click.command()
@click.option("--once", is_flag=True, help="Run pipeline once and exit (no daemon)")
@click.option("--mode", default="full",
              type=click.Choice(["full", "gold-only", "macro-only", "features-only", "incremental"]),
              help="Pipeline mode (used with --once)")
@click.option("--status", is_flag=True, help="Show last pipeline run status")
@click.option("--config", default=None, help="Path to config YAML")
def main(once: bool, mode: str, status: bool, config: str):
    """Mini-Medallion Pipeline Scheduler."""

    cfg = load_config(config)
    log_cfg = cfg.get("logging", {})
    setup_logger(
        level=log_cfg.get("level", "INFO"),
        log_file=log_cfg.get("file", "logs/scheduler.log"),
    )

    if status:
        _show_status()
        return

    scheduler = PipelineScheduler(cfg)

    if once:
        logger.info(f"One-shot execution: mode={mode}")
        scheduler.run_once(mode=mode)
    else:
        scheduler.run_daemon()


if __name__ == "__main__":
    main()
