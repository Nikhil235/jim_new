# 📊 Production Monitoring Setup
**Mini-Medallion Data Pipeline Monitoring**  
**Last Updated**: May 13, 2026  
**Status**: ✅ Ready to Deploy

---

## 🎯 Monitoring Overview

This document covers setting up comprehensive monitoring for the Mini-Medallion data pipeline including:
- Health status monitoring
- Performance metrics collection
- Real-time alerting
- Grafana dashboards
- Logging and retention

---

## 📈 Metrics & KPIs

### Critical Metrics (Monitor Constantly)

| Metric | Target | Alert | Source |
|--------|--------|-------|--------|
| **Pipeline Success Rate** | 99%+ | < 95% | Health file |
| **Data Freshness** | < 24h | > 25h | Last update time |
| **Rows Ingested** | 100K-150K | < 80K or > 200K | Health file |
| **Pipeline Duration** | 120-150s | > 180s | Health file |
| **Feature Count** | 280-290 | < 270 or > 300 | Health file |
| **Storage Available** | > 50% | < 20% | Disk usage |
| **Database Connectivity** | 100% | Any failure | QuestDB/Redis |

### Performance Metrics (Monitor Trends)

| Metric | Unit | Baseline | Trend Alert |
|--------|------|----------|------------|
| Fetch gold time | seconds | 2.5 | > 5.0 |
| Fetch macro time | seconds | 1.5 | > 3.0 |
| Fetch FRED time | seconds | 4.0 | > 8.0 |
| Write storage time | seconds | 56 | > 90 |
| Generate features time | seconds | 50 | > 75 |
| CPU usage | % | 40-60 | > 85 for 2min |
| Memory usage | MB | 800-1200 | > 2000 |
| Disk I/O | IOPS | 100-200 | > 500 |

---

## 🔌 Health Monitoring System

### Health File Monitoring

The scheduler writes a health file at `data/pipeline_health.json` after each run.

**Parse health file for monitoring:**

```python
# health_monitor.py - Simple health checker
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

HEALTH_FILE = Path("data/pipeline_health.json")

def check_health():
    if not HEALTH_FILE.exists():
        print("CRITICAL: Health file missing")
        return False
    
    try:
        health = json.loads(HEALTH_FILE.read_text())
    except json.JSONDecodeError:
        print("CRITICAL: Health file corrupted")
        return False
    
    last_update = datetime.fromisoformat(health.get("last_updated", ""))
    time_since_update = datetime.utcnow() - last_update
    
    # Check freshness (< 25 hours)
    if time_since_update > timedelta(hours=25):
        print(f"WARNING: Data is {time_since_update.total_seconds()/3600:.1f} hours old")
        return False
    
    # Check latest run status
    latest_mode = max(health.items(), key=lambda x: x[1].get("start_time", ""))
    status = latest_mode[1].get("status")
    if status != "SUCCESS":
        print(f"CRITICAL: Last pipeline run failed with status: {status}")
        return False
    
    # Check row counts
    rows = latest_mode[1].get("total_rows", 0)
    if rows < 80000 or rows > 200000:
        print(f"WARNING: Unexpected row count: {rows}")
        return False
    
    print("OK: Pipeline health is good")
    return True

if __name__ == "__main__":
    sys.exit(0 if check_health() else 1)
```

**Run as health check script:**
```bash
# Nagios/Icinga compatible
python health_monitor.py
echo $?  # Returns 0 for OK, 1 for critical

# Cron job - alert if fails
0 8 * * * python health_monitor.py || mail -s "ALERT: Pipeline health check failed" ops@company.com
```

### Prometheus Integration

**Metrics exported by pipeline:**

```python
# src/ingestion/metrics_exporter.py (already implemented)
from prometheus_client import Counter, Gauge, Histogram, start_http_server

# Counters
pipeline_runs = Counter('medallion_pipeline_runs_total', 'Total pipeline runs', ['mode', 'status'])

# Gauges
pipeline_rows = Gauge('medallion_pipeline_rows_ingested', 'Rows ingested in last run', ['mode'])
pipeline_features = Gauge('medallion_pipeline_features_generated', 'Features generated')
data_freshness = Gauge('medallion_data_freshness_hours', 'Hours since last data update')

# Histograms
pipeline_duration = Histogram('medallion_pipeline_duration_seconds', 'Pipeline execution time', ['mode'])
step_duration = Histogram('medallion_pipeline_step_duration_seconds', 'Step execution time', ['step'])
```

**Scrape configuration** (docker/prometheus.yml):
```yaml
global:
  scrape_interval: 5m
  evaluation_interval: 1m

scrape_configs:
  - job_name: 'medallion-pipeline'
    metrics_path: '/metrics'
    static_configs:
      - targets: ['localhost:8000']  # Where metrics are exported

  - job_name: 'medallion-docker'
    static_configs:
      - targets: ['localhost:9323']  # Docker metrics

  - job_name: 'questdb'
    static_configs:
      - targets: ['localhost:9090']  # QuestDB Prometheus endpoint
```

