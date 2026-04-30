"""Non-executing bridge for structured chat-owned tool requests.

This module is the first bounded bridge between future chat-side structured
tool requests and the approved tool foundation. It adapts and presents only.

It does not execute tools, call the tool execution orchestrator, parse LLM tool
calls, import chat UI, persist audits, touch storage, mutate facts, or govern
truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from src.application.tools.tool_request_adapter import adapt_tool_request
from src.application.tools.tool_use_presentation import present_tool_adapter_result


class ChatToolBridgeContractError(ValueError):
    """Raised when the chat tool bridge result violates its contract."""


_ALLOWED_STATUSES = {"ready", "clarification", "refusal", "error"}


@dataclass(frozen=True)
class ChatToolBridgeResult:
    status: str
    adapter_result: Mapping[str, Any]
    presentation: Mapping[str, Any]
    request_id: str | None = None
    tool_id: str | None = None
    correlation_id: str | None = None
    source: str = "chat_tool_bridge"
    executed: bool = False
    can_govern_truth: bool = False

    def validate(self) -> None:
        if self.status not in _ALLOWED_STATUSES:
            raise ChatToolBridgeContractError("status is not an approved bridge status.")
        if not isinstance(self.adapter_result, Mapping):
            raise ChatToolBridgeContractError("adapter_result must be a mapping.")
        if not isinstance(self.presentation, Mapping):
            raise ChatToolBridgeContractError("presentation must be a mapping.")
        if self.request_id is not None and not isinstance(self.request_id, str):
            raise ChatToolBridgeContractError("request_id must be a string or None.")
        if self.tool_id is not None and not isinstance(self.tool_id, str):
            raise ChatToolBridgeContractError("tool_id must be a string or None.")
        if self.correlation_id is not None and not isinstance(self.correlation_id, str):
            raise ChatToolBridgeContractError("correlation_id must be a string or None.")
        if self.source != "chat_tool_bridge":
            raise ChatToolBridgeContractError("source must remain chat_tool_bridge.")
        if self.executed is not False:
            raise ChatToolBridgeContractError("chat tool bridge must not execute tools.")
        if self.can_govern_truth is not False:
            raise ChatToolBridgeContractError("chat tool bridge cannot govern truth.")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "status": self.status,
            "adapter_result": dict(self.adapter_result),
            "presentation": dict(self.presentation),
            "request_id": self.request_id,
            "tool_id": self.tool_id,
            "correlation_id": self.correlation_id,
            "source": self.source,
            "executed": False,
            "can_govern_truth": False,
        }


def build_chat_tool_bridge_envelope(payload: Mapping[str, Any]) -> ChatToolBridgeResult:
    """Adapt and present a structured chat-side tool request without execution."""

    adapter_result = adapt_tool_request(payload)
    adapter_payload = adapter_result.to_dict()

    presentation = present_tool_adapter_result(adapter_result)
    presentation_payload = presentation.to_dict()

    tool_request = adapter_payload.get("tool_request")
    tool_request_mapping = tool_request if isinstance(tool_request, Mapping) else None

    return ChatToolBridgeResult(
        status=_string_or_default(presentation_payload.get("status"), "error"),
        adapter_result=adapter_payload,
        presentation=presentation_payload,
        request_id=_string_or_none(_from_mapping(tool_request_mapping, "request_id")),
        tool_id=_string_or_none(_from_mapping(tool_request_mapping, "tool_id")),
        correlation_id=_string_or_none(_from_mapping(tool_request_mapping, "correlation_id")),
        source="chat_tool_bridge",
        executed=False,
        can_govern_truth=False,
    )


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
