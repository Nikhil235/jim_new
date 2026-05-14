# 📋 Production Operational Procedures
**Mini-Medallion Data Pipeline Operations**  
**Last Updated**: May 13, 2026  
**Status**: ✅ Ready for Production

---

## 🎯 Quick Start: Running the Scheduler in Production

### Option 1: Windows Task Scheduler (Recommended for Windows)

```powershell
# 1. Create batch script (e.g., run_scheduler.bat)
@echo off
cd C:\path\to\JIM_Latest
python -m venv .venv
call .venv\Scripts\activate.bat
python scripts/daily_scheduler.py
pause
```

**Then create a Scheduled Task:**
1. Open Task Scheduler (taskschd.msc)
2. Create Basic Task → "Mini-Medallion Pipeline"
3. Trigger: Daily at 05:50 UTC (before 06:00 start)
4. Action: Run batch script
5. Settings: Run with highest privileges, repeat every 1 day

### Option 2: Linux/macOS with Cron

```bash
# Edit crontab
crontab -e

# Add this line to run scheduler at 05:50 UTC daily
50 05 * * * cd /path/to/JIM_Latest && python scripts/daily_scheduler.py >> logs/scheduler.log 2>&1

# Or for background daemon (use nohup)
nohup python scripts/daily_scheduler.py > logs/scheduler.log 2>&1 &
```

### Option 3: Docker Container (Production Recommended)

```dockerfile
# Dockerfile.scheduler
FROM python:3.11-slim

WORKDIR /app
COPY requirements-merged.txt .
RUN pip install -r requirements-merged.txt

COPY . .

CMD ["python", "scripts/daily_scheduler.py"]
```

**Build and run:**
```bash
docker build -f Dockerfile.scheduler -t mini-medallion-scheduler .
docker run -d \
  --name scheduler \
  -v /path/to/data:/app/data \
  -v /path/to/logs:/app/logs \
  --network medallion-net \
  mini-medallion-scheduler
```

### Option 4: PM2 (Node.js Process Manager - Cross-Platform)

```bash
# Install PM2
npm install -g pm2

# Create ecosystem.config.js
cat > ecosystem.config.js << 'EOF'
module.exports = {
  apps: [{
    name: "pipeline-scheduler",
    script: "scripts/daily_scheduler.py",
    interpreter: "python",
    cwd: "/path/to/JIM_Latest",
    autorestart: true,
    max_memory_restart: "2G",
    error_file: "logs/scheduler-error.log",
    out_file: "logs/scheduler-out.log",
    log_date_format: "YYYY-MM-DD HH:mm:ss Z"
  }]
};
EOF

# Start scheduler
pm2 start ecosystem.config.js
pm2 save
pm2 startup
```

---

## 🔧 Daily Operations

### Starting the Pipeline

**Single run (manual testing):**
```bash
# Full pipeline
python scripts/daily_scheduler.py --once --mode full

# Specific mode
python scripts/daily_scheduler.py --once --mode gold-only
python scripts/daily_scheduler.py --once --mode macro-only
python scripts/daily_scheduler.py --once --mode features-only
python scripts/daily_scheduler.py --once --mode incremental
```

**Daemon mode (background):**
```bash
# Start daemon
python scripts/daily_scheduler.py

# Stop daemon (Ctrl+C or kill the process)
pkill -f daily_scheduler.py
```

**Via REST API:**
```bash
# Trigger pipeline via HTTP
curl -X POST http://localhost:8000/pipeline/run -H "Content-Type: application/json" -d '{"mode": "full"}'

# Check pipeline status
curl http://localhost:8000/health
```

### Monitoring Daily Execution

**Check health status file:**
```bash
# View latest health status
cat data/pipeline_health.json | jq .

# PowerShell
Get-Content data/pipeline_health.json | ConvertFrom-Json | Format-Table

# Watch for updates (Linux)
watch -n 5 'cat data/pipeline_health.json | jq .'
```

**Expected output:**
```json
{
  "full": {
    "status": "SUCCESS",
    "start_time": "2026-05-13T06:00:15",
    "end_time": "2026-05-13T06:02:18",
    "duration_sec": 123,
    "total_rows": 120164,
    "feature_count": 285,
    "steps": [...]
  },
  "last_updated": "2026-05-13T06:02:18.123456"
}
```

**Check logs:**
```bash
# View latest log entries
tail -50 logs/pipeline.log

# Watch logs in real-time
tail -f logs/pipeline.log

# Search for errors
grep ERROR logs/pipeline.log
grep FAILED logs/pipeline.log
```

### Verifying Data Freshness

