"""
Tests for Enhancement #10: Logging & Observability

Test coverage:
- Structured JSON logging
- Log entry serialization
- Correlation ID tracking
- Distributed tracing
- Performance metrics
- Metrics collection
- Tracing decorator
- Error tracking
"""

import asyncio
import json
from datetime import datetime

import pytest

from src.infrastructure.logging_config import (
    LogLevel,
    LogEntry,
    TraceMetrics,
    StructuredLogger,
    TracingManager,
    traced,
    PerformanceTracker,
    MetricsCollector,
)


# ============================================================================
# Unit Tests: LogEntry
# ============================================================================

class TestLogEntry:
    """Test LogEntry functionality"""
    
    def test_log_entry_creation(self):
        """Test creating log entry"""
        entry = LogEntry(
            timestamp=datetime(2026, 5, 14, 10, 0, 0),
            level=LogLevel.INFO,
            component="trading_engine",
            message="Trade executed",
            correlation_id="corr_001",
        )
        
        assert entry.level == LogLevel.INFO
        assert entry.component == "trading_engine"
    
    def test_log_entry_with_error(self):
        """Test log entry with error"""
        entry = LogEntry(
            timestamp=datetime(2026, 5, 14, 10, 0, 0),
            level=LogLevel.ERROR,
            component="trading_engine",
            message="Trade failed",
            correlation_id="corr_001",
            error_type="TradeExecutionError",
            error_message="Insufficient funds",
        )
        
        assert entry.error_type == "TradeExecutionError"
        assert entry.error_message == "Insufficient funds"
    
    def test_log_entry_serialization(self):
        """Test log entry to_json_dict"""
        entry = LogEntry(
            timestamp=datetime(2026, 5, 14, 10, 0, 0),
            level=LogLevel.INFO,
            component="trading_engine",
            message="Trade executed",
            correlation_id="corr_001",
            tags={"env": "production"},
            data={"trade_id": "t_001", "pnl": 1250.50},
        )
        
        json_dict = entry.to_json_dict()
        assert json_dict["component"] == "trading_engine"
        assert json_dict["level"] == "INFO"
        assert json_dict["tags"]["env"] == "production"
        assert json_dict["data"]["trade_id"] == "t_001"


# ============================================================================
# Unit Tests: TraceMetrics
# ============================================================================

class TestTraceMetrics:
    """Test TraceMetrics functionality"""
    
    def test_trace_metrics_creation(self):
        """Test creating trace metrics"""
        metric = TraceMetrics(
            operation_name="trade_execution",
            duration_ms=1250.5,
            status="success",
        )
        
        assert metric.operation_name == "trade_execution"
        assert metric.duration_ms == 1250.5
        assert metric.status == "success"
    
    def test_trace_metrics_with_error(self):
        """Test trace metrics with error"""
        metric = TraceMetrics(
            operation_name="trade_execution",
            duration_ms=500.0,
            status="error",
            error_type="TradeExecutionError",
        )
        
        assert metric.status == "error"
        assert metric.error_type == "TradeExecutionError"


# ============================================================================
# Unit Tests: StructuredLogger
# ============================================================================

