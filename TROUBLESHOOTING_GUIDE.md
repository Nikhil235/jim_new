# 🔧 Troubleshooting Guide
**Mini-Medallion Data Pipeline Troubleshooting**  
**Last Updated**: May 13, 2026  
**Status**: ✅ Comprehensive Guide

---

## 🎯 Quick Diagnosis

**Before deep troubleshooting, run this diagnostic:**

```bash
# All-in-one health check
python scripts/check_infrastructure.py

# Quick pipeline test
python scripts/daily_scheduler.py --once --mode gold-only

# Check health file
cat data/pipeline_health.json | jq '.full.status'
```

---

## 🔴 Critical Issues

### Issue 1: Pipeline Not Starting

**Symptoms:**
- Scheduler daemon not running
- No new health file entry
- Process shows as crashed

**Diagnosis:**

```bash
# Check if process is running
ps aux | grep daily_scheduler
pgrep -f daily_scheduler

# Check for error messages
tail -100 logs/pipeline.log | grep -E "ERROR|TRACEBACK"

# Try running manually
python scripts/daily_scheduler.py --once --mode gold-only
```

**Solutions:**

1. **Python not found**
   ```bash
   # Verify Python installation
   python --version
   which python
   
   # If not in PATH, use absolute path or venv
   /usr/bin/python3 scripts/daily_scheduler.py
   source .venv/bin/activate  # Activate virtual environment
   ```

2. **Missing dependencies**
   ```bash
   # Reinstall requirements
   pip install -r requirements-merged.txt --upgrade
   
   # Check specific packages
   python -c "import click; import schedule; import loguru; print('OK')"
   ```

3. **Config file missing or invalid**
   ```bash
   # Check config exists
   test -f configs/base.yaml && echo "OK" || echo "Missing"
   
   # Validate YAML syntax
   python -c "import yaml; yaml.safe_load(open('configs/base.yaml'))"
   ```

4. **Permission denied**
   ```bash
   # Fix script permissions (Linux/Mac)
   chmod +x scripts/daily_scheduler.py
   chmod -R 755 data/
   
   # Windows: Run PowerShell as Administrator
   powershell -Command "Start-Process powershell -Verb RunAs"
   ```

5. **Port already in use**
   ```bash
   # Find process using port 8000
   lsof -i :8000  # macOS/Linux
   netstat -ano | findstr :8000  # Windows
   
   # Kill the process
   kill -9 <PID>  # Unix
   taskkill /PID <PID> /F  # Windows
   ```

---

### Issue 2: Data Source Connection Failed

**Symptoms:**
- Errors fetching gold/macro/FRED data
- Row counts very low (< 100 rows)
- API timeout messages

**Diagnosis:**

```bash
# Test each data source individually
python -c "from src.ingestion.gold_fetcher import GoldFetcher; GoldFetcher().fetch_latest()"
python -c "from src.ingestion.macro_fetcher import MacroFetcher; MacroFetcher().fetch_latest()"
python -c "from src.ingestion.fred_fetcher import FREDFetcher; FREDFetcher().fetch_latest()"

# Test network connectivity
ping yahoo.com
curl -I https://query1.finance.yahoo.com
curl -I https://fred.stlouisfed.org
```

**Solutions:**

1. **Network issue**
   ```bash
   # Check internet connectivity
   ping 8.8.8.8
   
   # Test DNS
   nslookup yahoo.com
   
   # If behind proxy, configure
   export HTTP_PROXY=http://proxy:port
   export HTTPS_PROXY=http://proxy:port
   ```

2. **API rate limits**
   ```bash
   # Yahoo Finance has rate limits
   # Solution: Wait 5-10 minutes before retrying
   
   # Or reduce request frequency in config
   # Edit configs/base.yaml:
   # data:
   #   request_delay: 2  # seconds between requests
   ```

3. **API key expired**
   ```bash
   # Check API keys in .env
   grep FRED_API_KEY .env
   
   # Get new API key from https://fred.stlouisfed.org/docs/api/
   # Update .env:
   # FRED_API_KEY=your-new-key
   
   # Restart scheduler
   pkill -f daily_scheduler.py
   python scripts/daily_scheduler.py
   ```

