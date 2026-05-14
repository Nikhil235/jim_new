# Data Retention Policy Reference

## Overview

This document defines the retention policies for all data types managed by Mini-Medallion. It ensures compliance with legal requirements, optimizes storage costs through multi-tier archival, and maintains system performance.

## Policy Summary

### Market Data (OHLCV)

**Total Retention**: 7 years (2,555 days)

| Tier | Storage Backend | Duration | Purpose | Access Pattern |
|------|-----------------|----------|---------|-----------------|
| HOT | QuestDB | 90 days | Active trading analysis | Frequent (Real-time) |
| WARM | MinIO (S3) | 300 days | Historical backtesting | Occasional (Daily) |
| COLD | Glacier | 7 years | Compliance/Archive | Rare (Quarterly) |

**Use Case**: OHLCV data is actively used for 90 days during trading analysis, then archived to MinIO for historical backtesting research, and finally moved to Glacier for long-term compliance storage.

**Compliance**: Satisfies SEC Rule 17a-3(f) which requires 6-year retention of non-exchange data.

### Engineered Features

**Total Retention**: 3 years (1,095 days)

| Tier | Storage Backend | Duration | Purpose | Access Pattern |
|------|-----------------|----------|---------|-----------------|
| HOT | QuestDB | 60 days | Active model training | Frequent (Real-time) |
| WARM | MinIO (S3) | 180 days | Model refinement | Occasional (Weekly) |
| COLD | Glacier | 3 years | Regulatory audit | Rare (Annual) |

**Use Case**: Engineered features are used for 60 days in active model training, then archived after feature becomes stale, and retained in cold storage for audit compliance.

**Compliance**: Satisfies ML model audit requirements for feature engineering decisions.

### Application Logs

**Total Retention**: 1 year (365 days)

| Tier | Storage Backend | Duration | Purpose | Access Pattern |
|------|-----------------|----------|---------|-----------------|
| HOT | Local Filesystem | 30 days | Real-time debugging | Frequent (On-demand) |
| WARM | MinIO (S3) | 90 days | Incident investigation | Occasional (Monthly) |
| DELETE | - | After 1 year | Purge | Never |

**Use Case**: Recent logs (30 days) are available locally for quick debugging. Older logs (up to 90 days) are in archive for incident investigation. Beyond 1 year, logs are deleted per compliance policy.

**Compliance**: Satisfies standard IT log retention policies (1 year retention).

## Configuration

### YAML Configuration Format

```yaml
# configs/retention_policies.yaml

market_data:
  description: "OHLCV pricing data from exchange feeds"
  data_type: "market_data"
  tiers:
    - name: HOT
      storage: questdb
      retention_days: 90
      access_pattern: hot
      performance_sla: "P99 < 100ms"
      
    - name: WARM
      storage: minio
      retention_days: 300
      access_pattern: cold
      performance_sla: "P99 < 1s"
      
    - name: COLD
      storage: glacier
      retention_days: 2555
      access_pattern: archive
      performance_sla: "P99 < 1h"
  
  total_retention_days: 2945
  audit_required: true
  estimated_daily_volume_gb: 50


engineered_features:
  description: "Machine learning features computed from raw data"
  data_type: "features"
  tiers:
    - name: HOT
      storage: questdb
      retention_days: 60
      access_pattern: hot
      
    - name: WARM
      storage: minio
      retention_days: 180
      access_pattern: cold
      
    - name: COLD
      storage: glacier
      retention_days: 1095
      access_pattern: archive
  
  total_retention_days: 1335
  audit_required: true
  estimated_daily_volume_gb: 20


application_logs:
  description: "Application logs and debug information"
  data_type: "logs"
  tiers:
    - name: HOT
      storage: filesystem
      retention_days: 30
      access_pattern: hot
      
    - name: WARM
      storage: minio
      retention_days: 90
      access_pattern: cold
  
  total_retention_days: 120
  audit_required: false
  delete_after_days: 365
  estimated_daily_volume_gb: 5
```

## Archival Schedule

### Daily Archival Process

**Scheduled Time**: 2:00 AM UTC daily

**Operations**:
1. 2:00 AM - Identify data older than HOT tier threshold
2. 2:05 AM - Begin archival to WARM tier (if applicable)
3. 2:45 AM - Verify archive integrity
4. 3:00 AM - Delete from HOT tier after successful verification
5. 3:15 AM - Export audit logs
6. 3:30 AM - Send completion notification

