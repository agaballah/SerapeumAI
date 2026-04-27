from __future__ import annotations

import pytest

from src.application.tools.tool_registry import (
    ToolAuthorityLevel,
    ToolScope,
    ToolSideEffect,
)
from src.application.tools.unit_conversion_tool import (
    TOOL_ID,
    UnitConversionToolError,
    convert_unit,
    unit_conversion_tool_definition,
)


def test_unit_conversion_tool_definition_validates_against_registry_contract():
    definition = unit_conversion_tool_definition()

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
    ("dimension", "value", "from_unit", "to_unit", "expected"),
    [
        ("length", 1000, "mm", "m", "1"),
        ("length", 1, "ft", "in", "12"),
        ("area", 1, "m2", "ft2", "10.76391041670972230833350556"),
        ("volume", 1, "m3", "l", "1000"),
        ("mass", 1, "tonne", "kg", "1000"),
        ("force", 1, "kN", "N", "1000"),
        ("pressure", 1, "MPa", "kPa", "1000"),
    ],
)
def test_linear_unit_conversions_are_deterministic(
    dimension, value, from_unit, to_unit, expected
):
    first = convert_unit(value, from_unit, to_unit, dimension)
    second = convert_unit(value, from_unit, to_unit, dimension)

    assert first == second
    assert first["operation"] == "unit_conversion"
    assert first["dimension"] == dimension
    assert first["input_value"] == str(value)
    assert first["from_unit"] == from_unit
    assert first["to_unit"] == to_unit
    assert first["converted_value"] == expected
    assert first["tool_id"] == TOOL_ID
    assert first["tool_version"] == "1.0"
    assert first["warnings"] == []
    assert first["can_govern_truth"] is False
    assert "rounding_policy" in first
    assert "formula_or_operation" in first


@pytest.mark.parametrize(
    ("value", "from_unit", "to_unit", "expected"),
    [
        (0, "C", "F", "32"),
        (32, "F", "C", "0"),
        (0, "C", "K", "273.15"),
        (273.15, "K", "C", "0"),
    ],
)
def test_temperature_offset_conversions_are_deterministic(
    value, from_unit, to_unit, expected
):
    result = convert_unit(value, from_unit, to_unit, "temperature")

    assert result["dimension"] == "temperature"
    assert result["from_unit"] == from_unit
    assert result["to_unit"] == to_unit
    assert result["converted_value"] == expected
    assert result["can_govern_truth"] is False


def test_same_unit_conversion_returns_same_value():
    result = convert_unit("2.50", "m", "m", "length")

    assert result["input_value"] == "2.5"
    assert result["converted_value"] == "2.5"


def test_unsupported_dimension_is_controlled():
    with pytest.raises(UnitConversionToolError, match="Unsupported dimension"):
        convert_unit(1, "m", "m", "speed")


def test_unsupported_source_unit_is_controlled():
    with pytest.raises(UnitConversionToolError, match="Unsupported unit"):
        convert_unit(1, "yard", "m", "length")


def test_unsupported_target_unit_is_controlled():
    with pytest.raises(UnitConversionToolError, match="Unsupported unit"):
        convert_unit(1, "m", "yard", "length")


def test_cross_dimension_conversion_is_rejected_by_dimension_unit_validation():
    with pytest.raises(UnitConversionToolError, match="Unsupported unit"):
        convert_unit(1, "m", "kg", "length")


@pytest.mark.parametrize("bad_input", ["abc", "", True, object()])
def test_non_numeric_values_are_rejected(bad_input):
    with pytest.raises(UnitConversionToolError):
        convert_unit(bad_input, "m", "cm", "length")


def test_invalid_dimension_type_is_rejected():
    with pytest.raises(UnitConversionToolError, match="dimension"):
        convert_unit(1, "m", "cm", None)


def test_invalid_unit_type_is_rejected():
    with pytest.raises(UnitConversionToolError, match="unit"):
        convert_unit(1, None, "cm", "length")


def test_unit_conversion_has_no_llm_provider_internet_file_db_or_runtime_dependency():
    definition = unit_conversion_tool_definition()

    assert definition.side_effects == (ToolSideEffect.NONE,)
    assert definition.requires_consent is False
    assert definition.can_govern_truth is False

    result = convert_unit(1, "m", "cm", "length")
    assert result["converted_value"] == "100"
    assert result["can_govern_truth"] is False
