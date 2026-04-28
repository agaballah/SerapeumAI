from __future__ import annotations

import json

from src.application.tools.calculator_tool import TOOL_ID as CALCULATOR_TOOL_ID
from src.application.tools.tool_invocation_contract import ToolInvocationRequest
from src.application.tools.tool_request_adapter import (
    ToolRequestAdapterResult,
    adapt_tool_request,
)


def _valid_payload():
    return {
        "request_id": "req-adapter-001",
        "tool_id": CALCULATOR_TOOL_ID,
        "arguments": {"operation": "add", "operands": [1, 2]},
        "correlation_id": "chat-adapter-001",
        "requested_by": "chat_adapter",
        "consent_granted": False,
    }


def test_valid_structured_mapping_becomes_ready_request_envelope():
    result = adapt_tool_request(_valid_payload()).to_dict()

    assert result["status"] == "ready"
    assert result["error"] is None
    assert result["clarification"] is None
    assert result["can_govern_truth"] is False

    request = ToolInvocationRequest(**result["tool_request"])
    assert request.to_dict()["request_id"] == "req-adapter-001"
    assert request.to_dict()["tool_id"] == CALCULATOR_TOOL_ID
    assert request.to_dict()["arguments"] == {"operation": "add", "operands": [1, 2]}
    assert request.to_dict()["correlation_id"] == "chat-adapter-001"
    assert request.to_dict()["requested_by"] == "chat_adapter"
    assert request.to_dict()["consent_granted"] is False


def test_missing_tool_id_returns_controlled_clarification():
    payload = _valid_payload()
    payload.pop("tool_id")

    result = adapt_tool_request(payload).to_dict()

    assert result["status"] == "clarification"
    assert result["tool_request"] is None
    assert result["clarification"]["missing_field"] == "tool_id"
    assert result["can_govern_truth"] is False


def test_missing_arguments_returns_controlled_clarification():
    payload = _valid_payload()
    payload.pop("arguments")

    result = adapt_tool_request(payload).to_dict()

    assert result["status"] == "clarification"
    assert result["tool_request"] is None
    assert result["clarification"]["missing_field"] == "arguments"
    assert result["can_govern_truth"] is False


def test_non_mapping_arguments_returns_controlled_error():
    payload = _valid_payload()
    payload["arguments"] = ["not", "a", "mapping"]

    result = adapt_tool_request(payload).to_dict()

    assert result["status"] == "error"
    assert result["tool_request"] is None
    assert result["error"]["error_type"] == "invalid_arguments"
    assert result["can_govern_truth"] is False


def test_non_mapping_payload_returns_controlled_error():
    result = adapt_tool_request(["bad"]).to_dict()

    assert result["status"] == "error"
    assert result["tool_request"] is None
    assert result["error"]["error_type"] == "invalid_payload"
    assert result["can_govern_truth"] is False


def test_blank_request_id_is_repaired_deterministically():
    payload = _valid_payload()
    payload["request_id"] = "   "

    result = adapt_tool_request(payload).to_dict()

    assert result["status"] == "ready"
    assert result["tool_request"]["request_id"] == "adapted-tool-request"
    assert result["can_govern_truth"] is False


def test_unknown_tool_id_remains_structurally_ready_for_orchestrator_rejection():
    payload = _valid_payload()
    payload["tool_id"] = "unknown.local"

    result = adapt_tool_request(payload).to_dict()

    assert result["status"] == "ready"
    assert result["tool_request"]["tool_id"] == "unknown.local"
    assert result["can_govern_truth"] is False


def test_result_is_json_serializable():
    result = adapt_tool_request(_valid_payload()).to_dict()

    assert json.loads(json.dumps(result, sort_keys=True)) == result


def test_adapter_result_contract_cannot_govern_truth():
    result = ToolRequestAdapterResult(
        status="ready",
        tool_request={"request_id": "req", "tool_id": CALCULATOR_TOOL_ID, "arguments": {}},
        can_govern_truth=True,
    )

    try:
        result.to_dict()
    except Exception as exc:
        assert "cannot govern truth" in str(exc)
    else:
        raise AssertionError("Expected adapter result to reject governing truth.")


def test_adapter_does_not_execute_tools_or_return_tool_result():
    result = adapt_tool_request(_valid_payload()).to_dict()

    assert result["status"] == "ready"
    assert "tool_response" not in result
    assert "audit_sink_result" not in result
    assert "computed_result" not in result["tool_request"]
    assert result["tool_request"]["arguments"]["operation"] == "add"


def test_adapter_does_not_expose_chat_router_or_llm_parser_symbols():
    import src.application.tools.tool_request_adapter as adapter

    forbidden_names = {
        "execute_tool_with_audit",
        "tool_router",
        "autonomous_tool_router",
        "parse_llm_tool_call",
        "llm_tool_call",
        "chat_page",
        "mcp",
        "agent_loop",
        "audit_persistence",
    }

    for name in forbidden_names:
        assert not hasattr(adapter, name)

def test_non_boolean_string_consent_returns_controlled_error():
    payload = _valid_payload()
    payload["consent_granted"] = "false"

    result = adapt_tool_request(payload).to_dict()

    assert result["status"] == "error"
    assert result["tool_request"] is None
    assert result["error"]["error_type"] == "invalid_consent_granted"
    assert result["can_govern_truth"] is False


def test_non_boolean_numeric_consent_returns_controlled_error():
    payload = _valid_payload()
    payload["consent_granted"] = 1

    result = adapt_tool_request(payload).to_dict()

    assert result["status"] == "error"
    assert result["tool_request"] is None
    assert result["error"]["error_type"] == "invalid_consent_granted"
    assert result["can_govern_truth"] is False


def test_omitted_consent_defaults_to_false_without_coercing_truthy_values():
    payload = _valid_payload()
    payload.pop("consent_granted")

    result = adapt_tool_request(payload).to_dict()

    assert result["status"] == "ready"
    assert result["tool_request"]["consent_granted"] is False
    assert result["can_govern_truth"] is False
