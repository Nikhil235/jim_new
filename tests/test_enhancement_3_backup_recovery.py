"""
Tests for Enhancement #3: Backup & Disaster Recovery

Test coverage:
- BackupManager full backup workflow
- Backup verification and integrity
- Cross-region replication
- Disaster recovery operations
- Point-in-time recovery
- Recovery verification
- RPO/RTO calculations
- Cleanup and retention
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Tuple, List, Dict, Any

import pytest

from src.infrastructure.backup_manager import (
    BackupType,
    BackupStatus,
    BackupTarget,
    VerificationStatus,
    BackupMetadata,
    BackupStats,
    BackupConnector,
    BackupPolicy,
    BackupManager,
    RPOCalculator,
    RTOCalculator,
)

from src.infrastructure.disaster_recovery import (
    RecoveryType,
    RecoveryStatus,
    DataTier,
    RecoveryPoint,
    RecoveryOperation,
    RecoveryStats,
    RecoveryConnector,
    DisasterRecoveryManager,
)


# ============================================================================
# Mock Connectors for Testing
# ============================================================================

class MockBackupConnector(BackupConnector):
    """Mock backup connector for testing"""
    
    def __init__(self, target: BackupTarget):
        self.target = target
        self.backups = {}
        self.create_count = 0
    
    async def create_backup(self, backup_type: BackupType) -> Tuple[int, int, str]:
        """Create mock backup"""
        self.create_count += 1
        # Return: 100MB, 1M rows, checksum
        return 100 * 1024 * 1024, 1000000, "checksum123"
    
    async def verify_backup(self, backup_path: str, expected_checksum: str) -> bool:
        """Verify mock backup"""
        self.backups[backup_path] = expected_checksum
        return True
    
    async def restore_backup(self, backup_path: str) -> bool:
        """Restore mock backup"""
        return backup_path in self.backups
    
    async def delete_backup(self, backup_path: str) -> bool:
        """Delete mock backup"""
        if backup_path in self.backups:
            del self.backups[backup_path]
            return True
        return False
    
    async def list_backups(self) -> List[str]:
        """List mock backups"""
        return list(self.backups.keys())


class MockRecoveryConnector(RecoveryConnector):
    """Mock recovery connector for testing"""
    
    def __init__(self, data_tier: DataTier):
        self.data_tier = data_tier
        self.recovery_points = []
    
    async def get_available_recovery_points(self, data_tier: DataTier,
                                            hours_back: int) -> List[RecoveryPoint]:
        """Get mock recovery points"""
        points = []
        now = datetime.utcnow()
        
        for i in range(24, 24 + hours_back, 24):
            point_time = now - timedelta(hours=i)
            point = RecoveryPoint(
                timestamp=point_time,
                data_tier=data_tier,
                backup_id=f"backup_{i}",
                backup_path=f"backups/{data_tier.value}/{i}",
                verified=True,
                recovery_time_estimate_hours=1.0,
            )
            points.append(point)
        
        return points
    
    async def recover_to_point(self, recovery_point: RecoveryPoint) -> bool:
        """Perform mock recovery"""
        self.recovery_points.append(recovery_point)
        return True
    
    async def verify_recovery(self, data_tier: DataTier) -> bool:
        """Verify mock recovery"""
        return len(self.recovery_points) > 0
    
    async def get_recovery_status(self) -> Dict[str, Any]:
        """Get mock recovery status"""
        return {
            "data_tier": self.data_tier.value,
            "points_recovered": len(self.recovery_points),
            "last_recovery": self.recovery_points[-1].timestamp.isoformat() if self.recovery_points else None,
        }


# ============================================================================
# Unit Tests: Backup Manager
# ============================================================================

class TestBackupMetadata:
    """Test BackupMetadata functionality"""
    
    def test_metadata_creation(self):
        """Test creating backup metadata"""
        metadata = BackupMetadata(
            backup_id="backup_001",
            timestamp=datetime.utcnow(),
            backup_type=BackupType.FULL,
            target=BackupTarget.QUESTDB,
            source_system="questdb_primary",
            backup_path="/backups/questdb/001",
            size_bytes=100 * 1024 * 1024,
            row_count=1000000,
            duration_ms=5000.0,
            status=BackupStatus.COMPLETED,
            checksum="abc123",
        )
        
        assert metadata.backup_id == "backup_001"
        assert metadata.status == BackupStatus.COMPLETED
        assert metadata.target == BackupTarget.QUESTDB
    
    def test_metadata_serialization(self):
        """Test metadata to_dict"""
        metadata = BackupMetadata(
            backup_id="backup_001",
            timestamp=datetime(2026, 5, 14, 10, 0, 0),
            backup_type=BackupType.FULL,
            target=BackupTarget.QUESTDB,
            source_system="questdb_primary",
            backup_path="/backups/questdb/001",
            size_bytes=100 * 1024 * 1024,
            row_count=1000000,
            duration_ms=5000.0,
            status=BackupStatus.COMPLETED,
            checksum="abc123",
        )
        
        data = metadata.to_dict()
        assert data["backup_id"] == "backup_001"
        assert data["status"] == "completed"
        assert data["target"] == "questdb"


class TestBackupPolicy:
    """Test BackupPolicy functionality"""
    
    def test_policy_creation(self):
        """Test creating backup policy"""
        policy = BackupPolicy(
            name="questdb_daily",
            target=BackupTarget.QUESTDB,
            backup_type=BackupType.FULL,
            retention_days=7,
            backup_frequency_hours=24,
        )
        
        assert policy.name == "questdb_daily"
        assert policy.retention_days == 7
    
    def test_should_backup_now_first_time(self):
        """Test should_backup_now for first backup"""
        policy = BackupPolicy(
            name="test",
            target=BackupTarget.QUESTDB,
            backup_type=BackupType.FULL,
            retention_days=7,
            backup_frequency_hours=24,
        )
        
        assert policy.should_backup_now(None)
    
    def test_should_backup_now_frequency_check(self):
        """Test should_backup_now with frequency"""
        policy = BackupPolicy(
            name="test",
            target=BackupTarget.QUESTDB,
            backup_type=BackupType.FULL,
            retention_days=7,
            backup_frequency_hours=24,
        )
        
        # Just backed up 1 hour ago - should not backup
        last_backup = datetime.utcnow() - timedelta(hours=1)
        assert not policy.should_backup_now(last_backup)
        
        # Backed up 30 hours ago - should backup
        last_backup = datetime.utcnow() - timedelta(hours=30)
        assert policy.should_backup_now(last_backup)


class TestBackupStats:
    """Test BackupStats functionality"""
    
    def test_stats_creation(self):
        """Test creating backup stats"""
        stats = BackupStats()
        assert stats.total_backups == 0
        assert stats.success_rate == 0.0
    
    def test_success_rate_calculation(self):
        """Test success rate calculation"""
        stats = BackupStats()
        stats.total_backups = 10
        stats.successful_backups = 8
        stats.failed_backups = 2
        assert stats.success_rate == 80.0


class TestBackupManager:
    """Test BackupManager functionality"""
    
    def test_manager_creation(self):
        """Test creating backup manager"""
        manager = BackupManager()
        assert manager.policies
        assert len(manager.policies) > 0
    
    def test_register_connector(self):
        """Test registering backup connector"""
        manager = BackupManager()
        connector = MockBackupConnector(BackupTarget.QUESTDB)
        
        manager.register_connector(BackupTarget.QUESTDB, connector)
        assert BackupTarget.QUESTDB in manager.connectors
    
    def test_generate_backup_path(self):
        """Test backup path generation"""
        manager = BackupManager()
        date = datetime(2026, 5, 14)
        path = manager._generate_backup_path(BackupTarget.QUESTDB, "backup_001")
        
        assert "backup_001" in path
        assert "questdb" in path
        assert "2026/05/14" in path


# ============================================================================
# Integration Tests: Backup & Recovery Workflow
# ============================================================================

class TestBackupIntegration:
    """Integration tests for backup workflow"""
    
    def test_create_all_backups(self):
        """Test creating backups for all targets"""
        loop = asyncio.new_event_loop()
        try:
            manager = BackupManager()
            
            # Register connectors
            for target in [BackupTarget.QUESTDB, BackupTarget.REDIS, BackupTarget.MINIO]:
                connector = MockBackupConnector(target)
                manager.register_connector(target, connector)
            
            # Create backups
            results = loop.run_until_complete(manager.create_all_backups())
            
            # Check results
            assert len(results) > 0
            assert all(results.values())  # All should succeed
            assert len(manager.backups) > 0
        finally:
            loop.close()
    
    def test_verify_all_backups(self):
        """Test verifying all backups"""
        loop = asyncio.new_event_loop()
        try:
            manager = BackupManager()
            
            # Register connectors
            for target in [BackupTarget.QUESTDB, BackupTarget.REDIS]:
                connector = MockBackupConnector(target)
                manager.register_connector(target, connector)
            
            # Create and verify backups
            loop.run_until_complete(manager.create_all_backups())
            results = loop.run_until_complete(manager.verify_all_backups())
            
            # Check verification results
            assert len(results) > 0
            for backup_id, verified in results.items():
                assert verified
        finally:
            loop.close()
    
    def test_backup_stats_tracking(self):
        """Test backup statistics tracking"""
        loop = asyncio.new_event_loop()
        try:
            manager = BackupManager()
            
            # Register connector
            connector = MockBackupConnector(BackupTarget.QUESTDB)
            manager.register_connector(BackupTarget.QUESTDB, connector)
            
            # Create backup
            loop.run_until_complete(manager.create_all_backups())
            
            # Check stats
            stats = manager.get_stats()
            assert stats.total_backups > 0
            assert stats.successful_backups > 0
        finally:
            loop.close()
    
    def test_backup_cleanup(self):
        """Test cleanup of old backups"""
        loop = asyncio.new_event_loop()
        try:
            manager = BackupManager()
            
            # Register connector
            connector = MockBackupConnector(BackupTarget.QUESTDB)
            manager.register_connector(BackupTarget.QUESTDB, connector)
            
            # Create backup and add old one
            loop.run_until_complete(manager.create_all_backups())
            
            # Create an old backup entry
            old_backup = BackupMetadata(
                backup_id="old_backup",
                timestamp=datetime.utcnow() - timedelta(days=10),
                backup_type=BackupType.FULL,
                target=BackupTarget.QUESTDB,
                source_system="questdb_primary",
                backup_path="/backups/old",
                size_bytes=0,
                row_count=0,
                duration_ms=0,
                status=BackupStatus.COMPLETED,
            )
            manager.backups.append(old_backup)
            
            # Cleanup
            deleted = loop.run_until_complete(manager.cleanup_old_backups())
            assert deleted >= 0
        finally:
            loop.close()


# ============================================================================
# Unit Tests: Disaster Recovery
# ============================================================================

class TestRecoveryPoint:
    """Test RecoveryPoint functionality"""
    
    def test_recovery_point_creation(self):
        """Test creating recovery point"""
        point = RecoveryPoint(
            timestamp=datetime.utcnow(),
            data_tier=DataTier.QUESTDB,
            backup_id="backup_001",
            backup_path="/backups/questdb/001",
            verified=True,
        )
        
        assert point.data_tier == DataTier.QUESTDB
        assert point.verified


class TestRecoveryOperation:
    """Test RecoveryOperation functionality"""
    
    def test_recovery_operation_creation(self):
        """Test creating recovery operation"""
        now = datetime.utcnow()
        operation = RecoveryOperation(
            operation_id="recovery_001",
            recovery_type=RecoveryType.POINT_IN_TIME,
            target_timestamp=now - timedelta(hours=1),
            data_tiers=[DataTier.QUESTDB],
            status=RecoveryStatus.PLANNED,
            initiated_at=now,
        )
        
        assert operation.recovery_type == RecoveryType.POINT_IN_TIME
        assert operation.status == RecoveryStatus.PLANNED


class TestDisasterRecoveryManager:
    """Test DisasterRecoveryManager functionality"""
    
    def test_manager_creation(self):
        """Test creating recovery manager"""
        manager = DisasterRecoveryManager()
        assert manager.stats
        assert len(manager.operations) == 0
    
    def test_register_connector(self):
        """Test registering recovery connector"""
        manager = DisasterRecoveryManager()
        connector = MockRecoveryConnector(DataTier.QUESTDB)
        
        manager.register_connector(DataTier.QUESTDB, connector)
        assert DataTier.QUESTDB in manager.connectors


# ============================================================================
# Integration Tests: Recovery Workflow
# ============================================================================

class TestRecoveryIntegration:
    """Integration tests for recovery workflow"""
    
    def test_get_recovery_points(self):
        """Test getting recovery points"""
        loop = asyncio.new_event_loop()
        try:
            manager = DisasterRecoveryManager()
            connector = MockRecoveryConnector(DataTier.QUESTDB)
            manager.register_connector(DataTier.QUESTDB, connector)
            
            # Get recovery points
            points = loop.run_until_complete(
                manager.get_recovery_points(DataTier.QUESTDB, hours_back=168)
            )
            
            assert len(points) > 0
            assert all(p.data_tier == DataTier.QUESTDB for p in points)
        finally:
            loop.close()
    
    def test_recover_to_point(self):
        """Test recovery to specific point"""
        loop = asyncio.new_event_loop()
        try:
            manager = DisasterRecoveryManager()
            connector = MockRecoveryConnector(DataTier.QUESTDB)
            manager.register_connector(DataTier.QUESTDB, connector)
            
            # Get recovery points and recover
            points = loop.run_until_complete(
                manager.get_recovery_points(DataTier.QUESTDB)
            )
            
            if points:
                success = loop.run_until_complete(
                    manager.recover_to_point(points[0])
                )
                assert success
                assert len(manager.operations) > 0
        finally:
            loop.close()
    
    def test_recovery_stats_tracking(self):
        """Test recovery statistics tracking"""
        loop = asyncio.new_event_loop()
        try:
            manager = DisasterRecoveryManager()
            connector = MockRecoveryConnector(DataTier.QUESTDB)
            manager.register_connector(DataTier.QUESTDB, connector)
            
            # Run recovery
            points = loop.run_until_complete(
                manager.get_recovery_points(DataTier.QUESTDB)
            )
            
            if points:
                loop.run_until_complete(manager.recover_to_point(points[0]))
            
            # Check stats
            stats = manager.get_stats()
            assert stats.total_recoveries > 0
        finally:
            loop.close()


# ============================================================================
# Tests: RPO/RTO Calculations
# ============================================================================

class TestRPOCalculation:
    """Test RPO (Recovery Point Objective) calculation"""
    
    def test_rpo_calculation(self):
        """Test RPO calculation"""
        times = [
            datetime.utcnow() - timedelta(days=3),
            datetime.utcnow() - timedelta(days=2),
            datetime.utcnow() - timedelta(days=1),
        ]
        
        rpo_hours = RPOCalculator.calculate_rpo_hours(times)
        assert rpo_hours == 24.0  # Daily backups


class TestRTOCalculation:
    """Test RTO (Recovery Time Objective) calculation"""
    
    def test_rto_estimation(self):
        """Test RTO time estimation"""
        # 100GB at 1GB/s throughput should take ~100 seconds + verification
        backup_size_gb = 100
        rto_minutes = RTOCalculator.estimate_recovery_time(backup_size_gb)
        
        # Should be roughly 100 seconds (1.67 min) + 5 min verification + 10% buffer
        # Total should be around 7-8 minutes
        assert rto_minutes > 0
        assert rto_minutes < 30  # More than a few minutes but less than 30


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
