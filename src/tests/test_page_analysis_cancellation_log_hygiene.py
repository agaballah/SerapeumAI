# -*- coding: utf-8 -*-
"""
test_page_analysis_cancellation_log_hygiene.py

Wave 1A-2B: cooperative cancellation shutdown log hygiene.

Expected app/session-close cancellation must not be logged as ERROR/Traceback
or recorded as an unhealthy LLM failure. Real failures must still be logged as
errors and recorded as failures.
"""

import logging

import pytest

from src.analysis_engine.page_analysis import PageAnalyzer
from src.infra.adapters.cancellation import CancellationError


class _CancellationToken:
    def is_set(self):
        return True


class _FakeTracker:
    def __init__(self):
        self.failures = []

    def record_failure(self, *args, **kwargs):
        self.failures.append((args, kwargs))

    def record_success(self, *args, **kwargs):
        raise AssertionError("record_success should not be called in these tests")


def _analyzer_shell():
    analyzer = object.__new__(PageAnalyzer)
    analyzer.db = object()
    analyzer.llm = object()
    analyzer.adaptive_engine = object()
    return analyzer


def test_single_page_cooperative_cancellation_is_info_not_error(monkeypatch, caplog):
    tracker = _FakeTracker()

    import src.analysis_engine.health_tracker as health_tracker

    monkeypatch.setattr(health_tracker, "get_health_tracker", lambda: tracker)

    analyzer = _analyzer_shell()
    page = {
        "doc_id": "doc-1",
        "page_index": 10,
        "py_text": "This page has enough text to avoid no-signal behavior.",
    }

    with caplog.at_level(logging.DEBUG):
        result = analyzer._analyze_single_page(
            page,
            [page],
            cancellation_token=_CancellationToken(),
        )

    assert result is None
    assert tracker.failures == []

    messages = [record.getMessage() for record in caplog.records]
    assert any("analysis cancelled" in message for message in messages)

    assert not any(record.levelno >= logging.ERROR for record in caplog.records)
    assert not any(record.exc_info for record in caplog.records)


def test_single_page_real_failure_still_logs_error_and_records_failure(monkeypatch, caplog):
    tracker = _FakeTracker()

    import src.analysis_engine.health_tracker as health_tracker

    monkeypatch.setattr(health_tracker, "get_health_tracker", lambda: tracker)

    class _FailingAdaptiveEngine:
        def analyze_page(self, page):
            raise RuntimeError("real model failure")

    analyzer = _analyzer_shell()
    analyzer.adaptive_engine = _FailingAdaptiveEngine()

    page = {
        "doc_id": "doc-2",
        "page_index": 3,
        "py_text": "This page has enough text to trigger adaptive analysis. " * 3,
    }

    with caplog.at_level(logging.DEBUG):
        result = analyzer._analyze_single_page(page, [page], cancellation_token=None)

    assert result is None
    assert tracker.failures

    error_records = [record for record in caplog.records if record.levelno >= logging.ERROR]
    assert error_records
    assert any("real model failure" in record.getMessage() for record in error_records)
    assert any(record.exc_info for record in error_records)


def test_cancellation_error_type_remains_distinct():
    assert issubclass(CancellationError, Exception)
