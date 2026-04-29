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
        "ToolUsePresentation",
        "ToolUsePresentationContractError",
        "adapt_tool_request",
        "execute_tool_with_audit",
        "present_tool_adapter_result",
        "present_tool_orchestration_result",
    ]
)


def _purge_tool_package_and_lazy_targets() -> None:
    for module_name in [
        "src.application.tools",
        "src.application.tools.tool_request_adapter",
        "src.application.tools.tool_execution_orchestrator",
        "src.application.tools.tool_use_presentation",
    ]:
        sys.modules.pop(module_name, None)


def test_plain_package_import_does_not_eagerly_load_lazy_targets():
    _purge_tool_package_and_lazy_targets()

    imported_tools = importlib.import_module("src.application.tools")

    assert imported_tools.__all__ == EXPECTED_PUBLIC_EXPORTS
    assert "src.application.tools.tool_request_adapter" not in sys.modules
    assert "src.application.tools.tool_execution_orchestrator" not in sys.modules
    assert "src.application.tools.tool_use_presentation" not in sys.modules


def test_plain_package_import_does_not_mutate_decimal_precision():
    _purge_tool_package_and_lazy_targets()

    original_precision = decimal.getcontext().prec
    decimal.getcontext().prec = 11
    try:
        imported_tools = importlib.import_module("src.application.tools")

        assert imported_tools.__all__ == EXPECTED_PUBLIC_EXPORTS
        assert decimal.getcontext().prec == 11
    finally:
        decimal.getcontext().prec = original_precision


def test_presentation_public_symbols_import_through_package_boundary():
    from src.application.tools import (
        ToolUsePresentation,
        ToolUsePresentationContractError,
        present_tool_adapter_result,
        present_tool_orchestration_result,
    )
    from src.application.tools.tool_use_presentation import (
        ToolUsePresentation as DirectPresentation,
        ToolUsePresentationContractError as DirectError,
        present_tool_adapter_result as direct_present_adapter,
        present_tool_orchestration_result as direct_present_orchestrator,
    )

    assert ToolUsePresentation is DirectPresentation
    assert ToolUsePresentationContractError is DirectError
    assert present_tool_adapter_result is direct_present_adapter
    assert present_tool_orchestration_result is direct_present_orchestrator


def test_present_tool_adapter_result_works_through_package_boundary():
    from src.application.tools import adapt_tool_request, present_tool_adapter_result

    adapter_result = adapt_tool_request(
        {
            "request_id": "req-export-presentation",
            "tool_id": CALCULATOR_TOOL_ID,
            "arguments": {"operation": "add", "operands": [1, 2]},
            "correlation_id": "chat-export-presentation",
            "requested_by": "presentation_export_test",
            "consent_granted": False,
        }
    )
    result = present_tool_adapter_result(adapter_result).to_dict()

    assert result["status"] == "ready"
    assert result["tool_id"] == CALCULATOR_TOOL_ID
    assert result["can_govern_truth"] is False
    assert json.loads(json.dumps(result, sort_keys=True)) == result


def test_present_tool_orchestration_result_works_through_package_boundary():
    from src.application.tools import present_tool_orchestration_result

    result = present_tool_orchestration_result(
        {
            "request_id": "req-export-orch",
            "tool_id": CALCULATOR_TOOL_ID,
            "correlation_id": "chat-export-orch",
            "response_status": "success",
            "audit_accepted": True,
            "tool_response": {"status": "success", "can_govern_truth": False},
            "audit_sink_result": {"status": "accepted", "can_govern_truth": False},
            "can_govern_truth": False,
        }
    ).to_dict()

    assert result["status"] == "success"
    assert result["tool_id"] == CALCULATOR_TOOL_ID
    assert result["can_govern_truth"] is False
    assert json.loads(json.dumps(result, sort_keys=True)) == result


def test_existing_orchestrator_and_adapter_exports_remain_available():
    from src.application.tools import (
        ToolExecutionOrchestrationResult,
        ToolExecutionOrchestratorContractError,
        ToolRequestAdapterContractError,
        ToolRequestAdapterResult,
        adapt_tool_request,
        execute_tool_with_audit,
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

    assert ToolExecutionOrchestrationResult is DirectOrchestrationResult
    assert ToolExecutionOrchestratorContractError is DirectOrchestrationError
    assert execute_tool_with_audit is direct_execute
    assert ToolRequestAdapterContractError is DirectAdapterError
    assert ToolRequestAdapterResult is DirectAdapterResult
    assert adapt_tool_request is direct_adapt


def test_private_presentation_helpers_are_not_exported():
    import src.application.tools as tools

    forbidden_names = {
        "_as_mapping",
        "_mapping_or_none",
        "_from_mapping",
        "_string_or_none",
        "_string_or_default",
        "_invalid_input",
    }

    for name in forbidden_names:
        assert name not in tools.__all__
        try:
            getattr(tools, name)
        except AttributeError:
            pass
        else:
            raise AssertionError(f"Private helper was exported: {name}")


def test_no_chat_router_or_llm_parser_symbols_are_exported():
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
    }

    for name in forbidden_names:
        assert name not in tools.__all__
        try:
            getattr(tools, name)
        except AttributeError:
            pass
        else:
            raise AssertionError(f"Forbidden symbol was exported: {name}")
