"""
Resilience Utilities
====================
Provides decorators for automatic retries, timeouts, and circuit breakers
to ensure robust data ingestion pipelines and API interactions.
"""

import time
import functools
from loguru import logger
import threading
from typing import Callable, Any, Type, Tuple, Optional


def retry(
    max_attempts: int = 3,
    backoff_multiplier: float = 2.0,
    initial_delay: float = 1.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    jitter: bool = True
):
    """
    Retry a function upon encountering specified exceptions.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            attempt = 1
            delay = initial_delay
            while attempt <= max_attempts:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        logger.error(f"[{func.__name__}] Failed after {max_attempts} attempts. Last error: {e}")
                        raise
                    
                    import random
                    actual_delay = delay * (random.uniform(0.5, 1.5) if jitter else 1.0)
                    logger.warning(f"[{func.__name__}] Attempt {attempt}/{max_attempts} failed: {e}. Retrying in {actual_delay:.2f}s...")
                    time.sleep(actual_delay)
                    
                    attempt += 1
                    delay *= backoff_multiplier
        return wrapper
    return decorator


def timeout(seconds: int):
    """
    Timeout a function after a specified number of seconds.
    Note: This is a simple thread-based timeout and may not interrupt C-extensions or blocking I/O immediately.
    """
    class TimeoutError(Exception):
        pass

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            result = []
            exception = []

            def worker():
                try:
                    result.append(func(*args, **kwargs))
                except Exception as e:
                    exception.append(e)

            thread = threading.Thread(target=worker)
            thread.daemon = True
            thread.start()
            thread.join(seconds)

            if thread.is_alive():
                logger.error(f"[{func.__name__}] Timed out after {seconds} seconds.")
                raise TimeoutError(f"Function {func.__name__} timed out after {seconds} seconds.")
            
            if exception:
                raise exception[0]
            
            return result[0]
        return wrapper
    return decorator


class CircuitBreaker:
    """
    A simple Circuit Breaker pattern.
    """
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.last_failure_time = 0.0

    def __call__(self, func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            if self.state == "OPEN":
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    logger.info(f"[{func.__name__}] Circuit breaker half-open. Testing connection...")
                    self.state = "HALF_OPEN"
                else:
                    raise Exception(f"Circuit breaker is OPEN for {func.__name__}. Fast failing.")

            try:
                result = func(*args, **kwargs)
                if self.state == "HALF_OPEN":
                    logger.info(f"[{func.__name__}] Circuit breaker closed. Recovered.")
                    self.state = "CLOSED"
                    self.failures = 0
                return result
            except Exception as e:
                self.failures += 1
                self.last_failure_time = time.time()
                if self.state == "HALF_OPEN" or self.failures >= self.failure_threshold:
                    if self.state != "OPEN":
                        logger.error(f"[{func.__name__}] Circuit breaker OPENED after {self.failures} failures.")
                    self.state = "OPEN"
                raise e
        return wrapper

def circuit_breaker(failure_threshold: int = 5, recovery_timeout: int = 60):
    """
    Decorator for circuit breaker.
    """
    return CircuitBreaker(failure_threshold, recovery_timeout)
