# -*- coding: utf-8 -*-
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.application.orchestrators.agent_orchestrator import AgentOrchestrator
from src.application.services.mounted_chat_runtime import run_mounted_chat_query
from src.infra.adapters.llm_service import LLMService
from src.infra.persistence.database_manager import DatabaseManager


class ProjectEchoLLM(LLMService):
    def __init__(self):
        self.model = "project-isolation-echo"

    def chat(self, messages, **kwargs):
        blob = "\n".join(str(m.get("content", "")) for m in messages if isinstance(m, dict))
        has_alpha = "Alpha Pump Room" in blob
        has_beta = "Beta Chiller Yard" in blob

        if has_alpha and has_beta:
            content = "LEAK DETECTED: Alpha Pump Room and Beta Chiller Yard both appeared."
        elif has_alpha:
            content = "The project scope includes Alpha Pump Room."
        elif has_beta:
            content = "The project scope includes Beta Chiller Yard."
        else:
            content = "No project-specific scope item was found."

        return {"choices": [{"message": {"content": content}}]}


def _build_truth_db(root_dir: Path) -> DatabaseManager:
    root_dir.mkdir(parents=True, exist_ok=True)
    db = DatabaseManager(root_dir=str(root_dir), db_name=":memory:")

    migrations = Path("src/infra/persistence/migrations")
    db.execute_script((migrations / "001_baseline_v14.sql").read_text(encoding="utf-8-sig"))

    v16 = migrations / "016_fix_missing_column.sql"
    if v16.exists():
        db.execute_script(v16.read_text(encoding="utf-8-sig"))

    db.execute_script((migrations / "017_truth_engine_v2.sql").read_text(encoding="utf-8-sig"))

    v18 = migrations / "018_fact_snapshots.sql"
    if v18.exists():
        db.execute_script(v18.read_text(encoding="utf-8-sig"))

    return db


def _insert_trusted_project_fact(db: DatabaseManager, *, project_id: str, fact_id: str, statement: str) -> None:
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
            fact_id,
            project_id,
            "document.requirement",
            "document",
            f"{project_id}_scope_doc",
            "VALIDATED",
            "DOC_CONTROL",
            now,
            now,
            "TEXT",
            "{}",
            "project_isolation_test",
            '{"statement": "%s"}' % statement,
        ),
    )


def _combined_answer_payload(result):
    presentation = result.get("answer_presentation") or {}
    parts = [
        str(result.get("answer", "")),
        str(presentation.get("source_basis_banner", "")),
        str(presentation.get("details_copy_text", "")),
    ]
    return "\n".join(parts)


def test_mounted_runtime_filters_mutually_exclusive_project_facts_in_shared_store(tmp_path):
    db = _build_truth_db(tmp_path / "SharedProjectStore" / ".serapeum")

    _insert_trusted_project_fact(
        db,
        project_id="ProjectA",
        fact_id="fact_alpha",
        statement="Alpha Pump Room",
    )
    _insert_trusted_project_fact(
        db,
        project_id="ProjectB",
        fact_id="fact_beta",
        statement="Beta Chiller Yard",
    )

    orchestrator = AgentOrchestrator(db=db, llm=ProjectEchoLLM())

    controller_a = SimpleNamespace(
        active_project_id="ProjectA",
        orchestrator=orchestrator,
        job_manager=None,
    )
    result_a = run_mounted_chat_query(controller_a, "provide project scope summary")
    payload_a = _combined_answer_payload(result_a)

    assert result_a["mode"] == "answered"
    assert "Alpha Pump Room" in payload_a
    assert "Beta Chiller Yard" not in payload_a
    assert "LEAK DETECTED" not in payload_a

    controller_b = SimpleNamespace(
        active_project_id="ProjectB",
        orchestrator=orchestrator,
        job_manager=None,
    )
    result_b = run_mounted_chat_query(controller_b, "provide project scope summary")
    payload_b = _combined_answer_payload(result_b)

    assert result_b["mode"] == "answered"
    assert "Beta Chiller Yard" in payload_b
    assert "Alpha Pump Room" not in payload_b
    assert "LEAK DETECTED" not in payload_b


def test_mounted_runtime_isolates_two_project_roots_with_exclusive_facts(tmp_path):
    db_a = _build_truth_db(tmp_path / "ProjectA" / ".serapeum")
    db_b = _build_truth_db(tmp_path / "ProjectB" / ".serapeum")

    _insert_trusted_project_fact(
        db_a,
        project_id="ProjectA",
        fact_id="fact_alpha_root",
        statement="Alpha Pump Room",
    )
    _insert_trusted_project_fact(
        db_b,
        project_id="ProjectB",
        fact_id="fact_beta_root",
        statement="Beta Chiller Yard",
    )

    controller_a = SimpleNamespace(
        active_project_id="ProjectA",
        orchestrator=AgentOrchestrator(db=db_a, llm=ProjectEchoLLM()),
        job_manager=None,
    )
    result_a = run_mounted_chat_query(controller_a, "provide project scope summary")
    payload_a = _combined_answer_payload(result_a)

    assert result_a["mode"] == "answered"
    assert "Alpha Pump Room" in payload_a
    assert "Beta Chiller Yard" not in payload_a

    controller_b = SimpleNamespace(
        active_project_id="ProjectB",
        orchestrator=AgentOrchestrator(db=db_b, llm=ProjectEchoLLM()),
        job_manager=None,
    )
    result_b = run_mounted_chat_query(controller_b, "provide project scope summary")
    payload_b = _combined_answer_payload(result_b)

    assert result_b["mode"] == "answered"
    assert "Beta Chiller Yard" in payload_b
    assert "Alpha Pump Room" not in payload_b


def test_mounted_runtime_missing_project_still_returns_project_unavailable():
    controller = SimpleNamespace(
        active_project_id=None,
        orchestrator=AgentOrchestrator(db=_build_truth_db(Path(".serapeum_test_unused")), llm=ProjectEchoLLM()),
        job_manager=None,
    )

    result = run_mounted_chat_query(controller, "provide project scope summary")

    assert result["mode"] == "error"
    assert result["compliance_status"] == "PROJECT_UNAVAILABLE"
    assert "No active project is loaded" in result["answer"]
