# Mini-Medallion: Comprehensive Enhancement Opportunities Analysis
**Analysis Date**: May 14, 2026  
**Status**: Phase 1-5 Complete (~95% of core system)  
**Purpose**: Identify practical, high-impact improvements for production readiness

---

## Executive Summary

The Mini-Medallion system is **95% feature-complete** with all core infrastructure, data pipeline, models, risk management, and backtesting frameworks implemented. However, there are **40+ opportunities** for enhancement across reliability, performance, explainability, and operational excellence.

**Key Insight**: Most enhancements require **low-to-medium effort** and significantly improve production readiness without requiring architectural changes.

**Effort Breakdown**:
- 🟢 **Low (5-15 hours)**: 18 items
- 🟡 **Medium (15-40 hours)**: 15 items  
- 🔴 **High (40+ hours)**: 7 items

---

# PHASE 1: INFRASTRUCTURE & COMPUTE

## Current Capabilities
✅ QuestDB for tick data storage  
✅ Redis for feature caching  
✅ MinIO for data lake (parquet archival)  
✅ Prometheus for metrics collection  
✅ Grafana for dashboards  
✅ GPU acceleration (RAPIDS, cuDF, PyTorch)  
✅ Docker containerization  
✅ MLflow for model registry

---

## 1.1 Missing Health Checks & Self-Healing

### Current State
- Docker services have `restart: unless-stopped` but no health checks
- No automatic service restart on failure
- No circuit breaker for database connections
- No automatic failover between Redis/parquet storage

### Enhancement: Container Health Checks
**Effort**: 🟢 Low (8 hours)  
**Impact**: High — Prevents cascading failures

```yaml
# docker-compose.yml additions
questdb:
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:9000/health"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 40s

redis:
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 30s
    timeout: 3s
    retries: 3

minio:
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
    interval: 30s
    timeout: 10s
    retries: 3
```

**Implementation**:
- Add health check endpoints to each service
- Create health monitoring dashboard in Grafana
- Implement service restart automation
- Add alerting for repeated health check failures

---

### Enhancement: Connection Pool Management
**Effort**: 🟢 Low (6 hours)  
**Impact**: Medium — Improves resilience

**Current Implementation Issue**:
```python
# src/features/feature_store.py - Current lazy connection
def _get_redis(self):
    if self._redis is None:
        try:
            import redis
            self._redis = redis.Redis(...)
            return self._redis
        except Exception:
            self._redis = None  # Lost connection info
            return None
```

**Recommended Enhancement**:
```python
# Add connection pooling and retry logic
from redis.connection import ConnectionPool
from redis.backoff import ExponentialBackoff
from redis.retry import Retry

class FeatureStore:
    def __init__(self, config=None):
        # ... existing code ...
        retry = Retry(ExponentialBackoff(), 3)
        self.pool = ConnectionPool.from_url(
            f"redis://{host}:{port}/{db}",
            connection_class=redis.Redis,
            retry=retry,
            socket_keepalive=True,
            socket_keepalive_options={...},
        )
        self._redis = redis.Redis(connection_pool=self.pool)
        
    def health_check(self) -> bool:
        try:
            self._redis.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False
```

---

## 1.2 Data Retention & Archival Policies

### Current State
- QuestDB tables have `WAL` (Write-Ahead Logging) but no retention policy
- Redis max memory set to 2GB with `allkeys-lru` eviction but not monitored
- MinIO has unlimited storage — no cleanup
- Prometheus stores metrics with default 15-day retention
- Logs accumulate indefinitely

### Enhancement: Automated Data Retention Policies
**Effort**: 🟡 Medium (20 hours)  
**Impact**: High — Prevents disk exhaustion

**For QuestDB**:
```sql
-- Add retention policy to tick tables
ALTER TABLE gold_ticks SET PARAM maxUncommittedRows = 500000;

-- Archive old data to MinIO (monthly)
INSERT INTO gold_ticks_archive_2026_04
SELECT * FROM gold_ticks 
WHERE timestamp < '2026-05-01'
  AND timestamp >= '2026-04-01';

-- Delete archived rows
DELETE FROM gold_ticks 
WHERE timestamp < '2026-05-01';
```

**Create Retention Manager**:
```python
# src/infrastructure/retention_manager.py
class DataRetentionManager:
    """Automated cleanup and archival of old data."""
    
    def __init__(self, config: dict):
        self.questdb = QuestDBWriter(config)
        self.minio = MinioClient(config)
        
        # Retention policies (days)
        self.tick_data_retention = 365      # 1 year
        self.feature_retention = 90         # 3 months
        self.log_retention = 30             # 1 month
        
    async def archive_old_data(self):
        """Daily archival task."""
        # Archive ticks older than 1 year to MinIO
        cutoff_date = datetime.now() - timedelta(days=self.tick_data_retention)
        
        # Query and export
        df = self.questdb.fetch_data(
            f"SELECT * FROM gold_ticks WHERE timestamp < '{cutoff_date}'"
        )
        
        # Upload to MinIO
        year_month = cutoff_date.strftime("%Y_%m")
        self.minio.upload_parquet(
            df, 
            f"archives/gold_ticks_{year_month}.parquet"
        )
        
        # Delete from QuestDB
        self.questdb.execute(
            f"DELETE FROM gold_ticks WHERE timestamp < '{cutoff_date}'"
        )
        
        logger.info(f"Archived {len(df)} rows for {year_month}")
        
    async def cleanup_logs(self):
        """Remove logs older than retention period."""
        # Use loguru's built-in rotation
        # Already configured in src/utils/logger.py (retention="30 days")
        pass
```

**Implementation Steps**:
1. Create `src/infrastructure/retention_manager.py`
2. Add scheduled task to `scripts/daily_scheduler.py` to run retention
3. Add monitoring metrics (rows archived, deleted, etc.)
4. Add configuration options to `configs/base.yaml`
5. Test with staging data before production

---

### Enhancement: Redis Memory Monitoring
**Effort**: 🟢 Low (5 hours)  
**Impact**: Medium

```python
# Add to src/ingestion/metrics_exporter.py
class RedisMemoryMonitor:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.memory_gauge = Gauge(
            'redis_memory_bytes',
            'Redis memory usage in bytes',
            ['instance']
        )
        self.memory_limit_gauge = Gauge(
            'redis_memory_limit_bytes',
            'Redis max memory limit',
            ['instance']
        )
        
    def update_metrics(self):
        """Update Redis memory metrics."""
        info = self.redis.info('memory')
        self.memory_gauge.labels(instance='feature_store').set(
            info['used_memory']
        )
        self.memory_limit_gauge.labels(instance='feature_store').set(
            info['maxmemory']
        )
        
        # Alert if > 80% utilized
        usage_pct = info['used_memory'] / info['maxmemory']
        if usage_pct > 0.8:
            logger.warning(
                f"Redis memory utilization {usage_pct*100:.1f}% "
                f"({info['used_memory']/(1024**3):.2f}GB / "
                f"{info['maxmemory']/(1024**3):.2f}GB)"
            )
```

---

## 1.3 Backup & Disaster Recovery Strategies

### Current State
- QuestDB uses `./docker/volumes/questdb` volume mounting
- Redis uses `appendonly yes` but no off-site backup
- MinIO is single-instance (no replication)
- No backup automation or recovery testing

### Enhancement: Automated Backup Strategy
**Effort**: 🟡 Medium (25 hours)  
**Impact**: Critical — Enables recovery from data loss

**Create Backup Manager**:
```python
# src/infrastructure/backup_manager.py
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
import boto3
from loguru import logger

class BackupManager:
    """Manages backups of critical data to S3."""
    
    def __init__(self, config: dict):
        self.config = config
        self.backup_cfg = config.get("backup", {})
        
        # S3 client for remote backups
        self.s3 = boto3.client(
            's3',
            endpoint_url=self.backup_cfg.get('s3_endpoint'),
            aws_access_key_id=self.backup_cfg.get('s3_key'),
            aws_secret_access_key=self.backup_cfg.get('s3_secret'),
        )
        self.bucket = self.backup_cfg.get('backup_bucket', 'medallion-backups')
        
        # Retention
        self.full_backup_days = self.backup_cfg.get('full_backup_frequency_days', 7)
        self.incremental_backup_days = self.backup_cfg.get('incremental_backup_frequency_days', 1)
        self.backup_retention_days = self.backup_cfg.get('backup_retention_days', 90)
        
    async def backup_questdb(self) -> bool:
        """Backup QuestDB to S3."""
        try:
            questdb_path = Path("./docker/volumes/questdb")
            
            # Create compressed archive
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"/tmp/questdb_backup_{timestamp}.tar.gz"
            
            import tarfile
            with tarfile.open(backup_file, "w:gz") as tar:
                tar.add(questdb_path, arcname="questdb")
            
            # Upload to S3
            s3_key = f"questdb_backups/questdb_{timestamp}.tar.gz"
            self.s3.upload_file(backup_file, self.bucket, s3_key)
            
            logger.info(f"✓ QuestDB backup: s3://{self.bucket}/{s3_key}")
            
            # Cleanup local backup
            Path(backup_file).unlink()
            return True
            
        except Exception as e:
            logger.error(f"QuestDB backup failed: {e}")
            return False
    
    async def backup_redis(self) -> bool:
        """Backup Redis dump.rdb to S3."""
        try:
            from src.features.feature_store import FeatureStore
            redis = FeatureStore().get_redis()
            
            # Force BGSAVE
            redis.bgsave()
            
            # Wait for save to complete
            while redis.lastsave() == redis.lastsave():
                await asyncio.sleep(1)
            
            # Upload dump file
            dump_path = Path("./docker/volumes/redis/dump.rdb")
            if dump_path.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                s3_key = f"redis_backups/dump_{timestamp}.rdb"
                
                self.s3.upload_file(
                    str(dump_path),
                    self.bucket,
                    s3_key
                )
                logger.info(f"✓ Redis backup: s3://{self.bucket}/{s3_key}")
                return True
        except Exception as e:
            logger.error(f"Redis backup failed: {e}")
            return False
    
    async def backup_minio(self) -> bool:
        """Backup MinIO data to S3."""
        try:
            minio_path = Path("./docker/volumes/minio")
            
            # Create compressed archive
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"/tmp/minio_backup_{timestamp}.tar.gz"
            
            import tarfile
            with tarfile.open(backup_file, "w:gz") as tar:
                tar.add(minio_path, arcname="minio")
            
            s3_key = f"minio_backups/minio_{timestamp}.tar.gz"
            self.s3.upload_file(backup_file, self.bucket, s3_key)
            
            logger.info(f"✓ MinIO backup: s3://{self.bucket}/{s3_key}")
            Path(backup_file).unlink()
            return True
            
        except Exception as e:
            logger.error(f"MinIO backup failed: {e}")
            return False
    
    async def cleanup_old_backups(self) -> None:
        """Remove backups older than retention period."""
        try:
            cutoff = datetime.now() - timedelta(days=self.backup_retention_days)
            
            for prefix in ['questdb_backups/', 'redis_backups/', 'minio_backups/']:
                response = self.s3.list_objects_v2(
                    Bucket=self.bucket,
                    Prefix=prefix
                )
                
                for obj in response.get('Contents', []):
                    if obj['LastModified'].replace(tzinfo=None) < cutoff:
                        self.s3.delete_object(Bucket=self.bucket, Key=obj['Key'])
                        logger.info(f"Deleted old backup: {obj['Key']}")
                        
        except Exception as e:
            logger.error(f"Backup cleanup failed: {e}")
    
    async def run_daily_backup(self) -> dict:
        """Run all backups."""
        results = {
            'questdb': await self.backup_questdb(),
            'redis': await self.backup_redis(),
            'minio': await self.backup_minio(),
        }
        await self.cleanup_old_backups()
        return results
```

**Add to Configuration**:
```yaml
# configs/base.yaml
backup:
  enabled: true
  backup_bucket: "medallion-backups"
  s3_endpoint: "https://s3.aws.amazon.com"  # Or MinIO endpoint
  s3_key: "${AWS_ACCESS_KEY_ID}"
  s3_secret: "${AWS_SECRET_ACCESS_KEY}"
  full_backup_frequency_days: 7
  incremental_backup_frequency_days: 1
  backup_retention_days: 90
```

