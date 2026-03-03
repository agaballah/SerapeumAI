# -*- coding: utf-8 -*-
"""
Phase 3.2: Structured Logging
----------------------------
Standardizes JSON logging format for AI pipeline observability.
"""

import logging
import json
import time
import sys
from typing import Any, Dict, Optional

class JsonFormatter(logging.Formatter):
    """
    Standardizes log output as JSON for machine readability.
    """
    def format(self, record):
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "func": record.funcName,
        }
        
        # Merge extra fields if present
        if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):
            log_data.update(record.extra_data)
            
        return json.dumps(log_data)

def setup_structured_logging(level=logging.INFO):
    """
    Configure the root logger with JSON formatting.
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    
    root = logging.getLogger()
    root.setLevel(level)
    # Remove existing handlers to avoid duplicates
    for h in root.handlers[:]:
        root.removeHandler(h)
    root.addHandler(handler)
    
    return root

class AILogger:
    """
    Wrapper for logging AI pipeline events with structured metadata.
    """
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        
    def info(self, message: str, **kwargs):
        self.logger.info(message, extra={"extra_data": kwargs})
        
    def error(self, message: str, error: Exception = None, **kwargs):
        data = kwargs
        if error:
            data["error_type"] = error.__class__.__name__
            data["error_details"] = str(error)
        self.logger.error(message, extra={"extra_data": data})

    def track_pipeline_event(self, event_type: str, page_id: int, status: str, **kwargs):
        """Helper to log complex pipeline events."""
        self.info(
            f"PipelineEvent: {event_type} - {status}",
            event_type=event_type,
            page_id=page_id,
            status=status,
            **kwargs
        )
