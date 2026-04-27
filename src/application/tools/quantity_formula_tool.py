"""Deterministic local quantity/formula tool for SerapeumAI.

This module evaluates a narrow set of explicit AECO-safe formulas only.
It does not parse arbitrary formulas, call an LLM, provider, database,
filesystem, internet endpoint, runtime manager, or UI surface.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation, getcontext
from typing import Any, Mapping

from src.application.tools.tool_registry import (
    ToolAuthorityLevel,
    ToolDefinition,
    ToolScope,
    ToolSideEffect,
)

TOOL_ID = "quantity_formula.local"
TOOL_VERSION = "1.0"
ROUNDING_POLICY = "Decimal arithmetic; result serialized as plain decimal string; no display rounding applied."

getcontext().prec = 28


class QuantityFormulaToolError(ValueError):
    """Raised when formula input is invalid or unsupported."""


FORMULA_CONTRACTS: dict[str, dict[str, Any]] = {
    "rectangle_area": {
        "required": ("length", "width"),
        "formula": "area = length * width",
        "result_unit": "derived_area",
        "physical_dimensions": True,
    },
    "room_volume": {
        "required": ("length", "width", "height"),
        "formula": "volume = length * width * height",
        "result_unit": "derived_volume",
        "physical_dimensions": True,
    },
    "concrete_volume": {
        "required": ("length", "width", "thickness"),
        "formula": "volume = length * width * thickness",
        "result_unit": "derived_volume",
        "physical_dimensions": True,
    },
    "percentage_ratio": {
        "required": ("part", "whole"),
        "formula": "percentage = part / whole * 100",
        "result_unit": "percent",
        "physical_dimensions": False,
    },
    "progress_ratio": {
        "required": ("completed", "total"),
        "formula": "progress = completed / total * 100",
        "result_unit": "percent",
        "physical_dimensions": False,
    },
    "density_mass": {
        "required": ("density", "volume"),
        "formula": "mass = density * volume",
        "result_unit": "derived_mass",
        "physical_dimensions": True,
    },
    "linear_weight": {
        "required": ("unit_weight", "length"),
        "formula": "weight = unit_weight * length",
        "result_unit": "derived_weight",
        "physical_dimensions": True,
    },
    "circle_area": {
        "required": ("radius",),
        "formula": "area = pi * radius ^ 2",
        "result_unit": "derived_area",
        "physical_dimensions": True,
    },
}

PI = Decimal("3.141592653589793238462643383")


def quantity_formula_tool_definition() -> ToolDefinition:
    """Return the source-defined non-mutating quantity/formula tool definition."""

    definition = ToolDefinition(
        tool_id=TOOL_ID,
        display_name="Local Quantity Formula",
        description="Evaluates supported AECO-safe quantity formulas deterministically without LLM involvement.",
        input_schema={
            "type": "object",
            "properties": {
                "formula_id": {"type": "string"},
                "inputs": {"type": "object"},
            },
            "required": ["formula_id", "inputs"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "operation": {"type": "string"},
                "formula_id": {"type": "string"},
                "formula_or_operation": {"type": "string"},
                "normalized_inputs": {"type": "object"},
                "computed_result": {"type": "string"},
                "result_unit": {"type": "string"},
                "rounding_policy": {"type": "string"},
                "warnings": {"type": "array"},
                "tool_id": {"type": "string"},
                "tool_version": {"type": "string"},
                "can_govern_truth": {"type": "boolean"},
            },
            "required": [
                "operation",
                "formula_id",
                "formula_or_operation",
                "normalized_inputs",
                "computed_result",
                "result_unit",
                "rounding_policy",
                "warnings",
                "tool_id",
                "tool_version",
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


def _to_decimal(value: Any, field_name: str) -> Decimal:
    if isinstance(value, bool):
        raise QuantityFormulaToolError(f"Boolean value is not valid for {field_name}.")
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise QuantityFormulaToolError(f"NaN and infinity are not valid for {field_name}.")
        return Decimal(str(value))
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            raise QuantityFormulaToolError(f"Empty string is not valid for {field_name}.")
        try:
            return Decimal(stripped)
        except InvalidOperation as exc:
            raise QuantityFormulaToolError(f"Non-numeric input for {field_name}: {value!r}") from exc
    raise QuantityFormulaToolError(f"Unsupported input type for {field_name}: {type(value).__name__}")


def _decimal_to_string(value: Decimal) -> str:
    if value == value.to_integral_value():
        return str(value.quantize(Decimal(1)))
    return format(value.normalize(), "f")


def _normalize_formula_id(formula_id: str) -> str:
    if not isinstance(formula_id, str) or not formula_id.strip():
        raise QuantityFormulaToolError("formula_id must be a non-empty string.")
    normalized = formula_id.strip().lower()
    if normalized not in FORMULA_CONTRACTS:
        raise QuantityFormulaToolError(f"Unsupported formula: {formula_id!r}")
    return normalized


def _normalize_inputs(formula_id: str, inputs: Mapping[str, Any]) -> tuple[dict[str, Decimal], list[str]]:
    if not isinstance(inputs, Mapping):
        raise QuantityFormulaToolError("inputs must be a mapping.")

    contract = FORMULA_CONTRACTS[formula_id]
    required = contract["required"]
    missing = [name for name in required if name not in inputs]
    if missing:
        raise QuantityFormulaToolError(f"Missing required input(s): {', '.join(missing)}")

    extra = sorted(name for name in inputs if name not in required)
    if extra:
        raise QuantityFormulaToolError(f"Unsupported extra input(s): {', '.join(extra)}")

    normalized = {name: _to_decimal(inputs[name], name) for name in required}

    if contract["physical_dimensions"]:
        for name, value in normalized.items():
            if value < 0:
                raise QuantityFormulaToolError(f"Negative physical dimension/value is not allowed for {name}.")

    if formula_id in {"percentage_ratio", "progress_ratio"}:
        for name, value in normalized.items():
            if value < 0:
                raise QuantityFormulaToolError(f"Negative ratio input is not allowed for {name}.")

    return normalized, []


def _compute(formula_id: str, values: Mapping[str, Decimal]) -> Decimal:
    if formula_id == "rectangle_area":
        return values["length"] * values["width"]
    if formula_id == "room_volume":
        return values["length"] * values["width"] * values["height"]
    if formula_id == "concrete_volume":
        return values["length"] * values["width"] * values["thickness"]
    if formula_id == "percentage_ratio":
        if values["whole"] == 0:
            raise QuantityFormulaToolError("Division by zero is not allowed for percentage_ratio.")
        return values["part"] / values["whole"] * Decimal("100")
    if formula_id == "progress_ratio":
        if values["total"] == 0:
            raise QuantityFormulaToolError("Division by zero is not allowed for progress_ratio.")
        return values["completed"] / values["total"] * Decimal("100")
    if formula_id == "density_mass":
        return values["density"] * values["volume"]
    if formula_id == "linear_weight":
        return values["unit_weight"] * values["length"]
    if formula_id == "circle_area":
        return PI * values["radius"] * values["radius"]

    raise QuantityFormulaToolError(f"Unsupported formula: {formula_id!r}")


def evaluate_formula(formula_id: str, inputs: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate a supported quantity formula and return a governed envelope."""

    normalized_formula_id = _normalize_formula_id(formula_id)
    normalized_inputs, warnings = _normalize_inputs(normalized_formula_id, inputs)
    result = _compute(normalized_formula_id, normalized_inputs)
    contract = FORMULA_CONTRACTS[normalized_formula_id]

    return {
        "operation": "quantity_formula",
        "formula_id": normalized_formula_id,
        "formula_or_operation": contract["formula"],
        "normalized_inputs": {
            name: _decimal_to_string(value)
            for name, value in normalized_inputs.items()
        },
        "computed_result": _decimal_to_string(result),
        "result_unit": contract["result_unit"],
        "rounding_policy": ROUNDING_POLICY,
        "warnings": warnings,
        "tool_id": TOOL_ID,
        "tool_version": TOOL_VERSION,
        "can_govern_truth": False,
    }
