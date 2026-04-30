# -*- coding: utf-8 -*-
import time
from pathlib import Path

import pytest

from src.application.orchestrators.agent_orchestrator import AgentOrchestrator
from src.infra.adapters.llm_service import LLMService
from src.infra.persistence.database_manager import DatabaseManager


@pytest.fixture
def lane_db(tmp_path):
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

    def chat(self, messages, **kwargs):
        return {"choices": [{"message": {"content": "Synthesized scope indicates generator room ventilation is required."}}]}


def _insert_fact(db, *, fact_id, fact_type, value_json, status="VALIDATED"):
    now = int(time.time())
    db.execute(
        "INSERT OR IGNORE INTO file_registry (file_id, project_id, first_seen_path, created_at) VALUES (?, ?, ?, ?)",
        ("file1", "proj1", "C:/proj/Scope.pdf", now),
    )
    db.execute(
        "INSERT OR IGNORE INTO file_versions (file_version_id, file_id, sha256, size_bytes, file_ext, imported_at, source_path) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("fv1", "file1", "abc", 100, ".pdf", now, "C:/proj/Scope.pdf"),
    )
    db.execute(
        """
        INSERT INTO facts
            (fact_id, project_id, fact_type, subject_kind, subject_id,
             status, domain, created_at, updated_at, value_type,
             as_of_json, method_id, value_json)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (fact_id, "proj1", fact_type, "document", "doc1", status, "DOC_CONTROL", now, now, "TEXT", "{}", "m1", value_json),
    )
    db.execute(
        """
        INSERT INTO fact_inputs (fact_id, file_version_id, location_json, input_kind)
        VALUES (?, ?, ?, ?)
        """,
        (fact_id, "fv1", '{"page_index": 0}', "builder_input"),
    )


def _insert_doc_page(db, *, text, page_summary=None):
    now = int(time.time())
    db.execute(
        "INSERT INTO documents (doc_id, project_id, file_name, abs_path, file_ext, created, updated) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("doc1", "proj1", "Scope.pdf", "C:/proj/Scope.pdf", ".pdf", now, now),
    )
    db.execute(
        "INSERT INTO file_registry (file_id, project_id, first_seen_path, created_at) VALUES (?, ?, ?, ?)",
        ("file1", "proj1", "C:/proj/Scope.pdf", now),
    )
    db.execute(
        "INSERT INTO file_versions (file_version_id, file_id, sha256, size_bytes, file_ext, imported_at, source_path) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("fv1", "file1", "abc", 100, ".pdf", now, "C:/proj/Scope.pdf"),
    )
    db.execute(
        """
        INSERT INTO pages (doc_id, page_index, py_text_extracted, py_text_len, py_text, ocr_text, page_summary_short, page_summary_detailed, updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("doc1", 0, 1, len(text), text, "", page_summary or "", page_summary or "", now),
    )


def test_answer_includes_trusted_facts_section_when_trusted_document_facts_exist(lane_db):
    _insert_fact(lane_db, fact_id="f1", fact_type="document.requirement", value_json='{"statement": "Provide generator room ventilation"}')
    orchestrator = AgentOrchestrator(db=lane_db, llm=MockLLM())
    result = orchestrator.answer_question(query="provide project scope summary", project_id="proj1")
    assert result["mode"] == "answered"
    assert "Support-only answer" not in result["answer"]
    assert result["answer_presentation"]["summary_block"]["source_label"] == "Trusted Facts"
    assert "## Trusted Facts" not in result["answer"]
    assert "generator room ventilation" in result["answer"].lower()
    assert "## Trusted Facts" in result["answer_presentation"]["details_copy_text"]
    assert "[Trusted Fact]" in result["answer_presentation"]["details_copy_text"]


def test_answer_uses_extracted_evidence_when_trusted_facts_are_missing(lane_db):
    _insert_doc_page(lane_db, text="The project scope includes the generator room and underground diesel tank.")
    orchestrator = AgentOrchestrator(db=lane_db, llm=MockLLM())
    result = orchestrator.answer_question(query="scope", project_id="proj1")
    assert result["mode"] == "answered"
    assert "Support-only answer" in result["answer"]
    assert "not yet certified as trusted fact" in result["answer"]
    assert result["answer_presentation"]["source_basis_banner"].startswith("Support-only answer")
    assert "## Trusted Facts" not in result["answer"]
    assert "generator room" in result["answer"].lower()
    assert "No trusted facts found for this question." in result["answer_presentation"]["details_copy_text"]
    assert "## Direct Answer\nSupport-only answer" in result["answer_presentation"]["details_copy_text"]
    assert "## Extracted Evidence" in result["answer_presentation"]["details_copy_text"]


def test_answer_labels_ai_generated_synthesis_as_non_governing(lane_db):
    _insert_doc_page(lane_db, text="The project scope includes the generator room.", page_summary="AI summary mentions generator room ventilation.")
    orchestrator = AgentOrchestrator(db=lane_db, llm=MockLLM())
    result = orchestrator.answer_question(query="provide project scope summary", project_id="proj1")
    assert result["mode"] == "answered"
    assert "Support-only answer" in result["answer"]
    assert "not yet certified as trusted fact" in result["answer"]
    assert "AI-generated non-governing synthesis" in result["answer_presentation"]["source_basis_banner"]
    assert "generator room ventilation" in result["answer"].lower()
    assert "## AI-Generated Synthesis" in result["answer_presentation"]["details_copy_text"]
    assert "non-governing" in result["answer_presentation"]["details_copy_text"]
    assert "Synthesized scope indicates generator room ventilation is required." in result["answer_presentation"]["details_copy_text"]
