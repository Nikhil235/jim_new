# Operations Runbooks

**Version**: 1.0  
**Last Updated**: May 14, 2026  
**Status**: ACTIVE

---

## Table of Contents

1. [Daily Startup Procedures](#daily-startup)
2. [Incident Response](#incidents)
3. [Model Monitoring & Retraining](#model-ops)
4. [Data Quality Issues](#data-quality)
5. [Performance Troubleshooting](#performance)
6. [Disaster Recovery](#disaster-recovery)
7. [Maintenance Windows](#maintenance)

---

## Daily Startup Procedures {#daily-startup}

### Morning Checklist (Before 08:00 UTC)

**Step 1: Infrastructure Verification (5 min)**
```bash
# Check all services are running
docker ps | grep -E "questdb|redis|minio|prometheus|grafana"

# Verify databases
python scripts/check_infrastructure.py
# Expected output: All systems GREEN

# Check disk space
df -h /data
# Should be < 80% used
```

**Step 2: Data Pipeline Check (10 min)**
```bash
# Review yesterday's pipeline run
tail -100 logs/pipeline_$(date -d yesterday +%Y-%m-%d).log

# Check for errors
grep -i "error\|failed\|exception" logs/pipeline_*.log

# Verify data completeness
python scripts/check_data_quality.py --date yesterday
# Expected: >99.5% completeness
```

**Step 3: Model Status Check (5 min)**
```bash
# Get model performance summary
python -c "
from src.models.performance_monitor import get_model_performance_monitor
monitor = get_model_performance_monitor()
print(monitor.generate_daily_report())
"

# Alert if any model degraded
# Check: degradation_threshold = 10%
```

**Step 4: System Health Report (5 min)**
```bash
# Generate health report
python -c "
from src.infrastructure.health_monitor import get_health_monitor
monitor = get_health_monitor()
print(monitor.generate_health_report('text'))
" | tee logs/health_$(date +%Y-%m-%d_%H:%M).log

# Verify SLA compliance
# Expected: >99.9% uptime
```

**If any checks FAIL**: Follow [Incident Response](#incidents)

### Pre-Market Startup (1 hour before trading)

```bash
# Verify market data feeds are live
python -c "from src.ingestion.gold_fetcher import GoldDataFetcher; f = GoldDataFetcher(); print(f.fetch_latest())"

# Test signal generation
python -c "from src.models.ensemble import EnsembleModel; m = EnsembleModel(); print('Model OK')"

# Test order execution
python -c "from src.execution.engine import ExecutionEngine; e = ExecutionEngine(); print('Execution OK')"

# Final safety check
python scripts/pre_market_checklist.py
# Expected: READY FOR TRADING
```

---

## Incident Response {#incidents}

### Template: Incident Investigation

**Time Reported**: [TIME]  
**Reported By**: [PERSON]  
**Severity**: 🔴 CRITICAL / 🟠 HIGH / 🟡 MEDIUM / 🟢 LOW

### Triage (5 minutes)

1. **Identify affected component**
   - Database? API? Models? Execution?
   - Check logs: `tail -50 logs/*.log`
   
2. **Determine impact**
   - Trading active? Backtest running? Analysis only?
   - Scope: Single trade? Entire system?
   
3. **Check recent changes**
   - Any deployments in last 24h?
   - Model updates? Data changes?

### Common Issues & Solutions

#### Issue 1: Database Connection Error

**Symptoms**: "Cannot connect to QuestDB"

```bash
# Verify QuestDB is running
docker ps | grep questdb

# If not running:
docker-compose up -d questdb

# Check QuestDB logs
docker logs questdb | tail -20

# Verify connectivity
python -c "import psycopg2; conn = psycopg2.connect('localhost', 9009); print('OK')"

# If still failing:
# Step 1: Stop container
docker stop questdb

# Step 2: Restart
docker-compose up -d questdb

# Step 3: Wait 30 seconds for startup
sleep 30

# Step 4: Verify
python scripts/check_infrastructure.py
```

**Resolution Criteria**: `check_infrastructure.py` returns GREEN

#### Issue 2: Model Performance Degradation

**Symptoms**: "Win rate dropped 15% below baseline"

```bash
# Check latest model metrics
python -c "
from src.models.performance_monitor import get_model_performance_monitor
m = get_model_performance_monitor()
for model in ['wavelet', 'hmm', 'lstm', 'tft', 'genetic', 'ensemble']:
    is_degraded, reason = m.detect_degradation(model)
    print(f'{model}: {\"DEGRADED\" if is_degraded else \"OK\"} - {reason}')
"

# Check market conditions
python -c "
from src.models.hmm import HMMRegimeDetector
hmm = HMMRegimeDetector()
regime = hmm.predict_regime(data)
print(f'Current regime: {regime}')
"

# If degradation confirmed:
# Option 1: Disable model
python -c "
from src.models.performance_monitor import get_model_performance_monitor
m = get_model_performance_monitor()
m.disable_model('wavelet', 'Performance degradation detected')
"

# Option 2: Check for data quality issues
python scripts/check_data_quality.py

# Option 3: Retrain model
python scripts/retrain_model.py --model wavelet --lookback 252
```

**Resolution Criteria**: Win rate recovers or model disabled

#### Issue 3: High Latency

**Symptoms**: "Orders executing 500ms+ after signal"

```bash
# Identify slow component
python -c "
from src.infrastructure.health_monitor import get_health_monitor
h = get_health_monitor()
for endpoint in ['database', 'cache', 'api']:
    h.measure_endpoint_latency(endpoint, num_samples=100)
    print(h.latency_metrics[endpoint])
"

# If database slow:
# - Check QuestDB CPU/memory
docker stats questdb

# If redis slow:
# - Check Redis memory usage
redis-cli info memory

# If API slow:
# - Check Python process load
ps aux | grep python

# Resolution: Scale resources or investigate query efficiency
```

**Resolution Criteria**: Latency < 100ms for market updates

#### Issue 4: Data Quality Problem

**Symptoms**: "Null values in features", "Suspicious price spike"

```bash
# Get detailed quality report
python scripts/check_data_quality.py --detailed

# Check specific date/symbol
python -c "
from src.ingestion.data_quality import DataQualityMonitor
dq = DataQualityMonitor()
report = dq.validate(symbol='XAU/USD', date='2026-05-14')
print(report)
"

# If outliers detected:
# - Check raw source data (Yahoo, FRED, etc.)
# - Mark as suspect and exclude from trading
python scripts/mark_bad_data.py --date 2026-05-14 --reason 'outlier_detected'

# Re-run pipeline if needed
python run_daily_pipeline.py --date 2026-05-14 --force-rerun
```

**Resolution Criteria**: Data completeness >99.5%, no null values in trading window

### Escalation Path

| Severity | Action | Escalate To | Time |
|----------|--------|-------------|------|
| CRITICAL | Disable trading immediately | CTO, Operations Lead | Now |
| HIGH | Investigate root cause | Engineering Team | 5 min |
| MEDIUM | Schedule fix, continue monitoring | Team Lead | 1 hour |
| LOW | Track for next review | Engineering | Next week |

---

## Model Monitoring & Retraining {#model-ops}

### Weekly Model Review (Monday 09:00 UTC)

```bash
# Generate performance report for past week
python -c "
from src.models.performance_monitor import get_model_performance_monitor
m = get_model_performance_monitor()
for model in m.model_names:
    scorecard = m.scorecards[model]
    print(m.generate_model_scorecard(model))
    print()
"

# Check for degradation across all models
python -c "
from src.models.performance_monitor import get_model_performance_monitor
m = get_model_performance_monitor()
degraded = [name for name in m.model_names if m.detect_degradation(name)[0]]
if degraded:
    print(f'ALERT: Degraded models: {degraded}')
else:
    print('All models performing normally')
"

# Decision tree:
# - Degradation detected? → Schedule retrain
# - Win rate declining trend? → Prepare feature updates
# - Regime shift? → Test model performance in new regime
```

### Retraining Procedure

**When to retrain**:
- Weekly (standard)
- After major market events
- When degradation detected
- When new features added

```bash
# Step 1: Prepare training data
python scripts/prepare_training_data.py \
  --lookback 252 \
  --test_split 0.2 \
  --output training_data.pkl

# Step 2: Retrain model
python scripts/retrain_model.py \
  --model wavelet \
  --data training_data.pkl \
  --output wavelet_v2.pkl

# Step 3: A/B test
python scripts/run_ab_test.py \
  --model_old wavelet_v1.pkl \
  --model_new wavelet_v2.pkl \
  --lookback 30  # Test on last 30 days

# Step 4: Review A/B test results
# Expected: No significant degradation in v2

# Step 5: Deploy (if A/B passes)
python scripts/deploy_model.py \
  --model wavelet \
  --version v2.pkl \
  --strategy gradual \
  --phase_in_days 7

# Phase-in schedule:
# Days 1-2: 10% of trades
# Days 3-4: 25% of trades
# Days 5-6: 50% of trades
# Day 7: 100% of trades

# Step 6: Monitor performance
# - Check daily win rates
# - Monitor for any degradation
# - Rollback if issues detected
```

---

## Data Quality Issues {#data-quality}

### Daily Quality Checks

```bash
# Completeness check
python -c "
from src.ingestion.data_quality import DataQualityMonitor
dq = DataQualityMonitor()
report = dq.check_completeness()
assert report['percent_complete'] > 99.5
"

# Outlier detection
python -c "
from src.ingestion.data_quality import DataQualityMonitor
dq = DataQualityMonitor()
outliers = dq.detect_outliers(z_score_threshold=3.0)
assert len(outliers) < 5
"

# Null value check
python -c "
from src.ingestion.data_quality import DataQualityMonitor
dq = DataQualityMonitor()
nulls = dq.check_nulls()
assert sum(nulls.values()) == 0
"
```

### If Quality Issues Detected

```bash
# 1. Identify source
python scripts/trace_bad_data.py --date 2026-05-14

# 2. Check source feeds
# - Gold price: Check Yahoo Finance, alternative sources
# - Macro: Check FRED, Yahoo Finance
# - Alternative: Check data providers

# 3. Mark bad data
python scripts/mark_bad_data.py \
  --date 2026-05-14 \
  --symbol XAU/USD \
  --reason 'source_feed_error'

# 4. Re-fetch data
python scripts/refetch_data.py \
  --date 2026-05-14 \
  --symbol XAU/USD \
  --sources alternative

# 5. Validate fixes
python scripts/check_data_quality.py --date 2026-05-14
```

---

## Performance Troubleshooting {#performance}

### If System is Slow

```bash
# 1. Identify bottleneck
python scripts/profile_system.py

# Output example:
# - Database query: 400ms (TOO SLOW)
# - Feature computation: 50ms
# - Signal generation: 30ms
# - Execution: 20ms

# 2. Database performance
# Check slow queries
python -c "
from src.ingestion.questdb_writer import QuestDBWriter
w = QuestDBWriter()
slow_queries = w.get_slow_queries(threshold_ms=100)
for q in slow_queries:
    print(q)
"

# Add indexes if needed
python scripts/optimize_database.py --action add_indexes

# 3. Feature performance
# Profile feature computation
python scripts/profile_features.py
# Identify which features are slow

# 4. Cache optimization
# Check Redis memory
redis-cli info memory

# Increase cache if needed
docker-compose down
# Edit docker-compose.yml to increase Redis memory
docker-compose up -d redis

# 5. CPU bottleneck
# Check if CPU-bound (GPU acceleration?)
python -c "
from src.utils.gpu import get_dataframe_engine
print('Using GPU-acceleration') if 'cudf' in str(get_dataframe_engine()) else print('Using CPU')
"
```

---

## Disaster Recovery {#disaster-recovery}

### RTO/RPO Targets

- **RTO** (Recovery Time Objective): 4 hours
- **RPO** (Recovery Point Objective): 24 hours

### Backup Verification (Monthly)

```bash
# Test data restoration
python scripts/test_backup_restore.py \
  --backup_date $(date -d '30 days ago' +%Y-%m-%d) \
  --test_data sample_trades.pkl

# Expected: Successfully restored data within 1 hour

# Generate report
python scripts/generate_disaster_recovery_report.py
```

### Disaster Recovery Procedure (If Data Loss)

```bash
# 1. Stop all trading immediately
python scripts/stop_trading.py --reason 'data_loss_detected'

# 2. Assess damage
python scripts/assess_damage.py

# 3. Restore from backup
python scripts/restore_from_backup.py \
  --backup_type questdb \
  --date 2026-05-13  # Last known good date

# 4. Verify restored data
python scripts/verify_restored_data.py

# 5. Audit transaction log
python scripts/audit_transaction_log.py

# 6. Resume trading
python scripts/resume_trading.py --mode paper  # Start in paper mode

# 7. Monitor closely for 24 hours
```

---

## Maintenance Windows {#maintenance}

### Scheduled Maintenance (Sundays 02:00-04:00 UTC)

**Do NOT schedule trading during this window**

```bash
# 1. Backup data
docker exec questdb tar czf /backup/questdb_$(date +%Y-%m-%d).tar.gz /var/lib/questdb

# 2. Update containers
docker-compose pull
docker-compose up -d

# 3. Run migrations (if needed)
python scripts/run_migrations.py

# 4. Verify all services
python scripts/check_infrastructure.py

# 5. Restore backup if issues
docker-compose down
# Restore from backup
docker-compose up -d
```

---

## Emergency Contacts

| Role | Name | Phone | Email |
|------|------|-------|-------|
| Operations Lead | [Name] | +1-XXX-XXX-XXXX | ops@company.com |
| CTO | [Name] | +1-XXX-XXX-XXXX | cto@company.com |
| Database Admin | [Name] | +1-XXX-XXX-XXXX | dba@company.com |
| Data Lead | [Name] | +1-XXX-XXX-XXXX | data@company.com |

---

**Document Version**: 1.0  
**Last Updated**: May 14, 2026  
**Next Review**: June 14, 2026
