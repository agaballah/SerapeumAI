"""Application tool contract exports.

This package boundary exposes stable application-tool contracts only.
It does not wire chat, route autonomous tool calls, parse LLM tool calls,
persist audits, touch storage, use internet, or interact with UI/runtime
providers.

Exports are resolved lazily so plain package import stays side-effect-light.
"""

from __future__ import annotations

from typing import Any

_ORCHESTRATOR_EXPORTS = {
    "ToolExecutionOrchestrationResult",
    "ToolExecutionOrchestratorContractError",
    "execute_tool_with_audit",
}

_ADAPTER_EXPORTS = {
    "ToolRequestAdapterContractError",
    "ToolRequestAdapterResult",
    "adapt_tool_request",
}

_PRESENTATION_EXPORTS = {
    "ToolUsePresentationContractError",
    "ToolUsePresentation",
    "present_tool_adapter_result",
    "present_tool_orchestration_result",
}

__all__ = sorted(_ORCHESTRATOR_EXPORTS | _ADAPTER_EXPORTS | _PRESENTATION_EXPORTS)


def __getattr__(name: str) -> Any:
    if name in _ORCHESTRATOR_EXPORTS:
        from src.application.tools.tool_execution_orchestrator import (
            ToolExecutionOrchestrationResult,
            ToolExecutionOrchestratorContractError,
            execute_tool_with_audit,
        )

        exports = {
            "ToolExecutionOrchestrationResult": ToolExecutionOrchestrationResult,
            "ToolExecutionOrchestratorContractError": ToolExecutionOrchestratorContractError,
            "execute_tool_with_audit": execute_tool_with_audit,
        }
        return exports[name]

    if name in _ADAPTER_EXPORTS:
        from src.application.tools.tool_request_adapter import (
            ToolRequestAdapterContractError,
            ToolRequestAdapterResult,
            adapt_tool_request,
        )

        exports = {
            "ToolRequestAdapterContractError": ToolRequestAdapterContractError,
            "ToolRequestAdapterResult": ToolRequestAdapterResult,
            "adapt_tool_request": adapt_tool_request,
        }
        return exports[name]

    if name in _PRESENTATION_EXPORTS:
        from src.application.tools.tool_use_presentation import (
            ToolUsePresentationContractError,
            ToolUsePresentation,
            present_tool_adapter_result,
            present_tool_orchestration_result,
        )

        exports = {
            "ToolUsePresentationContractError": ToolUsePresentationContractError,
            "ToolUsePresentation": ToolUsePresentation,
            "present_tool_adapter_result": present_tool_adapter_result,
            "present_tool_orchestration_result": present_tool_orchestration_result,
        }
        return exports[name]

    raise AttributeError(f"module 'src.application.tools' has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
