#!/usr/bin/env python3
"""
Daily Data Pipeline Runner
===========================
Schedules and runs the Phase 2 data acquisition pipeline daily.

This is the critical missing piece that wires all the fetchers together.

Usage:
  # Run pipeline once
  python run_daily_pipeline.py --once
  
  # Run pipeline once per day at 00:00 UTC
  python run_daily_pipeline.py --schedule
  
  # Run specific mode (default: full)
  python run_daily_pipeline.py --mode gold-only --once
"""

import sys
import argparse
import schedule
import time
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingestion.pipeline_orchestrator import PipelineOrchestrator
from src.utils.logger import logger


def run_pipeline(mode: str = "full"):
    """Execute the data acquisition pipeline."""
    logger.info(f"{'='*60}")
    logger.info(f"PIPELINE START: {datetime.utcnow().isoformat()} (Mode: {mode})")
    logger.info(f"{'='*60}")
    
    try:
        orchestrator = PipelineOrchestrator()
        report = orchestrator.run(mode=mode)
        
        logger.info(f"{'='*60}")
        logger.info(f"PIPELINE COMPLETE: {datetime.utcnow().isoformat()}")
        logger.info(f"Overall Status: {report.status}")
        logger.info(f"Total Duration: {report.duration_sec:.2f}s")
        logger.info(f"Steps Completed: {report.total_steps - len([s for s in report.steps if s.status == 'failed'])}/{report.total_steps}")
        logger.info(f"{'='*60}")
        
        # Return exit code based on status
        if report.status == "success":
            return 0
        elif report.status == "partial":
            return 1  # Partial success - recoverable
        else:
            return 2  # Full failure
            
    except Exception as e:
        logger.error(f"PIPELINE FAILED: {str(e)}", exc_info=True)
        return 2


def schedule_daily_run(mode: str = "full", hour: int = 0, minute: int = 0):
    """Schedule daily pipeline runs at specified time (UTC)."""
    logger.info(f"Scheduler initialized: Daily runs at {hour:02d}:{minute:02d} UTC (mode: {mode})")
    
    # Schedule the job
    schedule.every().day.at(f"{hour:02d}:{minute:02d}").do(run_pipeline, mode=mode)
    
    # Keep scheduler running
    logger.info("Scheduler is now running. Press Ctrl+C to stop.")
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")
        return 0


def main():
    parser = argparse.ArgumentParser(
        description="Daily Data Pipeline Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run once now
  python run_daily_pipeline.py --once
  
  # Run once, gold data only
  python run_daily_pipeline.py --once --mode gold-only
  
  # Schedule daily at 00:00 UTC (full pipeline)
  python run_daily_pipeline.py --schedule
  
  # Schedule daily at 02:00 UTC (macro + features)
  python run_daily_pipeline.py --schedule --hour 2 --mode macro-only
        """
    )
    
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run pipeline once and exit"
    )
    
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="Run pipeline on a schedule (default: daily at 00:00 UTC)"
    )
    
    parser.add_argument(
        "--mode",
        default="full",
        choices=["full", "gold-only", "macro-only", "features-only", "incremental"],
        help="Pipeline execution mode (default: full)"
    )
    
    parser.add_argument(
        "--hour",
        type=int,
        default=0,
        help="Hour for scheduled run (0-23, UTC) (default: 0)"
    )
    
    parser.add_argument(
        "--minute",
        type=int,
        default=0,
        help="Minute for scheduled run (0-59) (default: 0)"
    )
    
    args = parser.parse_args()
    
    # Validation
    if not args.once and not args.schedule:
        parser.error("Must specify either --once or --schedule")
    
    if args.hour < 0 or args.hour > 23:
        parser.error("Hour must be 0-23")
    
    if args.minute < 0 or args.minute > 59:
        parser.error("Minute must be 0-59")
    
    # Execute
    if args.once:
        exit_code = run_pipeline(mode=args.mode)
        sys.exit(exit_code)
    else:
        exit_code = schedule_daily_run(mode=args.mode, hour=args.hour, minute=args.minute)
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
