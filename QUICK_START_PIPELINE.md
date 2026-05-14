# QUICK START: RUNNING THE PHASE 2 DATA PIPELINE
**Date**: May 13, 2026 (Operations Ready)  
**For**: Developers, DevOps, Operations

🔗 **For detailed operations procedures, see [OPERATIONAL_PROCEDURES.md](OPERATIONAL_PROCEDURES.md)**  
📊 **For monitoring setup, see [PRODUCTION_MONITORING.md](PRODUCTION_MONITORING.md)**  
🔧 **For troubleshooting, see [TROUBLESHOOTING_GUIDE.md](TROUBLESHOOTING_GUIDE.md)**

---

## 🚀 ONE-TIME SETUP

### Step 1: Install Dependencies
```bash
cd /path/to/JIM_Latest
pip install -r requirements-merged.txt  # Updated: consolidated requirements
```

### Step 2: Verify Docker Stack
```bash
docker-compose up -d
docker-compose ps
# All 6 services should be "Up"
```

### Step 3: Test Once (Don't Schedule Yet)
```bash
python scripts/daily_scheduler.py --once --mode full
```

**Expected output**: Green checkmarks for each step, final status "SUCCESS"

### Step 4: Check Data in QuestDB
```bash
curl -X GET http://localhost:9000/exec -d "SELECT COUNT(*) FROM gold_1d"
# Should return > 0 rows
```

---

## ⏰ DAILY EXECUTION (Choose One)

### Option A: Command-Line (Development)
```bash
# Run once now (test)
python scripts/daily_scheduler.py --once --mode full

# Run once with specific mode
python scripts/daily_scheduler.py --once --mode gold-only

# Start scheduler in foreground (Ctrl+C to stop)
python scripts/daily_scheduler.py

# Run in background
nohup python scripts/daily_scheduler.py > logs/scheduler.log 2>&1 &
```

### Option B: Python Script (Simple)
```bash
# Create a wrapper script to run in background
cat > run_scheduler.sh << 'EOF'
#!/bin/bash
cd /path/to/JIM_Latest
nohup python run_daily_pipeline.py --schedule > logs/scheduler.log 2>&1 &
EOF

chmod +x run_scheduler.sh
./run_scheduler.sh
```

### Option C: Crontab (Linux/macOS)
```bash
# Edit crontab
crontab -e

# Add this line (runs daily at 00:00 UTC)
0 0 * * * cd /path/to/JIM_Latest && python run_daily_pipeline.py --schedule

# Or for one-time daily execution (no scheduler)
0 0 * * * cd /path/to/JIM_Latest && python run_daily_pipeline.py --once
```

### Option D: Systemd (Production Linux)
```bash
# Create service file
sudo tee /etc/systemd/system/medallion-pipeline.service > /dev/null << 'EOF'
[Unit]
Description=Mini-Medallion Daily Data Pipeline
After=network.target docker.service
Wants=docker.service

[Service]
Type=simple
User=medallion
WorkingDirectory=/path/to/JIM_Latest
ExecStart=/usr/bin/python3 /path/to/JIM_Latest/run_daily_pipeline.py --schedule
Restart=always
RestartSec=10
StandardOutput=append:/var/log/medallion-pipeline.log
StandardError=append:/var/log/medallion-pipeline-error.log

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable medallion-pipeline
sudo systemctl start medallion-pipeline

# Monitor
sudo systemctl status medallion-pipeline
tail -f /var/log/medallion-pipeline.log
```

### Option E: Windows Task Scheduler
```batch
# Create a batch file wrapper
echo @echo off > run_pipeline.bat
echo cd /d C:\path\to\JIM_Latest >> run_pipeline.bat
echo python run_daily_pipeline.py --once >> run_pipeline.bat

# Then in Task Scheduler:
# 1. Create Basic Task
# 2. Trigger: Daily at 00:00
# 3. Action: Start a program
# 4. Program: C:\Python311\python.exe
# 5. Arguments: C:\path\to\JIM_Latest\run_pipeline.bat
# 6. Run with highest privileges: Yes
```

---

## 🔧 COMMON OPERATIONS

### Check Scheduler Status
```bash
# See if scheduler is running
ps aux | grep run_daily_pipeline

# View recent pipeline executions
tail -50 logs/medallion.log

# Count successful runs
grep "PIPELINE COMPLETE" logs/medallion.log | wc -l
```

### Run Specific Mode Only
```bash
# Gold data only
python run_daily_pipeline.py --once --mode gold-only

# Macro data only (requires FRED API key)
python run_daily_pipeline.py --once --mode macro-only

# Features only (uses existing data)
python run_daily_pipeline.py --once --mode features-only

# Incremental (new data only)
python run_daily_pipeline.py --once --mode incremental
```

