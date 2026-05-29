# 🚀 Prediction Logs Auto-Save - Quick Start

## What Was Implemented?

Your prediction logs are now **automatically saved every 5 minutes** to your local system in a dedicated directory.

### Location
```
E:\PRO\JIMxNik\PredictionLogs\
```

### File Format
```
PredictionLogs_DDMMYYYY_HHMMSS.csv
Example: PredictionLogs_27052026_120530.csv
```

**Format:** Standard CSV with headers - fully compatible with Excel, Python, R, etc.

---

## ✨ Key Features

| Feature | Details |
|---------|---------|
| **Auto-Save** | Every 5 minutes automatically |
| **Manual Save** | "Save to Disk" button anytime |
| **Session-Wise** | New file per session |
| **Format** | JSON with metadata |
| **Storage** | Local disk (no cloud) |
| **Deduplication** | Prevents duplicate entries |

---

## 🎯 How to Use

### 1. **View Prediction Logs**
```
Dashboard → Prediction Log (left sidebar)
```

### 2. **Monitor Auto-Save Status**
Look for the green status panel:
```
📁 Local Storage Active
Session: 27052026_120530
Last saved: 5/27/2026, 12:05:30 PM
Auto-saving every 5 minutes
```

### 3. **Manual Save (Anytime)**
```
Click → "Save to Disk" button
Wait → Button shows "Saving..."
Done → Button shows "Saved!" (3 seconds)
```

### 4. **Export CSV**
```
Click → "Export CSV" button
Opens → Browser download dialog
Result → prediction_log_YYYY-MM-DD.csv
```

---

## 📁 What Gets Saved?

Each log file contains:

```json
{
  "session_id": "27052026_120530",
  "created_at": "2026-05-27T12:05:30",
  "last_updated": "2026-05-27T12:10:30",
  "total_records": 45,
  "logs": [
    {
      "timestamp": "2026-05-27T12:05:00",
      "price": "2345.67",
      "regime": "NORMAL",
      "wavelet_signal": "LONG",
      "ensemble_signal": "LONG",
      "kelly_fraction": 0.025,
      "trade_taken": "YES",
      "pnl": "45.23"
      // ... more fields
    }
    // ... more logs
  ]
}
```

---

## ⚙️ Configuration

### Change Save Interval (Default: 5 minutes)

**File:** `dashboard/src/pages/PredictionLog.jsx` (Line 67)

```javascript
// Change this value (in milliseconds)
300000  // ← default 5 minutes

// Examples:
60000   // 1 minute
180000  // 3 minutes
600000  // 10 minutes
```

### Change Storage Location

**File:** `src/api/paper_trading_routes.py` (Line 1010)

```python
LOGS_DIR = r"E:\PRO\JIMxNik\PredictionLogs"  # ← change this path
```

---

## 🐍 Python Usage

Access your saved logs programmatically:

```python
from src.utils.prediction_log_manager import PredictionLogManager
import pandas as pd
from pathlib import Path

# List all sessions
sessions = PredictionLogManager.list_sessions()
print(f"Found {len(sessions)} sessions")
for session in sessions:
    print(f"  {session['session_id']}: {session['total_records']} records")

# Get latest session
latest = PredictionLogManager.get_latest_session()
print(f"Latest session: {latest.session_id}")

# Load logs from CSV
logs = latest.load_logs()
print(f"Loaded {len(logs)} logs")

# Convert to DataFrame for analysis
df = pd.read_csv(latest.filepath)
print(df.head())

# Get session metadata
metadata = latest.get_metadata()
print(f"Session created: {metadata['created_at']}")
print(f"Total records: {metadata['total_records']}")

# Cleanup old sessions (>7 days)
cleanup = PredictionLogManager.cleanup_old_sessions(days_to_keep=7)
print(f"Deleted {cleanup['deleted_count']} old sessions")
```

---

## 📊 Data Analysis Example

```python
import pandas as pd
from pathlib import Path

# Load latest session CSV
logs_dir = Path(r"E:\PRO\JIMxNik\PredictionLogs")
latest_file = max(logs_dir.glob("PredictionLogs_*.csv"), key=lambda p: p.stat().st_mtime)

# Read directly into DataFrame
df = pd.read_csv(latest_file)

# Analysis
print(f"Total trades: {len(df[df['trade_taken'] == 'YES'])}")
print(f"Win rate: {len(df[df['pnl'] > 0]) / len(df) * 100:.1f}%")
print(f"Avg P&L: ${df['pnl'].astype(float).mean():.2f}")
print(f"Total P&L: ${df['pnl'].astype(float).sum():.2f}")

# Plot signals
signal_counts = df['ensemble_signal'].value_counts()
print(f"\nSignal Distribution:\n{signal_counts}")

# Export to Excel
df.to_excel("prediction_analysis.xlsx", index=False)
```

---

## 🔍 Troubleshooting

### "Save Failed" Error?
1. Check if `E:\PRO\JIMxNik\PredictionLogs\` exists
2. Ensure folder is writable
3. Verify API server is running on `localhost:8000`
4. Check browser console for details (F12 → Console)

### Logs Not Appearing?
1. Make sure prediction logs are being generated
2. Wait at least 1 second after page load
3. Check API response: `GET /paper-trading/prediction-log`
4. Verify at least one log entry exists

### Directory Not Found?
```powershell
# Create it manually
mkdir "E:\PRO\JIMxNik\PredictionLogs"
```

---

## 📝 Important Notes

✅ **Automatic Startup:** Saves begin immediately when you open Prediction Log page

✅ **No Data Loss:** New sessions created per application launch, old sessions preserved

✅ **Efficient Storage:** ~5-10 KB per 100 logs, minimal disk usage

✅ **Real-time:** Logs saved within seconds of API updates

⚠️ **Manual Action:** You should periodically backup these files to external storage

---

## 📚 Full Documentation

For detailed information, see:
- [`PREDICTION_LOGS_SETUP.md`](PREDICTION_LOGS_SETUP.md) - Complete setup guide
- [`IMPLEMENTATION_SUMMARY_PREDICTION_LOGS.md`](IMPLEMENTATION_SUMMARY_PREDICTION_LOGS.md) - Technical details

---

## 🎯 Next Steps

1. **Open Dashboard** → Go to Prediction Log page
2. **Wait for Logs** → Monitor the session info panel
3. **Check Files** → Navigate to `E:\PRO\JIMxNik\PredictionLogs\`
4. **View JSON** → Open any PredictionLogs_*.json file to see saved data
5. **Export Data** → Use the Export CSV button for spreadsheet analysis

---

## 📞 Summary

| Action | What Happens |
|--------|--------------|
| Page Opens | Saves logs immediately (1s delay) |
| Every 15s | Fetches latest logs from API |
| Every 5m | Auto-saves new logs to disk |
| Click "Save" | Manually trigger save anytime |
| Click "Export" | Download all logs as CSV |
| Session Info | Shows ID and last save time |

---

**Status:** ✅ **LIVE AND READY TO USE**

Your prediction logs are now being automatically archived to your local system!
