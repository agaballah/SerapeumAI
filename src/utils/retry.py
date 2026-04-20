# -*- coding: utf-8 -*-
# Copyright (c) 2025 Ahmed Gaballa
# Licensed under the Apache License, Version 2.0

"""
retry.py — Retry logic for LLM and network operations
-----------------------------------------------------
Implements exponential backoff with configurable retry strategies.
"""

import time
import functools
from typing import Callable, Any, Optional, Type, Tuple
from enum import Enum


class RetryStrategy(Enum):
    """Retry strategy types."""
    EXPONENTIAL = "exponential"  # 1s, 2s, 4s, 8s...
    LINEAR = "linear"            # 1s, 2s, 3s, 4s...
    FIXED = "fixed"              # 1s, 1s, 1s, 1s...


class RetryError(Exception):
    """Raised when all retry attempts are exhausted."""
    
    def __init__(self, attempts: int, last_exception: Exception):
        self.attempts = attempts
        self.last_exception = last_exception
        super().__init__(
            f"Failed after {attempts} attempts. Last error: {last_exception}"
        )


def retry(
    max_attempts: int = 3,
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[int, Exception], None]] = None
):
    """
    Decorator for retrying functions with exponential backoff.
    
    Args:
        max_attempts: Maximum number of attempts (including first)
        strategy: Retry delay strategy
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        exceptions: Tuple of exceptions to catch and retry
        on_retry: Optional callback(attempt_num, exception)
        
    Usage:
        @retry(max_attempts=3, strategy=RetryStrategy.EXPONENTIAL)
        def call_llm():
            return llm.chat(...)
        
        # With callback:
        def log_retry(attempt, error):
            print(f"Attempt {attempt} failed: {error}")
        
        @retry(max_attempts=5, on_retry=log_retry)
        def flaky_function():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    # Don't retry on last attempt
                    if attempt >= max_attempts:
                        raise RetryError(max_attempts, e) from e
                    
                    # Calculate delay
                    if strategy == RetryStrategy.EXPONENTIAL:
                        delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                    elif strategy == RetryStrategy.LINEAR:
                        delay = min(base_delay * attempt, max_delay)
                    else:  # FIXED
                        delay = base_delay
                    
                    # Callback
                    if on_retry:
                        try:
                            on_retry(attempt, e)
                        except Exception:
                            pass  # Don't let callback errors break retry
                    
                    # Wait before retry
                    time.sleep(delay)
            
            # Should never reach here, but just in case
            raise RetryError(max_attempts, last_exception)
        
        return wrapper
    return decorator


class RetryContext:
    """
    Context manager for manual retry logic.
    
    Usage:
        retry_ctx = RetryContext(max_attempts=3)
        
        while retry_ctx.should_retry():
            try:
                result = risky_operation()
                break
            except Exception as e:
                retry_ctx.record_failure(e)
        else:
            # All attempts failed
            raise retry_ctx.get_error()
    """
    
    def __init__(
        self,
        max_attempts: int = 3,
        strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
        base_delay: float = 1.0,
        max_delay: float = 60.0
    ):
        self.max_attempts = max_attempts
        self.strategy = strategy
        self.base_delay = base_delay
        self.max_delay = max_delay
        
        self.attempt = 0
        self.last_exception: Optional[Exception] = None
    
    def should_retry(self) -> bool:
        """Check if should attempt (or retry)."""
        return self.attempt < self.max_attempts
    
    def record_failure(self, exception: Exception):
        """Record a failure and sleep if retry is possible."""
        self.attempt += 1
        self.last_exception = exception
        
        # Don't sleep after last attempt
        if self.attempt >= self.max_attempts:
            return
        
        # Calculate delay
        if self.strategy == RetryStrategy.EXPONENTIAL:
            delay = min(self.base_delay * (2 ** (self.attempt - 1)), self.max_delay)
        elif self.strategy == RetryStrategy.LINEAR:
            delay = min(self.base_delay * self.attempt, self.max_delay)
        else:  # FIXED
            delay = self.base_delay
        
        time.sleep(delay)
    
    def get_error(self) -> RetryError:
        """Get RetryError for final failure."""
        return RetryError(self.attempt, self.last_exception)


# Convenience functions for common patterns

def retry_llm_call(func: Callable, *args, **kwargs) -> Any:
    """
    Retry an LLM call with sensible defaults.
    
    Usage:
        result = retry_llm_call(lambda: llm.chat(messages=...))
    """
    @retry(
        max_attempts=3,
        strategy=RetryStrategy.EXPONENTIAL,
        base_delay=2.0,
        max_delay=10.0,
        on_retry=lambda attempt, err: print(f"LLM call failed (attempt {attempt}): {err}")
    )
    def wrapped():
        return func(*args, **kwargs)
    
    return wrapped()


def retry_network_call(func: Callable, *args, **kwargs) -> Any:
    """
    Retry a network call with sensible defaults.
    
    Usage:
        result = retry_network_call(lambda: requests.get(url))
    """
    @retry(
        max_attempts=5,
        strategy=RetryStrategy.EXPONENTIAL,
        base_delay=1.0,
        max_delay=30.0,
        on_retry=lambda attempt, err: print(f"Network call failed (attempt {attempt}): {err}")
    )
    def wrapped():
        return func(*args, **kwargs)
    
    return wrapped()
