"""
Tests for Advanced Health Monitoring (Enhancement #1)

Tests all functionality of the health monitoring system including:
- Service health checks
- Resource metrics collection
- Connection pool tracking
- Cache metrics
- Endpoint latency monitoring
- SLA tracking
- Dependency graphs
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from src.infrastructure.health_monitor_extended import (
    AdvancedHealthMonitor,
    HealthStatus,
    ServiceName,
    ServiceHealth,
    ResourceMetrics,
    LatencyMetrics,
    ConnectionPoolHealth,
    CacheMetrics,
    HealthReport,
    check_database_health,
    check_cache_health,
    check_api_health,
)


class TestLatencyMetrics:
    """Test latency metrics tracking"""
    
    def test_latency_metrics_creation(self):
        """Test creating latency metrics"""
        metrics = LatencyMetrics(endpoint="/api/test")
        
        assert metrics.endpoint == "/api/test"
        assert metrics.p50 == 0.0
        assert metrics.p95 == 0.0
        assert metrics.p99 == 0.0
        assert metrics.samples == 0
    
    def test_latency_metrics_update(self):
        """Test updating latency metrics"""
        metrics = LatencyMetrics(endpoint="/api/test")
        
        metrics.update(50.0)
        assert metrics.samples == 1
        assert metrics.min_ms == 50.0
        assert metrics.max_ms == 50.0
        
        metrics.update(100.0)
        assert metrics.samples == 2
        assert metrics.min_ms == 50.0
        assert metrics.max_ms == 100.0
        
        metrics.update(25.0)
        assert metrics.samples == 3
        assert metrics.min_ms == 25.0
        assert metrics.max_ms == 100.0
    
    def test_latency_metrics_to_dict(self):
        """Test converting latency metrics to dict"""
        metrics = LatencyMetrics(endpoint="/api/test")
        metrics.update(50.0)
        
        d = metrics.to_dict()
        assert d["endpoint"] == "/api/test"
        assert d["samples"] == 1
        assert d["min_ms"] == 50.0
        assert d["max_ms"] == 50.0


class TestServiceHealth:
    """Test service health tracking"""
    
    def test_service_health_creation(self):
        """Test creating service health"""
        health = ServiceHealth(name=ServiceName.DATABASE)
        
        assert health.name == ServiceName.DATABASE
        assert health.status == HealthStatus.UNKNOWN
        assert health.error_count == 0
    
    def test_service_health_status_change(self):
        """Test changing service health status"""
        health = ServiceHealth(name=ServiceName.DATABASE)
        
        health.status = HealthStatus.HEALTHY
        health.message = "All systems go"
        
        assert health.status == HealthStatus.HEALTHY
        assert health.message == "All systems go"
    
    def test_service_health_error_tracking(self):
        """Test tracking errors in service health"""
        health = ServiceHealth(name=ServiceName.API)
        
        health.error_count = 1
        health.last_error = "Connection timeout"
        
        assert health.error_count == 1
        assert health.last_error == "Connection timeout"
    
    def test_service_health_to_dict(self):
        """Test converting service health to dict"""
        health = ServiceHealth(
            name=ServiceName.DATABASE,
            status=HealthStatus.HEALTHY,
            message="OK"
        )
        
        d = health.to_dict()
        assert d["name"] == "database"
        assert d["status"] == "HEALTHY"
        assert d["message"] == "OK"


class TestConnectionPoolHealth:
    """Test connection pool health tracking"""
    
    def test_pool_creation(self):
        """Test creating connection pool health"""
        pool = ConnectionPoolHealth(
            pool_name="postgres_main",
            max_connections=100
        )
        
        assert pool.pool_name == "postgres_main"
        assert pool.max_connections == 100
        assert pool.active_connections == 0
    
    def test_pool_utilization_calculation(self):
        """Test calculating pool utilization"""
        pool = ConnectionPoolHealth(
            pool_name="postgres_main",
            max_connections=100
        )
        
        pool.active_connections = 0
        assert pool.utilization_percent() == 0.0
        
        pool.active_connections = 50
        assert pool.utilization_percent() == 50.0
        
        pool.active_connections = 100
        assert pool.utilization_percent() == 100.0
    
    def test_pool_to_dict(self):
        """Test converting pool to dict"""
        pool = ConnectionPoolHealth(
            pool_name="postgres_main",
            max_connections=100,
            active_connections=25,
            idle_connections=75
        )
        
        d = pool.to_dict()
        assert d["pool_name"] == "postgres_main"
        assert d["active_connections"] == 25
        assert d["utilization_percent"] == 25.0


class TestCacheMetrics:
    """Test cache metrics tracking"""
    
    def test_cache_creation(self):
        """Test creating cache metrics"""
        cache = CacheMetrics(
            cache_name="redis_main",
            max_memory_mb=1024.0
        )
        
        assert cache.cache_name == "redis_main"
        assert cache.max_memory_mb == 1024.0
        assert cache.hits == 0
        assert cache.misses == 0
    
    def test_cache_hit_rate_calculation(self):
        """Test calculating cache hit rate"""
        cache = CacheMetrics(cache_name="redis_main")
        
        cache.hits = 0
        cache.misses = 0
        assert cache.hit_rate() == 0.0
        
        cache.hits = 100
        cache.misses = 0
        assert cache.hit_rate() == 100.0
        
        cache.hits = 75
        cache.misses = 25
        assert cache.hit_rate() == 75.0
    
    def test_cache_memory_utilization(self):
        """Test calculating cache memory utilization"""
        cache = CacheMetrics(
            cache_name="redis_main",
            max_memory_mb=1000.0,
            memory_used_mb=500.0
        )
        
        assert cache.memory_utilization() == 50.0
    
    def test_cache_to_dict(self):
        """Test converting cache metrics to dict"""
        cache = CacheMetrics(
            cache_name="redis_main",
            hits=100,
            misses=50,
            memory_used_mb=512.0,
            max_memory_mb=1024.0
        )
        
        d = cache.to_dict()
        assert d["cache_name"] == "redis_main"
        assert d["hits"] == 100
        assert d["hit_rate"] == 66.66666666666666


class TestResourceMetrics:
    """Test system resource metrics"""
    
    def test_resource_metrics_creation(self):
        """Test creating resource metrics"""
        metrics = ResourceMetrics()
        
        assert metrics.timestamp is not None
        # Just check that it's a datetime
        assert isinstance(metrics.timestamp, datetime)
    
    def test_resource_metrics_values_exist(self):
        """Test resource metrics have expected attributes"""
        metrics = ResourceMetrics()
        
        # Just verify attributes exist (not testing system-specific values)
        assert hasattr(metrics, 'cpu_percent')
        assert hasattr(metrics, 'memory_percent')
        assert hasattr(metrics, 'disk_percent')
        assert hasattr(metrics, 'cpu_cores')
    
    def test_resource_metrics_to_dict(self):
        """Test converting resource metrics to dict"""
        metrics = ResourceMetrics()
        d = metrics.to_dict()
        
        assert "cpu_percent" in d
        assert "memory_percent" in d
        assert "disk_percent" in d
        assert isinstance(d, dict)


class TestAdvancedHealthMonitor:
    """Test advanced health monitor"""
    
    def test_monitor_creation(self):
        """Test creating health monitor"""
        monitor = AdvancedHealthMonitor()
        
        assert monitor.check_interval == 60
        assert monitor.sla_target == 99.9
        assert len(monitor.services) == len(ServiceName)
    
    def test_monitor_with_checks(self):
        """Test monitor with service checks"""
        async def always_healthy():
            return HealthStatus.HEALTHY, "OK"
        
        # Only check critical services
        checks = {
            ServiceName.DATABASE: always_healthy,
            ServiceName.API: always_healthy,
        }
        
        monitor = AdvancedHealthMonitor(service_checks=checks)
        
        # Run checks synchronously for testing
        loop = asyncio.new_event_loop()
        try:
            report = loop.run_until_complete(monitor.run_checks())
            # Services with checks should be healthy
            assert report.services[ServiceName.DATABASE].status == HealthStatus.HEALTHY
            assert report.services[ServiceName.API].status == HealthStatus.HEALTHY
        finally:
            loop.close()
    
    def test_monitor_with_failing_check(self):
        """Test monitor with failing health check"""
        async def always_fails():
            return HealthStatus.CRITICAL, "Connection error"
        
        checks = {
            ServiceName.DATABASE: always_fails,
        }
        
        monitor = AdvancedHealthMonitor(service_checks=checks)
        
        loop = asyncio.new_event_loop()
        try:
            report = loop.run_until_complete(monitor.run_checks())
            assert report.overall_status == HealthStatus.CRITICAL
            assert report.services[ServiceName.DATABASE].status == HealthStatus.CRITICAL
        finally:
            loop.close()
    
    def test_monitor_endpoint_latency(self):
        """Test recording endpoint latency"""
        monitor = AdvancedHealthMonitor()
        
        monitor.record_endpoint_latency("/api/status", 50.0)
        monitor.record_endpoint_latency("/api/status", 75.0)
        monitor.record_endpoint_latency("/api/status", 100.0)
        
        assert "/api/status" in monitor.latencies
        metrics = monitor.latencies["/api/status"]
        assert metrics.samples == 3
        assert metrics.min_ms == 50.0
        assert metrics.max_ms == 100.0
    
    def test_monitor_connection_pool_registration(self):
        """Test registering connection pool"""
        monitor = AdvancedHealthMonitor()
        
        pool = monitor.register_connection_pool("postgres_main", max_connections=100)
        
        assert "postgres_main" in monitor.connection_pools
        assert pool.max_connections == 100
    
    def test_monitor_cache_registration(self):
        """Test registering cache"""
        monitor = AdvancedHealthMonitor()
        
        cache = monitor.register_cache("redis_main", max_memory_mb=1024.0)
        
        assert "redis_main" in monitor.caches
        assert cache.max_memory_mb == 1024.0
    
    def test_monitor_dependencies(self):
        """Test adding service dependencies"""
        monitor = AdvancedHealthMonitor()
        
        monitor.add_service_dependency("api", "database")
        monitor.add_service_dependency("api", "cache")
        
        assert "database" in monitor.dependency_graph["api"]
        assert "cache" in monitor.dependency_graph["api"]
    
    def test_monitor_sla_calculation(self):
        """Test SLA calculation"""
        async def always_healthy():
            return HealthStatus.HEALTHY, "OK"
        
        checks = {ServiceName.DATABASE: always_healthy}
        monitor = AdvancedHealthMonitor(service_checks=checks)
        
        loop = asyncio.new_event_loop()
        try:
            # Run checks multiple times
            for i in range(5):
                report = loop.run_until_complete(monitor.run_checks())
                # Check that the service we're monitoring is healthy
                assert report.services[ServiceName.DATABASE].status == HealthStatus.HEALTHY
            
            # Monitor recorded at least 5 checks
            assert monitor.check_count >= 5
        finally:
            loop.close()
    
    def test_monitor_resource_collection(self):
        """Test collecting resource metrics"""
        monitor = AdvancedHealthMonitor()
        
        loop = asyncio.new_event_loop()
        try:
            report = loop.run_until_complete(monitor.run_checks())
            
            assert report.resources is not None
            assert report.resources.cpu_percent >= 0.0
            assert report.resources.memory_percent >= 0.0
            assert report.resources.disk_percent >= 0.0
        finally:
            loop.close()


class TestHealthReport:
    """Test health report generation"""
    
    def test_report_generation(self):
        """Test generating health report"""
        async def healthy_check():
            return HealthStatus.HEALTHY, "OK"
        
        checks = {ServiceName.DATABASE: healthy_check}
        monitor = AdvancedHealthMonitor(service_checks=checks)
        
        loop = asyncio.new_event_loop()
        try:
            report = loop.run_until_complete(monitor.run_checks())
            
            assert report is not None
            assert report.timestamp is not None
            assert report.overall_status is not None
            assert len(report.services) > 0
            assert report.resources is not None
        finally:
            loop.close()
    
    def test_report_to_dict(self):
        """Test converting report to dict"""
        report = HealthReport()
        report.overall_status = HealthStatus.HEALTHY
        report.sla_uptime_percent = 99.9
        
        d = report.to_dict()
        
        assert d["overall_status"] == "HEALTHY"
        assert d["sla_uptime_percent"] == 99.9
        assert "services" in d
        assert "resources" in d


class TestHealthCheckFunctions:
    """Test built-in health check functions"""
    
    def test_database_check(self):
        """Test database health check"""
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(check_database_health())
            
            assert isinstance(result, tuple)
            assert len(result) == 2
            assert result[0] == HealthStatus.HEALTHY
        finally:
            loop.close()
    
    def test_cache_check(self):
        """Test cache health check"""
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(check_cache_health())
            
            assert isinstance(result, tuple)
            assert len(result) == 2
            assert result[0] == HealthStatus.HEALTHY
        finally:
            loop.close()
    
    def test_api_check(self):
        """Test API health check"""
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(check_api_health())
            
            assert isinstance(result, bool)
            assert result is True
        finally:
            loop.close()


class TestHealthMonitorIntegration:
    """Integration tests for health monitor"""
    
    def test_full_health_monitoring_workflow(self):
        """Test complete health monitoring workflow"""
        async def db_check():
            return HealthStatus.HEALTHY, "Database OK"
        
        async def cache_check():
            return HealthStatus.HEALTHY, "Cache OK"
        
        checks = {
            ServiceName.DATABASE: db_check,
            ServiceName.CACHE: cache_check,
        }
        
        monitor = AdvancedHealthMonitor(
            service_checks=checks,
            check_interval_seconds=1,
            sla_target_uptime=99.9,
            latency_p99_threshold_ms=500.0
        )
        
        # Register pools and caches
        monitor.register_connection_pool("postgres_main", max_connections=100)
        monitor.register_cache("redis_main", max_memory_mb=1024.0)
        
        # Record some latencies
        for latency in [50.0, 75.0, 100.0, 125.0, 150.0]:
            monitor.record_endpoint_latency("/api/status", latency)
        
        loop = asyncio.new_event_loop()
        try:
            # Run health check
            report = loop.run_until_complete(monitor.run_checks())
            
            # Verify results
            assert len(report.services) > 0
            assert report.resources is not None
            assert len(report.connection_pools) > 0
            assert len(report.caches) > 0
            assert len(report.endpoint_latencies) > 0
            # Verify our checked services are healthy
            assert report.services[ServiceName.DATABASE].status == HealthStatus.HEALTHY
            assert report.services[ServiceName.CACHE].status == HealthStatus.HEALTHY
        finally:
            loop.close()
    
    def test_degraded_status_detection(self):
        """Test detecting degraded system status"""
        async def db_check():
            return HealthStatus.HEALTHY, "Database OK"
        
        async def cache_check():
            return HealthStatus.DEGRADED, "Cache slow"
        
        checks = {
            ServiceName.DATABASE: db_check,
            ServiceName.CACHE: cache_check,
        }
        
        monitor = AdvancedHealthMonitor(service_checks=checks)
        
        loop = asyncio.new_event_loop()
        try:
            report = loop.run_until_complete(monitor.run_checks())
            
            # Should be degraded, not healthy or critical
            assert report.overall_status == HealthStatus.DEGRADED
        finally:
            loop.close()
    
    def test_critical_status_detection(self):
        """Test detecting critical system status"""
        async def db_check():
            return HealthStatus.CRITICAL, "Database down"
        
        async def cache_check():
            return HealthStatus.HEALTHY, "Cache OK"
        
        checks = {
            ServiceName.DATABASE: db_check,
            ServiceName.CACHE: cache_check,
        }
        
        monitor = AdvancedHealthMonitor(service_checks=checks)
        
        loop = asyncio.new_event_loop()
        try:
            report = loop.run_until_complete(monitor.run_checks())
            
            assert report.overall_status == HealthStatus.CRITICAL
        finally:
            loop.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
