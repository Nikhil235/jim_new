"""
Logging & Observability Configuration - Structured logging with distributed tracing

Provides:
- Structured JSON logging for all components
- OpenTelemetry-based distributed tracing
- Correlation IDs for request tracking
- Performance metrics collection
- Error tracking and reporting
- Log aggregation setup

Production Features:
- Zero-overhead structured logging
- Automatic span creation
- Context propagation
- Custom business metrics
- Error aggregation
- Performance histograms
"""

import json
import logging
import time
import uuid
import functools
from datetime import datetime
from typing import Any, Dict, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from contextlib import contextmanager
import contextvars

# For OpenTelemetry integration (when available)
try:
    from opentelemetry import trace, metrics
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False


class LogLevel(Enum):
    """Log levels"""
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3
    CRITICAL = 4
    
    @staticmethod
    def from_string(value: str) -> 'LogLevel':
        """Convert string to LogLevel"""
        return LogLevel[value.upper()]


@dataclass
class LogEntry:
    """Structured log entry"""
    timestamp: datetime
    level: LogLevel
    component: str
    message: str
    correlation_id: str
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    duration_ms: Optional[float] = None
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    tags: Dict[str, str] = None
    data: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = {}
        if self.data is None:
            self.data = {}
    
    def to_json_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.name,
            "component": self.component,
            "message": self.message,
            "correlation_id": self.correlation_id,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "duration_ms": self.duration_ms,
            "error_message": self.error_message,
            "error_type": self.error_type,
            "request_id": self.request_id,
            "user_id": self.user_id,
            "tags": self.tags,
            "data": self.data,
        }


@dataclass
class TraceMetrics:
    """Metrics for a traced operation"""
    operation_name: str
    duration_ms: float
    status: str  # "success", "error", "timeout"
    error_type: Optional[str] = None
    component: Optional[str] = None
    attributes: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.attributes is None:
            self.attributes = {}


# Context variables for tracking
correlation_id_var = contextvars.ContextVar('correlation_id')
trace_id_var = contextvars.ContextVar('trace_id')
span_id_var = contextvars.ContextVar('span_id')


class StructuredLogger:
    """
    Structured logging with automatic JSON formatting
    
    Example:
        >>> logger = StructuredLogger("trading_engine")
        >>> logger.info("Trade executed", data={"trade_id": "t_001", "pnl": 1250.50})
    """
    
    def __init__(
        self,
        component: str,
        log_level: LogLevel = LogLevel.INFO,
        output_handler: Optional[Callable] = None,
    ):
        """
        Initialize StructuredLogger
        
        Args:
            component: Component name for logs
            log_level: Minimum log level
            output_handler: Custom output handler function
        """
        self.component = component
        self.log_level = log_level
        self.output_handler = output_handler or self._default_output
        self.entries = []
        
        # Get or create correlation ID
        try:
            self.correlation_id = correlation_id_var.get()
        except LookupError:
            self.correlation_id = str(uuid.uuid4())
            correlation_id_var.set(self.correlation_id)
    
    def debug(self, message: str, data: Optional[Dict[str, Any]] = None, 
              **kwargs) -> None:
        """Log debug message"""
        if LogLevel.DEBUG.value >= self.log_level.value:
            self._log(LogLevel.DEBUG, message, data, **kwargs)
    
    def info(self, message: str, data: Optional[Dict[str, Any]] = None,
             **kwargs) -> None:
        """Log info message"""
        if LogLevel.INFO.value >= self.log_level.value:
            self._log(LogLevel.INFO, message, data, **kwargs)
    
    def warning(self, message: str, data: Optional[Dict[str, Any]] = None,
                **kwargs) -> None:
        """Log warning message"""
        if LogLevel.WARNING.value >= self.log_level.value:
            self._log(LogLevel.WARNING, message, data, **kwargs)
    
    def error(self, message: str, error: Optional[Exception] = None,
              data: Optional[Dict[str, Any]] = None, **kwargs) -> None:
        """Log error message"""
        if LogLevel.ERROR.value >= self.log_level.value:
            if error:
                kwargs['error_type'] = type(error).__name__
                kwargs['error_message'] = str(error)
            self._log(LogLevel.ERROR, message, data, **kwargs)
    
    def critical(self, message: str, error: Optional[Exception] = None,
                 data: Optional[Dict[str, Any]] = None, **kwargs) -> None:
        """Log critical message"""
        if LogLevel.CRITICAL.value >= self.log_level.value:
            if error:
                kwargs['error_type'] = type(error).__name__
                kwargs['error_message'] = str(error)
            self._log(LogLevel.CRITICAL, message, data, **kwargs)
    
    def _log(self, level: LogLevel, message: str, 
             data: Optional[Dict[str, Any]] = None, **kwargs) -> None:
        """Internal logging method"""
        try:
            trace_id = trace_id_var.get()
        except LookupError:
            trace_id = None
        
        try:
            span_id = span_id_var.get()
        except LookupError:
            span_id = None
        
        entry = LogEntry(
            timestamp=datetime.utcnow(),
            level=level,
            component=self.component,
            message=message,
            correlation_id=self.correlation_id,
            trace_id=trace_id,
            span_id=span_id,
            data=data or {},
            **kwargs,
        )
        
        self.entries.append(entry)
        self.output_handler(entry)
    
    def _default_output(self, entry: LogEntry) -> None:
        """Default output handler (stdout as JSON)"""
        json_data = entry.to_json_dict()
        print(json.dumps(json_data))
    
    def get_entries(self) -> list:
        """Get all logged entries"""
        return self.entries.copy()


