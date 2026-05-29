# Prediction Logs Auto-Save System

## Overview
The Prediction Logs Auto-Save system automatically saves your trading prediction logs to the local file system in a session-wise organized format. This provides persistent, local backup of all prediction cycles for analysis, auditing, and reporting.

## Features

✅ **Session-Wise Organization**
- Each application session gets its own log file
- Logs are organized by date and time: `PredictionLogs_DDMMYYYY_HHMMSS.json`
- Multiple sessions can coexist for long-running systems

✅ **Automatic 5-Minute Saves**
- Logs are automatically saved every 5 minutes
- New logs are appended to the session file (duplicates prevented)
- Session metadata is updated on each save

✅ **Manual Save Control**
- "Save to Disk" button in the UI for on-demand saves
- Visual feedback showing save status (saving, success, error)
- Session ID and last save time displayed in the interface

✅ **JSON Format Storage**
- Structured JSON format for easy parsing and analysis
- Includes session metadata (created_at, last_updated, total_records)
- All prediction log fields preserved

✅ **Automatic Initialization**
- Saves immediately when the page loads (1 second delay)
- Starts 5-minute auto-save cycle
- Creates directory automatically if it doesn't exist

## Storage Location

```
E:\PRO\JIMxNik\PredictionLogs\
├── PredictionLogs_27052026_120000.json  (Session 1 - May 27, 12:00:00)
├── PredictionLogs_27052026_150530.json  (Session 2 - May 27, 15:05:30)
├── PredictionLogs_28052026_080000.json  (Session 3 - May 28, 08:00:00)
└── ...
```

## File Format

Each session file contains prediction logs in CSV format:

```csv
timestamp,price,regime,wavelet_signal,wavelet_conf,hmm_signal,hmm_conf,lstm_signal,lstm_conf,tft_signal,tft_conf,genetic_signal,genetic_conf,nlp_signal,nlp_conf,ensemble_signal,ensemble_conf,kelly_fraction,trade_taken,pnl
2026-05-27T12:00:15,2345.67,NORMAL,LONG,0.85,LONG,0.78,HOLD,0.62,LONG,0.88,LONG,0.81,HOLD,0.5,LONG,0.82,0.025,YES,45.23
2026-05-27T12:01:15,2346.12,NORMAL,LONG,0.87,LONG,0.79,LONG,0.65,LONG,0.89,LONG,0.82,HOLD,0.51,LONG,0.83,0.026,YES,48.56
...
```

Each row represents one prediction cycle with all model signals, confidence scores, trade execution status, and P&L.

## How It Works

### Automatic Process (Backend)
1. **Fetch Logs**: Every 15 seconds, the frontend fetches the latest logs from the API
2. **Save Logs**: Every 5 minutes, the frontend sends logs to the backend
3. **Persist Data**: The backend saves/appends logs to the session JSON file
4. **Prevent Duplicates**: Uses timestamp to prevent duplicate entries
5. **Update Metadata**: Session metadata is updated on each save

### User Interface
- **Prediction Log Page**: Dashboard at `/prediction-log` (accessible from sidebar)
- **Save Status**: Visual indicator showing current save status
- **Session Info**: Displays current session ID and last save time
- **Manual Save**: "Save to Disk" button for on-demand saves
- **Export CSV**: Download logs as CSV file for spreadsheet analysis

## Configuration

### Auto-Save Interval
Currently set to **5 minutes (300,000 milliseconds)**

To modify, edit `dashboard/src/pages/PredictionLog.jsx`:
```javascript
// Line 67 - Change interval duration
saveIntervalRef.current = setInterval(() => {
  saveLogs();
}, 300000);  // Change this value (in milliseconds)
```

Examples:
- `60000` = 1 minute
- `300000` = 5 minutes (default)
- `600000` = 10 minutes
- `1800000` = 30 minutes

### Storage Location
Default: `E:\PRO\JIMxNik\PredictionLogs`

To change, edit `src/api/paper_trading_routes.py`:
```python
# Line 1010
LOGS_DIR = r"E:\PRO\JIMxNik\PredictionLogs"  # Change this path
```

