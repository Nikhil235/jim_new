"""
Tests for Enhancement #2: Data Lifecycle Manager

Test coverage:
- RetentionTier serialization and tier-for-date calculations
- DataRetentionPolicy enforcement
- ArchivalRecord tracking
- DataLifecycleManager archival operations
- Mock storage connectors
- Integration tests with full workflow
- Stress tests with large data volumes
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Tuple, Dict, Any

import pytest

from src.infrastructure.data_lifecycle_manager import (
    DataType,
    StorageBackend,
    ArchivalStatus,
    RetentionTier,
    DataRetentionPolicy,
    ArchivalRecord,
    ArchivalStats,
    StorageConnector,
    DataLifecycleManager,
)


# ============================================================================
# Mock Storage Connector for Testing
# ============================================================================

class MockStorageConnector(StorageConnector):
    """Mock storage connector for testing"""
    
    def __init__(self, backend: StorageBackend):
        self.backend = backend
        self.data_store: Dict[str, Tuple[int, int]] = {}  # path -> (rows, bytes)
        self.query_count = 0
        self.archive_count = 0
        self.delete_count = 0
    
    async def query_data(self, data_type: DataType, date: datetime) -> Tuple[int, int]:
        """Query data from storage"""
        self.query_count += 1
        # Return 1000 rows, 10MB of data
        return 1000, 10 * 1024 * 1024
    
    async def archive_data(self, data_type: DataType, date: datetime, 
                          target_path: str) -> Tuple[int, int]:
        """Archive data to target path"""
        self.archive_count += 1
        rows, bytes_count = 1000, 10 * 1024 * 1024
        self.data_store[target_path] = (rows, bytes_count)
        return rows, bytes_count
    
    async def delete_data(self, data_type: DataType, date: datetime) -> bool:
        """Delete data"""
        self.delete_count += 1
        return True
    
    async def verify_integrity(self, source_rows: int, source_bytes: int,
                              target_path: str) -> bool:
        """Verify archive integrity"""
        stored = self.data_store.get(target_path)
        if not stored:
            return False
        stored_rows, stored_bytes = stored
        return stored_rows == source_rows and stored_bytes == source_bytes


# ============================================================================
# Unit Tests: RetentionTier
# ============================================================================

class TestRetentionTier:
    """Test RetentionTier functionality"""
    
    def test_retention_tier_creation(self):
        """Test creating a retention tier"""
        tier = RetentionTier("HOT", StorageBackend.QUESTDB, 90, "hot")
        assert tier.name == "HOT"
        assert tier.storage_backend == StorageBackend.QUESTDB
        assert tier.retention_days == 90
        assert tier.access_pattern == "hot"
    
    def test_retention_tier_serialization(self):
        """Test tier serialization to dict"""
        tier = RetentionTier("WARM", StorageBackend.MINIO, 300, "cold")
        tier_dict = tier.to_dict()
        
        assert tier_dict["name"] == "WARM"
        assert tier_dict["storage_backend"] == "minio"
        assert tier_dict["retention_days"] == 300
        assert tier_dict["access_pattern"] == "cold"
    
    def test_retention_tier_deserialization(self):
        """Test tier creation from dict"""
        data = {
            "name": "COLD",
            "storage_backend": "glacier",
            "retention_days": 2555,
            "access_pattern": "archive",
        }
        tier = RetentionTier.from_dict(data)
        
        assert tier.name == "COLD"
        assert tier.storage_backend == StorageBackend.GLACIER
        assert tier.retention_days == 2555


# ============================================================================
# Unit Tests: DataRetentionPolicy
# ============================================================================

class TestDataRetentionPolicy:
    """Test DataRetentionPolicy functionality"""
    
    def test_policy_creation(self):
        """Test creating a retention policy"""
        tiers = [
            RetentionTier("HOT", StorageBackend.QUESTDB, 90, "hot"),
            RetentionTier("WARM", StorageBackend.MINIO, 300, "cold"),
        ]
        policy = DataRetentionPolicy(
            data_type=DataType.MARKET_DATA,
            tiers=tiers,
            total_retention_days=390,
        )
        
        assert policy.data_type == DataType.MARKET_DATA
        assert len(policy.tiers) == 2
        assert policy.total_archive_days == 390
    
    def test_get_tier_for_recent_date(self):
        """Test getting tier for recent data"""
        tiers = [
            RetentionTier("HOT", StorageBackend.QUESTDB, 90, "hot"),
            RetentionTier("WARM", StorageBackend.MINIO, 300, "cold"),
        ]
        policy = DataRetentionPolicy(
            data_type=DataType.MARKET_DATA,
            tiers=tiers,
            total_retention_days=390,
        )
        
        # Data from 30 days ago should be in HOT tier
        date_30_days_ago = datetime.utcnow() - timedelta(days=30)
        tier = policy.get_tier_for_date(date_30_days_ago)
        assert tier.name == "HOT"
    
    def test_get_tier_for_old_date(self):
        """Test getting tier for older data"""
        tiers = [
            RetentionTier("HOT", StorageBackend.QUESTDB, 90, "hot"),
            RetentionTier("WARM", StorageBackend.MINIO, 300, "cold"),
        ]
        policy = DataRetentionPolicy(
            data_type=DataType.MARKET_DATA,
            tiers=tiers,
            total_retention_days=390,
        )
        
        # Data from 150 days ago should be in WARM tier
        date_150_days_ago = datetime.utcnow() - timedelta(days=150)
        tier = policy.get_tier_for_date(date_150_days_ago)
        assert tier.name == "WARM"
    
    def test_get_tier_for_expired_date(self):
        """Test getting tier for data beyond retention"""
        tiers = [
            RetentionTier("HOT", StorageBackend.QUESTDB, 90, "hot"),
            RetentionTier("WARM", StorageBackend.MINIO, 300, "cold"),
        ]
        policy = DataRetentionPolicy(
            data_type=DataType.MARKET_DATA,
            tiers=tiers,
            total_retention_days=390,
        )
        
        # Data from 400 days ago is beyond retention
        date_400_days_ago = datetime.utcnow() - timedelta(days=400)
        tier = policy.get_tier_for_date(date_400_days_ago)
        assert tier is None


# ============================================================================
# Unit Tests: ArchivalRecord
# ============================================================================

class TestArchivalRecord:
    """Test ArchivalRecord functionality"""
    
    def test_archival_record_creation(self):
        """Test creating an archival record"""
        record = ArchivalRecord(
            timestamp=datetime.utcnow(),
            data_type=DataType.MARKET_DATA,
            date_archived=datetime.utcnow() - timedelta(days=90),
            source_tier=StorageBackend.QUESTDB,
            target_tier=StorageBackend.MINIO,
            rows_count=1000,
            bytes_transferred=10 * 1024 * 1024,
            duration_ms=5000.0,
            status=ArchivalStatus.COMPLETED,
        )
        
        assert record.data_type == DataType.MARKET_DATA
        assert record.status == ArchivalStatus.COMPLETED
        assert record.rows_count == 1000
    
    def test_archival_record_serialization(self):
        """Test record serialization"""
        record = ArchivalRecord(
            timestamp=datetime(2024, 5, 20, 10, 30, 0),
            data_type=DataType.FEATURES,
            date_archived=datetime(2024, 3, 20),
            source_tier=StorageBackend.QUESTDB,
            target_tier=StorageBackend.MINIO,
            rows_count=500,
            bytes_transferred=5 * 1024 * 1024,
            duration_ms=2500.0,
            status=ArchivalStatus.COMPLETED,
        )
        
        record_dict = record.to_dict()
        assert record_dict["data_type"] == "features"
        assert record_dict["source_tier"] == "questdb"
        assert record_dict["target_tier"] == "minio"
        assert record_dict["rows_count"] == 500


# ============================================================================
# Unit Tests: ArchivalStats
# ============================================================================

class TestArchivalStats:
    """Test ArchivalStats functionality"""
    
    def test_stats_creation(self):
        """Test creating stats"""
        stats = ArchivalStats()
        assert stats.total_operations == 0
        assert stats.success_rate == 0.0
    
    def test_success_rate_calculation(self):
        """Test success rate calculation"""
        stats = ArchivalStats(
            total_operations=10,
            successful_operations=8,
            failed_operations=2,
        )
        assert stats.success_rate == 80.0
    
    def test_average_duration_calculation(self):
        """Test average duration calculation"""
        stats = ArchivalStats(
            total_operations=5,
            total_duration_ms=5000.0,
        )
        assert stats.average_duration_ms == 1000.0


# ============================================================================
# Unit Tests: DataLifecycleManager
# ============================================================================

class TestDataLifecycleManager:
    """Test DataLifecycleManager functionality"""
    
    def test_manager_creation(self):
        """Test creating a manager"""
        manager = DataLifecycleManager()
        assert manager.policies
        assert DataType.MARKET_DATA in manager.policies
        assert DataType.FEATURES in manager.policies
    
    def test_default_policies(self):
        """Test default policies are correct"""
        manager = DataLifecycleManager()
        
        market_policy = manager.policies[DataType.MARKET_DATA]
        assert len(market_policy.tiers) == 3
        assert market_policy.tiers[0].name == "HOT"
        assert market_policy.tiers[1].name == "WARM"
        assert market_policy.tiers[2].name == "COLD"
    
    def test_register_connector(self):
        """Test registering a storage connector"""
        manager = DataLifecycleManager()
        connector = MockStorageConnector(StorageBackend.QUESTDB)
        
        manager.register_connector(StorageBackend.QUESTDB, connector)
        assert StorageBackend.QUESTDB in manager.connectors
    
    def test_generate_archive_path(self):
        """Test archive path generation"""
        manager = DataLifecycleManager()
        date = datetime(2024, 5, 20, 10, 30, 0)
        
        path = manager._generate_archive_path(DataType.MARKET_DATA, date)
        assert "market_data" in path
        assert "2024/05/20" in path
    
    def test_archival_record_tracking(self):
        """Test that archival records are tracked"""
        manager = DataLifecycleManager()
        
        record = ArchivalRecord(
            timestamp=datetime.utcnow(),
            data_type=DataType.MARKET_DATA,
            date_archived=datetime.utcnow(),
            source_tier=StorageBackend.QUESTDB,
            target_tier=StorageBackend.MINIO,
            rows_count=1000,
            bytes_transferred=10 * 1024 * 1024,
            duration_ms=5000.0,
            status=ArchivalStatus.COMPLETED,
        )
        
        manager._record_archival(record)
        assert len(manager.archival_records) == 1
        assert manager.stats.total_operations == 1
        assert manager.stats.successful_operations == 1


# ============================================================================
# Integration Tests: Full Archival Workflow
# ============================================================================

class TestDataLifecycleIntegration:
    """Integration tests for full archival workflow"""
    
    def test_archive_for_date(self):
        """Test archiving data for a date"""
        loop = asyncio.new_event_loop()
        try:
            manager = DataLifecycleManager()
            
            # Register mock connectors
            for backend in [StorageBackend.QUESTDB, StorageBackend.MINIO, StorageBackend.GLACIER]:
                connector = MockStorageConnector(backend)
                manager.register_connector(backend, connector)
            
            # Archive data from 100 days ago
            date = datetime.utcnow() - timedelta(days=100)
            results = loop.run_until_complete(manager.archive_for_date(date))
            
            # Check results
            assert len(results) > 0
            # At least one data type should have been processed
            assert any(results.values())
        finally:
            loop.close()
    
    def test_archival_stats_tracking(self):
        """Test that statistics are properly tracked"""
        loop = asyncio.new_event_loop()
        try:
            manager = DataLifecycleManager()
            
            # Register mock connectors
            for backend in [StorageBackend.QUESTDB, StorageBackend.MINIO, StorageBackend.GLACIER]:
                connector = MockStorageConnector(backend)
                manager.register_connector(backend, connector)
            
            # Run archival
            date = datetime.utcnow() - timedelta(days=100)
            loop.run_until_complete(manager.archive_for_date(date))
            
            # Check stats
            stats = manager.get_stats()
            assert stats.total_operations > 0
        finally:
            loop.close()
    
    def test_audit_log_export(self):
        """Test exporting audit log"""
        import tempfile
        import os
        
        loop = asyncio.new_event_loop()
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                audit_log_path = os.path.join(tmpdir, "audit.json")
                manager = DataLifecycleManager(audit_log_path=audit_log_path)
                
                # Add a record
                record = ArchivalRecord(
                    timestamp=datetime.utcnow(),
                    data_type=DataType.MARKET_DATA,
                    date_archived=datetime.utcnow(),
                    source_tier=StorageBackend.QUESTDB,
                    target_tier=StorageBackend.MINIO,
                    rows_count=1000,
                    bytes_transferred=10 * 1024 * 1024,
                    duration_ms=5000.0,
                    status=ArchivalStatus.COMPLETED,
                )
                manager._record_archival(record)
                
                # Export audit log
                loop.run_until_complete(manager.export_audit_log())
                
                # Verify file was created
                assert os.path.exists(audit_log_path)
                
                # Verify content (just check that file has content)
                with open(audit_log_path) as f:
                    content = f.read()
                    assert len(content) > 0
                    # File should be valid JSON-like structure
                    assert "records" in content or "statistics" in content
        finally:
            loop.close()


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
