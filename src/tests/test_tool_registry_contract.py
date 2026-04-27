from __future__ import annotations

import pytest

from src.application.tools.tool_registry import (
    FUTURE_SAFE_TOOL_CANDIDATES,
    MemoryCategory,
    ToolAuthorityLevel,
    ToolContractError,
    ToolDefinition,
    ToolScope,
    ToolSideEffect,
    calculation_doctrine,
    memory_separation_doctrine,
    normalize_side_effects,
    validate_tool_registry,
)


def valid_tool(**overrides):
    data = {
        "tool_id": "calculator.local",
        "display_name": "Local Calculator",
        "description": "Performs deterministic local arithmetic.",
        "input_schema": {"type": "object", "properties": {}},
        "output_schema": {"type": "object", "properties": {}},
        "authority_level": ToolAuthorityLevel.DETERMINISTIC,
        "scope": ToolScope.SESSION,
        "side_effects": (ToolSideEffect.NONE,),
        "requires_consent": False,
        "can_govern_truth": False,
        "audit_log_required": True,
        "enabled_by_default": False,
        "requires_project": False,
        "requires_snapshot": False,
        "result_provenance_required": False,
    }
    data.update(overrides)
    return ToolDefinition(**data)


def test_valid_deterministic_tool_definition_passes():
    tool = valid_tool()
    tool.validate()

    out = tool.to_dict()
    assert out["tool_id"] == "calculator.local"
    assert out["authority_level"] == "deterministic"
    assert out["side_effects"] == ["none"]


def test_registry_key_must_match_tool_id():
    with pytest.raises(ToolContractError):
        validate_tool_registry({"wrong.key": valid_tool()})


def test_string_authority_value_is_rejected_even_when_value_is_known():
    tool = valid_tool(authority_level="deterministic")
    with pytest.raises(ToolContractError):
        tool.validate()


def test_unknown_authority_value_is_rejected():
    tool = valid_tool(authority_level="bad-authority")
    with pytest.raises(ToolContractError):
        tool.validate()


def test_string_side_effect_value_is_rejected_even_when_value_is_known():
    with pytest.raises(ToolContractError):
        normalize_side_effects(("internet",))


def test_unknown_side_effect_value_is_rejected():
    with pytest.raises(ToolContractError):
        normalize_side_effects(("bad-effect",))


def test_none_side_effect_cannot_mix_with_other_effects():
    with pytest.raises(ToolContractError):
        normalize_side_effects((ToolSideEffect.NONE, ToolSideEffect.READ_PROJECT_DB))


def test_side_effectful_tool_requires_consent():
    tool = valid_tool(
        side_effects=(ToolSideEffect.WRITE_PROJECT_DB,),
        requires_consent=False,
    )

    with pytest.raises(ToolContractError):
        tool.validate()


def test_side_effectful_tool_cannot_be_enabled_by_default():
    tool = valid_tool(
        side_effects=(ToolSideEffect.INTERNET,),
        requires_consent=True,
        enabled_by_default=True,
    )

    with pytest.raises(ToolContractError):
        tool.validate()


def test_ai_support_and_external_tools_cannot_govern_truth():
    for authority in (ToolAuthorityLevel.AI_SUPPORT, ToolAuthorityLevel.EXTERNAL):
        tool = valid_tool(
            authority_level=authority,
            can_govern_truth=True,
            result_provenance_required=True,
        )
        with pytest.raises(ToolContractError):
            tool.validate()


def test_truth_governing_tool_requires_allowed_authority_and_provenance():
    without_provenance = valid_tool(
        authority_level=ToolAuthorityLevel.TRUST_QUERY,
        can_govern_truth=True,
        result_provenance_required=False,
    )
    with pytest.raises(ToolContractError):
        without_provenance.validate()

    with_provenance = valid_tool(
        authority_level=ToolAuthorityLevel.TRUST_QUERY,
        can_govern_truth=True,
        result_provenance_required=True,
        scope=ToolScope.PROJECT,
        requires_project=True,
        side_effects=(ToolSideEffect.READ_PROJECT_DB,),
    )
    with_provenance.validate()


def test_project_snapshot_and_file_scoped_tools_require_project():
    for scope in (ToolScope.PROJECT, ToolScope.SNAPSHOT, ToolScope.FILE):
        tool = valid_tool(scope=scope, requires_project=False)
        with pytest.raises(ToolContractError):
            tool.validate()


def test_snapshot_scoped_tools_require_snapshot():
    tool = valid_tool(
        scope=ToolScope.SNAPSHOT,
        requires_project=True,
        requires_snapshot=False,
    )

    with pytest.raises(ToolContractError):
        tool.validate()


def test_json_schema_like_contract_requires_type_field():
    tool = valid_tool(input_schema={"properties": {}})
    with pytest.raises(ToolContractError):
        tool.validate()


def test_calculation_doctrine_forbids_llm_arithmetic():
    doctrine = calculation_doctrine()

    assert doctrine["llm_may_calculate"] is False
    assert doctrine["application_must_calculate"] is True
    assert "formula_or_operation" in doctrine["required_result_fields"]
    assert "computed_result" in doctrine["required_result_fields"]
    assert "rounding_policy" in doctrine["required_result_fields"]


def test_memory_separation_doctrine_blocks_memory_as_truth():
    doctrine = memory_separation_doctrine()

    assert doctrine["memory_can_be_certified_fact_silently"] is False
    assert doctrine["project_memory_can_cross_projects"] is False
    assert doctrine["runtime_diagnostics_can_govern_engineering_truth"] is False
    assert MemoryCategory.CERTIFIED_FACT.value in doctrine["categories"]


def test_future_safe_tool_candidates_are_declared_without_execution():
    assert "calculator" in FUTURE_SAFE_TOOL_CANDIDATES
    assert "fact_query" in FUTURE_SAFE_TOOL_CANDIDATES
    assert "schedule_query" in FUTURE_SAFE_TOOL_CANDIDATES
