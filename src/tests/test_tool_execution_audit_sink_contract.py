from __future__ import annotations

import json

import pytest

from src.application.tools.calculator_tool import TOOL_ID as CALCULATOR_TOOL_ID
from src.application.tools.tool_execution_audit import (
    build_tool_execution_audit_event,
)
from src.application.tools.tool_execution_audit_sink import (
    InMemoryToolExecutionAuditSink,
    NoopToolExecutionAuditSink,
    ToolExecutionAuditSinkContractError,
    ToolExecutionAuditSinkResult,
    accept_tool_execution_audit_event,
)
from src.application.tools.tool_execution_harness import execute_tool_invocation
from src.application.tools.tool_invocation_contract import ToolInvocationRequest


def _request():
    return ToolInvocationRequest(
        request_id="req-001",
        tool_id=CALCULATOR_TOOL_ID,
        arguments={"operation": "add", "operands": [1, 2]},
        correlation_id="chat-001",
        requested_by="test",
        consent_granted=False,
    )


def _audit_event():
    request = _request()
    response = execute_tool_invocation(request)
    return build_tool_execution_audit_event(
        request=request,
        response=response,
        event_id="evt-001",
        created_at="2026-04-28T06:00:00Z",
    )


def test_noop_sink_accepts_valid_audit_event_without_storage():
    sink = NoopToolExecutionAuditSink()
    result = sink.accept(_audit_event()).to_dict()

    assert result == {
        "sink_name": "noop_tool_execution_audit_sink",
        "accepted": True,
        "event_id": "evt-001",
        "request_id": "req-001",
        "tool_id": CALCULATOR_TOOL_ID,
        "response_status": "success",
        "error": None,
        "can_govern_truth": False,
    }
    assert not hasattr(sink, "_events")


def test_in_memory_sink_accepts_valid_audit_event_in_process_only():
    sink = InMemoryToolExecutionAuditSink()
    event = _audit_event()

    result = sink.accept(event).to_dict()

    assert result["accepted"] is True
    assert result["sink_name"] == "in_memory_tool_execution_audit_sink"
    assert result["event_id"] == "evt-001"
    assert len(sink.events()) == 1
    assert sink.events()[0]["event_id"] == "evt-001"


def test_in_memory_events_returns_snapshot_not_mutable_store():
    sink = InMemoryToolExecutionAuditSink()
    sink.accept(_audit_event())

    snapshot = sink.events()
    snapshot[0]["event_id"] = "mutated"

    assert sink.events()[0]["event_id"] == "evt-001"


def test_accept_helper_uses_sink_protocol():
    result = accept_tool_execution_audit_event(
        NoopToolExecutionAuditSink(),
        _audit_event(),
    ).to_dict()

    assert result["accepted"] is True
    assert result["sink_name"] == "noop_tool_execution_audit_sink"


def test_accept_helper_rejects_object_without_accept():
    with pytest.raises(ToolExecutionAuditSinkContractError, match="accept"):
        accept_tool_execution_audit_event(object(), _audit_event())


@pytest.mark.parametrize(
    "sink",
    [NoopToolExecutionAuditSink(), InMemoryToolExecutionAuditSink()],
)
def test_sinks_reject_raw_dict_event_with_controlled_error(sink):
    result = sink.accept({"event_id": "evt-001"}).to_dict()

    assert result["accepted"] is False
    assert result["error"]["error_type"] == "invalid_event"
    assert "ToolExecutionAuditEvent" in result["error"]["message"]
    assert result["can_govern_truth"] is False


def test_sink_result_is_json_serializable():
    result = NoopToolExecutionAuditSink().accept(_audit_event()).to_dict()

    assert json.loads(json.dumps(result, sort_keys=True)) == result


def test_sink_result_cannot_govern_truth():
    with pytest.raises(ToolExecutionAuditSinkContractError, match="cannot govern truth"):
        ToolExecutionAuditSinkResult(
            sink_name="bad_sink",
            accepted=True,
            event_id="evt-001",
            request_id="req-001",
            tool_id=CALCULATOR_TOOL_ID,
            response_status="success",
            error=None,
            can_govern_truth=True,
        ).to_dict()


def test_accepted_sink_result_cannot_include_error():
    with pytest.raises(ToolExecutionAuditSinkContractError, match="must not include an error"):
        ToolExecutionAuditSinkResult(
            sink_name="bad_sink",
            accepted=True,
            event_id="evt-001",
            request_id="req-001",
            tool_id=CALCULATOR_TOOL_ID,
            response_status="success",
            error={"error_type": "bad"},
            can_govern_truth=False,
        ).to_dict()


def test_rejected_sink_result_must_include_error_mapping():
    with pytest.raises(ToolExecutionAuditSinkContractError, match="must include"):
        ToolExecutionAuditSinkResult(
            sink_name="bad_sink",
            accepted=False,
            event_id=None,
            request_id=None,
            tool_id=None,
            response_status=None,
            error=None,
            can_govern_truth=False,
        ).to_dict()


def test_invalid_sink_name_is_rejected():
    with pytest.raises(ToolExecutionAuditSinkContractError, match="sink_name"):
        ToolExecutionAuditSinkResult(
            sink_name="",
            accepted=True,
            event_id="evt-001",
            request_id="req-001",
            tool_id=CALCULATOR_TOOL_ID,
            response_status="success",
            error=None,
            can_govern_truth=False,
        ).to_dict()


def test_sink_interface_does_not_execute_tools(monkeypatch):
    event = _audit_event()
    called = {"value": False}

    def blocked_execute_tool_invocation(*args, **kwargs):
        called["value"] = True
        raise AssertionError("sink must not execute tools")

    monkeypatch.setattr(
        "src.application.tools.tool_execution_harness.execute_tool_invocation",
        blocked_execute_tool_invocation,
    )

    result = NoopToolExecutionAuditSink().accept(event).to_dict()

    assert result["accepted"] is True
    assert called["value"] is False
