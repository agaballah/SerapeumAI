# -*- coding: utf-8 -*-
"""
test_chat_project_isolation.py

Packet 6: Project isolation / chat session residue closure.

Locks release-critical chat behavior:

- A response created for an old chat token must not be delivered after reset.
- A response created for Project A must not be delivered after Project B becomes active.
- Late worker errors must be dropped under the same token/project guard.
- Mounted chat runtime always uses the active project and does not accept stale snapshot UI state.
"""

from types import SimpleNamespace

from src.application.services.mounted_chat_runtime import run_mounted_chat_query
from src.ui.pages.chat_page import ChatPage


def _chat_shell(active_project_id="ProjectA", token=0):
    chat = object.__new__(ChatPage)
    chat._chat_session_token = token
    chat.controller = SimpleNamespace(active_project_id=active_project_id)
    chat.messages = []

    def _capture(sender, text, **_kwargs):
        chat.messages.append((sender, text))

    chat.add_message = _capture
    return chat


def test_current_chat_request_accepts_matching_token_and_project():
    chat = _chat_shell(active_project_id="ProjectA", token=7)

    assert chat._is_current_chat_request(7, "ProjectA") is True


def test_current_chat_request_rejects_old_session_token():
    chat = _chat_shell(active_project_id="ProjectA", token=8)

    assert chat._is_current_chat_request(7, "ProjectA") is False


def test_current_chat_request_rejects_old_project_response_after_project_change():
    chat = _chat_shell(active_project_id="ProjectB", token=7)

    assert chat._is_current_chat_request(7, "ProjectA") is False


def test_late_chat_worker_error_is_dropped_after_project_change():
    chat = _chat_shell(active_project_id="ProjectB", token=3)

    chat._deliver_chat_error(3, "ProjectA", RuntimeError("late old-project failure"))

    assert chat.messages == []


def test_late_chat_worker_error_is_dropped_after_session_reset():
    chat = _chat_shell(active_project_id="ProjectA", token=4)

    chat._deliver_chat_error(3, "ProjectA", RuntimeError("late old-token failure"))

    assert chat.messages == []


def test_current_chat_worker_error_is_delivered_for_current_project_and_token():
    chat = _chat_shell(active_project_id="ProjectA", token=4)

    chat._deliver_chat_error(4, "ProjectA", RuntimeError("current failure"))

    assert chat.messages == [("System", "Error: current failure")]


class _RecorderOrchestrator:
    def __init__(self):
        self.calls = []

    def answer_question(self, *, query, project_id, snapshot_id=None):
        self.calls.append(
            {
                "query": query,
                "project_id": project_id,
                "snapshot_id": snapshot_id,
            }
        )
        return {
            "answer": f"answer for {project_id}",
            "mode": "answered",
            "citations": [],
            "support_facts": [],
        }


def test_mounted_chat_runtime_uses_active_project_and_no_snapshot_ui_state():
    orchestrator = _RecorderOrchestrator()
    controller = SimpleNamespace(
        active_project_id="ProjectB",
        orchestrator=orchestrator,
        job_manager=None,
    )

    result = run_mounted_chat_query(controller, "what is this document?")

    assert result["answer"] == "answer for ProjectB"
    assert orchestrator.calls == [
        {
            "query": "what is this document?",
            "project_id": "ProjectB",
            "snapshot_id": None,
        }
    ]


def test_mounted_chat_runtime_refuses_without_active_project():
    controller = SimpleNamespace(
        active_project_id=None,
        orchestrator=_RecorderOrchestrator(),
        job_manager=None,
    )

    result = run_mounted_chat_query(controller, "hello")

    assert result["mode"] == "error"
    assert result["compliance_status"] == "PROJECT_UNAVAILABLE"
    assert "No active project" in result["answer"]
