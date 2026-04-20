# -*- coding: utf-8 -*-
import time
from pathlib import Path

import pytest

from src.application.api.fact_api import FactQueryAPI
from src.application.orchestrators.agent_orchestrator import AgentOrchestrator
from src.application.services.coverage_gate import CoverageGate
from src.domain.facts.authority_service import AuthorityService
from src.domain.facts.models import (
    AI_GENERATED_PROVENANCE,
    FactStatus,
    TRUSTED_FACT_STATUSES,
    is_trusted_fact_status,
)
from src.infra.adapters.llm_service import LLMService
from src.infra.persistence.database_manager import DatabaseManager


@pytest.fixture
def truth_db(tmp_path):
    db = DatabaseManager(root_dir=str(tmp_path), db_name=":memory:")
    base = Path("src/infra/persistence/migrations")
    db.execute_script((base / "001_baseline_v14.sql").read_text())
    v16 = base / "016_fix_missing_column.sql"
    if v16.exists():
        db.execute_script(v16.read_text())
    db.execute_script((base / "017_truth_engine_v2.sql").read_text())
    v18 = base / "018_fact_snapshots.sql"
    if v18.exists():
        db.execute_script(v18.read_text())
    db.project_id = "proj1"
    return db


class MockLLM(LLMService):
    def __init__(self):
        self.model = "mock"

    def chat_json(self, system, user, **kwargs):
        return {"answer": "mock", "citations": []}

    def chat(self, messages, **kwargs):
        return {"choices": [{"message": {"content": "mock"}}]}


