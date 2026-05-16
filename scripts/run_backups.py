import os
import time
import tarfile
from pathlib import Path
from datetime import datetime, timedelta
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

# Try importing project config
try:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
except ImportError:
    pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VOLUMES_DIR = PROJECT_ROOT / "docker" / "volumes"
BACKUPS_DIR = PROJECT_ROOT / "backups"
DATA_DIR = PROJECT_ROOT / "data" / "processed"

def compress_directory(source_dir: Path, output_file: Path) -> bool:
    """Compress a directory into a tar.gz archive."""
    if not source_dir.exists():
        logger.warning(f"Source directory does not exist: {source_dir}")
        return False
        
    logger.info(f"Compressing {source_dir.name} to {output_file.name}...")
    try:
        with tarfile.open(output_file, "w:gz") as tar:
            tar.add(source_dir, arcname=source_dir.name)
        
        size_mb = os.path.getsize(output_file) / (1024 * 1024)
        logger.info(f"✅ Backup successful: {output_file.name} ({size_mb:.2f} MB)")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to compress {source_dir}: {e}")
        if output_file.exists():
            os.remove(output_file)
        return False

def backup_databases():
    """Backup QuestDB and Redis Docker volumes."""
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 1. Backup QuestDB
    questdb_dir = VOLUMES_DIR / "questdb"
    questdb_backup = BACKUPS_DIR / f"questdb_backup_{date_str}.tar.gz"
    compress_directory(questdb_dir, questdb_backup)
    
    # 2. Backup Redis
    redis_dir = VOLUMES_DIR / "redis"
    redis_backup = BACKUPS_DIR / f"redis_backup_{date_str}.tar.gz"
    compress_directory(redis_dir, redis_backup)

def enforce_retention_policy():
    """Delete backups older than 30 days and tick data older than 1 year."""
    logger.info("Running Data Retention Cleanup...")
    
    # Backup retention: 30 days
    backup_retention_sec = 30 * 86400
    cutoff_backups = time.time() - backup_retention_sec
    
    deleted_backups = 0
    if BACKUPS_DIR.exists():
        for f in BACKUPS_DIR.glob("*.tar.gz"):
            if os.path.getmtime(f) < cutoff_backups:
                logger.info(f"Deleting expired backup: {f.name}")
                os.remove(f)
                deleted_backups += 1
                
    # Tick data retention: 1 year (365 days)
    data_retention_sec = 365 * 86400
    cutoff_data = time.time() - data_retention_sec
    
    deleted_data = 0
    if DATA_DIR.exists():
        for f in DATA_DIR.glob("*.parquet"):
            if os.path.getmtime(f) < cutoff_data:
                logger.info(f"Deleting 1-year old tick data: {f.name}")
                os.remove(f)
                deleted_data += 1
                
    logger.info(f"Retention Cleanup Complete. Deleted {deleted_backups} old backups, {deleted_data} old tick files.")

def run_daily_backup():
    """Execute the full daily backup and retention process."""
    logger.info("=" * 60)
    logger.info(f"🚀 STARTING DAILY BACKUP: {datetime.now().isoformat()}")
    logger.info("=" * 60)
    
    backup_databases()
    enforce_retention_policy()
    
    logger.info("✅ Daily Backup completed.")
    logger.info("=" * 60)

if __name__ == "__main__":
    import sys
    
    # Check if we should run right now
    if len(sys.argv) > 1 and sys.argv[1] == "--now":
        run_daily_backup()
        sys.exit(0)

    logger.info("Starting Backup Daemon...")
    logger.info("Backups scheduled to run daily at 02:00 AM.")
    
    try:
        while True:
            now = datetime.now()
            # Target is today at 02:00 AM
            target = now.replace(hour=2, minute=0, second=0, microsecond=0)
            
            # If it's already past 2 AM today, schedule for tomorrow at 2 AM
            if now >= target:
                target += timedelta(days=1)
                
            sleep_seconds = (target - now).total_seconds()
            
            hours = int(sleep_seconds // 3600)
            minutes = int((sleep_seconds % 3600) // 60)
            logger.info(f"Sleeping for {hours}h {minutes}m until next scheduled backup at {target.isoformat()}...")
            
            # Sleep until 2 AM
            time.sleep(sleep_seconds)
            
            # Run the backup!
            run_daily_backup()
            
            # Sleep a bit extra to ensure we don't double-trigger in the same minute
            time.sleep(60)
            
    except KeyboardInterrupt:
        logger.info("Backup Daemon stopped by user.")
