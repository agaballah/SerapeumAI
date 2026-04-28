"""Application tool contract exports.

This package boundary exposes stable application-tool contracts only.
It does not wire chat, route autonomous tool calls, parse LLM tool calls,
persist audits, touch storage, use internet, or interact with UI/runtime
providers.

Exports are resolved lazily so plain package import stays side-effect-light.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "ToolExecutionOrchestrationResult",
    "ToolExecutionOrchestratorContractError",
    "execute_tool_with_audit",
]

_ORCHESTRATOR_EXPORTS = set(__all__)


def __getattr__(name: str) -> Any:
    if name not in _ORCHESTRATOR_EXPORTS:
        raise AttributeError(f"module 'src.application.tools' has no attribute {name!r}")

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


def __dir__() -> list[str]:
    return sorted(set(globals()) | _ORCHESTRATOR_EXPORTS)
