from __future__ import annotations

import json

import pytest

from src.application.tools.calculator_tool import (
    TOOL_ID as CALCULATOR_TOOL_ID,
    calculate,
)
from src.application.tools.quantity_formula_tool import (
    TOOL_ID as QUANTITY_FORMULA_TOOL_ID,
    evaluate_formula,
)
from src.application.tools.tool_registry import (
    ToolAuthorityLevel,
    ToolScope,
    ToolSideEffect,
)
from src.application.tools.tool_resolver import (
    ToolResolutionStatus,
    ToolResolverContractError,
    default_resolvable_tool_ids,
    resolve_tool,
)
from src.application.tools.unit_conversion_tool import (
    TOOL_ID as UNIT_CONVERSION_TOOL_ID,
    convert_unit,
)


EXPECTED_TOOL_IDS = (
    CALCULATOR_TOOL_ID,
    UNIT_CONVERSION_TOOL_ID,
    QUANTITY_FORMULA_TOOL_ID,
)


@pytest.mark.parametrize("tool_id", EXPECTED_TOOL_IDS)
def test_known_deterministic_tool_ids_resolve_successfully(tool_id):
    resolution = resolve_tool(tool_id)
    out = resolution.to_dict()

    assert out["tool_id"] == tool_id
    assert out["status"] == ToolResolutionStatus.RESOLVED.value
    assert out["is_resolvable"] is True
    assert out["display_name"]
    assert out["authority_level"] == ToolAuthorityLevel.DETERMINISTIC.value
    assert out["scope"] == ToolScope.SESSION.value
    assert out["side_effects"] == [ToolSideEffect.NONE.value]
    assert out["requires_consent"] is False
    assert out["can_govern_truth"] is False
    assert out["enabled_by_default"] is True
    assert out["requires_project"] is False
    assert out["requires_snapshot"] is False
    assert out["warnings"] == []
    assert out["error"] is None


def test_tool_id_whitespace_is_normalized_only():
    resolution = resolve_tool("  calculator.local  ")

    assert resolution.to_dict()["tool_id"] == "calculator.local"
    assert resolution.to_dict()["status"] == "resolved"


def test_unknown_tool_id_returns_controlled_not_found():
    resolution = resolve_tool("unknown.local")
    out = resolution.to_dict()

    assert out["tool_id"] == "unknown.local"
    assert out["status"] == ToolResolutionStatus.NOT_FOUND.value
    assert out["is_resolvable"] is False
    assert out["display_name"] is None
    assert out["authority_level"] is None
    assert out["scope"] is None
    assert out["side_effects"] == []
    assert out["can_govern_truth"] is None
    assert out["error"]["error_type"] == "tool_not_found"


@pytest.mark.parametrize("bad_tool_id", ["", "   ", None, 123])
def test_empty_or_non_string_tool_id_is_rejected(bad_tool_id):
    with pytest.raises(ToolResolverContractError, match="tool_id"):
        resolve_tool(bad_tool_id)


def test_default_resolvable_tool_ids_are_stable_sorted_tuple():
    assert default_resolvable_tool_ids() == tuple(sorted(EXPECTED_TOOL_IDS))


def test_resolution_envelope_is_json_serializable():
    resolution = resolve_tool("calculator.local").to_dict()

    assert json.loads(json.dumps(resolution, sort_keys=True)) == resolution


def test_unknown_resolution_envelope_is_json_serializable():
    resolution = resolve_tool("missing.local").to_dict()

    assert json.loads(json.dumps(resolution, sort_keys=True)) == resolution


def test_resolver_does_not_execute_tool_implementations(monkeypatch):
    called = {
        "calculate": False,
        "convert_unit": False,
        "evaluate_formula": False,
    }

    def blocked_calculate(*args, **kwargs):
        called["calculate"] = True
        raise AssertionError("calculate must not be called by resolver")

    def blocked_convert_unit(*args, **kwargs):
        called["convert_unit"] = True
        raise AssertionError("convert_unit must not be called by resolver")

    def blocked_evaluate_formula(*args, **kwargs):
        called["evaluate_formula"] = True
        raise AssertionError("evaluate_formula must not be called by resolver")

    monkeypatch.setattr(
        "src.application.tools.calculator_tool.calculate",
        blocked_calculate,
    )
    monkeypatch.setattr(
        "src.application.tools.unit_conversion_tool.convert_unit",
        blocked_convert_unit,
    )
    monkeypatch.setattr(
        "src.application.tools.quantity_formula_tool.evaluate_formula",
        blocked_evaluate_formula,
    )

    for tool_id in EXPECTED_TOOL_IDS:
        assert resolve_tool(tool_id).is_resolvable is True

    assert called == {
        "calculate": False,
        "convert_unit": False,
        "evaluate_formula": False,
    }


def test_imported_tool_functions_remain_callable_outside_resolver():
    # Guard against a false-positive monkeypatch assumption in the non-execution test.
    assert calculate("add", [1, 2])["computed_result"] == "3"
    assert convert_unit(1, "m", "cm", "length")["converted_value"] == "100"
    assert evaluate_formula("rectangle_area", {"length": 2, "width": 3})[
        "computed_result"
    ] == "6"
