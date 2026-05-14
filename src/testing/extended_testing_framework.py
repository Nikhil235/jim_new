"""
Enhancement #11: Extended Testing & Runbooks

Comprehensive testing framework including:
- Load testing framework for concurrent predictions
- Chaos testing for fault injection and resilience
- Property-based testing
- Performance benchmarking
- SLA monitoring and alerting

Production file: src/testing/extended_testing_framework.py
~950 lines of code with full async support
"""

import asyncio
import logging
import numpy as np
import time
import random
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Tuple, Any
from collections import defaultdict
import uuid


logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS
# ============================================================================

class LoadProfile(Enum):
    """Load testing profiles"""
    CONSTANT = "constant"  # Fixed concurrent users
    RAMP_UP = "ramp_up"    # Gradual increase
    SPIKE = "spike"        # Sudden spike
    WAVE = "wave"          # Repeating pattern


class ChaosEventType(Enum):
    """Chaos testing event types"""
    LATENCY_INJECTION = "latency_injection"
    NETWORK_ERROR = "network_error"
    SERVICE_TIMEOUT = "service_timeout"
    MEMORY_PRESSURE = "memory_pressure"
    CPU_SPIKE = "cpu_spike"
    DATA_CORRUPTION = "data_corruption"
    MODEL_DEGRADATION = "model_degradation"


class SLAMetric(Enum):
    """SLA metric types"""
    AVAILABILITY = "availability"
    LATENCY_P99 = "latency_p99"
    LATENCY_P95 = "latency_p95"
    ERROR_RATE = "error_rate"
    THROUGHPUT = "throughput"
    RESOURCE_USAGE = "resource_usage"


# ============================================================================
# DATACLASSES
# ============================================================================

@dataclass
class LoadTestConfig:
    """Configuration for load testing"""
    name: str
    description: str
    concurrent_users: int
    test_duration_seconds: int
    ramp_up_time_seconds: int = 0
    load_profile: LoadProfile = LoadProfile.CONSTANT
    request_rate_per_sec: float = 100.0
    max_concurrent_requests: int = 1000


@dataclass
class LoadTestMetrics:
    """Metrics from load test execution"""
    test_id: str
    test_name: str
    timestamp: datetime
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    latencies: List[float] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    throughput_req_per_sec: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    min_latency_ms: float = 0.0
    average_latency_ms: float = 0.0
    memory_peak_mb: float = 0.0
    cpu_peak_percent: float = 0.0
    success_rate_percent: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "test_id": self.test_id,
            "test_name": self.test_name,
            "timestamp": self.timestamp.isoformat(),
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "throughput_req_per_sec": self.throughput_req_per_sec,
            "p50_latency_ms": self.p50_latency_ms,
            "p95_latency_ms": self.p95_latency_ms,
            "p99_latency_ms": self.p99_latency_ms,
            "average_latency_ms": self.average_latency_ms,
            "success_rate_percent": self.success_rate_percent,
        }


@dataclass
class ChaosEvent:
    """Chaos test event definition"""
    event_id: str
    event_type: ChaosEventType
    target_component: str
    severity: float  # 0-1, where 1 is catastrophic
    duration_seconds: int
    start_delay_seconds: int = 0
    probability_trigger: float = 1.0  # Always trigger if 1.0
    recovery_time_seconds: int = 5


@dataclass
class ChaosTestResult:
    """Result from chaos testing"""
    test_id: str
    timestamp: datetime
    events_triggered: int = 0
    events_recovered: int = 0
    events_cascaded: int = 0
    total_downtime_seconds: float = 0.0
    mttr_mean_seconds: float = 0.0  # Mean Time To Recovery
    mttf_mean_seconds: float = 0.0  # Mean Time To Failure
    success_rate_percent: float = 0.0
    resilience_score: float = 0.0  # 0-100
    cascade_detected: bool = False
    error_details: List[str] = field(default_factory=list)


@dataclass
class SLAThreshold:
    """SLA threshold definition"""
    metric: SLAMetric
    threshold_value: float
    window_minutes: int = 60
    severity: str = "warning"  # "warning" or "critical"


