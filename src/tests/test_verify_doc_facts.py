# -*- coding: utf-8 -*-
"""
test_verify_doc_facts.py — Real app-path verification for document fact routing.

Proves:
  1. document-intent queries infer document.* fact types
  2. certified document facts are returned (fact_context non-empty)
  3. orchestrator does NOT refuse supported document queries
  4. orchestrator DOES refuse queries with genuinely missing coverage
"""
import sys
import time
import pytest
from pathlib import Path
sys.path.insert(0, str(Path('.').resolve()))

from src.application.api.fact_api import FactQueryAPI
from src.application.services.coverage_gate import CoverageGate
from src.infra.persistence.database_manager import DatabaseManager
from src.infra.adapters.llm_service import LLMService
from src.application.orchestrators.agent_orchestrator import AgentOrchestrator


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def doc_db(tmp_path):
    """In-memory DB pre-loaded with migrations and one certified document fact."""
    db = DatabaseManager(root_dir=str(tmp_path), db_name=":memory:")
    base = Path("src/infra/persistence/migrations")
    db.execute_script(open(base / "001_baseline_v14.sql").read())
    v16 = base / "016_fix_missing_column.sql"
    if v16.exists():
        db.execute_script(open(v16).read())
    db.execute_script(open(base / "017_truth_engine_v2.sql").read())
    v18 = base / "018_fact_snapshots.sql"
    if v18.exists():
        db.execute_script(open(v18).read())

    # Create a snapshot so the orchestrator uses a known snapshot_id
    snap_id = db.create_snapshot("proj1", status="VALIDATED")

    now = int(time.time())
    import json as _json
    # as_of_json must contain the snapshot_id so _query_certified's LIKE filter matches
    as_of = _json.dumps({"snapshot_id": snap_id})

    facts = [
        ("f1","document.page_count",'"10"'),
        ("f2","document.has_text",'true'),
        ("f3","document.profile",'"text_pdf"'),
    ]
    for fact_id, fact_type, value_json in facts:
        db.execute("""
            INSERT INTO facts
                (fact_id, project_id, fact_type, subject_kind, subject_id,
                 status, domain, created_at, updated_at, value_type,
                 as_of_json, method_id, value_json)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (fact_id,"proj1",fact_type,"document","doc1",
              "VALIDATED","DOC_CONTROL",now,now,"TEXT",as_of,"m1",value_json))
        try:
            db.execute("INSERT INTO fact_snapshot_registry (snapshot_id, fact_id) VALUES (?, ?)", (snap_id, fact_id))
        except Exception:
            pass
    db.project_id = "proj1"
    return db


class MockLLM(LLMService):
    def __init__(self):
        self.model = "mock"
    def chat_json(self, system, user, **kwargs):
        return {"answer": "Based on certified facts, the document has 10 pages.", "citations": []}
    def chat(self, messages, **kwargs):
        return {"choices": [{"message": {"content": "Direct answer"}}]}


@pytest.fixture
def doc_db_without_snapshot_registry(tmp_path):
    """Project has trusted document facts, but they are not locked into fact_snapshot_registry."""
    db = DatabaseManager(root_dir=str(tmp_path), db_name=":memory:")
    base = Path("src/infra/persistence/migrations")
    db.execute_script(open(base / "001_baseline_v14.sql").read())
    v16 = base / "016_fix_missing_column.sql"
    if v16.exists():
        db.execute_script(open(v16).read())
    db.execute_script(open(base / "017_truth_engine_v2.sql").read())
    v18 = base / "018_fact_snapshots.sql"
    if v18.exists():
        db.execute_script(open(v18).read())

    snap_id = db.create_snapshot("proj1", status="VALIDATED")
    now = int(time.time())
    for fact_id, fact_type, value_json in (
        ("f10", "document.page_count", '"8"'),
        ("f11", "document.has_text", 'true'),
        ("f12", "document.profile", '"text_pdf"'),
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
                fact_id, "proj1", fact_type, "document", "doc1",
                "VALIDATED", "DOC_CONTROL", now, now, "TEXT",
                '{"file_version_id": "fv_doc_001", "doc_id": "doc1"}', "m1", value_json,
            ),
        )
    db.project_id = "proj1"
    return db, snap_id


# ─── Tests ───────────────────────────────────────────────────────────────────

def test_document_intent_infers_document_fact_types(doc_db):
    """Verify _infer_fact_types maps all document-style queries to document.*."""
    api = FactQueryAPI(doc_db)
    document_queries = [
        "what is this document",
        "summarize this document",
        "tell me about this file",
        "how many pages",
        "does this PDF have text",
        "document profile",
    ]
    for q in document_queries:
        inferred = api._infer_fact_types(q)
        assert "document.page_count" in inferred, f"Missing document.page_count for: {q}"
        assert "document.has_text" in inferred, f"Missing document.has_text for: {q}"
        assert "document.profile" in inferred, f"Missing document.profile for: {q}"


def test_certified_document_facts_returned(doc_db):
    """Verify get_certified_facts returns certified document facts and non-empty context."""
    api = FactQueryAPI(doc_db)
    result = api.get_certified_facts(
        query_intent="what is this document", project_id="proj1"
    )
    assert result["has_certified_data"], "has_certified_data should be True"
    assert result["count"] > 0, "count should be > 0"
    fc = result.get("formatted_context", "")
    assert "document.page_count" in fc, "document.page_count should appear in formatted_context"


def test_coverage_gate_passes_for_document_query(doc_db):
    """Verify CoverageGate does not refuse supported document queries."""
    gate = CoverageGate(doc_db)
    result = gate.check("what is this document", project_id="proj1")
    assert result["is_complete"], (
        f"Coverage gate should pass for document query. Missing: {result.get('missing_fact_types')}"
    )


def test_coverage_gate_refuses_missing_schedule_facts(doc_db):
    """Verify CoverageGate still refuses queries whose fact types don't exist."""
    gate = CoverageGate(doc_db)
    result = gate.check("what is the delay risk", project_id="proj1")
    assert not result["is_complete"], "Should refuse when schedule facts are absent"
    assert "schedule" in str(result.get("missing_fact_types", [])).lower()


def test_orchestrator_answers_supported_document_query(doc_db):
    """Verify orchestrator produces a non-refused answer for a supported document query."""
    orchestrator = AgentOrchestrator(db=doc_db, llm=MockLLM())
    res = orchestrator.answer_question(query="what is this document", project_id="proj1")
    assert res.get("mode") != "refused", f"Should not be refused. Got: {res}"
    assert res.get("answer"), "Should have an answer"


def test_orchestrator_refuses_missing_coverage(doc_db):
    """Verify orchestrator still refuses when certified facts for the intent are absent."""
    orchestrator = AgentOrchestrator(db=doc_db, llm=MockLLM())
    res = orchestrator.answer_question(query="what is the delay risk in schedule", project_id="proj1")
    assert res.get("mode") == "refused", (
        f"Should be refused for missing schedule facts. Got mode={res.get('mode')}"
    )


def test_certified_document_facts_returned_without_snapshot_registry(doc_db_without_snapshot_registry):
    """Document trusted facts should still be retrievable when only the mounted fact layer has them."""
    db, snap_id = doc_db_without_snapshot_registry
    api = FactQueryAPI(db)
    result = api.get_certified_facts(
        query_intent="what is this document", project_id="proj1", snapshot_id=snap_id
    )
    assert result["has_certified_data"] is True
    assert result["count"] >= 3
    assert "document.page_count" in result.get("formatted_context", "")


def test_orchestrator_answers_supported_document_query_without_snapshot_registry(doc_db_without_snapshot_registry):
    """Live answer path must align with mounted validated document facts even without snapshot registry entries."""
    db, snap_id = doc_db_without_snapshot_registry
    orchestrator = AgentOrchestrator(db=db, llm=MockLLM())
    res = orchestrator.answer_question(
        query="what is this document", project_id="proj1", snapshot_id=snap_id
    )
    assert res.get("mode") != "refused", f"Should not be refused. Got: {res}"
    assert res.get("answer")


@pytest.fixture
def doc_db_with_semantic_scope_facts(tmp_path):
    """Project has trusted semantic document facts suitable for broad scope-summary questions."""
    db = DatabaseManager(root_dir=str(tmp_path), db_name=":memory:")
    base = Path("src/infra/persistence/migrations")
    db.execute_script(open(base / "001_baseline_v14.sql").read())
    v16 = base / "016_fix_missing_column.sql"
    if v16.exists():
        db.execute_script(open(v16).read())
    db.execute_script(open(base / "017_truth_engine_v2.sql").read())
    v18 = base / "018_fact_snapshots.sql"
    if v18.exists():
        db.execute_script(open(v18).read())

    snap_id = db.create_snapshot("proj1", status="VALIDATED")
    now = int(time.time())
    facts = [
        ("fs1", "document.requirement", '{"statement": "Contractor shall provide generator room ventilation"}'),
        ("fs2", "document.scope_item", '{"item": "Generator room is in scope"}'),
        ("fs3", "document.includes_component", '{"component": "underground diesel tank"}'),
    ]
    for fact_id, fact_type, value_json in facts:
        db.execute(
            """
            INSERT INTO facts
                (fact_id, project_id, fact_type, subject_kind, subject_id,
                 status, domain, created_at, updated_at, value_type,
                 as_of_json, method_id, value_json)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                fact_id, "proj1", fact_type, "document", "doc_scope",
                "VALIDATED", "DOC_CONTROL", now, now, "JSON",
                '{"file_version_id": "fv_doc_scope", "doc_id": "doc_scope"}', "m_scope", value_json,
            ),
        )
    db.project_id = "proj1"
    return db, snap_id


def test_broad_scope_summary_infers_semantic_document_fact_types(doc_db):
    api = FactQueryAPI(doc_db)
    for query in ("provide project scope summary", "summarize scope", "scope"):
        inferred = api._infer_fact_types(query)
        assert inferred[0] == "document.scope_item"
        assert "document.requirement" in inferred
        assert "document.includes_component" in inferred
        assert "document.design_obligation" in inferred


def test_coverage_gate_passes_for_broad_scope_summary_with_semantic_facts(doc_db_with_semantic_scope_facts):
    db, snap_id = doc_db_with_semantic_scope_facts
    gate = CoverageGate(db)
    result = gate.check("provide project scope summary", project_id="proj1", snapshot_id=snap_id)
    assert result["is_complete"] is True


def test_orchestrator_answers_broad_scope_summary_with_trusted_document_semantic_facts(doc_db_with_semantic_scope_facts):
    db, snap_id = doc_db_with_semantic_scope_facts
    orchestrator = AgentOrchestrator(db=db, llm=MockLLM())
    res = orchestrator.answer_question(
        query="provide project scope summary", project_id="proj1", snapshot_id=snap_id
    )
    assert res.get("mode") != "refused", f"Should not be refused. Got: {res}"
    assert res.get("answer")


def test_orchestrator_answers_broad_scope_summary_from_available_grounded_material_even_without_semantic_document_facts(doc_db):
    orchestrator = AgentOrchestrator(db=doc_db, llm=MockLLM())
    res = orchestrator.answer_question(
        query="provide project scope summary", project_id="proj1"
    )
    assert res.get("mode") == "answered"
    assert "## Trusted Facts" not in res.get("answer", "")
    details = res.get("answer_presentation", {}).get("details_copy_text", "")
    assert "## Trusted Facts" in details
    assert "Trusted coverage is partial" in details
