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


def test_plain_package_import_does_not_eagerly_load_bridge_or_other_lazy_targets():
    _purge_tool_package_and_lazy_targets()

    imported_tools = importlib.import_module("src.application.tools")

    assert imported_tools.__all__ == EXPECTED_PUBLIC_EXPORTS
    for module_name in LAZY_TARGETS:
        assert module_name not in sys.modules


def test_plain_package_import_does_not_mutate_decimal_precision():
    _purge_tool_package_and_lazy_targets()

    original_precision = decimal.getcontext().prec
    decimal.getcontext().prec = 15
    try:
        imported_tools = importlib.import_module("src.application.tools")

        assert imported_tools.__all__ == EXPECTED_PUBLIC_EXPORTS
        assert decimal.getcontext().prec == 15
    finally:
        decimal.getcontext().prec = original_precision


def test_bridge_public_symbols_import_through_package_boundary():
    from src.application.tools import (
        ChatToolBridgeContractError,
        ChatToolBridgeResult,
        build_chat_tool_bridge_envelope,
    )
    from src.application.tools.chat_tool_bridge import (
        ChatToolBridgeContractError as DirectError,
        ChatToolBridgeResult as DirectResult,
        build_chat_tool_bridge_envelope as direct_build,
    )

    assert ChatToolBridgeContractError is DirectError
    assert ChatToolBridgeResult is DirectResult
    assert build_chat_tool_bridge_envelope is direct_build


def test_bridge_import_through_package_boundary_builds_non_executing_envelope():
    from src.application.tools import build_chat_tool_bridge_envelope

    result = build_chat_tool_bridge_envelope(
        {
            "request_id": "req-bridge-export-001",
            "tool_id": CALCULATOR_TOOL_ID,
            "arguments": {"operation": "add", "operands": [1, 2]},
            "correlation_id": "chat-bridge-export-001",
            "requested_by": "bridge_export_test",
            "consent_granted": False,
        }
    ).to_dict()

    assert result["status"] == "ready"
    assert result["tool_id"] == CALCULATOR_TOOL_ID
    assert result["executed"] is False
    assert result["can_govern_truth"] is False
    assert json.loads(json.dumps(result, sort_keys=True)) == result


def test_bridge_export_access_does_not_load_orchestrator():
    _purge_tool_package_and_lazy_targets()

    imported_tools = importlib.import_module("src.application.tools")
    assert "src.application.tools.tool_execution_orchestrator" not in sys.modules

    result = imported_tools.build_chat_tool_bridge_envelope(
        {
            "request_id": "req-bridge-export-lazy",
            "tool_id": CALCULATOR_TOOL_ID,
            "arguments": {"operation": "add", "operands": [1, 2]},
            "correlation_id": "chat-bridge-export-lazy",
            "requested_by": "bridge_export_test",
            "consent_granted": False,
        }
    ).to_dict()

    assert result["status"] == "ready"
    assert "src.application.tools.chat_tool_bridge" in sys.modules
    assert "src.application.tools.tool_request_adapter" in sys.modules
    assert "src.application.tools.tool_use_presentation" in sys.modules
    assert "src.application.tools.tool_execution_orchestrator" not in sys.modules


def test_private_bridge_helpers_are_not_exported():
    import src.application.tools as tools

    forbidden_names = {
        "_from_mapping",
        "_string_or_none",
        "_string_or_default",
        "_BRIDGE_EXPORTS",
    }

    for name in forbidden_names:
        assert name not in tools.__all__


def test_no_chat_ui_router_llm_parser_or_agent_symbols_are_exported():
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