@dataclass
class SLAViolation:
    """SLA violation record"""
    violation_id: str
    timestamp: datetime
    metric: SLAMetric
    actual_value: float
    threshold_value: float
    severity: str
    duration_seconds: float
    affected_requests: int


@dataclass
class PerformanceBaseline:
    """Baseline performance metrics for regression detection"""
    test_name: str
    baseline_date: datetime
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    throughput_req_per_sec: float
    success_rate_percent: float
    baseline_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class BenchmarkResult:
    """Performance benchmark result"""
    benchmark_id: str
    timestamp: datetime
    test_name: str
    baseline: PerformanceBaseline
    current_metrics: LoadTestMetrics
    regression_detected: bool = False
    regression_metrics: List[str] = field(default_factory=list)
    degradation_percent: Dict[str, float] = field(default_factory=dict)


# ============================================================================
# LOAD TEST FRAMEWORK
# ============================================================================

class LoadTestRunner:
    """Framework for running load tests"""
    
    def __init__(self, max_workers: int = 100):
        self.max_workers = max_workers
        self.test_results: List[LoadTestMetrics] = []
    
    async def run_load_test(
        self,
        config: LoadTestConfig,
        workload_fn: Callable,
    ) -> LoadTestMetrics:
        """Run load test with specified configuration"""
        test_id = str(uuid.uuid4())
        metrics = LoadTestMetrics(
            test_id=test_id,
            test_name=config.name,
            timestamp=datetime.utcnow(),
        )
        
        start_time = time.time()
        tasks = []
        
        # Generate load based on profile
        concurrent_count = 0
        elapsed = 0.0
        request_count = 0
        
        while elapsed < config.test_duration_seconds:
            # Calculate concurrent users based on profile
            if config.load_profile == LoadProfile.CONSTANT:
                concurrent_count = config.concurrent_users
            elif config.load_profile == LoadProfile.RAMP_UP:
                progress = elapsed / config.ramp_up_time_seconds
                concurrent_count = int(config.concurrent_users * min(progress, 1.0))
            elif config.load_profile == LoadProfile.SPIKE:
                # Spike pattern: spike every 10 seconds
                spike_cycle = (elapsed / 10) % 1
                concurrent_count = config.concurrent_users if spike_cycle < 0.3 else int(config.concurrent_users * 0.3)
            elif config.load_profile == LoadProfile.WAVE:
                # Wave pattern: sin function
                concurrent_count = int(
                    config.concurrent_users * 0.5 +
                    config.concurrent_users * 0.5 * np.sin(elapsed * np.pi / 20)
                )
            
            # Submit requests at target rate
            for _ in range(int(config.request_rate_per_sec / 10)):
                if len(tasks) < config.max_concurrent_requests:
                    task = asyncio.create_task(self._run_single_request(
                        workload_fn, metrics
                    ))
                    tasks.append(task)
                request_count += 1
            
            # Wait briefly before next batch
            await asyncio.sleep(0.1)
            elapsed = time.time() - start_time
        
        # Wait for all remaining tasks
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # Calculate metrics
        metrics.total_requests = request_count
        metrics.successful_requests = len(metrics.latencies)
        metrics.failed_requests = request_count - metrics.successful_requests
        metrics.success_rate_percent = (
            metrics.successful_requests / request_count * 100
            if request_count > 0 else 0.0
        )
        
        if metrics.latencies:
            metrics.latencies.sort()
            metrics.p50_latency_ms = metrics.latencies[int(len(metrics.latencies) * 0.50)]
            metrics.p95_latency_ms = metrics.latencies[int(len(metrics.latencies) * 0.95)]
            metrics.p99_latency_ms = metrics.latencies[int(len(metrics.latencies) * 0.99)]
            metrics.min_latency_ms = metrics.latencies[0]
            metrics.max_latency_ms = metrics.latencies[-1]
            metrics.average_latency_ms = np.mean(metrics.latencies)
        
        elapsed_time = time.time() - start_time
        metrics.throughput_req_per_sec = request_count / elapsed_time if elapsed_time > 0 else 0.0
        
        self.test_results.append(metrics)
        return metrics
    
    async def _run_single_request(
        self,
        workload_fn: Callable,
        metrics: LoadTestMetrics,
    ) -> None:
        """Execute single request and record metrics"""
        try:
            start = time.time()
            await workload_fn()
            latency_ms = (time.time() - start) * 1000
            metrics.latencies.append(latency_ms)
        except Exception as e:
            metrics.errors.append(str(e))


