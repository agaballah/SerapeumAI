"""Bounded tool registry contract for SerapeumAI.

This module defines source-level contracts for future application-owned tools.
It does not execute tools, route chat, call external services, mutate databases,
write files, provision runtimes, or perform internet access.

Core doctrine:
- The LLM may select a tool and propose arguments.
- The application validates scope, schema, authority, side effects, and consent.
- The application executes only approved deterministic tools in later packets.
- The LLM narrates verified tool results.
- The LLM does not calculate, certify, mutate truth, or silently create memory.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


class ToolAuthorityLevel(str, Enum):
    """Authority level for a registered tool."""

    DETERMINISTIC = "deterministic"
    TRUST_QUERY = "trust_query"
    SUPPORT_RETRIEVAL = "support_retrieval"
    AI_SUPPORT = "ai_support"
    EXTERNAL = "external"


class ToolScope(str, Enum):
    """Scope a tool is allowed to operate within."""

    SESSION = "session"
    PROJECT = "project"
    SNAPSHOT = "snapshot"
    FILE = "file"
    GLOBAL = "global"


class ToolSideEffect(str, Enum):
    """Declared side effects for a tool.

    Side effects are declarations for governance and validation. This module
    does not execute side effects.
    """

    NONE = "none"
    READ_PROJECT_DB = "read_project_db"
    READ_GLOBAL_DB = "read_global_db"
    READ_LOCAL_FILE = "read_local_file"
    WRITE_PROJECT_DB = "write_project_db"
    WRITE_LOCAL_FILE = "write_local_file"
    INTERNET = "internet"
    MACHINE_STATE = "machine_state"
    RUNTIME_STATE = "runtime_state"


class MemoryCategory(str, Enum):
    """Separated memory categories.

    Memory is not certified fact and must never silently become governing truth.
    """

    SESSION = "session"
    PROJECT = "project"
    USER_PREFERENCE = "user_preference"
    RUNTIME_DIAGNOSTIC = "runtime_diagnostic"
    CERTIFIED_FACT = "certified_fact"


class ToolContractError(ValueError):
    """Raised when a tool definition violates the registry contract."""


MUTATING_SIDE_EFFECTS = {
    ToolSideEffect.WRITE_PROJECT_DB,
    ToolSideEffect.WRITE_LOCAL_FILE,
    ToolSideEffect.INTERNET,
    ToolSideEffect.MACHINE_STATE,
    ToolSideEffect.RUNTIME_STATE,
}

READ_SIDE_EFFECTS = {
    ToolSideEffect.READ_PROJECT_DB,
    ToolSideEffect.READ_GLOBAL_DB,
    ToolSideEffect.READ_LOCAL_FILE,
}


@dataclass(frozen=True)
class ToolDefinition:
    """Source-defined metadata for one future application tool."""

    tool_id: str
    display_name: str
    description: str
    input_schema: Mapping[str, Any]
    output_schema: Mapping[str, Any]
    authority_level: ToolAuthorityLevel
    scope: ToolScope
    side_effects: tuple[ToolSideEffect, ...] = (ToolSideEffect.NONE,)
    requires_consent: bool = False
    can_govern_truth: bool = False
    audit_log_required: bool = True
    enabled_by_default: bool = False
    requires_project: bool = False
    requires_snapshot: bool = False
    result_provenance_required: bool = False
    version: str = "1.0"

    def validate(self) -> None:
        validate_tool_definition(self)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_id": self.tool_id,
            "display_name": self.display_name,
            "description": self.description,
            "input_schema": dict(self.input_schema),
            "output_schema": dict(self.output_schema),
            "authority_level": self.authority_level.value,
            "scope": self.scope.value,
            "side_effects": [item.value for item in self.side_effects],
            "requires_consent": self.requires_consent,
            "can_govern_truth": self.can_govern_truth,
            "audit_log_required": self.audit_log_required,
            "enabled_by_default": self.enabled_by_default,
            "requires_project": self.requires_project,
            "requires_snapshot": self.requires_snapshot,
            "result_provenance_required": self.result_provenance_required,
            "version": self.version,
        }


@dataclass(frozen=True)
class ToolResultEnvelope:
    """Standard future result envelope for verified tool results."""

    tool_id: str
    ok: bool
    result: Mapping[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()
    provenance: tuple[Mapping[str, Any], ...] = ()
    can_govern_truth: bool = False
    authority_level: ToolAuthorityLevel = ToolAuthorityLevel.SUPPORT_RETRIEVAL

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_id": self.tool_id,
            "ok": self.ok,
            "result": dict(self.result),
            "warnings": list(self.warnings),
            "provenance": [dict(item) for item in self.provenance],
            "can_govern_truth": self.can_govern_truth,
            "authority_level": self.authority_level.value,
        }


def normalize_enum(value: Any, enum_type: type[Enum], field_name: str) -> Enum:
    if isinstance(value, enum_type):
        return value
    try:
        return enum_type(value)
    except Exception as exc:
        allowed = ", ".join(item.value for item in enum_type)
        raise ToolContractError(
            f"Invalid {field_name}: {value!r}. Allowed values: {allowed}"
        ) from exc


def normalize_side_effects(values: Any) -> tuple[ToolSideEffect, ...]:
    if values is None:
        return (ToolSideEffect.NONE,)
    if isinstance(values, ToolSideEffect):
        raw_values = (values,)
    elif isinstance(values, str):
        raise ToolContractError(
            "side_effects must use ToolSideEffect instances, not strings."
        )
    else:
        raw_values = tuple(values)

    effects = []
    for value in raw_values:
        require_enum_instance(value, ToolSideEffect, "side_effects")
        effects.append(value)

    if not effects:
        return (ToolSideEffect.NONE,)

    normalized = tuple(effects)

    if ToolSideEffect.NONE in normalized and len(normalized) > 1:
        raise ToolContractError("side_effects cannot mix NONE with other effects.")

    return normalized


def validate_json_schema_like(schema: Mapping[str, Any], field_name: str) -> None:
    if not isinstance(schema, Mapping):
        raise ToolContractError(f"{field_name} must be a mapping.")
    schema_type = schema.get("type")
    if schema_type is None:
        raise ToolContractError(f"{field_name} must include a 'type' field.")
    if not isinstance(schema_type, str):
        raise ToolContractError(f"{field_name}.type must be a string.")


def require_enum_instance(value: Any, enum_type: type[Enum], field_name: str) -> None:
    """Require source-defined contracts to use enum instances, not strings.

    String/JSON loading can be added later in a dedicated loader. The registry
    contract itself must not accept values that later fail serialization.
    """

    if not isinstance(value, enum_type):
        allowed = ", ".join(item.value for item in enum_type)
        raise ToolContractError(
            f"{field_name} must be a {enum_type.__name__} instance. "
            f"Allowed values: {allowed}"
        )


def validate_tool_definition(tool: ToolDefinition) -> None:
    if not tool.tool_id or not tool.tool_id.strip():
        raise ToolContractError("tool_id is required.")
    if " " in tool.tool_id:
        raise ToolContractError("tool_id must be stable and must not contain spaces.")
    if not tool.display_name.strip():
        raise ToolContractError("display_name is required.")
    if not tool.description.strip():
        raise ToolContractError("description is required.")

    validate_json_schema_like(tool.input_schema, "input_schema")
    validate_json_schema_like(tool.output_schema, "output_schema")

    require_enum_instance(tool.authority_level, ToolAuthorityLevel, "authority_level")
    require_enum_instance(tool.scope, ToolScope, "scope")
    side_effects = normalize_side_effects(tool.side_effects)

    if tool.enabled_by_default and any(effect in MUTATING_SIDE_EFFECTS for effect in side_effects):
        raise ToolContractError(
            "Tools with mutating, internet, machine, or runtime side effects "
            "must not be enabled by default."
        )

    if any(effect in MUTATING_SIDE_EFFECTS for effect in side_effects) and not tool.requires_consent:
        raise ToolContractError("Side-effectful tools must require consent.")

    if tool.authority_level in {ToolAuthorityLevel.AI_SUPPORT, ToolAuthorityLevel.EXTERNAL}:
        if tool.can_govern_truth:
            raise ToolContractError("AI_SUPPORT and EXTERNAL tools cannot govern truth.")

    if tool.can_govern_truth and tool.authority_level not in {
        ToolAuthorityLevel.DETERMINISTIC,
        ToolAuthorityLevel.TRUST_QUERY,
    }:
        raise ToolContractError(
            "Only deterministic or trust-query tools may govern truth."
        )

    if tool.can_govern_truth and not tool.result_provenance_required:
        raise ToolContractError("Truth-governing tools require result provenance.")

    if tool.scope in {ToolScope.PROJECT, ToolScope.SNAPSHOT, ToolScope.FILE}:
        if not tool.requires_project:
            raise ToolContractError(
                "Project, snapshot, and file scoped tools must require a project."
            )

    if tool.scope == ToolScope.SNAPSHOT and not tool.requires_snapshot:
        raise ToolContractError("Snapshot-scoped tools must require a snapshot.")


def validate_tool_registry(tools: Mapping[str, ToolDefinition]) -> None:
    if not isinstance(tools, Mapping):
        raise ToolContractError("tool registry must be a mapping.")

    for key, tool in tools.items():
        if key != tool.tool_id:
            raise ToolContractError(
                f"Registry key {key!r} must match tool_id {tool.tool_id!r}."
            )
        tool.validate()


def calculation_doctrine() -> dict[str, Any]:
    """Return deterministic calculation doctrine for future tool packets."""

    return {
        "llm_may_calculate": False,
        "application_must_calculate": True,
        "required_result_fields": [
            "formula_or_operation",
            "normalized_inputs",
            "units",
            "source_references",
            "computed_result",
            "rounding_policy",
            "warnings",
            "tool_id",
            "tool_version",
        ],
    }


def memory_separation_doctrine() -> dict[str, Any]:
    """Return memory separation doctrine for future tool/memory packets."""

    return {
        "memory_can_be_certified_fact_silently": False,
        "project_memory_can_cross_projects": False,
        "user_preferences_can_answer_project_facts": False,
        "runtime_diagnostics_can_govern_engineering_truth": False,
        "persistent_memory_requires_explicit_audit_design": True,
        "categories": [item.value for item in MemoryCategory],
    }


FUTURE_SAFE_TOOL_CANDIDATES: tuple[str, ...] = (
    "calculator",
    "unit_conversion",
    "quantity_formula",
    "fact_query",
    "evidence_retrieval",
    "schedule_query",
    "metadata_inspection",
    "register_table_comparison",
)