class TestStructuredLogger:
    """Test StructuredLogger functionality"""
    
    def test_logger_creation(self):
        """Test creating structured logger"""
        logger = StructuredLogger("trading_engine")
        assert logger.component == "trading_engine"
        assert logger.correlation_id
    
    def test_logger_info(self):
        """Test info logging"""
        logger = StructuredLogger("trading_engine")
        logger.info("Test message", data={"key": "value"})
        
        entries = logger.get_entries()
        assert len(entries) == 1
        assert entries[0].level == LogLevel.INFO
        assert entries[0].message == "Test message"
    
    def test_logger_error(self):
        """Test error logging"""
        logger = StructuredLogger("trading_engine")
        error = ValueError("Test error")
        logger.error("Error occurred", error=error)
        
        entries = logger.get_entries()
        assert len(entries) == 1
        assert entries[0].level == LogLevel.ERROR
        assert entries[0].error_type == "ValueError"
    
    def test_logger_debug(self):
        """Test debug logging"""
        logger = StructuredLogger("trading_engine", log_level=LogLevel.DEBUG)
        logger.debug("Debug message")
        
        entries = logger.get_entries()
        assert len(entries) == 1
        assert entries[0].level == LogLevel.DEBUG
    
    def test_logger_warning(self):
        """Test warning logging"""
        logger = StructuredLogger("trading_engine")
        logger.warning("Warning message")
        
        entries = logger.get_entries()
        assert len(entries) == 1
        assert entries[0].level == LogLevel.WARNING
    
    def test_logger_critical(self):
        """Test critical logging"""
        logger = StructuredLogger("trading_engine")
        logger.critical("Critical message")
        
        entries = logger.get_entries()
        assert len(entries) == 1
        assert entries[0].level == LogLevel.CRITICAL
    
    def test_logger_with_custom_output(self):
        """Test logger with custom output handler"""
        outputs = []
        
        def custom_handler(entry):
            outputs.append(entry)
        
        logger = StructuredLogger(
            "trading_engine",
            output_handler=custom_handler
        )
        logger.info("Test message")
        
        assert len(outputs) == 1
        assert outputs[0].message == "Test message"
    
    def test_logger_correlation_id_persistence(self):
        """Test correlation ID persists across logs"""
        logger1 = StructuredLogger("component_1")
        logger2 = StructuredLogger("component_2")
        
        logger1.info("Message 1")
        logger2.info("Message 2")
        
        entries1 = logger1.get_entries()
        entries2 = logger2.get_entries()
        
        # Correlation IDs should be the same if created in same context
        assert entries1[0].correlation_id == entries2[0].correlation_id


# ============================================================================
# Unit Tests: TracingManager
# ============================================================================

class TestTracingManager:
    """Test TracingManager functionality"""
    
    def test_tracing_manager_creation(self):
        """Test creating tracing manager"""
        manager = TracingManager("test_service")
        assert manager.service_name == "test_service"
    
    def test_trace_metric_recording(self):
        """Test recording trace metrics"""
        manager = TracingManager("test_service")
        
        metric = TraceMetrics(
            operation_name="test_op",
            duration_ms=100.0,
            status="success",
        )
        
        manager.record_metric(metric)
        metrics = manager.get_metrics()
        
        assert len(metrics) == 1
        assert metrics[0].operation_name == "test_op"
    
    def test_span_context_manager(self):
        """Test span context manager"""
        manager = TracingManager("test_service")
        
        # Should not raise error even if OTEL not available
        with manager.span("test_span", attributes={"key": "value"}) as span:
            assert span is not None


# ============================================================================
# Tests: Traced Decorator
# ============================================================================

class TestTracedDecorator:
    """Test traced decorator"""
    
    def test_traced_async_function(self):
        """Test traced decorator on async function"""
        loop = asyncio.new_event_loop()
        try:
            logger = StructuredLogger("test")
            
            @traced(logger)
            async def test_async_func():
                return "result"
            
            result = loop.run_until_complete(test_async_func())
            assert result == "result"
            
            entries = logger.get_entries()
            assert len(entries) > 0
            assert "completed" in entries[-1].message
        finally:
            loop.close()
    
    def test_traced_sync_function(self):
        """Test traced decorator on sync function"""
        logger = StructuredLogger("test")
        
        @traced(logger)
        def test_sync_func():
            return "result"
        
        result = test_sync_func()
        assert result == "result"
        
        entries = logger.get_entries()
        assert len(entries) > 0
        assert "completed" in entries[-1].message
    
    def test_traced_function_with_error(self):
        """Test traced decorator with error"""
        logger = StructuredLogger("test")
        
        @traced(logger)
        def test_func_error():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            test_func_error()
        
        entries = logger.get_entries()
        assert any("failed" in entry.message for entry in entries)
    
    def test_traced_with_tracer(self):
        """Test traced decorator with TracingManager"""
        logger = StructuredLogger("test")
        tracer = TracingManager("test_service")
        
        @traced(logger, tracer)
        def test_func():
            return "result"
        
        result = test_func()
        assert result == "result"
        
        metrics = tracer.get_metrics()
        assert len(metrics) > 0


# ============================================================================
# Unit Tests: PerformanceTracker
# ============================================================================

