from __future__ import annotations

import json

from src.application.tools.calculator_tool import TOOL_ID as CALCULATOR_TOOL_ID
from src.application.tools.tool_request_adapter import adapt_tool_request
from src.application.tools.tool_use_presentation import (
    ToolUsePresentation,
    present_tool_adapter_result,
    present_tool_orchestration_result,
)


def _ready_adapter_result():
    return adapt_tool_request(
        {
            "request_id": "req-present-001",
            "tool_id": CALCULATOR_TOOL_ID,
            "arguments": {"operation": "add", "operands": [1, 2]},
            "correlation_id": "chat-present-001",
            "requested_by": "presentation_test",
            "consent_granted": False,
        }
    )


def test_adapter_ready_presents_non_truth_governing_ready_envelope():
    result = present_tool_adapter_result(_ready_adapter_result()).to_dict()

    assert result["status"] == "ready"
    assert result["severity"] == "info"
    assert result["summary"] == "Structured tool request is ready."
    assert result["tool_id"] == CALCULATOR_TOOL_ID
    assert result["request_id"] == "req-present-001"
    assert result["correlation_id"] == "chat-present-001"
    assert result["source_status"] == "ready"
    assert result["can_govern_truth"] is False
    assert result["metadata"]["source"] == "adapter"


def test_adapter_clarification_presents_warning_with_next_action():
    adapter_result = adapt_tool_request({"request_id": "req-missing-tool", "arguments": {}})
    result = present_tool_adapter_result(adapter_result).to_dict()

    assert result["status"] == "clarification"
    assert result["severity"] == "warning"
    assert result["source_status"] == "clarification"
    assert result["metadata"]["missing_field"] == "tool_id"
    assert "tool_id" in result["next_action"]
    assert result["can_govern_truth"] is False


def test_adapter_error_presents_controlled_error():
    adapter_result = adapt_tool_request(
        {
            "request_id": "req-bad-args",
            "tool_id": CALCULATOR_TOOL_ID,
            "arguments": ["bad"],
            "consent_granted": False,
        }
    )
    result = present_tool_adapter_result(adapter_result).to_dict()

    assert result["status"] == "error"
    assert result["severity"] == "error"
    assert result["source_status"] == "error"
    assert result["metadata"]["error_type"] == "invalid_arguments"
    assert result["can_govern_truth"] is False


def test_adapter_refusal_like_mapping_is_supported():
    result = present_tool_adapter_result(
        {
            "status": "refusal",
            "tool_request": {
                "request_id": "req-refused",
                "tool_id": CALCULATOR_TOOL_ID,
                "correlation_id": "chat-refused",
            },
            "error": {
                "error_type": "missing_consent",
                "message": "Consent is required before this tool can run.",
            },
            "can_govern_truth": False,
        }
    ).to_dict()

    assert result["status"] == "refusal"
    assert result["severity"] == "warning"
    assert result["tool_id"] == CALCULATOR_TOOL_ID
    assert result["metadata"]["reason"] == "missing_consent"
    assert result["can_govern_truth"] is False


def test_orchestration_success_mapping_presents_non_truth_governing_success():
    result = present_tool_orchestration_result(
        {
            "request_id": "req-orch-success",
            "tool_id": CALCULATOR_TOOL_ID,
            "correlation_id": "chat-orch-success",
            "response_status": "success",
            "audit_accepted": True,
            "tool_response": {"status": "success", "can_govern_truth": False},
            "audit_sink_result": {"status": "accepted", "can_govern_truth": False},
            "can_govern_truth": False,
        }
    ).to_dict()

    assert result["status"] == "success"
    assert result["severity"] == "info"
    assert result["tool_id"] == CALCULATOR_TOOL_ID
    assert result["metadata"]["audit_accepted"] is True
    assert result["can_govern_truth"] is False


def test_orchestration_refusal_mapping_presents_controlled_refusal():
    result = present_tool_orchestration_result(
        {
            "request_id": "req-orch-blocked",
            "tool_id": CALCULATOR_TOOL_ID,
            "response_status": "blocked",
            "error": {
                "error_type": "not_eligible",
                "message": "Tool is not eligible in this scope.",
            },
            "can_govern_truth": False,
        }
    ).to_dict()

    assert result["status"] == "refusal"
    assert result["severity"] == "warning"
    assert result["source_status"] == "blocked"
    assert result["metadata"]["reason"] == "not_eligible"
    assert result["can_govern_truth"] is False


def test_orchestration_error_mapping_presents_controlled_error():
    result = present_tool_orchestration_result(
        {
            "request_id": "req-orch-error",
            "tool_id": CALCULATOR_TOOL_ID,
            "response_status": "error",
            "error": {
                "error_type": "execution_error",
                "message": "Tool execution failed.",
            },
            "can_govern_truth": False,
        }
    ).to_dict()

    assert result["status"] == "error"
    assert result["severity"] == "error"
    assert result["source_status"] == "error"
    assert result["metadata"]["error_type"] == "execution_error"
    assert result["can_govern_truth"] is False


def test_presentation_output_is_json_serializable():
    result = present_tool_adapter_result(_ready_adapter_result()).to_dict()

    assert json.loads(json.dumps(result, sort_keys=True)) == result


def test_invalid_payload_produces_controlled_error():
    result = present_tool_adapter_result(["bad"]).to_dict()

    assert result["status"] == "error"
    assert result["severity"] == "error"
    assert result["metadata"]["error_type"] == "invalid_input"
    assert result["can_govern_truth"] is False


def test_presentation_contract_rejects_truth_governance():
    presentation = ToolUsePresentation(
        status="success",
        severity="info",
        summary="Bad",
        detail="Bad",
        source_status="success",
        can_govern_truth=True,
    )

    try:
        presentation.to_dict()
    except Exception as exc:
        assert "cannot govern truth" in str(exc)
    else:
        raise AssertionError("Expected presentation contract to reject truth governance.")


def test_module_does_not_expose_chat_router_or_llm_parser_symbols():
    import src.application.tools.tool_use_presentation as presentation

    forbidden_names = {
        "execute_tool_with_audit",
        "chat_page",
        "chat_panel",
        "tool_router",
        "autonomous_tool_router",
        "parse_llm_tool_call",
        "llm_tool_call",
        "mcp",
        "agent_loop",
        "audit_persistence",
    }

    for name in forbidden_names:
        assert not hasattr(presentation, name)
