from __future__ import annotations

import decimal
import importlib
import json
import sys

from src.application.tools.calculator_tool import TOOL_ID as CALCULATOR_TOOL_ID


EXPECTED_PUBLIC_EXPORTS = sorted(
    [
        "ToolExecutionOrchestrationResult",
        "ToolExecutionOrchestratorContractError",
        "ToolRequestAdapterContractError",
        "ToolRequestAdapterResult",
        "ChatToolBridgeContractError",
        "ChatToolBridgeResult",
        "build_chat_tool_bridge_envelope",
        "ToolUsePresentation",
        "ToolUsePresentationContractError",
        "adapt_tool_request",
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


def test_plain_package_import_is_side_effect_light_and_lazy():
    _purge_tool_package_and_lazy_targets()

    tools = importlib.import_module("src.application.tools")

    assert tools.__all__ == EXPECTED_PUBLIC_EXPORTS
    for module_name in LAZY_TARGETS:
        assert module_name not in sys.modules


def test_plain_package_import_does_not_mutate_decimal_precision():
    _purge_tool_package_and_lazy_targets()

    original_precision = decimal.getcontext().prec
    decimal.getcontext().prec = 13
    try:
        tools = importlib.import_module("src.application.tools")

        assert tools.__all__ == EXPECTED_PUBLIC_EXPORTS
        assert decimal.getcontext().prec == 13
    finally:
        decimal.getcontext().prec = original_precision


def test_package_exports_match_direct_module_imports():
    from src.application.tools import (
        ToolExecutionOrchestrationResult,
        ToolExecutionOrchestratorContractError,
        ToolRequestAdapterContractError,
        ToolRequestAdapterResult,
        ToolUsePresentation,
        ToolUsePresentationContractError,
        adapt_tool_request,
        execute_tool_with_audit,
        present_tool_adapter_result,
        present_tool_orchestration_result,
    )
    from src.application.tools.tool_execution_orchestrator import (
        ToolExecutionOrchestrationResult as DirectOrchestrationResult,
        ToolExecutionOrchestratorContractError as DirectOrchestrationError,
        execute_tool_with_audit as direct_execute,
    )
    from src.application.tools.tool_request_adapter import (
        ToolRequestAdapterContractError as DirectAdapterError,
        ToolRequestAdapterResult as DirectAdapterResult,
        adapt_tool_request as direct_adapt,
    )
    from src.application.tools.tool_use_presentation import (
        ToolUsePresentation as DirectPresentation,
        ToolUsePresentationContractError as DirectPresentationError,
        present_tool_adapter_result as direct_present_adapter,
        present_tool_orchestration_result as direct_present_orchestration,
    )

    assert ToolExecutionOrchestrationResult is DirectOrchestrationResult
    assert ToolExecutionOrchestratorContractError is DirectOrchestrationError
    assert execute_tool_with_audit is direct_execute

    assert ToolRequestAdapterContractError is DirectAdapterError
    assert ToolRequestAdapterResult is DirectAdapterResult
    assert adapt_tool_request is direct_adapt

    assert ToolUsePresentation is DirectPresentation
    assert ToolUsePresentationContractError is DirectPresentationError
    assert present_tool_adapter_result is direct_present_adapter
    assert present_tool_orchestration_result is direct_present_orchestration


def test_adapter_ready_to_presentation_ready_without_execution():
    from src.application.tools import adapt_tool_request, present_tool_adapter_result

    adapter_result = adapt_tool_request(
        {
            "request_id": "req-foundation-ready",
            "tool_id": CALCULATOR_TOOL_ID,
            "arguments": {"operation": "add", "operands": [1, 2]},
            "correlation_id": "chat-foundation-ready",
            "requested_by": "foundation_gate",
            "consent_granted": False,
        }
    )

    adapter_payload = adapter_result.to_dict()
    presentation_payload = present_tool_adapter_result(adapter_result).to_dict()

    assert adapter_payload["status"] == "ready"
    assert adapter_payload["can_govern_truth"] is False
    assert presentation_payload["status"] == "ready"
    assert presentation_payload["can_govern_truth"] is False
    assert presentation_payload["tool_id"] == CALCULATOR_TOOL_ID

    assert json.loads(json.dumps(adapter_payload, sort_keys=True)) == adapter_payload
    assert json.loads(json.dumps(presentation_payload, sort_keys=True)) == presentation_payload


def test_orchestration_success_like_mapping_to_presentation_success_without_execution():
    from src.application.tools import present_tool_orchestration_result

    presentation_payload = present_tool_orchestration_result(
        {
            "request_id": "req-foundation-orch-success",
            "tool_id": CALCULATOR_TOOL_ID,
            "correlation_id": "chat-foundation-orch-success",
            "response_status": "success",
            "audit_accepted": True,
            "tool_response": {"status": "success", "can_govern_truth": False},
            "audit_sink_result": {"status": "accepted", "can_govern_truth": False},
            "can_govern_truth": False,
        }
    ).to_dict()

    assert presentation_payload["status"] == "success"
    assert presentation_payload["severity"] == "info"
    assert presentation_payload["tool_id"] == CALCULATOR_TOOL_ID
    assert presentation_payload["can_govern_truth"] is False
    assert json.loads(json.dumps(presentation_payload, sort_keys=True)) == presentation_payload


def test_no_chat_router_llm_parser_or_agent_symbols_are_exported():
    import src.application.tools as tools

    forbidden_names = {
        "chat",
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


def test_lazy_targets_load_only_when_requested_by_export_access():
    _purge_tool_package_and_lazy_targets()

    tools = importlib.import_module("src.application.tools")
    for module_name in LAZY_TARGETS:
        assert module_name not in sys.modules

    _ = tools.adapt_tool_request
    assert "src.application.tools.tool_request_adapter" in sys.modules
    assert "src.application.tools.tool_execution_orchestrator" not in sys.modules
    assert "src.application.tools.tool_use_presentation" not in sys.modules

    _ = tools.present_tool_adapter_result
    assert "src.application.tools.tool_use_presentation" in sys.modules
    assert "src.application.tools.tool_execution_orchestrator" not in sys.modules

    _ = tools.execute_tool_with_audit
    assert "src.application.tools.tool_execution_orchestrator" in sys.modules
