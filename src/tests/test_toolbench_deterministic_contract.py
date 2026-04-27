from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, Callable

import pytest

from src.application.tools.calculator_tool import (
    TOOL_ID as CALCULATOR_TOOL_ID,
    calculate,
    calculator_tool_definition,
)
from src.application.tools.quantity_formula_tool import (
    TOOL_ID as QUANTITY_FORMULA_TOOL_ID,
    evaluate_formula,
    quantity_formula_tool_definition,
)
from src.application.tools.tool_registry import (
    ToolAuthorityLevel,
    ToolScope,
    ToolSideEffect,
)
from src.application.tools.unit_conversion_tool import (
    TOOL_ID as UNIT_CONVERSION_TOOL_ID,
    convert_unit,
    unit_conversion_tool_definition,
)

COMMON_RESULT_FIELDS = {
    "operation",
    "tool_id",
    "tool_version",
    "rounding_policy",
    "warnings",
    "formula_or_operation",
    "can_govern_truth",
}


def _calculator_sample() -> dict[str, Any]:
    return calculate("multiply", [6, 7])


def _unit_conversion_sample() -> dict[str, Any]:
    return convert_unit(1, "m", "cm", "length")


def _quantity_formula_sample() -> dict[str, Any]:
    return evaluate_formula("rectangle_area", {"length": 3, "width": 5})


TOOL_CASES: tuple[
    tuple[str, Callable[[], Any], Callable[[], Mapping[str, Any]]],
    ...,
] = (
    (CALCULATOR_TOOL_ID, calculator_tool_definition, _calculator_sample),
    (UNIT_CONVERSION_TOOL_ID, unit_conversion_tool_definition, _unit_conversion_sample),
    (
        QUANTITY_FORMULA_TOOL_ID,
        quantity_formula_tool_definition,
        _quantity_formula_sample,
    ),
)


@pytest.mark.parametrize(("tool_id", "definition_factory", "sample_factory"), TOOL_CASES)
def test_deterministic_tool_definitions_share_safe_registry_contract(
    tool_id, definition_factory, sample_factory
):
    definition = definition_factory()

    assert definition.tool_id == tool_id
    assert definition.authority_level == ToolAuthorityLevel.DETERMINISTIC
    assert definition.scope == ToolScope.SESSION
    assert definition.side_effects == (ToolSideEffect.NONE,)
    assert definition.requires_consent is False
    assert definition.can_govern_truth is False
    assert definition.audit_log_required is True
    assert definition.enabled_by_default is True
    assert definition.requires_project is False
    assert definition.requires_snapshot is False

    definition.validate()


@pytest.mark.parametrize(("tool_id", "definition_factory", "sample_factory"), TOOL_CASES)
def test_deterministic_tool_results_share_minimum_envelope(
    tool_id, definition_factory, sample_factory
):
    result = sample_factory()

    assert isinstance(result, dict)
    assert COMMON_RESULT_FIELDS.issubset(result)
    assert result["tool_id"] == tool_id
    assert isinstance(result["operation"], str)
    assert result["operation"]
    assert isinstance(result["tool_version"], str)
    assert result["tool_version"]
    assert isinstance(result["rounding_policy"], str)
    assert result["rounding_policy"]
    assert isinstance(result["warnings"], list)
    assert isinstance(result["formula_or_operation"], str)
    assert result["formula_or_operation"]
    assert result["can_govern_truth"] is False


@pytest.mark.parametrize(("tool_id", "definition_factory", "sample_factory"), TOOL_CASES)
def test_deterministic_tool_results_are_repeatable(
    tool_id, definition_factory, sample_factory
):
    first = sample_factory()
    second = sample_factory()

    assert first == second


@pytest.mark.parametrize(("tool_id", "definition_factory", "sample_factory"), TOOL_CASES)
def test_deterministic_tool_results_are_json_serializable_plain_mappings(
    tool_id, definition_factory, sample_factory
):
    result = sample_factory()

    encoded = json.dumps(result, sort_keys=True)
    decoded = json.loads(encoded)

    assert isinstance(decoded, dict)
    assert decoded == result


@pytest.mark.parametrize(("tool_id", "definition_factory", "sample_factory"), TOOL_CASES)
def test_deterministic_tool_results_do_not_claim_truth_authority(
    tool_id, definition_factory, sample_factory
):
    definition = definition_factory()
    result = sample_factory()

    assert definition.can_govern_truth is False
    assert result["can_govern_truth"] is False
    assert "certified" not in result
    assert "fact_state" not in result
    assert "truth_state" not in result
