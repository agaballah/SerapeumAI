"""Source-level tool invocation request/response contracts.

This module defines validation and serialization boundaries only.
It does not execute tools, route requests, call an LLM, persist audits,
touch storage, use internet, or interact with UI/runtime providers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


class ToolInvocationContractError(ValueError):
    """Raised when a tool invocation request/response contract is invalid."""


class ToolInvocationStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"


def _validate_non_empty_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ToolInvocationContractError(f"{field_name} must be a non-empty string.")
    return value.strip()


def _validate_optional_string(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ToolInvocationContractError(f"{field_name} must be None or a non-empty string.")
    return value.strip()


def _validate_plain_mapping(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ToolInvocationContractError(f"{field_name} must be a mapping.")

    out: dict[str, Any] = {}
    for key, item in value.items():
        if not isinstance(key, str) or not key.strip():
            raise ToolInvocationContractError(f"{field_name} keys must be non-empty strings.")
        out[key.strip()] = item
    return out


@dataclass(frozen=True)
class ToolInvocationRequest:
    """Validated request shape for future application-owned tool invocation."""

    request_id: str
    tool_id: str
    arguments: Mapping[str, Any] = field(default_factory=dict)
    correlation_id: str | None = None
    requested_by: str = "system"
    consent_granted: bool = False

    def validate(self) -> None:
        _validate_non_empty_string(self.request_id, "request_id")
        _validate_non_empty_string(self.tool_id, "tool_id")
        _validate_plain_mapping(self.arguments, "arguments")
        _validate_optional_string(self.correlation_id, "correlation_id")
        _validate_non_empty_string(self.requested_by, "requested_by")
        if not isinstance(self.consent_granted, bool):
            raise ToolInvocationContractError("consent_granted must be a boolean.")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "request_id": _validate_non_empty_string(self.request_id, "request_id"),
            "tool_id": _validate_non_empty_string(self.tool_id, "tool_id"),
            "arguments": _validate_plain_mapping(self.arguments, "arguments"),
            "correlation_id": _validate_optional_string(self.correlation_id, "correlation_id"),
            "requested_by": _validate_non_empty_string(self.requested_by, "requested_by"),
            "consent_granted": self.consent_granted,
        }


@dataclass(frozen=True)
class ToolInvocationResponse:
    """Validated response shape for future application-owned tool invocation."""

    request_id: str
    tool_id: str
    status: ToolInvocationStatus
    result: Mapping[str, Any] | None = None
    error: Mapping[str, Any] | None = None
    correlation_id: str | None = None
    can_govern_truth: bool = False

    def validate(self) -> None:
        _validate_non_empty_string(self.request_id, "request_id")
        _validate_non_empty_string(self.tool_id, "tool_id")
        _normalize_status(self.status)
        _validate_optional_string(self.correlation_id, "correlation_id")

        if not isinstance(self.can_govern_truth, bool):
            raise ToolInvocationContractError("can_govern_truth must be a boolean.")
        if self.can_govern_truth is not False:
            raise ToolInvocationContractError("Tool invocation responses cannot govern truth.")

        status = _normalize_status(self.status)
        if status == ToolInvocationStatus.SUCCESS:
            if self.result is None:
                raise ToolInvocationContractError("success response requires result.")
            if self.error is not None:
                raise ToolInvocationContractError("success response cannot include error.")
            _validate_plain_mapping(self.result, "result")
        elif status == ToolInvocationStatus.ERROR:
            if self.error is None:
                raise ToolInvocationContractError("error response requires error.")
            if self.result is not None:
                raise ToolInvocationContractError("error response cannot include result.")
            _validate_plain_mapping(self.error, "error")
        else:
            raise ToolInvocationContractError(f"Unsupported status: {status}")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        status = _normalize_status(self.status)
        return {
            "request_id": _validate_non_empty_string(self.request_id, "request_id"),
            "tool_id": _validate_non_empty_string(self.tool_id, "tool_id"),
            "status": status.value,
            "result": (
                _validate_plain_mapping(self.result, "result")
                if self.result is not None
                else None
            ),
            "error": (
                _validate_plain_mapping(self.error, "error")
                if self.error is not None
                else None
            ),
            "correlation_id": _validate_optional_string(self.correlation_id, "correlation_id"),
            "can_govern_truth": False,
        }


def _normalize_status(value: Any) -> ToolInvocationStatus:
    if isinstance(value, ToolInvocationStatus):
        return value
    if isinstance(value, str):
        try:
            return ToolInvocationStatus(value)
        except ValueError as exc:
            raise ToolInvocationContractError(f"Unsupported status: {value!r}") from exc
    raise ToolInvocationContractError("status must be a ToolInvocationStatus or string value.")
