from __future__ import annotations

import src.application.tools as tools
from src.application.tools import (
    ToolExecutionOrchestrationResult,
    ToolExecutionOrchestratorContractError,
    execute_tool_with_audit,
)
from src.application.tools.calculator_tool import TOOL_ID as CALCULATOR_TOOL_ID
from src.application.tools.tool_execution_orchestrator import (
    ToolExecutionOrchestrationResult as DirectToolExecutionOrchestrationResult,
    ToolExecutionOrchestratorContractError as DirectToolExecutionOrchestratorContractError,
    execute_tool_with_audit as direct_execute_tool_with_audit,
)
from src.application.tools.tool_invocation_contract import ToolInvocationRequest


def _request():
    return ToolInvocationRequest(
        request_id="req-export-001",
        tool_id=CALCULATOR_TOOL_ID,
        arguments={"operation": "add", "operands": [1, 2]},
        correlation_id="chat-export-001",
        requested_by="test",
        consent_granted=False,
    )


def test_package_boundary_exports_stable_orchestrator_symbols():
    assert execute_tool_with_audit is direct_execute_tool_with_audit
    assert ToolExecutionOrchestrationResult is DirectToolExecutionOrchestrationResult
    assert (
        ToolExecutionOrchestratorContractError
        is DirectToolExecutionOrchestratorContractError
    )


def test_package_boundary_all_is_explicit_and_minimal():
    assert tools.__all__ == [
        "ToolExecutionOrchestrationResult",
        "ToolExecutionOrchestratorContractError",
        "execute_tool_with_audit",
    ]


def test_execute_tool_with_audit_works_through_package_import_path():
    result = execute_tool_with_audit(_request(), event_id="evt-export-001").to_dict()

    assert result["request_id"] == "req-export-001"
    assert result["tool_id"] == CALCULATOR_TOOL_ID
    assert result["response_status"] == "success"
    assert result["audit_accepted"] is True
    assert result["tool_response"]["result"]["computed_result"] == "3"
    assert result["can_govern_truth"] is False
    assert result["tool_response"]["can_govern_truth"] is False
    assert result["audit_sink_result"]["can_govern_truth"] is False


def test_private_orchestrator_helpers_are_not_exported():
    private_names = {
        "_validate_request_for_orchestration",
        "_build_and_accept_audit_event",
        "_validate_sink",
        "_sink_name",
        "_require_non_empty",
    }

    for name in private_names:
        assert not hasattr(tools, name)


def test_export_boundary_does_not_introduce_chat_router_or_llm_parser_symbols():
    forbidden_names = {
        "chat",
        "chat_page",
        "tool_router",
        "autonomous_tool_router",
        "llm_tool_call",
        "parse_llm_tool_call",
        "mcp",
        "agent_loop",
        "audit_persistence",
    }

    for name in forbidden_names:
        assert not hasattr(tools, name)

def test_plain_package_import_does_not_mutate_decimal_precision():
    import decimal
    import importlib
    import sys

    sys.modules.pop("src.application.tools", None)

    original_precision = decimal.getcontext().prec
    decimal.getcontext().prec = 7
    try:
        imported_tools = importlib.import_module("src.application.tools")

        assert imported_tools.__all__ == [
            "ToolExecutionOrchestrationResult",
            "ToolExecutionOrchestratorContractError",
            "execute_tool_with_audit",
        ]
        assert decimal.getcontext().prec == 7
    finally:
        decimal.getcontext().prec = original_precision
