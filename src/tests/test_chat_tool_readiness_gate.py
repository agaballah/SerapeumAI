from __future__ import annotations

import importlib
import json
import sys

from src.application.tools.calculator_tool import TOOL_ID as CALCULATOR_TOOL_ID


FORBIDDEN_EXPORTS = {
    "chat_page",
    "chat_panel",
    "tool_router",
    "autonomous_tool_router",
    "parse_llm_tool_call",
    "llm_tool_call",
    "mcp",
    "agent_loop",
    "audit_persistence",
    "certify_fact",
    "candidate_fact",
}


LAZY_TARGETS = {
    "src.application.tools.chat_tool_bridge",
    "src.application.tools.tool_execution_orchestrator",
    "src.application.tools.tool_request_adapter",
    "src.application.tools.tool_use_presentation",
}


FORBIDDEN_UI_OR_ROUTING_MODULES = {
    "src.ui.pages.chat_page",
    "src.ui.chat_page",
    "src.application.chat",
    "src.application.chat.tool_router",
    "src.application.tools.autonomous_tool_router",
    "src.application.tools.llm_tool_call_parser",
    "src.application.tools.mcp",
    "src.application.tools.agent_loop",
}


def _purge_modules() -> None:
    for module_name in [
        "src.application.tools",
        *sorted(LAZY_TARGETS),
        *sorted(FORBIDDEN_UI_OR_ROUTING_MODULES),
    ]:
        sys.modules.pop(module_name, None)


def _valid_payload() -> dict[str, object]:
    return {
        "request_id": "req-chat-tool-readiness",
        "tool_id": CALCULATOR_TOOL_ID,
        "arguments": {"operation": "add", "operands": [1, 2]},
        "correlation_id": "chat-readiness-gate",
        "requested_by": "chat_tool_readiness_gate",
        "consent_granted": False,
    }


def test_chat_tool_bridge_is_exported_but_plain_package_import_is_lazy():
    _purge_modules()

    tools = importlib.import_module("src.application.tools")

    assert "build_chat_tool_bridge_envelope" in tools.__all__
    assert "ChatToolBridgeResult" in tools.__all__
    for module_name in LAZY_TARGETS:
        assert module_name not in sys.modules


def test_readiness_gate_builds_bridge_envelope_without_execution_or_orchestrator():
    _purge_modules()

    tools = importlib.import_module("src.application.tools")
    result = tools.build_chat_tool_bridge_envelope(_valid_payload()).to_dict()

    assert result["status"] == "ready"
    assert result["executed"] is False
    assert result["can_govern_truth"] is False
    assert result["tool_id"] == CALCULATOR_TOOL_ID
    assert json.loads(json.dumps(result, sort_keys=True)) == result

    assert "src.application.tools.chat_tool_bridge" in sys.modules
    assert "src.application.tools.tool_request_adapter" in sys.modules
    assert "src.application.tools.tool_use_presentation" in sys.modules
    assert "src.application.tools.tool_execution_orchestrator" not in sys.modules


def test_readiness_gate_rejects_success_status_for_non_executing_bridge():
    from src.application.tools import ChatToolBridgeResult

    result = ChatToolBridgeResult(
        status="success",
        adapter_result={"status": "ready", "can_govern_truth": False},
        presentation={"status": "ready", "can_govern_truth": False},
    )

    try:
        result.to_dict()
    except Exception as exc:
        assert "status is not an approved bridge status" in str(exc)
    else:
        raise AssertionError("Expected non-executing bridge to reject success status.")


def test_chat_tool_bridge_is_not_ui_or_autonomous_router_wiring():
    _purge_modules()

    tools = importlib.import_module("src.application.tools")
    _ = tools.build_chat_tool_bridge_envelope(_valid_payload()).to_dict()

    for module_name in FORBIDDEN_UI_OR_ROUTING_MODULES:
        assert module_name not in sys.modules

    for name in FORBIDDEN_EXPORTS:
        assert name not in tools.__all__
        try:
            getattr(tools, name)
        except AttributeError:
            pass
        else:
            raise AssertionError(f"Forbidden symbol was exported: {name}")


def test_readiness_gate_handles_clarification_and_error_without_truth_governance():
    from src.application.tools import build_chat_tool_bridge_envelope

    clarification = build_chat_tool_bridge_envelope(
        {
            "request_id": "req-readiness-missing-tool",
            "arguments": {},
            "consent_granted": False,
        }
    ).to_dict()

    error = build_chat_tool_bridge_envelope(
        {
            "request_id": "req-readiness-bad-arguments",
            "tool_id": CALCULATOR_TOOL_ID,
            "arguments": ["bad"],
            "consent_granted": False,
        }
    ).to_dict()

    assert clarification["status"] == "clarification"
    assert clarification["executed"] is False
    assert clarification["can_govern_truth"] is False
    assert json.loads(json.dumps(clarification, sort_keys=True)) == clarification

    assert error["status"] == "error"
    assert error["executed"] is False
    assert error["can_govern_truth"] is False
    assert json.loads(json.dumps(error, sort_keys=True)) == error