```bash
# Check data files last modified time
ls -lrh data/processed/ | tail -10
ls -lrh data/features/ | tail -10

# PowerShell
Get-ChildItem data/processed/ -File | Sort-Object LastWriteTime -Descending | Select-Object Name, LastWriteTime | head -10
Get-ChildItem data/features/ -File | Sort-Object LastWriteTime -Descending | Select-Object Name, LastWriteTime | head -10

# Count recent records in QuestDB
curl -s "http://localhost:9000/?query=SELECT count() FROM gold_1d WHERE timestamp > now() - 1d" | jq .

# Check feature store Redis size
redis-cli INFO stats | grep used_memory_human
```

### Configuration Changes

**Update pipeline schedule:**
```yaml
# Edit configs/base.yaml
pipeline:
  schedule:
    daily_update_time: "06:00"      # UTC, London open
    macro_update_time: "14:00"      # UTC, US open
    # Features auto-schedule at 14:30
```

**Restart scheduler after config changes:**
```bash
# Stop current scheduler
pkill -f daily_scheduler.py

# Wait 10 seconds
sleep 10

# Start new scheduler with updated config
python scripts/daily_scheduler.py
```

**Enable/disable specific data sources:**
```yaml
# In configs/base.yaml
data:
  gold:
    enabled: true
  macro:
    enabled: true
    symbols:
      DXY: true
      VIX: true
  fred:
    enabled: true
  alternative:
    enabled: false  # Disable if not needed
```

---

## 🚨 Alert Thresholds & Triggers

### Set up alerting for critical issues:

**Pipeline failure:**
```
IF: pipeline status == "FAILED" or "CRASHED"
THEN: Send alert → Email/Slack/PagerDuty
```

**Data staleness:**
```
IF: last_updated < now() - 25 hours
THEN: Send alert → Email/Slack
```

**Data quality degradation:**
```
IF: rows_ingested < avg_rows * 0.8 (more than 20% drop)
THEN: Send alert → Email/Slack
```

**Storage threshold:**
```
IF: disk_usage > 80% of available
THEN: Send alert → Email/Slack
```

**Feature generation delay:**
```
IF: feature_generation_time > 90 seconds
THEN: Send alert → Slack (informational)
```

### Alert Destinations (Configure in `.env`)

```bash
# Email alerts
ALERT_EMAIL_ENABLED=true
ALERT_EMAIL_RECIPIENT=ops-team@company.com
ALERT_EMAIL_SMTP_HOST=smtp.gmail.com
ALERT_EMAIL_SMTP_PORT=587

# Slack alerts
ALERT_SLACK_ENABLED=true
ALERT_SLACK_WEBHOOK=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# PagerDuty alerts
ALERT_PAGERDUTY_ENABLED=false
ALERT_PAGERDUTY_KEY=your-integration-key
```

---

## 📊 Monitoring Dashboard Setup

### Prometheus Metrics

The scheduler exports these key metrics:

```promql
# Pipeline execution time (seconds)
medallion_pipeline_duration_seconds

# Rows ingested per run
medallion_pipeline_rows_ingested

# Features generated
medallion_pipeline_features_generated

# Pipeline success rate
medallion_pipeline_success_rate

# Step duration by step name
medallion_pipeline_step_duration_seconds{step="fetch_gold"}
```

**Prometheus scrape config** (already in `docker/prometheus.yml`):
```yaml
scrape_configs:
  - job_name: 'medallion-pipeline'
    static_configs:
      - targets: ['localhost:8000']
    scrape_interval: 5m
```

### Grafana Dashboard

**Create dashboard with these panels:**

1. **Pipeline Status** (Status indicator)
   - Query: `medallion_pipeline_status`
   - Refresh: Every 5 minutes

2. **Pipeline Duration** (Time-series graph)
   - Query: `medallion_pipeline_duration_seconds`
   - Alert: > 180 seconds

3. **Rows Ingested** (Bar chart)
   - Query: `medallion_pipeline_rows_ingested`
   - Alert: < 100K rows

4. **Features Generated** (Gauge)
   - Query: `medallion_pipeline_features_generated`
   - Expected: 280-290 features

5. **Step Breakdown** (Heatmap)
   - Query: `medallion_pipeline_step_duration_seconds`
   - Shows: Which steps are slow

6. **Data Freshness** (Timeline)
   - Query: Time since last update
   - Alert: > 25 hours

---

## 📝 Daily Checklist

**Each morning (before 07:00 UTC):**

- [ ] Check `data/pipeline_health.json` for successful run
- [ ] Verify row counts are within normal range (100K-150K)
- [ ] Confirm feature count is 280-290
- [ ] Check logs for any warnings or errors
- [ ] Verify data files were created/updated
- [ ] Monitor disk space (ensure >50 GB free)
- [ ] Check Prometheus/Grafana metrics are reporting

**Weekly review:**
- [ ] Analyze pipeline performance trends
- [ ] Check for any recurring errors
- [ ] Review data quality metrics
- [ ] Verify infrastructure health (QuestDB, Redis, MinIO)
- [ ] Update documentation if procedures changed

