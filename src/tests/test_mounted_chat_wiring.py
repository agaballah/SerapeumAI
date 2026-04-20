from __future__ import annotations

from pathlib import Path

from src.application.services.mounted_chat_runtime import run_mounted_chat_query


class _FakeOrchestrator:
    def __init__(self):
        self.calls = []

    def answer_question(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "answer": "This project includes demo scope work.",
            "answer_presentation": {
                "main_answer_text": "This project includes demo scope work.",
                "details_copy_text": "## Trusted Facts\n- document.scope_item: demo\n\n## Extracted Evidence\n- deterministic extraction: demo",
            },
            "citations": [],
            "support_facts": [],
            "mode": "answered",
            "source_lanes": {"trusted_facts": 1, "extracted_evidence": 1},
        }


class _Controller:
    def __init__(self, orchestrator=None, active_project_id=None):
        self.orchestrator = orchestrator
        self.active_project_id = active_project_id
        self.selected_snapshot_id = "SHOULD_NOT_BE_USED"

    def get_selected_snapshot_id(self):
        raise AssertionError("mounted chat wiring must not use informational snapshot selection")


def test_mounted_chat_runtime_calls_orchestrator_with_active_project_and_no_snapshot():
    orch = _FakeOrchestrator()
    controller = _Controller(orchestrator=orch, active_project_id="ProjectA")

    result = run_mounted_chat_query(controller, "SCOPE")

    assert orch.calls == [{"query": "SCOPE", "project_id": "ProjectA", "snapshot_id": None}]
    assert result["answer"] == "This project includes demo scope work."
    assert "## Trusted Facts" in result["answer_presentation"]["details_copy_text"]
    assert "## Extracted Evidence" in result["answer_presentation"]["details_copy_text"]


def test_mounted_chat_runtime_reports_missing_project_cleanly():
    orch = _FakeOrchestrator()
    controller = _Controller(orchestrator=orch, active_project_id=None)

    result = run_mounted_chat_query(controller, "SCOPE")

    assert result["mode"] == "error"
    assert "No active project is loaded" in result["answer"]
    assert orch.calls == []


def test_chat_page_is_wired_to_mounted_runtime_helper():
    source = Path("src/ui/pages/chat_page.py").read_text(encoding="utf-8")
    assert "run_mounted_chat_query" in source
    send_block = source.split("def send_message", 1)[1].split("def add_message", 1)[0]
    assert "self.controller.orchestrator.answer_question(" not in send_block
