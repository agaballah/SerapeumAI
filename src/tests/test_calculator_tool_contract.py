from __future__ import annotations

import pytest

from src.application.tools.calculator_tool import (
    TOOL_ID,
    CalculatorToolError,
    calculate,
    calculator_tool_definition,
)
from src.application.tools.tool_registry import (
    ToolAuthorityLevel,
    ToolScope,
    ToolSideEffect,
)


def test_calculator_tool_definition_validates_against_registry_contract():
    definition = calculator_tool_definition()

    assert definition.tool_id == TOOL_ID
    assert definition.authority_level == ToolAuthorityLevel.DETERMINISTIC
    assert definition.scope == ToolScope.SESSION
    assert definition.side_effects == (ToolSideEffect.NONE,)
    assert definition.can_govern_truth is False
    assert definition.enabled_by_default is True
    assert definition.requires_project is False
    assert definition.requires_snapshot is False

    definition.validate()


@pytest.mark.parametrize(
    ("operation", "inputs", "expected"),
    [
        ("add", [2, 3], "5"),
        ("subtract", [10, 4], "6"),
        ("multiply", [6, 7], "42"),
        ("divide", [22, 7], "3.142857142857142857142857143"),
        ("power", [2, 8], "256"),
        ("sum", [1, 2, 3, 4], "10"),
        ("average", [2, 4, 6], "4"),
    ],
)
def test_calculator_operations_are_deterministic(operation, inputs, expected):
    first = calculate(operation, inputs)
    second = calculate(operation, inputs)

    assert first == second
    assert first["computed_result"] == expected
    assert first["operation"] == operation
    assert first["tool_id"] == TOOL_ID
    assert first["tool_version"] == "1.0"
    assert first["units"] == "dimensionless"
    assert first["can_govern_truth"] is False
    assert first["warnings"] == []
    assert "rounding_policy" in first
    assert "formula_or_operation" in first
    assert first["normalized_inputs"] == [str(item) for item in inputs]


def test_string_numeric_inputs_are_normalized_deterministically():
    result = calculate("add", ["2.50", "3.25"])

    assert result["normalized_inputs"] == ["2.5", "3.25"]
    assert result["computed_result"] == "5.75"


def test_operation_is_case_and_whitespace_normalized():
    result = calculate(" DIVIDE ", ["10", "4"])

    assert result["operation"] == "divide"
    assert result["computed_result"] == "2.5"


def test_division_by_zero_is_controlled():
    with pytest.raises(CalculatorToolError, match="Division by zero"):
        calculate("divide", [1, 0])


def test_invalid_operation_is_controlled():
    with pytest.raises(CalculatorToolError, match="Unsupported operation"):
        calculate("sqrt", [4])


@pytest.mark.parametrize("bad_input", ["abc", "", True, object()])
def test_non_numeric_inputs_are_rejected(bad_input):
    with pytest.raises(CalculatorToolError):
        calculate("add", [1, bad_input])


def test_empty_inputs_are_rejected():
    with pytest.raises(CalculatorToolError, match="At least one numeric input"):
        calculate("sum", [])


def test_binary_operations_require_exactly_two_inputs():
    with pytest.raises(CalculatorToolError, match="requires exactly 2 inputs"):
        calculate("add", [1, 2, 3])


def test_inputs_must_be_iterable():
    with pytest.raises(CalculatorToolError, match="inputs must be an iterable"):
        calculate("add", None)


def test_calculator_has_no_llm_provider_internet_file_db_or_runtime_dependency():
    definition = calculator_tool_definition()

    assert definition.side_effects == (ToolSideEffect.NONE,)
    assert definition.requires_consent is False
    assert definition.can_govern_truth is False

    result = calculate("multiply", [3, 5])
    assert result["computed_result"] == "15"
    assert result["can_govern_truth"] is False
