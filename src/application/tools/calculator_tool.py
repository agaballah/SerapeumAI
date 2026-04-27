"""Deterministic local calculator tool for SerapeumAI.

This module performs local arithmetic only. It does not call an LLM, provider,
database, filesystem, internet endpoint, runtime manager, or UI surface.
"""

from __future__ import annotations

from decimal import Decimal, DivisionByZero, InvalidOperation, getcontext
from typing import Any, Iterable

from src.application.tools.tool_registry import (
    ToolAuthorityLevel,
    ToolDefinition,
    ToolScope,
    ToolSideEffect,
)

TOOL_ID = "calculator.local"
TOOL_VERSION = "1.0"
ROUNDING_POLICY = "Decimal arithmetic; result serialized as plain decimal string; no display rounding applied."
SUPPORTED_OPERATIONS = {"add", "subtract", "multiply", "divide", "power", "sum", "average"}

# Enough precision for normal engineering-support arithmetic without introducing
# floating-point nondeterminism. This is not a units or quantity engine.
getcontext().prec = 28


class CalculatorToolError(ValueError):
    """Raised when calculator input is invalid or operation cannot be performed."""


def calculator_tool_definition() -> ToolDefinition:
    """Return the source-defined non-mutating calculator tool definition."""

    definition = ToolDefinition(
        tool_id=TOOL_ID,
        display_name="Local Calculator",
        description="Performs deterministic local arithmetic without LLM involvement.",
        input_schema={
            "type": "object",
            "properties": {
                "operation": {"type": "string"},
                "inputs": {"type": "array"},
            },
            "required": ["operation", "inputs"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "operation": {"type": "string"},
                "normalized_inputs": {"type": "array"},
                "computed_result": {"type": "string"},
                "rounding_policy": {"type": "string"},
                "warnings": {"type": "array"},
                "tool_id": {"type": "string"},
                "tool_version": {"type": "string"},
                "formula_or_operation": {"type": "string"},
                "units": {"type": "string"},
                "can_govern_truth": {"type": "boolean"},
            },
            "required": [
                "operation",
                "normalized_inputs",
                "computed_result",
                "rounding_policy",
                "warnings",
                "tool_id",
                "tool_version",
                "formula_or_operation",
                "units",
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
        raise CalculatorToolError("Boolean values are not valid calculator inputs.")
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise CalculatorToolError("NaN and infinity are not valid calculator inputs.")
        return Decimal(str(value))
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            raise CalculatorToolError("Empty strings are not valid calculator inputs.")
        try:
            return Decimal(stripped)
        except InvalidOperation as exc:
            raise CalculatorToolError(f"Non-numeric input: {value!r}") from exc

    raise CalculatorToolError(f"Unsupported input type: {type(value).__name__}")


def _normalize_inputs(inputs: Iterable[Any]) -> tuple[Decimal, ...]:
    try:
        normalized = tuple(_to_decimal(value) for value in inputs)
    except TypeError as exc:
        raise CalculatorToolError("inputs must be an iterable of numeric values.") from exc

    if not normalized:
        raise CalculatorToolError("At least one numeric input is required.")
    return normalized


def _require_count(operation: str, values: tuple[Decimal, ...], count: int) -> None:
    if len(values) != count:
        raise CalculatorToolError(f"{operation} requires exactly {count} inputs.")


def _decimal_to_string(value: Decimal) -> str:
    if value == value.to_integral_value():
        return str(value.quantize(Decimal(1)))
    return format(value.normalize(), "f")


def _formula(operation: str, values: tuple[Decimal, ...]) -> str:
    serialized = [_decimal_to_string(value) for value in values]
    if operation == "add":
        return " + ".join(serialized)
    if operation == "subtract":
        return f"{serialized[0]} - {serialized[1]}"
    if operation == "multiply":
        return " * ".join(serialized)
    if operation == "divide":
        return f"{serialized[0]} / {serialized[1]}"
    if operation == "power":
        return f"{serialized[0]} ^ {serialized[1]}"
    if operation == "sum":
        return "sum(" + ", ".join(serialized) + ")"
    if operation == "average":
        return "average(" + ", ".join(serialized) + ")"
    return operation


def calculate(operation: str, inputs: Iterable[Any]) -> dict[str, Any]:
    """Perform deterministic local arithmetic and return a governed envelope."""

    if not isinstance(operation, str) or not operation.strip():
        raise CalculatorToolError("operation must be a non-empty string.")

    normalized_operation = operation.strip().lower()
    if normalized_operation not in SUPPORTED_OPERATIONS:
        raise CalculatorToolError(f"Unsupported operation: {operation!r}")

    values = _normalize_inputs(inputs)

    try:
        if normalized_operation == "add":
            _require_count(normalized_operation, values, 2)
            result = values[0] + values[1]
        elif normalized_operation == "subtract":
            _require_count(normalized_operation, values, 2)
            result = values[0] - values[1]
        elif normalized_operation == "multiply":
            _require_count(normalized_operation, values, 2)
            result = values[0] * values[1]
        elif normalized_operation == "divide":
            _require_count(normalized_operation, values, 2)
            if values[1] == 0:
                raise CalculatorToolError("Division by zero is not allowed.")
            result = values[0] / values[1]
        elif normalized_operation == "power":
            _require_count(normalized_operation, values, 2)
            result = values[0] ** values[1]
        elif normalized_operation == "sum":
            result = sum(values, Decimal(0))
        elif normalized_operation == "average":
            result = sum(values, Decimal(0)) / Decimal(len(values))
        else:
            raise CalculatorToolError(f"Unsupported operation: {operation!r}")
    except DivisionByZero as exc:
        raise CalculatorToolError("Division by zero is not allowed.") from exc
    except InvalidOperation as exc:
        raise CalculatorToolError(f"Invalid calculation for operation: {operation!r}") from exc

    return {
        "operation": normalized_operation,
        "normalized_inputs": [_decimal_to_string(value) for value in values],
        "computed_result": _decimal_to_string(result),
        "rounding_policy": ROUNDING_POLICY,
        "warnings": [],
        "tool_id": TOOL_ID,
        "tool_version": TOOL_VERSION,
        "formula_or_operation": _formula(normalized_operation, values),
        "units": "dimensionless",
        "can_govern_truth": False,
    }
