from __future__ import annotations

import json

import pytest

from src.application.tools.calculator_tool import (
    TOOL_ID as CALCULATOR_TOOL_ID,
    calculate,
    calculator_tool_definition,
)
from src.application.tools.quantity_formula_tool import (
    TOOL_ID as QUANTITY_FORMULA_TOOL_ID,
    evaluate_formula,
)
from src.application.tools.tool_eligibility_gate import (
    ToolEligibilityDecision,
    check_tool_eligibility,
)
from src.application.tools.tool_registry import (
    ToolAuthorityLevel,
    ToolDefinition,
    ToolScope,
    ToolSideEffect,
)
from src.application.tools.tool_resolver import ToolResolverContractError
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
def test_known_deterministic_tools_are_eligible_by_default(tool_id):
    eligibility = check_tool_eligibility(tool_id).to_dict()

    assert eligibility["tool_id"] == tool_id
    assert eligibility["is_eligible"] is True
    assert eligibility["decision"] == ToolEligibilityDecision.ALLOW.value
    assert eligibility["reasons"] == ["eligible"]
    assert eligibility["warnings"] == []
    assert eligibility["resolution_status"] == "resolved"
    assert eligibility["can_govern_truth"] is False
    assert eligibility["requires_consent"] is False
    assert eligibility["consent_granted"] is False
    assert eligibility["requires_project"] is False
    assert eligibility["project_available"] is False
    assert eligibility["requires_snapshot"] is False
    assert eligibility["snapshot_available"] is False


def test_unknown_tool_id_is_denied_cleanly():
    eligibility = check_tool_eligibility("unknown.local").to_dict()

    assert eligibility["tool_id"] == "unknown.local"
    assert eligibility["is_eligible"] is False
    assert eligibility["decision"] == "deny"
    assert "tool_not_resolved" in eligibility["reasons"]
    assert "unsupported_authority_level" in eligibility["reasons"]
    assert "unsupported_scope" in eligibility["reasons"]
    assert "side_effects_not_allowed" in eligibility["reasons"]
    assert "truth_governance_not_allowed" in eligibility["reasons"]
    assert eligibility["resolution_status"] == "not_found"


@pytest.mark.parametrize("bad_tool_id", ["", "   ", None, 123])
def test_empty_or_non_string_tool_id_is_controlled(bad_tool_id):
    with pytest.raises(ToolResolverContractError, match="tool_id"):
        check_tool_eligibility(bad_tool_id)


@pytest.mark.parametrize(
    ("flag_name", "kwargs"),
    [
        ("consent_granted", {"consent_granted": "yes"}),
        ("project_available", {"project_available": "yes"}),
        ("snapshot_available", {"snapshot_available": "yes"}),
    ],
)
def test_context_flags_must_be_boolean(flag_name, kwargs):
    with pytest.raises(ToolResolverContractError, match=flag_name):
        check_tool_eligibility("calculator.local", **kwargs)


def _definition_with(**overrides):
    base = calculator_tool_definition()
    values = {
        "tool_id": "custom.local",
        "display_name": base.display_name,
        "description": base.description,
        "input_schema": base.input_schema,
        "output_schema": base.output_schema,
        "authority_level": base.authority_level,
        "scope": base.scope,
        "side_effects": base.side_effects,
        "requires_consent": base.requires_consent,
        "can_govern_truth": base.can_govern_truth,
        "audit_log_required": base.audit_log_required,
        "enabled_by_default": base.enabled_by_default,
        "requires_project": base.requires_project,
        "requires_snapshot": base.requires_snapshot,
        "result_provenance_required": base.result_provenance_required,
    }
    values.update(overrides)
    definition = ToolDefinition(**values)
    definition.validate()
    return definition


def _catalog_for(definition):
    return {"custom.local": lambda: definition}


def test_disabled_tool_is_denied():
    eligibility = check_tool_eligibility(
        "custom.local",
        definition_factories=_catalog_for(_definition_with(enabled_by_default=False)),
    ).to_dict()

    assert eligibility["is_eligible"] is False
    assert "tool_disabled" in eligibility["reasons"]


def test_side_effecting_tool_is_denied_with_registry_valid_definition():
    side_effect = next(effect for effect in ToolSideEffect if effect != ToolSideEffect.NONE)

    eligibility = check_tool_eligibility(
        "custom.local",
        definition_factories=_catalog_for(
            _definition_with(
                side_effects=(side_effect,),
                enabled_by_default=False,
                requires_consent=True,
            )
        ),
    ).to_dict()

    assert eligibility["is_eligible"] is False
    assert "tool_disabled" in eligibility["reasons"]
    assert "side_effects_not_allowed" in eligibility["reasons"]
    assert "consent_required" in eligibility["reasons"]