**Timeline**: Full process completes within 90 minutes

### Archival Flow

```
┌──────────────┐
│  HOT TIER    │
│ (QuestDB)    │
│  90 days     │
└──────┬───────┘
       │ Daily archival at 2:00 AM
       │ (data reaches 90 days old)
       ↓
┌──────────────┐
│  WARM TIER   │
│  (MinIO)     │
│ 300 days     │
└──────┬───────┘
       │ After 390 days old
       ↓
┌──────────────┐
│  COLD TIER   │
│  (Glacier)   │
│  7 years     │
└──────┬───────┘
       │ After 7 years
       ↓
   PURGED
```

## Storage Tiers: Detailed Specifications

### HOT Tier (QuestDB)

**Characteristics**:
- **Storage**: In-memory database (QuestDB)
- **Performance**: <100ms P99 latency
- **Cost**: ~$5,000/month for 50GB daily volume
- **Capacity**: 4.5TB for 90-day market data retention

**Access Patterns**:
- Real-time queries (< 1 second)
- Concurrent analytical queries (10-100 concurrent)
- Live trading analysis
- Model retraining

**Maintenance**:
- Nightly index optimization
- Column compression enabled
- In-memory cache for hot keys
- Automatic backup to local disk

### WARM Tier (MinIO/S3)

**Characteristics**:
- **Storage**: S3-compatible object storage (MinIO)
- **Performance**: <1 second P99 latency
- **Cost**: ~$500/month for 50GB daily volume (using AWS S3 standard pricing)
- **Capacity**: 15TB for 300-day market data retention

**Access Patterns**:
- Periodic backtesting (daily/weekly)
- Historical analysis
- Quarterly audits
- Feature engineering validation

**Format**:
- Parquet format (columnar, compressed)
- Partitioned by date: `s3://bucket/market_data/2024/05/20/AAPL.parquet`
- Typically 100MB-500MB files per day per asset

**Maintenance**:
- Lifecycle policies for automatic deletion
- Versioning disabled (reduces storage)
- Encryption enabled (S3-SSE-KMS)
- Cross-region replication for disaster recovery

### COLD Tier (Glacier)

**Characteristics**:
- **Storage**: AWS Glacier deep archive
- **Performance**: 12-48 hour retrieval time
- **Cost**: ~$50/month for 50GB daily volume (extremely low cost)
- **Capacity**: Unlimited (archives as needed)

**Access Patterns**:
- Annual compliance audits
- Regulatory investigations (rare)
- Historical research (exceptional)
- Never accessed for production workloads

**Format**:
- Compressed tar archives (1GB-10GB per archive)
- File structure: `archives/market_data/2024/market_data_2024-05-20.tar.gz`
- Includes metadata JSON for quick lookup

**Maintenance**:
- Automatic archival from WARM → COLD
- Tagging for compliance categorization
- Retention lock enabled (immutable after archival)
- Quarterly inventory verification

## Archival Operations

### Operation: Archive Market Data

**Trigger**: Daily at 2:00 AM UTC for data reaching 90 days old

**Steps**:

1. **Query Source**
   ```
   SELECT * FROM ohlcv_data 
   WHERE date = current_date - 90 days
   ```

2. **Export to Parquet**
   - Create partitioned Parquet files
   - Compression: Snappy
   - Row groups: 100,000 rows each

3. **Upload to MinIO**
   - Destination: `s3://market-data/warm/2024/05/20/`
   - Parallel upload (16 concurrent streams)
   - Checksum verification

4. **Verify Integrity**
   - Row count match
   - File size match
   - Checksum validation

5. **Delete from QuestDB**
   - Remove data from hot tier
   - Commit transaction
   - Verify deletion

### Operation: Restore from Archive

**Use Case**: Backtesting engine needs historical market data

**Steps**:

1. **Identify Archive Location**
   - Determine which tier contains data
   - Locate specific Parquet file

2. **Download from MinIO**
   - Download Parquet file
   - Decompress if needed
   - Verify checksums

3. **Load into QuestDB**
   - Create temporary table
   - Bulk insert from Parquet
   - Verify row counts

4. **Return to Requester**
   - Data available in hot tier
   - Query completes normally
   - No application changes needed

**Timeline**: <5 minutes for typical restore

### Operation: Purge Expired Data

**Trigger**: Monthly, last day at 11:00 PM UTC

**Steps**:

1. **Identify Expired Data**
   - Find records beyond retention period
   - Verify compliance before deletion

2. **Generate Deletion Report**
   - Document what will be deleted
   - Estimate storage freed
   - Final compliance check

3. **Execute Deletion**
   - Delete from Glacier
   - Delete from MinIO (if not already gone)
   - Delete from QuestDB (if still present)

4. **Archive Deletion Records**
   - Log deletion event
   - Store deletion report for audit
   - Update compliance records

## Compliance & Audit

### Audit Logging

Every archival operation is logged with:

```json
{
  "timestamp": "2024-05-20T02:15:30Z",
  "operation": "archive",
  "data_type": "market_data",
  "date_archived": "2024-02-20",
  "source_tier": "questdb",
  "target_tier": "minio",
  "rows_count": 1000000,
  "bytes_transferred": 10737418240,
  "duration_ms": 1234.5,
  "status": "completed",
  "checksum": "abc123def456..."
}
```

### Compliance Reports

**Monthly Report**:
- Total data archived
- Total data purged
- Archive integrity (% verified)
- Recovery time (for spot checks)
- Cost breakdown by tier

**Annual Report**:
- Regulatory compliance summary
- Data retention metrics
- Archive recovery statistics
- Security audit results

## Disaster Recovery

### Backup Strategy

- **Market Data**: Cross-region replication (US East + EU)
- **Features**: Daily snapshots retained for 7 days
- **Logs**: Backup to secondary S3 region

### Recovery Procedures

**RTO** (Recovery Time Objective): 4 hours
**RPO** (Recovery Point Objective): 24 hours

**Steps**:
1. Identify backup source
2. Restore to temporary environment
3. Verify data integrity
4. Promote to production
5. Update data pointers

## Cost Analysis

### Storage Costs (Annual)

Assuming 50GB daily volume:

| Tier | Duration | Daily Vol | Annual Vol | Cost/GB | Annual Cost |
|------|----------|-----------|------------|---------|-------------|
| HOT (QuestDB) | 90 days | 50GB | 4.5TB | $100/TB | $450,000 |
| WARM (MinIO) | 300 days | 50GB | 15TB | $20/TB | $300,000 |
| COLD (Glacier) | 7 years | 50GB | 128TB | $4/TB | $512,000 |
| **Total** | - | - | **147.5TB** | - | **$1,262,000** |

### Cost Comparison: No Archival vs. Archival

**No Archival (Keep All in QuestDB)**:
- 7 years × 365 days × 50GB = 128TB
- Cost: 128TB × $100/TB = $12,800,000/year

**With Archival Strategy**:
- Tiered approach: $1,262,000/year
- **Savings**: $11,538,000/year (90% reduction)

## Migration Guide

### Migrating to Retention Policy

**Phase 1**: Deploy policies (no archival yet)
- Load retention policies from config
- Initialize audit logging
- Monitor for issues

**Phase 2**: Enable archival for new data
- Start archiving data dated > 90 days old
- Verify archive integrity
- Monitor restore latency

**Phase 3**: Backfill historical data
- Archive data from previous year
- Restore and verify sampling
- Update compliance records

**Phase 4**: Enable automatic purging
- Begin automatic purging after retention period
- Generate monthly reports
- Monitor compliance

## Troubleshooting

### Archive Integrity Check Failed

**Cause**: Data corruption during transfer

**Solution**:
1. Reattempt archival
2. If fails again, verify network/storage
3. Use backup copy from secondary region
4. Escalate to ops team

### Restore Takes Too Long

**Cause**: Large dataset, network latency

**Solution**:
1. Request data from closer region
2. Parallelize restore operation
3. Use incremental restore (restore only needed dates)
4. Consider moving data back to WARM tier

### Archival Schedule Missed

**Cause**: Scheduler error, resource constraint

**Solution**:
1. Check scheduler logs
2. Verify storage capacity
3. Run manual archival for missed date
4. Update monitoring alerts

## Summary

The Data Retention Policy provides:
- ✅ Multi-tier storage strategy optimizing cost vs. performance
- ✅ Compliance with regulatory requirements (SEC, SOX, GDPR)
- ✅ Automatic archival reducing storage footprint by 90%
- ✅ Complete audit trail for regulatory inspection
- ✅ Fast recovery procedures for business continuity
- ✅ Transparent cost breakdown for budget planning

**Status**: ✅ Production Ready
**Last Updated**: 2024-05-20
**Next Review**: 2024-08-20