**Add to Daily Scheduler**:
```python
# scripts/daily_scheduler.py
async def run_daily_tasks():
    # ... existing tasks ...
    
    # Run backups
    backup_mgr = BackupManager(config)
    backup_results = await backup_mgr.run_daily_backup()
    
    health_data['backups'] = backup_results
```

---

## 1.4 Monitoring Gaps

### Enhancement: Advanced Alerting Rules
**Effort**: 🟢 Low (8 hours)  
**Impact**: High — Enables proactive issue detection

**Create AlertManager Configuration**:
```yaml
# docker/prometheus.yml - Add alerting rules
groups:
  - name: medallion_alerts
    interval: 30s
    rules:
      # Infrastructure alerts
      - alert: HighCPUUsage
        expr: process_cpu_seconds_total > 0.85
        for: 5m
        annotations:
          summary: "High CPU usage detected ({{ $value }}%)"
          
      - alert: HighMemoryUsage
        expr: process_resident_memory_bytes > 2000000000  # 2GB
        for: 5m
        
      - alert: DiskSpaceLow
        expr: node_filesystem_avail_bytes / node_filesystem_size_bytes < 0.2
        for: 5m
        
      - alert: QuestDBDown
        expr: up{job="questdb"} == 0
        for: 1m
        
      - alert: RedisDown
        expr: up{job="redis"} == 0
        for: 1m
        
      # Data quality alerts
      - alert: DataStaleness
        expr: time() - max(medallion_data_ingest_timestamp) > 86400  # 24h
        for: 5m
        
      - alert: HighDataLoss
        expr: medallion_data_quality_missing_points > 0.01
        for: 5m
        
      # Trading alerts
      - alert: HighDrawdown
        expr: medallion_drawdown > 0.15
        for: 5m
        
      - alert: CircuitBreakerTriggered
        expr: medallion_circuit_breaker_active == 1
        for: 1m
```

---

### Enhancement: Health Endpoint
**Effort**: 🟢 Low (6 hours)  
**Impact**: Medium

```python
# Add to src/api/app.py
@app.get("/health/detailed")
async def detailed_health():
    """Get detailed health status of all components."""
    health_status = {
        "timestamp": datetime.utcnow().isoformat(),
        "overall_status": "HEALTHY",
        "components": {}
    }
    
    # Check QuestDB
    try:
        from src.ingestion.questdb_writer import QuestDBWriter
        writer = QuestDBWriter(CONFIG)
        writer.test_connection()
        health_status['components']['questdb'] = {
            'status': 'UP',
            'response_time_ms': measure_latency(writer.test_connection)
        }
    except Exception as e:
        health_status['components']['questdb'] = {
            'status': 'DOWN',
            'error': str(e)
        }
        health_status['overall_status'] = 'DEGRADED'
    
    # Check Redis
    try:
        from src.features.feature_store import FeatureStore
        fs = FeatureStore(CONFIG)
        if fs.is_available():
            health_status['components']['redis'] = {'status': 'UP'}
        else:
            health_status['components']['redis'] = {'status': 'DOWN'}
            health_status['overall_status'] = 'DEGRADED'
    except Exception as e:
        health_status['components']['redis'] = {'status': 'DOWN', 'error': str(e)}
    
    # Check MinIO
    try:
        health_status['components']['minio'] = check_minio_health(CONFIG)
    except Exception as e:
        health_status['components']['minio'] = {'status': 'DOWN', 'error': str(e)}
    
    # Check disk space
    import shutil
    total, used, free = shutil.disk_usage("/")
    health_status['disk'] = {
        'total_gb': total / (1024**3),
        'used_gb': used / (1024**3),
        'free_gb': free / (1024**3),
        'percent_used': (used / total) * 100
    }
    
    return health_status
```

---

---

# PHASE 2: DATA PIPELINE

## Current Capabilities
✅ Gold price ingestion (spot + futures)  
✅ Macro data fetching (DXY, VIX, yields, etc.)  
✅ FRED economic data integration  
✅ Alternative data sources (news sentiment, ETF flows, COT)  
✅ 200+ feature engineering  
✅ Data quality monitoring  
✅ Redis feature store  
✅ QuestDB time-series storage  
✅ Data pipeline orchestration  
✅ Daily scheduler with backfill

---

## 2.1 Data Quality Enhancements

### Current State
- Basic outlier detection (z-score)
- Gap detection and completeness checks
- Source timestamp alignment
- But: No automatic correction, no feedback loop

### Enhancement: Outlier Correction & Imputation
**Effort**: 🟡 Medium (18 hours)  
**Impact**: High — Improves data reliability

```python
# src/ingestion/data_repair.py
import pandas as pd
import numpy as np
from scipy import stats

class DataRepairEngine:
    """Repair common data quality issues."""
    
    @staticmethod
    def detect_and_fix_outliers(
        df: pd.DataFrame,
        column: str,
        method: str = 'iqr',
        zscore_threshold: float = 5.0,
        iqr_multiplier: float = 3.0
    ) -> pd.DataFrame:
        """
        Detect and correct outliers using IQR or Z-score methods.
        
        Methods:
          - 'iqr': Interquartile range (more robust to extreme values)
          - 'zscore': Z-score (parametric)
          - 'isolation_forest': Isolation Forest (ML-based)
        """
        df = df.copy()
        
        if method == 'iqr':
            Q1 = df[column].quantile(0.25)
            Q3 = df[column].quantile(0.75)
            IQR = Q3 - Q1
            lower = Q1 - iqr_multiplier * IQR
            upper = Q3 + iqr_multiplier * IQR
            
            outlier_mask = (df[column] < lower) | (df[column] > upper)
            
        elif method == 'zscore':
            z_scores = np.abs(stats.zscore(df[column]))
            outlier_mask = z_scores > zscore_threshold
            
        elif method == 'isolation_forest':
            from sklearn.ensemble import IsolationForest
            iso_forest = IsolationForest(contamination=0.01, random_state=42)
            predictions = iso_forest.fit_predict(df[[column]])
            outlier_mask = predictions == -1
        
        # Replace outliers with median of surrounding values
        if outlier_mask.any():
            for idx in np.where(outlier_mask)[0]:
                # Use 5-bar moving median
                start = max(0, idx - 5)
                end = min(len(df), idx + 5)
                surrounding = df[column].iloc[start:end]
                df.loc[idx, column] = surrounding.median()
        
        return df, outlier_mask.sum()
    
    @staticmethod
    def impute_missing_values(
        df: pd.DataFrame,
        method: str = 'forward_fill'
    ) -> pd.DataFrame:
        """
        Impute missing values using various methods.
        
        Methods:
          - 'forward_fill': Forward fill (bfill fallback)
          - 'interpolate': Linear interpolation
          - 'knn': K-nearest neighbors
        """
        df = df.copy()
        
        if method == 'forward_fill':
            df = df.fillna(method='ffill').fillna(method='bfill')
            
        elif method == 'interpolate':
            df = df.interpolate(method='linear', limit_direction='both')
            
        elif method == 'knn':
            from sklearn.impute import KNNImputer
            imputer = KNNImputer(n_neighbors=5)
            df = pd.DataFrame(
                imputer.fit_transform(df),
                columns=df.columns,
                index=df.index
            )
        
        return df
    
    @staticmethod
    def detect_gaps(
        df: pd.DataFrame,
        expected_interval: int = 60,  # seconds
        threshold_multiplier: float = 2.0
    ) -> list:
        """Detect gaps in time series data."""
        if len(df) < 2:
            return []
        
        time_diffs = df.index.to_series().diff().dt.total_seconds()
        expected_diff = expected_interval
        threshold = expected_diff * threshold_multiplier
        
        gaps = df.index[time_diffs > threshold].tolist()
        return gaps
    
    @staticmethod
    def repair_gaps(
        df: pd.DataFrame,
        expected_interval: int = 60,
        method: str = 'interpolate'
    ) -> pd.DataFrame:
        """Fill in detected gaps."""
        df = df.copy()
        
        # Resample to expected interval
        resampled = df.resample(f'{expected_interval}S').first()
        
        # Interpolate missing values
        if method == 'interpolate':
            resampled = resampled.interpolate(method='time')
        elif method == 'forward_fill':
            resampled = resampled.fillna(method='ffill')
        
        return resampled
```

**Integration with Data Quality Monitor**:
```python
# Modify src/ingestion/data_quality.py
from src.ingestion.data_repair import DataRepairEngine

class DataQualityMonitor:
    # ... existing code ...
    
    def validate_and_repair_ohlcv(
        self,
        df: pd.DataFrame,
        source: str = "unknown",
        auto_repair: bool = False
    ) -> Tuple[pd.DataFrame, Dict]:
        """Validate and optionally repair data."""
        repair_engine = DataRepairEngine()
        
        # Run existing validation checks
        report = self.validate_ohlcv(df, source)
        
        if auto_repair and report['overall_status'] == 'FAIL':
            # Repair outliers
            df, n_outliers = repair_engine.detect_and_fix_outliers(
                df, 'close', method='iqr'
            )
            report['repairs']['outliers_fixed'] = n_outliers
            
            # Repair gaps
            original_len = len(df)
            df = repair_engine.repair_gaps(df)
            report['repairs']['rows_interpolated'] = len(df) - original_len
            
            # Impute missing
            df = repair_engine.impute_missing_values(df, method='interpolate')
            
            report['overall_status'] = 'REPAIRED'
            report['repairs_applied'] = True
        
        return df, report
```

---

### Enhancement: Source-Specific Validation Rules
**Effort**: 🟢 Low (10 hours)  
**Impact**: Medium

```python
# src/ingestion/source_validators.py
class SourceValidators:
    """Source-specific validation rules."""
    
    @staticmethod
    def validate_gold_spot(df: pd.DataFrame) -> Dict[str, bool]:
        """XAU/USD spot price validation."""
        return {
            'price_range': (df['close'] > 1000) & (df['close'] < 2500),  # Gold range
            'volume_positive': df['volume'] > 0,
            'bid_ask_order': df['bid'] < df['ask'],
            'bid_ask_spread': (df['ask'] - df['bid']) < 5.0,
        }
    
    @staticmethod
    def validate_dxy(df: pd.DataFrame) -> Dict[str, bool]:
        """DXY validation."""
        return {
            'price_range': (df['close'] > 90) & (df['close'] < 110),
            'correlation_gold': df['close'].corr(df.get('gold', pd.Series())) < 0,  # Inverse
        }
    
    @staticmethod
    def validate_vix(df: pd.DataFrame) -> Dict[str, bool]:
        """VIX validation."""
        return {
            'price_range': (df['close'] > 5) & (df['close'] < 80),
            'no_negative': df['close'] >= 0,
        }
```

---

## 2.2 Real-Time vs Batch Processing Optimization

### Current State
- Daily batch pipeline runs once/day at 00:00 UTC
- 1-minute bars stored in QuestDB
- Features stored in Redis with 24h freshness target
- But: No real-time streaming capability

### Enhancement: Streaming Data Ingestion
**Effort**: 🟡 Medium (30 hours)  
**Impact**: Critical for live trading — Enables intraday signals

