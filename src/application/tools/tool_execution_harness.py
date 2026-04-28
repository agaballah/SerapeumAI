"""Bounded execution harness for deterministic local tools.

This module executes approved deterministic local tools only after request
validation, resolver lookup, and eligibility checks. It does not wire chat,
parse LLM tool calls, persist audits, touch storage, use internet, or interact
with UI/runtime providers.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Callable

from src.application.tools.calculator_tool import (
    TOOL_ID as CALCULATOR_TOOL_ID,
    calculate,
)
from src.application.tools.quantity_formula_tool import (
    TOOL_ID as QUANTITY_FORMULA_TOOL_ID,
    evaluate_formula,
)
from src.application.tools.tool_eligibility_gate import check_tool_eligibility
from src.application.tools.tool_invocation_contract import (
    ToolInvocationContractError,
    ToolInvocationRequest,
    ToolInvocationResponse,
    ToolInvocationStatus,
)
from src.application.tools.tool_resolver import ToolResolverContractError
from src.application.tools.unit_conversion_tool import (
    TOOL_ID as UNIT_CONVERSION_TOOL_ID,
    convert_unit,
)


class ToolExecutionHarnessError(ValueError):
    """Raised for internal harness contract failures."""


ToolExecutor = Callable[[Mapping[str, Any]], Mapping[str, Any]]


def execute_tool_invocation(
    request: ToolInvocationRequest,
    *,
    executors: Mapping[str, ToolExecutor] | None = None,
    definition_factories: Mapping[str, Any] | None = None,
) -> ToolInvocationResponse:
    """Execute an approved deterministic local tool invocation."""

    if not isinstance(request, ToolInvocationRequest):
        raise ToolExecutionHarnessError(
            "request must be a ToolInvocationRequest instance."
        )

    try:
        request.validate()
    except ToolInvocationContractError as exc:
        return _error_response(
            request_id=_safe_attr(request, "request_id", ""),
            tool_id=_safe_attr(request, "tool_id", ""),
            correlation_id=_safe_attr(request, "correlation_id", None),
            error_type="invalid_request",
            message=str(exc),
        )

    try:
        eligibility = check_tool_eligibility(
            request.tool_id,
            consent_granted=request.consent_granted,
            definition_factories=definition_factories,
        )
    except ToolResolverContractError as exc:
        return _error_response(
            request_id=request.request_id,
            tool_id=request.tool_id,
            correlation_id=request.correlation_id,
            error_type="tool_resolution_error",
            message=str(exc),
        )

    if not eligibility.is_eligible:
        return _error_response(
            request_id=request.request_id,
            tool_id=request.tool_id,
            correlation_id=request.correlation_id,
            error_type="tool_not_eligible",
            message="Tool is not eligible for execution.",
            details=eligibility.to_dict(),
        )

    executor_catalog = dict(executors or _default_executors())
    executor = executor_catalog.get(request.tool_id)
    if executor is None:
        return _error_response(
            request_id=request.request_id,
            tool_id=request.tool_id,
            correlation_id=request.correlation_id,
            error_type="executor_not_registered",
            message=f"No executor is registered for tool: {request.tool_id}",
        )

    try:
        result = dict(executor(request.arguments))
    except Exception as exc:  # noqa: BLE001 - convert tool failures to response envelope
        return _error_response(
            request_id=request.request_id,
            tool_id=request.tool_id,
            correlation_id=request.correlation_id,
            error_type="tool_execution_error",
            message=str(exc),
        )

    return ToolInvocationResponse(
        request_id=request.request_id,
        tool_id=request.tool_id,
        status=ToolInvocationStatus.SUCCESS,
        result=result,
        error=None,
        correlation_id=request.correlation_id,
        can_govern_truth=False,
    )


def _default_executors() -> dict[str, ToolExecutor]:
    return {
        CALCULATOR_TOOL_ID: _execute_calculator,
        UNIT_CONVERSION_TOOL_ID: _execute_unit_conversion,
        QUANTITY_FORMULA_TOOL_ID: _execute_quantity_formula,
    }


def _execute_calculator(arguments: Mapping[str, Any]) -> Mapping[str, Any]:
    operation = _required(arguments, "operation")
    operands = arguments.get("operands", arguments.get("inputs"))
    if operands is None:
        raise ToolExecutionHarnessError(
            "calculator.local requires operands or inputs."
        )
    return calculate(operation, operands)


def _execute_unit_conversion(arguments: Mapping[str, Any]) -> Mapping[str, Any]:
    return convert_unit(
        _required(arguments, "value"),
        _required(arguments, "from_unit"),
        _required(arguments, "to_unit"),
        _required(arguments, "dimension"),
    )


def _execute_quantity_formula(arguments: Mapping[str, Any]) -> Mapping[str, Any]:
    return evaluate_formula(
        _required(arguments, "formula_id"),
        _required(arguments, "inputs"),
    )


def _required(arguments: Mapping[str, Any], key: str) -> Any:
    if key not in arguments:
        raise ToolExecutionHarnessError(f"Missing required argument: {key}")
    return arguments[key]


def _error_response(
    *,
    request_id: str,
    tool_id: str,
    correlation_id: str | None,
    error_type: str,
    message: str,
    details: Mapping[str, Any] | None = None,
) -> ToolInvocationResponse:
    error: dict[str, Any] = {
        "error_type": error_type,
        "message": message,
    }
    if details is not None:
        error["details"] = dict(details)

    return ToolInvocationResponse(
        request_id=request_id or "invalid-request",
        tool_id=tool_id or "invalid-tool",
        status=ToolInvocationStatus.ERROR,
        result=None,
        error=error,
        correlation_id=correlation_id,
        can_govern_truth=False,
    )


def _safe_attr(obj: object, attr: str, default: Any) -> Any:
    return getattr(obj, attr, default)