def _insert_fact(db, *, fact_id, fact_type, status, subject_id="doc1", subject_kind="document", as_of_json="{}", domain="DOC_CONTROL"):
    now = int(time.time())
    db.execute(
        """
        INSERT INTO facts
            (fact_id, project_id, fact_type, subject_kind, subject_id,
             status, domain, created_at, updated_at, value_type,
             as_of_json, method_id, value_json)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            fact_id, "proj1", fact_type, subject_kind, subject_id,
            status, domain, now, now, "TEXT", as_of_json, "test_method", '"value"'
        ),
    )


def test_trusted_state_contract_constants():
    assert FactStatus.VALIDATED.value in TRUSTED_FACT_STATUSES
    assert FactStatus.HUMAN_CERTIFIED.value in TRUSTED_FACT_STATUSES
    assert FactStatus.CANDIDATE.value not in TRUSTED_FACT_STATUSES
    assert AI_GENERATED_PROVENANCE not in TRUSTED_FACT_STATUSES
    assert is_trusted_fact_status("VALIDATED") is True
    assert is_trusted_fact_status("HUMAN_CERTIFIED") is True
    assert is_trusted_fact_status("CANDIDATE") is False
    assert is_trusted_fact_status("AI_GENERATED") is False


def test_authority_service_rejects_non_trusted_cert_type(truth_db):
    _insert_fact(truth_db, fact_id="f1", fact_type="schedule.activity", status="CANDIDATE", subject_id="A101", subject_kind="activity", domain="SCHEDULE")
    auth = AuthorityService(truth_db)

    assert auth.authorize_certificate("f1", "PLANNER", cert_type="CANDIDATE") is False
    row = truth_db.execute("SELECT status FROM facts WHERE fact_id = ?", ("f1",)).fetchone()
    assert row["status"] == "CANDIDATE"

    assert auth.authorize_certificate("f1", "PLANNER") is True
    row = truth_db.execute("SELECT status FROM facts WHERE fact_id = ?", ("f1",)).fetchone()
    assert row["status"] == FactStatus.HUMAN_CERTIFIED.value


def test_coverage_gate_counts_human_certified_as_trusted(truth_db):
    snap_id = truth_db.create_snapshot("proj1", status="VALIDATED")
    for fact_id, fact_type in (
        ("f_doc_hc_pg", "document.page_count"),
        ("f_doc_hc_txt", "document.has_text"),
        ("f_doc_hc_prof", "document.profile"),
    ):
        _insert_fact(
            truth_db,
            fact_id=fact_id,
            fact_type=fact_type,
            status=FactStatus.HUMAN_CERTIFIED.value,
            as_of_json='{"snapshot_id": "%s"}' % snap_id,
        )
        truth_db.execute("INSERT INTO fact_snapshot_registry (snapshot_id, fact_id) VALUES (?, ?)", (snap_id, fact_id))
    gate = CoverageGate(truth_db)
    result = gate.check("what is this document", project_id="proj1", snapshot_id=snap_id)
    assert result["is_complete"] is True


def test_fact_api_returns_human_certified_document_fact(truth_db):
    snap_id = truth_db.create_snapshot("proj1", status="VALIDATED")
    _insert_fact(
        truth_db,
        fact_id="f_doc_hc2",
        fact_type="document.profile",
        status=FactStatus.HUMAN_CERTIFIED.value,
        as_of_json='{"snapshot_id": "%s"}' % snap_id,
    )
    truth_db.execute("INSERT INTO fact_snapshot_registry (snapshot_id, fact_id) VALUES (?, ?)", (snap_id, "f_doc_hc2"))
    api = FactQueryAPI(truth_db)
    result = api.get_certified_facts("what is this document", project_id="proj1", snapshot_id=snap_id)
    assert result["has_certified_data"] is True
    assert any(f["status"] == FactStatus.HUMAN_CERTIFIED.value for f in result["facts"])


def test_orchestrator_refuses_when_no_project_grounded_material_exists(truth_db, monkeypatch):
    _insert_fact(truth_db, fact_id="f_doc", fact_type="document.page_count", status=FactStatus.VALIDATED.value)
    orchestrator = AgentOrchestrator(db=truth_db, llm=MockLLM())

    called = {"candidate": False}

    def _fake_candidate(*args, **kwargs):
        called["candidate"] = True
        return {
            "has_candidate_data": True,
            "formatted_context": "[AI-GENERATED CANDIDATE SUPPORT - NOT ANSWER-GOVERNING]",
            "facts": [{"fact_id": "cand1", "method_id": "query_derivation_v1", "governs_answers": False}],
        }

    monkeypatch.setattr(orchestrator, "_derive_candidate_facts_from_evidence", _fake_candidate)

    result = orchestrator.answer_question(query="what is the weather", project_id="proj1")
    assert result["mode"] == "refused"
    assert result["compliance_status"] == "NO_PROJECT_GROUNDED_MATERIAL"
    assert called["candidate"] is False
    assert result["supporting_only"] is True
    assert result["support_facts"] == []


def test_coverage_gap_wording_is_precise_when_other_trusted_facts_exist(truth_db):
    _insert_fact(truth_db, fact_id="f_doc", fact_type="document.page_count", status=FactStatus.VALIDATED.value)
    gate = CoverageGate(truth_db)
    result = gate.check("what is the delay risk in schedule", project_id="proj1")
    assert result["is_complete"] is False
    assert "No certified facts have been built" not in result["refusal_message"]
    assert "Trusted facts exist for this project" in result["refusal_message"]


def test_orchestrator_no_grounded_material_wording_is_specific(truth_db, monkeypatch):
    _insert_fact(truth_db, fact_id="f_doc", fact_type="document.page_count", status=FactStatus.VALIDATED.value)
    orchestrator = AgentOrchestrator(db=truth_db, llm=MockLLM())

    monkeypatch.setattr(orchestrator.fact_api, "get_certified_facts", lambda *args, **kwargs: {
        "facts": [], "count": 0, "has_certified_data": False, "formatted_context": "", "conflicts": []
    })

    result = orchestrator.answer_question(query="what is the weather", project_id="proj1")
    assert result["mode"] == "refused"
    assert result["compliance_status"] == "NO_PROJECT_GROUNDED_MATERIAL"
    assert "meaningful project-grounded material" in result["answer"]
    assert "current project state" not in result["answer"]


def test_broad_scope_summary_refusal_is_precise_when_only_base_document_facts_exist(truth_db):
    _insert_fact(truth_db, fact_id="f_doc_pg", fact_type="document.page_count", status=FactStatus.VALIDATED.value)
    gate = CoverageGate(truth_db)
    result = gate.check("provide project scope summary", project_id="proj1")
    assert result["is_complete"] is False
    assert "document.semantic_any" in str(result.get("missing_fact_types", []))
    assert "Trusted facts exist for this project" in result["refusal_message"]
    assert "No trusted facts in the governing states" not in result["refusal_message"]
