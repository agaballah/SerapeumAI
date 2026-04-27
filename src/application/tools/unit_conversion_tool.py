"""Deterministic local unit conversion tool for SerapeumAI.

This module performs local unit conversion only. It does not call an LLM,
provider, database, filesystem, internet endpoint, runtime manager, or UI surface.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation, getcontext
from typing import Any

from src.application.tools.tool_registry import (
    ToolAuthorityLevel,
    ToolDefinition,
    ToolScope,
    ToolSideEffect,
)

TOOL_ID = "unit_conversion.local"
TOOL_VERSION = "1.0"
ROUNDING_POLICY = "Decimal arithmetic; result serialized as plain decimal string; no display rounding applied."

getcontext().prec = 28


class UnitConversionToolError(ValueError):
    """Raised when unit conversion input is invalid or unsupported."""


# For linear dimensions, factors convert from unit to the dimension base unit.
# Base units:
# length=m, area=m2, volume=m3, mass=kg, force=N, pressure=Pa.
LINEAR_CONVERSIONS: dict[str, dict[str, Decimal]] = {
    "length": {
        "mm": Decimal("0.001"),
        "cm": Decimal("0.01"),
        "m": Decimal("1"),
        "km": Decimal("1000"),
        "in": Decimal("0.0254"),
        "ft": Decimal("0.3048"),
    },
    "area": {
        "mm2": Decimal("0.000001"),
        "cm2": Decimal("0.0001"),
        "m2": Decimal("1"),
        "km2": Decimal("1000000"),
        "in2": Decimal("0.00064516"),
        "ft2": Decimal("0.09290304"),
    },
    "volume": {
        "ml": Decimal("0.000001"),
        "l": Decimal("0.001"),
        "m3": Decimal("1"),
        "in3": Decimal("0.000016387064"),
        "ft3": Decimal("0.028316846592"),
    },
    "mass": {
        "g": Decimal("0.001"),
        "kg": Decimal("1"),
        "tonne": Decimal("1000"),
        "lb": Decimal("0.45359237"),
    },
    "force": {
        "N": Decimal("1"),
        "kN": Decimal("1000"),
        "lbf": Decimal("4.4482216152605"),
    },
    "pressure": {
        "Pa": Decimal("1"),
        "kPa": Decimal("1000"),
        "MPa": Decimal("1000000"),
        "bar": Decimal("100000"),
        "psi": Decimal("6894.757293168"),
    },
}

SUPPORTED_DIMENSIONS = set(LINEAR_CONVERSIONS) | {"temperature"}
TEMPERATURE_UNITS = {"C", "F", "K"}


def unit_conversion_tool_definition() -> ToolDefinition:
    """Return the source-defined non-mutating unit conversion tool definition."""

    definition = ToolDefinition(
        tool_id=TOOL_ID,
        display_name="Local Unit Conversion",
        description="Converts supported engineering units deterministically without LLM involvement.",
        input_schema={
            "type": "object",
            "properties": {
                "value": {"type": "number"},
                "from_unit": {"type": "string"},
                "to_unit": {"type": "string"},
                "dimension": {"type": "string"},
            },
            "required": ["value", "from_unit", "to_unit", "dimension"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "operation": {"type": "string"},
                "dimension": {"type": "string"},
                "input_value": {"type": "string"},
                "from_unit": {"type": "string"},
                "to_unit": {"type": "string"},
                "converted_value": {"type": "string"},
                "rounding_policy": {"type": "string"},
                "warnings": {"type": "array"},
                "tool_id": {"type": "string"},
                "tool_version": {"type": "string"},
                "formula_or_operation": {"type": "string"},
                "can_govern_truth": {"type": "boolean"},
            },
            "required": [
                "operation",
                "dimension",
                "input_value",
                "from_unit",
                "to_unit",
                "converted_value",
                "rounding_policy",
                "warnings",
                "tool_id",
                "tool_version",
                "formula_or_operation",
                "can_govern_truth",
            ],
        },
        authority_level=ToolAuthorityLevel.DETERMINISTIC,
        scope=ToolScope.SESSION,
        side_effects=(ToolSideEffect.NONE,),
        requires_consent=False,
        can_govern_truth=False,
        audit_log_required=True,
        enabled_by_default=True,
        requires_project=False,
        requires_snapshot=False,
        result_provenance_required=False,
    )
    definition.validate()
    return definition


def _to_decimal(value: Any) -> Decimal:
    if isinstance(value, bool):
        raise UnitConversionToolError("Boolean values are not valid conversion inputs.")
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise UnitConversionToolError("NaN and infinity are not valid conversion inputs.")
        return Decimal(str(value))
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            raise UnitConversionToolError("Empty strings are not valid conversion inputs.")
        try:
            return Decimal(stripped)
        except InvalidOperation as exc:
            raise UnitConversionToolError(f"Non-numeric input: {value!r}") from exc
    raise UnitConversionToolError(f"Unsupported input type: {type(value).__name__}")


def _normalize_dimension(dimension: str) -> str:
    if not isinstance(dimension, str) or not dimension.strip():
        raise UnitConversionToolError("dimension must be a non-empty string.")
    normalized = dimension.strip().lower()
    if normalized not in SUPPORTED_DIMENSIONS:
        raise UnitConversionToolError(f"Unsupported dimension: {dimension!r}")
    return normalized


def _normalize_unit(unit: str, dimension: str) -> str:
    if not isinstance(unit, str) or not unit.strip():
        raise UnitConversionToolError("unit must be a non-empty string.")

    stripped = unit.strip()
    if dimension == "temperature":
        normalized = stripped.upper()
        if normalized not in TEMPERATURE_UNITS:
            raise UnitConversionToolError(
                f"Unsupported unit {unit!r} for dimension {dimension!r}."
            )
        return normalized

    normalized = stripped
    supported_units = LINEAR_CONVERSIONS[dimension]
    if normalized not in supported_units:
        raise UnitConversionToolError(
            f"Unsupported unit {unit!r} for dimension {dimension!r}."
        )
    return normalized


def _decimal_to_string(value: Decimal) -> str:
    if value == value.to_integral_value():
        return str(value.quantize(Decimal(1)))
    return format(value.normalize(), "f")


def _convert_temperature(value: Decimal, from_unit: str, to_unit: str) -> Decimal:
    if from_unit == to_unit:
        return value

    if from_unit == "C":
        celsius = value
    elif from_unit == "F":
        celsius = (value - Decimal("32")) * Decimal("5") / Decimal("9")
    elif from_unit == "K":
        celsius = value - Decimal("273.15")
    else:
        raise UnitConversionToolError(f"Unsupported temperature unit: {from_unit!r}")

    if to_unit == "C":
        return celsius
    if to_unit == "F":
        return (celsius * Decimal("9") / Decimal("5")) + Decimal("32")
    if to_unit == "K":
        return celsius + Decimal("273.15")

    raise UnitConversionToolError(f"Unsupported temperature unit: {to_unit!r}")


def convert_unit(value: Any, from_unit: str, to_unit: str, dimension: str) -> dict[str, Any]:
    """Convert a value between supported units and return a governed envelope."""

    normalized_dimension = _normalize_dimension(dimension)
    normalized_value = _to_decimal(value)
    normalized_from = _normalize_unit(from_unit, normalized_dimension)
    normalized_to = _normalize_unit(to_unit, normalized_dimension)

    if normalized_dimension == "temperature":
        converted = _convert_temperature(normalized_value, normalized_from, normalized_to)
        formula = f"{_decimal_to_string(normalized_value)} {normalized_from} -> {normalized_to}"
    else:
        factors = LINEAR_CONVERSIONS[normalized_dimension]
        base_value = normalized_value * factors[normalized_from]
        converted = base_value / factors[normalized_to]
        formula = (
            f"{_decimal_to_string(normalized_value)} {normalized_from} "
            f"* {factors[normalized_from]} / {factors[normalized_to]} -> {normalized_to}"
        )

    return {
        "operation": "unit_conversion",
        "dimension": normalized_dimension,
        "input_value": _decimal_to_string(normalized_value),
        "from_unit": normalized_from,
        "to_unit": normalized_to,
        "converted_value": _decimal_to_string(converted),
        "rounding_policy": ROUNDING_POLICY,
        "warnings": [],
        "tool_id": TOOL_ID,
        "tool_version": TOOL_VERSION,
        "formula_or_operation": formula,
        "can_govern_truth": False,
    }
