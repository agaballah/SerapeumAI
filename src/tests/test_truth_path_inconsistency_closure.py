# -*- coding: utf-8 -*-
"""
test_truth_path_inconsistency_closure.py

Packet 2: Truth-path inconsistency closure.

Locks the release-critical invariant:

- Mounted Facts page may show VALIDATED document facts.
- Chat must use the same trusted-state semantics.
- Chat must not falsely refuse with "no certified facts" when trusted document
  facts exist but are not locked into fact_snapshot_registry.
"""

import time
from pathlib import Path

import pytest

from src.application.api.fact_api import FactQueryAPI
from src.application.orchestrators.agent_orchestrator import AgentOrchestrator
from src.application.services.coverage_gate import CoverageGate
from src.infra.adapters.llm_service import LLMService
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


class MockLLM(LLMService):
    def __init__(self):
        self.model = "mock"

    def chat_json(self, system, user, **kwargs):
        return {
            "answer": "Based on trusted document facts, this document has 8 pages.",
            "citations": [],
        }

    def chat(self, messages, **kwargs):
        return {"choices": [{"message": {"content": "Direct answer"}}]}


@pytest.fixture
def mounted_validated_doc_facts_without_snapshot_registry(tmp_path):
    """
    Simulates the live blocker condition:

    The project has VALIDATED document facts visible through the mounted fact
    layer, but fact_snapshot_registry does not contain those fact ids.
    """
    db = DatabaseManager(root_dir=str(tmp_path), db_name=":memory:")
    _load_truth_schema(db)

    project_id = "proj_truth_path"
    snapshot_id = db.create_snapshot(project_id, status="VALIDATED")

    now = int(time.time())
    for fact_id, fact_type, value_json in (
        ("doc_f1", "document.page_count", '"8"'),
        ("doc_f2", "document.has_text", "true"),
        ("doc_f3", "document.profile", '"text_pdf"'),
    ):
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
                "VALIDATED",
                "DOC_CONTROL",
                now,
                now,
                "TEXT",
                '{"file_version_id": "fv_doc_001", "doc_id": "doc1"}',
                "document_builder",
                value_json,
            ),
        )

    db.project_id = project_id
    try:
        yield db, project_id, snapshot_id
    finally:
        db.close_all_connections()


def test_fact_api_returns_mounted_validated_document_facts_without_snapshot_registry(
    mounted_validated_doc_facts_without_snapshot_registry,
):
    db, project_id, snapshot_id = mounted_validated_doc_facts_without_snapshot_registry

    result = FactQueryAPI(db).get_certified_facts(
        query_intent="what is this document",
        project_id=project_id,
        snapshot_id=snapshot_id,
    )

    assert result["has_certified_data"] is True
    assert result["count"] >= 3
    assert "document.page_count" in result.get("formatted_context", "")
    assert "document.has_text" in result.get("formatted_context", "")
    assert "document.profile" in result.get("formatted_context", "")


def test_coverage_gate_does_not_false_refuse_document_query_when_validated_facts_exist(
    mounted_validated_doc_facts_without_snapshot_registry,
):
    db, project_id, snapshot_id = mounted_validated_doc_facts_without_snapshot_registry

    result = CoverageGate(db).check(
        "what is this document",
        project_id=project_id,
        snapshot_id=snapshot_id,
    )

    assert result["is_complete"] is True
    assert result["missing_fact_types"] == []
    assert result["refusal_message"] is None


def test_orchestrator_answers_from_trusted_document_facts_without_false_no_certified_claim(
    mounted_validated_doc_facts_without_snapshot_registry,
):
    db, project_id, snapshot_id = mounted_validated_doc_facts_without_snapshot_registry

    response = AgentOrchestrator(db=db, llm=MockLLM()).answer_question(
        query="what is this document",
        project_id=project_id,
        snapshot_id=snapshot_id,
    )

    assert response.get("mode") == "answered"
    assert response.get("supporting_only") is False
    assert response.get("source_lanes", {}).get("trusted_facts", 0) >= 3
    assert "no certified facts" not in response.get("answer", "").lower()
    assert "no trusted facts" not in response.get("answer", "").lower()


def test_missing_schedule_facts_are_reported_as_missing_domain_not_no_facts_at_all(
    mounted_validated_doc_facts_without_snapshot_registry,
):
    db, project_id, snapshot_id = mounted_validated_doc_facts_without_snapshot_registry

    result = CoverageGate(db).check(
        "what is the delay risk in schedule",
        project_id=project_id,
        snapshot_id=snapshot_id,
    )

    assert result["is_complete"] is False
    assert result["has_any_facts"] is True
    assert "schedule" in str(result.get("missing_fact_types", [])).lower()

    refusal = result.get("refusal_message", "")
    assert "Trusted facts exist for this project" in refusal
    assert "No trusted facts" not in refusal
    assert "No certified facts" not in refusal