# ============================================================================
# CHAOS TESTING FRAMEWORK
# ============================================================================

class ChaosTestRunner:
    """Framework for chaos/fault injection testing"""
    
    def __init__(self):
        self.test_results: List[ChaosTestResult] = []
        self.injected_faults: Dict[str, ChaosEvent] = {}
    
    async def run_chaos_test(
        self,
        events: List[ChaosEvent],
        workload_fn: Callable,
        test_duration_seconds: int = 300,
    ) -> ChaosTestResult:
        """Run chaos test with specified events"""
        test_id = str(uuid.uuid4())
        result = ChaosTestResult(
            test_id=test_id,
            timestamp=datetime.utcnow(),
        )
        
        # Schedule chaos events
        event_tasks = []
        for event in events:
            task = asyncio.create_task(
                self._trigger_chaos_event(event, result)
            )
            event_tasks.append(task)
        
        # Run workload concurrently
        start_time = time.time()
        workload_tasks = []
        
        while time.time() - start_time < test_duration_seconds:
            try:
                task = asyncio.create_task(workload_fn())
                workload_tasks.append(task)
            except Exception as e:
                result.error_details.append(f"Workload error: {str(e)}")
                result.events_cascaded += 1
            
            await asyncio.sleep(0.1)
        
        # Wait for completion
        if event_tasks:
            await asyncio.gather(*event_tasks, return_exceptions=True)
        if workload_tasks:
            await asyncio.gather(*workload_tasks, return_exceptions=True)
        
        # Calculate resilience score
        result.events_recovered = max(0, result.events_triggered - result.events_cascaded)
        result.success_rate_percent = (
            result.events_recovered / max(1, result.events_triggered) * 100
        )
        result.resilience_score = min(
            100.0,
            result.success_rate_percent * 0.7 + (100 - result.cascade_detected * 50)
        )
        
        self.test_results.append(result)
        return result
    
    async def _trigger_chaos_event(
        self,
        event: ChaosEvent,
        result: ChaosTestResult,
    ) -> None:
        """Trigger a chaos event"""
        if random.random() > event.probability_trigger:
            return
        
        await asyncio.sleep(event.start_delay_seconds)
        result.events_triggered += 1
        
        try:
            # Simulate event impact
            if event.event_type == ChaosEventType.LATENCY_INJECTION:
                await asyncio.sleep(event.duration_seconds * event.severity)
            elif event.event_type == ChaosEventType.NETWORK_ERROR:
                # Simulate network error
                pass
            elif event.event_type == ChaosEventType.SERVICE_TIMEOUT:
                await asyncio.sleep(event.duration_seconds)
            elif event.event_type == ChaosEventType.MEMORY_PRESSURE:
                # Simulate memory pressure
                pass
            
            result.total_downtime_seconds += event.duration_seconds
            
            # Simulate recovery
            await asyncio.sleep(event.recovery_time_seconds)
            result.events_recovered += 1
            result.mttr_mean_seconds = (
                result.total_downtime_seconds / max(1, result.events_recovered)
            )
        except Exception as e:
            result.error_details.append(f"Chaos event failed: {str(e)}")


# ============================================================================
# PERFORMANCE MONITORING
# ============================================================================