**Access Prometheus UI:**
```
http://localhost:9090/graph
```

**Useful queries:**
```promql
# Pipeline success rate (last 7 days)
increase(medallion_pipeline_runs_total{status="success"}[7d]) / increase(medallion_pipeline_runs_total[7d])

# Average pipeline duration by mode
avg(rate(medallion_pipeline_duration_seconds_sum[5m]) / rate(medallion_pipeline_duration_seconds_count[5m])) by (mode)

# Current data freshness
medallion_data_freshness_hours

# Step performance (slowest first)
topk(5, medallion_pipeline_step_duration_seconds_bucket)
```

---

## 📊 Grafana Dashboard

### Dashboard Setup

**Access Grafana:**
```
http://localhost:3000
Username: admin
Password: medallion
```

**Add Prometheus data source:**
1. Configuration → Data Sources → Add Prometheus
2. URL: `http://localhost:9090`
3. Test & Save

### Create Dashboards

**Dashboard 1: Pipeline Overview (for operations team)**

```json
{
  "dashboard": {
    "title": "Mini-Medallion Pipeline Overview",
    "panels": [
      {
        "title": "Pipeline Status",
        "type": "stat",
        "targets": [{"expr": "medallion_pipeline_status"}],
        "thresholds": [0, 1],
        "colors": ["red", "green"]
      },
      {
        "title": "Rows Ingested",
        "type": "gauge",
        "targets": [{"expr": "medallion_pipeline_rows_ingested"}],
        "min": 0,
        "max": 200000,
        "thresholds": [80000, 100000, 150000]
      },
      {
        "title": "Pipeline Duration",
        "type": "timeseries",
        "targets": [{"expr": "medallion_pipeline_duration_seconds"}],
        "alert": "duration > 180s"
      },
      {
        "title": "Feature Count",
        "type": "gauge",
        "targets": [{"expr": "medallion_pipeline_features_generated"}],
        "min": 250,
        "max": 300
      },
      {
        "title": "Data Freshness",
        "type": "stat",
        "targets": [{"expr": "medallion_data_freshness_hours"}],
        "unit": "hours",
        "thresholds": [0, 24, 25]
      },
      {
        "title": "Step Performance",
        "type": "heatmap",
        "targets": [{"expr": "medallion_pipeline_step_duration_seconds"}]
      }
    ]
  }
}
```

**Dashboard 2: Performance Analysis (for engineering team)**

```json
{
  "panels": [
    {
      "title": "Pipeline Duration Trend",
      "type": "timeseries",
      "targets": [
        {"expr": "avg(medallion_pipeline_duration_seconds) by (mode)"}
      ]
    },
    {
      "title": "Success Rate",
      "type": "timeseries",
      "targets": [
        {
          "expr": "increase(medallion_pipeline_runs_total{status=\"success\"}[1h]) / increase(medallion_pipeline_runs_total[1h])"
        }
      ]
    },
    {
      "title": "Step Breakdown",
      "type": "piechart",
      "targets": [
        {"expr": "avg(medallion_pipeline_step_duration_seconds_sum) by (step)"}
      ]
    },
    {
      "title": "Resource Usage",
      "type": "timeseries",
      "targets": [
        {"expr": "container_memory_usage_bytes{name=\"medallion\"}"},
        {"expr": "rate(container_cpu_usage_seconds_total{name=\"medallion\"}[5m])"}
      ]
    }
  ]
}
```

### Dashboard 3: Infrastructure Health (for devops team)

```json
{
  "panels": [
    {
      "title": "Disk Space Usage",
      "type": "gauge",
      "targets": [
        {"expr": "node_filesystem_avail_bytes{mountpoint=\"/\"} / node_filesystem_size_bytes{mountpoint=\"/\"} * 100"}
      ]
    },
    {
      "title": "Database Connectivity",
      "type": "stat",
      "targets": [
        {"expr": "up{job=\"questdb\"}"}
      ]
    },
    {
      "title": "Redis Memory Usage",
      "type": "gauge",
      "targets": [
        {"expr": "redis_memory_used_bytes / 1024 / 1024"}
      ]
    },
    {
      "title": "Container Status",
      "type": "table",
      "targets": [
        {"expr": "up"}
      ]
    }
  ]
}
```

---

## 🚨 Alerting Setup

### Alert Rules (prometheus rules)

Create `docker/prometheus_rules.yml`:

