# Gold Data Management System

The JIM trading system includes an automated, incremental gold price data management system that handles downloading, tracking, and storing historical and live data in multiple formats (SQLite, Parquet, CSV).

## 1. Key Features & Data Timeframes

- **Incremental Updates**: Downloads only missing data based on `Database/gold_metadata.json` to prevent duplicate fetches.
- **Auto-Sync**: Automatically runs on startup before trading or pipeline logic.
- **Multiple Formats**: Saves data to SQLite (fast queries), Parquet (compressed, fast reads), and CSV (human-readable).

| Timeframe | Coverage | Usage |
|-----------|----------|-------|
| **Daily** | 2000-present | Backtesting, long-term analysis |
| **Hourly** | Last 12 months | Swing trading, technical analysis |
| **Minute** | Last ~60 days | Intraday, high-frequency |

## 2. Directory Structure

All data is stored inside the `Database/` directory:
```text
Database/
├── gold_metadata.json          ← Last update timestamps & counters
├── gold_raw/                   ← Historical daily data (2000-present)
│   ├── gold_ohlcv.db           (SQLite database)
│   ├── gold_ohlcv.parquet      (Compressed format - recommended)
│   └── daily_ohlcv.csv         (Combined CSV)
└── gold_processed/             ← Recent/processed data
    ├── hourly_recent_ohlcv.db  (SQLite)
    ├── hourly_recent_ohlcv.parquet
    └── minute_recent_ohlcv.parquet
```

## 3. Usage & Syncing Data

**Automatic Sync (Recommended)**
The system automatically syncs data whenever you start the main application or pipeline:
```bash
.\run_jim.ps1
# OR
python main.py --mode api
# OR
python scripts/run_pipeline.py --mode full
```

**Manual Control & Forced Updates**
```bash
# Initialize and sync data
python scripts/init_system.py

# Force full re-download of all historical data
python scripts/init_system.py --force

# Run the test suite to verify data integrity
python scripts/test_gold_data.py
```

**Direct Manager Access (Python)**
```python
from scripts.gold_data_manager import GoldDataManager

manager = GoldDataManager()
manager.run_incremental_update(force_daily=False)
print(manager.get_status())
```

## 4. Loading Data in Your Code

**Method 1: Parquet (Fastest - Recommended)**
```python
import pandas as pd

# Load daily data
df_daily = pd.read_parquet("Database/gold_raw/gold_ohlcv.parquet")

# Load minute data
df_minute = pd.read_parquet("Database/gold_processed/minute_recent_ohlcv.parquet")
```

**Method 2: SQLite (Efficient Filtering)**
```python
import sqlite3
import pandas as pd

conn = sqlite3.connect("Database/gold_raw/gold_ohlcv.db")
df = pd.read_sql_query(
    "SELECT * FROM gold_ohlcv WHERE timestamp > '2020-01-01' ORDER BY timestamp DESC", 
    conn
)
conn.close()
```

## 5. Troubleshooting

| Issue | Solution |
|-------|----------|
| **"No data available" for minute data** | Yahoo Finance only provides ~60 days of minute data. Use hourly or daily data for older periods. |
| **Data looks stale / Not updating** | Force an update: `python scripts/init_system.py --force`. Alternatively, delete `Database/gold_metadata.json` and reinitialize. |
| **Download fails due to network** | The system automatically retries on the next run. No manual action is needed. |
| **SQLite "database is locked"** | Restart the Python kernel or application. |
