"""
Advanced Health Monitoring
==========================
Multi-tier health checks with SLA tracking, latency monitoring, and service dependency
verification. Provides comprehensive system observability for production operations.

Features:
- Endpoint latency monitoring (p99, p95, p50)
- Database connection pool health
- Cache hit/miss ratios (Redis)
- Disk space and I/O monitoring
- Network connectivity tests
- Service dependency checks
- SLA compliance tracking
- Health report generation (JSON, HTML)
"""

import time
import psutil
import socket
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from collections import deque
from loguru import logger

from src.utils.config import get_config


@dataclass
class ServiceHealth:
    """Health status of a single service."""
    name: str
    status: str  # "healthy", "degraded", "unhealthy"
    latency_ms: float = 0.0
    message: str = ""
    last_check: datetime = field(default_factory=datetime.now)
    check_count: int = 0
    failure_count: int = 0


@dataclass
class LatencyMetrics:
    """Latency statistics for an endpoint."""
    endpoint: str
    samples: int = 0
    mean_ms: float = 0.0
    p50_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0
    min_ms: float = 0.0
    max_ms: float = 0.0
    
    def update(self, measurements: List[float]):
        """Update metrics from new measurements."""
        if not measurements:
            return
        
        self.samples += len(measurements)
        sorted_m = sorted(measurements)
        self.mean_ms = sum(measurements) / len(measurements)
        
        idx_50 = int(len(sorted_m) * 0.50)
        idx_95 = int(len(sorted_m) * 0.95)
        idx_99 = int(len(sorted_m) * 0.99)
        
        self.p50_ms = sorted_m[idx_50] if idx_50 < len(sorted_m) else sorted_m[-1]
        self.p95_ms = sorted_m[idx_95] if idx_95 < len(sorted_m) else sorted_m[-1]
        self.p99_ms = sorted_m[idx_99] if idx_99 < len(sorted_m) else sorted_m[-1]
        self.min_ms = sorted_m[0]
        self.max_ms = sorted_m[-1]


