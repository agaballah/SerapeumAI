"""Non-executing resolver for application-owned tool definitions.

This module resolves tool IDs to ToolDefinition metadata only.
It does not execute tools, route requests, call an LLM, persist audits,
touch storage, use internet, or interact with UI/runtime providers.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Mapping

from src.application.tools.calculator_tool import calculator_tool_definition
from src.application.tools.quantity_formula_tool import quantity_formula_tool_definition
from src.application.tools.tool_registry import ToolDefinition
from src.application.tools.unit_conversion_tool import unit_conversion_tool_definition


class ToolResolverContractError(ValueError):
    """Raised when resolver input is invalid."""


class ToolResolutionStatus(str, Enum):
    RESOLVED = "resolved"
    NOT_FOUND = "not_found"


DefinitionFactory = Callable[[], ToolDefinition]


DEFAULT_TOOL_DEFINITION_FACTORIES: Mapping[str, DefinitionFactory] = {
    "calculator.local": calculator_tool_definition,
    "unit_conversion.local": unit_conversion_tool_definition,
    "quantity_formula.local": quantity_formula_tool_definition,
}


@dataclass(frozen=True)
class ToolResolution:
    """Plain non-executing resolution envelope."""

    tool_id: str
    status: ToolResolutionStatus
    is_resolvable: bool
    display_name: str | None = None
    authority_level: str | None = None
    scope: str | None = None
    side_effects: tuple[str, ...] = ()
    requires_consent: bool | None = None
    can_govern_truth: bool | None = None
    enabled_by_default: bool | None = None
    requires_project: bool | None = None
    requires_snapshot: bool | None = None
    warnings: tuple[str, ...] = ()
    error: Mapping[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_id": self.tool_id,
            "status": self.status.value,
            "is_resolvable": self.is_resolvable,
            "display_name": self.display_name,
            "authority_level": self.authority_level,
            "scope": self.scope,
            "side_effects": list(self.side_effects),
            "requires_consent": self.requires_consent,
            "can_govern_truth": self.can_govern_truth,
            "enabled_by_default": self.enabled_by_default,
            "requires_project": self.requires_project,
            "requires_snapshot": self.requires_snapshot,
            "warnings": list(self.warnings),
            "error": dict(self.error) if self.error is not None else None,
        }


def _normalize_tool_id(tool_id: Any) -> str:
    if not isinstance(tool_id, str) or not tool_id.strip():
        raise ToolResolverContractError("tool_id must be a non-empty string.")
    return tool_id.strip()


def resolve_tool(
    tool_id: Any,
    definition_factories: Mapping[str, DefinitionFactory] | None = None,
) -> ToolResolution:
    """Resolve a tool ID to metadata without executing the tool."""

    normalized_tool_id = _normalize_tool_id(tool_id)
    catalog = dict(definition_factories or DEFAULT_TOOL_DEFINITION_FACTORIES)

    factory = catalog.get(normalized_tool_id)
    if factory is None:
        return ToolResolution(
            tool_id=normalized_tool_id,
            status=ToolResolutionStatus.NOT_FOUND,
            is_resolvable=False,
            warnings=(),
            error={
                "error_type": "tool_not_found",
                "message": f"Tool is not registered: {normalized_tool_id}",
            },
        )

    definition = factory()
    definition.validate()

    return ToolResolution(
        tool_id=definition.tool_id,
        status=ToolResolutionStatus.RESOLVED,
        is_resolvable=True,
        display_name=definition.display_name,
        authority_level=definition.authority_level.value,
        scope=definition.scope.value,
        side_effects=tuple(effect.value for effect in definition.side_effects),
        requires_consent=definition.requires_consent,
        can_govern_truth=definition.can_govern_truth,
        enabled_by_default=definition.enabled_by_default,
        requires_project=definition.requires_project,
        requires_snapshot=definition.requires_snapshot,
        warnings=(),
        error=None,
    )


def default_resolvable_tool_ids() -> tuple[str, ...]:
    """Return the default resolver catalog tool IDs without mutating catalog state."""

    return tuple(sorted(DEFAULT_TOOL_DEFINITION_FACTORIES))