```python
# src/ingestion/streaming_ingestor.py
import asyncio
from typing import Callable, Optional
import pandas as pd
from loguru import logger

class StreamingIngestor:
    """Real-time data streaming with minimal latency."""
    
    def __init__(self, config: dict, on_new_tick: Optional[Callable] = None):
        self.config = config
        self.on_new_tick = on_new_tick  # Callback when new tick arrives
        self.active = False
        self.tick_buffer = []
        self.buffer_size = 100
        
    async def start_streaming(self, sources: list):
        """Start streaming data from multiple sources."""
        self.active = True
        logger.info(f"Starting streaming ingestor for {len(sources)} sources")
        
        tasks = [
            self._stream_source(source)
            for source in sources
        ]
        
        await asyncio.gather(*tasks)
    
    async def _stream_source(self, source: str):
        """Stream data from a single source."""
        if source == 'gold_spot':
            await self._stream_gold_spot()
        elif source == 'gold_futures':
            await self._stream_gold_futures()
        elif source == 'macro_feeds':
            await self._stream_macro()
    
    async def _stream_gold_spot(self):
        """Stream XAU/USD spot prices via WebSocket."""
        try:
            import aiohttp
            import json
            
            # Use finnhub or similar provider with WebSocket
            async with aiohttp.ClientSession() as session:
                # Example: Connect to WebSocket feed
                url = "wss://finnhub.io/ws?token={API_KEY}"
                async with session.ws_connect(url) as ws:
                    # Subscribe to gold
                    await ws.send_json({
                        "type": "subscribe",
                        "symbol": "XAUUSD"
                    })
                    
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            await self._process_tick(data, 'gold_spot')
        except Exception as e:
            logger.error(f"Gold spot streaming error: {e}")
            await asyncio.sleep(5)  # Reconnect after delay
            await self._stream_gold_spot()
    
    async def _stream_macro(self):
        """Stream macro data from multiple providers."""
        # Similar pattern for DXY, VIX, yields, etc.
        pass
    
    async def _process_tick(self, tick_data: dict, source: str):
        """Process incoming tick and update feature store."""
        try:
            # Validate tick
            if not self._validate_tick(tick_data, source):
                logger.warning(f"Invalid tick from {source}: {tick_data}")
                return
            
            # Add to buffer
            self.tick_buffer.append({
                'timestamp': pd.Timestamp.now(),
                'source': source,
                'data': tick_data
            })
            
            # If buffer full, flush to databases
            if len(self.tick_buffer) >= self.buffer_size:
                await self._flush_buffer()
            
            # Trigger callback if provided
            if self.on_new_tick:
                await self.on_new_tick(tick_data, source)
                
        except Exception as e:
            logger.error(f"Tick processing error: {e}")
    
    async def _flush_buffer(self):
        """Write buffered ticks to QuestDB and Redis."""
        if not self.tick_buffer:
            return
        
        try:
            from src.ingestion.questdb_writer import QuestDBWriter
            from src.features.feature_store import FeatureStore
            
            questdb = QuestDBWriter(self.config)
            feature_store = FeatureStore(self.config)
            
            # Group by source
            for source in set(t['source'] for t in self.tick_buffer):
                ticks = [t for t in self.tick_buffer if t['source'] == source]
                
                # Write to QuestDB
                df = pd.DataFrame([t['data'] for t in ticks])
                df['timestamp'] = [t['timestamp'] for t in ticks]
                questdb.write_data(df, source)
                
                # Update feature store with latest values
                latest = df.iloc[-1]
                feature_store.store_features_latest(
                    source,
                    latest.to_dict()
                )
            
            logger.debug(f"Flushed {len(self.tick_buffer)} ticks")
            self.tick_buffer = []
            
        except Exception as e:
            logger.error(f"Buffer flush error: {e}")
    
    def stop_streaming(self):
        """Stop streaming and flush remaining buffer."""
        self.active = False
        if self.tick_buffer:
            asyncio.run(self._flush_buffer())
```

**Add to API**:
```python
# src/api/app.py
streaming_ingestor = None

@app.on_event("startup")
async def startup():
    global streaming_ingestor
    
    # ... existing startup code ...
    
    # Start streaming if enabled
    if CONFIG.get("pipeline", {}).get("enable_streaming", False):
        streaming_ingestor = StreamingIngestor(CONFIG)
        asyncio.create_task(
            streaming_ingestor.start_streaming(['gold_spot', 'macro_feeds'])
        )

@app.on_event("shutdown")
async def shutdown():
    if streaming_ingestor:
        streaming_ingestor.stop_streaming()
```

---

## 2.3 Error Recovery & Retry Mechanisms

### Current State
- Basic error handling in fetchers
- No automatic retry with exponential backoff
- Failed source just skipped
- No error tracking or alerting

### Enhancement: Robust Retry Logic
**Effort**: 🟡 Medium (16 hours)  
**Impact**: High — Improves pipeline reliability

```python
# src/utils/retry.py
import asyncio
from typing import Callable, TypeVar, Optional
from functools import wraps
from loguru import logger

T = TypeVar('T')

class RetryConfig:
    """Configuration for retry behavior."""
    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: tuple = (Exception,)
    ):
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions

def async_retry(config: RetryConfig = None):
    """Async retry decorator with exponential backoff."""
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            attempt = 0
            delay = config.initial_delay
            
            while attempt < config.max_attempts:
                try:
                    return await func(*args, **kwargs)
                except config.retryable_exceptions as e:
                    attempt += 1
                    if attempt >= config.max_attempts:
                        logger.error(
                            f"Max retries ({config.max_attempts}) exceeded "
                            f"for {func.__name__}: {e}"
                        )
                        raise
                    
                    # Calculate backoff with optional jitter
                    if config.jitter:
                        import random
                        jitter = random.uniform(0, delay * 0.1)
                        wait_time = min(delay + jitter, config.max_delay)
                    else:
                        wait_time = min(delay, config.max_delay)
                    
                    logger.warning(
                        f"{func.__name__} failed (attempt {attempt}/{config.max_attempts}), "
                        f"retrying in {wait_time:.1f}s: {e}"
                    )
                    
                    await asyncio.sleep(wait_time)
                    delay *= config.exponential_base
        
        return wrapper
    return decorator

# Usage example
retry_config = RetryConfig(
    max_attempts=5,
    initial_delay=1.0,
    max_delay=30.0,
    retryable_exceptions=(TimeoutError, ConnectionError)
)

@async_retry(retry_config)
async def fetch_gold_with_retries():
    """Fetch gold data with automatic retries."""
    from src.ingestion.gold_fetcher import GoldDataFetcher
    fetcher = GoldDataFetcher(CONFIG)
    return fetcher.fetch_historical()
```

**Integrate with Pipeline**:
```python
# Modify src/ingestion/pipeline_orchestrator.py
from src.utils.retry import async_retry, RetryConfig

class PipelineOrchestrator:
    # ... existing code ...
    
    @async_retry(RetryConfig(max_attempts=5, initial_delay=2.0))
    async def fetch_all_sources(self) -> dict:
        """Fetch data from all sources with retries."""
        results = {}
        
        for source_name, source_config in self.sources.items():
            try:
                logger.info(f"Fetching {source_name}...")
                result = await self._fetch_source(source_name, source_config)
                results[source_name] = result
            except Exception as e:
                logger.error(f"Failed to fetch {source_name}: {e}")
                results[source_name] = {'error': str(e), 'status': 'FAILED'}
        
        return results
```

---

## 2.4 Alternative Data Source Diversification

### Current State
- News sentiment (NewsAPI)
- Google Trends
- COT reports
- ETF flows
- Mining production data
- But: Limited integration, no scoring system

### Enhancement: Alternative Data Aggregator
**Effort**: 🟡 Medium (22 hours)  
**Impact**: Medium — Potentially improves signal quality

```python
# src/ingestion/alternative_data_aggregator.py
import pandas as pd
import numpy as np
from typing import Dict, List
from datetime import datetime, timedelta

class AlternativeDataAggregator:
    """Aggregate and score alternative data sources."""
    
    def __init__(self, config: dict):
        self.config = config
        self.sources = {}
        self.score_weights = {
            'news_sentiment': 0.25,
            'google_trends': 0.15,
            'cot_positioning': 0.20,
            'etf_flows': 0.20,
            'mining_supply': 0.10,
            'central_bank_purchases': 0.10,
        }
    
    def aggregate_sentiment_score(self) -> float:
        """Aggregate sentiment from multiple sources."""
        try:
            scores = []
            
            # News sentiment
            news_score = self._get_news_sentiment()
            if news_score is not None:
                scores.append(news_score * self.score_weights['news_sentiment'])
            
            # Google Trends
            trends_score = self._get_trends_score()
            if trends_score is not None:
                scores.append(trends_score * self.score_weights['google_trends'])
            
            # COT positioning
            cot_score = self._get_cot_score()
            if cot_score is not None:
                scores.append(cot_score * self.score_weights['cot_positioning'])
            
            # ETF flows
            etf_score = self._get_etf_flow_score()
            if etf_score is not None:
                scores.append(etf_score * self.score_weights['etf_flows'])
            
            # Combine
            return sum(scores) / len(scores) if scores else 0.5
            
        except Exception as e:
            logger.error(f"Sentiment aggregation error: {e}")
            return 0.5  # Neutral default
    
    def _get_news_sentiment(self) -> Optional[float]:
        """Fetch and score news sentiment."""
        try:
            from src.ingestion.alternative_data import NewsDataFetcher
            fetcher = NewsDataFetcher(self.config)
            
            # Get recent news
            articles = fetcher.fetch_recent(query="gold price", days=7)
            
            # Score articles (-1 to 1)
            scores = [self._score_text(article['title'] + ' ' + article['description'])
                     for article in articles]
            
            # Average score, normalize to [0, 1]
            avg_score = np.mean(scores) if scores else 0.0
            return (avg_score + 1) / 2  # Convert [-1, 1] to [0, 1]
            
        except Exception as e:
            logger.warning(f"News sentiment fetch failed: {e}")
            return None
    
    def _score_text(self, text: str) -> float:
        """Score text for gold sentiment using keyword analysis."""
        keywords = {
            'positive': ['surge', 'rally', 'bullish', 'buying', 'demand', 'flight-to-safety',
                        'uncertainty', 'crisis', 'recession', 'hedge', 'safe-haven'],
            'negative': ['decline', 'weakness', 'bearish', 'selling', 'oversold', 'loss',
                        'weakness', 'unwinding'],
        }
        
        text_lower = text.lower()
        
        pos_count = sum(text_lower.count(kw) for kw in keywords['positive'])
        neg_count = sum(text_lower.count(kw) for kw in keywords['negative'])
        
        total = pos_count + neg_count
        if total == 0:
            return 0.0
        
        return (pos_count - neg_count) / total
    
    def _get_trends_score(self) -> Optional[float]:
        """Get Google Trends score for gold keywords."""
        try:
            from src.ingestion.alternative_data import GoogleTrendsFetcher
            fetcher = GoogleTrendsFetcher(self.config)
            
            keywords = ['buy gold', 'gold price', 'gold investment']
            scores = []
            
            for kw in keywords:
                trend_data = fetcher.get_trend(kw, days=7)
                # Normalize to [0, 1]
                normalized = trend_data['value'].mean() / 100.0
                scores.append(normalized)
            
            return np.mean(scores)
            
        except Exception as e:
            logger.warning(f"Trends fetch failed: {e}")
            return None
    
    def _get_cot_score(self) -> Optional[float]:
        """Get COT positioning score."""
        try:
            from src.ingestion.alternative_data import COTFetcher
            fetcher = COTFetcher(self.config)
            
            cot_data = fetcher.get_latest()
            
            # Extract positioning
            large_spec_long = cot_data['large_speculator_long_percent']
            large_spec_short = cot_data['large_speculator_short_percent']
            
            # Score: positive if specs heavily long
            score = (large_spec_long - large_spec_short) / 100.0
            return (score + 1) / 2  # Normalize to [0, 1]
            
        except Exception as e:
            logger.warning(f"COT fetch failed: {e}")
            return None
    
    def _get_etf_flow_score(self) -> Optional[float]:
        """Get ETF flow score."""
        try:
            from src.ingestion.alternative_data import ETFFlowFetcher
            fetcher = ETFFlowFetcher(self.config)
            
            flows = fetcher.get_weekly_flows(['GLD', 'IAU'])
            
            # Score based on net inflows
            total_flow = sum(f['net_flow'] for f in flows)
            
            # Normalize (expecting ~$10M net flow = neutral)
            max_flow = 50_000_000  # $50M
            normalized = min(max(total_flow / max_flow, -1), 1)
            
            return (normalized + 1) / 2
            
        except Exception as e:
            logger.warning(f"ETF flow fetch failed: {e}")
            return None
    
    async def store_aggregated_score(self):
        """Store aggregated sentiment in feature store."""
        try:
            score = self.aggregate_sentiment_score()
            
            from src.features.feature_store import FeatureStore
            fs = FeatureStore(self.config)
            
            fs.store_features('alternative_data', {
                'sentiment_score': score,
                'timestamp': datetime.now().isoformat(),
                'components': {
                    'news': self._get_news_sentiment(),
                    'trends': self._get_trends_score(),
                    'cot': self._get_cot_score(),
                    'etf_flows': self._get_etf_flow_score(),
                }
            })
            
            logger.info(f"Alternative data sentiment score: {score:.3f}")
            
        except Exception as e:
            logger.error(f"Failed to store aggregated score: {e}")
```

---

---

# PHASE 3: MATHEMATICAL MODELING