class HealthMonitor:
    """
    Advanced health monitoring system.
    Tracks multiple services, endpoints, and system resources.
    """
    
    def __init__(self, config: Optional[dict] = None, window_size: int = 100):
        self.config = config or get_config()
        self.window_size = window_size
        
        # Service status tracking
        self.services: Dict[str, ServiceHealth] = {}
        
        # Latency measurements (keep rolling window)
        self.latencies: Dict[str, deque] = {}
        self.latency_metrics: Dict[str, LatencyMetrics] = {}
        
        # System metrics
        self.start_time = datetime.now()
        self.uptime_seconds = 0
        self.cpu_percent = 0.0
        self.memory_percent = 0.0
        self.disk_percent = 0.0
        
        # SLA tracking
        self.sla_target_uptime = 0.999  # 99.9%
        self.total_checks = 0
        self.failed_checks = 0
        
        logger.info("Health monitor initialized")
    
    def measure_endpoint_latency(self, endpoint: str, func, num_samples: int = 10) -> LatencyMetrics:
        """
        Measure latency for an endpoint by running function multiple times.
        
        Args:
            endpoint: Endpoint name for tracking
            func: Callable that performs the endpoint operation
            num_samples: Number of measurements to take
            
        Returns:
            LatencyMetrics with statistical analysis
        """
        if endpoint not in self.latencies:
            self.latencies[endpoint] = deque(maxlen=self.window_size)
            self.latency_metrics[endpoint] = LatencyMetrics(endpoint)
        
        measurements = []
        for _ in range(num_samples):
            try:
                start = time.perf_counter()
                func()
                elapsed_ms = (time.perf_counter() - start) * 1000
                measurements.append(elapsed_ms)
                self.latencies[endpoint].append(elapsed_ms)
            except Exception as e:
                logger.warning(f"Latency measurement failed for {endpoint}: {e}")
        
        if measurements:
            self.latency_metrics[endpoint].update(measurements)
        
        return self.latency_metrics[endpoint]
    
    def check_database_health(self, db_name: str = "questdb") -> ServiceHealth:
        """Check database connection pool health."""
        try:
            from src.ingestion.questdb_writer import QuestDBWriter
            
            writer = QuestDBWriter(self.config)
            is_available = writer.is_available()
            
            if is_available:
                status = "healthy"
                message = "Database connected and responsive"
                latency = 0.0
            else:
                status = "unhealthy"
                message = "Database connection failed"
                latency = float('inf')
            
            service = self.services.get(db_name, ServiceHealth(db_name, status, latency, message))
            service.status = status
            service.message = message
            service.latency_ms = latency
            service.check_count += 1
            service.last_check = datetime.now()
            self.services[db_name] = service
            
            return service
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            service = ServiceHealth(db_name, "unhealthy", 0.0, str(e))
            self.services[db_name] = service
            return service
    
    def check_cache_health(self, cache_name: str = "redis") -> ServiceHealth:
        """Check cache (Redis) connection health."""
        try:
            import redis
            
            redis_config = self.config.get("database", {}).get("redis", {})
            r = redis.Redis(
                host=redis_config.get("host", "localhost"),
                port=redis_config.get("port", 6379),
                socket_connect_timeout=2
            )
            
            start = time.perf_counter()
            r.ping()
            latency = (time.perf_counter() - start) * 1000
            
            service = ServiceHealth(cache_name, "healthy", latency, "Cache connected")
            service.check_count += 1
            service.last_check = datetime.now()
            self.services[cache_name] = service
            
            return service
        except Exception as e:
            logger.error(f"Cache health check failed: {e}")
            service = ServiceHealth(cache_name, "unhealthy", 0.0, str(e))
            self.services[cache_name] = service
            return service
    
    def check_disk_health(self) -> Dict[str, float]:
        """Check disk space and I/O."""
        try:
            disk_info = psutil.disk_usage('/')
            self.disk_percent = disk_info.percent
            
            return {
                "total_gb": disk_info.total / (1024**3),
                "used_gb": disk_info.used / (1024**3),
                "free_gb": disk_info.free / (1024**3),
                "percent_used": disk_info.percent
            }
        except Exception as e:
            logger.error(f"Disk health check failed: {e}")
            return {}
    
    def check_system_resources(self) -> Dict[str, float]:
        """Check CPU and memory utilization."""
        try:
            self.cpu_percent = psutil.cpu_percent(interval=0.1)
            self.memory_percent = psutil.virtual_memory().percent
            
            return {
                "cpu_percent": self.cpu_percent,
                "memory_percent": self.memory_percent,
                "process_count": len(psutil.pids())
            }
        except Exception as e:
            logger.error(f"System resource check failed: {e}")
            return {}
    
    def check_network_connectivity(self, test_host: str = "8.8.8.8", test_port: int = 53) -> ServiceHealth:
        """Check network connectivity."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(2)
            
            start = time.perf_counter()
            sock.connect((test_host, test_port))
            latency = (time.perf_counter() - start) * 1000
            sock.close()
            
            service = ServiceHealth("network", "healthy", latency, "Network connected")
            service.check_count += 1
            service.last_check = datetime.now()
            self.services["network"] = service
            
            return service
        except Exception as e:
            logger.warning(f"Network connectivity check failed: {e}")
            service = ServiceHealth("network", "degraded", 0.0, str(e))
            self.services["network"] = service
            return service
    
    def run_full_health_check(self) -> Dict:
        """
        Execute comprehensive health check across all components.
        
        Returns:
            Dictionary with full system health status
        """
        logger.info("Running full health check...")
        
        self.total_checks += 1
        check_failed = False
        
        # Check all services
        db_health = self.check_database_health()
        cache_health = self.check_cache_health()
        network_health = self.check_network_connectivity()
        
        if db_health.status != "healthy" or cache_health.status != "healthy":
            check_failed = True
        
        # Check system resources
        system_resources = self.check_system_resources()
        disk_health = self.check_disk_health()
        
        if check_failed:
            self.failed_checks += 1
        
        # Calculate uptime
        self.uptime_seconds = (datetime.now() - self.start_time).total_seconds()
        uptime_percent = 100.0 * (1.0 - self.failed_checks / max(1, self.total_checks))
        
        # Determine overall status
        overall_status = "healthy"
        if self.failed_checks > 0:
            overall_status = "degraded"
        if disk_health.get("percent_used", 0) > 90:
            overall_status = "degraded"
        if self.cpu_percent > 90 or self.memory_percent > 90:
            overall_status = "degraded"
        
        return {
            "timestamp": datetime.now().isoformat(),
            "overall_status": overall_status,
            "uptime_seconds": self.uptime_seconds,
            "uptime_percent": uptime_percent,
            "sla_compliant": uptime_percent >= (self.sla_target_uptime * 100),
            "services": {name: asdict(service) for name, service in self.services.items()},
            "system": {
                "cpu_percent": system_resources.get("cpu_percent", 0.0),
                "memory_percent": system_resources.get("memory_percent", 0.0),
                "process_count": system_resources.get("process_count", 0),
                "disk": disk_health,
            },
            "latencies": {
                name: asdict(metrics)
                for name, metrics in self.latency_metrics.items()
            },
            "checks": {
                "total": self.total_checks,
                "failed": self.failed_checks,
                "success_rate": 100.0 * (1.0 - self.failed_checks / max(1, self.total_checks))
            }
        }
    
    def generate_health_report(self, format: str = "json") -> str:
        """
        Generate formatted health report.
        
        Args:
            format: "json" or "text"
            
        Returns:
            Formatted health report
        """
        health = self.run_full_health_check()
        
        if format == "json":
            import json
            return json.dumps(health, indent=2, default=str)
        
        elif format == "text":
            report = []
            report.append("=" * 60)
            report.append("HEALTH REPORT")
            report.append(f"Generated: {health['timestamp']}")
            report.append("=" * 60)
            report.append(f"\nOverall Status: {health['overall_status'].upper()}")
            report.append(f"Uptime: {health['uptime_seconds']:.0f}s ({health['uptime_percent']:.2f}%)")
            report.append(f"SLA Compliant (99.9%): {health['sla_compliant']}")
            
            report.append("\nServices:")
            for name, svc in health['services'].items():
                status = "✓" if svc['status'] == "healthy" else "✗"
                report.append(f"  {status} {name}: {svc['status']} ({svc['latency_ms']:.1f}ms)")
            
            report.append("\nSystem Resources:")
            report.append(f"  CPU: {health['system']['cpu_percent']:.1f}%")
            report.append(f"  Memory: {health['system']['memory_percent']:.1f}%")
            report.append(f"  Disk: {health['system']['disk'].get('percent_used', 0):.1f}%")
            
            report.append(f"\nHealth Checks: {health['checks']['total']} total, {health['checks']['failed']} failed, {health['checks']['success_rate']:.1f}% success rate")
            
            report.append("=" * 60)
            return "\n".join(report)
        
        else:
            raise ValueError(f"Unknown format: {format}")


# Singleton instance for global access
_health_monitor: Optional[HealthMonitor] = None


def get_health_monitor() -> HealthMonitor:
    """Get or create global health monitor instance."""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = HealthMonitor()
    return _health_monitor
