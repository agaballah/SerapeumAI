from __future__ import annotations

import decimal
import importlib
import json
import sys

from src.application.tools.calculator_tool import TOOL_ID as CALCULATOR_TOOL_ID


EXPECTED_PUBLIC_EXPORTS = sorted(
    [
        "ChatToolBridgeContractError",
        "ChatToolBridgeResult",
        "ToolExecutionOrchestrationResult",
        "ToolExecutionOrchestratorContractError",
        "ToolRequestAdapterContractError",
        "ToolRequestAdapterResult",
        "ToolUsePresentation",
        "ToolUsePresentationContractError",
        "adapt_tool_request",
        "build_chat_tool_bridge_envelope",
        "execute_tool_with_audit",
        "present_tool_adapter_result",
        "present_tool_orchestration_result",
    ]
)


LAZY_TARGETS = {
    "src.application.tools.chat_tool_bridge",
    "src.application.tools.tool_execution_orchestrator",
    "src.application.tools.tool_request_adapter",
    "src.application.tools.tool_use_presentation",
}


def _purge_tool_package_and_lazy_targets() -> None:
    for module_name in ["src.application.tools", *sorted(LAZY_TARGETS)]:
        sys.modules.pop(module_name, None)


def test_plain_package_import_stays_lazy_and_side_effect_light():
    _purge_tool_package_and_lazy_targets()

    tools = importlib.import_module("src.application.tools")

    assert tools.__all__ == EXPECTED_PUBLIC_EXPORTS
    for module_name in LAZY_TARGETS:
        assert module_name not in sys.modules


def test_plain_package_import_does_not_mutate_decimal_precision():
    _purge_tool_package_and_lazy_targets()

    original_precision = decimal.getcontext().prec
    decimal.getcontext().prec = 17
    try:
        tools = importlib.import_module("src.application.tools")

        assert tools.__all__ == EXPECTED_PUBLIC_EXPORTS
        assert decimal.getcontext().prec == 17
    finally:
        decimal.getcontext().prec = original_precision


def test_bridge_export_builds_ready_envelope_without_orchestrator_execution_path():
    _purge_tool_package_and_lazy_targets()

    tools = importlib.import_module("src.application.tools")
    result = tools.build_chat_tool_bridge_envelope(
        {
            "request_id": "req-bridge-consolidation",
            "tool_id": CALCULATOR_TOOL_ID,
            "arguments": {"operation": "add", "operands": [1, 2]},
            "correlation_id": "chat-bridge-consolidation",
            "requested_by": "bridge_consolidation_gate",
            "consent_granted": False,
        }
    ).to_dict()

    assert result["status"] == "ready"
    assert result["executed"] is False
    assert result["can_govern_truth"] is False
    assert result["tool_id"] == CALCULATOR_TOOL_ID
    assert "src.application.tools.chat_tool_bridge" in sys.modules
    assert "src.application.tools.tool_execution_orchestrator" not in sys.modules
    assert json.loads(json.dumps(result, sort_keys=True)) == result


def test_bridge_rejects_success_status_because_it_never_executes():
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


def test_bridge_clarification_and_error_outputs_remain_json_safe_and_non_truth_governing():
    from src.application.tools import build_chat_tool_bridge_envelope

    clarification = build_chat_tool_bridge_envelope(
        {
            "request_id": "req-missing-tool",
            "arguments": {},
            "consent_granted": False,
        }
    ).to_dict()

    error = build_chat_tool_bridge_envelope(
        {
            "request_id": "req-bad-arguments",
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


def test_no_chat_ui_router_llm_parser_agent_or_persistence_symbols_are_exported():
    import src.application.tools as tools

    forbidden_names = {
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

    for name in forbidden_names:
        assert name not in tools.__all__
        try:
            getattr(tools, name)
        except AttributeError:
            pass
        else:
            raise AssertionError(f"Forbidden symbol was exported: {name}")
