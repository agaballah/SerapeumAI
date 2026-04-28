from __future__ import annotations

import json

import pytest

from src.application.tools.calculator_tool import TOOL_ID as CALCULATOR_TOOL_ID
from src.application.tools.tool_eligibility_gate import check_tool_eligibility
from src.application.tools.tool_execution_audit import (
    ToolExecutionAuditContractError,
    build_tool_execution_audit_event,
)
from src.application.tools.tool_execution_harness import execute_tool_invocation
from src.application.tools.tool_invocation_contract import (
    ToolInvocationRequest,
    ToolInvocationResponse,
    ToolInvocationStatus,
)


def _request(tool_id: str = CALCULATOR_TOOL_ID, request_id: str = "req-001"):
    return ToolInvocationRequest(
        request_id=request_id,
        tool_id=tool_id,
        arguments={"operation": "add", "operands": [1, 2]},
        correlation_id="chat-001",
        requested_by="test",
        consent_granted=False,
    )


def test_successful_tool_response_can_produce_audit_event():
    request = _request()
    response = execute_tool_invocation(request)
    eligibility = check_tool_eligibility(request.tool_id)

    event = build_tool_execution_audit_event(
        request=request,
        response=response,
        eligibility=eligibility,
        event_id="evt-001",
        created_at="2026-04-28T06:00:00Z",
    ).to_dict()

    assert event == {
        "event_type": "tool_execution.completed",
        "event_id": "evt-001",
        "request_id": "req-001",
        "tool_id": CALCULATOR_TOOL_ID,
        "correlation_id": "chat-001",
        "requested_by": "test",
        "consent_granted": False,
        "response_status": "success",
        "eligibility_decision": "allow",
        "eligibility_reasons": ["eligible"],
        "error_type": None,
        "can_govern_truth": False,
        "event_source": "tool_execution_harness",
        "created_at": "2026-04-28T06:00:00Z",
    }


def test_error_tool_response_can_produce_audit_event_with_error_type():
    request = _request(tool_id="unknown.local")
    response = execute_tool_invocation(request)

    event = build_tool_execution_audit_event(
        request=request,
        response=response,
        eligibility=response.to_dict()["error"]["details"],
        event_id="evt-002",
    ).to_dict()

    assert event["response_status"] == "error"
    assert event["eligibility_decision"] == "deny"
    assert "tool_not_resolved" in event["eligibility_reasons"]
    assert event["error_type"] == "tool_not_eligible"
    assert event["can_govern_truth"] is False


def test_audit_event_derives_stable_event_id_when_not_supplied():
    request = _request()
    response = execute_tool_invocation(request)

    event = build_tool_execution_audit_event(
        request=request,
        response=response,
    ).to_dict()

    assert event["event_id"] == (
        f"tool-execution:{request.request_id}:{request.tool_id}:success"
    )


def test_audit_event_accepts_eligibility_mapping():
    request = _request()
    response = execute_tool_invocation(request)

    event = build_tool_execution_audit_event(
        request=request,
        response=response,
        eligibility={"decision": "allow", "reasons": ["eligible"]},
    ).to_dict()

    assert event["eligibility_decision"] == "allow"
    assert event["eligibility_reasons"] == ["eligible"]


def test_audit_event_allows_missing_eligibility_for_legacy_callers():
    request = _request()
    response = execute_tool_invocation(request)

    event = build_tool_execution_audit_event(
        request=request,
        response=response,
    ).to_dict()

    assert event["eligibility_decision"] is None
    assert event["eligibility_reasons"] == []


def test_request_response_request_id_mismatch_is_rejected():
    request = _request(request_id="req-001")
    response = ToolInvocationResponse(
        request_id="req-002",
        tool_id=request.tool_id,
        status=ToolInvocationStatus.SUCCESS,
        result={"ok": True},
        can_govern_truth=False,
    )

    with pytest.raises(ToolExecutionAuditContractError, match="request_id"):
        build_tool_execution_audit_event(request=request, response=response)


def test_request_response_tool_id_mismatch_is_rejected():
    request = _request(tool_id=CALCULATOR_TOOL_ID)
    response = ToolInvocationResponse(
        request_id=request.request_id,
        tool_id="unit_conversion.local",
        status=ToolInvocationStatus.SUCCESS,
        result={"ok": True},
        can_govern_truth=False,
    )

    with pytest.raises(ToolExecutionAuditContractError, match="tool_id"):
        build_tool_execution_audit_event(request=request, response=response)


def test_request_response_correlation_id_mismatch_is_rejected():
    request = _request()
    response = ToolInvocationResponse(
        request_id=request.request_id,
        tool_id=request.tool_id,
        status=ToolInvocationStatus.SUCCESS,
        result={"ok": True},
        correlation_id="different-correlation",
        can_govern_truth=False,
    )

    with pytest.raises(ToolExecutionAuditContractError, match="correlation_id"):
        build_tool_execution_audit_event(request=request, response=response)


