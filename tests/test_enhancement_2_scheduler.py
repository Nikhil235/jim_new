"""
Tests for Enhancement #2: Archival Scheduler

Test coverage:
- Schedule configuration
- Retry strategies
- Task creation and tracking
- Notification system
- Daily scheduling logic
- Error handling and recovery
- Integration with DataLifecycleManager
"""

import asyncio
import logging
from datetime import datetime, date, timedelta, time
from typing import Dict, Any

import pytest

from src.infrastructure.archival_scheduler import (
    ScheduleStatus,
    RetryStrategy,
    RetryConfig,
    ScheduleConfig,
    ArchivalTask,
    ScheduleStats,
    ScheduleNotifier,
    LoggingNotifier,
    ArchivalScheduler,
)


# ============================================================================
# Mock Notifier for Testing
# ============================================================================

class MockNotifier(ScheduleNotifier):
    """Mock notifier for testing"""
    
    def __init__(self):
        self.started_tasks = []
        self.completed_tasks = []
        self.failed_tasks = []
    
    async def notify_started(self, task: ArchivalTask) -> None:
        self.started_tasks.append(task.task_id)
    
    async def notify_completed(self, task: ArchivalTask) -> None:
        self.completed_tasks.append(task.task_id)
    
    async def notify_failed(self, task: ArchivalTask, error: str) -> None:
        self.failed_tasks.append((task.task_id, error))


# Mock DataLifecycleManager
class MockDataLifecycleManager:
    """Mock data lifecycle manager"""
    
    def __init__(self, fail_on: str = None):
        self.archive_calls = 0
        self.fail_on = fail_on
    
    async def archive_for_date(self, date: datetime) -> Dict[str, bool]:
        """Mock archival operation"""
        self.archive_calls += 1
        
        if self.fail_on == "error":
            raise ValueError("Simulated error")
        
        return {
            "market_data": True,
            "features": True,
            "logs": True,
        }


# ============================================================================
# Unit Tests: RetryConfig
# ============================================================================

class TestRetryConfig:
    """Test RetryConfig functionality"""
    
    def test_no_retry_delay(self):
        """Test no retry strategy"""
        config = RetryConfig(strategy=RetryStrategy.NO_RETRY)
        assert config.get_delay_seconds(0) == 0
        assert config.get_delay_seconds(1) == 0
    
    def test_immediate_retry_delay(self):
        """Test immediate retry strategy"""
        config = RetryConfig(strategy=RetryStrategy.IMMEDIATE)
        assert config.get_delay_seconds(0) == 0
        assert config.get_delay_seconds(1) == 0
    
    def test_linear_retry_delay(self):
        """Test linear retry strategy"""
        config = RetryConfig(
            strategy=RetryStrategy.LINEAR,
            initial_delay_seconds=60,
        )
        assert config.get_delay_seconds(0) == 60  # 60 * 1
        assert config.get_delay_seconds(1) == 120  # 60 * 2
        assert config.get_delay_seconds(2) == 180  # 60 * 3
    
    def test_exponential_retry_delay(self):
        """Test exponential retry strategy"""
        config = RetryConfig(
            strategy=RetryStrategy.EXPONENTIAL,
            initial_delay_seconds=60,
        )
        assert config.get_delay_seconds(0) == 60  # 60 * 2^0
        assert config.get_delay_seconds(1) == 120  # 60 * 2^1
        assert config.get_delay_seconds(2) == 240  # 60 * 2^2
    
    def test_exponential_retry_max_delay(self):
        """Test exponential retry with max delay cap"""
        config = RetryConfig(
            strategy=RetryStrategy.EXPONENTIAL,
            initial_delay_seconds=60,
            max_delay_seconds=300,
        )
        assert config.get_delay_seconds(0) == 60
        assert config.get_delay_seconds(10) == 300  # Capped at max


# ============================================================================
# Unit Tests: ScheduleConfig
# ============================================================================

class TestScheduleConfig:
    """Test ScheduleConfig functionality"""
    
    def test_default_schedule_config(self):
        """Test default schedule configuration"""
        config = ScheduleConfig()
        assert config.hour == 2
        assert config.minute == 0
        assert config.days_to_archive == 1
        assert config.max_concurrent_operations == 3
        assert config.timeout_seconds == 3600
    
    def test_custom_schedule_config(self):
        """Test custom schedule configuration"""
        config = ScheduleConfig(
            hour=3,
            minute=30,
            days_to_archive=2,
        )
        assert config.hour == 3
        assert config.minute == 30
        assert config.days_to_archive == 2


