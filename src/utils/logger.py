"""
Logging Setup
=============
Structured logging with Loguru.
Every event in the system gets logged — trades, signals, errors, risk events.
"""

import sys
from pathlib import Path
from loguru import logger

from src.utils.config import PROJECT_ROOT


def setup_logger(
    level: str = "INFO",
    log_file: str = "logs/medallion.log",
    rotation: str = "100 MB",
    retention: str = "30 days",
) -> None:
    """
    Configure the global logger.

    Args:
        level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_file: Path to log file relative to project root.
        rotation: When to rotate (e.g., "100 MB", "1 day").
        retention: How long to keep old logs.
    """
    # Remove default handler
    logger.remove()

    # Console handler (colorized, human-readable)
    logger.add(
        sys.stderr,
        level=level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{module}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        colorize=True,
    )

    # File handler (structured, for post-mortem analysis)
    log_path = PROJECT_ROOT / log_file
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger.add(
        str(log_path),
        level="DEBUG",  # File always captures everything
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {module}:{function}:{line} | {message}",
        rotation=rotation,
        retention=retention,
        compression="gz",
        enqueue=True,  # Thread-safe
    )

    # Trade-specific log (separate file for trade audit trail)
    trade_log_path = PROJECT_ROOT / "logs" / "trades.log"
    logger.add(
        str(trade_log_path),
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {message}",
        filter=lambda record: "trade" in record["extra"],
        rotation="1 day",
        retention="1 year",
    )

    logger.info(f"Logger initialized | level={level} | file={log_path}")


def get_trade_logger():
    """Get a logger specifically for trade events."""
    return logger.bind(trade=True)


def get_risk_logger():
    """Get a logger specifically for risk events."""
    return logger.bind(risk=True)
