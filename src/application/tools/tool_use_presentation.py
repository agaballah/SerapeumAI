"""Presentation envelopes for tool-use outcomes.

This module converts adapter/orchestration outcomes into stable application
presentation envelopes. It does not execute tools, call the orchestrator, parse
LLM tool calls, import chat UI, persist audits, touch storage, or govern truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


class ToolUsePresentationContractError(ValueError):
    """Raised when a presentation envelope violates the contract."""


_ALLOWED_STATUSES = {"ready", "clarification", "refusal", "error", "success"}
_ALLOWED_SEVERITIES = {"info", "warning", "error"}


@dataclass(frozen=True)
class ToolUsePresentation:
    status: str
    severity: str
    summary: str
    detail: str
    source_status: str
    next_action: str | None = None
    tool_id: str | None = None
    request_id: str | None = None
    correlation_id: str | None = None
    metadata: Mapping[str, Any] | None = None
    can_govern_truth: bool = False

    def validate(self) -> None:
        if self.status not in _ALLOWED_STATUSES:
            raise ToolUsePresentationContractError("status is not an approved presentation status.")
        if self.severity not in _ALLOWED_SEVERITIES:
            raise ToolUsePresentationContractError("severity is not an approved presentation severity.")
        if not isinstance(self.summary, str) or not self.summary.strip():
            raise ToolUsePresentationContractError("summary must be a non-empty string.")
        if not isinstance(self.detail, str):
            raise ToolUsePresentationContractError("detail must be a string.")
        if not isinstance(self.source_status, str) or not self.source_status.strip():
            raise ToolUsePresentationContractError("source_status must be a non-empty string.")
        if self.next_action is not None and not isinstance(self.next_action, str):
            raise ToolUsePresentationContractError("next_action must be a string or None.")
        if self.tool_id is not None and not isinstance(self.tool_id, str):
            raise ToolUsePresentationContractError("tool_id must be a string or None.")
        if self.request_id is not None and not isinstance(self.request_id, str):
            raise ToolUsePresentationContractError("request_id must be a string or None.")
        if self.correlation_id is not None and not isinstance(self.correlation_id, str):
            raise ToolUsePresentationContractError("correlation_id must be a string or None.")
        if self.metadata is not None and not isinstance(self.metadata, Mapping):
            raise ToolUsePresentationContractError("metadata must be a mapping or None.")
        if self.can_govern_truth is not False:
            raise ToolUsePresentationContractError("tool-use presentation cannot govern truth.")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "status": self.status,
            "severity": self.severity,
            "summary": self.summary,
            "detail": self.detail,
            "next_action": self.next_action,
            "tool_id": self.tool_id,
            "request_id": self.request_id,
            "correlation_id": self.correlation_id,
            "source_status": self.source_status,
            "can_govern_truth": False,
            "metadata": dict(self.metadata) if self.metadata is not None else {},
        }


def present_tool_adapter_result(result: Any) -> ToolUsePresentation:
    data = _as_mapping(result)
    if data is None:
        return _invalid_input("adapter", "Adapter result must be a mapping or expose to_dict().")

    source_status = _string_or_default(data.get("status"), "error")
    tool_request = _mapping_or_none(data.get("tool_request"))
    error = _mapping_or_none(data.get("error"))
    clarification = _mapping_or_none(data.get("clarification"))

    tool_id = _string_or_none(_from_mapping(tool_request, "tool_id"))
    request_id = _string_or_none(_from_mapping(tool_request, "request_id"))
    correlation_id = _string_or_none(_from_mapping(tool_request, "correlation_id"))

    if source_status == "ready":
        return ToolUsePresentation(
            status="ready",
            severity="info",
            summary="Structured tool request is ready.",
            detail="A validated structured tool request is ready for a later execution boundary.",
            next_action=None,
            tool_id=tool_id,
            request_id=request_id,
            correlation_id=correlation_id,
            source_status=source_status,
            metadata={"source": "adapter"},
            can_govern_truth=False,
        )

    if source_status == "clarification":
        missing_field = _string_or_none(_from_mapping(clarification, "missing_field"))
        message = _string_or_default(_from_mapping(clarification, "message"), "More information is required.")
        return ToolUsePresentation(
            status="clarification",
            severity="warning",
            summary="Tool request needs clarification.",
            detail=message,
            next_action=f"Provide the missing field: {missing_field}." if missing_field else "Provide the missing tool request information.",
            tool_id=tool_id,
            request_id=request_id,
            correlation_id=correlation_id,
            source_status=source_status,
            metadata={"source": "adapter", "missing_field": missing_field},
            can_govern_truth=False,
        )

    if source_status == "refusal":
        reason = _string_or_default(_from_mapping(error, "error_type"), "tool_request_refused")
        message = _string_or_default(_from_mapping(error, "message"), "The tool request was refused.")
        return ToolUsePresentation(
            status="refusal",
            severity="warning",
            summary="Tool request was refused.",
            detail=message,
            next_action="Revise the structured request before trying again.",
            tool_id=tool_id,
            request_id=request_id,
            correlation_id=correlation_id,
            source_status=source_status,
            metadata={"source": "adapter", "reason": reason},
            can_govern_truth=False,
        )

    if source_status == "error":
        reason = _string_or_default(_from_mapping(error, "error_type"), "tool_request_error")
        message = _string_or_default(_from_mapping(error, "message"), "The tool request could not be prepared.")
        return ToolUsePresentation(
            status="error",
            severity="error",
            summary="Tool request could not be prepared.",
            detail=message,
            next_action="Correct the structured tool request.",
            tool_id=tool_id,
            request_id=request_id,
            correlation_id=correlation_id,
            source_status=source_status,
            metadata={"source": "adapter", "error_type": reason},
            can_govern_truth=False,
        )

    return ToolUsePresentation(
        status="error",
        severity="error",
        summary="Unsupported adapter result status.",
        detail=f"Unsupported adapter status: {source_status}",
        next_action="Use a supported adapter status.",
        tool_id=tool_id,
        request_id=request_id,
        correlation_id=correlation_id,
        source_status=source_status,
        metadata={"source": "adapter"},
        can_govern_truth=False,
    )


def present_tool_orchestration_result(result: Any) -> ToolUsePresentation:
    data = _as_mapping(result)
    if data is None:
        return _invalid_input("orchestrator", "Orchestration result must be a mapping or expose to_dict().")

    response_status = _string_or_default(data.get("response_status"), _string_or_default(data.get("status"), "error"))
    tool_response = _mapping_or_none(data.get("tool_response"))
    error = _mapping_or_none(data.get("error"))
    audit_sink_result = _mapping_or_none(data.get("audit_sink_result"))

    tool_id = _string_or_none(data.get("tool_id"))
    request_id = _string_or_none(data.get("request_id"))
    correlation_id = _string_or_none(data.get("correlation_id"))

    if response_status == "success":
        return ToolUsePresentation(
            status="success",
            severity="info",
            summary="Tool completed successfully.",
            detail="The deterministic tool completed and produced a non-truth-governing application result.",
            next_action=None,
            tool_id=tool_id,
            request_id=request_id,
            correlation_id=correlation_id,
            source_status=response_status,
            metadata={
                "source": "orchestrator",
                "audit_accepted": bool(data.get("audit_accepted", False)),
                "tool_response_status": _from_mapping(tool_response, "status"),
                "audit_sink_status": _from_mapping(audit_sink_result, "status"),
            },
            can_govern_truth=False,
        )

    if response_status in {"blocked", "refused", "not_eligible"}:
        message = _string_or_default(_from_mapping(error, "message"), "The tool request was refused by policy.")
        return ToolUsePresentation(
            status="refusal",
            severity="warning",
            summary="Tool request was refused.",
            detail=message,
            next_action="Review tool eligibility, scope, consent, and required inputs.",
            tool_id=tool_id,
            request_id=request_id,
            correlation_id=correlation_id,
            source_status=response_status,
            metadata={"source": "orchestrator", "reason": _from_mapping(error, "error_type")},
            can_govern_truth=False,
        )

    message = _string_or_default(_from_mapping(error, "message"), "The tool request failed before a trusted result could be presented.")
    return ToolUsePresentation(
        status="error",
        severity="error",
        summary="Tool request failed.",
        detail=message,
        next_action="Inspect the structured tool request and retry if appropriate.",
        tool_id=tool_id,
        request_id=request_id,
        correlation_id=correlation_id,
        source_status=response_status,
        metadata={"source": "orchestrator", "error_type": _from_mapping(error, "error_type")},
        can_govern_truth=False,
    )


def _as_mapping(value: Any) -> Mapping[str, Any] | None:
    if isinstance(value, Mapping):
        return value
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        converted = to_dict()
        if isinstance(converted, Mapping):
            return converted
    return None


def _mapping_or_none(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _from_mapping(mapping: Mapping[str, Any] | None, key: str) -> Any:
    if mapping is None:
        return None
    return mapping.get(key)


def _string_or_none(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _string_or_default(value: Any, default: str) -> str:
    stripped = _string_or_none(value)
    return stripped if stripped is not None else default


def _invalid_input(source: str, message: str) -> ToolUsePresentation:
    return ToolUsePresentation(
        status="error",
        severity="error",
        summary="Invalid tool-use presentation input.",
        detail=message,
        next_action="Provide a mapping or result object with to_dict().",
        tool_id=None,
        request_id=None,
        correlation_id=None,
        source_status="invalid_input",
        metadata={"source": source, "error_type": "invalid_input"},
        can_govern_truth=False,
    )