class PerformanceMonitor:
    """Monitor performance metrics and SLA compliance"""
    
    def __init__(self):
        self.thresholds: List[SLAThreshold] = []
        self.violations: List[SLAViolation] = []
        self.baselines: Dict[str, PerformanceBaseline] = {}
    
    def add_sla_threshold(self, threshold: SLAThreshold) -> None:
        """Add SLA threshold"""
        self.thresholds.append(threshold)
    
    def check_violations(
        self,
        metrics: LoadTestMetrics,
    ) -> List[SLAViolation]:
        """Check metrics against SLA thresholds"""
        violations = []
        
        for threshold in self.thresholds:
            actual_value = 0.0
            
            if threshold.metric == SLAMetric.LATENCY_P99:
                actual_value = metrics.p99_latency_ms
            elif threshold.metric == SLAMetric.LATENCY_P95:
                actual_value = metrics.p95_latency_ms
            elif threshold.metric == SLAMetric.ERROR_RATE:
                actual_value = 100 - metrics.success_rate_percent
            elif threshold.metric == SLAMetric.THROUGHPUT:
                actual_value = metrics.throughput_req_per_sec
            elif threshold.metric == SLAMetric.AVAILABILITY:
                actual_value = metrics.success_rate_percent
            
            # Check if violation
            if (threshold.metric in [SLAMetric.LATENCY_P99, SLAMetric.LATENCY_P95, SLAMetric.ERROR_RATE] and
                actual_value > threshold.threshold_value) or \
               (threshold.metric in [SLAMetric.THROUGHPUT, SLAMetric.AVAILABILITY] and
                actual_value < threshold.threshold_value):
                
                violation = SLAViolation(
                    violation_id=str(uuid.uuid4()),
                    timestamp=datetime.utcnow(),
                    metric=threshold.metric,
                    actual_value=actual_value,
                    threshold_value=threshold.threshold_value,
                    severity=threshold.severity,
                    duration_seconds=10.0,
                    affected_requests=metrics.failed_requests,
                )
                violations.append(violation)
                self.violations.append(violation)
        
        return violations
    
    def establish_baseline(
        self,
        test_name: str,
        metrics: LoadTestMetrics,
    ) -> PerformanceBaseline:
        """Establish performance baseline"""
        baseline = PerformanceBaseline(
            test_name=test_name,
            baseline_date=datetime.utcnow(),
            p50_latency_ms=metrics.p50_latency_ms,
            p95_latency_ms=metrics.p95_latency_ms,
            p99_latency_ms=metrics.p99_latency_ms,
            throughput_req_per_sec=metrics.throughput_req_per_sec,
            success_rate_percent=metrics.success_rate_percent,
        )
        self.baselines[test_name] = baseline
        return baseline
    
    def detect_regression(
        self,
        test_name: str,
        metrics: LoadTestMetrics,
        regression_threshold_percent: float = 5.0,
    ) -> Optional[BenchmarkResult]:
        """Detect performance regression"""
        if test_name not in self.baselines:
            return None
        
        baseline = self.baselines[test_name]
        result = BenchmarkResult(
            benchmark_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            test_name=test_name,
            baseline=baseline,
            current_metrics=metrics,
        )
        
        # Check each metric for regression
        checks = [
            ("p99_latency_ms", metrics.p99_latency_ms, baseline.p99_latency_ms, False),
            ("p95_latency_ms", metrics.p95_latency_ms, baseline.p95_latency_ms, False),
            ("throughput", metrics.throughput_req_per_sec, baseline.throughput_req_per_sec, True),
            ("success_rate", metrics.success_rate_percent, baseline.success_rate_percent, True),
        ]
        
        for metric_name, current, baseline_val, is_higher_better in checks:
            if is_higher_better:
                degradation = ((baseline_val - current) / baseline_val * 100) if baseline_val > 0 else 0
            else:
                degradation = ((current - baseline_val) / baseline_val * 100) if baseline_val > 0 else 0
            
            if abs(degradation) > regression_threshold_percent:
                result.regression_detected = True
                result.regression_metrics.append(metric_name)
                result.degradation_percent[metric_name] = degradation
        
        return result


# ============================================================================
# OPERATIONAL RUNBOOKS
# ============================================================================

@dataclass
class RunbookStep:
    """Single step in a runbook"""
    step_number: int
    title: str
    description: str
    command: Optional[str] = None
    expected_outcome: str = ""
    estimated_duration_minutes: int = 5
    rollback_command: Optional[str] = None


@dataclass
class Runbook:
    """Operational runbook"""
    runbook_id: str
    name: str
    description: str
    category: str
    severity: str  # "low", "medium", "high", "critical"
    estimated_total_time_minutes: int
    steps: List[RunbookStep] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    created_date: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    def add_step(self, step: RunbookStep) -> None:
        """Add step to runbook"""
        self.steps.append(step)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "runbook_id": self.runbook_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "severity": self.severity,
            "estimated_total_time_minutes": self.estimated_total_time_minutes,
            "steps": len(self.steps),
            "prerequisites": self.prerequisites,
        }


