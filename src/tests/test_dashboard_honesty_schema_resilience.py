# -*- coding: utf-8 -*-
"""
test_dashboard_honesty_schema_resilience.py

Packet 4: Dashboard honesty / extractor schema resilience.

Locks release-critical dashboard behavior:

- Missing optional extraction schema columns must not crash dashboard refresh.
- extractor_id is accepted when extractor_name is absent.
- runtime metrics do not overclaim when timing columns are absent.
- dashboard fact counts show qualified facts, not all built facts.
- P6 critical path status is not overclaimed when float data is absent.
"""

from pathlib import Path

import pytest

from src.application.services.dashboard_honesty import (
    assess_p6_truth,
    backlog_label,
    compute_fact_visibility_metrics,
    fact_ratio_health,
    governance_status_label,
)
from src.infra.persistence.database_manager import DatabaseManager
from src.ui.pages.dashboard_page import DashboardPage


def _page_without_ui() -> DashboardPage:
    """Create a DashboardPage shell without constructing Tk widgets."""
    return object.__new__(DashboardPage)


@pytest.fixture
def db(tmp_path):
    manager = DatabaseManager(root_dir=str(tmp_path), db_name=":memory:")
    try:
        yield manager
    finally:
        manager.close_all_connections()


def test_extraction_runtime_uses_extractor_id_when_extractor_name_missing(db):
    page = _page_without_ui()

    db.execute(
        """
        CREATE TABLE extraction_runs (
            extractor_id TEXT,
            status TEXT,
            started_at REAL,
            ended_at REAL
        )
        """
    )
    db.execute("INSERT INTO extraction_runs VALUES ('pdf_parser', 'SUCCESS', 10.0, 10.25)")
    db.execute("INSERT INTO extraction_runs VALUES ('ocr_lane', 'SUCCESS', 20.0, 20.50)")
    db.execute("INSERT INTO extraction_runs VALUES ('pdf_parser', 'FAILED', 30.0, 99.0)")
    db.commit()

    rows = page._fetch_extraction_runtimes(db)
    metrics = {row[0]: row[1] for row in rows}

    assert metrics["pdf_parser"] == pytest.approx(0.25)
    assert metrics["ocr_lane"] == pytest.approx(0.50)
    assert len(metrics) == 2


def test_extraction_runtime_missing_name_columns_returns_empty_not_error(db):
    page = _page_without_ui()

    db.execute(
        """
        CREATE TABLE extraction_runs (
            status TEXT,
            started_at REAL,
            ended_at REAL
        )
        """
    )
    db.execute("INSERT INTO extraction_runs VALUES ('SUCCESS', 1.0, 2.0)")
    db.commit()

    assert page._fetch_extraction_runtimes(db) == []


def test_extraction_runtime_missing_timing_columns_counts_runs_without_overclaiming_timing(db):
    page = _page_without_ui()

    db.execute("CREATE TABLE extraction_runs (extractor_name TEXT, status TEXT)")
    db.execute("INSERT INTO extraction_runs VALUES ('native_pdf', 'SUCCESS')")
    db.execute("INSERT INTO extraction_runs VALUES ('native_pdf', 'SUCCESS')")
    db.execute("INSERT INTO extraction_runs VALUES ('ocr_lane', 'SUCCESS')")
    db.commit()

    rows = page._fetch_extraction_runtimes(db)
    metrics = {row[0]: row[1] for row in rows}

    assert metrics["native_pdf"] == 2
    assert metrics["ocr_lane"] == 1


def test_recent_logs_and_latest_failure_missing_optional_columns_return_safe_defaults(db):
    page = _page_without_ui()

    db.execute("CREATE TABLE job_queue (type_name TEXT, status TEXT)")
    db.execute("INSERT INTO job_queue VALUES ('ANALYZE_DOC', 'FAILED')")
    db.commit()

    assert page._fetch_recent_logs(db) == []
    assert page._fetch_latest_failure(db) is None


def test_recent_logs_and_latest_failure_work_when_required_columns_exist(db):
    page = _page_without_ui()

    db.execute(
        """
        CREATE TABLE job_queue (
            type_name TEXT,
            status TEXT,
            updated_at INTEGER,
            error_text TEXT
        )
        """
    )
    db.execute("INSERT INTO job_queue VALUES ('EXTRACT', 'DONE', 100, NULL)")
    db.execute("INSERT INTO job_queue VALUES ('ANALYZE_DOC', 'FAILED', 200, 'LM Studio unavailable')")
    db.commit()

    logs = page._fetch_recent_logs(db)
    latest_failure = page._fetch_latest_failure(db)

    assert logs[0] == (200, "ANALYZE_DOC", "FAILED")
    assert latest_failure == (200, "LM Studio unavailable")


def test_dashboard_fact_metrics_show_qualified_facts_not_total_built_facts():
    metrics = compute_fact_visibility_metrics(
        total_facts=10,
        valid_facts=3,
        human_facts=2,
        candidate_facts=5,
    )

    assert metrics["built_facts"] == 10
    assert metrics["qualified_facts"] == 5
    assert metrics["candidate_facts"] == 5
    assert metrics["pending_qualification"] == 5
    assert fact_ratio_health(metrics) == "PARTIAL"
    assert governance_status_label(metrics["valid_facts"], trusted_label="TRUSTED") == "TRUSTED"
    assert governance_status_label(metrics["human_facts"], trusted_label="GOLDEN") == "GOLDEN"
    assert backlog_label(metrics["candidate_facts"]) == "ACTION_REQUIRED"


def test_p6_truth_does_not_overclaim_critical_path_without_float_data():
    no_schedule = assess_p6_truth(total_activities=0, activities_with_float=0, critical_count=0)
    no_float = assess_p6_truth(total_activities=8, activities_with_float=0, critical_count=0)
    partial_float = assess_p6_truth(total_activities=8, activities_with_float=3, critical_count=1)
    full_float = assess_p6_truth(total_activities=8, activities_with_float=8, critical_count=2)

    assert no_schedule["status"] == "N/A"
    assert no_float["status"] == "LIMITED"
    assert "critical path unknown" in no_float["metric"]
    assert partial_float["status"] == "PARTIAL"
    assert full_float["status"] == "VERIFIED"
