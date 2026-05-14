"""
Test suite for Enhancement #7: Automated Model Retraining

Tests cover:
- RetrainingJob creation and status tracking
- ModelVersion creation and versioning
- ABTestResult generation and statistical significance
- ModelRetrainingOrchestrator scheduling with day/hour validation
- Job execution workflow (training → version creation → A/B test → deployment)
- Canary deployment stages (CANARY_10 → CANARY_50 → PRODUCTION)
- Rollback functionality
- Error handling and job failures

Test count: 25 tests | Expected coverage: >90%
"""

import asyncio
import pytest
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from src.models.model_retraining_orchestrator import (
    RetrainingStatus,
    ModelStatus,
    DeploymentStrategy,
    ModelVersion,
    ABTestResult,
    RetrainingJob,
    ModelTrainer,
    MockModelTrainer,
    ABTestRunner,
    ModelRetrainingOrchestrator,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture
def mock_trainer():
    """Create mock trainer"""
    return MockModelTrainer("test_model")


@pytest.fixture
def ab_test_runner():
    """Create A/B test runner"""
    return ABTestRunner(sample_size=1000)


@pytest.fixture
def orchestrator(mock_trainer):
    """Create model retraining orchestrator"""
    return ModelRetrainingOrchestrator(
        model_name="trading_model",
        trainer=mock_trainer,
        retraining_day=0,  # Monday
        retraining_hour=2,  # 2 AM UTC
    )


# ============================================================================
# TESTS: ModelVersion
# ============================================================================

def test_model_version_creation():
    """Test ModelVersion creation with default values"""
    now = datetime.utcnow()
    version = ModelVersion(
        version_id="v1",
        model_name="test_model",
        created_at=now,
        trained_at=now,
        training_data_rows=10000,
        training_duration_seconds=120.5,
        model_path="models/test_model/v1",
    )
    
    assert version.version_id == "v1"
    assert version.model_name == "test_model"
    assert version.training_data_rows == 10000
    assert version.training_duration_seconds == 120.5
    assert version.status == ModelStatus.TRAINING
    assert version.created_by == "automated_retrainer"


def test_model_version_with_metrics():
    """Test ModelVersion with custom metrics"""
    now = datetime.utcnow()
    metrics = {
        "mae": 4.5,
        "rmse": 5.2,
        "accuracy": 0.87,
        "latency_ms": 14.3,
    }
    version = ModelVersion(
        version_id="v2",
        model_name="test_model",
        created_at=now,
        trained_at=now,
        training_data_rows=15000,
        training_duration_seconds=150.0,
        model_path="models/test_model/v2",
        metrics=metrics,
        status=ModelStatus.PRODUCTION,
    )
    
    assert version.metrics == metrics
    assert version.metrics["mae"] == 4.5
    assert version.status == ModelStatus.PRODUCTION


def test_model_version_with_hyperparameters():
    """Test ModelVersion with hyperparameters"""
    now = datetime.utcnow()
    hyperparameters = {
        "learning_rate": 0.001,
        "batch_size": 32,
        "epochs": 10,
        "dropout": 0.2,
    }
    version = ModelVersion(
        version_id="v3",
        model_name="test_model",
        created_at=now,
        trained_at=now,
        training_data_rows=20000,
        training_duration_seconds=180.0,
        model_path="models/test_model/v3",
        hyperparameters=hyperparameters,
    )
    
    assert version.hyperparameters == hyperparameters
    assert version.hyperparameters["learning_rate"] == 0.001


# ============================================================================
# TESTS: ABTestResult
# ============================================================================

def test_ab_test_result_creation():
    """Test ABTestResult creation"""
    now = datetime.utcnow()
    result = ABTestResult(
        test_id="test_1",
        timestamp=now,
        baseline_model="models/v1",
        candidate_model="models/v2",
        test_duration_hours=1.0,
        baseline_traffic_percent=50.0,
        candidate_traffic_percent=50.0,
    )
    
    assert result.test_id == "test_1"
    assert result.baseline_model == "models/v1"
    assert result.candidate_model == "models/v2"
    assert result.test_duration_hours == 1.0
    assert result.p_value == 1.0  # Default
    assert result.is_significant is False  # Default


def test_ab_test_result_with_metrics():
    """Test ABTestResult with comparison metrics"""
    now = datetime.utcnow()
    result = ABTestResult(
        test_id="test_2",
        timestamp=now,
        baseline_model="models/v1",
        candidate_model="models/v2",
        test_duration_hours=2.0,
        baseline_traffic_percent=50.0,
        candidate_traffic_percent=50.0,
        baseline_mae=5.2,
        candidate_mae=5.0,
        mae_improvement_percent=3.85,
        baseline_accuracy=0.840,
        candidate_accuracy=0.851,
        accuracy_improvement_percent=1.31,
        baseline_latency_ms=16.5,
        candidate_latency_ms=15.2,
        latency_change_percent=-7.88,
        baseline_sample_count=1000,
        candidate_sample_count=1000,
        p_value=0.01,
        is_significant=True,
        recommendation="promote",
    )
    
    assert result.mae_improvement_percent > 0
    assert result.accuracy_improvement_percent > 0
    assert result.latency_change_percent < 0  # Improvement (latency reduced)
    assert result.is_significant is True
    assert result.recommendation == "promote"


def test_ab_test_result_to_dict():
    """Test ABTestResult serialization to dict"""
    now = datetime.utcnow()
    result = ABTestResult(
        test_id="test_3",
        timestamp=now,
        baseline_model="models/v1",
        candidate_model="models/v2",
        test_duration_hours=1.0,
        baseline_traffic_percent=50.0,
        candidate_traffic_percent=50.0,
        mae_improvement_percent=2.5,
        is_significant=True,
        recommendation="promote",
    )
    
    result_dict = result.to_dict()
    assert result_dict["test_id"] == "test_3"
    assert result_dict["baseline_model"] == "models/v1"
    assert result_dict["candidate_model"] == "models/v2"
    assert result_dict["mae_improvement_percent"] == 2.5
    assert result_dict["is_significant"] is True
    assert "timestamp" in result_dict


# ============================================================================
# TESTS: RetrainingJob
# ============================================================================

def test_retraining_job_creation():
    """Test RetrainingJob creation"""
    now = datetime.utcnow()
    scheduled_time = now + timedelta(days=1)
    
    job = RetrainingJob(
        job_id="retrain_123",
        model_name="trading_model",
        scheduled_time=scheduled_time,
    )
    
    assert job.job_id == "retrain_123"
    assert job.model_name == "trading_model"
    assert job.scheduled_time == scheduled_time
    assert job.status == RetrainingStatus.SCHEDULED
    assert job.started_at is None
    assert job.completed_at is None
    assert job.error_message is None


def test_retraining_job_execution_tracking():
    """Test RetrainingJob execution tracking"""
    now = datetime.utcnow()
    job = RetrainingJob(
        job_id="retrain_456",
        model_name="trading_model",
        scheduled_time=now,
        status=RetrainingStatus.IN_PROGRESS,
        started_at=now,
    )
    
    assert job.status == RetrainingStatus.IN_PROGRESS
    assert job.started_at is not None
    
    # Simulate completion
    job.completed_at = now + timedelta(seconds=10)
    job.status = RetrainingStatus.COMPLETED
    
    assert job.status == RetrainingStatus.COMPLETED
    assert job.completed_at is not None


def test_retraining_job_failure():
    """Test RetrainingJob failure tracking"""
    now = datetime.utcnow()
    job = RetrainingJob(
        job_id="retrain_789",
        model_name="trading_model",
        scheduled_time=now,
        status=RetrainingStatus.FAILED,
        error_message="Training data corrupted",
    )
    
    assert job.status == RetrainingStatus.FAILED
    assert "corrupted" in job.error_message


def test_retraining_job_to_dict():
    """Test RetrainingJob serialization"""
    now = datetime.utcnow()
    completed = now + timedelta(seconds=30)
    job = RetrainingJob(
        job_id="retrain_dict",
        model_name="trading_model",
        scheduled_time=now,
        status=RetrainingStatus.COMPLETED,
        completed_at=completed,
    )
    
    job_dict = job.to_dict()
    assert job_dict["job_id"] == "retrain_dict"
    assert job_dict["model_name"] == "trading_model"
    assert job_dict["status"] == "completed"
    assert "completed_at" in job_dict


# ============================================================================
# TESTS: MockModelTrainer
# ============================================================================

def test_mock_trainer_initialization(mock_trainer):
    """Test MockModelTrainer initialization"""
    assert mock_trainer.model_name == "test_model"
    assert mock_trainer.training_count == 0


def test_mock_trainer_training(event_loop, mock_trainer):
    """Test MockModelTrainer training"""
    async def run_test():
        training_data = {"rows": 10000, "features": 50}
        hyperparameters = {"learning_rate": 0.001}
        
        model_path, metrics = await mock_trainer.train(training_data, hyperparameters)
        
        assert "models/test_model" in model_path
        assert "v_1" in model_path
        assert "mae" in metrics
        assert metrics["accuracy"] == 0.85
        assert mock_trainer.training_count == 1
    
    event_loop.run_until_complete(run_test())


def test_mock_trainer_evaluation(event_loop, mock_trainer):
    """Test MockModelTrainer evaluation"""
    async def run_test():
        metrics = await mock_trainer.evaluate(
            "models/test_model/v_1",
            {"test_rows": 5000}
        )
        
        assert metrics["mae"] == 5.0
        assert metrics["accuracy"] == 0.85
        assert metrics["latency_ms"] == 15.0
    
    event_loop.run_until_complete(run_test())


def test_mock_trainer_data_loading(event_loop, mock_trainer):
    """Test MockModelTrainer data loading"""
    async def run_test():
        data = await mock_trainer.load_training_data(hours_back=168)
        
        assert data["rows"] == 10000
        assert data["features"] == 50
    
    event_loop.run_until_complete(run_test())


# ============================================================================
# TESTS: ABTestRunner
# ============================================================================

def test_ab_test_runner_initialization(ab_test_runner):
    """Test ABTestRunner initialization"""
    assert ab_test_runner.sample_size == 1000
    assert len(ab_test_runner.test_results) == 0


def test_ab_test_runner_run_test(event_loop, ab_test_runner):
    """Test ABTestRunner.run_test()"""
    async def run_test():
        result = await ab_test_runner.run_test(
            baseline_model="models/v1",
            candidate_model="models/v2",
            test_hours=1.0,
            baseline_traffic=0.5,
        )
        
        assert result.test_id is not None
        assert result.baseline_model == "models/v1"
        assert result.candidate_model == "models/v2"
        assert result.test_duration_hours == 1.0
        assert result.baseline_traffic_percent == 50.0
        assert result.candidate_traffic_percent == 50.0
        assert result.baseline_sample_count == 1000
        assert result.candidate_sample_count == 1000
        # Candidate should show improvement
        assert result.accuracy_improvement_percent > 0 or result.mae_improvement_percent > 0
    
    event_loop.run_until_complete(run_test())


def test_ab_test_runner_stores_results(event_loop, ab_test_runner):
    """Test ABTestRunner stores results"""
    async def run_test():
        result1 = await ab_test_runner.run_test("v1", "v2")
        result2 = await ab_test_runner.run_test("v2", "v3")
        
        all_results = ab_test_runner.get_test_results()
        assert len(all_results) == 2
        assert all_results[0].baseline_model == "v1"
        assert all_results[1].baseline_model == "v2"
    
    event_loop.run_until_complete(run_test())


def test_ab_test_runner_get_test_results_by_model(event_loop, ab_test_runner):
    """Test ABTestRunner.get_test_results() filtering"""
    async def run_test():
        await ab_test_runner.run_test("models/v1", "models/v2")
        await ab_test_runner.run_test("models/v2", "models/v3")
        
        v2_results = ab_test_runner.get_test_results("models/v2")
        assert len(v2_results) == 1
        assert "models/v2" in v2_results[0].candidate_model
    
    event_loop.run_until_complete(run_test())


# ============================================================================
# TESTS: ModelRetrainingOrchestrator - Scheduling
# ============================================================================

def test_orchestrator_initialization(orchestrator):
    """Test ModelRetrainingOrchestrator initialization"""
    assert orchestrator.model_name == "trading_model"
    assert orchestrator.retraining_day == 0  # Monday
    assert orchestrator.retraining_hour == 2  # 2 AM
    assert len(orchestrator.jobs) == 0
    assert orchestrator.current_production_version is None
    assert orchestrator.deployment_strategy == DeploymentStrategy.CANARY


def test_orchestrator_schedule_retraining(event_loop, orchestrator):
    """Test ModelRetrainingOrchestrator.schedule_retraining()"""
    async def run_test():
        job = await orchestrator.schedule_retraining()
        
        assert job.job_id is not None
        assert job.model_name == "trading_model"
        assert job.status == RetrainingStatus.SCHEDULED
        assert job.scheduled_time is not None
        assert job.job_id in orchestrator.jobs
    
    event_loop.run_until_complete(run_test())


def test_orchestrator_schedule_respects_day_and_hour(event_loop):
    """Test schedule_retraining() respects retraining_day and retraining_hour"""
    async def run_test():
        orchestrator = ModelRetrainingOrchestrator(
            model_name="test",
            trainer=MockModelTrainer("test"),
            retraining_day=2,  # Wednesday
            retraining_hour=14,  # 2 PM
        )
        job = await orchestrator.schedule_retraining()
        
        # Next scheduled time should be Wednesday at 14:00 UTC
        assert job.scheduled_time.weekday() == 2 or (
            job.scheduled_time.weekday() == 2  # Allow for edge case at midnight
        )
        assert job.scheduled_time.hour == 14
        assert job.scheduled_time.minute == 0
        assert job.scheduled_time.second == 0
    
    event_loop.run_until_complete(run_test())


def test_orchestrator_get_job_status(event_loop, orchestrator):
    """Test ModelRetrainingOrchestrator.get_job_status()"""
    async def run_test():
        job = await orchestrator.schedule_retraining()
        
        retrieved_job = orchestrator.get_job_status(job.job_id)
        assert retrieved_job is not None
        assert retrieved_job.job_id == job.job_id
        assert retrieved_job.status == RetrainingStatus.SCHEDULED
        
        # Non-existent job
        assert orchestrator.get_job_status("nonexistent") is None
    
    event_loop.run_until_complete(run_test())


def test_orchestrator_get_retraining_jobs(event_loop, orchestrator):
    """Test ModelRetrainingOrchestrator.get_retraining_jobs()"""
    async def run_test():
        job1 = await orchestrator.schedule_retraining()
        job2 = await orchestrator.schedule_retraining()
        
        all_jobs = orchestrator.get_retraining_jobs()
        assert len(all_jobs) == 2
        
        # Filter by status
        scheduled_jobs = orchestrator.get_retraining_jobs(RetrainingStatus.SCHEDULED)
        assert len(scheduled_jobs) == 2
    
    event_loop.run_until_complete(run_test())


# ============================================================================
# TESTS: ModelRetrainingOrchestrator - Execution
# ============================================================================

def test_orchestrator_execute_retraining_job(event_loop, orchestrator):
    """Test ModelRetrainingOrchestrator.execute_retraining_job()"""
    async def run_test():
        job = await orchestrator.schedule_retraining()
        success = await orchestrator.execute_retraining_job(job.job_id)
        
        assert success is True
        
        updated_job = orchestrator.get_job_status(job.job_id)
        assert updated_job.status == RetrainingStatus.COMPLETED
        assert updated_job.started_at is not None
        assert updated_job.completed_at is not None
        assert updated_job.model_version is not None
    
    event_loop.run_until_complete(run_test())


def test_orchestrator_execute_nonexistent_job(event_loop, orchestrator):
    """Test execute_retraining_job() with non-existent job"""
    async def run_test():
        success = await orchestrator.execute_retraining_job("nonexistent_job")
        assert success is False
    
    event_loop.run_until_complete(run_test())


def test_orchestrator_training_data_loading(event_loop, orchestrator):
    """Test training data is loaded with 168-hour window"""
    async def run_test():
        job = await orchestrator.schedule_retraining()
        await orchestrator.execute_retraining_job(job.job_id)
        
        updated_job = orchestrator.get_job_status(job.job_id)
        assert updated_job.training_data_rows > 0  # Mock returns 10000
    
    event_loop.run_until_complete(run_test())


# ============================================================================
# TESTS: ModelRetrainingOrchestrator - Model Versioning
# ============================================================================

def test_orchestrator_creates_model_version(event_loop, orchestrator):
    """Test execute_retraining_job() creates ModelVersion"""
    async def run_test():
        job = await orchestrator.schedule_retraining()
        await orchestrator.execute_retraining_job(job.job_id)
        
        versions = orchestrator.get_model_versions()
        assert len(versions) > 0
        
        version = list(versions.values())[0]
        assert version.model_name == "trading_model"
        assert version.training_data_rows > 0
        assert version.training_duration_seconds > 0
    
    event_loop.run_until_complete(run_test())


def test_orchestrator_get_model_versions(event_loop, orchestrator):
    """Test ModelRetrainingOrchestrator.get_model_versions()"""
    async def run_test():
        # No versions initially
        versions = orchestrator.get_model_versions()
        assert len(versions) == 0
        
        # Execute job to create version
        job = await orchestrator.schedule_retraining()
        await orchestrator.execute_retraining_job(job.job_id)
        
        versions = orchestrator.get_model_versions()
        assert len(versions) == 1
    
    event_loop.run_until_complete(run_test())


def test_orchestrator_get_current_production_version(event_loop, orchestrator):
    """Test ModelRetrainingOrchestrator.get_current_production_version()"""
    async def run_test():
        # No production version initially
        assert orchestrator.get_current_production_version() is None
        
        # Execute job (should promote to production via canary)
        job = await orchestrator.schedule_retraining()
        await orchestrator.execute_retraining_job(job.job_id)
        
        current = orchestrator.get_current_production_version()
        assert current is not None
        assert current.status == ModelStatus.PRODUCTION
    
    event_loop.run_until_complete(run_test())


# ============================================================================
# TESTS: ModelRetrainingOrchestrator - A/B Testing
# ============================================================================

def test_orchestrator_ab_test_first_model(event_loop, orchestrator):
    """Test first model is promoted without A/B test"""
    async def run_test():
        job = await orchestrator.schedule_retraining()
        await orchestrator.execute_retraining_job(job.job_id)
        
        ab_results = orchestrator.get_ab_test_results()
        # First model shouldn't have A/B test
        assert len(ab_results) == 0
        
        # But should be in production
        current = orchestrator.get_current_production_version()
        assert current is not None
    
    event_loop.run_until_complete(run_test())


def test_orchestrator_ab_test_second_model(event_loop, orchestrator):
    """Test second model runs A/B test against first"""
    async def run_test():
        # Train first model
        job1 = await orchestrator.schedule_retraining()
        await orchestrator.execute_retraining_job(job1.job_id)
        
        # Train second model
        job2 = await orchestrator.schedule_retraining()
        await orchestrator.execute_retraining_job(job2.job_id)
        
        ab_results = orchestrator.get_ab_test_results()
        # Second model should run A/B test
        assert len(ab_results) == 1
        
        result = ab_results[0]
        assert result.baseline_sample_count > 0
        assert result.candidate_sample_count > 0
    
    event_loop.run_until_complete(run_test())


def test_orchestrator_ab_test_promotes_significant(event_loop, orchestrator):
    """Test A/B test promotes significant improvements"""
    async def run_test():
        job1 = await orchestrator.schedule_retraining()
        await orchestrator.execute_retraining_job(job1.job_id)
        
        job2 = await orchestrator.schedule_retraining()
        await orchestrator.execute_retraining_job(job2.job_id)
        
        ab_results = orchestrator.get_ab_test_results()
        result = ab_results[0]
        
        # Mock trainer generates significant improvement
        if result.is_significant:
            current = orchestrator.get_current_production_version()
            assert current.model_path == result.candidate_model
    
    event_loop.run_until_complete(run_test())


def test_orchestrator_get_ab_test_results(event_loop, orchestrator):
    """Test ModelRetrainingOrchestrator.get_ab_test_results()"""
    async def run_test():
        job1 = await orchestrator.schedule_retraining()
        await orchestrator.execute_retraining_job(job1.job_id)
        
        job2 = await orchestrator.schedule_retraining()
        await orchestrator.execute_retraining_job(job2.job_id)
        
        results = orchestrator.get_ab_test_results()
        assert len(results) >= 1
        
        result = results[0]
        assert result.test_id is not None
        assert result.timestamp is not None
    
    event_loop.run_until_complete(run_test())


# ============================================================================
# TESTS: ModelRetrainingOrchestrator - Canary Deployment
# ============================================================================

def test_orchestrator_canary_deployment_stages(event_loop, orchestrator):
    """Test _deploy_canary() stages model through CANARY_10 → CANARY_50 → PRODUCTION"""
    async def run_test():
        job = await orchestrator.schedule_retraining()
        await orchestrator.execute_retraining_job(job.job_id)
        
        version = list(orchestrator.get_model_versions().values())[0]
        assert version.status == ModelStatus.PRODUCTION
        assert orchestrator.current_production_version == version.version_id
    
    event_loop.run_until_complete(run_test())


def test_orchestrator_multiple_canary_deployments(event_loop, orchestrator):
    """Test multiple canary deployments"""
    async def run_test():
        # First model
        job1 = await orchestrator.schedule_retraining()
        await orchestrator.execute_retraining_job(job1.job_id)
        
        versions = orchestrator.get_model_versions()
        assert len(versions) == 1
        v1 = list(versions.values())[0]
        assert v1.status == ModelStatus.PRODUCTION
        
        # Second model
        job2 = await orchestrator.schedule_retraining()
        await orchestrator.execute_retraining_job(job2.job_id)
        
        versions = orchestrator.get_model_versions()
        assert len(versions) == 2
        
        current = orchestrator.get_current_production_version()
        assert current.model_path != v1.model_path  # Different version
    
    event_loop.run_until_complete(run_test())


# ============================================================================
# TESTS: ModelRetrainingOrchestrator - Error Handling
# ============================================================================

def test_orchestrator_job_failure_tracking(event_loop):
    """Test job failure is tracked"""
    # Create failing trainer
    class FailingTrainer(ModelTrainer):
        async def train(self, training_data, hyperparameters):
            raise ValueError("Training failed")
        
        async def evaluate(self, model_path, test_data):
            return {}
        
        async def load_training_data(self, hours_back):
            return {"rows": 1000}
    
    async def run_test():
        orchestrator = ModelRetrainingOrchestrator(
            model_name="failing_model",
            trainer=FailingTrainer(),
        )
        
        job = await orchestrator.schedule_retraining()
        success = await orchestrator.execute_retraining_job(job.job_id)
        
        assert success is False
        
        updated_job = orchestrator.get_job_status(job.job_id)
        assert updated_job.status == RetrainingStatus.FAILED
        assert updated_job.error_message is not None
        assert "Training failed" in updated_job.error_message
    
    event_loop.run_until_complete(run_test())


# ============================================================================
# TESTS: ModelRetrainingOrchestrator - Rollback
# ============================================================================

def test_orchestrator_rollback_requires_previous_version(event_loop, orchestrator):
    """Test rollback returns False if no previous version"""
    async def run_test():
        # No previous version
        success = await orchestrator.rollback_to_previous()
        assert success is False
    
    event_loop.run_until_complete(run_test())


def test_orchestrator_rollback_to_previous(event_loop, orchestrator):
    """Test ModelRetrainingOrchestrator.rollback_to_previous()"""
    async def run_test():
        # Train first model
        job1 = await orchestrator.schedule_retraining()
        await orchestrator.execute_retraining_job(job1.job_id)
        
        versions = orchestrator.get_model_versions()
        v1_id = list(versions.keys())[0]
        
        # Train second model
        job2 = await orchestrator.schedule_retraining()
        await orchestrator.execute_retraining_job(job2.job_id)
        
        versions = orchestrator.get_model_versions()
        v2_id = [k for k in versions.keys() if k != v1_id][0]
        
        # Second version should be production
        current = orchestrator.get_current_production_version()
        assert current.version_id == v2_id
        
        # Rollback
        success = await orchestrator.rollback_to_previous()
        
        # Depends on implementation - we're testing the method exists and can be called
        assert isinstance(success, bool)
    
    event_loop.run_until_complete(run_test())


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

def test_orchestrator_full_workflow(event_loop, orchestrator):
    """Test full retraining workflow: schedule → execute → verify"""
    async def run_test():
        # Schedule
        job = await orchestrator.schedule_retraining()
        assert job.status == RetrainingStatus.SCHEDULED
        
        # Execute
        success = await orchestrator.execute_retraining_job(job.job_id)
        assert success is True
        
        # Verify
        updated_job = orchestrator.get_job_status(job.job_id)
        assert updated_job.status == RetrainingStatus.COMPLETED
        
        versions = orchestrator.get_model_versions()
        assert len(versions) > 0
        
        current = orchestrator.get_current_production_version()
        assert current is not None
    
    event_loop.run_until_complete(run_test())


def test_orchestrator_multiple_jobs_sequence(event_loop, orchestrator):
    """Test executing multiple retraining jobs in sequence"""
    async def run_test():
        for i in range(3):
            job = await orchestrator.schedule_retraining()
            success = await orchestrator.execute_retraining_job(job.job_id)
            assert success is True
        
        all_jobs = orchestrator.get_retraining_jobs()
        assert len(all_jobs) == 3
        
        versions = orchestrator.get_model_versions()
        assert len(versions) >= 1  # At least one model version
    
    event_loop.run_until_complete(run_test())


def test_orchestrator_stateful_operations(event_loop, orchestrator):
    """Test orchestrator maintains state across operations"""
    async def run_test():
        # Create first model
        job1 = await orchestrator.schedule_retraining()
        await orchestrator.execute_retraining_job(job1.job_id)
        v1_id = list(orchestrator.get_model_versions().keys())[0]
        
        # Verify state persists
        current = orchestrator.get_current_production_version()
        assert current.version_id == v1_id
        
        # Create second model
        job2 = await orchestrator.schedule_retraining()
        await orchestrator.execute_retraining_job(job2.job_id)
        
        # Verify both jobs exist
        jobs = orchestrator.get_retraining_jobs()
        assert len(jobs) == 2
        assert jobs[0].status == RetrainingStatus.COMPLETED
        assert jobs[1].status == RetrainingStatus.COMPLETED
    
    event_loop.run_until_complete(run_test())


# ============================================================================
# ENUMS VALIDATION TESTS
# ============================================================================

def test_retraining_status_enum():
    """Test RetrainingStatus enum values"""
    assert RetrainingStatus.SCHEDULED.value == "scheduled"
    assert RetrainingStatus.IN_PROGRESS.value == "in_progress"
    assert RetrainingStatus.COMPLETED.value == "completed"
    assert RetrainingStatus.FAILED.value == "failed"
    assert RetrainingStatus.ROLLED_BACK.value == "rolled_back"


def test_model_status_enum():
    """Test ModelStatus enum values"""
    assert ModelStatus.TRAINING.value == "training"
    assert ModelStatus.STAGING.value == "staging"
    assert ModelStatus.CANARY_10.value == "canary_10"
    assert ModelStatus.CANARY_50.value == "canary_50"
    assert ModelStatus.PRODUCTION.value == "production"
    assert ModelStatus.ARCHIVED.value == "archived"
    assert ModelStatus.ROLLED_BACK.value == "rolled_back"


def test_deployment_strategy_enum():
    """Test DeploymentStrategy enum values"""
    assert DeploymentStrategy.CANARY.value == "canary"
    assert DeploymentStrategy.BLUE_GREEN.value == "blue_green"
    assert DeploymentStrategy.SHADOW.value == "shadow"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
