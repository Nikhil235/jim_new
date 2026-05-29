"""
Initialization & Gold Data Synchronization
===========================================
Called automatically on application startup to ensure gold data is up-to-date.

This runs before any trading logic and handles:
1. Creating necessary directories
2. Syncing gold data (incremental update)
3. Validating data integrity
4. Initializing metadata tracking
"""

import sys
import os
from pathlib import Path
from loguru import logger

# Setup logging
logger.remove()
logger.add(
    sys.stderr,
    format="<level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
)

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATABASE_FOLDER = PROJECT_ROOT / "Database"

def ensure_directories():
    """Create all required directories."""
    directories = [
        DATABASE_FOLDER,
        DATABASE_FOLDER / "gold_raw",
        DATABASE_FOLDER / "gold_processed",
        PROJECT_ROOT / "logs",
        PROJECT_ROOT / "artifacts",
    ]
    
    for d in directories:
        d.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"✓ All directories initialized")


def sync_gold_data(force_full_update: bool = False):
    """
    Synchronize gold data on startup.
    
    Args:
        force_full_update: If True, re-download all historical data
    
    Returns:
        bool: True if sync successful or skipped (non-critical)
    """
    logger.info("\n" + "=" * 70)
    logger.info("GOLD DATA SYNCHRONIZATION")
    logger.info("=" * 70)
    
    try:
        # Import here to avoid circular imports
        from scripts.gold_data_manager import GoldDataManager
        
        manager = GoldDataManager()
        logger.info(f"Current data status:")
        status = manager.get_status()
        for key, data in status.items():
            logger.info(f"  {key.upper():8} | {data.get('count', 0):7,} records | Last: {data.get('last_date', 'Never')}")
        
        # Run incremental update
        success = manager.run_incremental_update(force_daily=force_full_update)
        
        if success:
            logger.info("✓ Gold data synchronization complete")
        else:
            logger.warning("⚠ Gold data synchronization completed with warnings")
        
        logger.info("=" * 70 + "\n")
        return True
        
    except Exception as e:
        logger.error(f"✗ Gold data sync failed: {e}")
        logger.warning("Continuing without data sync (system may not have gold data)")
        return False


def initialize_system(force_gold_update: bool = False):
    """
    Initialize the system on startup.
    
    Args:
        force_gold_update: If True, force full gold data re-download
    
    Returns:
        dict: Initialization status report
    """
    logger.info("=" * 70)
    logger.info("SYSTEM INITIALIZATION")
    logger.info("=" * 70)
    
    status = {
        "directories_ok": False,
        "gold_data_ok": False,
        "overall": False,
    }
    
    try:
        # Step 1: Ensure directories
        logger.info("Step 1/2: Creating directories...")
        ensure_directories()
        status["directories_ok"] = True
        
        # Step 2: Sync gold data
        logger.info("Step 2/2: Synchronizing gold data...")
        status["gold_data_ok"] = sync_gold_data(force_full_update=force_gold_update)
        
        # Overall status
        status["overall"] = status["directories_ok"] and status["gold_data_ok"]
        
        logger.info("=" * 70)
        logger.info("INITIALIZATION COMPLETE")
        logger.info(f"Directories: {'✓' if status['directories_ok'] else '✗'}")
        logger.info(f"Gold Data:   {'✓' if status['gold_data_ok'] else '⚠ (Warning)'}")
        logger.info("=" * 70 + "\n")
        
        return status
        
    except Exception as e:
        logger.error(f"Initialization error: {e}")
        status["overall"] = False
        return status


if __name__ == "__main__":
    # When run directly, initialize with full setup
    force_update = "--force" in sys.argv
    initialize_system(force_gold_update=force_update)
