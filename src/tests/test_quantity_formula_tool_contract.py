from __future__ import annotations

import pytest

from src.application.tools.quantity_formula_tool import (
    TOOL_ID,
    QuantityFormulaToolError,
    evaluate_formula,
    quantity_formula_tool_definition,
)
from src.application.tools.tool_registry import (
    ToolAuthorityLevel,
    ToolScope,
    ToolSideEffect,
)


def test_quantity_formula_tool_definition_validates_against_registry_contract():
    definition = quantity_formula_tool_definition()

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
    ("formula_id", "inputs", "expected", "result_unit"),
    [
        ("rectangle_area", {"length": 5, "width": 4}, "20", "derived_area"),
        ("room_volume", {"length": 5, "width": 4, "height": 3}, "60", "derived_volume"),
        ("concrete_volume", {"length": 10, "width": 2, "thickness": "0.15"}, "3", "derived_volume"),
        ("percentage_ratio", {"part": 25, "whole": 200}, "12.5", "percent"),
        ("progress_ratio", {"completed": 30, "total": 40}, "75", "percent"),
        ("density_mass", {"density": 2400, "volume": 2}, "4800", "derived_mass"),
        ("linear_weight", {"unit_weight": 12, "length": 3}, "36", "derived_weight"),
        ("circle_area", {"radius": 2}, "12.56637061435917295385057353", "derived_area"),
    ],
)
def test_supported_formulas_are_deterministic(formula_id, inputs, expected, result_unit):
    first = evaluate_formula(formula_id, inputs)
    second = evaluate_formula(formula_id, inputs)

    assert first == second
    assert first["operation"] == "quantity_formula"
    assert first["formula_id"] == formula_id
    assert first["computed_result"] == expected
    assert first["result_unit"] == result_unit
    assert first["tool_id"] == TOOL_ID
    assert first["tool_version"] == "1.0"
    assert first["warnings"] == []
    assert first["can_govern_truth"] is False
    assert "rounding_policy" in first
    assert "formula_or_operation" in first
    assert isinstance(first["normalized_inputs"], dict)


def test_formula_id_is_case_and_whitespace_normalized():
    result = evaluate_formula(" RECTANGLE_AREA ", {"length": "2.50", "width": "4"})

    assert result["formula_id"] == "rectangle_area"
    assert result["normalized_inputs"] == {"length": "2.5", "width": "4"}
    assert result["computed_result"] == "10"


def test_unsupported_formula_is_controlled():
    with pytest.raises(QuantityFormulaToolError, match="Unsupported formula"):
        evaluate_formula("triangle_area", {"base": 2, "height": 3})


def test_missing_required_input_is_controlled():
    with pytest.raises(QuantityFormulaToolError, match="Missing required input"):
        evaluate_formula("rectangle_area", {"length": 2})


def test_extra_input_is_rejected():
    with pytest.raises(QuantityFormulaToolError, match="Unsupported extra input"):
        evaluate_formula("rectangle_area", {"length": 2, "width": 3, "height": 4})


@pytest.mark.parametrize("bad_input", ["abc", "", True, object()])
def test_non_numeric_inputs_are_rejected(bad_input):
    with pytest.raises(QuantityFormulaToolError):
        evaluate_formula("rectangle_area", {"length": 2, "width": bad_input})


def test_inputs_must_be_mapping():
    with pytest.raises(QuantityFormulaToolError, match="inputs must be a mapping"):
        evaluate_formula("rectangle_area", None)


def test_division_by_zero_in_percentage_ratio_is_controlled():
    with pytest.raises(QuantityFormulaToolError, match="Division by zero"):
        evaluate_formula("percentage_ratio", {"part": 1, "whole": 0})


def test_division_by_zero_in_progress_ratio_is_controlled():
    with pytest.raises(QuantityFormulaToolError, match="Division by zero"):
        evaluate_formula("progress_ratio", {"completed": 1, "total": 0})


def test_negative_physical_dimension_is_rejected():
    with pytest.raises(QuantityFormulaToolError, match="Negative physical"):
        evaluate_formula("room_volume", {"length": 2, "width": -3, "height": 4})


def test_negative_ratio_input_is_rejected():
    with pytest.raises(QuantityFormulaToolError, match="Negative ratio"):
        evaluate_formula("progress_ratio", {"completed": -1, "total": 10})


def test_quantity_formula_has_no_llm_provider_internet_file_db_or_runtime_dependency():
    definition = quantity_formula_tool_definition()

    assert definition.side_effects == (ToolSideEffect.NONE,)
    assert definition.requires_consent is False
    assert definition.can_govern_truth is False

    result = evaluate_formula("rectangle_area", {"length": 3, "width": 5})
    assert result["computed_result"] == "15"
    assert result["can_govern_truth"] is False