def test_string_eligibility_reasons_are_rejected():
    request = _request()
    response = execute_tool_invocation(request)

    with pytest.raises(ToolExecutionAuditContractError, match="eligibility reasons"):
        build_tool_execution_audit_event(
            request=request,
            response=response,
            eligibility={"decision": "deny", "reasons": "tool_disabled"},
        )


def test_non_sequence_eligibility_reasons_are_rejected():
    request = _request()
    response = execute_tool_invocation(request)

    with pytest.raises(ToolExecutionAuditContractError, match="eligibility reasons"):
        build_tool_execution_audit_event(
            request=request,
            response=response,
            eligibility={"decision": "deny", "reasons": 123},
        )


def test_blank_eligibility_reason_is_rejected():
    request = _request()
    response = execute_tool_invocation(request)

    with pytest.raises(ToolExecutionAuditContractError, match="eligibility reasons"):
        build_tool_execution_audit_event(
            request=request,
            response=response,
            eligibility={"decision": "deny", "reasons": ["tool_disabled", " "]},
        )

def test_audit_event_is_json_serializable():
    request = _request()
    response = execute_tool_invocation(request)
    event = build_tool_execution_audit_event(
        request=request,
        response=response,
        eligibility=check_tool_eligibility(request.tool_id),
    ).to_dict()

    assert json.loads(json.dumps(event, sort_keys=True)) == event


def test_audit_event_does_not_include_raw_result_payload_by_default():
    request = _request()
    response = execute_tool_invocation(request)
    event = build_tool_execution_audit_event(request=request, response=response).to_dict()

    assert "result" not in event
    assert "response" not in event


def test_audit_event_cannot_govern_truth():
    request = _request()
    response = execute_tool_invocation(request)
    event = build_tool_execution_audit_event(request=request, response=response)

    assert event.to_dict()["can_govern_truth"] is False


def test_invalid_created_at_type_is_rejected():
    from datetime import datetime

    request = _request()
    response = execute_tool_invocation(request)

    with pytest.raises(ToolExecutionAuditContractError, match="created_at"):
        build_tool_execution_audit_event(
            request=request,
            response=response,
            created_at=datetime.utcnow(),
        )


def test_blank_created_at_is_rejected():
    request = _request()
    response = execute_tool_invocation(request)

    with pytest.raises(ToolExecutionAuditContractError, match="created_at"):
        build_tool_execution_audit_event(
            request=request,
            response=response,
            created_at="   ",
        )


def test_created_at_is_trimmed_when_valid():
    request = _request()
    response = execute_tool_invocation(request)

    event = build_tool_execution_audit_event(
        request=request,
        response=response,
        created_at="  2026-04-28T06:00:00Z  ",
    ).to_dict()

    assert event["created_at"] == "2026-04-28T06:00:00Z"

def test_invalid_event_id_is_rejected():
    request = _request()
    response = execute_tool_invocation(request)

    with pytest.raises(ToolExecutionAuditContractError, match="event_id"):
        build_tool_execution_audit_event(
            request=request,
            response=response,
            event_id="   ",
        )


def test_invalid_event_source_is_rejected():
    request = _request()
    response = execute_tool_invocation(request)

    with pytest.raises(ToolExecutionAuditContractError, match="event_source"):
        build_tool_execution_audit_event(
            request=request,
            response=response,
            event_source="",
        )


def test_audit_builder_rejects_non_request_input():
    response = execute_tool_invocation(_request())

    with pytest.raises(ToolExecutionAuditContractError, match="request"):
        build_tool_execution_audit_event(
            request={"bad": True},
            response=response,
        )


def test_audit_builder_rejects_non_response_input():
    request = _request()

    with pytest.raises(ToolExecutionAuditContractError, match="response"):
        build_tool_execution_audit_event(
            request=request,
            response={"bad": True},
        )


def test_audit_builder_does_not_execute_tools(monkeypatch):
    request = _request()
    response = execute_tool_invocation(request)
    called = {"value": False}

    def blocked_execute_tool_invocation(*args, **kwargs):
        called["value"] = True
        raise AssertionError("audit builder must not execute tools")

    monkeypatch.setattr(
        "src.application.tools.tool_execution_harness.execute_tool_invocation",
        blocked_execute_tool_invocation,
    )

    event = build_tool_execution_audit_event(
        request=request,
        response=response,
        eligibility={"decision": "allow", "reasons": ["eligible"]},
    )

    assert event.to_dict()["request_id"] == request.request_id
    assert called["value"] is False
