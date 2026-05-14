# Data Retention & Lifecycle Policy

**Effective Date**: May 14, 2026  
**Status**: ACTIVE  
**Review Frequency**: Quarterly

---

## Executive Summary

This document defines the data retention, archival, and purge policies for Mini-Medallion. The policy balances operational efficiency (keeping recent data hot), analysis capability (warm historical data), and compliance (cold archival).

**Key Principle**: 3-Tier Data Lifecycle
- **Hot**: Current and recent data (fast, expensive storage)
- **Warm**: Historical data for analysis (slower, medium cost)
- **Cold**: Archived compliance data (slowest, lowest cost)

---

## Data Classifications

### Market Data (Gold Prices)
- **Type**: OHLCV candles from multiple sources
- **Volume**: ~1 row/day (360 rows/year)
- **Lifecycle**:
  - **Hot** (QuestDB): 90 days - Active trading analysis
  - **Warm** (MinIO): 300 days - Backtesting, analysis
  - **Cold** (S3 Glacier): 7 years - Compliance, archival
  - **Purge**: After 7 years

### Feature Data (140+ features)
- **Type**: Computed features from market data
- **Volume**: ~140 features/day
- **Lifecycle**:
  - **Hot** (Redis): 30 days - Model inference
  - **Warm** (MinIO): 180 days - Feature analysis, retraining
  - **Cold** (S3 Glacier): 3 years - Compliance
  - **Purge**: After 3 years

### Trade Records
- **Type**: Trade execution, fills, exits
- **Volume**: ~50-500 trades/month
- **Lifecycle**:
  - **Hot** (Database): 60 days - Live P&L tracking
  - **Warm** (MinIO): 1 year - Performance analysis
  - **Cold** (Glacier): 7 years - Regulatory compliance
  - **Purge**: After 7 years

### Model Metadata
- **Type**: Model versions, hyperparameters, performance
- **Volume**: ~1 record/week per model (6 models)
- **Lifecycle**:
  - **Hot** (Database): 90 days - Current model versions
  - **Warm** (MinIO): 2 years - Model history, reversion
  - **Cold** (Glacier): Indefinite - Archive
  - **Purge**: Never (keep indefinitely)

### Log Files
- **Type**: Application logs, API logs, error logs
- **Volume**: ~1GB/month (depends on trade frequency)
- **Lifecycle**:
  - **Hot** (Filesystem): 30 days - Current troubleshooting
  - **Warm** (S3): 90 days - Archive, analysis
  - **Purge**: After 90 days

### Reference Data
- **Type**: Macro data, alternative data, risk scenarios
- **Volume**: Varies by source
- **Lifecycle**:
  - **Hot** (Cache): Current values
  - **Warm** (Database): 5 years
  - **Cold** (Glacier): Indefinite
  - **Purge**: Never

---

## Retention Policy by Storage Tier

### QuestDB (Hot Storage)
| Data Type | Retention | Rationale |
|-----------|-----------|-----------|
| Market Data | 90 days | Active trading window |
| Trade Records | 60 days | Current P&L tracking |
| Regime Data | 30 days | Volatility changes |
| Feature Cache | 30 days | Model inference |

**Action**: Automatic archival to MinIO when exceeding retention  
**Frequency**: Daily at 02:00 UTC  
**Verification**: Checksums before deletion

### Redis (Hot Cache)
| Data Type | Retention | Rationale |
|-----------|-----------|-----------|
| Current Features | 1 day | Next inference |
| Regime Status | 1 day | Pattern stability |
| Price Cache | 1 hour | Current orders |

**Action**: Automatic expiration (TTL)  
**Frequency**: Real-time (background)  
**Verification**: Cache hit/miss ratios

### MinIO (Warm Storage)
| Data Type | Retention | Rationale |
|-----------|-----------|-----------|
| Market Data | 300 days | Backtesting |
| Trade Records | 1 year | Performance analysis |
| Features | 180 days | Model retraining |
| Logs | 90 days | Incident analysis |

**Action**: Automatic archival to Glacier when exceeding retention  
**Frequency**: Weekly on Sundays at 03:00 UTC  
**Verification**: Redundancy checksums

### S3 Glacier (Cold Storage)
| Data Type | Retention | Rationale |
|-----------|-----------|-----------|
| Market Data | 7 years | Regulatory compliance |
| Trade Records | 7 years | Compliance, audit trail |
| Features | 3 years | Historical analysis |
| Models | Indefinite | Archive, history |