```yaml
groups:
  - name: medallion_alerts
    interval: 1m
    rules:
      # Pipeline failed
      - alert: PipelineFailed
        expr: medallion_pipeline_status != 1
        for: 5m
        annotations:
          summary: "Pipeline failed"
          action: "Check logs and restart scheduler"

      # Data is stale
      - alert: DataStale
        expr: medallion_data_freshness_hours > 24
        for: 10m
        annotations:
          summary: "Data is stale ({{ $value }} hours old)"
          action: "Check data sources and pipeline logs"

      # Low row count
      - alert: LowRowCount
        expr: medallion_pipeline_rows_ingested < 80000
        for: 5m
        annotations:
          summary: "Ingested only {{ $value }} rows (expected 100K+)"
          action: "Check data source connectivity"

      # Pipeline slow
      - alert: PipelineSlow
        expr: medallion_pipeline_duration_seconds > 180
        for: 10m
        annotations:
          summary: "Pipeline took {{ $value }}s (target: 120-150s)"
          action: "Check system performance and optimize slow steps"

      # Disk nearly full
      - alert: DiskSpaceWarning
        expr: node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"} < 0.2
        for: 5m
        annotations:
          summary: "Disk space critical"
          action: "Clean up old data and logs"

      # Database down
      - alert: DatabaseDown
        expr: up{job="questdb"} == 0
        for: 1m
        annotations:
          summary: "QuestDB is offline"
          action: "Restart QuestDB service"
```

### Alert Receivers (Alert Manager)

Configure `docker/alertmanager.yml`:

```yaml
global:
  resolve_timeout: 5m

route:
  receiver: 'default'
  group_by: ['alertname', 'instance']
  group_wait: 1m
  group_interval: 5m
  repeat_interval: 1h
  routes:
    - match:
        severity: critical
      receiver: 'pagerduty'
      repeat_interval: 5m
    - match:
        severity: warning
      receiver: 'slack'

receivers:
  - name: 'default'
    email_configs:
      - to: 'ops@company.com'
        from: 'alerts@company.com'
        smarthost: 'smtp.gmail.com:587'
        auth_username: 'alerts@company.com'
        auth_password: 'password'

  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: 'YOUR-PAGERDUTY-KEY'

  - name: 'slack'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
        channel: '#medallion-alerts'
        title: 'Medallion Alert'
        text: '{{ .GroupLabels.alertname }}'
```

---

## 📋 Monitoring Checklist

### Daily (Automated)

- [ ] Health file check runs at 08:00 UTC
- [ ] Alerts sent if data > 24h old
- [ ] Pipeline success rate tracked
- [ ] Row counts within normal range
- [ ] Prometheus metrics collected every 5 minutes

### Weekly (Manual Review)

- [ ] Review Grafana dashboard for trends
- [ ] Check for recurring slow steps
- [ ] Analyze alert frequency and false positives
- [ ] Verify backup completeness
- [ ] Review resource usage trends

### Monthly (Deep Analysis)

- [ ] Performance optimization opportunities
- [ ] Capacity planning for next quarter
- [ ] Update alerting thresholds if needed
- [ ] Review and clean up logs (>3 months)
- [ ] Infrastructure maintenance window planning

---

## 📚 Monitoring Tools

### Command-Line Monitoring

```bash
# Watch health file in real-time
watch -n 5 'cat data/pipeline_health.json | jq . | tail -20'

# Monitor logs for errors
tail -f logs/pipeline.log | grep -E "ERROR|FAILED|WARNING"

# Check system resources while pipeline runs
watch -n 1 'ps aux | grep -E "python|scheduler"'

# Monitor database connections
watch -n 5 'redis-cli INFO stats | grep connected_clients'

# Check parquet file sizes growing
watch -n 60 'du -sh data/features/*.parquet | tail -5'
```

### Docker Monitoring

```bash
# Check container status
docker ps | grep medallion

# View container logs
docker logs -f medallion-scheduler

# Monitor container resource usage
docker stats medallion-scheduler

# Inspect container metrics
docker inspect medallion-scheduler | jq '.State'
```

### Systemd Journal Monitoring (Linux)

```bash
# View service logs
journalctl -u medallion-scheduler -f

# Recent errors
journalctl -u medallion-scheduler -p err -n 20

# Last 1 hour of logs
journalctl -u medallion-scheduler --since "1 hour ago"
```

---

## 🔗 Related Documentation

- [OPERATIONAL_PROCEDURES.md](OPERATIONAL_PROCEDURES.md) - Daily operations guide
- [TROUBLESHOOTING_GUIDE.md](TROUBLESHOOTING_GUIDE.md) - Troubleshooting procedures
- [SCHEDULER_TEST_REPORT.md](SCHEDULER_TEST_REPORT.md) - Test results
- [PROJECT_STATUS.md](PROJECT_STATUS.md) - Current status

---

**Status**: ✅ Ready to deploy  
**Last Updated**: May 13, 2026  
**Next Review**: After first 7 days of monitoring