class TestPerformanceTracker:
    """Test PerformanceTracker functionality"""
    
    def test_tracker_creation(self):
        """Test creating performance tracker"""
        tracker = PerformanceTracker("trading_engine")
        assert tracker.component == "trading_engine"
    
    def test_track_operation(self):
        """Test tracking operation"""
        tracker = PerformanceTracker("trading_engine")
        
        tracker.track_operation("trade_execution", 100.0)
        tracker.track_operation("trade_execution", 150.0)
        
        stats = tracker.get_stats("trade_execution")
        assert stats["count"] == 2
        assert stats["total_ms"] == 250.0
        assert stats["avg_ms"] == 125.0
        assert stats["min_ms"] == 100.0
        assert stats["max_ms"] == 150.0
    
    def test_get_summary(self):
        """Test getting performance summary"""
        tracker = PerformanceTracker("trading_engine")
        tracker.track_operation("op1", 100.0)
        tracker.track_operation("op2", 200.0)
        
        summary = tracker.get_summary()
        assert summary["component"] == "trading_engine"
        assert summary["total_tracked"] == 2
        assert "op1" in summary["operations"]


# ============================================================================
# Unit Tests: MetricsCollector
# ============================================================================

class TestMetricsCollector:
    """Test MetricsCollector functionality"""
    
    def test_counter_increment(self):
        """Test counter increment"""
        collector = MetricsCollector()
        
        collector.increment_counter("trades_executed", 1)
        collector.increment_counter("trades_executed", 1)
        
        metrics = collector.get_metrics()
        assert metrics["counters"]["trades_executed"] == 2
    
    def test_gauge_set(self):
        """Test gauge set"""
        collector = MetricsCollector()
        
        collector.set_gauge("portfolio_value", 100000.50)
        
        metrics = collector.get_metrics()
        assert metrics["gauges"]["portfolio_value"] == 100000.50
    
    def test_histogram_record(self):
        """Test histogram record"""
        collector = MetricsCollector()
        
        collector.record_histogram("execution_time_ms", 100.0)
        collector.record_histogram("execution_time_ms", 150.0)
        collector.record_histogram("execution_time_ms", 120.0)
        
        metrics = collector.get_metrics()
        histogram = metrics["histograms"]["execution_time_ms"]
        
        assert histogram["count"] == 3
        assert histogram["sum"] == 370.0
        assert histogram["avg"] == 370.0 / 3
        assert histogram["min"] == 100.0
        assert histogram["max"] == 150.0
    
    def test_get_all_metrics(self):
        """Test getting all metrics"""
        collector = MetricsCollector()
        
        collector.increment_counter("counter_1", 5)
        collector.set_gauge("gauge_1", 100.0)
        collector.record_histogram("histogram_1", 50.0)
        
        metrics = collector.get_metrics()
        
        assert "counters" in metrics
        assert "gauges" in metrics
        assert "histograms" in metrics
        assert metrics["counters"]["counter_1"] == 5
        assert metrics["gauges"]["gauge_1"] == 100.0


# ============================================================================
# Integration Tests: End-to-End Logging
# ============================================================================

class TestLoggingIntegration:
    """Integration tests for logging system"""
    
    def test_full_logging_workflow(self):
        """Test complete logging workflow"""
        logger = StructuredLogger("trading_engine")
        tracer = TracingManager("test_service")
        tracker = PerformanceTracker("trading_engine")
        collector = MetricsCollector()
        
        # Log operations
        logger.info("Starting trades", data={"count": 100})
        
        # Track performance
        tracker.track_operation("trade_execution", 125.0)
        
        # Collect metrics
        collector.increment_counter("trades_executed", 100)
        collector.set_gauge("portfolio_value", 105000.0)
        
        # Record trace
        metric = TraceMetrics(
            operation_name="trading_session",
            duration_ms=5000.0,
            status="success",
        )
        tracer.record_metric(metric)
        
        # Verify all components
        assert len(logger.get_entries()) > 0
        assert len(tracker.get_stats()) > 0
        assert len(tracer.get_metrics()) > 0
        
        metrics = collector.get_metrics()
        assert metrics["counters"]["trades_executed"] == 100
        assert metrics["gauges"]["portfolio_value"] == 105000.0
    
    def test_logging_with_correlation_ids(self):
        """Test logging with correlation ID tracking"""
        logger1 = StructuredLogger("component_1")
        logger2 = StructuredLogger("component_2")
        
        logger1.info("Component 1 message")
        logger2.info("Component 2 message")
        
        entries1 = logger1.get_entries()
        entries2 = logger2.get_entries()
        
        # Both should have same correlation ID
        assert entries1[0].correlation_id == entries2[0].correlation_id


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