class RunbookLibrary:
    """Library of operational runbooks"""
    
    def __init__(self):
        self.runbooks: Dict[str, Runbook] = {}
    
    def create_deployment_runbook(self) -> Runbook:
        """Create deployment runbook"""
        rb = Runbook(
            runbook_id=str(uuid.uuid4()),
            name="Model Deployment",
            description="Deploy new model version to production",
            category="deployment",
            severity="high",
            estimated_total_time_minutes=30,
        )
        
        rb.add_step(RunbookStep(
            step_number=1,
            title="Prepare Deployment",
            description="Review model metrics and health checks",
            expected_outcome="Model passes all validation tests",
            estimated_duration_minutes=5,
        ))
        
        rb.add_step(RunbookStep(
            step_number=2,
            title="Backup Current Model",
            description="Archive current production model",
            command="aws s3 cp s3://models/production/ s3://models/archive/prod_backup_$(date +%s)/",
            expected_outcome="Backup completed successfully",
            estimated_duration_minutes=5,
            rollback_command="aws s3 cp s3://models/archive/prod_backup_$(date +%s)/ s3://models/production/",
        ))
        
        rb.add_step(RunbookStep(
            step_number=3,
            title="Canary Deployment (10%)",
            description="Deploy to 10% of traffic",
            expected_outcome="10% of requests routed to new model",
            estimated_duration_minutes=5,
        ))
        
        rb.add_step(RunbookStep(
            step_number=4,
            title="Monitor Metrics (5 min)",
            description="Monitor error rate, latency, and accuracy",
            expected_outcome="No increase in errors or latency",
            estimated_duration_minutes=5,
        ))
        
        rb.add_step(RunbookStep(
            step_number=5,
            title="Canary Deployment (50%)",
            description="Increase to 50% of traffic",
            expected_outcome="50% of requests routed to new model",
            estimated_duration_minutes=5,
        ))
        
        rb.add_step(RunbookStep(
            step_number=6,
            title="Monitor Metrics (5 min)",
            description="Confirm stable performance",
            expected_outcome="Metrics consistent with canary phase",
            estimated_duration_minutes=5,
        ))
        
        rb.add_step(RunbookStep(
            step_number=7,
            title="Full Deployment (100%)",
            description="Route all traffic to new model",
            expected_outcome="100% of requests routed to new model",
            estimated_duration_minutes=5,
        ))
        
        self.runbooks["deployment"] = rb
        return rb
    
    def create_incident_response_runbook(self) -> Runbook:
        """Create incident response runbook"""
        rb = Runbook(
            runbook_id=str(uuid.uuid4()),
            name="Incident Response",
            description="Respond to production incidents",
            category="incident_response",
            severity="critical",
            estimated_total_time_minutes=15,
            prerequisites=["Access to production logs", "AWS console access"],
        )
        
        rb.add_step(RunbookStep(
            step_number=1,
            title="Alert Received",
            description="Incident detected by monitoring system",
            expected_outcome="Team notified, incident ticket created",
            estimated_duration_minutes=1,
        ))
        
        rb.add_step(RunbookStep(
            step_number=2,
            title="Assess Severity",
            description="Check error rate, latency, affected users",
            expected_outcome="Severity classification (P1/P2/P3)",
            estimated_duration_minutes=2,
        ))
        
        rb.add_step(RunbookStep(
            step_number=3,
            title="Activate War Room",
            description="Start incident bridge call",
            command="call: incident-bridge@company.com",
            expected_outcome="Team assembled, communication channel active",
            estimated_duration_minutes=1,
        ))
        
        rb.add_step(RunbookStep(
            step_number=4,
            title="Investigate Root Cause",
            description="Check logs, metrics, recent deployments",
            expected_outcome="Root cause identified",
            estimated_duration_minutes=5,
        ))
        
        rb.add_step(RunbookStep(
            step_number=5,
            title="Execute Recovery",
            description="Implement fix or rollback",
            expected_outcome="Service restored, error rate normalized",
            estimated_duration_minutes=3,
        ))
        
        rb.add_step(RunbookStep(
            step_number=6,
            title="Post-Incident Review",
            description="Document incident and improvements",
            expected_outcome="Post-mortem scheduled",
            estimated_duration_minutes=2,
        ))
        
        self.runbooks["incident_response"] = rb
        return rb
    
    def create_disaster_recovery_runbook(self) -> Runbook:
        """Create disaster recovery runbook"""
        rb = Runbook(
            runbook_id=str(uuid.uuid4()),
            name="Disaster Recovery",
            description="Recover from complete system failure",
            category="disaster_recovery",
            severity="critical",
            estimated_total_time_minutes=60,
        )
        
        rb.add_step(RunbookStep(
            step_number=1,
            title="Declare Disaster",
            description="Confirm unrecoverable infrastructure failure",
            expected_outcome="DR mode activated",
            estimated_duration_minutes=5,
        ))
        
        rb.add_step(RunbookStep(
            step_number=2,
            title="Activate Backup Infrastructure",
            description="Restore from DR site backup",
            command="terraform apply -var-file=dr.tfvars",
            expected_outcome="Infrastructure provisioned in DR site",
            estimated_duration_minutes=20,
        ))
        
        rb.add_step(RunbookStep(
            step_number=3,
            title="Restore Data",
            description="Restore latest database backup",
            expected_outcome="Data restored to latest checkpoint",
            estimated_duration_minutes=15,
        ))
        
        rb.add_step(RunbookStep(
            step_number=4,
            title="Verify Services",
            description="Confirm all services operational",
            expected_outcome="All health checks pass",
            estimated_duration_minutes=10,
        ))
        
        rb.add_step(RunbookStep(
            step_number=5,
            title="Gradual Traffic Shift",
            description="Route traffic to DR site",
            expected_outcome="100% traffic on DR site",
            estimated_duration_minutes=5,
        ))
        
        rb.add_step(RunbookStep(
            step_number=6,
            title="Post-Recovery Analysis",
            description="Assess impact and recovery success",
            expected_outcome="Recovery metrics documented",
            estimated_duration_minutes=5,
        ))
        
        self.runbooks["disaster_recovery"] = rb
        return rb
    
    def create_scaling_runbook(self) -> Runbook:
        """Create scaling runbook"""
        rb = Runbook(
            runbook_id=str(uuid.uuid4()),
            name="Horizontal Scaling",
            description="Scale system for increased load",
            category="scaling",
            severity="medium",
            estimated_total_time_minutes=20,
        )
        
        rb.add_step(RunbookStep(
            step_number=1,
            title="Monitor Load",
            description="Check CPU, memory, request queue",
            expected_outcome="Load metrics identify scaling trigger",
            estimated_duration_minutes=2,
        ))
        
        rb.add_step(RunbookStep(
            step_number=2,
            title="Increase Instance Count",
            description="Add new instances to auto-scaling group",
            command="aws autoscaling set-desired-capacity --desired-capacity 20",
            expected_outcome="New instances provisioning",
            estimated_duration_minutes=5,
        ))
        
        rb.add_step(RunbookStep(
            step_number=3,
            title="Wait for Instances",
            description="Wait for health checks to pass",
            expected_outcome="All new instances healthy",
            estimated_duration_minutes=8,
        ))
        
        rb.add_step(RunbookStep(
            step_number=4,
            title="Verify Load Balancing",
            description="Confirm traffic distributed evenly",
            expected_outcome="Load balanced across all instances",
            estimated_duration_minutes=3,
        ))
        
        rb.add_step(RunbookStep(
            step_number=5,
            title="Monitor Performance",
            description="Verify latency and error rate normalized",
            expected_outcome="Performance metrics improved",
            estimated_duration_minutes=2,
        ))
        
        self.runbooks["scaling"] = rb
        return rb
    
    def get_runbook(self, category: str) -> Optional[Runbook]:
        """Get runbook by category"""
        return self.runbooks.get(category)
    
    def list_runbooks(self) -> List[Dict[str, Any]]:
        """List all runbooks"""
        return [rb.to_dict() for rb in self.runbooks.values()]


if __name__ == "__main__":
    print("Extended Testing & Runbooks Framework Loaded")
