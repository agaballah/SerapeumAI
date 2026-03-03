# -*- coding: utf-8 -*-
import time
import functools
import logging
import threading
from enum import Enum
from typing import Callable, Any, Dict, Optional, Type, Tuple
import tkinter as tk
from tkinter import messagebox

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "closed"   # Normal operation
    OPEN = "open"       # Failure detected, rejecting calls
    HALF_OPEN = "half_open"  # Testing if service is back

class CircuitBreaker:
    """
    Prevents cascading failures by stopping calls after N failures.
    """
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
        exceptions: Tuple[Type[Exception], ...] = (Exception,)
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.exceptions = exceptions
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0
        self._lock = threading.Lock()

    def __call__(self, func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            with self._lock:
                # 1. Check State
                if self.state == CircuitState.OPEN:
                    if time.time() - self.last_failure_time > self.recovery_timeout:
                        logger.info(f"[CircuitBreaker:{self.name}] Entering HALF-OPEN state")
                        self.state = CircuitState.HALF_OPEN
                    else:
                        raise RuntimeError(f"Circuit Breaker '{self.name}' is OPEN. Call rejected.")

            # 2. Execute
            try:
                result = func(*args, **kwargs)
                
                # 3. Success -> Close if it was half-open
                with self._lock:
                    if self.state == CircuitState.HALF_OPEN:
                        logger.info(f"[CircuitBreaker:{self.name}] Restoring to CLOSED state")
                        self.state = CircuitState.CLOSED
                        self.failure_count = 0
                return result

            except self.exceptions as e:
                with self._lock:
                    self.failure_count += 1
                    self.last_failure_time = time.time()
                    
                    if self.state != CircuitState.OPEN and self.failure_count >= self.failure_threshold:
                        logger.error(f"[CircuitBreaker:{self.name}] TRIP detected! Entering OPEN state. Error: {e}")
                        self.state = CircuitState.OPEN
                    
                    if self.state == CircuitState.HALF_OPEN:
                        logger.error(f"[CircuitBreaker:{self.name}] Half-open test FAILED. Re-entering OPEN state.")
                        self.state = CircuitState.OPEN
                
                raise e

        return wrapper

def safe_ui_command(error_title: str = "Application Error"):
    """
    Decorator for UI callbacks to prevent main loop crashes.
    Catches exceptions, logs them, and shows a message box.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"UI Command Error in {func.__name__}: {e}", exc_info=True)
                
                # Try to show error silently or via messagebox if in main thread
                try:
                    # Tkinter check (best effort)
                    messagebox.showerror(error_title, f"An unexpected error occurred:\n{str(e)}")
                except:
                    pass
                return None
        return wrapper
    return decorator

# Shared circuit for LLM services
llm_circuit = CircuitBreaker("LLM_SERVICE", failure_threshold=3, recovery_timeout=60)
db_circuit = CircuitBreaker("DATABASE_OPS", failure_threshold=10, recovery_timeout=10)
