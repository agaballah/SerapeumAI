"""Structured adapter for future chat-owned tool requests.

This module adapts application-owned structured request mappings into the
ToolInvocationRequest contract. It does not parse natural language, execute
tools, route autonomously, persist audits, touch storage, import chat UI, or
call the tool execution orchestrator.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from src.application.tools.tool_invocation_contract import (
    ToolInvocationContractError,
    ToolInvocationRequest,
)


class ToolRequestAdapterContractError(ValueError):
    """Raised when the adapter result contract itself is invalid."""


_ALLOWED_STATUSES = {"ready", "refusal", "clarification", "error"}


@dataclass(frozen=True)
class ToolRequestAdapterResult:
    status: str
    tool_request: Mapping[str, Any] | None = None
    error: Mapping[str, Any] | None = None
    clarification: Mapping[str, Any] | None = None
    can_govern_truth: bool = False

    def validate(self) -> None:
        if self.status not in _ALLOWED_STATUSES:
            raise ToolRequestAdapterContractError("status must be one of ready/refusal/clarification/error.")
        if self.can_govern_truth is not False:
            raise ToolRequestAdapterContractError("adapter result cannot govern truth.")
        if self.tool_request is not None and not isinstance(self.tool_request, Mapping):
            raise ToolRequestAdapterContractError("tool_request must be a mapping or None.")
        if self.error is not None and not isinstance(self.error, Mapping):
            raise ToolRequestAdapterContractError("error must be a mapping or None.")
        if self.clarification is not None and not isinstance(self.clarification, Mapping):
            raise ToolRequestAdapterContractError("clarification must be a mapping or None.")
        if self.status == "ready" and self.tool_request is None:
            raise ToolRequestAdapterContractError("ready result requires tool_request.")
        if self.status in {"refusal", "error"} and self.error is None:
            raise ToolRequestAdapterContractError("refusal/error result requires error.")
        if self.status == "clarification" and self.clarification is None:
            raise ToolRequestAdapterContractError("clarification result requires clarification.")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "status": self.status,
            "tool_request": dict(self.tool_request) if self.tool_request is not None else None,
            "error": dict(self.error) if self.error is not None else None,
            "clarification": dict(self.clarification) if self.clarification is not None else None,
            "can_govern_truth": False,
        }


def adapt_tool_request(payload: Mapping[str, Any]) -> ToolRequestAdapterResult:
    if not isinstance(payload, Mapping):
        return _error(
            "invalid_payload",
            "Tool request payload must be a mapping.",
        )

    request_id = _string_or_default(payload.get("request_id"), "adapted-tool-request")
    tool_id = _string_or_none(payload.get("tool_id"))
    arguments = payload.get("arguments")
    correlation_id = _string_or_none(payload.get("correlation_id"))
    requested_by = _string_or_default(payload.get("requested_by"), "tool_request_adapter")
    consent_granted = payload.get("consent_granted", False)
    if not isinstance(consent_granted, bool):
        return _error(
            "invalid_consent_granted",
            "Tool request consent_granted must be a boolean when provided.",
        )

    if tool_id is None:
        return _clarification(
            missing_field="tool_id",
            message="Tool request is missing a tool_id.",
        )

    if "arguments" not in payload:
        return _clarification(
            missing_field="arguments",
            message="Tool request is missing arguments.",
        )

    if not isinstance(arguments, Mapping):
        return _error(
            "invalid_arguments",
            "Tool request arguments must be a mapping.",
        )

    try:
        request = ToolInvocationRequest(
            request_id=request_id,
            tool_id=tool_id,
            arguments=dict(arguments),
            correlation_id=correlation_id,
            requested_by=requested_by,
            consent_granted=consent_granted,
        )
        request_dict = request.to_dict()
    except ToolInvocationContractError as exc:
        return _error(
            "invalid_tool_invocation_request",
            str(exc),
        )

    return ToolRequestAdapterResult(
        status="ready",
        tool_request=request_dict,
        error=None,
        clarification=None,
        can_govern_truth=False,
    )


def _string_or_none(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _string_or_default(value: Any, default: str) -> str:
    stripped = _string_or_none(value)
    return stripped if stripped is not None else default


def _clarification(*, missing_field: str, message: str) -> ToolRequestAdapterResult:
    return ToolRequestAdapterResult(
        status="clarification",
        tool_request=None,
        error=None,
        clarification={
            "reason": "missing_required_field",
            "missing_field": missing_field,
            "message": message,
        },
        can_govern_truth=False,
    )


def _error(error_type: str, message: str) -> ToolRequestAdapterResult:
    return ToolRequestAdapterResult(
        status="error",
        tool_request=None,
        error={
            "error_type": error_type,
            "message": message,
        },
        clarification=None,
        can_govern_truth=False,
    )
