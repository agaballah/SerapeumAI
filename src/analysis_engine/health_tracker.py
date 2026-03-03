# -*- coding: utf-8 -*-
# Copyright (c) 2025 Ahmed Gaballa
# Licensed under the Apache License, Version 2.0

"""
health_tracker.py — Page Analysis Health Tracking
-------------------------------------------------
Tracks which pages have successfully completed analysis and which need retry.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional
import json
import time


class HealthStatus(Enum):
    """Health status for a page."""
    PENDING = "pending"           # Not yet processed
    HEALTHY = "healthy"           # Successfully analyzed and saved
    UNHEALTHY_PARSE = "unhealthy_parse"  # LLM returned invalid JSON
    UNHEALTHY_SAVE = "unhealthy_save"    # Failed to save to DB
    UNHEALTHY_LLM = "unhealthy_llm"      # LLM call failed
    SKIPPED = "skipped"           # Intentionally skipped


@dataclass
class PageHealth:
    """Health record for a single page."""
    doc_id: str
    page_index: int
    status: HealthStatus
    summary: Optional[str] = None
    error_message: Optional[str] = None
    attempt_count: int = 0
    last_attempt_ts: float = 0
    duration_seconds: float = 0
    run_id: Optional[str] = None  # For correlating batch jobs
    
    def to_dict(self) -> Dict:
        return {
            "doc_id": self.doc_id,
            "page_index": self.page_index,
            "status": self.status.value,
            "summary": self.summary,
            "error_message": self.error_message,
            "attempt_count": self.attempt_count,
            "last_attempt_ts": self.last_attempt_ts,
            "duration_seconds": self.duration_seconds,
            "run_id": self.run_id
        }


class HealthTracker:
    """Tracks health of all pages during analysis."""
    
    def __init__(self):
        self.pages: Dict[str, PageHealth] = {}  # Key: f"{doc_id}_{page_index}"
        self.metrics: List[Dict] = []
        
    def _make_key(self, doc_id: str, page_index: int) -> str:
        return f"{doc_id}_{page_index}"
    
    def record_success(self, doc_id: str, page_index: int, summary: str, duration: float):
        """Record a successful analysis."""
        key = self._make_key(doc_id, page_index)
        self.pages[key] = PageHealth(
            doc_id=doc_id,
            page_index=page_index,
            status=HealthStatus.HEALTHY,
            summary=summary[:200],  # Truncate for storage
            attempt_count=self.pages.get(key, PageHealth(doc_id, page_index, HealthStatus.PENDING)).attempt_count + 1,
            last_attempt_ts=time.time(),
            duration_seconds=duration
        )
    
    def record_failure(
        self, 
        doc_id: str, 
        page_index: int, 
        failure_type: HealthStatus,
        error_message: str,
        duration: float
    ):
        """Record a failed analysis."""
        key = self._make_key(doc_id, page_index)
        existing = self.pages.get(key)
        
        self.pages[key] = PageHealth(
            doc_id=doc_id,
            page_index=page_index,
            status=failure_type,
            error_message=error_message[:500],  # Truncate
            attempt_count=(existing.attempt_count if existing else 0) + 1,
            last_attempt_ts=time.time(),
            duration_seconds=duration
        )
    
    def get_retry_candidates(self, max_attempts: int = 3) -> List[PageHealth]:
        """Get pages that should be retried."""
        candidates = []
        for page in self.pages.values():
            if page.status in [HealthStatus.UNHEALTHY_PARSE, HealthStatus.UNHEALTHY_SAVE, HealthStatus.UNHEALTHY_LLM]:
                if page.attempt_count < max_attempts:
                    candidates.append(page)
        return candidates
    
    def get_stats(self) -> Dict:
        """Get overall statistics."""
        stats = {
            "total": len(self.pages),
            "healthy": 0,
            "unhealthy_parse": 0,
            "unhealthy_save": 0,
            "unhealthy_llm": 0,
            "pending": 0,
            "skipped": 0
        }
        
        for page in self.pages.values():
            if page.status == HealthStatus.HEALTHY:
                stats["healthy"] += 1
            elif page.status == HealthStatus.UNHEALTHY_PARSE:
                stats["unhealthy_parse"] += 1
            elif page.status == HealthStatus.UNHEALTHY_SAVE:
                stats["unhealthy_save"] += 1
            elif page.status == HealthStatus.UNHEALTHY_LLM:
                stats["unhealthy_llm"] += 1
            elif page.status == HealthStatus.PENDING:
                stats["pending"] += 1
            elif page.status == HealthStatus.SKIPPED:
                stats["skipped"] += 1
        
        return stats
    
    def save_report(self, filepath: str):
        """Save health report to JSON file."""
        report = {
            "timestamp": time.time(),
            "stats": self.get_stats(),
            "pages": [p.to_dict() for p in self.pages.values()]
        }
        # Include collected metrics when present
        if self.metrics:
            report["metrics"] = list(self.metrics)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

    def record_metric(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a generic metric point for later reporting.

        Args:
            name: Metric name (e.g., 'llm_latency', 'vision_page_duration')
            value: Numeric value (seconds, count, etc.)
            tags: Optional dict of tags to help filter/aggregate
        """
        point = {"name": name, "value": float(value), "ts": time.time(), "tags": tags or {}}
        self.metrics.append(point)

    def get_metrics(self) -> List[Dict]:
        """Return collected metric points."""
        return list(self.metrics)
    
    def print_summary(self):
        """Print a concise summary."""
        stats = self.get_stats()
        
        print("\n" + "="*80)
        print("📊 PAGE ANALYSIS HEALTH SUMMARY")
        print("="*80)
        print(f"✅ Healthy:         {stats['healthy']:>4} / {stats['total']}")
        print(f"❌ Parse Errors:    {stats['unhealthy_parse']:>4}")
        print(f"❌ Save Errors:     {stats['unhealthy_save']:>4}")
        print(f"❌ LLM Errors:      {stats['unhealthy_llm']:>4}")
        print(f"⏸️  Pending:         {stats['pending']:>4}")
        print(f"⏭️  Skipped:         {stats['skipped']:>4}")
        
        health_rate = (stats['healthy'] / stats['total'] * 100) if stats['total'] > 0 else 0
        print(f"\n🎯 Health Rate: {health_rate:.1f}%")
        print("="*80 + "\n")
        
        # Show retry candidates
        retry_candidates = self.get_retry_candidates()
        if retry_candidates:
            print(f"🔄 {len(retry_candidates)} pages eligible for retry:")
            for page in retry_candidates[:10]:  # Show first 10
                print(f"   • Page {page.page_index} ({page.doc_id[:8]}...): {page.status.value} - {page.error_message}")
            if len(retry_candidates) > 10:
                print(f"   ... and {len(retry_candidates) - 10} more")
            print()


# Global instance
_global_tracker = HealthTracker()


def get_health_tracker() -> HealthTracker:
    """Get global health tracker instance."""
    return _global_tracker
