from __future__ import annotations

import json

import pytest

from src.application.tools.calculator_tool import (
    TOOL_ID as CALCULATOR_TOOL_ID,
    calculator_tool_definition,
)
from src.application.tools.quantity_formula_tool import TOOL_ID as QUANTITY_FORMULA_TOOL_ID
from src.application.tools.tool_execution_harness import (
    ToolExecutionHarnessError,
    execute_tool_invocation,
)
from src.application.tools.tool_invocation_contract import ToolInvocationRequest
from src.application.tools.tool_registry import ToolDefinition
from src.application.tools.unit_conversion_tool import TOOL_ID as UNIT_CONVERSION_TOOL_ID


def _request(tool_id: str, arguments: dict, request_id: str = "req-001"):
    return ToolInvocationRequest(
        request_id=request_id,
        tool_id=tool_id,
        arguments=arguments,
        correlation_id="chat-001",
        requested_by="test",
    )


def test_valid_calculator_request_executes_successfully():
    response = execute_tool_invocation(
        _request(
            CALCULATOR_TOOL_ID,
            {"operation": "add", "operands": [1, 2]},
        )
    )

    out = response.to_dict()
    assert out["status"] == "success"
    assert out["request_id"] == "req-001"
    assert out["tool_id"] == CALCULATOR_TOOL_ID
    assert out["correlation_id"] == "chat-001"
    assert out["result"]["computed_result"] == "3"
    assert out["result"]["can_govern_truth"] is False
    assert out["error"] is None
    assert out["can_govern_truth"] is False


def test_valid_calculator_request_accepts_inputs_alias():
    response = execute_tool_invocation(
        _request(
            CALCULATOR_TOOL_ID,
            {"operation": "multiply", "inputs": [6, 7]},
        )
    )

    assert response.to_dict()["result"]["computed_result"] == "42"


def test_valid_unit_conversion_request_executes_successfully():
    response = execute_tool_invocation(
        _request(
            UNIT_CONVERSION_TOOL_ID,
            {
                "value": 1,
                "from_unit": "m",
                "to_unit": "cm",
                "dimension": "length",
            },
            request_id="req-002",
        )
    )

    out = response.to_dict()
    assert out["status"] == "success"
    assert out["request_id"] == "req-002"
    assert out["tool_id"] == UNIT_CONVERSION_TOOL_ID
    assert out["result"]["converted_value"] == "100"
    assert out["can_govern_truth"] is False


def test_valid_quantity_formula_request_executes_successfully():
    response = execute_tool_invocation(
        _request(
            QUANTITY_FORMULA_TOOL_ID,
            {
                "formula_id": "rectangle_area",
                "inputs": {"length": 2, "width": 3},
            },
            request_id="req-003",
        )
    )

    out = response.to_dict()
    assert out["status"] == "success"
    assert out["request_id"] == "req-003"
    assert out["tool_id"] == QUANTITY_FORMULA_TOOL_ID
    assert out["result"]["computed_result"] == "6"
    assert out["can_govern_truth"] is False


def test_unknown_tool_returns_controlled_error_without_execution():
    called = {"value": False}

    def blocked_executor(arguments):
        called["value"] = True
        return {"bad": True}

    response = execute_tool_invocation(
        _request("unknown.local", {"operation": "add"}),
        executors={"unknown.local": blocked_executor},
    )

    out = response.to_dict()
    assert out["status"] == "error"
    assert out["result"] is None
    assert out["error"]["error_type"] == "tool_not_eligible"
    assert called["value"] is False
    assert out["can_govern_truth"] is False


def test_ineligible_tool_returns_controlled_error_and_does_not_execute():
    base = calculator_tool_definition()
    disabled = ToolDefinition(
        tool_id=base.tool_id,
        display_name=base.display_name,
        description=base.description,
        input_schema=base.input_schema,
        output_schema=base.output_schema,
        authority_level=base.authority_level,
        scope=base.scope,
        side_effects=base.side_effects,
        requires_consent=base.requires_consent,
        can_govern_truth=base.can_govern_truth,
        audit_log_required=base.audit_log_required,
        enabled_by_default=False,
        requires_project=base.requires_project,
        requires_snapshot=base.requires_snapshot,
        result_provenance_required=base.result_provenance_required,
    )

    called = {"value": False}

    def blocked_executor(arguments):
        called["value"] = True
        return {"bad": True}

    response = execute_tool_invocation(
        _request(CALCULATOR_TOOL_ID, {"operation": "add", "operands": [1, 2]}),
        executors={CALCULATOR_TOOL_ID: blocked_executor},
        definition_factories={CALCULATOR_TOOL_ID: lambda: disabled},
    )

    out = response.to_dict()
    assert out["status"] == "error"
    assert out["error"]["error_type"] == "tool_not_eligible"
    assert "tool_disabled" in out["error"]["details"]["reasons"]
    assert called["value"] is False


def test_bad_arguments_return_controlled_error_response():
    response = execute_tool_invocation(
        _request(CALCULATOR_TOOL_ID, {"operation": "add"})
    )

    out = response.to_dict()
    assert out["status"] == "error"
    assert out["result"] is None
    assert out["error"]["error_type"] == "tool_execution_error"
    assert "operands or inputs" in out["error"]["message"]


def test_tool_implementation_error_returns_controlled_error_response():
    def failing_executor(arguments):
        raise RuntimeError("boom")

    response = execute_tool_invocation(
        _request(CALCULATOR_TOOL_ID, {"operation": "add", "operands": [1, 2]}),
        executors={CALCULATOR_TOOL_ID: failing_executor},
    )

    out = response.to_dict()
    assert out["status"] == "error"
    assert out["result"] is None
    assert out["error"]["error_type"] == "tool_execution_error"
    assert out["error"]["message"] == "boom"
    assert out["can_govern_truth"] is False


def test_request_must_be_tool_invocation_request():
    with pytest.raises(ToolExecutionHarnessError, match="ToolInvocationRequest"):
        execute_tool_invocation({"tool_id": CALCULATOR_TOOL_ID})


def test_invalid_request_returns_controlled_error_response():
    response = execute_tool_invocation(
        ToolInvocationRequest(
            request_id="",
            tool_id=CALCULATOR_TOOL_ID,
            arguments={"operation": "add"},
        )
    )

    out = response.to_dict()
    assert out["status"] == "error"
    assert out["error"]["error_type"] == "invalid_request"
    assert out["can_govern_truth"] is False


def test_success_and_error_responses_are_json_serializable():
    success = execute_tool_invocation(
        _request(CALCULATOR_TOOL_ID, {"operation": "add", "operands": [1, 2]})
    )
    error = execute_tool_invocation(
        _request("unknown.local", {"operation": "add"})
    )

    assert json.loads(json.dumps(success.to_dict(), sort_keys=True)) == success.to_dict()
    assert json.loads(json.dumps(error.to_dict(), sort_keys=True)) == error.to_dict()


def test_all_responses_keep_truth_governance_false():
    responses = [
        execute_tool_invocation(
            _request(CALCULATOR_TOOL_ID, {"operation": "add", "operands": [1, 2]})
        ),
        execute_tool_invocation(_request("unknown.local", {"operation": "add"})),
        execute_tool_invocation(_request(CALCULATOR_TOOL_ID, {"operation": "add"})),
    ]

    for response in responses:
        assert response.to_dict()["can_govern_truth"] is False