## Current Capabilities
✅ Wavelet denoising (DWT with db4)  
✅ HMM regime detection (3 regimes)  
✅ LSTM temporal (bidirectional, 3-layer)  
✅ Temporal Fusion Transformer (TFT)  
✅ Genetic Algorithm optimization  
✅ Ensemble stacking (6 models)  
✅ Model serialization (joblib, torch)  
✅ Training pipeline  
✅ 50 tests passing

---

## 3.1 Hyperparameter Optimization

### Current State
- Models have hard-coded hyperparameters
- No systematic tuning
- No automated HP search

### Enhancement: Optuna-Based Hyperparameter Tuning
**Effort**: 🟡 Medium (25 hours)  
**Impact**: High — Potentially +5-10% performance improvement

```python
# src/models/hyperparameter_optimizer.py
import optuna
from optuna.pruners import MedianPruner
from optuna.samplers import TPESampler
import pandas as pd
import numpy as np
from typing import Callable, Dict, Any, Tuple
from loguru import logger

class HyperparameterOptimizer:
    """Automated hyperparameter tuning with Optuna."""
    
    def __init__(
        self,
        config: dict,
        cv_folds: int = 5,
        n_trials: int = 100,
        timeout: int = 3600
    ):
        self.config = config
        self.cv_folds = cv_folds
        self.n_trials = n_trials
        self.timeout = timeout
        self.best_params = {}
        self.best_score = -np.inf
    
    def optimize_lstm(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame,
        y_val: pd.Series
    ) -> Dict[str, Any]:
        """Optimize LSTM hyperparameters."""
        
        def objective(trial: optuna.Trial) -> float:
            """Objective function for LSTM tuning."""
            
            # Suggest hyperparameters
            hidden_size = trial.suggest_int('hidden_size', 32, 512, step=32)
            num_layers = trial.suggest_int('num_layers', 1, 5)
            dropout = trial.suggest_float('dropout', 0.0, 0.5, step=0.1)
            learning_rate = trial.suggest_float('learning_rate', 1e-5, 1e-2, log=True)
            batch_size = trial.suggest_categorical('batch_size', [16, 32, 64, 128])
            weight_decay = trial.suggest_float('weight_decay', 1e-6, 1e-2, log=True)
            
            try:
                from src.models.lstm_temporal import BidirectionalLSTM
                
                model = BidirectionalLSTM(
                    input_size=X_train.shape[1],
                    hidden_size=hidden_size,
                    num_layers=num_layers,
                    dropout=dropout,
                    num_classes=3
                )
                
                # Train model with early stopping
                val_score = self._train_lstm(
                    model,
                    X_train, y_train,
                    X_val, y_val,
                    learning_rate=learning_rate,
                    batch_size=batch_size,
                    weight_decay=weight_decay,
                    max_epochs=50
                )
                
                # Report intermediate values for pruning
                trial.report(val_score, step=0)
                
                return val_score
                
            except Exception as e:
                logger.error(f"LSTM trial failed: {e}")
                return -np.inf
        
        # Create study with TPE sampler and median pruner
        sampler = TPESampler(seed=42)
        pruner = MedianPruner()
        
        study = optuna.create_study(
            direction='maximize',
            sampler=sampler,
            pruner=pruner,
            study_name='lstm_tuning'
        )
        
        # Optimize
        logger.info(f"Starting LSTM hyperparameter optimization ({self.n_trials} trials)...")
        study.optimize(
            objective,
            n_trials=self.n_trials,
            timeout=self.timeout,
            show_progress_bar=True
        )
        
        # Extract best params
        self.best_params['lstm'] = study.best_params
        self.best_score = study.best_value
        
        logger.info(f"Best LSTM Sharpe: {self.best_score:.4f}")
        logger.info(f"Best hyperparameters: {self.best_params['lstm']}")
        
        return self.best_params['lstm']
    
    def optimize_hmm(
        self,
        X_train: pd.DataFrame,
    ) -> Dict[str, Any]:
        """Optimize HMM hyperparameters."""
        
        def objective(trial: optuna.Trial) -> float:
            """Objective function for HMM tuning."""
            
            n_components = trial.suggest_int('n_components', 2, 5)
            covariance_type = trial.suggest_categorical(
                'covariance_type',
                ['spherical', 'tied', 'diag', 'full']
            )
            n_iter = trial.suggest_int('n_iter', 100, 1000, step=100)
            
            try:
                from src.models.hmm_regime import HMMRegimeDetector
                
                detector = HMMRegimeDetector(
                    n_regimes=n_components,
                    covariance_type=covariance_type,
                    n_iter=n_iter
                )
                
                # Train and evaluate
                detector.train(X_train)
                
                # Score based on log-likelihood (higher is better)
                score = detector.model.score(X_train)
                
                return score
                
            except Exception as e:
                logger.error(f"HMM trial failed: {e}")
                return -np.inf
        
        sampler = TPESampler(seed=42)
        study = optuna.create_study(direction='maximize', sampler=sampler)
        
        logger.info(f"Starting HMM hyperparameter optimization...")
        study.optimize(objective, n_trials=50, timeout=1800)
        
        self.best_params['hmm'] = study.best_params
        logger.info(f"Best HMM score: {study.best_value:.4f}")
        
        return self.best_params['hmm']
    
    def optimize_ensemble(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame,
        y_val: pd.Series
    ) -> Dict[str, Any]:
        """Optimize ensemble stacking weights."""
        
        def objective(trial: optuna.Trial) -> float:
            """Objective function for ensemble weight tuning."""
            
            # Suggest model weights
            weights = [
                trial.suggest_float(f'weight_wavelet', 0.0, 1.0),
                trial.suggest_float(f'weight_hmm', 0.0, 1.0),
                trial.suggest_float(f'weight_lstm', 0.0, 1.0),
                trial.suggest_float(f'weight_tft', 0.0, 1.0),
                trial.suggest_float(f'weight_genetic', 0.0, 1.0),
            ]
            
            # Normalize
            weights = np.array(weights) / sum(weights)
            
            try:
                from src.models.ensemble_stacking import EnsembleStacker
                
                ensemble = EnsembleStacker(self.config)
                ensemble.set_weights(weights)
                
                # Evaluate on validation set
                signal, conf = ensemble.predict(X_val)
                
                # Score based on accuracy
                accuracy = (signal == y_val).mean()
                
                return accuracy
                
            except Exception as e:
                logger.error(f"Ensemble trial failed: {e}")
                return 0.0
        
        sampler = TPESampler(seed=42)
        study = optuna.create_study(direction='maximize', sampler=sampler)
        
        logger.info("Starting ensemble weight optimization...")
        study.optimize(objective, n_trials=50, timeout=1800)
        
        self.best_params['ensemble_weights'] = study.best_params
        logger.info(f"Best ensemble accuracy: {study.best_value:.4f}")
        
        return self.best_params['ensemble_weights']
    
    def _train_lstm(self, model, X_train, y_train, X_val, y_val,
                   learning_rate, batch_size, weight_decay, max_epochs):
        """Train LSTM and return validation score."""
        # Training implementation
        # Returns validation metric
        pass
    
    def save_best_params(self, path: str) -> None:
        """Save best hyperparameters to file."""
        import json
        with open(path, 'w') as f:
            json.dump(self.best_params, f, indent=2)
        logger.info(f"Saved best hyperparameters to {path}")
    
    def load_best_params(self, path: str) -> Dict[str, Any]:
        """Load best hyperparameters from file."""
        import json
        with open(path, 'r') as f:
            self.best_params = json.load(f)
        return self.best_params
```

**Integration**:
```python
# scripts/optimize_models.py
import asyncio
from src.models.hyperparameter_optimizer import HyperparameterOptimizer
from src.utils.config import load_config

async def main():
    config = load_config()
    
    # Load data
    X_train, y_train, X_val, y_val = load_training_data()
    
    # Run optimization
    optimizer = HyperparameterOptimizer(
        config,
        cv_folds=5,
        n_trials=100,
        timeout=7200  # 2 hours
    )
    
    # Optimize each component
    lstm_params = optimizer.optimize_lstm(X_train, y_train, X_val, y_val)
    hmm_params = optimizer.optimize_hmm(X_train)
    ensemble_weights = optimizer.optimize_ensemble(X_train, y_train, X_val, y_val)
    
    # Save
    optimizer.save_best_params('models/best_hyperparameters.json')

if __name__ == '__main__':
    asyncio.run(main())
```

---

## 3.2 Model Explainability & Interpretability

### Current State
- Models make predictions but outputs are "black box"
- No SHAP values, LIME, or feature importance tracking
- Difficult to debug why model made specific prediction

### Enhancement: SHAP-Based Explainability
**Effort**: 🟡 Medium (20 hours)  
**Impact**: Medium — Improves model trustworthiness, aids debugging

```python
# src/models/explainability.py
import shap
import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
from loguru import logger

class ModelExplainer:
    """Generate SHAP-based explanations for model predictions."""
    
    def __init__(self, model, model_type: str = 'ensemble'):
        self.model = model
        self.model_type = model_type
        self.explainer = None
        
    def initialize_explainer(self, X_background: pd.DataFrame):
        """Initialize SHAP explainer with background data sample."""
        try:
            # Use 100 background samples for speed
            X_background_sample = X_background.sample(
                min(100, len(X_background)),
                random_state=42
            )
            
            if self.model_type == 'tree_based':
                # TreeExplainer for XGBoost/LightGBM models
                self.explainer = shap.TreeExplainer(self.model)
            elif self.model_type == 'neural_net':
                # DeepExplainer for neural networks
                self.explainer = shap.DeepExplainer(
                    self.model,
                    X_background_sample.values
                )
            else:
                # Kernel explainer (model-agnostic, slower)
                self.explainer = shap.KernelExplainer(
                    self.model.predict,
                    X_background_sample.values
                )
            
            logger.info(f"✓ SHAP {self.model_type} explainer initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize SHAP explainer: {e}")
    
    def explain_prediction(
        self,
        X: pd.DataFrame,
        feature_names: Optional[list] = None
    ) -> Dict:
        """Generate SHAP explanation for a prediction."""
        
        if self.explainer is None:
            raise ValueError("Explainer not initialized. Call initialize_explainer() first.")
        
        try:
            # Get SHAP values
            shap_values = self.explainer.shap_values(X.values)
            
            # Convert to DataFrame for readability
            if isinstance(shap_values, list):
                # Multiple output classes
                shap_df = pd.DataFrame(
                    shap_values[0],  # Use first class
                    columns=feature_names or X.columns
                )
            else:
                shap_df = pd.DataFrame(
                    shap_values,
                    columns=feature_names or X.columns
                )
            
            # Calculate feature importance
            feature_importance = pd.DataFrame({
                'feature': shap_df.columns,
                'importance': np.abs(shap_df).mean(0)
            }).sort_values('importance', ascending=False)
            
            return {
                'shap_values': shap_values,
                'feature_importance': feature_importance.to_dict('records'),
                'top_features': feature_importance.head(10)['feature'].tolist(),
            }
            
        except Exception as e:
            logger.error(f"SHAP explanation failed: {e}")
            return {'error': str(e)}
    
    def get_prediction_summary(
        self,
        X: pd.DataFrame,
        prediction: int,
        top_k: int = 5
    ) -> str:
        """Generate human-readable summary of prediction."""
        
        try:
            explanation = self.explain_prediction(X)
            
            if 'error' in explanation:
                return f"Could not explain prediction: {explanation['error']}"
            
            top_features = explanation['feature_importance'][:top_k]
            
            # Generate summary
            summary = f"Model predicted: {['SHORT', 'FLAT', 'LONG'][prediction]}\n\n"
            summary += "Top contributing features:\n"
            
            for i, item in enumerate(top_features, 1):
                summary += f"  {i}. {item['feature']}: {item['importance']:.4f}\n"
            
            return summary
            
        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            return str(e)
```

**Add to API**:
```python
# src/api/app.py
@app.post("/explain")
async def explain_prediction(request: Dict):
    """Get SHAP explanation for a prediction."""
    try:
        from src.models.explainability import ModelExplainer
        
        # Load model
        ensemble = load_ensemble_model()
        explainer = ModelExplainer(ensemble, model_type='ensemble')
        
        # Get explanation
        X = pd.DataFrame([request['features']])
        explanation = explainer.explain_prediction(X)
        
        return {
            'status': 'success',
            'explanation': explanation,
            'summary': explainer.get_prediction_summary(X, request.get('prediction', 0))
        }
        
    except Exception as e:
        logger.error(f"Explanation request failed: {e}")
        return {'status': 'error', 'error': str(e)}
```

