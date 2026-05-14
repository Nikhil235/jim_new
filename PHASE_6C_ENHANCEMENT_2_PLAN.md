# Phase 6C Enhancement #2: Data Retention Policy & Automation
**Status**: IN PROGRESS  
**Priority**: CRITICAL  
**Effort**: 4-5 days  
**Impact**: Critical (legal/compliance)

## Overview

Enhancement #2 implements automatic data lifecycle management, transforming the Mini-Medallion platform from storing all data indefinitely to a production-grade multi-tier storage strategy. This is essential for:
- **Compliance**: Legal retention requirements (GDPR, SOX, etc.)
- **Cost Control**: Hot tier for active data, cold tier for archives
- **Performance**: Reduced QuestDB/Redis footprint by archiving old data
- **Auditability**: Complete audit trail of all data movements

## Architecture

### Storage Tiers

```
┌─────────────────────────────────────────────────────────────────┐
│                      DATA LIFECYCLE                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  HOT TIER (Fast Access)        WARM TIER (Archive)  COLD TIER    │
│  ═══════════════════           ═══════════════════  ═════════    │
│  QuestDB (In-Memory)           MinIO (S3)           Glacier      │
│  Redis (Cache)                 Parquet Files        Long-term    │
│  Active Analysis               Historical Analysis  Compliance   │
│                                                                   │
│  Market Data: 90 days          300 days             7 years      │
│  Features: 60 days             180 days             3 years      │
│  Logs: 30 days                 90 days              1 year       │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Components

#### 1. DataLifecycleManager
Main orchestrator managing data movement between tiers.

**Responsibilities**:
- Monitor data age in hot tier
- Trigger archival when retention threshold reached
- Coordinate multi-storage movement
- Maintain audit logs
- Handle rollback on failures

**Key Methods**:
- `archive_market_data(date: datetime)` - Move OHLCV to MinIO
- `archive_features(date: datetime)` - Move engineered features
- `archive_logs(date: datetime)` - Move application logs
- `purge_cold_expired(date: datetime)` - Delete from Glacier
- `restore_from_archive(date, asset_class)` - Restore warm data
- `verify_archive_integrity(date)` - Checksum verification

#### 2. ArchivalScheduler
Scheduled execution of archival operations.

**Responsibilities**:
- Daily scheduled archival (configurable time)
- Orchestrate archival across all data types
- Error handling and retry logic
- Progress monitoring and notifications
- Performance metrics collection

**Key Methods**:
- `schedule_daily_archival(hour: int)` - Setup cron-like scheduler
- `run_archival_for_date(date)` - Execute full daily archival
- `retry_failed_archival(date)` - Retry failed operations

#### 3. RetentionPolicy
Configuration and enforcement of retention rules.

**Structure**:
```python
@dataclass
class RetentionTier:
    name: str  # "HOT", "WARM", "COLD"
    storage_backend: str  # "questdb", "minio", "glacier"
    retention_days: int  # How long to keep in this tier
    access_pattern: str  # "hot", "cold", "archive"

@dataclass
class DataRetentionPolicy:
    data_type: str  # "market_data", "features", "logs"
    tiers: List[RetentionTier]  # Ordered: hot → warm → cold
    total_retention_days: int  # Total across all tiers
    audit_required: bool  # Whether to log every access
```

### Implementation Plan

#### Phase 1: Foundation (Day 1-2)

**1.1 Create `src/infrastructure/data_lifecycle_manager.py`** (400+ lines)
- Core DataLifecycleManager class
- Hot tier monitoring logic
- Archive triggering system
- Error handling framework

**1.2 Create `src/infrastructure/archival_scheduler.py`** (250+ lines)
- ArchivalScheduler implementation
- Daily scheduling logic
- Progress tracking
- Retry mechanisms

**1.3 Database Schema Updates**
- Create `data_archival_log` table
  - Timestamp, data_type, rows_archived, duration_ms, status
- Create `retention_policies` table
  - Configuration storage for policies
- Create `archive_audit` table
  - Complete audit trail of all movements

#### Phase 2: Integration (Day 2-3)

**2.1 QuestDB Integration**
- Query old market data by date range
- Export to Parquet for archival
- Delete from hot tier after verification

**2.2 MinIO Integration**
- Upload Parquet to warm tier
- Configure lifecycle policies
- Implement restore functionality

**2.3 Redis Integration**
- Archive cache metadata
- Clear expired cache entries
- Monitor memory usage reduction

#### Phase 3: Testing (Day 3-5)

**3.1 Unit Tests** (15+ tests)
- Lifecycle calculations
- Tier transitions
- Policy enforcement
- Rollback logic

**3.2 Integration Tests** (10+ tests)
- Full archival workflow
- Multi-tier coordination
- Verification and restore
- Audit log accuracy

**3.3 Stress Tests**
- Large data volumes (100M+ rows)
- Concurrent archival operations
- Failure recovery scenarios

#### Phase 4: Documentation (Day 4-5)

**4.1 DATA_RETENTION_POLICY.md**
- Retention rules reference
- Configuration guide
- Troubleshooting

**4.2 DATA_RETENTION_GUIDE.md**
- Implementation guide
- Integration examples
- Best practices

## File Structure

```
src/infrastructure/
├── data_lifecycle_manager.py          # Core lifecycle management
├── archival_scheduler.py              # Scheduled archival
├── data_retention_policy.py           # Policy definitions
└── archive_utils.py                   # Helper functions (optional)

