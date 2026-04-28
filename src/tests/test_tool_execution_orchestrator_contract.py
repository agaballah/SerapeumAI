from __future__ import annotations

import json

import pytest

from src.application.tools.calculator_tool import TOOL_ID as CALCULATOR_TOOL_ID
from src.application.tools.tool_execution_audit_sink import (
    InMemoryToolExecutionAuditSink,
    ToolExecutionAuditSinkResult,
)
from src.application.tools.tool_execution_orchestrator import (
    ToolExecutionOrchestrationResult,
    ToolExecutionOrchestratorContractError,
    execute_tool_with_audit,
)
from src.application.tools.tool_invocation_contract import ToolInvocationRequest


def _request(
    tool_id: str = CALCULATOR_TOOL_ID,
    arguments: dict | None = None,
    request_id: str = "req-001",
):
    return ToolInvocationRequest(
        request_id=request_id,
        tool_id=tool_id,
        arguments=arguments or {"operation": "add", "operands": [1, 2]},
        correlation_id="chat-001",
        requested_by="test",
        consent_granted=False,
    )


def test_successful_calculator_request_returns_execution_and_audit_result():
    result = execute_tool_with_audit(
        _request(),
        event_id="evt-001",
        created_at="2026-04-28T06:00:00Z",
    ).to_dict()

    assert result["request_id"] == "req-001"
    assert result["tool_id"] == CALCULATOR_TOOL_ID
    assert result["response_status"] == "success"
    assert result["audit_sink_name"] == "noop_tool_execution_audit_sink"
    assert result["audit_accepted"] is True
    assert result["tool_response"]["result"]["computed_result"] == "3"
    assert result["tool_response"]["can_govern_truth"] is False
    assert result["audit_sink_result"]["accepted"] is True
    assert result["audit_sink_result"]["can_govern_truth"] is False
    assert result["can_govern_truth"] is False


def test_unknown_tool_keeps_tool_error_visible_and_still_audits():
    result = execute_tool_with_audit(
        _request(tool_id="unknown.local", arguments={"operation": "add"}),
        event_id="evt-unknown",
    ).to_dict()

    assert result["response_status"] == "error"
    assert result["tool_response"]["status"] == "error"
    assert result["tool_response"]["error"]["error_type"] == "tool_not_eligible"
    assert result["audit_accepted"] is True
    assert result["audit_sink_result"]["event_id"] == "evt-unknown"
    assert result["can_govern_truth"] is False


def test_default_sink_is_noop_and_does_not_store_events():
    result = execute_tool_with_audit(_request()).to_dict()

    assert result["audit_sink_name"] == "noop_tool_execution_audit_sink"
    assert result["audit_accepted"] is True


def test_injected_in_memory_sink_receives_exactly_one_event():
    sink = InMemoryToolExecutionAuditSink()

    result = execute_tool_with_audit(
        _request(),
        audit_sink=sink,
        event_id="evt-001",
    ).to_dict()

    assert result["audit_sink_name"] == "in_memory_tool_execution_audit_sink"
    assert result["audit_accepted"] is True
    assert len(sink.events()) == 1
    assert sink.events()[0]["event_id"] == "evt-001"
    assert sink.events()[0]["request_id"] == "req-001"


def test_invalid_request_object_is_rejected():
    with pytest.raises(ToolExecutionOrchestratorContractError, match="ToolInvocationRequest"):
        execute_tool_with_audit({"bad": True})


def test_invalid_sink_object_is_rejected():
    with pytest.raises(ToolExecutionOrchestratorContractError, match="accept"):
        execute_tool_with_audit(_request(), audit_sink=object())


def test_sink_rejection_is_visible_without_hiding_tool_response():
    class RejectingSink:
        sink_name = "rejecting_sink"

        def accept(self, event):
            return ToolExecutionAuditSinkResult(
                sink_name=self.sink_name,
                accepted=False,
                event_id=event.event_id,
                request_id=event.request_id,
                tool_id=event.tool_id,
                response_status=event.response_status,
                error={"error_type": "sink_rejected", "message": "blocked"},
                can_govern_truth=False,
            )

    result = execute_tool_with_audit(
        _request(),
        audit_sink=RejectingSink(),
        event_id="evt-001",
    ).to_dict()

    assert result["response_status"] == "success"
    assert result["tool_response"]["status"] == "success"
    assert result["audit_accepted"] is False
    assert result["audit_sink_result"]["error"]["error_type"] == "sink_rejected"