4. **Data source temporarily down**
   ```bash
   # This is normal - wait and retry
   # Scheduler will retry with exponential backoff
   
   # Check status page
   # Yahoo Finance: https://www.yahoo.com
   # FRED: https://fred.stlouisfed.org
   
   # Force retry
   python scripts/daily_scheduler.py --once --mode full
   ```

---

### Issue 3: Database Connection Failed

**Symptoms:**
- QuestDB or Redis connection errors
- Data saved to parquet only (fallback)
- "Connection refused" messages

**Diagnosis:**

```bash
# Check if containers are running
docker ps | grep -E "questdb|redis"

# Test QuestDB connection
python -c "import psycopg2; psycopg2.connect('host=localhost port=5432 user=admin')"

# Test Redis connection
redis-cli ping

# Check logs
docker logs questdb
docker logs redis
```

**Solutions:**

1. **Container not running**
   ```bash
   # Restart Docker services
   docker-compose down
   docker-compose up -d
   
   # Verify services started
   docker-compose ps
   ```

2. **Port conflicts**
   ```bash
   # Find what's using the ports
   lsof -i :9000 | head -5  # QuestDB
   lsof -i :6379 | head -5  # Redis
   
   # If needed, change ports in docker-compose.yml
   # Restart: docker-compose up -d
   ```

3. **Insufficient resources**
   ```bash
   # Check available memory/disk
   free -h      # Memory (Linux)
   df -h        # Disk space
   docker system df
   
   # Free up space if needed
   docker system prune
   rm -rf data/processed/*.parquet  # Remove old data
   ```

4. **Corrupted database**
   ```bash
   # Reset Docker volumes
   docker-compose down -v  # WARNING: Deletes data!
   docker-compose up -d
   
   # Or restore from backup
   tar xzf backups/questdb_backup.tar.gz -C docker/volumes/
   docker-compose up -d
   ```

---

## 🟡 Performance Issues

### Issue 4: Pipeline Runs Slowly (> 180 seconds)

**Symptoms:**
- Pipeline duration increasing over time
- CPU/memory high
- Disk I/O bottleneck

**Diagnosis:**

```bash
# Analyze step durations
cat data/pipeline_health.json | jq '.full.steps | sort_by(.duration) | reverse'

# Monitor system resources during run
top
iotop
iostat -x 1

# Check specific step performance
python -c "
import json
h = json.load(open('data/pipeline_health.json'))
steps = h['full']['steps']
for s in sorted(steps, key=lambda x: x['duration'], reverse=True):
    print(f\"{s['name']:20s} {s['duration']:6.2f}s\")
"
```

**Solutions:**

1. **Large batch size**
   ```yaml
   # Reduce batch size in configs/base.yaml
   pipeline:
     batch_size: 1000  # was 5000
     chunk_size: 500   # was 2000
   ```

2. **Slow disk I/O**
   ```bash
   # Check disk performance
   iostat -x 1 5
   
   # If slow (await > 100ms):
   # - Reduce batch size
   # - Add more RAM for caching
   # - Use SSD instead of HDD
   # - Archive old parquet files
   ```

3. **CPU saturation**
   ```bash
   # Check CPU usage
   top -b -n 1 | head -20
   
   # If > 90%:
   # - Reduce feature complexity
   # - Parallel processing disabled (check config)
   # - Another process consuming CPU (kill it)
   ```

4. **Memory pressure**
   ```bash
   # Check memory usage
   free -h
   ps aux --sort=-%mem | head -10
   
   # If > 80%:
   # - Reduce row chunks in config
   # - Close other applications
   # - Upgrade server RAM
   ```

5. **Network slow**
   ```bash
   # Test network speed
   curl -w "@curl-format.txt" -o /dev/null -s https://www.google.com
   
   # If slow:
   # - Check internet connection
   # - Increase request timeouts in config
   # - Use cached data if available
   ```

---

### Issue 5: Memory Leak

**Symptoms:**
- Memory usage grows over time
- Scheduler crashes after running for hours/days
- OOM (Out of Memory) errors

**Diagnosis:**

```bash
# Monitor memory during pipeline run
watch -n 2 'ps aux | grep python | grep -v grep'

# Check for memory leaks
python -m memory_profiler scripts/daily_scheduler.py

# Analyze with debug mode
export DEBUG=true
python scripts/daily_scheduler.py --once --mode gold-only
```

**Solutions:**

