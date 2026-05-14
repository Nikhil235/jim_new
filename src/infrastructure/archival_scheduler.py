"""
Archival Scheduler - Orchestrates scheduled data archival operations

Manages daily scheduled archival with retry logic, error handling,
progress monitoring, and notifications.

Production Features:
- Daily scheduled archival at configurable time
- Automatic retry on failures
- Progress tracking and logging
- Concurrent archival coordination
- Performance metrics collection
- Integration with health monitoring

Example:
    >>> scheduler = ArchivalScheduler(manager=lifecycle_manager)
    >>> await scheduler.schedule_daily_archival(hour=2, minute=30)
    >>> # Archival runs daily at 2:30 AM
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, date
from enum import Enum
from typing import Dict, List, Optional, Callable, Any
from abc import ABC, abstractmethod


class ScheduleStatus(Enum):
    """Status of scheduled archival task"""
    IDLE = "idle"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class RetryStrategy(Enum):
    """Strategy for retrying failed operations"""
    NO_RETRY = "no_retry"
    IMMEDIATE = "immediate"  # Retry immediately
    EXPONENTIAL = "exponential"  # Exponential backoff
    LINEAR = "linear"  # Linear backoff


@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    max_attempts: int = 3
    initial_delay_seconds: int = 60
    max_delay_seconds: int = 3600
    
    def get_delay_seconds(self, attempt: int) -> int:
        """Calculate delay for given attempt number"""
        if self.strategy == RetryStrategy.NO_RETRY:
            return 0
        elif self.strategy == RetryStrategy.IMMEDIATE:
            return 0
        elif self.strategy == RetryStrategy.LINEAR:
            delay = self.initial_delay_seconds * (attempt + 1)
        elif self.strategy == RetryStrategy.EXPONENTIAL:
            delay = self.initial_delay_seconds * (2 ** attempt)
        else:
            delay = 0
        
        return min(delay, self.max_delay_seconds)


@dataclass
class ScheduleConfig:
    """Configuration for archival schedule"""
    hour: int = 2  # Hour of day (0-23)
    minute: int = 0  # Minute of hour (0-59)
    days_to_archive: int = 1  # How many days back to archive
    retry_config: RetryConfig = field(default_factory=RetryConfig)
    max_concurrent_operations: int = 3
    timeout_seconds: int = 3600  # 1 hour timeout
    send_notifications: bool = True


@dataclass
class ArchivalTask:
    """Single archival task"""
    task_id: str
    scheduled_for: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: ScheduleStatus = ScheduleStatus.IDLE
    error_message: Optional[str] = None
    duration_seconds: float = 0.0
    retry_count: int = 0
    
    @property
    def is_overdue(self) -> bool:
        """Check if task is overdue for execution"""
        return datetime.utcnow() > self.scheduled_for


@dataclass
class ScheduleStats:
    """Statistics for archival scheduling"""
    total_scheduled: int = 0
    total_completed: int = 0
    total_failed: int = 0
    total_retried: int = 0
    average_duration_seconds: float = 0.0
    last_run_time: Optional[datetime] = None
    next_scheduled_run: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage"""
        total = self.total_completed + self.total_failed
        if total == 0:
            return 0.0
        return (self.total_completed / total) * 100.0


class ScheduleNotifier(ABC):
    """Abstract base for schedule notifications"""
    
    @abstractmethod
    async def notify_started(self, task: ArchivalTask) -> None:
        """Notify that archival has started"""
        pass
    
    @abstractmethod
    async def notify_completed(self, task: ArchivalTask) -> None:
        """Notify that archival has completed successfully"""
        pass
    
    @abstractmethod
    async def notify_failed(self, task: ArchivalTask, error: str) -> None:
        """Notify that archival has failed"""
        pass


