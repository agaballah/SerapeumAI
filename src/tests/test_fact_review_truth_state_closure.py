# -*- coding: utf-8 -*-
"""
test_fact_review_truth_state_closure.py

Packet 3: Review actions truth-state closure.

Locks the release-critical invariant:

- Certify action promotes facts to HUMAN_CERTIFIED.
- Reject action moves facts to REJECTED.
- FactQueryAPI/chat trusted path consumes HUMAN_CERTIFIED / VALIDATED only.
- Rejected facts are excluded from trusted answer paths.
"""

import time
from pathlib import Path

import pytest

from src.application.api.fact_api import FactQueryAPI
from src.application.services.coverage_gate import CoverageGate
from src.domain.facts.repository import FactRepository
from src.infra.persistence.database_manager import DatabaseManager


def _load_truth_schema(db: DatabaseManager) -> None:
    base = Path("src/infra/persistence/migrations")
    db.execute_script((base / "001_baseline_v14.sql").read_text(encoding="utf-8"))

    v16 = base / "016_fix_missing_column.sql"
    if v16.exists():
        db.execute_script(v16.read_text(encoding="utf-8"))

    db.execute_script((base / "017_truth_engine_v2.sql").read_text(encoding="utf-8"))

    v18 = base / "018_fact_snapshots.sql"
    if v18.exists():
        db.execute_script(v18.read_text(encoding="utf-8"))


@pytest.fixture
def review_db(tmp_path):
    db = DatabaseManager(root_dir=str(tmp_path), db_name=":memory:")
    _load_truth_schema(db)

    project_id = "proj_review_state"
    snapshot_id = db.create_snapshot(project_id, status="VALIDATED")
    now = int(time.time())

    facts = [
        ("candidate_page_count", "document.page_count", "CANDIDATE", '"12"'),
        ("candidate_has_text", "document.has_text", "CANDIDATE", "true"),
        ("candidate_profile", "document.profile", "CANDIDATE", '"text_pdf"'),
        ("validated_requirement", "document.requirement", "VALIDATED", '{"statement": "Contractor shall submit shop drawings"}'),
    ]

    for fact_id, fact_type, status, value_json in facts:
        db.execute(
            """
            INSERT INTO facts
                (fact_id, project_id, fact_type, subject_kind, subject_id,
                 status, domain, created_at, updated_at, value_type,
                 as_of_json, method_id, value_json)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                fact_id,
                project_id,
                fact_type,
                "document",
                "doc1",
                status,
                "DOC_CONTROL",
                now,
                now,
                "TEXT",
                '{"file_version_id": "fv_review_001", "doc_id": "doc1"}',
                "document_builder",
                value_json,
            ),
        )

    db.project_id = project_id
    try:
        yield db, project_id, snapshot_id
    finally:
        db.close_all_connections()


def test_certify_fact_promotes_candidate_to_human_certified(review_db):
    db, project_id, snapshot_id = review_db
    repo = FactRepository(db)

    assert repo.certify_fact("candidate_page_count") is True

    row = db.execute(
        "SELECT status FROM facts WHERE fact_id = ?",
        ("candidate_page_count",),
    ).fetchone()
    assert row["status"] == "HUMAN_CERTIFIED"

    result = FactQueryAPI(db).get_certified_facts(
        query_intent="how many pages",
        project_id=project_id,
        snapshot_id=snapshot_id,
    )
    assert result["has_certified_data"] is True
    assert any(f["fact_id"] == "candidate_page_count" for f in result["facts"])


def test_reject_fact_excludes_fact_from_trusted_query_path(review_db):
    db, project_id, snapshot_id = review_db
    repo = FactRepository(db)

    assert repo.certify_fact("candidate_page_count") is True
    assert repo.reject_fact("candidate_page_count") is True

    row = db.execute(
        "SELECT status FROM facts WHERE fact_id = ?",
        ("candidate_page_count",),
    ).fetchone()
    assert row["status"] == "REJECTED"

    result = FactQueryAPI(db).get_certified_facts(
        query_intent="how many pages",
        project_id=project_id,
        snapshot_id=snapshot_id,
    )
    assert not any(f["fact_id"] == "candidate_page_count" for f in result["facts"])


def test_coverage_gate_passes_after_required_document_facts_are_certified(review_db):
    db, project_id, snapshot_id = review_db
    repo = FactRepository(db)

    for fact_id in ("candidate_page_count", "candidate_has_text", "candidate_profile"):
        assert repo.certify_fact(fact_id) is True

    result = CoverageGate(db).check(
        "what is this document",
        project_id=project_id,
        snapshot_id=snapshot_id,
    )

    assert result["is_complete"] is True
    assert result["missing_fact_types"] == []
    assert result["refusal_message"] is None


def test_coverage_gate_fails_after_required_document_fact_is_rejected(review_db):
    db, project_id, snapshot_id = review_db
    repo = FactRepository(db)

    for fact_id in ("candidate_page_count", "candidate_has_text", "candidate_profile"):
        assert repo.certify_fact(fact_id) is True

    assert repo.reject_fact("candidate_profile") is True

    result = CoverageGate(db).check(
        "what is this document",
        project_id=project_id,
        snapshot_id=snapshot_id,
    )

    assert result["is_complete"] is False
    assert "document.profile" in result["missing_fact_types"]


def test_update_fact_status_rejects_unknown_status(review_db):
    db, _project_id, _snapshot_id = review_db
    repo = FactRepository(db)

    with pytest.raises(ValueError):
        repo.update_fact_status("candidate_page_count", "APPROVED_BY_MAGIC")


def test_update_fact_status_returns_false_for_missing_fact(review_db):
    db, _project_id, _snapshot_id = review_db
    repo = FactRepository(db)

    assert repo.certify_fact("missing_fact_id") is False