### Schedule at Different Time
```bash
# Default is 00:00 UTC
python run_daily_pipeline.py --schedule

# Schedule at 02:00 UTC instead
python run_daily_pipeline.py --schedule --hour 2

# Schedule at 02:30 UTC
python run_daily_pipeline.py --schedule --hour 2 --minute 30
```

### Verify Data Ingestion
```bash
# Connect to QuestDB
curl -X GET http://localhost:9000/exec -d "SELECT COUNT(*) as count, MAX(timestamp) as latest FROM gold_1d"

# Check features in Redis
redis-cli KEYS "gold:features:*" | head -5

# View all macro data tables
curl -X GET http://localhost:9000/exec -d "SHOW TABLES" | grep macro
```

### View Pipeline Output
```bash
# Real-time logging (follow last 100 lines)
tail -f logs/medallion.log

# Count rows ingested per step
grep "✅" logs/medallion.log | tail -10

# Find errors
grep "❌" logs/medallion.log

# Summary of last run
grep "PIPELINE COMPLETE" logs/medallion.log -A 5 | tail -10
```

---

## 🐛 TROUBLESHOOTING

### Pipeline won't start
```bash
# Check Python version (need 3.9+)
python --version

# Check imports work
python -c "from src.ingestion.pipeline_orchestrator import PipelineOrchestrator; print('OK')"

# Check Docker services are running
docker-compose ps
# If not, restart:
docker-compose down
docker-compose up -d
```

### FRED data not fetching
```bash
# Set API key
export FRED_API_KEY="your_key_here"

# Test FRED fetch
python -c "from src.ingestion.macro_fetcher import MacroFetcher; m = MacroFetcher(); print(m.fetch_fred_data())"
```

### QuestDB not accepting writes
```bash
# Check QuestDB is running
curl http://localhost:9000/status

# Check ILP port is open
nc -zv localhost 9009

# View QuestDB logs
docker logs questdb | tail -50
```

### Features not appearing in Redis
```bash
# Check Redis is running
redis-cli ping
# Should return: PONG

# View stored features
redis-cli KEYS "gold:features:*" | wc -l
# Should be > 0
```

### Scheduler not running at scheduled time
```bash
# For crontab: Check cron daemon is running
ps aux | grep cron

# Check crontab is set correctly
crontab -l

# For systemd: Check service status
sudo systemctl status medallion-pipeline

# View systemd logs
sudo journalctl -u medallion-pipeline -n 50
```

---

## 📊 MONITORING

### Key Metrics to Watch
1. **Pipeline Duration**: Should be < 1 minute
2. **Rows Ingested**: ~8,850 rows per daily run
3. **Features Generated**: Should be ~140
4. **Success Rate**: 100% (or note which step failed)
5. **Data Freshness**: Max age should be < 24 hours

### Grafana Dashboard (Optional)
Access http://localhost:3000 (admin/medallion) to view:
- QuestDB row count per table
- Redis memory usage
- Pipeline execution time
- Data quality alerts

### Log-Based Monitoring
```bash
# Check daily success rate
grep "PIPELINE COMPLETE" logs/medallion.log | grep "SUCCESS" | wc -l

# Find failures
grep "FAILED" logs/medallion.log

# Check latest run time
tail -1 logs/medallion.log
```

---

## ✅ CHECKLIST FOR PRODUCTION

Before going live, verify:
- [ ] Docker services all running: `docker-compose ps`
- [ ] First test run successful: `python run_daily_pipeline.py --once`
- [ ] Data appears in QuestDB: `curl http://localhost:9000/exec ...`
- [ ] Features appear in Redis: `redis-cli KEYS "*"`
- [ ] FRED API key set (if using macro data): `echo $FRED_API_KEY`
- [ ] Scheduler method chosen and tested
- [ ] Logs directory exists and is writable: `ls -la logs/`
- [ ] Cron/systemd/etc. configured and tested
- [ ] Monitoring/alerting setup (optional but recommended)
- [ ] Backup plan documented (what to do if scheduler fails)

---

## 🚨 ALERT THRESHOLDS (Optional but Recommended)

Set up alerts if:
- Pipeline takes > 2 minutes
- Fewer than 1,000 rows ingested per day
- Features not updated in last 25 hours
- QuestDB disk usage > 80%
- Redis memory usage > 1 GB
- Pipeline fails 2+ times in 24 hours

---

## 📞 SUPPORT

If pipeline fails:
1. Check logs: `tail -50 logs/medallion.log`
2. Run diagnostic: `python run_daily_pipeline.py --once`
3. Check dependencies: `pip list | grep -E "schedule|pandas|redis"`
4. Verify services: `docker-compose ps`

For FRED data issues specifically:
- Verify API key: `echo $FRED_API_KEY`
- Check FRED website: https://fred.stlouisfed.org
- Try offline: Run with `--mode gold-only` to skip FRED

---

*Last Updated: May 13, 2026*