---

## 3.3 Model Validation & Out-of-Sample Testing

### Current State
- Walk-forward analysis (Phase 5)
- CPCV framework
- DSR validation
- But: Limited real-time monitoring of model performance

### Enhancement: Model Performance Monitoring
**Effort**: 🟡 Medium (18 hours)  
**Impact**: High — Detects model decay early

```python
# src/models/performance_monitor.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from collections import deque
from loguru import logger

class ModelPerformanceMonitor:
    """Monitor model performance metrics in real-time."""
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        
        # Rolling windows for metrics
        self.predictions = deque(maxlen=window_size)
        self.actuals = deque(maxlen=window_size)
        self.confidences = deque(maxlen=window_size)
        self.timestamps = deque(maxlen=window_size)
        
        self.performance_history = []
    
    def record_prediction(
        self,
        prediction: int,
        actual: int,
        confidence: float,
        timestamp: datetime = None
    ):
        """Record a prediction for monitoring."""
        if timestamp is None:
            timestamp = datetime.now()
        
        self.predictions.append(prediction)
        self.actuals.append(actual)
        self.confidences.append(confidence)
        self.timestamps.append(timestamp)
        
        # Update performance stats
        self._update_performance_stats()
    
    def _update_performance_stats(self) -> Dict:
        """Calculate current performance metrics."""
        if len(self.predictions) < 10:
            return {}
        
        predictions = np.array(self.predictions)
        actuals = np.array(self.actuals)
        confidences = np.array(self.confidences)
        
        # Accuracy
        accuracy = (predictions == actuals).mean()
        
        # Directional accuracy (for long/short)
        direction_matches = ((predictions > 0) & (actuals > 0)) | \
                           ((predictions < 0) & (actuals < 0))
        directional_accuracy = direction_matches.mean()
        
        # Calibration: avg confidence vs actual accuracy
        calibration_error = abs(confidences.mean() - accuracy)
        
        # Precision per class
        precision_long = (predictions[predictions == 1] == actuals[predictions == 1]).mean()
        precision_short = (predictions[predictions == -1] == actuals[predictions == -1]).mean()
        precision_flat = (predictions[predictions == 0] == actuals[predictions == 0]).mean()
        
        stats = {
            'timestamp': datetime.now(),
            'accuracy': accuracy,
            'directional_accuracy': directional_accuracy,
            'calibration_error': calibration_error,
            'avg_confidence': confidences.mean(),
            'precision_long': precision_long,
            'precision_short': precision_short,
            'precision_flat': precision_flat,
            'sample_count': len(self.predictions),
        }
        
        self.performance_history.append(stats)
        
        # Check for performance degradation
        if len(self.performance_history) > 10:
            self._check_performance_degradation()
        
        return stats
    
    def _check_performance_degradation(self) -> None:
        """Alert if performance has degraded significantly."""
        if len(self.performance_history) < 20:
            return
        
        # Compare recent 10 vs earlier 10
        recent = np.array([s['accuracy'] for s in self.performance_history[-10:]])
        earlier = np.array([s['accuracy'] for s in self.performance_history[-20:-10]])
        
        degradation = earlier.mean() - recent.mean()
        
        if degradation > 0.05:  # >5% drop
            logger.warning(
                f"⚠ Model performance degraded: {earlier.mean():.2%} → {recent.mean():.2%} "
                f"({degradation:.2%} drop)"
            )
    
    def get_summary(self) -> Dict:
        """Get summary of current model performance."""
        if not self.performance_history:
            return {'status': 'no_data'}
        
        recent_stats = self.performance_history[-1]
        
        # Trend analysis (last 20 samples)
        if len(self.performance_history) > 20:
            trend = self.performance_history[-20:]
            accuracy_trend = [s['accuracy'] for s in trend]
            accuracy_change = accuracy_trend[-1] - accuracy_trend[0]
        else:
            accuracy_change = 0
        
        return {
            'current_accuracy': recent_stats['accuracy'],
            'accuracy_trend': accuracy_change,
            'directional_accuracy': recent_stats['directional_accuracy'],
            'calibration_error': recent_stats['calibration_error'],
            'avg_confidence': recent_stats['avg_confidence'],
            'sample_count': recent_stats['sample_count'],
            'last_updated': recent_stats['timestamp'].isoformat(),
        }
```

---

## 3.4 Automated Model Retraining

### Current State
- Models trained once, stored in MLflow
- No automated retraining schedule
- No monitoring for model drift

### Enhancement: Automatic Retraining Pipeline
**Effort**: 🟡 Medium (22 hours)  
**Impact**: High — Keeps models current with market conditions

```python
# src/models/retraining_scheduler.py
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional
from loguru import logger
import pandas as pd

class RetraniningScheduler:
    """Automatically retrain models based on triggers."""
    
    def __init__(self, config: dict):
        self.config = config
        retrain_cfg = config.get('models', {}).get('retraining', {})
        
        self.retrain_frequency = retrain_cfg.get('frequency_days', 7)
        self.performance_threshold = retrain_cfg.get('performance_threshold', 0.55)
        self.drift_threshold = retrain_cfg.get('drift_threshold', 0.10)
        
        self.last_retrain_time = None
        self.performance_monitor = None
    
    async def should_retrain(self) -> Dict[str, any]:
        """Determine if model should be retrained."""
        reasons = []
        should_retrain = False
        
        # Check 1: Schedule-based retraining
        if self.last_retrain_time is None or \
           (datetime.now() - self.last_retrain_time).days >= self.retrain_frequency:
            reasons.append('scheduled')
            should_retrain = True
        
        # Check 2: Performance degradation
        try:
            perf_summary = self.performance_monitor.get_summary()
            if perf_summary.get('current_accuracy', 0.5) < self.performance_threshold:
                reasons.append('performance_degradation')
                should_retrain = True
        except:
            pass
        
        # Check 3: Data drift detection
        try:
            drift_score = await self._detect_data_drift()
            if drift_score > self.drift_threshold:
                reasons.append(f'data_drift_{drift_score:.3f}')
                should_retrain = True
        except:
            pass
        
        return {
            'should_retrain': should_retrain,
            'reasons': reasons,
            'timestamp': datetime.now().isoformat(),
        }
    
    async def _detect_data_drift(self) -> float:
        """Detect concept drift using Kolmogorov-Smirnov test."""
        try:
            from scipy.stats import ks_2samp
            
            # Load recent vs historical features
            recent_features = self._load_recent_features(days=30)
            historical_features = self._load_historical_features(
                days_ago_start=60,
                days_ago_end=30
            )
            
            # KS test per feature
            drift_scores = []
            for col in recent_features.columns:
                stat, pvalue = ks_2samp(
                    recent_features[col],
                    historical_features[col]
                )
                drift_scores.append(stat)
            
            # Average drift across features
            return np.mean(drift_scores)
            
        except Exception as e:
            logger.error(f"Drift detection failed: {e}")
            return 0.0
    
    async def retrain_all_models(self) -> Dict:
        """Retrain all models."""
        logger.info("=" * 60)
        logger.info("STARTING MODEL RETRAINING")
        logger.info("=" * 60)
        
        results = {}
        
        try:
            # Load latest training data
            X_train, y_train, X_val, y_val = await self._load_training_data()
            
            # Retrain each model
            results['wavelet'] = await self._retrain_wavelet()
            results['hmm'] = await self._retrain_hmm(X_train, y_train)
            results['lstm'] = await self._retrain_lstm(X_train, y_train, X_val, y_val)
            results['tft'] = await self._retrain_tft(X_train, y_train, X_val, y_val)
            results['genetic'] = await self._retrain_genetic(X_train, y_train)
            results['ensemble'] = await self._retrain_ensemble(X_train, y_train)
            
            # Update last retrain time
            self.last_retrain_time = datetime.now()
            
            # Log results
            logger.info("RETRAINING COMPLETE")
            for model_name, result in results.items():
                status = "✓" if result.get('success') else "✗"
                logger.info(f"  {status} {model_name}: {result.get('message', 'Unknown')}")
            
            return results
            
        except Exception as e:
            logger.error(f"Retraining failed: {e}")
            return {'error': str(e)}
    
    async def _retrain_lstm(self, X_train, y_train, X_val, y_val):
        """Retrain LSTM model."""
        try:
            from src.models.lstm_temporal import BidirectionalLSTM
            
            logger.info("Retraining LSTM...")
            
            model = BidirectionalLSTM(
                input_size=X_train.shape[1],
                hidden_size=128,
                num_layers=3,
                dropout=0.2,
            )
            
            # Train
            metrics = model.train(X_train, y_train)
            
            # Validate
            val_signal, val_conf = model.predict(X_val)
            val_accuracy = (val_signal == y_val).mean()
            
            logger.info(f"  LSTM validation accuracy: {val_accuracy:.3f}")
            
            # Save
            model.save('models/lstm_latest.pt')
            
            return {
                'success': True,
                'message': f'Accuracy: {val_accuracy:.3f}',
                'metrics': metrics,
            }
            
        except Exception as e:
            logger.error(f"LSTM retraining failed: {e}")
            return {'success': False, 'error': str(e)}
    
    # Similar methods for other models...
    
    async def _load_training_data(self) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]:
        """Load latest training data from QuestDB/feature store."""
        # Implementation
        pass
    
    def _load_recent_features(self, days: int) -> pd.DataFrame:
        """Load recent features for drift detection."""
        # Implementation
        pass
    
    def _load_historical_features(self, days_ago_start: int, days_ago_end: int) -> pd.DataFrame:
        """Load historical features for drift detection."""
        # Implementation
        pass
```

**Integrate with Scheduler**:
```python
# scripts/daily_scheduler.py
async def run_daily_tasks():
    # ... existing tasks ...
    
    # Check if models need retraining
    retraining_scheduler = RetraniningScheduler(config)
    retrain_check = await retraining_scheduler.should_retrain()
    
    if retrain_check['should_retrain']:
        logger.info(f"Retraining triggered: {retrain_check['reasons']}")
        retrain_results = await retraining_scheduler.retrain_all_models()
        health_data['retraining'] = retrain_results
    else:
        health_data['retraining'] = {'skipped': 'Not needed yet'}
```

---

---

# PHASE 4: RISK MANAGEMENT

## Current Capabilities
✅ Kelly Criterion sizing (regime-aware)  
✅ Circuit breakers (6 types)  
✅ Position tracking  
✅ GPU Monte Carlo VaR  
✅ Meta-labeling framework (critic model)  
✅ Trade history tracking  
✅ 71 integration tests

---

## 4.1 Advanced Risk Metrics

### Current State
- VaR (95%) via Monte Carlo
- CVaR (99%)
- Maximum Drawdown
- Sharpe Ratio
- But: Missing several advanced metrics

### Enhancement: Extended Risk Metrics Suite
**Effort**: 🟡 Medium (20 hours)  
**Impact**: High — Better risk visibility

