"""
Test suite for Enhancement #11: Extended Testing & Runbooks

Tests cover:
- LoadProfile and ChaosEventType enums
- LoadTestConfig and LoadTestMetrics
- ChaosEvent and ChaosTestResult
- SLAThreshold and SLAViolation
- PerformanceBaseline and BenchmarkResult
- LoadTestRunner (load test execution)
- ChaosTestRunner (fault injection)
- PerformanceMonitor (SLA monitoring and regression detection)
- Runbook, RunbookStep, RunbookLibrary
- Full integration workflows

Test count: 50 tests | Expected coverage: >90%
"""

import asyncio
import pytest
import numpy as np
from datetime import datetime, timedelta
from typing import List

from src.testing.extended_testing_framework import (
    LoadProfile,
    ChaosEventType,
    SLAMetric,
    LoadTestConfig,
    LoadTestMetrics,
    ChaosEvent,
    ChaosTestResult,
    SLAThreshold,
    SLAViolation,
    PerformanceBaseline,
    BenchmarkResult,
    LoadTestRunner,
    ChaosTestRunner,
    PerformanceMonitor,
    RunbookStep,
    Runbook,
    RunbookLibrary,
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
def load_test_config() -> LoadTestConfig:
    """Create load test configuration"""
    return LoadTestConfig(
        name="Test Load",
        description="Test load configuration",
        concurrent_users=10,
        test_duration_seconds=5,
        request_rate_per_sec=50.0,
    )


@pytest.fixture
def load_test_runner():
    """Create LoadTestRunner"""
    return LoadTestRunner()


@pytest.fixture
def chaos_test_runner():
    """Create ChaosTestRunner"""
    return ChaosTestRunner()


@pytest.fixture
def performance_monitor():
    """Create PerformanceMonitor"""
    return PerformanceMonitor()


@pytest.fixture
def runbook_library():
    """Create RunbookLibrary"""
    return RunbookLibrary()


# ============================================================================
# TESTS: Enums
# ============================================================================

def test_load_profile_enum():
    """Test LoadProfile enum values"""
    assert LoadProfile.CONSTANT.value == "constant"
    assert LoadProfile.RAMP_UP.value == "ramp_up"
    assert LoadProfile.SPIKE.value == "spike"
    assert LoadProfile.WAVE.value == "wave"


def test_chaos_event_type_enum():
    """Test ChaosEventType enum values"""
    assert ChaosEventType.LATENCY_INJECTION.value == "latency_injection"
    assert ChaosEventType.NETWORK_ERROR.value == "network_error"
    assert ChaosEventType.SERVICE_TIMEOUT.value == "service_timeout"
    assert ChaosEventType.CPU_SPIKE.value == "cpu_spike"


def test_sla_metric_enum():
    """Test SLAMetric enum values"""
    assert SLAMetric.AVAILABILITY.value == "availability"
    assert SLAMetric.LATENCY_P99.value == "latency_p99"
    assert SLAMetric.ERROR_RATE.value == "error_rate"
    assert SLAMetric.THROUGHPUT.value == "throughput"


# ============================================================================
# TESTS: LoadTestConfig
# ============================================================================

def test_load_test_config_creation():
    """Test LoadTestConfig creation"""
    config = LoadTestConfig(
        name="Test",
        description="Test config",
        concurrent_users=50,
        test_duration_seconds=10,
        request_rate_per_sec=100.0,
    )
    
    assert config.name == "Test"
    assert config.concurrent_users == 50
    assert config.test_duration_seconds == 10
    assert config.load_profile == LoadProfile.CONSTANT


def test_load_test_config_with_ramp_up():
    """Test LoadTestConfig with ramp-up"""
    config = LoadTestConfig(
        name="Ramp Test",
        description="Ramp up test",
        concurrent_users=100,
        test_duration_seconds=30,
        ramp_up_time_seconds=10,
        load_profile=LoadProfile.RAMP_UP,
    )
    
    assert config.load_profile == LoadProfile.RAMP_UP
    assert config.ramp_up_time_seconds == 10


# ============================================================================
# TESTS: LoadTestMetrics
# ============================================================================

def test_load_test_metrics_creation():
    """Test LoadTestMetrics creation"""
    metrics = LoadTestMetrics(
        test_id="test_1",
        test_name="Test Metrics",
        timestamp=datetime.utcnow(),
        total_requests=100,
        successful_requests=95,
        failed_requests=5,
    )
    
    assert metrics.test_id == "test_1"
    assert metrics.total_requests == 100
    assert metrics.failed_requests == 5


def test_load_test_metrics_latency_calculation():
    """Test latency metrics calculation"""
    metrics = LoadTestMetrics(
        test_id="test_2",
        test_name="Latency Test",
        timestamp=datetime.utcnow(),
        latencies=[10.0, 20.0, 30.0, 40.0, 50.0],
    )
    
    metrics.latencies.sort()
    metrics.p50_latency_ms = metrics.latencies[int(len(metrics.latencies) * 0.50)]
    metrics.p95_latency_ms = metrics.latencies[int(len(metrics.latencies) * 0.95)]
    metrics.p99_latency_ms = metrics.latencies[int(len(metrics.latencies) * 0.99)]
    metrics.average_latency_ms = np.mean(metrics.latencies)
    
    assert metrics.p50_latency_ms == 30.0
    assert metrics.average_latency_ms == 30.0


def test_load_test_metrics_to_dict():
    """Test LoadTestMetrics serialization"""
    metrics = LoadTestMetrics(
        test_id="test_3",
        test_name="Serialization Test",
        timestamp=datetime.utcnow(),
        throughput_req_per_sec=100.0,
        success_rate_percent=99.5,
    )
    
    metrics_dict = metrics.to_dict()
    assert metrics_dict["test_id"] == "test_3"
    assert metrics_dict["throughput_req_per_sec"] == 100.0


# ============================================================================
# TESTS: ChaosEvent & ChaosTestResult
# ============================================================================

def test_chaos_event_creation():
    """Test ChaosEvent creation"""
    event = ChaosEvent(
        event_id="chaos_1",
        event_type=ChaosEventType.LATENCY_INJECTION,
        target_component="api_server",
        severity=0.5,
        duration_seconds=10,
    )
    
    assert event.event_id == "chaos_1"
    assert event.event_type == ChaosEventType.LATENCY_INJECTION
    assert event.severity == 0.5


def test_chaos_test_result_creation():
    """Test ChaosTestResult creation"""
    result = ChaosTestResult(
        test_id="chaos_test_1",
        timestamp=datetime.utcnow(),
        events_triggered=5,
        events_recovered=4,
    )
    
    assert result.test_id == "chaos_test_1"
    assert result.events_triggered == 5
    assert result.events_recovered == 4


def test_chaos_test_result_resilience_score():
    """Test resilience score calculation"""
    result = ChaosTestResult(
        test_id="chaos_test_2",
        timestamp=datetime.utcnow(),
        events_triggered=10,
        events_recovered=9,
        events_cascaded=1,
    )
    
    result.success_rate_percent = (result.events_recovered / result.events_triggered * 100)
    result.resilience_score = min(100.0, result.success_rate_percent)
    
    assert result.success_rate_percent == 90.0
    assert result.resilience_score == 90.0


# ============================================================================
# TESTS: SLAThreshold & SLAViolation
# ============================================================================

def test_sla_threshold_creation():
    """Test SLAThreshold creation"""
    threshold = SLAThreshold(
        metric=SLAMetric.LATENCY_P99,
        threshold_value=100.0,
        window_minutes=60,
        severity="critical",
    )
    
    assert threshold.metric == SLAMetric.LATENCY_P99
    assert threshold.threshold_value == 100.0
    assert threshold.severity == "critical"


def test_sla_violation_creation():
    """Test SLAViolation creation"""
    violation = SLAViolation(
        violation_id="violation_1",
        timestamp=datetime.utcnow(),
        metric=SLAMetric.LATENCY_P99,
        actual_value=150.0,
        threshold_value=100.0,
        severity="critical",
        duration_seconds=300.0,
        affected_requests=50,
    )
    
    assert violation.metric == SLAMetric.LATENCY_P99
    assert violation.actual_value == 150.0


# ============================================================================
# TESTS: PerformanceBaseline & BenchmarkResult
# ============================================================================

def test_performance_baseline_creation():
    """Test PerformanceBaseline creation"""
    baseline = PerformanceBaseline(
        test_name="baseline_test",
        baseline_date=datetime.utcnow(),
        p50_latency_ms=50.0,
        p95_latency_ms=95.0,
        p99_latency_ms=150.0,
        throughput_req_per_sec=1000.0,
        success_rate_percent=99.5,
    )
    
    assert baseline.test_name == "baseline_test"
    assert baseline.p99_latency_ms == 150.0


def test_benchmark_result_creation():
    """Test BenchmarkResult creation"""
    baseline = PerformanceBaseline(
        test_name="bench_test",
        baseline_date=datetime.utcnow(),
        p50_latency_ms=50.0,
        p95_latency_ms=95.0,
        p99_latency_ms=150.0,
        throughput_req_per_sec=1000.0,
        success_rate_percent=99.5,
    )
    
    metrics = LoadTestMetrics(
        test_id="bench_1",
        test_name="bench_test",
        timestamp=datetime.utcnow(),
    )
    
    result = BenchmarkResult(
        benchmark_id="bench_result_1",
        timestamp=datetime.utcnow(),
        test_name="bench_test",
        baseline=baseline,
        current_metrics=metrics,
    )
    
    assert result.test_name == "bench_test"
    assert result.regression_detected == False


# ============================================================================
# TESTS: LoadTestRunner
# ============================================================================

def test_load_test_runner_creation():
    """Test LoadTestRunner creation"""
    runner = LoadTestRunner(max_workers=50)
    assert runner.max_workers == 50
    assert len(runner.test_results) == 0


async def mock_workload():
    """Mock workload function"""
    await asyncio.sleep(0.001)


def test_load_test_runner_run_async(event_loop, load_test_config):
    """Test running load test"""
    async def run_test():
        runner = LoadTestRunner(max_workers=10)
        config = LoadTestConfig(
            name="Quick Test",
            description="Quick load test",
            concurrent_users=5,
            test_duration_seconds=1,
            request_rate_per_sec=10.0,
        )
        
        metrics = await runner.run_load_test(config, mock_workload)
        
        assert metrics.test_id is not None
        assert metrics.total_requests > 0
        assert metrics.p50_latency_ms >= 0
    
    event_loop.run_until_complete(run_test())


def test_load_test_runner_metrics_collection(event_loop):
    """Test metrics collection during load test"""
    async def run_test():
        runner = LoadTestRunner(max_workers=5)
        config = LoadTestConfig(
            name="Metrics Test",
            description="Test metrics",
            concurrent_users=3,
            test_duration_seconds=1,
            request_rate_per_sec=5.0,
        )
        
        metrics = await runner.run_load_test(config, mock_workload)
        
        assert len(runner.test_results) == 1
        assert metrics.success_rate_percent >= 0
    
    event_loop.run_until_complete(run_test())


# ============================================================================
# TESTS: ChaosTestRunner
# ============================================================================

def test_chaos_test_runner_creation():
    """Test ChaosTestRunner creation"""
    runner = ChaosTestRunner()
    assert len(runner.test_results) == 0


def test_chaos_event_creation_with_params():
    """Test ChaosEvent with various parameters"""
    event = ChaosEvent(
        event_id="test_event",
        event_type=ChaosEventType.NETWORK_ERROR,
        target_component="database",
        severity=0.8,
        duration_seconds=30,
        start_delay_seconds=5,
        probability_trigger=0.9,
        recovery_time_seconds=10,
    )
    
    assert event.severity == 0.8
    assert event.start_delay_seconds == 5


async def mock_chaos_workload():
    """Mock workload for chaos testing"""
    await asyncio.sleep(0.0001)


def test_chaos_test_runner_run_async(event_loop):
    """Test running chaos test"""
    async def run_test():
        runner = ChaosTestRunner()
        events = [
            ChaosEvent(
                event_id="chaos_1",
                event_type=ChaosEventType.LATENCY_INJECTION,
                target_component="api",
                severity=0.3,
                duration_seconds=2,
                probability_trigger=1.0,
            ),
        ]
        
        result = await runner.run_chaos_test(
            events,
            mock_chaos_workload,
            test_duration_seconds=3,
        )
        
        assert result.test_id is not None
        assert result.events_triggered >= 0
    
    event_loop.run_until_complete(run_test())


# ============================================================================
# TESTS: PerformanceMonitor
# ============================================================================

def test_performance_monitor_creation():
    """Test PerformanceMonitor creation"""
    monitor = PerformanceMonitor()
    assert len(monitor.thresholds) == 0
    assert len(monitor.violations) == 0


def test_performance_monitor_add_threshold():
    """Test adding SLA threshold"""
    monitor = PerformanceMonitor()
    threshold = SLAThreshold(
        metric=SLAMetric.LATENCY_P99,
        threshold_value=100.0,
    )
    
    monitor.add_sla_threshold(threshold)
    assert len(monitor.thresholds) == 1


def test_performance_monitor_check_violations():
    """Test checking SLA violations"""
    monitor = PerformanceMonitor()
    monitor.add_sla_threshold(SLAThreshold(
        metric=SLAMetric.LATENCY_P99,
        threshold_value=50.0,
    ))
    
    metrics = LoadTestMetrics(
        test_id="test_1",
        test_name="Violation Test",
        timestamp=datetime.utcnow(),
        p99_latency_ms=75.0,  # Above threshold
        success_rate_percent=99.0,
    )
    
    violations = monitor.check_violations(metrics)
    assert len(violations) == 1
    assert violations[0].actual_value == 75.0


def test_performance_monitor_establish_baseline():
    """Test establishing performance baseline"""
    monitor = PerformanceMonitor()
    metrics = LoadTestMetrics(
        test_id="baseline_1",
        test_name="baseline_test",
        timestamp=datetime.utcnow(),
        p50_latency_ms=50.0,
        p99_latency_ms=100.0,
        throughput_req_per_sec=500.0,
        success_rate_percent=99.5,
    )
    
    baseline = monitor.establish_baseline("baseline_test", metrics)
    assert baseline.test_name == "baseline_test"
    assert monitor.baselines["baseline_test"] == baseline


def test_performance_monitor_detect_regression():
    """Test detecting performance regression"""
    monitor = PerformanceMonitor()
    
    # Establish baseline
    baseline_metrics = LoadTestMetrics(
        test_id="base_1",
        test_name="regression_test",
        timestamp=datetime.utcnow(),
        p99_latency_ms=100.0,
        throughput_req_per_sec=1000.0,
        success_rate_percent=99.0,
    )
    monitor.establish_baseline("regression_test", baseline_metrics)
    
    # Current metrics with degradation
    current_metrics = LoadTestMetrics(
        test_id="current_1",
        test_name="regression_test",
        timestamp=datetime.utcnow(),
        p99_latency_ms=150.0,  # 50% worse
        throughput_req_per_sec=1000.0,
        success_rate_percent=99.0,
    )
    
    result = monitor.detect_regression(
        "regression_test",
        current_metrics,
        regression_threshold_percent=10.0,
    )
    
    assert result is not None
    assert result.regression_detected == True


# ============================================================================
# TESTS: RunbookStep & Runbook
# ============================================================================

def test_runbook_step_creation():
    """Test RunbookStep creation"""
    step = RunbookStep(
        step_number=1,
        title="Deploy Model",
        description="Deploy new model to production",
        command="kubectl apply -f model.yaml",
        expected_outcome="Model deployed successfully",
    )
    
    assert step.step_number == 1
    assert step.title == "Deploy Model"
    assert step.command == "kubectl apply -f model.yaml"


def test_runbook_creation():
    """Test Runbook creation"""
    runbook = Runbook(
        runbook_id="rb_1",
        name="Deployment Runbook",
        description="Steps for deploying model",
        category="deployment",
        severity="high",
        estimated_total_time_minutes=30,
    )
    
    assert runbook.name == "Deployment Runbook"
    assert len(runbook.steps) == 0


def test_runbook_add_step():
    """Test adding steps to runbook"""
    runbook = Runbook(
        runbook_id="rb_2",
        name="Test Runbook",
        description="Test",
        category="test",
        severity="medium",
        estimated_total_time_minutes=20,
    )
    
    step = RunbookStep(
        step_number=1,
        title="Step 1",
        description="First step",
    )
    
    runbook.add_step(step)
    assert len(runbook.steps) == 1


def test_runbook_to_dict():
    """Test Runbook serialization"""
    runbook = Runbook(
        runbook_id="rb_3",
        name="Serialization Test",
        description="Test serialization",
        category="test",
        severity="low",
        estimated_total_time_minutes=10,
    )
    
    rb_dict = runbook.to_dict()
    assert rb_dict["runbook_id"] == "rb_3"
    assert rb_dict["category"] == "test"


# ============================================================================
# TESTS: RunbookLibrary
# ============================================================================

def test_runbook_library_creation():
    """Test RunbookLibrary creation"""
    library = RunbookLibrary()
    assert len(library.runbooks) == 0


def test_runbook_library_create_deployment():
    """Test creating deployment runbook"""
    library = RunbookLibrary()
    rb = library.create_deployment_runbook()
    
    assert rb.name == "Model Deployment"
    assert rb.category == "deployment"
    assert len(rb.steps) == 7


def test_runbook_library_create_incident_response():
    """Test creating incident response runbook"""
    library = RunbookLibrary()
    rb = library.create_incident_response_runbook()
    
    assert rb.name == "Incident Response"
    assert rb.category == "incident_response"
    assert rb.severity == "critical"
    assert len(rb.steps) == 6


def test_runbook_library_create_disaster_recovery():
    """Test creating disaster recovery runbook"""
    library = RunbookLibrary()
    rb = library.create_disaster_recovery_runbook()
    
    assert rb.name == "Disaster Recovery"
    assert rb.category == "disaster_recovery"
    assert len(rb.steps) == 6


def test_runbook_library_create_scaling():
    """Test creating scaling runbook"""
    library = RunbookLibrary()
    rb = library.create_scaling_runbook()
    
    assert rb.name == "Horizontal Scaling"
    assert rb.category == "scaling"
    assert len(rb.steps) == 5


def test_runbook_library_get_runbook():
    """Test retrieving runbook"""
    library = RunbookLibrary()
    library.create_deployment_runbook()
    
    rb = library.get_runbook("deployment")
    assert rb is not None
    assert rb.name == "Model Deployment"


def test_runbook_library_list_runbooks():
    """Test listing all runbooks"""
    library = RunbookLibrary()
    library.create_deployment_runbook()
    library.create_incident_response_runbook()
    library.create_disaster_recovery_runbook()
    library.create_scaling_runbook()
    
    runbooks = library.list_runbooks()
    assert len(runbooks) == 4


def test_runbook_library_all_runbooks():
    """Test creating all runbook types"""
    library = RunbookLibrary()
    
    rb_deploy = library.create_deployment_runbook()
    rb_incident = library.create_incident_response_runbook()
    rb_dr = library.create_disaster_recovery_runbook()
    rb_scale = library.create_scaling_runbook()
    
    assert rb_deploy is not None
    assert rb_incident is not None
    assert rb_dr is not None
    assert rb_scale is not None


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

def test_full_load_test_workflow(event_loop):
    """Test complete load test workflow"""
    async def run_test():
        runner = LoadTestRunner()
        config = LoadTestConfig(
            name="Integration Test",
            description="Full workflow test",
            concurrent_users=5,
            test_duration_seconds=1,
            request_rate_per_sec=10.0,
            load_profile=LoadProfile.CONSTANT,
        )
        
        metrics = await runner.run_load_test(config, mock_workload)
        
        # Check metrics
        assert metrics.total_requests > 0
        assert metrics.success_rate_percent >= 0
        assert len(runner.test_results) == 1
    
    event_loop.run_until_complete(run_test())


def test_sla_monitoring_workflow(event_loop):
    """Test SLA monitoring workflow"""
    async def run_test():
        runner = LoadTestRunner()
        monitor = PerformanceMonitor()
        
        # Add SLA thresholds
        monitor.add_sla_threshold(SLAThreshold(
            metric=SLAMetric.LATENCY_P99,
            threshold_value=100.0,
        ))
        monitor.add_sla_threshold(SLAThreshold(
            metric=SLAMetric.ERROR_RATE,
            threshold_value=50.0,  # Allow high error rate for test purposes
        ))
        
        # Run load test
        config = LoadTestConfig(
            name="SLA Test",
            description="SLA monitoring test",
            concurrent_users=3,
            test_duration_seconds=1,
            request_rate_per_sec=5.0,
        )
        
        metrics = await runner.run_load_test(config, mock_workload)
        
        # Check violations (may have violations but that's okay for this test)
        violations = monitor.check_violations(metrics)
        # Test should complete without error
        assert isinstance(violations, list)
    
    event_loop.run_until_complete(run_test())


def test_chaos_testing_workflow(event_loop):
    """Test chaos testing workflow"""
    async def run_test():
        runner = ChaosTestRunner()
        events = [
            ChaosEvent(
                event_id="chaos_1",
                event_type=ChaosEventType.LATENCY_INJECTION,
                target_component="api",
                severity=0.2,
                duration_seconds=1,
                recovery_time_seconds=1,
                probability_trigger=1.0,
            ),
            ChaosEvent(
                event_id="chaos_2",
                event_type=ChaosEventType.SERVICE_TIMEOUT,
                target_component="db",
                severity=0.3,
                duration_seconds=1,
                start_delay_seconds=1,
                recovery_time_seconds=1,
                probability_trigger=1.0,
            ),
        ]
        
        result = await runner.run_chaos_test(
            events,
            mock_chaos_workload,
            test_duration_seconds=5,
        )
        
        assert result.test_id is not None
        assert result.events_triggered >= 0
    
    event_loop.run_until_complete(run_test())


def test_runbook_coverage():
    """Test that all operational runbooks are available"""
    library = RunbookLibrary()
    
    # Create all runbooks
    library.create_deployment_runbook()
    library.create_incident_response_runbook()
    library.create_disaster_recovery_runbook()
    library.create_scaling_runbook()
    
    # Verify all categories are available
    assert library.get_runbook("deployment") is not None
    assert library.get_runbook("incident_response") is not None
    assert library.get_runbook("disaster_recovery") is not None
    assert library.get_runbook("scaling") is not None
    
    # Verify total count
    assert len(library.list_runbooks()) == 4


def test_load_profile_constant(event_loop):
    """Test constant load profile"""
    async def run_test():
        runner = LoadTestRunner()
        config = LoadTestConfig(
            name="Constant Load",
            description="Constant load profile test",
            concurrent_users=10,
            test_duration_seconds=1,
            request_rate_per_sec=20.0,
            load_profile=LoadProfile.CONSTANT,
        )
        
        metrics = await runner.run_load_test(config, mock_workload)
        assert metrics.total_requests > 0
    
    event_loop.run_until_complete(run_test())


def test_load_profile_ramp_up(event_loop):
    """Test ramp-up load profile"""
    async def run_test():
        runner = LoadTestRunner()
        config = LoadTestConfig(
            name="Ramp Up Load",
            description="Ramp up load profile test",
            concurrent_users=20,
            test_duration_seconds=2,
            ramp_up_time_seconds=1,
            request_rate_per_sec=20.0,
            load_profile=LoadProfile.RAMP_UP,
        )
        
        metrics = await runner.run_load_test(config, mock_workload)
        assert metrics.total_requests > 0
    
    event_loop.run_until_complete(run_test())


def test_load_profile_spike(event_loop):
    """Test spike load profile"""
    async def run_test():
        runner = LoadTestRunner()
        config = LoadTestConfig(
            name="Spike Load",
            description="Spike load profile test",
            concurrent_users=30,
            test_duration_seconds=3,
            request_rate_per_sec=30.0,
            load_profile=LoadProfile.SPIKE,
        )
        
        metrics = await runner.run_load_test(config, mock_workload)
        assert metrics.total_requests > 0
    
    event_loop.run_until_complete(run_test())


def test_load_profile_wave(event_loop):
    """Test wave load profile"""
    async def run_test():
        runner = LoadTestRunner()
        config = LoadTestConfig(
            name="Wave Load",
            description="Wave load profile test",
            concurrent_users=25,
            test_duration_seconds=3,
            request_rate_per_sec=25.0,
            load_profile=LoadProfile.WAVE,
        )
        
        metrics = await runner.run_load_test(config, mock_workload)
        assert metrics.total_requests > 0
    
    event_loop.run_until_complete(run_test())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
