# -*- coding: utf-8 -*-
# Copyright (c) 2025 Ahmed Gaballa
# Licensed under the Apache License, Version 2.0

"""
error_handler.py — Structured error handling framework
------------------------------------------------------
Replaces bare `except Exception` with severity-based handling.
"""

import logging
import traceback
import time
from enum import Enum
from typing import Optional, Dict, Any, List
from dataclasses import dataclass


logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels."""
    WARNING = 1   # User-recoverable (e.g., password-protected PDF)
    ERROR = 2     # Document-level failure (skip and continue)
    CRITICAL = 3  # Pipeline-breaking (stop everything)


@dataclass
class ErrorRecord:
    """Record of an error occurrence."""
    timestamp: float
    severity: ErrorSeverity
    exception_type: str
    message: str
    user_message: str
    context: Dict[str, Any]
    traceback_str: str
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "severity": self.severity.name,
            "exception_type": self.exception_type,
            "message": self.message,
            "user_message": self.user_message,
            "context": self.context,
            "traceback": self.traceback_str[:1000]  # Truncate
        }


class ErrorHandler:
    """
    Global error handler with structured logging and UI notifications.
    
    Usage:
        from src.utils.error_handler import handle_error, ErrorSeverity
        
        try:
            risky_operation()
        except PDFPasswordError as e:
            handle_error(e, severity=ErrorSeverity.WARNING,
                        user_message="This PDF is password protected",
                        context={"file": filepath})
        except CorruptedFileError as e:
            handle_error(e, severity=ErrorSeverity.ERROR,
                        context={"file": filepath})
        except Exception as e:
            handle_error(e, severity=ErrorSeverity.CRITICAL,
                        context={"stage": "extraction"})
            raise  # Re-raise critical errors
    """
    
    def __init__(self):
        self.errors: List[ErrorRecord] = []
        self._ui_callback = None
    
    def set_ui_callback(self, callback):
        """Set callback for UI notifications (called on ERROR/CRITICAL)."""
        self._ui_callback = callback
    
    def handle(
        self,
        exception: Exception,
        severity: ErrorSeverity,
        user_message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        auto_raise: bool = False
    ):
        """
        Handle an exception with structured logging.
        
        Args:
            exception: The caught exception
            severity: WARNING/ERROR/CRITICAL
            user_message: User-friendly message (shown in UI)
            context: Additional context (file path, stage, etc.)
            auto_raise: If True, re-raise CRITICAL errors after handling
        """
        # Create error record
        record = ErrorRecord(
            timestamp=time.time(),
            severity=severity,
            exception_type=exception.__class__.__name__,
            message=str(exception),
            user_message=user_message or str(exception),
            context=context or {},
            traceback_str=traceback.format_exc()
        )
        
        self.errors.append(record)
        
        # Log with appropriate level
        log_level = {
            ErrorSeverity.WARNING: logging.WARNING,
            ErrorSeverity.ERROR: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL
        }[severity]
        
        logger.log(
            log_level,
            f"[{severity.name}] {record.exception_type}: {record.message}",
            extra=record.context,
            exc_info=(severity == ErrorSeverity.CRITICAL)  # Full traceback for critical
        )
        
        # Notify UI for ERROR/CRITICAL
        if severity in [ErrorSeverity.ERROR, ErrorSeverity.CRITICAL] and self._ui_callback:
            try:
                self._ui_callback(record)
            except Exception as ui_err:
                logger.error(f"UI callback failed: {ui_err}")
        
        # Auto-raise critical errors
        if auto_raise and severity == ErrorSeverity.CRITICAL:
            raise exception
    
    def get_recent_errors(self, limit: int = 10) -> List[ErrorRecord]:
        """Get recent errors for UI display."""
        return self.errors[-limit:]
    
    def get_error_counts(self) -> Dict[str, int]:
        """Get error counts by severity."""
        counts = {
            "WARNING": 0,
            "ERROR": 0,
            "CRITICAL": 0
        }
        for err in self.errors:
            counts[err.severity.name] += 1
        return counts
    
    def clear(self):
        """Clear error history."""
        self.errors.clear()


# Global instance
_global_handler = ErrorHandler()


def handle_error(
    exception: Exception,
    severity: ErrorSeverity,
    user_message: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    auto_raise: bool = False
):
    """Convenience function for global error handler."""
    _global_handler.handle(exception, severity, user_message, context, auto_raise)


def get_error_handler() -> ErrorHandler:
    """Get global error handler instance."""
    return _global_handler


# Custom exception types for common scenarios
class PDFPasswordError(Exception):
    """PDF is password protected."""
    pass


class CorruptedFileError(Exception):
    """File is corrupted or unreadable."""
    pass


class ModelNotLoadedError(Exception):
    """Required model is not loaded."""
    pass


class InsufficientMemoryError(Exception):
    """Not enough memory to complete operation."""
    pass