## API Endpoints

### Save Prediction Logs
```
POST /paper-trading/save-prediction-logs
Content-Type: application/json

Request Body:
[
  { "timestamp": "...", "price": "...", ... },
  ...
]

Response:
{
  "status": "success",
  "session_id": "27052026_120000",
  "file_path": "E:\\PRO\\JIMxNik\\PredictionLogs\\PredictionLogs_27052026_120000.json",
  "records_saved": 15,
  "total_records_in_session": 150
}
```

## Python Utilities

A utility module is available for programmatic access:

```python
from src.utils.prediction_log_manager import (
    PredictionLogSession,
    PredictionLogManager,
    save_prediction_logs
)

# Get latest session
session = PredictionLogManager.get_latest_session()

# Save logs
result = session.save_logs(logs_list)

# List all sessions
sessions = PredictionLogManager.list_sessions()

# Export to CSV
csv_result = session.export_csv()

# Cleanup old sessions (older than 7 days)
cleanup_result = PredictionLogManager.cleanup_old_sessions(days_to_keep=7)
```

## Save Status Indicators

| Status | Meaning | Duration |
|--------|---------|----------|
| `idle` | Ready to save or save completed | - |
| `saving` | Currently saving logs | - |
| `success` | Logs saved successfully ✓ | 3 seconds |
| `error` | Save failed ✗ | 3 seconds |

## Examples

### Example 1: Manual Save
1. Open Dashboard → Prediction Log
2. Click "Save to Disk" button
3. Button shows "Saving..." while in progress
4. Button shows "Saved!" when complete (for 3 seconds)
5. Check the "Last saved" timestamp in the session info panel

### Example 2: Auto-Save Process
1. Page loads
2. System saves logs after 1 second
3. Every 15 seconds, new logs are fetched from API
4. Every 5 minutes, accumulated logs are saved
5. Check `E:\PRO\JIMxNik\PredictionLogs\` for new files

### Example 3: Accessing Saved Logs
```python
import json
from pathlib import Path

logs_dir = Path(r"E:\PRO\JIMxNik\PredictionLogs")
latest_file = max(logs_dir.glob("PredictionLogs_*.json"), key=lambda p: p.stat().st_mtime)

with open(latest_file, "r") as f:
    data = json.load(f)
    
print(f"Session: {data['session_id']}")
print(f"Total records: {data['total_records']}")
print(f"Last updated: {data['last_updated']}")

for log in data['logs']:
    print(f"{log['timestamp']}: {log['ensemble_signal']} @ {log['price']}")
```

## Troubleshooting

### Logs Not Saving?
1. Check that the directory `E:\PRO\JIMxNik\PredictionLogs\` exists and is writable
2. Verify the API endpoint is running (`localhost:8000`)
3. Check browser console for error messages
4. Verify API server logs for endpoint errors

### Session File Not Created?
1. Ensure logs are available (at least 1 prediction log entry)
2. Click "Save to Disk" button to manually trigger save
3. Check file permissions on PredictionLogs directory

### High Disk Usage?
Use the cleanup utility to remove old sessions:
```python
from src.utils.prediction_log_manager import PredictionLogManager
result = PredictionLogManager.cleanup_old_sessions(days_to_keep=7)
print(f"Deleted {result['deleted_count']} old sessions")
```

## Performance Notes

- **Storage**: ~5-10 KB per 100 prediction logs (JSON format)
- **Save Time**: < 500ms typical for 200 logs
- **API Overhead**: Minimal, POST body is < 50KB for 200 logs
- **CPU Impact**: Negligible (JSON serialization is fast)

## Security Considerations

- Logs contain trading signals and price data (consider as sensitive)
- Store in secure location with proper access controls
- Implement log rotation for long-running systems
- Backup logs regularly to external storage

## Future Enhancements

Potential improvements:
- [ ] Configurable save frequency per session
- [ ] Automatic compression of old session files
- [ ] Database backend instead of JSON files
- [ ] Real-time log streaming to server
- [ ] Log search and filtering interface
- [ ] Statistical analysis dashboard
