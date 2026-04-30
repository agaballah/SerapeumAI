from __future__ import annotations

import decimal
import importlib
import sys

import src.application.tools as tools


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


def _purge_tool_package_and_lazy_targets() -> None:
    for module_name in [
        "src.application.tools",
        "src.application.tools.chat_tool_bridge",
        "src.application.tools.chat_tool_bridge",
    "src.application.tools.tool_execution_orchestrator",
        "src.application.tools.tool_request_adapter",
        "src.application.tools.tool_use_presentation",
    ]:
        sys.modules.pop(module_name, None)


def test_package_boundary_all_is_explicit_and_minimal():
    assert tools.__all__ == EXPECTED_PUBLIC_EXPORTS


def test_package_boundary_rejects_unknown_symbols():
    try:
        getattr(tools, "not_a_public_tool_symbol")
    except AttributeError as exc:
        assert "not_a_public_tool_symbol" in str(exc)
    else:
        raise AssertionError("Expected unknown package export to raise AttributeError.")


def test_plain_package_import_does_not_eagerly_load_lazy_targets():
    _purge_tool_package_and_lazy_targets()

    imported_tools = importlib.import_module("src.application.tools")

    assert imported_tools.__all__ == EXPECTED_PUBLIC_EXPORTS
    assert "src.application.tools.tool_execution_orchestrator" not in sys.modules
    assert "src.application.tools.tool_request_adapter" not in sys.modules
    assert "src.application.tools.tool_use_presentation" not in sys.modules


def test_plain_package_import_does_not_mutate_decimal_precision():
    _purge_tool_package_and_lazy_targets()

    original_precision = decimal.getcontext().prec
    decimal.getcontext().prec = 7
    try:
        imported_tools = importlib.import_module("src.application.tools")

        assert imported_tools.__all__ == EXPECTED_PUBLIC_EXPORTS
        assert decimal.getcontext().prec == 7
    finally:
        decimal.getcontext().prec = original_precision


def test_lazy_export_import_loads_orchestrator_only_when_requested():
    _purge_tool_package_and_lazy_targets()

    imported_tools = importlib.import_module("src.application.tools")
    assert "src.application.tools.tool_execution_orchestrator" not in sys.modules

    _ = imported_tools.execute_tool_with_audit

    assert "src.application.tools.tool_execution_orchestrator" in sys.modules


def test_orchestrator_public_symbols_import_through_package_boundary():
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


def test_private_orchestrator_helpers_are_not_exported():
    forbidden_names = {
        "_as_mapping",
        "_mapping_or_none",
        "_from_mapping",
        "_string_or_none",
        "_string_or_default",
        "_invalid_input",
        "_ORCHESTRATOR_EXPORTS",
        "_ADAPTER_EXPORTS",
        "_PRESENTATION_EXPORTS",
        "_BRIDGE_EXPORTS",
    }

    for name in forbidden_names:
        assert name not in tools.__all__