tests/
├── test_enhancement_2_lifecycle.py    # Unit tests (15+ tests)
├── test_enhancement_2_integration.py  # Integration tests (10+ tests)
└── test_enhancement_2_stress.py       # Stress tests (5+ tests)

docs/
├── DATA_RETENTION_POLICY.md           # Configuration reference
└── DATA_RETENTION_GUIDE.md            # Implementation guide

configs/
├── retention_policies.yaml            # Default policies
└── archival_schedule.yaml             # Scheduling config
```

## Success Criteria

- [ ] DataLifecycleManager fully implements all archival scenarios
- [ ] ArchivalScheduler runs daily without manual intervention
- [ ] 30+ test cases pass with >90% coverage
- [ ] Archive integrity verification passes
- [ ] <1 hour archival time for daily data volume
- [ ] Audit logs capture all operations
- [ ] Restore from archive works for any date
- [ ] Documentation complete (200+ lines per file)

## Testing Strategy

**Unit Testing** (15 tests):
- Individual lifecycle transitions
- Policy enforcement
- Tier calculations
- Error handling

**Integration Testing** (10 tests):
- Full workflow (hot → warm → cold)
- Multi-storage coordination
- Restore operations
- Audit logging

**Stress Testing** (5 tests):
- 100M+ row archival
- Concurrent operations
- Memory constraints
- Network failures

## Timeline

```
Day 1: Architecture & Design
  - Create data_lifecycle_manager.py foundation
  - Design ArchivalScheduler structure
  - Plan database schema

Day 2: Core Implementation
  - Implement DataLifecycleManager
  - Implement ArchivalScheduler
  - Setup database schema

Day 3: Integration
  - QuestDB integration
  - MinIO integration
  - Redis integration

Day 4: Testing
  - Unit tests (15 tests)
  - Integration tests (10 tests)
  - Stress tests (5 tests)

Day 5: Documentation & Polish
  - DATA_RETENTION_POLICY.md
  - DATA_RETENTION_GUIDE.md
  - Final verification & polish
```

## Next Steps

1. Create `src/infrastructure/data_lifecycle_manager.py` with core classes
2. Create `src/infrastructure/archival_scheduler.py` with scheduling logic
3. Define database schema in schema migration
4. Implement unit tests framework
5. Begin implementation on Day 1

## Configuration Example

```yaml
# configs/retention_policies.yaml
market_data:
  hot:
    storage: questdb
    retention_days: 90
    access_pattern: frequent
  warm:
    storage: minio
    retention_days: 300
    access_pattern: occasional
  cold:
    storage: glacier
    retention_days: 2555  # ~7 years
    access_pattern: rare

features:
  hot:
    storage: questdb
    retention_days: 60
  warm:
    storage: minio
    retention_days: 180
  cold:
    storage: glacier
    retention_days: 1095  # ~3 years

logs:
  hot:
    storage: filesystem
    retention_days: 30
  warm:
    storage: minio
    retention_days: 90
  delete:
    after_days: 365
```

## Implementation Notes

- **Atomicity**: Use transactions to ensure atomic tier transitions
- **Auditability**: Every operation logged with timestamp, user, status
- **Recoverability**: Failed operations can be retried or rolled back
- **Performance**: Batch operations to minimize I/O overhead
- **Monitoring**: Metrics exported to Prometheus for visualization

## Related Enhancements

- **Enhancement #1**: Health monitoring (tracks lifecycle health)
- **Enhancement #3**: Backup & DR (depends on retention policy)
- **Enhancement #10**: Logging & Observability (logs archival operations)
