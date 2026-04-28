"""Non-writing sink contract for tool execution audit events.

This module defines deterministic sink semantics only. It does not persist
events, write files, touch databases, execute tools, wire chat/router behavior,
or interact with UI/runtime providers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from src.application.tools.tool_execution_audit import ToolExecutionAuditEvent


class ToolExecutionAuditSinkContractError(ValueError):
    """Raised when a tool execution audit sink contract is invalid."""


@dataclass(frozen=True)
class ToolExecutionAuditSinkResult:
    """JSON-safe result envelope returned by audit sinks."""

    sink_name: str
    accepted: bool
    event_id: str | None
    request_id: str | None
    tool_id: str | None
    response_status: str | None
    error: dict[str, Any] | None
    can_govern_truth: bool = False

    def validate(self) -> None:
        _require_non_empty(self.sink_name, "sink_name")
        if not isinstance(self.accepted, bool):
            raise ToolExecutionAuditSinkContractError("accepted must be boolean.")
        if self.can_govern_truth is not False:
            raise ToolExecutionAuditSinkContractError(
                "Tool execution audit sink results cannot govern truth."
            )
        if self.accepted and self.error is not None:
            raise ToolExecutionAuditSinkContractError(
                "Accepted sink results must not include an error."
            )
        if not self.accepted and not isinstance(self.error, dict):
            raise ToolExecutionAuditSinkContractError(
                "Rejected sink results must include a controlled error mapping."
            )

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "sink_name": self.sink_name,
            "accepted": self.accepted,
            "event_id": self.event_id,
            "request_id": self.request_id,
            "tool_id": self.tool_id,
            "response_status": self.response_status,
            "error": self.error,
            "can_govern_truth": False,
        }


class ToolExecutionAuditSink(Protocol):
    """Protocol for non-writing audit event sinks."""

    @property
    def sink_name(self) -> str:
        """Return deterministic sink name."""

    def accept(self, event: ToolExecutionAuditEvent) -> ToolExecutionAuditSinkResult:
        """Accept an audit event and return a deterministic sink result."""


class NoopToolExecutionAuditSink:
    """Production-safe no-op sink that validates but does not store events."""

    sink_name = "noop_tool_execution_audit_sink"

    def accept(self, event: ToolExecutionAuditEvent) -> ToolExecutionAuditSinkResult:
        try:
            event_dict = _validated_event_dict(event)
        except ToolExecutionAuditSinkContractError as exc:
            return _error_result(self.sink_name, "invalid_event", str(exc))

        return ToolExecutionAuditSinkResult(
            sink_name=self.sink_name,
            accepted=True,
            event_id=event_dict["event_id"],
            request_id=event_dict["request_id"],
            tool_id=event_dict["tool_id"],
            response_status=event_dict["response_status"],
            error=None,
            can_govern_truth=False,
        )


class InMemoryToolExecutionAuditSink:
    """Test-only in-memory sink. It performs no DB/file writes."""

    sink_name = "in_memory_tool_execution_audit_sink"

    def __init__(self) -> None:
        self._events: list[dict[str, Any]] = []

    def accept(self, event: ToolExecutionAuditEvent) -> ToolExecutionAuditSinkResult:
        try:
            event_dict = _validated_event_dict(event)
        except ToolExecutionAuditSinkContractError as exc:
            return _error_result(self.sink_name, "invalid_event", str(exc))

        self._events.append(dict(event_dict))
        return ToolExecutionAuditSinkResult(
            sink_name=self.sink_name,
            accepted=True,
            event_id=event_dict["event_id"],
            request_id=event_dict["request_id"],
            tool_id=event_dict["tool_id"],
            response_status=event_dict["response_status"],
            error=None,
            can_govern_truth=False,
        )

    def events(self) -> tuple[dict[str, Any], ...]:
        """Return immutable snapshot of accepted event dictionaries."""
        return tuple(dict(event) for event in self._events)


def accept_tool_execution_audit_event(
    sink: ToolExecutionAuditSink,
    event: ToolExecutionAuditEvent,
) -> ToolExecutionAuditSinkResult:
    """Accept an audit event through a sink protocol implementation."""

    if not hasattr(sink, "accept"):
        raise ToolExecutionAuditSinkContractError("sink must implement accept(event).")
    return sink.accept(event)


def _validated_event_dict(event: ToolExecutionAuditEvent) -> dict[str, Any]:
    if not isinstance(event, ToolExecutionAuditEvent):
        raise ToolExecutionAuditSinkContractError(
            "event must be a ToolExecutionAuditEvent instance."
        )
    return event.to_dict()


def _error_result(
    sink_name: str,
    error_type: str,
    message: str,
) -> ToolExecutionAuditSinkResult:
    return ToolExecutionAuditSinkResult(
        sink_name=sink_name,
        accepted=False,
        event_id=None,
        request_id=None,
        tool_id=None,
        response_status=None,
        error={
            "error_type": error_type,
            "message": message,
        },
        can_govern_truth=False,
    )


def _require_non_empty(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ToolExecutionAuditSinkContractError(
            f"{field_name} must be a non-empty string."
        )
    return value.strip()