class LoggingNotifier(ScheduleNotifier):
    """Default notifier that logs to logger"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    async def notify_started(self, task: ArchivalTask) -> None:
        self.logger.info(f"Archival task {task.task_id} started")
    
    async def notify_completed(self, task: ArchivalTask) -> None:
        self.logger.info(
            f"Archival task {task.task_id} completed in {task.duration_seconds:.1f}s"
        )
    
    async def notify_failed(self, task: ArchivalTask, error: str) -> None:
        self.logger.error(
            f"Archival task {task.task_id} failed (attempt {task.retry_count}): {error}"
        )


class ArchivalScheduler:
    """
    Orchestrates scheduled data archival operations
    
    Responsibilities:
    - Schedule daily archival at configured time
    - Execute archival with error handling
    - Retry failed operations
    - Track progress and metrics
    - Send notifications
    
    Example:
        >>> from src.infrastructure.data_lifecycle_manager import DataLifecycleManager
        >>> manager = DataLifecycleManager()
        >>> scheduler = ArchivalScheduler(manager=manager)
        >>> await scheduler.schedule_daily_archival(hour=2)
        >>> # Archival runs daily at 2:00 AM
    """
    
    def __init__(
        self,
        manager: Any,  # DataLifecycleManager
        config: Optional[ScheduleConfig] = None,
        notifier: Optional[ScheduleNotifier] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize ArchivalScheduler
        
        Args:
            manager: DataLifecycleManager instance
            config: Schedule configuration
            notifier: Notification handler
            logger: Logger instance
        """
        self.manager = manager
        self.config = config or ScheduleConfig()
        self.notifier = notifier or LoggingNotifier(
            logger or logging.getLogger(__name__)
        )
        self.logger = logger or logging.getLogger(__name__)
        
        self.tasks: List[ArchivalTask] = []
        self.stats = ScheduleStats()
        self._scheduler_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def schedule_daily_archival(
        self,
        hour: int = 2,
        minute: int = 0,
        days_to_archive: int = 1,
    ) -> None:
        """
        Schedule daily archival at specified time
        
        Args:
            hour: Hour of day (0-23) for archival
            minute: Minute of hour (0-59) for archival
            days_to_archive: Number of days back to archive
        """
        self.config.hour = hour
        self.config.minute = minute
        self.config.days_to_archive = days_to_archive
        
        self.logger.info(
            f"Scheduling daily archival at {hour:02d}:{minute:02d} UTC"
        )
        
        if self._scheduler_task and not self._scheduler_task.done():
            self.logger.warning("Scheduler already running")
            return
        
        self._running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
    
    async def stop_scheduler(self) -> None:
        """Stop the scheduler"""
        self._running = False
        if self._scheduler_task:
            await self._scheduler_task
        self.logger.info("Scheduler stopped")
    
    async def _scheduler_loop(self) -> None:
        """Main scheduler loop"""
        while self._running:
            try:
                await self._check_and_run_scheduled_tasks()
                # Check every minute
                await asyncio.sleep(60)
            except Exception as e:
                self.logger.error(f"Scheduler loop error: {e}")
                await asyncio.sleep(60)
    
    async def _check_and_run_scheduled_tasks(self) -> None:
        """Check if any tasks should run and execute them"""
        now = datetime.utcnow()
        scheduled_time = self._get_next_scheduled_time()
        
        # Check if we should run archival
        if (now.hour == self.config.hour and 
            now.minute == self.config.minute and
            (not self.tasks or self.tasks[-1].scheduled_for.date() < now.date())):
            
            await self.run_archival_for_date(now.date())
    
    def _get_next_scheduled_time(self) -> datetime:
        """Calculate next scheduled execution time"""
        now = datetime.utcnow()
        scheduled = datetime(
            now.year,
            now.month,
            now.day,
            self.config.hour,
            self.config.minute,
        )
        
        # If scheduled time has passed today, schedule for tomorrow
        if scheduled <= now:
            scheduled += timedelta(days=1)
        
        self.stats.next_scheduled_run = scheduled
        return scheduled
    
    async def run_archival_for_date(self, target_date: date) -> bool:
        """
        Run archival for a specific date
        
        Args:
            target_date: Date to archive
        
        Returns:
            Success status
        """
        task_id = f"archival_{target_date.isoformat()}_{len(self.tasks)}"
        task = ArchivalTask(
            task_id=task_id,
            scheduled_for=datetime.combine(target_date, 
                                          time(self.config.hour, self.config.minute)),
        )
        
        self.tasks.append(task)
        self.stats.total_scheduled += 1
        
        # Run with retries
        success = await self._run_with_retries(task, target_date)
        
        return success
    
    async def _run_with_retries(self, task: ArchivalTask, 
                               target_date: date) -> bool:
        """Run archival with retry logic"""
        for attempt in range(self.config.retry_config.max_attempts):
            try:
                task.retry_count = attempt
                await self.notifier.notify_started(task)
                
                # Run archival
                task.started_at = datetime.utcnow()
                result = await asyncio.wait_for(
                    self.manager.archive_for_date(
                        datetime.combine(target_date, time(0, 0))
                    ),
                    timeout=self.config.timeout_seconds,
                )
                task.completed_at = datetime.utcnow()
                
                # Check results
                all_succeeded = all(result.values())
                if all_succeeded:
                    task.status = ScheduleStatus.COMPLETED
                    task.duration_seconds = (
                        task.completed_at - task.started_at
                    ).total_seconds()
                    
                    self.stats.total_completed += 1
                    self.stats.average_duration_seconds = (
                        (self.stats.average_duration_seconds * (self.stats.total_completed - 1) +
                         task.duration_seconds) / self.stats.total_completed
                    )
                    self.stats.last_run_time = task.completed_at
                    
                    await self.notifier.notify_completed(task)
                    self.logger.info(
                        f"Archival completed successfully in {task.duration_seconds:.1f}s"
                    )
                    return True
                else:
                    # Partial failure, retry
                    failed_types = [k for k, v in result.items() if not v]
                    raise ValueError(f"Archival failed for: {failed_types}")
                
            except asyncio.TimeoutError as e:
                error_msg = f"Archival timeout after {self.config.timeout_seconds}s"
                self.logger.warning(error_msg)
                
                if attempt < self.config.retry_config.max_attempts - 1:
                    delay = self.config.retry_config.get_delay_seconds(attempt)
                    self.logger.info(f"Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                    self.stats.total_retried += 1
                else:
                    task.status = ScheduleStatus.FAILED
                    task.error_message = error_msg
                    self.stats.total_failed += 1
                    await self.notifier.notify_failed(task, error_msg)
                    return False
                    
            except Exception as e:
                error_msg = str(e)
                self.logger.error(f"Archival error: {error_msg}")
                
                if attempt < self.config.retry_config.max_attempts - 1:
                    delay = self.config.retry_config.get_delay_seconds(attempt)
                    self.logger.info(f"Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                    self.stats.total_retried += 1
                else:
                    task.status = ScheduleStatus.FAILED
                    task.error_message = error_msg
                    self.stats.total_failed += 1
                    await self.notifier.notify_failed(task, error_msg)
                    return False
        
        return False
    
    async def retry_failed_archival(self, task_id: str) -> bool:
        """
        Retry a previously failed archival task
        
        Args:
            task_id: ID of task to retry
        
        Returns:
            Success status
        """
        task = next((t for t in self.tasks if t.task_id == task_id), None)
        if not task:
            self.logger.warning(f"Task {task_id} not found")
            return False
        
        if task.status != ScheduleStatus.FAILED:
            self.logger.warning(f"Task {task_id} is not in FAILED state")
            return False
        
        # Reset task state and retry
        task.status = ScheduleStatus.IDLE
        task.error_message = None
        task.retry_count = 0
        
        self.logger.info(f"Retrying archival task {task_id}")
        scheduled_date = task.scheduled_for.date()
        return await self._run_with_retries(task, scheduled_date)
    
    def get_task_status(self, task_id: str) -> Optional[ArchivalTask]:
        """Get status of a specific task"""
        return next((t for t in self.tasks if t.task_id == task_id), None)
    
    def get_all_tasks(self) -> List[ArchivalTask]:
        """Get all archival tasks"""
        return self.tasks.copy()
    
    def get_stats(self) -> ScheduleStats:
        """Get scheduler statistics"""
        return self.stats
    
    def get_failed_tasks(self) -> List[ArchivalTask]:
        """Get all failed tasks"""
        return [t for t in self.tasks if t.status == ScheduleStatus.FAILED]
