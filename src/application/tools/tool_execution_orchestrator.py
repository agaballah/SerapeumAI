"""Non-chat orchestration contract for deterministic tool execution with audit.

This module composes existing contracts only. It does not parse LLM tool calls,
wire chat/router behavior, persist audit events, write files, touch databases,
or interact with UI/runtime providers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from src.application.tools.tool_execution_audit import (
    ToolExecutionAuditContractError,
    build_tool_execution_audit_event,
)
from src.application.tools.tool_execution_audit_sink import (
    NoopToolExecutionAuditSink,
    ToolExecutionAuditSink,
    ToolExecutionAuditSinkContractError,
    ToolExecutionAuditSinkResult,
)
from src.application.tools.tool_execution_harness import execute_tool_invocation
from src.application.tools.tool_invocation_contract import (
    ToolInvocationContractError,
    ToolInvocationRequest,
    ToolInvocationResponse,
)


class ToolExecutionOrchestratorContractError(ValueError):
    """Raised when the tool execution orchestrator contract is invalid."""


@dataclass(frozen=True)
class ToolExecutionOrchestrationResult:
    """Combined JSON-safe execution + audit sink result envelope."""

    request_id: str
    tool_id: str
    response_status: str
    audit_sink_name: str
    audit_accepted: bool
    tool_response: Mapping[str, Any]
    audit_sink_result: Mapping[str, Any]
    can_govern_truth: bool = False

    def validate(self) -> None:
        _require_non_empty(self.request_id, "request_id")
        _require_non_empty(self.tool_id, "tool_id")
        _require_non_empty(self.response_status, "response_status")
        _require_non_empty(self.audit_sink_name, "audit_sink_name")

        if not isinstance(self.audit_accepted, bool):
            raise ToolExecutionOrchestratorContractError(
                "audit_accepted must be boolean."
            )
        if self.can_govern_truth is not False:
            raise ToolExecutionOrchestratorContractError(
                "Tool execution orchestration results cannot govern truth."
            )
        if not isinstance(self.tool_response, Mapping):
            raise ToolExecutionOrchestratorContractError(
                "tool_response must be a mapping."
            )
        if not isinstance(self.audit_sink_result, Mapping):
            raise ToolExecutionOrchestratorContractError(
                "audit_sink_result must be a mapping."
            )

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "request_id": self.request_id,
            "tool_id": self.tool_id,
            "response_status": self.response_status,
            "audit_sink_name": self.audit_sink_name,
            "audit_accepted": self.audit_accepted,
            "tool_response": dict(self.tool_response),
            "audit_sink_result": dict(self.audit_sink_result),
            "can_govern_truth": False,
        }


def execute_tool_with_audit(
    request: ToolInvocationRequest,
    *,
    audit_sink: ToolExecutionAuditSink | None = None,
    event_id: str | None = None,
    created_at: str | None = None,
    event_source: str = "tool_execution_orchestrator",
    executors: Mapping[str, Any] | None = None,
    definition_factories: Mapping[str, Any] | None = None,
) -> ToolExecutionOrchestrationResult:
    """Execute a deterministic tool and send a non-persistent audit event to a sink."""

    if not isinstance(request, ToolInvocationRequest):
        raise ToolExecutionOrchestratorContractError(
            "request must be a ToolInvocationRequest instance."
        )

    sink = NoopToolExecutionAuditSink() if audit_sink is None else audit_sink
    _validate_sink(sink)

    request_validation_error = _validate_request_for_orchestration(request)
    if request_validation_error is not None:
        return request_validation_error

    tool_response = execute_tool_invocation(
        request,
        executors=executors,
        definition_factories=definition_factories,
    )
    tool_response_dict = tool_response.to_dict()

    audit_sink_result = _build_and_accept_audit_event(
        request=request,
        tool_response=tool_response,
        sink=sink,
        event_id=event_id,
        created_at=created_at,
        event_source=event_source,
    )
    audit_sink_result_dict = audit_sink_result.to_dict()

    result = ToolExecutionOrchestrationResult(
        request_id=request.request_id,
        tool_id=request.tool_id,
        response_status=tool_response_dict["status"],
        audit_sink_name=audit_sink_result_dict["sink_name"],
        audit_accepted=audit_sink_result_dict["accepted"],
        tool_response=tool_response_dict,
        audit_sink_result=audit_sink_result_dict,
        can_govern_truth=False,
    )
    result.validate()
    return result


def _validate_request_for_orchestration(
    request: ToolInvocationRequest,
) -> ToolExecutionOrchestrationResult | None:
    try:
        request_dict = request.to_dict()
    except ToolInvocationContractError as exc:
        error_message = str(exc)
        tool_id = request.tool_id if isinstance(request.tool_id, str) and request.tool_id.strip() else "invalid_tool_id"
        request_id = request.request_id if isinstance(request.request_id, str) and request.request_id.strip() else "invalid_request_id"

        tool_response = {
            "request_id": request_id,
            "tool_id": tool_id,
            "status": "error",
            "result": None,
            "error": {
                "error_type": "invalid_tool_invocation_request",
                "message": error_message,
            },
            "correlation_id": None,
            "can_govern_truth": False,
        }
        audit_sink_result = {
            "sink_name": "request_validation",
            "accepted": False,
            "event_id": None,
            "request_id": request_id,
            "tool_id": tool_id,
            "response_status": "error",
            "error": {
                "error_type": "audit_event_build_error",
                "message": error_message,
            },
            "can_govern_truth": False,
        }

        return ToolExecutionOrchestrationResult(
            request_id=request_id,
            tool_id=tool_id,
            response_status="error",
            audit_sink_name="request_validation",
            audit_accepted=False,
            tool_response=tool_response,
            audit_sink_result=audit_sink_result,
            can_govern_truth=False,
        )

    return None
def _build_and_accept_audit_event(
    *,
    request: ToolInvocationRequest,
    tool_response: ToolInvocationResponse,
    sink: ToolExecutionAuditSink,
    event_id: str | None,
    created_at: str | None,
    event_source: str,
) -> ToolExecutionAuditSinkResult:
    try:
        audit_event = build_tool_execution_audit_event(
            request=request,
            response=tool_response,
            event_id=event_id,
            created_at=created_at,
            event_source=event_source,
        )
    except (ToolExecutionAuditContractError, ToolInvocationContractError) as exc:
        return ToolExecutionAuditSinkResult(
            sink_name=_sink_name(sink),
            accepted=False,
            event_id=None,
            request_id=request.request_id,
            tool_id=request.tool_id,
            response_status=tool_response.to_dict()["status"],
            error={
                "error_type": "audit_event_build_error",
                "message": str(exc),
            },
            can_govern_truth=False,
        )

    return sink.accept(audit_event)


def _validate_sink(sink: object) -> None:
    if not hasattr(sink, "accept") or not callable(getattr(sink, "accept")):
        raise ToolExecutionOrchestratorContractError(
            "audit_sink must implement accept(event)."
        )


def _sink_name(sink: object) -> str:
    name = getattr(sink, "sink_name", sink.__class__.__name__)
    if not isinstance(name, str) or not name.strip():
        return "unknown_audit_sink"
    return name.strip()


def _require_non_empty(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ToolExecutionOrchestratorContractError(
            f"{field_name} must be a non-empty string."
        )
    return value.strip()