class TracingManager:
    """
    Distributed tracing management with OpenTelemetry
    
    Example:
        >>> manager = TracingManager()
        >>> with manager.span("trade_execution") as span:
        ...     span.set_attribute("trade_id", "t_001")
    """
    
    def __init__(self, service_name: str = "mini-medallion"):
        """
        Initialize TracingManager
        
        Args:
            service_name: Service name for traces
        """
        self.service_name = service_name
        self.enabled = OTEL_AVAILABLE
        self.metrics_data = []
        
        if OTEL_AVAILABLE:
            self._setup_otel()
        
    def _setup_otel(self) -> None:
        """Setup OpenTelemetry"""
        try:
            jaeger_exporter = JaegerExporter(
                agent_host_name="localhost",
                agent_port=6831,
            )
            
            trace_provider = TracerProvider()
            trace_provider.add_span_processor(
                BatchSpanProcessor(jaeger_exporter)
            )
            trace.set_tracer_provider(trace_provider)
            self.tracer = trace.get_tracer(__name__)
        except Exception as e:
            print(f"Failed to setup OpenTelemetry: {e}")
            self.enabled = False
    
    @contextmanager
    def span(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """
        Create a traced span
        
        Args:
            name: Span name
            attributes: Span attributes
        
        Yields:
            Span context manager
        """
        if self.enabled:
            with self.tracer.start_as_current_span(name) as span:
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, str(value))
                yield span
        else:
            # Dummy span when OTEL not available
            class DummySpan:
                def set_attribute(self, key, value): pass
            yield DummySpan()
    
    def record_metric(self, metric: TraceMetrics) -> None:
        """Record operation metric"""
        self.metrics_data.append(metric)
    
    def get_metrics(self) -> list:
        """Get all recorded metrics"""
        return self.metrics_data.copy()


