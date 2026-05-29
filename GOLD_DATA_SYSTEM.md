# Gold Data Download & Incremental Sync System

## Overview

The JIM trading system now includes an **automated gold price data management system** that:

- ✅ Downloads OHLCV data in **dollar/oz** from year 2000 to present
- ✅ Provides **per-minute** data for recent periods (~60 days)
- ✅ Stores data in **multiple formats** (SQLite, Parquet, CSV)
- ✅ **Automatically syncs** before each run (incremental updates only)
- ✅ **Tracks metadata** about last downloads to avoid re-fetching
- ✅ Supports **forced full updates** when needed

## System Architecture

### Components

```
┌─────────────────────────────────────────┐
│   GoldDataManager (gold_data_manager.py) │
│   - Tracks metadata (gold_metadata.json) │
│   - Checks last stored data              │
│   - Downloads missing data only          │
│   - Supports 3 timeframes                │
└─────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────┐
│   Data Storage (Database/ folder)        │
│   ├── gold_raw/                          │
│   │   ├── gold_ohlcv.db (SQLite)         │
│   │   ├── gold_ohlcv.parquet             │
│   │   ├── daily_ohlcv.csv                │
│   │   └── gold_YYYY_ohlcv.csv (yearly)   │
│   └── gold_processed/                    │
│       ├── hourly_recent_ohlcv.db         │
│       ├── minute_recent_ohlcv.db         │
│       ├── hourly_recent_ohlcv.csv        │
│       └── minute_recent_ohlcv.csv        │
└─────────────────────────────────────────┘
```

### Data Timeframes

| Timeframe | Coverage | Availability | Usage |
|-----------|----------|--------------|-------|
| **Daily** | 2000-present | Full history | Backtesting, long-term analysis |
| **Hourly** | ~12 months | Last 12 months | Swing trading, technical analysis |
| **Minute** | ~60 days | Most recent 60 days | Intraday, high-frequency |

### Metadata Tracking

File: `Database/gold_metadata.json`

```json
{
  "created": "2026-05-25T10:30:00",
  "last_daily_update": "2026-05-25T10:35:00",
  "last_minute_update": "2026-05-25T10:45:00",
  "last_hourly_update": "2026-05-25T10:40:00",
  "daily_end_date": "2026-05-25",
  "minute_end_date": "2026-05-24T16:00:00",
  "hourly_end_date": "2026-05-25T09:00:00",
  "daily_data_count": 9500,
  "hourly_data_count": 8760,
  "minute_data_count": 50000
}
```

## Usage

### Automatic Startup Sync (Recommended)

When you run the system, gold data automatically syncs:

```bash
# All three methods trigger automatic data sync:

# Method 1: Run full pipeline
.\run_jim.ps1

# Method 2: Direct pipeline execution
python scripts/run_pipeline.py --mode full

# Method 3: Main application
python main.py --mode api
```

The automatic sync:
- ✅ Checks `gold_metadata.json` for last download time
- ✅ Queries the SQLite database for latest data
- ✅ Downloads **only missing data** (incremental)
- ✅ Skips if recently updated (configurable)
- ✅ Updates metadata with new timestamps

### Manual Data Updates

#### 1. Initialize System Only

```bash
# Initialize directories and sync gold data
python scripts/init_system.py

# Force full re-download of all historical data
python scripts/init_system.py --force
```

#### 2. Gold Data Manager Direct Control

```bash
# Create manager and update incrementally
from scripts.gold_data_manager import GoldDataManager

manager = GoldDataManager()

# Update only missing data
manager.update_daily_data()        # Daily data since 2000
manager.update_hourly_data()       # Hourly data (12 months)
manager.update_minute_data()       # Minute data (60 days)

# Or run all updates at once
manager.run_incremental_update(force_daily=False)

# Force full re-download
manager.run_incremental_update(force_daily=True)

# Check current status
status = manager.get_status()
print(status)
```

#### 3. Old Download Script (Legacy)

The original download script still works for full downloads:

```bash
# Full download (all data from scratch)
python scripts/download_gold_data.py
```

## Loading Data in Your Code

### From SQLite Database

```python
import sqlite3
import pandas as pd

# Connect to daily data
conn = sqlite3.connect("Database/gold_raw/gold_ohlcv.db")
df = pd.read_sql_query(
    "SELECT * FROM gold_ohlcv WHERE timestamp > '2020-01-01' ORDER BY timestamp",
    conn
)
conn.close()

# Convert timestamp to datetime
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.set_index('timestamp')
```

### From Parquet (Recommended - Fast)

```python
import pandas as pd

# Load daily data
df_daily = pd.read_parquet("Database/gold_raw/gold_ohlcv.parquet")

# Load hourly data
df_hourly = pd.read_parquet("Database/gold_processed/hourly_recent_ohlcv.parquet")

# Load minute data
df_minute = pd.read_parquet("Database/gold_processed/minute_recent_ohlcv.parquet")
```

### From CSV

```python
import pandas as pd

# Load specific year
df_2020 = pd.read_csv(
    "Database/gold_raw/gold_2020_ohlcv.csv",
    index_col='timestamp',
    parse_dates=True
)

# Load all combined daily
df_all = pd.read_csv(
    "Database/gold_raw/daily_ohlcv.csv",
    index_col='timestamp',
    parse_dates=True
)
```

## Data Format

### OHLCV Columns

