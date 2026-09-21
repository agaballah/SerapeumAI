# -*- coding: utf-8 -*-
"""
test_conflict_resolution_behavior.py — Behavioral tests for WP-05-A.

Tests the conflict lifecycle, AI safety, and source navigation behaviors.
Each test proves a specific behavioral guarantee.
"""
from __future__ import annotations

import json
import os
import tempfile
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

from src.infra.persistence.database_manager import DatabaseManager
from src.application.api.fact_api import FactQueryAPI
from src.application.orchestrators.agent_orchestrator import AgentOrchestrator
from src.domain.intelligence.conflict_detector import (
    detect_and_store_conflicts,
    _values_are_equivalent,
)


# ──────────────────────────────────────────────────────────────
# FIXTURES
# ──────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_db():
    """Create a temporary database with all required tables."""
    db_path = os.path.join(tempfile.gettempdir(), f"wp05a_test_{os.getpid()}.db")
    if os.path.exists(db_path):
        os.unlink(db_path)
    db = DatabaseManager(db_path)
    yield db
    db.close_all_instances()
    if os.path.exists(db_path):
        os.unlink(db_path)


def _seed_facts(db: DatabaseManager, project_id: str = "proj-a") -> List[Dict]:
    """Seed test data: file registry, file versions, facts, and fact inputs."""
    # file_registry
    db._exec(
        "INSERT OR REPLACE INTO file_registry (file_id, project_id, first_seen_path, created_at) "
        "VALUES (?, ?, ?, ?)",
        ("file_1", project_id, "spec.pdf", 1000),
    )
    db._exec(
        "INSERT OR REPLACE INTO file_registry (file_id, project_id, first_seen_path, created_at) "
        "VALUES (?, ?, ?, ?)",
        ("file_2", project_id, "drawing.pdf", 1000),
    )

    # file_versions
    db._exec(
        "INSERT OR REPLACE INTO file_versions "
        "(file_version_id, file_id, sha256, size_bytes, file_ext, imported_at, source_path) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("fv-a", "file_1", "hash_a", 100, ".pdf", 1000, "D:/docs/spec.pdf"),
    )
    db._exec(
        "INSERT OR REPLACE INTO file_versions "
        "(file_version_id, file_id, sha256, size_bytes, file_ext, imported_at, source_path) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("fv-b", "file_2", "hash_b", 200, ".pdf", 2000, "D:/docs/drawing.pdf"),
    )

    # facts (conflicting pair + non-conflicting)
    facts_data = [
        {
            "fact_id": "fact_a", "project_id": project_id, "fact_type": "bim.element",
            "subject_kind": "element", "subject_id": "WALL_001",
            "as_of_json": "{}", "value_type": "json", "value_json": "fire_rating=120min",
            "status": "VALIDATED", "confidence": 0.95, "method_id": "ifc_extractor",
            "created_at": 1000, "updated_at": 1000,
        },
        {
            "fact_id": "fact_b", "project_id": project_id, "fact_type": "bim.element",
            "subject_kind": "element", "subject_id": "WALL_001",
            "as_of_json": "{}", "value_type": "json", "value_json": "fire_rating=60min",
            "status": "VALIDATED", "confidence": 0.85, "method_id": "pdf_extractor",
            "created_at": 2000, "updated_at": 2000,
        },
        {
            "fact_id": "fact_c", "project_id": project_id, "fact_type": "schedule.activity",
            "subject_kind": "activity", "subject_id": "ACT_001",
            "as_of_json": "{}", "value_type": "json", "value_json": "duration=14days",
            "status": "VALIDATED", "confidence": 1.0, "method_id": "p6_extractor",
            "created_at": 3000, "updated_at": 3000,
        },
    ]

    for f in facts_data:
        db._exec(
            """INSERT OR REPLACE INTO facts
            (fact_id, project_id, fact_type, subject_kind, subject_id,
             scope_json, as_of_json, value_type, value_json,
             status, confidence, method_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                f["fact_id"], f["project_id"], f["fact_type"], f["subject_kind"], f["subject_id"],
                "{}", f["as_of_json"], f["value_type"], f["value_json"],
                f["status"], f["confidence"], f["method_id"],
                f["created_at"], f["updated_at"],
            ),
        )

    # fact_inputs
    inputs = [
        ("fact_a", "fv-a", json.dumps({"page": 1, "method": "native"}), "evidence"),
        ("fact_b", "fv-b", json.dumps({"page": 3, "method": "ocr"}), "evidence"),
        ("fact_c", "fv-a", json.dumps({"row": 5}), "evidence"),
    ]
    for fid, fvid, loc, kind in inputs:
        db._exec(
            "INSERT OR REPLACE INTO fact_inputs (fact_id, file_version_id, location_json, input_kind) "
            "VALUES (?, ?, ?, ?)",
            (fid, fvid, loc, kind),
        )

    db.commit()
    return facts_data


def _make_fact_dicts_for_detector() -> List[Dict[str, Any]]:
    """Create fact dicts matching what BuildFactsJob passes to detect_and_store_conflicts."""
    return [
        {
            "fact_id": "fact_a", "project_id": "proj-a", "fact_type": "bim.element",
            "subject_id": "WALL_001", "value": "fire_rating=120min",
            "status": "VALIDATED", "confidence": 0.95, "method_id": "ifc_extractor",
            "inputs": [{"file_version_id": "fv-a", "location": {"page": 1}}],
        },
        {
            "fact_id": "fact_b", "project_id": "proj-a", "fact_type": "bim.element",
            "subject_id": "WALL_001", "value": "fire_rating=60min",
            "status": "VALIDATED", "confidence": 0.85, "method_id": "pdf_extractor",
            "inputs": [{"file_version_id": "fv-b", "location": {"page": 3}}],
        },
    ]


# ──────────────────────────────────────────────────────────────
# TEST 1: Two conflicting facts → both values disclosed
# ──────────────────────────────────────────────────────────────

def test_two_conflicting_facts_disclose_both_values(tmp_db):
    """When two facts conflict, the conflict record preserves both values and sources."""
    _seed_facts(tmp_db)

    fact_dicts = _make_fact_dicts_for_detector()
    conflicts = detect_and_store_conflicts(tmp_db, "proj-a", fact_dicts)
    assert len(conflicts) == 1, "Expected 1 conflict between fact_a and fact_b"
    assert conflicts[0]["subject_id"] == "WALL_001"
    assert conflicts[0]["fact_type"] == "bim.element"

    # Both values preserved in conflict record (to_dict returns parsed 'values')
    values = conflicts[0]["values"]
    value_set = {v["value"] for v in values}
    assert "fire_rating=120min" in value_set, "Value A missing from conflict record"
    assert "fire_rating=60min" in value_set, "Value B missing from conflict record"

    # conflict_flag set on both facts
    row_a = tmp_db.execute("SELECT conflict_flag FROM facts WHERE fact_id='fact_a'").fetchone()
    row_b = tmp_db.execute("SELECT conflict_flag FROM facts WHERE fact_id='fact_b'").fetchone()
    assert row_a[0] == 1, "fact_a should have conflict_flag=1"
    assert row_b[0] == 1, "fact_b should have conflict_flag=1"

    # Non-conflicting fact NOT flagged
    row_c = tmp_db.execute("SELECT conflict_flag FROM facts WHERE fact_id='fact_c'").fetchone()
    assert row_c[0] == 0, "fact_c should NOT have conflict_flag"


# ──────────────────────────────────────────────────────────────
# TEST 2: Chat must NOT silently present one value as settled
# ──────────────────────────────────────────────────────────────

def test_chat_does_not_silently_select_one_conflicting_value(tmp_db):
    """When conflicts exist, the disclosure block includes both values."""
    _seed_facts(tmp_db)

    fact_api = FactQueryAPI(tmp_db)
    result = fact_api.get_certified_facts(
        query_intent="fire rating for wall",
        project_id="proj-a",
    )

    conflicts = result.get("conflicts", [])
    assert len(conflicts) >= 1, "FactQueryAPI should detect the conflict"

    # The formatted LLM context includes conflict disclosure
    context = result.get("formatted_context", "")
    assert "CONFLICT" in context.upper(), "LLM context must include conflict disclosure"

    # The orchestrator's deterministic disclosure includes both values
    orch = AgentOrchestrator(db=tmp_db, llm=MagicMock())
    disclosure = orch._compose_conflict_disclosure(conflicts)
    assert "CONFLICT DISCLOSURE" in disclosure, "Disclosure must be labeled"
    assert "fire_rating=120min" in disclosure, "Value A must be in disclosure"
    assert "fire_rating=60min" in disclosure, "Value B must be in disclosure"
    assert "Action required" in disclosure, "Must state human resolution needed"

    # When no conflicts, disclosure is empty
    empty_disclosure = orch._compose_conflict_disclosure([])
    assert empty_disclosure == "", "No disclosure when no conflicts"


# ──────────────────────────────────────────────────────────────
# TEST 3: Resolved conflict preserves both values
# ──────────────────────────────────────────────────────────────

def test_resolved_conflict_preserves_both_values(tmp_db):
    """After resolution, both original values remain in fact_conflicts."""
    _seed_facts(tmp_db)

    fact_dicts = _make_fact_dicts_for_detector()
    conflicts = detect_and_store_conflicts(tmp_db, "proj-a", fact_dicts)
    conflict_id = conflicts[0]["conflict_id"]

    tmp_db.resolve_conflict(conflict_id, accepted_fact_id="fact_a", resolver="engineer")

    conflict = tmp_db.get_conflict_by_id(conflict_id)
    assert conflict is not None, "Conflict record must persist after resolution"
    assert conflict["resolution"] == "RESOLVED"
    assert conflict["resolved_by"] == "engineer"

    values = json.loads(conflict["values_json"])
    value_set = {v["value"] for v in values}
    assert "fire_rating=120min" in value_set, "Value A preserved"
    assert "fire_rating=60min" in value_set, "Value B preserved"

    # Accepted fact keeps its status
    row_a = tmp_db.execute("SELECT status FROM facts WHERE fact_id='fact_a'").fetchone()
    assert row_a[0] in ("VALIDATED", "HUMAN_CERTIFIED"), "Accepted fact not downgraded"

    # Non-accepted fact is SUPERSEDED (not deleted)
    row_b = tmp_db.execute("SELECT status FROM facts WHERE fact_id='fact_b'").fetchone()
    assert row_b[0] == "SUPERSEDED", "Non-accepted fact must be SUPERSEDED"
    assert row_b is not None, "Non-accepted fact must still exist in DB"


# ──────────────────────────────────────────────────────────────
# TEST 4: No conflict → normal behavior unchanged
# ──────────────────────────────────────────────────────────────

def test_no_conflict_normal_answer_unchanged(tmp_db):
    """When no conflicts exist for the queried subject, behavior is normal."""
    _seed_facts(tmp_db)

    fact_api = FactQueryAPI(tmp_db)
    result = fact_api.get_certified_facts(
        query_intent="schedule duration",
        project_id="proj-a",
    )

    facts = result.get("facts", [])
    schedule_facts = [f for f in facts if f.get("subject_id") == "ACT_001"]
    assert len(schedule_facts) == 1, "Should find exactly one schedule fact"

    # No conflicts for ACT_001
    act_conflicts = [c for c in result.get("conflicts", []) if c.get("subject_id") == "ACT_001"]
    assert len(act_conflicts) == 0, "ACT_001 should have no conflicts"


# ──────────────────────────────────────────────────────────────
# TEST 5: Conflict sources A/B remain available after resolution
# ──────────────────────────────────────────────────────────────

def test_conflict_sources_preserved_after_resolution(tmp_db):
    """Both source references remain queryable after conflict resolution."""
    _seed_facts(tmp_db)

    fact_dicts = _make_fact_dicts_for_detector()
    conflicts = detect_and_store_conflicts(tmp_db, "proj-a", fact_dicts)
    conflict_id = conflicts[0]["conflict_id"]
    tmp_db.resolve_conflict(conflict_id, accepted_fact_id="fact_a", resolver="engineer")

    # Both facts still exist
    row_a = tmp_db.execute("SELECT status FROM facts WHERE fact_id='fact_a'").fetchone()
    row_b = tmp_db.execute("SELECT status FROM facts WHERE fact_id='fact_b'").fetchone()
    assert row_a is not None, "fact_a must still exist"
    assert row_b is not None, "fact_b must still exist (as SUPERSEDED)"
    assert row_b[0] == "SUPERSEDED"

    # Both source paths still queryable
    src_a = tmp_db.execute(
        "SELECT fv.source_path FROM fact_inputs fi "
        "LEFT JOIN file_versions fv ON fv.file_version_id = fi.file_version_id "
        "WHERE fi.fact_id='fact_a' LIMIT 1"
    ).fetchone()
    src_b = tmp_db.execute(
        "SELECT fv.source_path FROM fact_inputs fi "
        "LEFT JOIN file_versions fv ON fv.file_version_id = fi.file_version_id "
        "WHERE fi.fact_id='fact_b' LIMIT 1"
    ).fetchone()
    assert src_a and src_a[0] == "D:/docs/spec.pdf", f"Source A path preserved: {src_a}"
    assert src_b and src_b[0] == "D:/docs/drawing.pdf", f"Source B path preserved: {src_b}"


# ──────────────────────────────────────────────────────────────
# TEST 6: Conflict state transitions OPEN → REVIEWED → RESOLVED
# ──────────────────────────────────────────────────────────────

def test_conflict_state_transitions(tmp_db):
    """Verify the full conflict lifecycle: UNRESOLVED → REVIEWED → RESOLVED."""
    _seed_facts(tmp_db)

    fact_dicts = _make_fact_dicts_for_detector()
    conflicts = detect_and_store_conflicts(tmp_db, "proj-a", fact_dicts)
    conflict_id = conflicts[0]["conflict_id"]

    # Initial: UNRESOLVED
    c = tmp_db.get_conflict_by_id(conflict_id)
    assert c["resolution"] == "UNRESOLVED", f"Initial: {c['resolution']}"

    # → REVIEWED
    tmp_db.mark_conflict_reviewed(conflict_id, reviewer="engineer_1")
    c = tmp_db.get_conflict_by_id(conflict_id)
    assert c["resolution"] == "REVIEWED", f"After review: {c['resolution']}"

    # → RESOLVED
    tmp_db.resolve_conflict(conflict_id, accepted_fact_id="fact_a", resolver="engineer_1")
    c = tmp_db.get_conflict_by_id(conflict_id)
    assert c["resolution"] == "RESOLVED", f"After resolve: {c['resolution']}"
    assert c["resolved_by"] == "engineer_1"

    # No more open conflicts
    open_conflicts = tmp_db.get_open_conflicts("proj-a")
    assert len(open_conflicts) == 0, "No open conflicts after resolution"


# ──────────────────────────────────────────────────────────────
# TEST 7: Source navigation uses stored provenance correctly
# ──────────────────────────────────────────────────────────────

def test_source_navigation_uses_stored_provenance(tmp_db):
    """Verify source_path and location_json are correctly stored and retrievable."""
    _seed_facts(tmp_db)

    row = tmp_db.execute(
        "SELECT fv.source_path, fi.location_json "
        "FROM fact_inputs fi "
        "LEFT JOIN file_versions fv ON fv.file_version_id = fi.file_version_id "
        "WHERE fi.fact_id = 'fact_a' LIMIT 1"
    ).fetchone()
    assert row is not None, "Provenance row must exist"
    assert row[0] == "D:/docs/spec.pdf", f"Got: {row[0]}"

    loc = json.loads(row[1])
    assert loc.get("page") == 1
    assert loc.get("method") == "native"

    row_b = tmp_db.execute(
        "SELECT fv.source_path, fi.location_json "
        "FROM fact_inputs fi "
        "LEFT JOIN file_versions fv ON fv.file_version_id = fi.file_version_id "
        "WHERE fi.fact_id = 'fact_b' LIMIT 1"
    ).fetchone()
    assert row_b[0] == "D:/docs/drawing.pdf"
    loc_b = json.loads(row_b[1])
    assert loc_b.get("page") == 3
    assert loc_b.get("method") == "ocr"


# ──────────────────────────────────────────────────────────────
# VALUE EQUIVALENCE (false-positive control)
# ──────────────────────────────────────────────────────────────

def test_value_equivalence_prevents_false_conflicts():
    """Formatting differences must NOT create false conflicts."""
    assert _values_are_equivalent("Hello", "hello") is True
    assert _values_are_equivalent("100", 100) is True
    assert _values_are_equivalent("60.0", "60") is True
    assert _values_are_equivalent("60min", "120min") is False
    assert _values_are_equivalent("A", "B") is False
    assert _values_are_equivalent(None, None) is True
    assert _values_are_equivalent("", None) is True


def test_same_value_facts_produce_no_conflict(tmp_db):
    """Identical values must NOT produce a conflict."""
    _seed_facts(tmp_db)
    fact_dicts = [
        {"fact_id": "f1", "project_id": "p", "fact_type": "t", "subject_id": "s",
         "value": "42", "status": "VALIDATED", "confidence": 1.0, "method_id": "m1", "inputs": []},
        {"fact_id": "f2", "project_id": "p", "fact_type": "t", "subject_id": "s",
         "value": "42", "status": "VALIDATED", "confidence": 1.0, "method_id": "m2", "inputs": []},
    ]
    conflicts = detect_and_store_conflicts(tmp_db, "p", fact_dicts)
    assert len(conflicts) == 0, "Same-value facts must NOT produce a conflict"


def test_different_value_facts_produce_conflict(tmp_db):
    """Different values for same subject MUST produce a conflict."""
    _seed_facts(tmp_db)
    fact_dicts = [
        {"fact_id": "f1", "project_id": "p", "fact_type": "t", "subject_id": "s",
         "value": "100", "status": "VALIDATED", "confidence": 1.0, "method_id": "m1", "inputs": []},
        {"fact_id": "f2", "project_id": "p", "fact_type": "t", "subject_id": "s",
         "value": "200", "status": "VALIDATED", "confidence": 1.0, "method_id": "m2", "inputs": []},
    ]
    conflicts = detect_and_store_conflicts(tmp_db, "p", fact_dicts)
    assert len(conflicts) == 1, "Different-value facts MUST produce a conflict"