1. **Explicit garbage collection**
   ```python
   # Add to src/ingestion/pipeline_orchestrator.py
   import gc
   
   def run(self, mode: str):
       # ... pipeline code ...
       gc.collect()  # Force garbage collection after each step
   ```

2. **Reduce chunk sizes**
   ```yaml
   # configs/base.yaml
   pipeline:
     chunk_size: 500      # Smaller chunks
     batch_size: 1000     # Smaller batches
   ```

3. **Clear intermediate data**
   ```python
   # Don't hold large dataframes in memory
   # Process in streaming fashion
   
   # Bad:
   df = pd.read_parquet('huge_file.parquet')  # Entire file in RAM
   
   # Good:
   for chunk in pd.read_parquet('huge_file.parquet', engine='pyarrow', chunksize=1000):
       process(chunk)
       del chunk  # Explicitly free memory
   ```

4. **Restart scheduler periodically**
   ```bash
   # Kill after 24 hours to free memory
   pkill -f daily_scheduler.py
   sleep 10
   python scripts/daily_scheduler.py
   
   # Or use cron to restart daily
   0 0 * * * pkill -f daily_scheduler.py
   1 0 * * * nohup python scripts/daily_scheduler.py > logs/scheduler.log 2>&1 &
   ```

---

## 🔵 Data Quality Issues

### Issue 6: Missing or Invalid Data

**Symptoms:**
- Row count very low (< 50K)
- NaN values in critical columns
- Feature count < 270

**Diagnosis:**

```bash
# Check data quality report
python scripts/daily_scheduler.py --once --mode full
grep -A 10 "Data Quality Report" logs/pipeline.log

# Inspect parquet files
python -c "
import pandas as pd
df = pd.read_parquet('data/processed/gold_1d_XAUUSD.parquet')
print(f'Rows: {len(df)}')
print(f'Columns: {len(df.columns)}')
print(f'NaN count:\\n{df.isna().sum()}')
print(f'Date range: {df.index.min()} to {df.index.max()}')
"

# Check recent data
tail -20 data/raw/gold_data.csv
```

**Solutions:**

1. **Gap in gold price data**
   ```bash
   # Expected: One row per day
   # If missing, might be holiday (no trading)
   
   # Check which dates are missing
   python -c "
   import pandas as pd
   df = pd.read_parquet('data/processed/gold_1d_XAUUSD.parquet')
   dates = df.index.to_series()
   missing = pd.date_range(dates.min(), dates.max()).difference(dates)
   print(f'Missing dates: {len(missing)}')
   for d in missing[:10]:
       print(f'  {d.date()} - {d.strftime(\"%A\")}')
   "
   
   # Expected missing dates:
   # - Weekends (Saturday/Sunday)
   # - US holidays
   # - New Year, Christmas, etc.
   ```

2. **NaN in feature columns**
   ```bash
   # Some features require historical data (e.g., 200-period SMA)
   # First 200 rows will have NaN for 200-period features
   
   # Solution: Use skipna=True in feature calculation
   # Or drop first N rows where N = max_lookback_window
   
   # Check which features have NaN
   python -c "
   import pandas as pd
   df = pd.read_parquet('data/features/feature_XAUUSD.parquet')
   nan_cols = df.columns[df.isna().any()]
   print(f'Columns with NaN:\\n{nan_cols.tolist()}')
   "
   ```

3. **Macro data incomplete**
   ```bash
   # Some macro indicators have less frequent data
   # E.g., Fed Funds only updates on business days
   
   # Check last update for each symbol
   python -c "
   import pandas as pd
   symbols = ['DXY', 'VIX', 'TLT', 'TIP']
   for s in symbols:
       try:
           df = pd.read_parquet(f'data/processed/macro_1d_{s}.parquet')
           print(f'{s}: {len(df)} rows, last={df.index[-1]}')
       except:
           print(f'{s}: NOT FOUND')
   "
   
   # Normal if some are 1-2 days behind gold data
   ```

---

### Issue 7: Feature Explosion / Too Many Features

**Symptoms:**
- Feature count > 300 (expected 280-290)
- Duplicate features
- Feature store size growing rapidly

**Diagnosis:**