def test_truth_governing_tool_is_denied_with_registry_valid_definition():
    eligibility = check_tool_eligibility(
        "custom.local",
        definition_factories=_catalog_for(
            _definition_with(
                can_govern_truth=True,
                result_provenance_required=True,
            )
        ),
    ).to_dict()

    assert eligibility["is_eligible"] is False
    assert "truth_governance_not_allowed" in eligibility["reasons"]


def test_consent_required_tool_is_denied_without_consent_and_allowed_with_consent():
    definition = _definition_with(requires_consent=True)
    denied = check_tool_eligibility(
        "custom.local",
        definition_factories=_catalog_for(definition),
    ).to_dict()
    allowed = check_tool_eligibility(
        "custom.local",
        consent_granted=True,
        definition_factories=_catalog_for(definition),
    ).to_dict()

    assert denied["is_eligible"] is False
    assert "consent_required" in denied["reasons"]
    assert allowed["is_eligible"] is True
    assert allowed["reasons"] == ["eligible"]


def test_project_required_tool_is_denied_without_project_context_and_allowed_with_project():
    definition = _definition_with(requires_project=True)
    denied = check_tool_eligibility(
        "custom.local",
        definition_factories=_catalog_for(definition),
    ).to_dict()
    allowed = check_tool_eligibility(
        "custom.local",
        project_available=True,
        definition_factories=_catalog_for(definition),
    ).to_dict()

    assert denied["is_eligible"] is False
    assert "project_required" in denied["reasons"]
    assert allowed["is_eligible"] is True
    assert allowed["reasons"] == ["eligible"]


def test_snapshot_required_tool_is_denied_without_snapshot_context_and_allowed_with_snapshot():
    definition = _definition_with(
        requires_project=True,
        requires_snapshot=True,
    )
    denied = check_tool_eligibility(
        "custom.local",
        project_available=True,
        definition_factories=_catalog_for(definition),
    ).to_dict()
    allowed = check_tool_eligibility(
        "custom.local",
        project_available=True,
        snapshot_available=True,
        definition_factories=_catalog_for(definition),
    ).to_dict()

    assert denied["is_eligible"] is False
    assert "snapshot_required" in denied["reasons"]
    assert allowed["is_eligible"] is True
    assert allowed["reasons"] == ["eligible"]


def test_non_deterministic_authority_is_denied_with_registry_valid_definition():
    eligibility = check_tool_eligibility(
        "custom.local",
        definition_factories=_catalog_for(
            _definition_with(authority_level=ToolAuthorityLevel.EXTERNAL)
        ),
    ).to_dict()

    assert eligibility["is_eligible"] is False
    assert "unsupported_authority_level" in eligibility["reasons"]


def test_non_session_scope_is_denied_with_registry_valid_definition():
    eligibility = check_tool_eligibility(
        "custom.local",
        project_available=True,
        definition_factories=_catalog_for(
            _definition_with(scope=ToolScope.PROJECT, requires_project=True)
        ),
    ).to_dict()

    assert eligibility["is_eligible"] is False
    assert "unsupported_scope" in eligibility["reasons"]


def test_eligibility_result_is_json_serializable():
    eligibility = check_tool_eligibility("calculator.local").to_dict()

    assert json.loads(json.dumps(eligibility, sort_keys=True)) == eligibility


def test_gate_does_not_execute_tool_implementations(monkeypatch):
    called = {
        "calculate": False,
        "convert_unit": False,
        "evaluate_formula": False,
    }

    def blocked_calculate(*args, **kwargs):
        called["calculate"] = True
        raise AssertionError("calculate must not be called by eligibility gate")

    def blocked_convert_unit(*args, **kwargs):
        called["convert_unit"] = True
        raise AssertionError("convert_unit must not be called by eligibility gate")

    def blocked_evaluate_formula(*args, **kwargs):
        called["evaluate_formula"] = True
        raise AssertionError("evaluate_formula must not be called by eligibility gate")

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
        assert check_tool_eligibility(tool_id).is_eligible is True

    assert called == {
        "calculate": False,
        "convert_unit": False,
        "evaluate_formula": False,
    }


def test_imported_tool_functions_remain_callable_outside_gate():
    assert calculate("add", [1, 2])["computed_result"] == "3"
    assert convert_unit(1, "m", "cm", "length")["converted_value"] == "100"
    assert evaluate_formula("rectangle_area", {"length": 2, "width": 3})[
        "computed_result"
    ] == "6"