**Action**: Archive only (no deletion)  
**Frequency**: Monthly on 1st at 04:00 UTC  
**Verification**: Monthly inventory audit

---

## Archival Procedures

### Automated Archival Pipeline
```python
# Daily at 02:00 UTC
1. Query QuestDB for data older than retention
2. Export to Parquet (compressed)
3. Calculate SHA256 checksum
4. Upload to MinIO
5. Verify upload (checksum match)
6. Delete from QuestDB
7. Log archival event with timestamp
8. Alert on failures
```

### Manual Archival (on demand)
```bash
# Archive specific date range
python scripts/manual_archive.py \
  --data-type market_data \
  --start-date 2024-01-01 \
  --end-date 2024-01-31 \
  --destination minIO
```

---

## Compliance Requirements

### Regulatory Retention
- **Trade Records**: 7 years (SEC, FINRA requirement)
- **Audit Trail**: 7 years (regulatory compliance)
- **Market Data**: 7 years (reference data)
- **Models**: Indefinite (potential justification/audit)

### Data Security
- **Encryption at Rest**: AES-256 for all archived data
- **Encryption in Transit**: TLS 1.3 for uploads
- **Access Control**: IAM roles for data access
- **Audit Trail**: All access logged and timestamped

### Disaster Recovery
- **Backup Frequency**: Daily
- **RPO (Recovery Point Objective)**: 24 hours
- **RTO (Recovery Time Objective)**: 4 hours
- **Cross-Region Replication**: MinIO to secondary S3 bucket

---

## Cost Optimization

### Storage Cost Breakdown (Annual)
| Tier | Cost | Ratio | Typical Volume |
|------|------|-------|----------------|
| QuestDB (Hot) | $5,000 | 100% | ~15 GB |
| MinIO (Warm) | $300 | 6% | ~100 GB |
| Glacier (Cold) | $100 | 2% | ~500 GB |
| **Total** | **$5,400** | - | ~615 GB |

### Cost Optimization Strategies
1. **Compression**: Parquet (4:1) for archived data
2. **Tiering**: Hot → Warm → Cold based on age
3. **Purging**: Delete non-compliance data after retention
4. **Deduplication**: Identify and remove duplicate trades
5. **Frequency**: Daily archival (vs manual periodic)

---

## Monitoring & Auditing

### Daily Health Checks
```bash
# Run daily at 05:00 UTC
- QuestDB: Check data age, alert if >90 days
- MinIO: Check bucket size, growth rate
- Glacier: Verify archive completeness
- Redis: Check TTL expiry rate
```

### Monthly Audit Report
```
Report: Data Retention Audit - {Month}
- QuestDB entries: {count}
- MinIO GB: {size}
- Glacier archives: {count}
- Archival success rate: {pct}%
- Failed archival attempts: {count}
- Data integrity issues: {count}
```

### Quarterly Review
- Compliance with retention policies: ✓ or ✗
- Cost analysis and optimization opportunities
- Disaster recovery test (restore sample data)
- Update policy based on regulatory changes

---

## Exception Handling

### Exceptions to Retention Policy
1. **Regulatory Hold**: Extended retention for litigation/investigation
2. **Active Analysis**: Extended retention for ongoing research
3. **Performance Issues**: Shortened retention if storage critical

**Approval Process**:
- Request: Data team
- Review: Compliance officer
- Approval: CTO
- Duration: Specified in exception ticket

---

## Implementation Checklist

- [x] Policy document created (this file)
- [ ] Automated archival pipeline deployed
- [ ] MinIO bucket created and configured
- [ ] S3 Glacier lifecycle policies set
- [ ] Daily health check alerts configured
- [ ] Monthly audit report automation
- [ ] Disaster recovery testing scheduled
- [ ] Team training completed
- [ ] Compliance review passed
- [ ] Monitoring dashboards created

---

## Contact & Questions

- **Policy Owner**: Data Engineering Lead
- **Compliance**: Legal/Compliance Officer
- **Technical**: Infrastructure Team
- **Review Cycle**: Quarterly (January, April, July, October)

---

**Document Version**: 1.0  
**Last Updated**: May 14, 2026  
**Next Review**: August 14, 2026