```
timestamp        : Datetime (UTC)
open             : Opening price ($/oz)
high             : High price ($/oz)
low              : Low price ($/oz)
close            : Closing price ($/oz)
volume           : Trading volume
returns          : Price returns (close-to-close %)
```

### Example Data

```
timestamp            open    high    low     close   volume
2026-05-25 16:00:00  2425.50 2428.75 2424.25 2427.00 5000
2026-05-25 17:00:00  2427.10 2429.50 2425.75 2428.50 4800
...
```

## Incremental Update Logic

The system is smart about incremental updates:

### Daily Data
- **Update Frequency**: Triggered on each run
- **Skip Logic**: No skip - always checks for new daily bars
- **Data Source**: Yahoo Finance `GC=F`
- **Lookback**: 2000-01-01 to today

### Hourly Data
- **Update Frequency**: Minimum 2 hours between updates
- **Skip Logic**: Skips if updated <2 hours ago
- **Data Source**: Yahoo Finance `GC=F`
- **Lookback**: Last 12 months

### Minute Data
- **Update Frequency**: Minimum 1 hour between updates
- **Skip Logic**: Skips if updated <1 hour ago
- **Data Source**: Yahoo Finance (limited to ~60 days)
- **Lookback**: Last 60 days

### Database Merge Logic

When new data arrives:

```
1. Check if timestamp already exists
2. If exists and overlapping: DELETE overlapping records
3. APPEND new records
4. CREATE INDEX on timestamp for fast queries
5. UPDATE metadata.json with:
   - last_update timestamp
   - end_date of latest data
   - record count
```

This ensures:
- ✅ No duplicate records
- ✅ Efficient incremental updates
- ✅ Always have latest data
- ✅ Fast query performance

## Troubleshooting

### Issue: "No data available" for minute data

**Reason**: Yahoo Finance only provides ~60 days of minute data

**Solution**: Use hourly or daily data instead

```python
# Use hourly data instead
df = pd.read_parquet("Database/gold_processed/hourly_recent_ohlcv.parquet")
```

### Issue: Duplicate timestamps in database

**Reason**: Manual data insertion or corrupted merge

**Solution**: Rebuild the database

```bash
# Force full update
python scripts/init_system.py --force
```

### Issue: Old data not updating

**Reason**: Metadata shows false "recently updated"

**Solution**: Delete metadata file and reinitialize

```bash
# Remove metadata
rm Database/gold_metadata.json

# Reinitialize
python scripts/init_system.py
```

### Issue: Download fails due to network

**Reason**: Yahoo Finance API temporarily unavailable

**Solution**: System auto-retries on next run. No manual action needed.

## Configuration

The system uses sensible defaults, but you can modify behavior:

### Edit in `gold_data_manager.py`

```python
# Change symbols (for different data sources)
self.symbol = "GC=F"        # Gold Futures (default)
self.symbol_spot = "XAUUSD=X"  # Spot price (fallback)

# Change lookback periods
# For hourly data: modify months parameter in update_hourly_data()
# For minute data: modify days parameter in update_minute_data()

# Change update frequency thresholds
# Edit the timedelta values in each update method
```

## Performance Tips

### Query Large Datasets Efficiently

```python
# ✗ SLOW: Load entire dataset
df = pd.read_parquet("Database/gold_raw/gold_ohlcv.parquet")
df_filtered = df[df['timestamp'] > '2020-01-01']

# ✓ FAST: Query only what you need
conn = sqlite3.connect("Database/gold_raw/gold_ohlcv.db")
df = pd.read_sql_query(
    "SELECT * FROM gold_ohlcv WHERE timestamp > '2020-01-01'",
    conn
)
conn.close()
```

### Use Parquet for Large Reads

```python
# Parquet is:
# - 80-90% smaller than CSV
# - 5-10x faster to read
# - Column-oriented (read only needed columns)
# - Supports filtering

df = pd.read_parquet(
    "Database/gold_raw/gold_ohlcv.parquet",
    filters=[("timestamp", ">=", "2020-01-01")]
)
```

## Data Retention Policy

Default data retention:

- **Daily**: Keep all data (2000-present) ~25 years
- **Hourly**: Keep 12 months
- **Minute**: Keep 60 days

To extend retention, modify the lookback parameters in `gold_data_manager.py`.

## Integration with Trading System

The gold data system automatically integrates:

1. **On Startup** (`run_jim.ps1`):
   - System initialization runs
   - Data syncs automatically
   - Pipeline processes data

2. **In Pipeline** (`run_pipeline.py`):
   - Gold data manager runs first
   - Then main pipeline uses synced data
   - Features generated from fresh data

3. **In Main App** (`main.py`):
   - Initialization runs on any mode
   - Data guaranteed fresh
   - No manual sync needed

## Quick Reference

```bash
# Full workflow (includes auto-sync)
.\run_jim.ps1

# Just sync gold data
python scripts/init_system.py

# Force re-download all historical data
python scripts/init_system.py --force

# Check current data status
python -c "from scripts.gold_data_manager import GoldDataManager; m=GoldDataManager(); print(m.get_status())"

# Load and analyze data
python
>>> import pandas as pd
>>> df = pd.read_parquet("Database/gold_raw/gold_ohlcv.parquet")
>>> print(df.tail())
>>> print(f"Data from {df.index.min()} to {df.index.max()}")
```

---

**Last Updated**: May 25, 2026
**Version**: 1.0
**System**: Mini-Medallion Gold Trading Engine
