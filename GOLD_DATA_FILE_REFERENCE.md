# Gold Data System - File Reference & Integration Map

## 📋 New Files Created

### Core System Files

#### 1. `scripts/gold_data_manager.py` (445 lines)
**Purpose**: Incremental gold data download manager
**Key Classes**:
- `GoldDataManager`: Main class for managing incremental updates
  - `update_daily_data()`: Downloads missing daily bars
  - `update_hourly_data()`: Downloads missing hourly bars
  - `update_minute_data()`: Downloads missing minute bars (8-day chunks)
  - `run_incremental_update()`: Orchestrates all updates
  - `get_status()`: Returns current data status
  - `_get_last_timestamp_in_db()`: Queries last date in database
  - `_append_to_sqlite()`: Efficiently appends new data
  - `_save_parquet()`: Saves to Parquet format
  - `_save_combined_formats()`: Maintains CSV exports

**Key Features**:
- Tracks metadata in `gold_metadata.json`
- Checks for existing data before downloading
- Handles duplicate removal and merging
- Timezone-aware timestamp handling
- Non-blocking error handling

#### 2. `scripts/init_system.py` (180 lines)
**Purpose**: System initialization called on startup
**Key Functions**:
- `ensure_directories()`: Creates Database/ and subdirectories
- `sync_gold_data()`: Calls gold data manager
- `initialize_system()`: Orchestrates full initialization
  - Step 1: Create directories
  - Step 2: Sync gold data
  - Returns status report

**Key Features**:
- Called by main.py before trading logic starts
- Can be run standalone: `python scripts/init_system.py`
- Supports `--force` flag for full re-download
- Comprehensive status reporting

#### 3. `scripts/test_gold_data.py` (280 lines)
**Purpose**: Comprehensive test suite for gold data system
**Key Functions**:
- `test_daily_data()`: Loads and validates daily data
- `test_hourly_data()`: Loads and validates hourly data
- `test_minute_data()`: Loads and validates minute data
- `test_sqlite_query()`: Tests database queries
- `test_metadata()`: Validates metadata file
- `test_file_sizes()`: Reports storage efficiency
- `run_all_tests()`: Runs all tests with summary

**Features**:
- 5 tests, all passing
- Reports record counts, date ranges, price ranges
- Tests all storage formats (SQLite, Parquet, CSV)
- Provides performance metrics
- Exit code 0 on success, 1 on failure

---

## 📚 Documentation Files Created

#### 1. `GOLD_DATA_SYSTEM.md` (400+ lines)
**Comprehensive Technical Documentation**
- System architecture diagram
- Data timeframes and availability
- Metadata structure
- Usage examples (3 methods)
- Data loading code samples
- Incremental update logic explanation
- Troubleshooting guide
- Performance tips
- Configuration options
- Data retention policy
- Integration details

#### 2. `GOLD_DATA_QUICK_START.md` (350+ lines)
**User-Friendly Quick Start Guide**
- Feature summary
- Data structure overview
- How to use (3 options)
- Code examples
- Data samples
- Architecture flow diagram
- Key files table
- Verification steps
- Quick reference commands
- Trading logic example

#### 3. This File: `GOLD_DATA_FILE_REFERENCE.md`
**File and integration map**

---

## 🔧 Modified Files