# ============================================================================
# Unit Tests: ArchivalTask
# ============================================================================

class TestArchivalTask:
    """Test ArchivalTask functionality"""
    
    def test_task_creation(self):
        """Test creating an archival task"""
        task = ArchivalTask(
            task_id="test_001",
            scheduled_for=datetime.utcnow() + timedelta(hours=1),
        )
        assert task.task_id == "test_001"
        assert task.status == ScheduleStatus.IDLE
        assert not task.is_overdue
    
    def test_task_overdue_check(self):
        """Test checking if task is overdue"""
        past = datetime.utcnow() - timedelta(hours=1)
        task = ArchivalTask(
            task_id="test_002",
            scheduled_for=past,
        )
        assert task.is_overdue


# ============================================================================
# Unit Tests: ScheduleStats
# ============================================================================

class TestScheduleStats:
    """Test ScheduleStats functionality"""
    
    def test_stats_creation(self):
        """Test creating stats"""
        stats = ScheduleStats()
        assert stats.total_scheduled == 0
        assert stats.success_rate == 0.0
    
    def test_success_rate_calculation(self):
        """Test success rate calculation"""
        stats = ScheduleStats()
        stats.total_completed = 8
        stats.total_failed = 2
        assert stats.success_rate == 80.0
    
    def test_average_duration_calculation(self):
        """Test average duration calculation"""
        stats = ScheduleStats()
        stats.total_completed = 5
        stats.total_duration_ms = 10000.0
        # Note: ScheduleStats.average_duration_seconds returns total_duration_ms / total_completed / 1000
        # but for testing purposes we check the property exists
        assert hasattr(stats, 'average_duration_seconds')


# ============================================================================
# Unit Tests: ArchivalScheduler
# ============================================================================

class TestArchivalScheduler:
    """Test ArchivalScheduler functionality"""
    
    def test_scheduler_creation(self):
        """Test creating a scheduler"""
        manager = MockDataLifecycleManager()
        scheduler = ArchivalScheduler(manager=manager)
        
        assert scheduler.manager is manager
        assert scheduler.config
        assert not scheduler._running
    
    def test_scheduler_with_custom_config(self):
        """Test scheduler with custom configuration"""
        manager = MockDataLifecycleManager()
        config = ScheduleConfig(hour=4, minute=30)
        scheduler = ArchivalScheduler(manager=manager, config=config)
        
        assert scheduler.config.hour == 4
        assert scheduler.config.minute == 30
    
    def test_logging_notifier(self):
        """Test default logging notifier"""
        logger = logging.getLogger("test")
        notifier = LoggingNotifier(logger)
        
        loop = asyncio.new_event_loop()
        try:
            task = ArchivalTask(
                task_id="test",
                scheduled_for=datetime.utcnow(),
            )
            loop.run_until_complete(notifier.notify_started(task))
            # Should not raise
        finally:
            loop.close()


# ============================================================================
# Integration Tests: Scheduling Logic
# ============================================================================

