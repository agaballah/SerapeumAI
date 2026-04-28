"""Non-persistent audit event contract for deterministic tool executions.

This module builds JSON-safe audit event envelopes only. It does not persist
events, write files, touch databases, execute tools, wire chat/router behavior,
or interact with UI/runtime providers.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Mapping

from src.application.tools.tool_eligibility_gate import ToolEligibility
from src.application.tools.tool_invocation_contract import (
    ToolInvocationRequest,
    ToolInvocationResponse,
)


class ToolExecutionAuditContractError(ValueError):
    """Raised when a tool execution audit event contract is invalid."""


@dataclass(frozen=True)
class ToolExecutionAuditEvent:
    """Plain non-persistent audit event envelope."""

    event_type: str
    event_id: str
    request_id: str
    tool_id: str
    correlation_id: str | None
    requested_by: str
    consent_granted: bool
    response_status: str
    eligibility_decision: str | None
    eligibility_reasons: tuple[str, ...]
    error_type: str | None
    can_govern_truth: bool
    event_source: str
    created_at: str | None

    def validate(self) -> None:
        _require_non_empty(self.event_type, "event_type")
        _require_non_empty(self.event_id, "event_id")
        _require_non_empty(self.request_id, "request_id")
        _require_non_empty(self.tool_id, "tool_id")
        _require_non_empty(self.requested_by, "requested_by")
        _require_non_empty(self.response_status, "response_status")
        _require_non_empty(self.event_source, "event_source")
        _validate_optional_string(self.created_at, "created_at")

        if self.can_govern_truth is not False:
            raise ToolExecutionAuditContractError(
                "Tool execution audit events cannot govern truth."
            )
        if not isinstance(self.consent_granted, bool):
            raise ToolExecutionAuditContractError("consent_granted must be boolean.")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "event_type": self.event_type,
            "event_id": self.event_id,
            "request_id": self.request_id,
            "tool_id": self.tool_id,
            "correlation_id": self.correlation_id,
            "requested_by": self.requested_by,
            "consent_granted": self.consent_granted,
            "response_status": self.response_status,
            "eligibility_decision": self.eligibility_decision,
            "eligibility_reasons": list(self.eligibility_reasons),
            "error_type": self.error_type,
            "can_govern_truth": False,
            "event_source": self.event_source,
            "created_at": self.created_at,
        }


def build_tool_execution_audit_event(
    *,
    request: ToolInvocationRequest,
    response: ToolInvocationResponse,
    eligibility: ToolEligibility | Mapping[str, Any] | None = None,
    event_id: str | None = None,
    created_at: str | None = None,
    event_source: str = "tool_execution_harness",
) -> ToolExecutionAuditEvent:
    """Build a non-persistent audit event without executing or persisting anything."""

    if not isinstance(request, ToolInvocationRequest):
        raise ToolExecutionAuditContractError(
            "request must be a ToolInvocationRequest instance."
        )
    if not isinstance(response, ToolInvocationResponse):
        raise ToolExecutionAuditContractError(
            "response must be a ToolInvocationResponse instance."
        )

    request.validate()
    response.validate()

    if request.request_id != response.request_id:
        raise ToolExecutionAuditContractError(
            "request and response request_id values must match."
        )
    if request.tool_id != response.tool_id:
        raise ToolExecutionAuditContractError(
            "request and response tool_id values must match."
        )
    if request.correlation_id != response.correlation_id:
        raise ToolExecutionAuditContractError(
            "request and response correlation_id values must match."
        )

    eligibility_dict = _eligibility_to_dict(eligibility)
    response_dict = response.to_dict()
    error = response_dict.get("error") or {}

    normalized_event_id = event_id or _derive_event_id(
        request_id=request.request_id,
        tool_id=request.tool_id,
        response_status=response_dict["status"],
    )

    event = ToolExecutionAuditEvent(
        event_type="tool_execution.completed",
        event_id=_require_non_empty(normalized_event_id, "event_id"),
        request_id=request.request_id,
        tool_id=request.tool_id,
        correlation_id=request.correlation_id,
        requested_by=request.requested_by,
        consent_granted=request.consent_granted,
        response_status=response_dict["status"],
        eligibility_decision=eligibility_dict.get("decision"),
        eligibility_reasons=_normalize_reasons(eligibility_dict.get("reasons")),
        error_type=error.get("error_type"),
        can_govern_truth=False,
        event_source=_require_non_empty(event_source, "event_source"),
        created_at=_validate_optional_string(created_at, "created_at"),
    )
    event.validate()
    return event


def _eligibility_to_dict(
    eligibility: ToolEligibility | Mapping[str, Any] | None,
) -> dict[str, Any]:
    if eligibility is None:
        return {}
    if isinstance(eligibility, ToolEligibility):
        return eligibility.to_dict()
    if isinstance(eligibility, Mapping):
        return dict(eligibility)
    raise ToolExecutionAuditContractError(
        "eligibility must be ToolEligibility, mapping, or None."
    )


def _normalize_reasons(raw_reasons: Any) -> tuple[str, ...]:
    if raw_reasons is None:
        return ()
    if isinstance(raw_reasons, str):
        raise ToolExecutionAuditContractError(
            "eligibility reasons must be a sequence of non-empty strings, not a string."
        )
    if not isinstance(raw_reasons, Sequence):
        raise ToolExecutionAuditContractError(
            "eligibility reasons must be a sequence of non-empty strings."
        )

    reasons: list[str] = []
    for reason in raw_reasons:
        if not isinstance(reason, str) or not reason.strip():
            raise ToolExecutionAuditContractError(
                "eligibility reasons must contain only non-empty strings."
            )
        reasons.append(reason.strip())
    return tuple(reasons)

def _derive_event_id(*, request_id: str, tool_id: str, response_status: str) -> str:
    return f"tool-execution:{request_id}:{tool_id}:{response_status}"


def _validate_optional_string(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ToolExecutionAuditContractError(
            f"{field_name} must be None or a non-empty string."
        )
    return value.strip()

def _require_non_empty(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ToolExecutionAuditContractError(f"{field_name} must be a non-empty string.")
    return value.strip()