### 1. `main.py`
**Changes**: Added system initialization on startup
```python
# Added before GPU detection
from scripts.init_system import initialize_system
init_status = initialize_system(force_gold_update=False)
```
**Impact**: 
- Gold data syncs automatically on every mode
- Non-blocking (won't crash if sync fails)
- All modes benefit (demo, api, pipeline, paper, etc.)

### 2. `run_jim.ps1`
**Changes**: Added Step 0 initialization
```powershell
# Step 0: Initialize System & Sync Gold Data
Write-Host "[0/3] Initializing System & Syncing Gold Data..."
& ".\.venv\Scripts\python.exe" "scripts/init_system.py"
```
**Impact**:
- Gold data syncs before pipeline runs
- Explicit visibility in startup logs
- Users can see initialization progress

### 3. `scripts/run_pipeline.py`
**Changes**: Added gold data manager before pipeline
```python
from scripts.gold_data_manager import GoldDataManager
gold_manager = GoldDataManager()
gold_manager.run_incremental_update(force_daily=False)
```
**Impact**:
- Pipeline always has fresh data
- Incremental updates avoid redundant downloads
- Clear separation: "PHASE 1: GOLD DATA SYNC" vs "PHASE 2: PIPELINE"

---

## 📊 Data Storage Locations

### Primary Storage

```
Database/
├── gold_metadata.json              (Updated on each sync)
│
├── gold_raw/                       (Historical daily data)
│   ├── gold_ohlcv.db              (SQLite: 6,457 records)
│   ├── gold_ohlcv.parquet         (Compressed: 0.28 MB)
│   ├── daily_ohlcv.csv            (Combined CSV)
│   ├── gold_2000_ohlcv.csv        (2000 data)
│   ├── gold_2001_ohlcv.csv        (2001 data)
│   └── ...
│   └── gold_2026_ohlcv.csv        (2026 data)
│
└── gold_processed/                 (Recent processed data)
    ├── hourly_recent_ohlcv.db     (SQLite: 5,599 records)
    ├── hourly_recent_ohlcv.parquet (Compressed: 0.20 MB)
    ├── hourly_recent_ohlcv.csv    (CSV export)
    ├── minute_recent_ohlcv.db     (SQLite: 6,699 records)
    ├── minute_recent_ohlcv.parquet (Compressed: 0.13 MB)
    └── minute_recent_ohlcv.csv    (CSV export)
```

### Total Storage Used
- **SQLite databases**: 1.93 MB
- **Parquet files**: 0.61 MB
- **CSV files**: ~3 MB (for reference)
- **Metadata**: ~1 KB
- **Total**: < 10 MB

---

## 🔄 Integration Workflow

### Startup Sequence

```
User runs: .\run_jim.ps1
           ↓
    run_jim.ps1 (Step 0)
    ├── Calls: scripts/init_system.py
    │   ├── ensure_directories()
    │   └── sync_gold_data()
    │       └── GoldDataManager.run_incremental_update()
    │
    run_jim.ps1 (Step 1)
    ├── Calls: scripts/run_pipeline.py --mode full
    │   ├── GoldDataManager.run_incremental_update()
    │   └── PipelineOrchestrator.run()
    │
    run_jim.ps1 (Step 2)
    ├── Calls: main.py --mode api
    │   ├── initialize_system()
    │   └── uvicorn (REST API)
    │
    run_jim.ps1 (Step 3)
    └── Calls: dashboard npm run dev
```

### Alternative Entry Points

**Direct API**:
```bash
python main.py --mode api
├── initialize_system() [from main.py]
└── API server running (gold data fresh)
```

**Direct Pipeline**:
```bash
python scripts/run_pipeline.py --mode full
├── GoldDataManager sync [from run_pipeline.py]
└── Pipeline orchestration
```

**Direct Initialization**:
```bash
python scripts/init_system.py
└── Gold data synced, ready for use
```

---

## 💾 API Reference

### GoldDataManager Class

**Initialization**:
```python
from scripts.gold_data_manager import GoldDataManager
manager = GoldDataManager()
```

**Methods**:

```python
# Incremental update (main method)
success = manager.run_incremental_update(force_daily=False)

# Individual updates
manager.update_daily_data(force_full_update=False)
manager.update_hourly_data(force_update=False)
manager.update_minute_data(days=8, force_update=False)

# Status & info
status = manager.get_status()
# Returns:
# {
#   "daily": {"count": 6457, "last_update": "...", "last_date": "..."},
#   "hourly": {...},
#   "minute": {...}
# }

# Metadata access
metadata = manager.metadata
# Fields: created, last_*_update, last_*_date, *_data_count
```

**Data Loading**:
```python
import pandas as pd

# From Parquet (recommended)
df = pd.read_parquet("Database/gold_raw/gold_ohlcv.parquet")

# From SQLite
import sqlite3
conn = sqlite3.connect("Database/gold_raw/gold_ohlcv.db")
df = pd.read_sql_query("SELECT * FROM gold_ohlcv WHERE timestamp > '2020-01-01'", conn)
conn.close()

# From CSV
df = pd.read_csv("Database/gold_raw/daily_ohlcv.csv", index_col='timestamp', parse_dates=True)
```

---

## 🔍 Monitoring & Debugging

### Check Current Status
```bash
# Python one-liner
python -c "from scripts.gold_data_manager import GoldDataManager; print(GoldDataManager().get_status())"

# Run test suite
python scripts/test_gold_data.py

# View metadata
cat Database/gold_metadata.json | python -m json.tool
```

### Data Quality Checks
```python
import pandas as pd
import sqlite3

# Check for gaps in daily data
df = pd.read_parquet("Database/gold_raw/gold_ohlcv.parquet")
df = df.sort_index()
date_diff = df.index.to_series().diff()
gaps = date_diff[date_diff > pd.Timedelta(days=2)]
print(f"Gaps found: {len(gaps)}")

# Check SQLite integrity
conn = sqlite3.connect("Database/gold_raw/gold_ohlcv.db")
cursor = conn.cursor()
cursor.execute("PRAGMA integrity_check;")
print(cursor.fetchone())
conn.close()
```

---

## 🚀 Common Operations

### Force Re-Download All Data
```bash
python scripts/init_system.py --force
```

### Update Only Specific Timeframe
```python
from scripts.gold_data_manager import GoldDataManager
m = GoldDataManager()

# Update only daily (2000-present)
m.update_daily_data()

# Update only hourly (12 months)
m.update_hourly_data(force_update=True)

# Update only minute (8 days)
m.update_minute_data(force_update=True)
```

### Export Data to Different Format
```python
import pandas as pd

# Load from Parquet
df = pd.read_parquet("Database/gold_raw/gold_ohlcv.parquet")

# Export to CSV
df.to_csv("my_gold_data.csv")

# Export to Excel
df.to_excel("my_gold_data.xlsx")

# Export to HDF5 (fast for large files)
df.to_hdf("my_gold_data.h5", key="gold")
```

---

## ✅ Verification Checklist

After setup, verify:

- [ ] `Database/` folder exists with `gold_raw/` and `gold_processed/` subdirectories
- [ ] `Database/gold_metadata.json` file exists
- [ ] `gold_ohlcv.db` SQLite database has data (~6,457 records)
- [ ] `gold_ohlcv.parquet` file exists (~0.28 MB)
- [ ] Hourly and minute data files exist
- [ ] `python scripts/test_gold_data.py` shows all ✓
- [ ] `.\run_jim.ps1` completes initialization step 0
- [ ] Data timestamps are current (within last 24 hours)

---

## 📞 Support

**All files are well-documented with inline comments.**

### For Specific Issues

**Data not updating**:
1. Check: `cat Database/gold_metadata.json`
2. Run: `python scripts/test_gold_data.py`
3. Force: `python scripts/init_system.py --force`

**SQLite errors**:
1. Verify database file: `ls -la Database/gold_raw/gold_ohlcv.db`
2. Check integrity: `python scripts/test_gold_data.py`
3. Rebuild: Delete database and re-run init

**Yahoo Finance timeouts**:
- System retries automatically on next run
- Incremental updates minimize data transferred
- Consider using cached/offline data if network issues persist

---

## 🎯 Summary

**What you now have**:
✅ Automated gold data downloads (OHLCV, $/oz)
✅ Incremental updates (only missing data)
✅ Multiple storage formats (SQLite, Parquet, CSV)
✅ Automatic startup sync
✅ Comprehensive testing
✅ Complete documentation

**Implementation Status**: ✅ Complete & Tested (May 25, 2026)
