from __future__ import annotations

import json

import pytest

from src.application.tools.tool_invocation_contract import (
    ToolInvocationContractError,
    ToolInvocationRequest,
    ToolInvocationResponse,
    ToolInvocationStatus,
)


def test_valid_request_validates_and_serializes():
    request = ToolInvocationRequest(
        request_id="req-001",
        tool_id="calculator.local",
        arguments={"operation": "add", "inputs": [1, 2]},
        correlation_id="chat-001",
        requested_by="test",
    )

    request.validate()

    assert request.to_dict() == {
        "request_id": "req-001",
        "tool_id": "calculator.local",
        "arguments": {"operation": "add", "inputs": [1, 2]},
        "correlation_id": "chat-001",
        "requested_by": "test",
        "consent_granted": False,
    }


def test_request_defaults_are_safe():
    request = ToolInvocationRequest(
        request_id="req-001",
        tool_id="calculator.local",
    )

    assert request.to_dict()["arguments"] == {}
    assert request.to_dict()["correlation_id"] is None
    assert request.to_dict()["requested_by"] == "system"
    assert request.to_dict()["consent_granted"] is False


@pytest.mark.parametrize("bad_value", ["", "   ", None])
def test_invalid_request_id_is_rejected(bad_value):
    with pytest.raises(ToolInvocationContractError, match="request_id"):
        ToolInvocationRequest(request_id=bad_value, tool_id="calculator.local").validate()


@pytest.mark.parametrize("bad_value", ["", "   ", None])
def test_invalid_tool_id_is_rejected(bad_value):
    with pytest.raises(ToolInvocationContractError, match="tool_id"):
        ToolInvocationRequest(request_id="req-001", tool_id=bad_value).validate()


def test_non_mapping_arguments_are_rejected():
    with pytest.raises(ToolInvocationContractError, match="arguments"):
        ToolInvocationRequest(
            request_id="req-001",
            tool_id="calculator.local",
            arguments=["not", "mapping"],
        ).validate()


def test_non_string_argument_keys_are_rejected():
    with pytest.raises(ToolInvocationContractError, match="arguments keys"):
        ToolInvocationRequest(
            request_id="req-001",
            tool_id="calculator.local",
            arguments={1: "bad"},
        ).validate()


def test_consent_granted_must_be_boolean():
    with pytest.raises(ToolInvocationContractError, match="consent_granted"):
        ToolInvocationRequest(
            request_id="req-001",
            tool_id="calculator.local",
            consent_granted="yes",
        ).validate()


def test_valid_success_response_validates_and_serializes():
    response = ToolInvocationResponse(
        request_id="req-001",
        tool_id="calculator.local",
        status=ToolInvocationStatus.SUCCESS,
        result={
            "operation": "calculate",
            "tool_id": "calculator.local",
            "tool_version": "1.0",
            "rounding_policy": "none",
            "warnings": [],
            "formula_or_operation": "1 + 2",
            "can_govern_truth": False,
            "computed_result": "3",
        },
        correlation_id="chat-001",
    )

    response.validate()

    out = response.to_dict()
    assert out["status"] == "success"
    assert out["result"]["computed_result"] == "3"
    assert out["error"] is None
    assert out["can_govern_truth"] is False


def test_valid_error_response_validates_and_serializes():
    response = ToolInvocationResponse(
        request_id="req-001",
        tool_id="calculator.local",
        status=ToolInvocationStatus.ERROR,
        error={
            "error_type": "validation_error",
            "message": "Invalid arguments",
        },
    )

    response.validate()

    out = response.to_dict()
    assert out["status"] == "error"
    assert out["result"] is None
    assert out["error"]["error_type"] == "validation_error"
    assert out["can_govern_truth"] is False


def test_success_response_requires_result():
    with pytest.raises(ToolInvocationContractError, match="requires result"):
        ToolInvocationResponse(
            request_id="req-001",
            tool_id="calculator.local",
            status=ToolInvocationStatus.SUCCESS,
        ).validate()


def test_success_response_cannot_include_error():
    with pytest.raises(ToolInvocationContractError, match="cannot include error"):
        ToolInvocationResponse(
            request_id="req-001",
            tool_id="calculator.local",
            status=ToolInvocationStatus.SUCCESS,
            result={"ok": True},
            error={"message": "bad"},
        ).validate()


def test_error_response_requires_error():
    with pytest.raises(ToolInvocationContractError, match="requires error"):
        ToolInvocationResponse(
            request_id="req-001",
            tool_id="calculator.local",
            status=ToolInvocationStatus.ERROR,
        ).validate()


def test_error_response_cannot_include_result():
    with pytest.raises(ToolInvocationContractError, match="cannot include result"):
        ToolInvocationResponse(
            request_id="req-001",
            tool_id="calculator.local",
            status=ToolInvocationStatus.ERROR,
            result={"ok": True},
            error={"message": "bad"},
        ).validate()


def test_unknown_status_is_rejected():
    with pytest.raises(ToolInvocationContractError, match="Unsupported status"):
        ToolInvocationResponse(
            request_id="req-001",
            tool_id="calculator.local",
            status="pending",
            result={"ok": True},
        ).validate()


def test_response_cannot_govern_truth():
    with pytest.raises(ToolInvocationContractError, match="cannot govern truth"):
        ToolInvocationResponse(
            request_id="req-001",
            tool_id="calculator.local",
            status=ToolInvocationStatus.SUCCESS,
            result={"ok": True},
            can_govern_truth=True,
        ).validate()


def test_request_and_response_are_json_serializable():
    request = ToolInvocationRequest(
        request_id="req-001",
        tool_id="calculator.local",
        arguments={"operation": "add"},
    )
    response = ToolInvocationResponse(
        request_id="req-001",
        tool_id="calculator.local",
        status="success",
        result={"operation": "calculate", "can_govern_truth": False},
    )

    assert json.loads(json.dumps(request.to_dict())) == request.to_dict()
    assert json.loads(json.dumps(response.to_dict())) == response.to_dict()


def test_contract_does_not_execute_tools(monkeypatch):
    executed = {"called": False}

    def fake_execute(*args, **kwargs):
        executed["called"] = True
        return {"bad": True}

    monkeypatch.setitem(globals(), "fake_execute", fake_execute)

    request = ToolInvocationRequest(
        request_id="req-001",
        tool_id="calculator.local",
        arguments={"operation": "multiply", "inputs": [6, 7]},
    )
    response = ToolInvocationResponse(
        request_id=request.request_id,
        tool_id=request.tool_id,
        status=ToolInvocationStatus.ERROR,
        error={"error_type": "not_executed", "message": "Contract only"},
    )

    assert request.to_dict()["arguments"]["operation"] == "multiply"
    assert response.to_dict()["error"]["error_type"] == "not_executed"
    assert executed["called"] is False