```python
# src/risk/advanced_metrics.py
import numpy as np
import pandas as pd
from typing import Tuple, Dict, Optional
from scipy.stats import norm

class AdvancedRiskMetrics:
    """Calculate advanced risk metrics beyond basic VaR."""
    
    @staticmethod
    def expected_shortfall(returns: np.ndarray, confidence: float = 0.95) -> float:
        """
        Expected Shortfall (Conditional VaR) - Average loss in worst-case scenarios.
        More sensitive to tail risk than VaR.
        """
        var = np.percentile(returns, (1 - confidence) * 100)
        es = returns[returns <= var].mean()
        return es
    
    @staticmethod
    def maximum_drawdown_duration(equity_curve: np.ndarray) -> int:
        """
        Maximum Drawdown Duration - Longest period for recovery after peak loss.
        Useful for understanding recovery time.
        """
        cummax = np.maximum.accumulate(equity_curve)
        drawdown = (equity_curve - cummax) / cummax
        
        # Find all drawdown periods
        in_drawdown = drawdown < 0
        
        # Calculate durations
        durations = []
        current_duration = 0
        
        for in_dd in in_drawdown:
            if in_dd:
                current_duration += 1
            else:
                if current_duration > 0:
                    durations.append(current_duration)
                current_duration = 0
        
        return max(durations) if durations else 0
    
    @staticmethod
    def recovery_factor(total_return: float, max_drawdown: float) -> float:
        """
        Recovery Factor = Total Return / Maximum Drawdown.
        Higher is better (return gained per unit of max risk taken).
        """
        if max_drawdown == 0:
            return np.inf
        return total_return / abs(max_drawdown)
    
    @staticmethod
    def calmar_ratio(annual_return: float, max_drawdown: float) -> float:
        """
        Calmar Ratio = Annual Return / Maximum Drawdown.
        Measures return relative to maximum downside risk.
        """
        if max_drawdown == 0:
            return np.inf
        return annual_return / abs(max_drawdown)
    
    @staticmethod
    def omega_ratio(returns: np.ndarray, threshold: float = 0.0) -> float:
        """
        Omega Ratio = Gains above threshold / Losses below threshold.
        Measures probability-weighted ratio of gains to losses.
        """
        excess_returns = returns - threshold
        gains = excess_returns[excess_returns > 0].sum()
        losses = abs(excess_returns[excess_returns < 0].sum())
        
        if losses == 0:
            return np.inf if gains > 0 else 0
        return gains / losses
    
    @staticmethod
    def sortino_ratio(returns: np.ndarray, risk_free_rate: float = 0.0) -> float:
        """
        Sortino Ratio = (Annual Return - Risk-free Rate) / Downside Deviation.
        Only penalizes downside volatility (unlike Sharpe).
        """
        excess_return = returns.mean() - risk_free_rate
        downside_returns = returns[returns < risk_free_rate]
        downside_std = np.sqrt(np.mean(downside_returns ** 2))
        
        if downside_std == 0:
            return np.inf
        
        annual_excess = excess_return * 252
        annual_downside = downside_std * np.sqrt(252)
        
        return annual_excess / annual_downside
    
    @staticmethod
    def painindex(equity_curve: np.ndarray) -> float:
        """
        Pain Index - Sum of all drawdowns.
        Measures total pain experienced during strategy.
        """
        cummax = np.maximum.accumulate(equity_curve)
        drawdown = (equity_curve - cummax) / cummax
        return -np.sum(drawdown[drawdown < 0])
    
    @staticmethod
    def ulcer_index(equity_curve: np.ndarray) -> float:
        """
        Ulcer Index - Square root of average squared drawdowns.
        Like Pain Index but emphasizes larger drawdowns.
        """
        cummax = np.maximum.accumulate(equity_curve)
        drawdown_pct = 100 * (equity_curve - cummax) / cummax
        downside_sum = np.sum(np.where(drawdown_pct < 0, drawdown_pct ** 2, 0))
        return np.sqrt(downside_sum / len(equity_curve))
    
    @staticmethod
    def var_conditional(pnl: np.ndarray, confidence: float = 0.95, method: str = 'historical') -> float:
        """
        Conditional Value at Risk (CVaR) - Average loss in worst-case scenarios.
        
        Methods:
          - 'historical': Historical CVaR (non-parametric)
          - 'parametric': Parametric CVaR (assumes normal distribution)
          - 'cornish_fisher': CVaR with Cornish-Fisher VaR
        """
        if method == 'historical':
            threshold = np.percentile(pnl, (1 - confidence) * 100)
            return pnl[pnl <= threshold].mean()
        
        elif method == 'parametric':
            # Parametric CVaR (assuming normal)
            z_score = norm.ppf(1 - confidence)
            mean = pnl.mean()
            std = pnl.std()
            
            # PDF at VaR point
            pdf_var = norm.pdf(z_score)
            
            return mean + std * (pdf_var / (1 - confidence))
        
        elif method == 'cornish_fisher':
            # Cornish-Fisher CVaR (accounts for skewness/kurtosis)
            z_score = norm.ppf(1 - confidence)
            skew = (pnl ** 3).mean() / (pnl.std() ** 3)
            kurt = (pnl ** 4).mean() / (pnl.std() ** 4) - 3
            
            cf_var = z_score + (z_score ** 2 - 1) / 6 * skew + \
                     (z_score ** 3 - 3 * z_score) / 24 * kurt
            
            mean = pnl.mean()
            std = pnl.std()
            pdf_cf_var = norm.pdf(cf_var)
            
            return mean + std * (pdf_cf_var / (1 - confidence))
    
    @staticmethod
    def tail_ratio(returns: np.ndarray, confidence: float = 0.95) -> float:
        """
        Tail Ratio = Abs(5% VaR) / 95% VaR.
        Measures asymmetry of tail risk (upside vs downside).
        Ratio > 1 means worse downside tail.
        """
        upside_tail = np.percentile(returns, confidence * 100)
        downside_tail = np.percentile(returns, (1 - confidence) * 100)
        
        if upside_tail == 0:
            return np.inf
        
        return abs(downside_tail) / upside_tail
    
    @staticmethod
    def get_all_metrics(equity_curve: np.ndarray, returns: np.ndarray) -> Dict:
        """Calculate all advanced risk metrics."""
        total_return = (equity_curve[-1] - equity_curve[0]) / equity_curve[0]
        annual_return = total_return / ((len(equity_curve) - 1) / 252)
        max_dd = ((equity_curve.max() - equity_curve.min()) / equity_curve.max())
        
        metrics = {
            'expected_shortfall_95': AdvancedRiskMetrics.expected_shortfall(returns, 0.95),
            'expected_shortfall_99': AdvancedRiskMetrics.expected_shortfall(returns, 0.99),
            'max_dd_duration_days': AdvancedRiskMetrics.maximum_drawdown_duration(equity_curve),
            'recovery_factor': AdvancedRiskMetrics.recovery_factor(total_return, max_dd),
            'calmar_ratio': AdvancedRiskMetrics.calmar_ratio(annual_return, max_dd),
            'omega_ratio': AdvancedRiskMetrics.omega_ratio(returns),
            'sortino_ratio': AdvancedRiskMetrics.sortino_ratio(returns),
            'pain_index': AdvancedRiskMetrics.painindex(equity_curve),
            'ulcer_index': AdvancedRiskMetrics.ulcer_index(equity_curve),
            'var_cond_95': AdvancedRiskMetrics.var_conditional(returns, 0.95, method='historical'),
            'var_cond_99': AdvancedRiskMetrics.var_conditional(returns, 0.99, method='cornish_fisher'),
            'tail_ratio_95': AdvancedRiskMetrics.tail_ratio(returns, 0.95),
        }
        
        return metrics
```

---

## 4.2 Stress Testing Framework

### Current State
- GPU Monte Carlo simulations
- Basic scenario analysis
- But: No systematic stress test suite, no recovery strategies

### Enhancement: Comprehensive Stress Testing
**Effort**: 🔴 High (35 hours)  
**Impact**: Critical — Essential for production readiness

```python
# src/risk/stress_tester.py
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from loguru import logger
import cupy as cp

class StressTestScenario:
    """Represents a single stress test scenario."""
    
    def __init__(self, name: str, description: str, shocks: Dict[str, float]):
        self.name = name
        self.description = description
        self.shocks = shocks  # {asset: shock_amount}
    
    def __repr__(self):
        return f"StressTestScenario({self.name})"

class StressTester:
    """Comprehensive stress testing framework."""
    
    def __init__(self, config: dict):
        self.config = config
        self.scenarios = self._build_default_scenarios()
        self.results = {}
    
    def _build_default_scenarios(self) -> List[StressTestScenario]:
        """Build standard stress test scenarios."""
        return [
            StressTestScenario(
                name='USD Rally',
                description='USD appreciates 3% (gold-negative)',
                shocks={'dxy': 0.03, 'gold': -0.025}
            ),
            StressTestScenario(
                name='USD Crash',
                description='USD depreciates 3% (gold-positive)',
                shocks={'dxy': -0.03, 'gold': 0.025}
            ),
            StressTestScenario(
                name='Rate Surprise',
                description='Fed unexpectedly raises rates 50bps',
                shocks={'rates': 0.005, 'gold': -0.02}
            ),
            StressTestScenario(
                name='Geopolitical Crisis',
                description='Safe-haven flight (VIX spike to 40+)',
                shocks={'vix': 0.30, 'gold': 0.08, 'stocks': -0.10}
            ),
            StressTestScenario(
                name='Liquidity Crisis',
                description='Bid-ask spreads widen 5x',
                shocks={'spread': 5.0}
            ),
            StressTestScenario(
                name='Flash Crash',
                description='Gold drops 5% in 5 minutes',
                shocks={'gold': -0.05}
            ),
            StressTestScenario(
                name='China Slowdown',
                description='Significant Chinese growth slowdown',
                shocks={'cny': -0.05, 'gold': 0.03}
            ),
            StressTestScenario(
                name='Stagflation',
                description='High inflation + slow growth',
                shocks={'inflation': 0.02, 'growth': -0.05, 'gold': 0.10}
            ),
        ]
    
    def add_custom_scenario(self, scenario: StressTestScenario) -> None:
        """Add custom stress test scenario."""
        self.scenarios.append(scenario)
        logger.info(f"Added scenario: {scenario.name}")
    
    async def run_all_stress_tests(
        self,
        current_position: float,
        current_portfolio_value: float,
        current_prices: Dict[str, float],
        n_simulations: int = 10000
    ) -> Dict:
        """Run all stress test scenarios."""
        
        results_summary = {
            'timestamp': pd.Timestamp.now().isoformat(),
            'position': current_position,
            'portfolio_value': current_portfolio_value,
            'scenarios': {}
        }
        
        for scenario in self.scenarios:
            try:
                logger.info(f"Running stress test: {scenario.name}...")
                
                scenario_result = await self._run_scenario(
                    scenario,
                    current_position,
                    current_portfolio_value,
                    current_prices,
                    n_simulations
                )
                
                results_summary['scenarios'][scenario.name] = scenario_result
                
            except Exception as e:
                logger.error(f"Stress test {scenario.name} failed: {e}")
                results_summary['scenarios'][scenario.name] = {'error': str(e)}
        
        self.results = results_summary
        return results_summary
    
    async def _run_scenario(
        self,
        scenario: StressTestScenario,
        current_position: float,
        portfolio_value: float,
        prices: Dict[str, float],
        n_sims: int
    ) -> Dict:
        """Run a single stress test scenario."""
        
        try:
            # Apply shocks to current prices
            shocked_prices = prices.copy()
            for asset, shock in scenario.shocks.items():
                if asset in shocked_prices:
                    shocked_prices[asset] *= (1 + shock)
            
            # Calculate P&L impact
            if 'gold' in shocked_prices:
                gold_pnl = current_position * (shocked_prices['gold'] - prices.get('gold', prices.get('gold', 0)))
            else:
                gold_pnl = 0
            
            # Calculate portfolio impact
            new_portfolio_value = portfolio_value + gold_pnl
            portfolio_return = (new_portfolio_value - portfolio_value) / portfolio_value
            
            # Monte Carlo simulation for 1-hour forward looking
            mc_results = await self._monte_carlo_scenario(
                scenario,
                shocked_prices,
                current_position,
                portfolio_value,
                n_sims
            )
            
            return {
                'scenario': scenario.description,
                'immediate_pnl': gold_pnl,
                'immediate_return_pct': portfolio_return * 100,
                'new_portfolio_value': new_portfolio_value,
                'max_loss_1h': mc_results['max_loss'],
                'avg_loss_1h': mc_results['avg_loss'],
                'probability_loss': mc_results['prob_loss'],
                'var_95_1h': mc_results['var_95'],
                'cvar_99_1h': mc_results['cvar_99'],
                'recommended_action': self._recommend_action(portfolio_return, mc_results),
            }
            
        except Exception as e:
            logger.error(f"Scenario execution failed: {e}")
            raise
    
    async def _monte_carlo_scenario(
        self,
        scenario: StressTestScenario,
        shocked_prices: Dict,
        position: float,
        portfolio_value: float,
        n_sims: int
    ) -> Dict:
        """Run Monte Carlo simulation under stress scenario."""
        
        # Use GPU for speed
        try:
            # Generate random returns
            mean_return = -0.001  # Assume continued weakness in stress
            std_dev = 0.02  # High volatility in stress
            
            returns_gpu = cp.random.normal(mean_return, std_dev, (n_sims, 1))
            
            # Calculate P&L paths
            gold_price = shocked_prices.get('gold', 2000)
            pnl_gpu = position * gold_price * returns_gpu
            
            # Portfolio values
            portfolio_gpu = portfolio_value + pnl_gpu
            
            # Calculate metrics on GPU
            var_95 = float(cp.percentile(pnl_gpu, 5))
            var_99 = float(cp.percentile(pnl_gpu, 1))
            cvar_99 = float(cp.mean(pnl_gpu[pnl_gpu <= var_99]))
            
            pnl_cpu = cp.asnumpy(pnl_gpu).flatten()
            
            return {
                'max_loss': float(pnl_cpu.min()),
                'avg_loss': float(pnl_cpu[pnl_cpu < 0].mean()),
                'prob_loss': float((pnl_cpu < 0).sum() / len(pnl_cpu)),
                'var_95': var_95,
                'cvar_99': cvar_99,
            }
            
        except Exception as e:
            logger.error(f"Monte Carlo simulation failed: {e}")
            # Fallback to CPU
            return self._monte_carlo_scenario_cpu(scenario, shocked_prices, position, portfolio_value, n_sims)
    
    def _monte_carlo_scenario_cpu(
        self,
        scenario: StressTestScenario,
        shocked_prices: Dict,
        position: float,
        portfolio_value: float,
        n_sims: int
    ) -> Dict:
        """CPU fallback for Monte Carlo."""
        mean_return = -0.001
        std_dev = 0.02
        
        returns = np.random.normal(mean_return, std_dev, n_sims)
        gold_price = shocked_prices.get('gold', 2000)
        pnl = position * gold_price * returns
        
        return {
            'max_loss': float(pnl.min()),
            'avg_loss': float(pnl[pnl < 0].mean()),
            'prob_loss': float((pnl < 0).sum() / len(pnl)),
            'var_95': float(np.percentile(pnl, 5)),
            'cvar_99': float(np.percentile(pnl, 1)),
        }
    
    def _recommend_action(self, immediate_return: float, mc_results: Dict) -> str:
        """Recommend action based on stress test results."""
        if immediate_return < -0.05:
            return "EMERGENCY: Close position immediately"
        elif immediate_return < -0.02:
            return "SEVERE: Reduce position size by 50%"
        elif mc_results['prob_loss'] > 0.70:
            return "WARNING: High probability of further losses, consider hedging"
        elif mc_results['cvar_99'] < immediate_return:
            return "CAUTION: Tail risk elevated, tighten stops"
        else:
            return "HOLD: Position within risk parameters"
    
    def generate_report(self) -> str:
        """Generate human-readable stress test report."""
        report = "=" * 70 + "\n"
        report += "STRESS TEST REPORT\n"
        report += "=" * 70 + "\n\n"
        
        for scenario_name, result in self.results.get('scenarios', {}).items():
            if 'error' in result:
                report += f"❌ {scenario_name}: {result['error']}\n\n"
                continue
            
            report += f"📊 {scenario_name}\n"
            report += f"   Description: {result['scenario']}\n"
            report += f"   Immediate P&L: ${result['immediate_pnl']:,.2f} ({result['immediate_return_pct']:.2f}%)\n"
            report += f"   1-Hour VaR 95%: ${result['var_95_1h']:,.2f}\n"
            report += f"   1-Hour CVaR 99%: ${result['cvar_99_1h']:,.2f}\n"
            report += f"   Probability of Loss: {result['probability_loss']:.1%}\n"
            report += f"   Action: {result['recommended_action']}\n\n"
        
        return report
```