def traced(logger: StructuredLogger, tracer: Optional[TracingManager] = None):
    """
    Decorator for automatic tracing and logging
    
    Example:
        >>> @traced(logger)
        ... async def execute_trade(trade_id):
        ...     return await broker.execute(trade_id)
    """
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            span_name = f"{func.__module__}.{func.__name__}"
            
            try:
                if tracer:
                    with tracer.span(span_name) as span:
                        result = await func(*args, **kwargs)
                else:
                    result = await func(*args, **kwargs)
                
                duration_ms = (time.time() - start_time) * 1000
                logger.info(
                    f"{span_name} completed",
                    data={"duration_ms": duration_ms},
                )
                
                if tracer:
                    metric = TraceMetrics(
                        operation_name=span_name,
                        duration_ms=duration_ms,
                        status="success",
                    )
                    tracer.record_metric(metric)
                
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(
                    f"{span_name} failed",
                    error=e,
                    data={"duration_ms": duration_ms},
                )
                
                if tracer:
                    metric = TraceMetrics(
                        operation_name=span_name,
                        duration_ms=duration_ms,
                        status="error",
                        error_type=type(e).__name__,
                    )
                    tracer.record_metric(metric)
                
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            span_name = f"{func.__module__}.{func.__name__}"
            
            try:
                if tracer:
                    with tracer.span(span_name) as span:
                        result = func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                duration_ms = (time.time() - start_time) * 1000
                logger.info(
                    f"{span_name} completed",
                    data={"duration_ms": duration_ms},
                )
                
                if tracer:
                    metric = TraceMetrics(
                        operation_name=span_name,
                        duration_ms=duration_ms,
                        status="success",
                    )
                    tracer.record_metric(metric)
                
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(
                    f"{span_name} failed",
                    error=e,
                    data={"duration_ms": duration_ms},
                )
                
                if tracer:
                    metric = TraceMetrics(
                        operation_name=span_name,
                        duration_ms=duration_ms,
                        status="error",
                        error_type=type(e).__name__,
                    )
                    tracer.record_metric(metric)
                
                raise
        
        # Return appropriate wrapper based on function type
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


class PerformanceTracker:
    """Track performance metrics for operations"""
    
    def __init__(self, component: str):
        """
        Initialize PerformanceTracker
        
        Args:
            component: Component name
        """
        self.component = component
        self.operations = {}
    
    def track_operation(self, operation_name: str, duration_ms: float) -> None:
        """Track an operation duration"""
        if operation_name not in self.operations:
            self.operations[operation_name] = {
                "count": 0,
                "total_ms": 0,
                "min_ms": float('inf'),
                "max_ms": 0,
                "avg_ms": 0,
            }
        
        stats = self.operations[operation_name]
        stats["count"] += 1
        stats["total_ms"] += duration_ms
        stats["min_ms"] = min(stats["min_ms"], duration_ms)
        stats["max_ms"] = max(stats["max_ms"], duration_ms)
        stats["avg_ms"] = stats["total_ms"] / stats["count"]
    
    def get_stats(self, operation_name: Optional[str] = None) -> Dict[str, Any]:
        """Get performance statistics"""
        if operation_name:
            return self.operations.get(operation_name, {})
        return self.operations.copy()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all operations"""
        return {
            "component": self.component,
            "operations": self.get_stats(),
            "total_tracked": len(self.operations),
        }


class MetricsCollector:
    """Collect application metrics"""
    
    def __init__(self):
        """Initialize MetricsCollector"""
        self.counters = {}
        self.gauges = {}
        self.histograms = {}
    
    def increment_counter(self, name: str, value: int = 1) -> None:
        """Increment a counter"""
        if name not in self.counters:
            self.counters[name] = 0
        self.counters[name] += value
    
    def set_gauge(self, name: str, value: float) -> None:
        """Set a gauge value"""
        self.gauges[name] = value
    
    def record_histogram(self, name: str, value: float) -> None:
        """Record a histogram value"""
        if name not in self.histograms:
            self.histograms[name] = []
        self.histograms[name].append(value)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all metrics"""
        return {
            "counters": self.counters.copy(),
            "gauges": self.gauges.copy(),
            "histograms": {
                name: {
                    "count": len(values),
                    "sum": sum(values),
                    "avg": sum(values) / len(values) if values else 0,
                    "min": min(values) if values else 0,
                    "max": max(values) if values else 0,
                }
                for name, values in self.histograms.items()
            },
        }