**Monthly maintenance:**
- [ ] Archive old logs (keep 3 months)
- [ ] Analyze storage growth and plan capacity
- [ ] Review and optimize slow steps
- [ ] Update API keys if expired
- [ ] Test disaster recovery procedures

---

## 🔄 Maintenance Tasks

### Backup Data

```bash
# Backup feature data
tar czf backups/features_$(date +%Y%m%d).tar.gz data/features/

# Backup QuestDB data
tar czf backups/questdb_$(date +%Y%m%d).tar.gz docker/volumes/questdb/

# Backup Redis (snapshot)
redis-cli BGSAVE
cp dump.rdb backups/redis_$(date +%Y%m%d).rdb

# Backup logs
tar czf backups/logs_$(date +%Y%m%d).tar.gz logs/
```

### Log Rotation

```bash
# Linux/macOS - add to crontab
0 2 * * 0 find /path/to/logs -name "*.log" -mtime +30 -delete

# PowerShell - run weekly
$logDir = "logs"
Get-ChildItem $logDir -Filter "*.log" -File | Where-Object {$_.LastWriteTime -lt (Get-Date).AddMonths(-1)} | Remove-Item
```

### Database Maintenance

```bash
# Vacuum QuestDB (remove deleted records)
curl "http://localhost:9000/?query=ALTER%20TABLE%20gold_1d%20VACUUM"

# Redis memory optimization
redis-cli MEMORY DOCTOR

# Clear stale Redis keys
redis-cli --scan --pattern "feature:*" | xargs redis-cli DEL

# Analyze parquet file sizes
du -sh data/processed/*.parquet
du -sh data/features/*.parquet
```

### Infrastructure Health Check

```bash
# Check all services are running
docker ps | grep medallion

# Verify QuestDB connectivity
python scripts/check_infrastructure.py

# Test API endpoints
curl -s http://localhost:8000/health | jq .

# Test data sources (API keys, network)
python -c "from src.ingestion import *; print('Connectivity OK')"
```

---

## 🆘 Quick Troubleshooting

### Scheduler not running

```bash
# Check if process is running
ps aux | grep daily_scheduler
pgrep -f daily_scheduler

# Check logs for startup errors
tail -50 logs/pipeline.log

# Verify Python and dependencies
python --version
pip list | grep -E "click|schedule|loguru"

# Try running manually first
python scripts/daily_scheduler.py --once --mode gold-only
```

### Pipeline failing

```bash
# Check data file permissions
ls -l data/processed/
chmod 755 data/processed/

# Verify data source connectivity
python -c "from src.ingestion.gold_fetcher import *; print(GoldFetcher().fetch_latest())"

# Check QuestDB/Redis connections
python scripts/check_infrastructure.py

# Check disk space
df -h | grep -E "^\/" | awk '{if ($5 > 80) print "WARNING: " $6 " is " $5 " full"}'
```

### High memory usage

```bash
# Monitor process memory
watch -n 2 'ps aux | grep python | grep -v grep'

# Check for memory leaks
python -m memory_profiler scripts/daily_scheduler.py

# Reduce batch size in config
# Edit configs/base.yaml: pipeline.batch_size = 1000 (instead of 5000)
```

### Slow pipeline execution

```bash
# Analyze step durations from health file
cat data/pipeline_health.json | jq '.full.steps | sort_by(.duration) | reverse'

# Check CPU/disk I/O
top
iotop

# Optimize slowest steps:
# 1. write_storage - Consider async writes
# 2. store_features - Consider batch compression
```

---

## 📞 Support & Escalation

**Level 1 (Automated Recovery):**
- Retry logic: Automatic retry with exponential backoff
- Fallback: Use parquet storage if QuestDB/Redis offline
- Recovery: Restart daemon if crash detected

**Level 2 (Manual Investigation):**
- Check health file and logs
- Run manual pipeline test
- Verify infrastructure connectivity
- Review configuration settings

**Level 3 (Escalation):**
- If level 2 fails, escalate to:
  - Infrastructure team (QuestDB/Redis/MinIO)
  - Data engineering team (data source issues)
  - Platform team (deployment/scaling)

**Contact:**
- Slack: #medallion-alerts
- Email: ops-medallion@company.com
- PagerDuty: medallion-oncall

---

## 📚 Related Documentation

- [SCHEDULER_TEST_REPORT.md](SCHEDULER_TEST_REPORT.md) - Test results and validation
- [PRODUCTION_MONITORING.md](PRODUCTION_MONITORING.md) - Advanced monitoring setup
- [TROUBLESHOOTING_GUIDE.md](TROUBLESHOOTING_GUIDE.md) - Detailed troubleshooting procedures
- [PROJECT_STATUS.md](PROJECT_STATUS.md) - Current project status
- [QUICK_START_PIPELINE.md](QUICK_START_PIPELINE.md) - Quick pipeline setup

---

**Status**: ✅ Ready for production deployment  
**Last Tested**: May 13, 2026  
**Next Review**: After 7 days of live operation