**Add to API**:
```python
@app.post("/stress-test")
async def run_stress_test(request: Dict):
    """Run comprehensive stress tests."""
    try:
        from src.risk.stress_tester import StressTester
        
        tester = StressTester(CONFIG)
        
        # Get current portfolio state
        current_position = request.get('position', 0)
        portfolio_value = request.get('portfolio_value', 100000)
        prices = request.get('prices', {})
        
        # Run tests
        results = await tester.run_all_stress_tests(
            current_position,
            portfolio_value,
            prices,
            n_simulations=10000
        )
        
        return {
            'status': 'success',
            'results': results,
            'report': tester.generate_report()
        }
        
    except Exception as e:
        logger.error(f"Stress test failed: {e}")
        return {'status': 'error', 'error': str(e)}
```

---

## 4.3 Dynamic Drawdown Recovery

### Enhancement: Adaptive Recovery Protocol
**Effort**: 🟡 Medium (18 hours)  
**Impact**: High — Protects capital during downturns

```python
# src/risk/recovery_manager.py
import numpy as np
from datetime import datetime, timedelta
from loguru import logger

class RecoveryManager:
    """Manage recovery from drawdown events."""
    
    def __init__(self, config: dict):
        self.config = config
        recovery_cfg = config.get('risk', {}).get('recovery', {})
        
        self.recovery_enabled = recovery_cfg.get('enabled', True)
        self.drawdown_threshold = recovery_cfg.get('drawdown_threshold', 0.10)
        self.position_reduction_pct = recovery_cfg.get('position_reduction_pct', 0.50)
        self.recovery_lookback_days = recovery_cfg.get('recovery_lookback_days', 30)
        
        self.in_recovery = False
        self.recovery_start_time = None
        self.peak_equity = None
        self.target_equity = None
    
    def check_and_initiate_recovery(
        self,
        current_equity: float,
        peak_equity: float,
        daily_losses: list
    ) -> Dict:
        """Check if recovery should be initiated."""
        
        current_drawdown = (peak_equity - current_equity) / peak_equity
        
        recovery_triggered = {
            'triggered': False,
            'reason': '',
            'recommended_action': 'HOLD',
        }
        
        # Check drawdown threshold
        if current_drawdown > self.drawdown_threshold and not self.in_recovery:
            recovery_triggered['triggered'] = True
            recovery_triggered['reason'] = f'Drawdown {current_drawdown:.2%} exceeds threshold {self.drawdown_threshold:.2%}'
            recovery_triggered['recommended_action'] = 'REDUCE_POSITION'
            
            self.in_recovery = True
            self.recovery_start_time = datetime.now()
            self.peak_equity = peak_equity
            self.target_equity = peak_equity  # Goal: recover to peak
        
        # Check consecutive losses
        if len(daily_losses) >= 3:
            recent_losses = daily_losses[-3:]
            if all(loss < 0 for loss in recent_losses):
                recovery_triggered['triggered'] = True
                recovery_triggered['reason'] = '3 consecutive daily losses'
                recovery_triggered['recommended_action'] = 'REDUCE_POSITION'
                
                self.in_recovery = True
        
        return recovery_triggered
    
    def get_recovery_position_size(
        self,
        base_position_size: float,
        current_equity: float,
        peak_equity: float
    ) -> float:
        """Get adjusted position size during recovery."""
        
        if not self.in_recovery:
            return base_position_size
        
        current_drawdown = (peak_equity - current_equity) / peak_equity
        
        # Reduce position size proportionally to drawdown
        reduction_factor = 1.0 - (current_drawdown / self.drawdown_threshold)
        reduction_factor = max(reduction_factor, 0.25)  # Never go below 25% of base
        
        adjusted_size = base_position_size * reduction_factor
        
        return adjusted_size
    
    def check_recovery_complete(
        self,
        current_equity: float,
        daily_equity_curve: list
    ) -> bool:
        """Check if recovery is complete."""
        
        if not self.in_recovery or self.peak_equity is None:
            return False
        
        # Recovery complete when:
        # 1. Equity recovers to within 95% of peak, AND
        # 2. No drawdown in last 5 days
        
        if current_equity >= self.peak_equity * 0.95:
            if len(daily_equity_curve) >= 5:
                recent_drawdown = (
                    (max(daily_equity_curve[-5:]) - current_equity) /
                    max(daily_equity_curve[-5:])
                )
                
                if recent_drawdown < 0.02:  # Less than 2% drawdown
                    self.in_recovery = False
                    logger.info(f"✓ Recovery complete after {(datetime.now() - self.recovery_start_time).days} days")
                    return True
        
        return False
    
    def get_recovery_status(self) -> Dict:
        """Get current recovery status."""
        return {
            'in_recovery': self.in_recovery,
            'recovery_start': self.recovery_start_time.isoformat() if self.recovery_start_time else None,
            'peak_equity': self.peak_equity,
            'target_equity': self.target_equity,
            'days_in_recovery': (datetime.now() - self.recovery_start_time).days if self.recovery_start_time else 0,
        }
```

---

---

# PHASE 5: BACKTESTING & VALIDATION

## Current Capabilities
✅ Event-driven backtester  
✅ Walk-forward analysis  
✅ CPCV validation  
✅ Deflated Sharpe Ratio  
✅ Performance metrics (20+)  
✅ Report generation  
✅ 50 tests passing

---

## 5.1 Performance Optimization

### Current State
- Single-threaded backtest
- ~1000 trades/second processing
- But: Slow for large-scale optimization

### Enhancement: Parallel Backtesting
**Effort**: 🟡 Medium (22 hours)  
**Impact**: High — 4-8x speedup for parameter tuning

```python
# src/backtesting/parallel_backtester.py
import multiprocessing as mp
from typing import List, Dict, Callable, Any
import pandas as pd
import numpy as np
from loguru import logger

class ParallelBacktester:
    """Run multiple backtests in parallel."""
    
    def __init__(self, n_workers: int = None):
        self.n_workers = n_workers or mp.cpu_count()
        logger.info(f"Initialized parallel backtester with {self.n_workers} workers")
    
    def backtest_parameter_grid(
        self,
        data: pd.DataFrame,
        strategy_func: Callable,
        param_grid: Dict[str, List[Any]],
        initial_capital: float = 100000
    ) -> pd.DataFrame:
        """Run backtests across parameter grid in parallel."""
        
        # Generate all parameter combinations
        param_combinations = self._generate_combinations(param_grid)
        logger.info(f"Generated {len(param_combinations)} parameter combinations")
        
        # Create task list
        tasks = [
            (data, strategy_func, params, initial_capital)
            for params in param_combinations
        ]
        
        # Run in parallel
        with mp.Pool(processes=self.n_workers) as pool:
            results = pool.starmap(
                self._backtest_single,
                tasks,
                chunksize=max(1, len(tasks) // (self.n_workers * 10))
            )
        
        # Compile results
        results_df = pd.DataFrame(results)
        results_df = results_df.sort_values('sharpe_ratio', ascending=False)
        
        logger.info(f"✓ Completed {len(results)} backtests")
        logger.info(f"  Best Sharpe: {results_df['sharpe_ratio'].iloc[0]:.3f}")
        
        return results_df
    
    @staticmethod
    def _backtest_single(
        data: pd.DataFrame,
        strategy_func: Callable,
        params: Dict,
        initial_capital: float
    ) -> Dict:
        """Run single backtest (for multiprocessing)."""
        try:
            from src.backtesting.backtester import Backtester, BacktestConfig
            
            # Create backtester
            config = BacktestConfig(initial_capital=initial_capital)
            backtester = Backtester(config)
            
            # Run backtest
            results = backtester.run(data, strategy_func, params)
            
            # Return key metrics
            return {
                **params,
                'total_return': results.total_return,
                'annual_return': results.annual_return,
                'sharpe_ratio': results.sharpe_ratio,
                'max_drawdown': results.max_drawdown,
                'win_rate': results.win_rate,
                'trades': results.total_trades,
                'profit_factor': results.profit_factor,
            }
            
        except Exception as e:
            logger.error(f"Backtest failed for params {params}: {e}")
            return {
                **params,
                'error': str(e),
                'total_return': np.nan,
            }
    
    @staticmethod
    def _generate_combinations(param_grid: Dict) -> List[Dict]:
        """Generate all parameter combinations from grid."""
        import itertools
        
        keys = param_grid.keys()
        values = param_grid.values()
        
        combinations = []
        for combo in itertools.product(*values):
            combinations.append(dict(zip(keys, combo)))
        
        return combinations
    
    def backtest_walk_forward_parallel(
        self,
        data: pd.DataFrame,
        strategy_func: Callable,
        param_grid: Dict,
        train_window: int = 252,  # 1 year
        test_window: int = 63,    # 1 quarter
        step: int = 63
    ) -> pd.DataFrame:
        """Run walk-forward analysis in parallel."""
        
        walk_forward_results = []
        
        # Generate walk-forward windows
        for start in range(0, len(data) - train_window - test_window, step):
            train_end = start + train_window
            test_end = train_end + test_window
            
            train_data = data.iloc[start:train_end]
            test_data = data.iloc[train_end:test_end]
            
            # Run parameter optimization on train data
            param_combinations = self._generate_combinations(param_grid)
            
            best_params = None
            best_sharpe = -np.inf
            
            for params in param_combinations:
                try:
                    result = self._backtest_single(
                        train_data, strategy_func, params, 100000
                    )
                    
                    if result.get('sharpe_ratio', -np.inf) > best_sharpe:
                        best_sharpe = result['sharpe_ratio']
                        best_params = params
                        
                except:
                    pass
            
            # Test best params on out-of-sample
            if best_params:
                oos_result = self._backtest_single(
                    test_data, strategy_func, best_params, 100000
                )
                
                oos_result['fold_start'] = start
                oos_result['train_sharpe'] = best_sharpe
                walk_forward_results.append(oos_result)
        
        results_df = pd.DataFrame(walk_forward_results)
        
        logger.info(f"Walk-forward completed: {len(results_df)} folds")
        logger.info(f"  Average OOS Sharpe: {results_df['sharpe_ratio'].mean():.3f}")
        
        return results_df
```