def test_audit_event_build_error_is_visible_without_hiding_tool_response():
    result = execute_tool_with_audit(
        _request(),
        event_id="   ",
    ).to_dict()

    assert result["response_status"] == "success"
    assert result["tool_response"]["status"] == "success"
    assert result["audit_accepted"] is False
    assert result["audit_sink_result"]["error"]["error_type"] == "audit_event_build_error"
    assert "event_id" in result["audit_sink_result"]["error"]["message"]


def test_orchestration_result_is_json_serializable():
    result = execute_tool_with_audit(_request()).to_dict()

    assert json.loads(json.dumps(result, sort_keys=True)) == result


def test_orchestration_result_cannot_govern_truth():
    with pytest.raises(ToolExecutionOrchestratorContractError, match="cannot govern truth"):
        ToolExecutionOrchestrationResult(
            request_id="req-001",
            tool_id=CALCULATOR_TOOL_ID,
            response_status="success",
            audit_sink_name="sink",
            audit_accepted=True,
            tool_response={"status": "success"},
            audit_sink_result={"accepted": True},
            can_govern_truth=True,
        ).to_dict()


def test_orchestration_result_requires_mapping_payloads():
    with pytest.raises(ToolExecutionOrchestratorContractError, match="tool_response"):
        ToolExecutionOrchestrationResult(
            request_id="req-001",
            tool_id=CALCULATOR_TOOL_ID,
            response_status="success",
            audit_sink_name="sink",
            audit_accepted=True,
            tool_response="bad",
            audit_sink_result={"accepted": True},
            can_govern_truth=False,
        ).to_dict()

    with pytest.raises(ToolExecutionOrchestratorContractError, match="audit_sink_result"):
        ToolExecutionOrchestrationResult(
            request_id="req-001",
            tool_id=CALCULATOR_TOOL_ID,
            response_status="success",
            audit_sink_name="sink",
            audit_accepted=True,
            tool_response={"status": "success"},
            audit_sink_result="bad",
            can_govern_truth=False,
        ).to_dict()


def test_orchestrator_does_not_write_or_persist_by_contract(tmp_path):
    before = set(tmp_path.iterdir())

    execute_tool_with_audit(_request())

    after = set(tmp_path.iterdir())
    assert after == before


def test_orchestrator_does_not_parse_chat_or_llm_tool_calls():
    result = execute_tool_with_audit(
        _request(arguments={"operation": "add", "operands": [1, 2]})
    ).to_dict()

    assert "chat_message" not in result
    assert "llm_tool_call" not in result
    assert "router_decision" not in result

def test_falsey_injected_sink_is_honored():
    class FalseySink:
        sink_name = "falsey_sink"

        def __init__(self):
            self.events = []

        def __bool__(self):
            return False

        def accept(self, event):
            self.events.append(event.to_dict())
            return ToolExecutionAuditSinkResult(
                sink_name=self.sink_name,
                accepted=True,
                event_id=event.event_id,
                request_id=event.request_id,
                tool_id=event.tool_id,
                response_status=event.response_status,
                error=None,
                can_govern_truth=False,
            )

    sink = FalseySink()

    result = execute_tool_with_audit(
        _request(),
        audit_sink=sink,
        event_id="evt-falsey",
    ).to_dict()

    assert result["audit_sink_name"] == "falsey_sink"
    assert result["audit_accepted"] is True
    assert len(sink.events) == 1
    assert sink.events[0]["event_id"] == "evt-falsey"


def test_request_validation_error_during_audit_build_is_controlled():
    result = execute_tool_with_audit(
        _request(request_id="   "),
        event_id="evt-invalid-request",
    ).to_dict()

    assert result["response_status"] == "error"
    assert result["tool_response"]["status"] == "error"
    assert result["audit_accepted"] is False
    assert result["audit_sink_result"]["error"]["error_type"] == "audit_event_build_error"
    assert "request_id" in result["audit_sink_result"]["error"]["message"]
