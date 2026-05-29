"""
Prediction Log Manager
======================
Manages session-wise prediction log storage to local filesystem.

Features:
- Session-wise log organization
- Automatic log creation every 5 minutes per session
- CSV format for easy Excel compatibility
- Session metadata tracking via separate metadata files
"""

import os
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from loguru import logger

# ============================================================================
# CONFIG
# ============================================================================

PREDICTION_LOGS_DIR = Path(r"E:\PRO\JIMxNik\PredictionLogs")
PREDICTION_LOGS_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# SESSION MANAGER
# ============================================================================

class PredictionLogSession:
    """Manages a single session's prediction logs in CSV format."""
    
    def __init__(self, session_id: str = None):
        """
        Initialize a session.
        
        Args:
            session_id: Format DDMMYYYY_HHMMSS. If None, creates new session with current time.
        """
        if session_id is None:
            now = datetime.now()
            session_id = now.strftime("%d%m%Y_%H%M%S")
        
        self.session_id = session_id
        self.filename = f"PredictionLogs_{session_id}.csv"
        self.filepath = PREDICTION_LOGS_DIR / self.filename
        self.metadata_filepath = PREDICTION_LOGS_DIR / f"PredictionLogs_{session_id}_metadata.json"
        self.created_at = datetime.now().isoformat()
        
    def save_logs(self, logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Save or append logs to session file in CSV format.
        
        Args:
            logs: List of log entries to save
            
        Returns:
            Status dict with save details
        """
        try:
            if not logs:
                return {
                    "status": "ok",
                    "records_saved": 0,
                    "message": "No logs to save"
                }
            
            # Get headers from first log
            headers = list(logs[0].keys())
            
            # Check if session file exists
            if self.filepath.exists():
                # Read existing logs to deduplicate
                with open(self.filepath, "r", newline="", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    existing_logs = list(reader) if reader else []
                
                existing_timestamps = {log.get("timestamp") for log in existing_logs}
                new_logs = [log for log in logs if log.get("timestamp") not in existing_timestamps]
                records_saved = len(new_logs)
                
                # Append new logs only
                if new_logs:
                    with open(self.filepath, "a", newline="", encoding="utf-8") as f:
                        writer = csv.DictWriter(f, fieldnames=headers)
                        writer.writerows(new_logs)
                
                total_records = len(existing_logs) + len(new_logs)
            else:
                # Create new session file with headers
                with open(self.filepath, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=headers)
                    writer.writeheader()
                    writer.writerows(logs)
                
                records_saved = len(logs)
                total_records = len(logs)
            
            # Update metadata
            metadata = {
                "session_id": self.session_id,
                "created_at": self.created_at,
                "last_updated": datetime.now().isoformat(),
                "total_records": total_records,
                "file_path": str(self.filepath),
                "records_added_this_save": records_saved
            }
            
            with open(self.metadata_filepath, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved {records_saved} prediction logs to session {self.session_id}")
            
            return {
                "status": "success",
                "session_id": self.session_id,
                "file_path": str(self.filepath),
                "records_saved": records_saved,
                "total_records_in_session": total_records
            }
            
        except Exception as e:
            logger.error(f"Failed to save prediction logs for session {self.session_id}: {e}", exc_info=True)
            return {
                "status": "error",
                "session_id": self.session_id,
                "error": str(e)
            }
    
    def load_logs(self) -> List[Dict[str, Any]]:
        """
        Load all logs from session file.
        
        Returns:
            List of log dictionaries
        """
        try:
            if not self.filepath.exists():
                return []
            
            with open(self.filepath, "r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                return list(reader) if reader else []
        except Exception as e:
            logger.error(f"Failed to load logs from session {self.session_id}: {e}")
            return []
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get session metadata."""
        try:
            if self.metadata_filepath.exists():
                with open(self.metadata_filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            return {"session_id": self.session_id, "status": "no_metadata"}
        except Exception as e:
            logger.error(f"Failed to read metadata for session {self.session_id}: {e}")
            return {}
    
    def export_to_excel_friendly(self, output_path: Optional[Path] = None) -> Dict[str, Any]:
        """
        Export session logs to Excel-friendly CSV (already in CSV format).
        
        Args:
            output_path: Alternative output path
            
        Returns:
            Status dict with export details
        """
        try:
            if not self.filepath.exists():
                return {
                    "status": "error",
                    "message": "Session file not found"
                }
            
            if output_path is None:
                output_path = PREDICTION_LOGS_DIR / f"PredictionLogs_{self.session_id}_export.csv"
            else:
                output_path = Path(output_path)
            
            # Copy CSV file (already in correct format)
            import shutil
            shutil.copy(self.filepath, output_path)
            
            logs = self.load_logs()
            logger.info(f"Exported {len(logs)} logs to CSV: {output_path}")
            
            return {
                "status": "success",
                "file_path": str(output_path),
                "records_exported": len(logs)
            }
            
        except Exception as e:
            logger.error(f"Failed to export session {self.session_id}: {e}")
            return {
                "status": "error",
                "error": str(e)
            }


# ============================================================================
# SESSION MANAGER
# ============================================================================

class PredictionLogManager:
    """Manages multiple sessions and provides utilities."""
    
    @staticmethod
    def list_sessions() -> List[Dict[str, Any]]:
        """List all saved prediction log sessions."""
        try:
            sessions = []
            for file in PREDICTION_LOGS_DIR.glob("PredictionLogs_*.csv"):
                try:
                    # Skip export files
                    if "_export" in file.name:
                        continue
                    
                    session_id = file.stem.replace("PredictionLogs_", "")
                    metadata_file = PREDICTION_LOGS_DIR / f"PredictionLogs_{session_id}_metadata.json"
                    
                    # Get metadata if available
                    if metadata_file.exists():
                        with open(metadata_file, "r", encoding="utf-8") as f:
                            metadata = json.load(f)
                    else:
                        # Count records manually if no metadata
                        with open(file, "r", newline="", encoding="utf-8") as f:
                            total_records = sum(1 for _ in f) - 1  # Subtract header
                        metadata = {
                            "session_id": session_id,
                            "created_at": datetime.fromtimestamp(file.stat().st_ctime).isoformat(),
                            "total_records": total_records
                        }
                    
                    sessions.append({
                        "session_id": metadata.get("session_id", session_id),
                        "created_at": metadata.get("created_at"),
                        "last_updated": metadata.get("last_updated"),
                        "total_records": metadata.get("total_records", 0),
                        "file_path": str(file)
                    })
                except Exception as e:
                    logger.error(f"Failed to read session file {file}: {e}")
            
            return sorted(sessions, key=lambda x: x.get("created_at"), reverse=True)
        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            return []
    
    @staticmethod
    def get_latest_session() -> Optional[PredictionLogSession]:
        """Get the most recent session."""
        sessions = PredictionLogManager.list_sessions()
        if not sessions:
            return None
        
        latest_session_id = sessions[0]["session_id"]
        return PredictionLogSession(latest_session_id)
    
    @staticmethod
    def get_session_by_id(session_id: str) -> PredictionLogSession:
        """Get a session by its ID."""
        return PredictionLogSession(session_id)
    
    @staticmethod
    def cleanup_old_sessions(days_to_keep: int = 7) -> Dict[str, Any]:
        """
        Delete sessions older than specified days.
        
        Args:
            days_to_keep: Number of days to keep (default 7)
            
        Returns:
            Status dict with cleanup details
        """
        try:
            from datetime import timedelta
            cutoff_time = datetime.now() - timedelta(days=days_to_keep)
            deleted_count = 0
            
            # Delete CSV files
            for file in PREDICTION_LOGS_DIR.glob("PredictionLogs_*.csv"):
                if "_export" in file.name or "_metadata" in file.name:
                    continue
                
                file_time = datetime.fromtimestamp(file.stat().st_mtime)
                if file_time < cutoff_time:
                    file.unlink()
                    deleted_count += 1
            
            # Delete associated metadata files
            for file in PREDICTION_LOGS_DIR.glob("PredictionLogs_*_metadata.json"):
                file_time = datetime.fromtimestamp(file.stat().st_mtime)
                if file_time < cutoff_time:
                    file.unlink()
            
            logger.info(f"Deleted {deleted_count} old prediction log sessions")
            
            return {
                "status": "success",
                "deleted_count": deleted_count,
                "days_to_keep": days_to_keep
            }
        except Exception as e:
            logger.error(f"Failed to cleanup old sessions: {e}")
            return {
                "status": "error",
                "error": str(e)
            }


# ============================================================================
# QUICK FUNCTIONS
# ============================================================================

def save_prediction_logs(logs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Quick function to save logs to the latest session."""
    try:
        # Get or create latest session
        latest_session = PredictionLogManager.get_latest_session()
        
        # Check if session is older than 1 hour, create new one if needed
        if latest_session:
            try:
                metadata = latest_session.get_metadata()
                if metadata and "last_updated" in metadata:
                    last_updated = datetime.fromisoformat(metadata["last_updated"])
                    time_since_update = (datetime.now() - last_updated).total_seconds()
                    
                    # If it's been more than 1 hour, create a new session
                    if time_since_update > 3600:
                        latest_session = PredictionLogSession()
            except:
                pass
        else:
            latest_session = PredictionLogSession()
        
        # Save logs
        return latest_session.save_logs(logs)
    except Exception as e:
        logger.error(f"Failed to save prediction logs: {e}")
        return {
            "status": "error",
            "error": str(e)
        }