---

## 5.2 Additional Validation Metrics

### Enhancement: Portfolio Quality Metrics
**Effort**: 🟢 Low (12 hours)  
**Impact**: Medium — Better strategy evaluation

```python
# Add to src/backtesting/metrics.py

class PortfolioQualityMetrics:
    """Additional portfolio quality metrics."""
    
    @staticmethod
    def trade_quality_score(trades_df: pd.DataFrame) -> float:
        """
        Trade Quality Score (0-100):
        Combines multiple factors for overall trade quality assessment.
        """
        if len(trades_df) == 0:
            return 0
        
        scores = []
        
        # Win rate contribution (max 30 points)
        win_rate = (trades_df['pnl'] > 0).mean()
        scores.append(min(win_rate * 100 * 0.3, 30))
        
        # Profit factor contribution (max 25 points)
        gross_profit = trades_df[trades_df['pnl'] > 0]['pnl'].sum()
        gross_loss = abs(trades_df[trades_df['pnl'] < 0]['pnl'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.inf
        scores.append(min(np.log(profit_factor + 1) * 25, 25))
        
        # Win/loss ratio contribution (max 20 points)
        avg_win = trades_df[trades_df['pnl'] > 0]['pnl'].mean()
        avg_loss = abs(trades_df[trades_df['pnl'] < 0]['pnl'].mean())
        reward_risk = avg_win / avg_loss if avg_loss > 0 else 0
        scores.append(min(reward_risk * 10, 20))
        
        # Consistency contribution (max 15 points)
        returns = trades_df['pnl'] / 100000  # Assume $100k account
        consistency = 1.0 / (returns.std() / returns.mean() + 1e-6)
        scores.append(min(consistency * 3, 15))
        
        # Consecutive wins contribution (max 10 points)
        max_consecutive_wins = self._max_consecutive(trades_df['pnl'] > 0)
        scores.append(min(max_consecutive_wins, 10))
        
        return sum(scores)
    
    @staticmethod
    def _max_consecutive(bool_series):
        """Find maximum consecutive True values."""
        max_consecutive = 0
        current_consecutive = 0
        
        for value in bool_series:
            if value:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0
        
        return max_consecutive
    
    @staticmethod
    def concentration_ratio(trades_df: pd.DataFrame) -> float:
        """
        Concentration Ratio: % of profits from top 10% of trades.
        Lower is better (more diversified).
        """
        if len(trades_df) == 0:
            return 0
        
        profitable_trades = trades_df[trades_df['pnl'] > 0].sort_values('pnl', ascending=False)
        
        if len(profitable_trades) == 0:
            return 0
        
        top_10_pct_count = max(1, len(profitable_trades) // 10)
        top_10_pct_profit = profitable_trades.head(top_10_pct_count)['pnl'].sum()
        total_profit = profitable_trades['pnl'].sum()
        
        if total_profit == 0:
            return 0
        
        return top_10_pct_profit / total_profit
    
    @staticmethod
    def recovery_quality(equity_curve: np.ndarray, drawdowns: np.ndarray) -> float:
        """
        Recovery Quality Score: How quickly does strategy recover from drawdowns?
        Higher is better.
        """
        if len(equity_curve) < 2:
            return 0
        
        # Find drawdown periods
        peak_idx = np.argmax(equity_curve)
        dd_recovery_times = []
        
        for i in range(peak_idx, len(equity_curve) - 1):
            if equity_curve[i] > equity_curve[i + 1]:  # New drawdown start
                # Find when it recovers
                for j in range(i + 1, len(equity_curve)):
                    if equity_curve[j] >= equity_curve[i]:
                        dd_recovery_times.append(j - i)
                        break
        
        if not dd_recovery_times:
            return 100
        
        # Average recovery time (in days, assuming daily data)
        avg_recovery = np.mean(dd_recovery_times)
        # Normalize: 50 days = good recovery, 200+ days = poor
        recovery_score = max(0, 100 - (avg_recovery * 0.5))
        
        return recovery_score
```

---

## 5.3 Real-Time Backtest Monitoring

### Enhancement: Live Backtest Performance Tracking
**Effort**: 🟢 Low (10 hours)  
**Impact**: Medium — Enables backtesting during trading

```python
# src/backtesting/live_monitor.py
import time
from datetime import datetime
from collections import deque
from loguru import logger

class LiveBacktestMonitor:
    """Monitor backtest performance in real-time."""
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        
        # Metrics
        self.tick_count = 0
        self.trade_count = 0
        self.event_count = 0
        
        # Performance tracking
        self.tick_times = deque(maxlen=1000)
        self.start_time = None
        self.last_status_time = None
        
        self.total_pnl = 0
        self.max_dd = 0
        self.current_dd = 0
    
    def on_event(self, event_type: str, processing_time_ms: float):
        """Record event processing."""
        self.event_count += 1
        
        if event_type == 'market':
            self.tick_count += 1
        elif event_type == 'fill':
            self.trade_count += 1
        
        self.tick_times.append(processing_time_ms)
        
        # Log periodically
        if self.event_count % 10000 == 0:
            self._log_status()
    
    def _log_status(self):
        """Log current backtest status."""
        if len(self.tick_times) == 0:
            return
        
        avg_tick_ms = np.mean(self.tick_times)
        max_tick_ms = np.max(self.tick_times)
        throughput = 1000 / avg_tick_ms  # Events per second
        
        elapsed = time.time() - self.start_time if self.start_time else 0
        
        logger.info(
            f"Backtest Progress: {self.event_count:,} events | "
            f"{self.trade_count:,} trades | "
            f"Throughput: {throughput:,.0f} evt/sec | "
            f"Latency: {avg_tick_ms:.3f}ms avg ({max_tick_ms:.3f}ms max) | "
            f"Elapsed: {elapsed:.1f}s"
        )
    
    def set_portfolio_state(self, equity: float, peak_equity: float, pnl: float):
        """Update portfolio state."""
        self.total_pnl = pnl
        self.current_dd = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0
        self.max_dd = max(self.max_dd, self.current_dd)
    
    def get_live_metrics(self) -> Dict:
        """Get current live metrics."""
        if len(self.tick_times) == 0:
            return {}
        
        avg_tick_ms = np.mean(self.tick_times)
        
        return {
            'tick_count': self.tick_count,
            'trade_count': self.trade_count,
            'event_count': self.event_count,
            'avg_latency_ms': float(avg_tick_ms),
            'throughput_events_per_sec': float(1000 / avg_tick_ms),
            'total_pnl': self.total_pnl,
            'current_drawdown_pct': float(self.current_dd * 100),
            'max_drawdown_pct': float(self.max_dd * 100),
            'timestamp': datetime.now().isoformat(),
        }
```

---

---

# IMPLEMENTATION PRIORITY MATRIX

## Quick Wins (Low Effort, High Impact) - Implement First
🟢 **These should be done immediately (week 1)**

| Item | Effort | Impact | Priority |
|------|--------|--------|----------|
| Container health checks | 8h | High | 🔴 URGENT |
| Redis connection pooling | 6h | Medium | 🔴 URGENT |
| Advanced risk metrics | 20h | High | 🟡 HIGH |
| Detailed health endpoint | 6h | Medium | 🟡 HIGH |
| Backup manager | 25h | Critical | 🟡 HIGH |
| Source-specific validation | 10h | Medium | 🟢 LOW |
| Stress testing framework | 35h | Critical | 🟡 HIGH |
| Model performance monitoring | 18h | High | 🟡 HIGH |
| Parallel backtesting | 22h | High | 🟡 HIGH |

## Medium-Term Enhancements (Week 2-3)
🟡 **Next tier of improvements**

| Item | Effort | Impact | Priority |
|------|--------|--------|----------|
| Hyperparameter optimization (Optuna) | 25h | High | 🟡 HIGH |
| SHAP explainability | 20h | Medium | 🟢 MEDIUM |
| Automatic retraining | 22h | High | 🟡 HIGH |
| Streaming ingestion | 30h | Critical | 🟡 HIGH |
| Retry mechanisms | 16h | High | 🟡 HIGH |
| Alternative data aggregator | 22h | Medium | 🟢 MEDIUM |
| Data repair engine | 18h | High | 🟡 HIGH |

## Long-Term Enhancements (Month 2+)
🔴 **Advanced features and optimizations**

| Item | Effort | Impact | Priority |
|------|--------|--------|----------|
| Advanced validation metrics | 12h | Medium | 🟢 MEDIUM |
| Recovery manager | 18h | High | 🟡 HIGH |
| Live backtest monitoring | 10h | Medium | 🟢 MEDIUM |

---

# DEPLOYMENT ROADMAP

## Week 1: Critical Infrastructure
- [ ] Docker health checks (8h)
- [ ] Redis connection pooling (6h)
- [ ] Backup manager setup (25h)
- [ ] Detailed health endpoint (6h)
- **Total: 45h → ~6 dev days**

## Week 2: Risk & Validation
- [ ] Advanced risk metrics (20h)
- [ ] Stress testing framework (35h)
- [ ] Model performance monitoring (18h)
- **Total: 73h → ~9 dev days**

## Week 3: Data Pipeline Enhancement
- [ ] Data repair engine (18h)
- [ ] Source-specific validators (10h)
- [ ] Streaming ingestion (30h)
- [ ] Retry mechanisms (16h)
- **Total: 74h → ~9 dev days**

## Week 4: Model Improvements
- [ ] Hyperparameter tuning (Optuna) (25h)
- [ ] SHAP explainability (20h)
- [ ] Automatic retraining (22h)
- **Total: 67h → ~8 dev days**

## Week 5: Performance & Polish
- [ ] Parallel backtesting (22h)
- [ ] Alternative data aggregator (22h)
- [ ] Recovery manager (18h)
- [ ] Live backtest monitoring (10h)
- **Total: 72h → ~9 dev days**

**Overall: ~5 weeks of development → System production-ready**

---

# EFFORT ESTIMATION SUMMARY

- **🟢 Low (5-15h)**: 8 items
- **🟡 Medium (15-40h)**: 19 items
- **🔴 High (40+h)**: 5 items

**Total Estimated Effort**: ~550-600 developer-hours  
**Team Capacity**: 
- 1 engineer: ~14-15 weeks
- 2 engineers: ~7-8 weeks
- 3 engineers: ~5-6 weeks

---

## Conclusion

The Mini-Medallion trading engine is **95% feature-complete** with a solid foundation. The enhancement opportunities identified above focus on:

1. **Reliability** - Health checks, backups, error recovery
2. **Performance** - Optimization, parallel processing, streaming
3. **Explainability** - SHAP, performance monitoring, debugging
4. **Risk Management** - Advanced metrics, stress testing, recovery
5. **Data Quality** - Repair, validation, real-time monitoring

Implementing these enhancements will transform the system from a capable prototype into a **production-grade trading platform** suitable for live trading operations.

**Next Steps**:
1. Prioritize infrastructure improvements (Week 1)
2. Implement risk management enhancements (Week 2)
3. Deploy data pipeline upgrades (Week 3)
4. Add model improvements (Week 4)
5. Optimize and scale (Week 5)

---

**Document Status**: Complete Analysis Ready for Implementation  
**Last Updated**: May 14, 2026  
**Prepared by**: GitHub Copilot
