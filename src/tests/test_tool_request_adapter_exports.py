from __future__ import annotations

import decimal
import importlib
import json
import sys

from src.application.tools.calculator_tool import TOOL_ID as CALCULATOR_TOOL_ID


def _purge_tool_package_and_lazy_targets() -> None:
    for module_name in [
        "src.application.tools",
        "src.application.tools.tool_request_adapter",
        "src.application.tools.tool_execution_orchestrator",
    ]:
        sys.modules.pop(module_name, None)


def test_plain_package_import_does_not_eagerly_load_adapter_or_orchestrator():
    _purge_tool_package_and_lazy_targets()

    imported_tools = importlib.import_module("src.application.tools")

    assert imported_tools.__all__ == sorted(
        [
            "ToolExecutionOrchestrationResult",
            "ToolExecutionOrchestratorContractError",
            "execute_tool_with_audit",
            "ToolRequestAdapterContractError",
            "ToolRequestAdapterResult",
            "adapt_tool_request",
        ]
    )
    assert "src.application.tools.tool_request_adapter" not in sys.modules
    assert "src.application.tools.tool_execution_orchestrator" not in sys.modules


def test_plain_package_import_does_not_mutate_decimal_precision():
    _purge_tool_package_and_lazy_targets()

    original_precision = decimal.getcontext().prec
    decimal.getcontext().prec = 9
    try:
        importlib.import_module("src.application.tools")
        assert decimal.getcontext().prec == 9
    finally:
        decimal.getcontext().prec = original_precision


def test_adapter_public_symbols_import_through_package_boundary():
    from src.application.tools import (
        ToolRequestAdapterContractError,
        ToolRequestAdapterResult,
        adapt_tool_request,
    )
    from src.application.tools.tool_request_adapter import (
        ToolRequestAdapterContractError as DirectError,
        ToolRequestAdapterResult as DirectResult,
        adapt_tool_request as direct_adapt,
    )

    assert ToolRequestAdapterContractError is DirectError
    assert ToolRequestAdapterResult is DirectResult
    assert adapt_tool_request is direct_adapt


def test_adapter_import_through_package_boundary_works_and_cannot_govern_truth():
    from src.application.tools import adapt_tool_request

    result = adapt_tool_request(
        {
            "request_id": "req-export-001",
            "tool_id": CALCULATOR_TOOL_ID,
            "arguments": {"operation": "add", "operands": [1, 2]},
            "correlation_id": "chat-export-001",
            "requested_by": "export_test",
            "consent_granted": False,
        }
    ).to_dict()

    assert result["status"] == "ready"
    assert result["tool_request"]["tool_id"] == CALCULATOR_TOOL_ID
    assert result["can_govern_truth"] is False
    assert json.loads(json.dumps(result, sort_keys=True)) == result


def test_existing_orchestrator_exports_remain_available():
    from src.application.tools import (
        ToolExecutionOrchestrationResult,
        ToolExecutionOrchestratorContractError,
        execute_tool_with_audit,
    )
    from src.application.tools.tool_execution_orchestrator import (
        ToolExecutionOrchestrationResult as DirectResult,
        ToolExecutionOrchestratorContractError as DirectError,
        execute_tool_with_audit as direct_execute,
    )

    assert ToolExecutionOrchestrationResult is DirectResult
    assert ToolExecutionOrchestratorContractError is DirectError
    assert execute_tool_with_audit is direct_execute


def test_private_adapter_helpers_are_not_exported():
    import src.application.tools as tools

    forbidden_names = {
        "_string_or_none",
        "_string_or_default",
        "_clarification",
        "_error",
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