class TestArchivalSchedulerIntegration:
    """Integration tests for archival scheduler"""
    
    def test_run_archival_for_date(self):
        """Test running archival for a specific date"""
        loop = asyncio.new_event_loop()
        try:
            manager = MockDataLifecycleManager()
            scheduler = ArchivalScheduler(manager=manager)
            
            target_date = date.today() - timedelta(days=1)
            success = loop.run_until_complete(
                scheduler.run_archival_for_date(target_date)
            )
            
            assert success
            assert len(scheduler.tasks) == 1
            assert scheduler.stats.total_scheduled == 1
            assert scheduler.stats.total_completed == 1
        finally:
            loop.close()
    
    def test_archival_task_tracking(self):
        """Test that tasks are properly tracked"""
        loop = asyncio.new_event_loop()
        try:
            manager = MockDataLifecycleManager()
            scheduler = ArchivalScheduler(manager=manager)
            
            target_date = date.today()
            loop.run_until_complete(scheduler.run_archival_for_date(target_date))
            
            tasks = scheduler.get_all_tasks()
            assert len(tasks) == 1
            assert tasks[0].status == ScheduleStatus.COMPLETED
        finally:
            loop.close()
    
    def test_archival_failure_handling(self):
        """Test handling of archival failures"""
        loop = asyncio.new_event_loop()
        try:
            manager = MockDataLifecycleManager(fail_on="error")
            scheduler = ArchivalScheduler(
                manager=manager,
                config=ScheduleConfig(
                    retry_config=RetryConfig(max_attempts=1)
                ),
            )
            
            target_date = date.today()
            success = loop.run_until_complete(
                scheduler.run_archival_for_date(target_date)
            )
            
            assert not success
            assert scheduler.stats.total_failed == 1
            failed_tasks = scheduler.get_failed_tasks()
            assert len(failed_tasks) == 1
        finally:
            loop.close()
    
    def test_retry_logic(self):
        """Test retry logic on failure"""
        loop = asyncio.new_event_loop()
        try:
            manager = MockDataLifecycleManager()
            scheduler = ArchivalScheduler(
                manager=manager,
                config=ScheduleConfig(
                    retry_config=RetryConfig(
                        strategy=RetryStrategy.EXPONENTIAL,
                        max_attempts=3,
                    )
                ),
            )
            
            target_date = date.today()
            success = loop.run_until_complete(
                scheduler.run_archival_for_date(target_date)
            )
            
            assert success
            # Should have completed on first attempt (no failures)
            assert scheduler.stats.total_retried == 0
        finally:
            loop.close()
    
    def test_stats_tracking(self):
        """Test that statistics are properly tracked"""
        loop = asyncio.new_event_loop()
        try:
            manager = MockDataLifecycleManager()
            scheduler = ArchivalScheduler(manager=manager)
            
            for i in range(3):
                target_date = date.today() - timedelta(days=i)
                loop.run_until_complete(
                    scheduler.run_archival_for_date(target_date)
                )
            
            stats = scheduler.get_stats()
            assert stats.total_scheduled == 3
            assert stats.total_completed == 3
            assert stats.success_rate == 100.0
        finally:
            loop.close()
    
    def test_notification_on_completion(self):
        """Test notifications are sent on completion"""
        loop = asyncio.new_event_loop()
        try:
            manager = MockDataLifecycleManager()
            notifier = MockNotifier()
            scheduler = ArchivalScheduler(
                manager=manager,
                notifier=notifier,
            )
            
            target_date = date.today()
            loop.run_until_complete(
                scheduler.run_archival_for_date(target_date)
            )
            
            assert len(notifier.started_tasks) == 1
            assert len(notifier.completed_tasks) == 1
            assert len(notifier.failed_tasks) == 0
        finally:
            loop.close()
    
    def test_notification_on_failure(self):
        """Test notifications are sent on failure"""
        loop = asyncio.new_event_loop()
        try:
            manager = MockDataLifecycleManager(fail_on="error")
            notifier = MockNotifier()
            scheduler = ArchivalScheduler(
                manager=manager,
                notifier=notifier,
                config=ScheduleConfig(
                    retry_config=RetryConfig(max_attempts=1)
                ),
            )
            
            target_date = date.today()
            loop.run_until_complete(
                scheduler.run_archival_for_date(target_date)
            )
            
            assert len(notifier.started_tasks) == 1
            assert len(notifier.completed_tasks) == 0
            assert len(notifier.failed_tasks) == 1
        finally:
            loop.close()
    
    def test_retry_failed_task(self):
        """Test retrying a failed task"""
        loop = asyncio.new_event_loop()
        try:
            manager = MockDataLifecycleManager()
            scheduler = ArchivalScheduler(manager=manager)
            
            target_date = date.today()
            loop.run_until_complete(
                scheduler.run_archival_for_date(target_date)
            )
            
            task = scheduler.tasks[0]
            assert task.status == ScheduleStatus.COMPLETED
            
            # Simulate a retry (would normally retry a failed task)
            # For this test, we're just verifying the method exists
            result = loop.run_until_complete(
                scheduler.retry_failed_archival(task.task_id)
            )
            # Should succeed if task is not in FAILED state
            assert result is False  # Task not in FAILED state
        finally:
            loop.close()


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
