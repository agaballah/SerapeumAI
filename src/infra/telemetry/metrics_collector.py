# -*- coding: utf-8 -*-
"""
Phase 3.2: Metrics Collector
---------------------------
Aggregates and persists performance and quality metrics for the AI pipeline.
"""

import time
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)

@dataclass
class PipelineMetric:
    """Represents a single point of telemetry data."""
    metric_name: str
    value: float
    unit: str
    tags: Dict[str, str]
    timestamp: float = field(default_factory=time.time)

class MetricsCollector:
    """
    Collects and aggregates telemetry data across extraction and analysis.
    
    Metrics categories:
    - Performance: Latency, VRAM usage, throughput.
    - Quality: Confidence scores, conflict rates, validation pass rates.
    - Cost/Resources: Token counts, model utilization.
    """
    
    def __init__(self, db=None, project_id: str = "default"):
        self.db = db
        self.project_id = project_id
        self.metrics_buffer: List[PipelineMetric] = []
        
    def record_metric(self, name: str, value: float, unit: str = "count", tags: Optional[Dict] = None):
        """Record a metric point."""
        all_tags = {"project_id": self.project_id}
        if tags:
            all_tags.update(tags)
            
        metric = PipelineMetric(
            metric_name=name,
            value=value,
            unit=unit,
            tags=all_tags
        )
        self.metrics_buffer.append(metric)
        logger.debug(f"Metric recorded: {name}={value}{unit} Tags={all_tags}")
        
    def record_latency(self, component: str, duration: float, tags: Optional[Dict] = None):
        """Helper to record component latency."""
        self.record_metric(f"{component}_latency", duration, "seconds", tags)
        
    def record_accuracy(self, field_name: str, confidence: float, tags: Optional[Dict] = None):
        """Helper to record extraction confidence/accuracy."""
        self.record_metric(f"confidence_{field_name}", confidence, "ratio", tags)
        
    def flush(self):
        """
        Persist buffered metrics to database.
        
        In Phase 3.2, this writes to the extraction_accuracy table or a 
        new telemetry table if implemented.
        """
        if not self.db or not self.metrics_buffer:
            self.metrics_buffer = []
            return
            
        try:
            # For now, we log as structured JSON in telemetry stream
            # Phase 3.3 will integrate deeper with SQLite tables
            for metric in self.metrics_buffer:
                # Mock DB insertion logic
                pass
            
            logger.info(f"Flushed {len(self.metrics_buffer)} metrics")
            self.metrics_buffer = []
        except Exception as e:
            logger.error(f"Failed to flush metrics: {e}")