```bash
# Check feature count
cat data/pipeline_health.json | jq '.full.feature_count'

# List all features
python -c "
import pandas as pd
df = pd.read_parquet('data/features/feature_XAUUSD.parquet')
print(f'Total features: {len(df.columns)}')
print('\\nFeature list:')
for i, col in enumerate(df.columns, 1):
    print(f'{i:3d}. {col}')
"

# Check for duplicates
python -c "
import pandas as pd
df = pd.read_parquet('data/features/feature_XAUUSD.parquet')
duplicates = df.columns[df.columns.duplicated()]
if len(duplicates) > 0:
    print(f'Duplicate features: {duplicates.tolist()}')
else:
    print('No duplicates')
"
```

**Solutions:**

1. **Reduce feature windows**
   ```yaml
   # configs/base.yaml
   features:
     lookback_windows: [5, 10, 20, 50, 100]  # was [5, 10, 20, 50, 100, 200]
     volatility_windows: [10, 20, 50]        # was [10, 20, 50, 100]
   ```

2. **Disable feature groups**
   ```yaml
   # Disable less useful feature groups
   features:
     include_momentum: true
     include_volatility: true
     include_temporal: false  # Disable temporal features
     include_microstructure: false
   ```

3. **Remove duplicate calculation**
   ```python
   # Check src/features/engine.py for duplicate loops
   # Ensure each feature calculated once only
   # Use set() to track calculated features
   ```

---

## 🟢 Configuration Issues

### Issue 8: Wrong Data Being Fetched

**Symptoms:**
- Gold price data looks wrong (jumps, gaps)
- Macro data not updating
- Alternative data always empty

**Diagnosis:**

```bash
# Check configuration
cat configs/base.yaml | grep -A 20 "^data:"

# Verify symbols are correct
grep -E "symbol|symbols:" configs/base.yaml

# Test data fetching with debug logging
export LOG_LEVEL=DEBUG
python scripts/daily_scheduler.py --once --mode gold-only
```

**Solutions:**

1. **Wrong symbol**
   ```yaml
   # Check current symbol
   data:
     gold:
       symbol: "GC=F"  # Gold futures - Correct
       # Not: "XAUUSD" (not available on Yahoo Finance)
   ```

2. **API endpoint changed**
   ```python
   # Yahoo Finance API may have changed
   # Solution: Check if yfinance library needs update
   pip install yfinance --upgrade
   
   # Or test fetching manually
   import yfinance as yf
   df = yf.download("GC=F", start="2020-01-01", progress=False)
   print(df.head())
   ```

3. **FRED API key invalid**
   ```bash
   # Get new key from https://fred.stlouisfed.org/docs/api/
   # Update .env file
   echo "FRED_API_KEY=your-new-key" >> .env
   
   # Verify
   grep FRED_API_KEY .env
   ```

4. **Alternative data source disabled**
   ```yaml
   # Check if enabled
   data:
     alternative:
       enabled: true  # Set to true if needed
       cot: true
       sentiment: true
       etf_flows: true
   ```

---

## 📞 Still Having Issues?

**Collect diagnostic information:**

```bash
# Create diagnostic bundle
mkdir diagnostics
cp data/pipeline_health.json diagnostics/
tail -100 logs/pipeline.log > diagnostics/logs.txt
python scripts/check_infrastructure.py > diagnostics/infrastructure.txt
python -c "import sys; print(sys.version)" > diagnostics/python_version.txt
pip list > diagnostics/packages.txt
docker ps > diagnostics/docker_containers.txt
df -h > diagnostics/disk_usage.txt

# Archive bundle
tar czf diagnostics_$(date +%Y%m%d_%H%M%S).tar.gz diagnostics/
```

**Send to support team:**
- Email: ops-medallion@company.com
- Slack: #medallion-support
- Include: diagnostics bundle + description of issue + when it started

---

## 📚 Related Documentation

- [OPERATIONAL_PROCEDURES.md](OPERATIONAL_PROCEDURES.md) - Daily operations
- [PRODUCTION_MONITORING.md](PRODUCTION_MONITORING.md) - Monitoring setup
- [PROJECT_STATUS.md](PROJECT_STATUS.md) - Project status
- [SCHEDULER_TEST_REPORT.md](SCHEDULER_TEST_REPORT.md) - Test results

---

**Status**: ✅ Comprehensive guide ready  
**Last Updated**: May 13, 2026  
**Feedback**: Help improve this guide → Submit issues to #medallion-support
