"""Non-executing eligibility gate for application-owned tools.

This module decides whether a resolved tool is eligible for future invocation.
It does not execute tools, route requests, call an LLM, persist audits,
touch storage, use internet, or interact with UI/runtime providers.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from src.application.tools.tool_registry import (
    ToolAuthorityLevel,
    ToolScope,
    ToolSideEffect,
)
from src.application.tools.tool_resolver import (
    ToolResolution,
    ToolResolverContractError,
    resolve_tool,
)


class ToolEligibilityDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"


@dataclass(frozen=True)
class ToolEligibility:
    """Plain non-executing eligibility envelope."""

    tool_id: str
    is_eligible: bool
    decision: ToolEligibilityDecision
    reasons: tuple[str, ...]
    warnings: tuple[str, ...]
    resolution_status: str
    can_govern_truth: bool | None
    requires_consent: bool | None
    consent_granted: bool
    requires_project: bool | None
    project_available: bool
    requires_snapshot: bool | None
    snapshot_available: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_id": self.tool_id,
            "is_eligible": self.is_eligible,
            "decision": self.decision.value,
            "reasons": list(self.reasons),
            "warnings": list(self.warnings),
            "resolution_status": self.resolution_status,
            "can_govern_truth": self.can_govern_truth,
            "requires_consent": self.requires_consent,
            "consent_granted": self.consent_granted,
            "requires_project": self.requires_project,
            "project_available": self.project_available,
            "requires_snapshot": self.requires_snapshot,
            "snapshot_available": self.snapshot_available,
        }


def check_tool_eligibility(
    tool_id: Any,
    *,
    consent_granted: bool = False,
    project_available: bool = False,
    snapshot_available: bool = False,
    definition_factories: Mapping[str, Any] | None = None,
) -> ToolEligibility:
    """Return a deterministic allow/deny envelope without executing the tool."""

    if not isinstance(consent_granted, bool):
        raise ToolResolverContractError("consent_granted must be a boolean.")
    if not isinstance(project_available, bool):
        raise ToolResolverContractError("project_available must be a boolean.")
    if not isinstance(snapshot_available, bool):
        raise ToolResolverContractError("snapshot_available must be a boolean.")

    try:
        resolution = resolve_tool(
            tool_id,
            definition_factories=definition_factories,
        )
    except ToolResolverContractError:
        raise

    return _eligibility_from_resolution(
        resolution,
        consent_granted=consent_granted,
        project_available=project_available,
        snapshot_available=snapshot_available,
    )


def _eligibility_from_resolution(
    resolution: ToolResolution,
    *,
    consent_granted: bool,
    project_available: bool,
    snapshot_available: bool,
) -> ToolEligibility:
    reasons: list[str] = []
    warnings = tuple(resolution.warnings)

    if not resolution.is_resolvable:
        reasons.append("tool_not_resolved")

    if resolution.enabled_by_default is False:
        reasons.append("tool_disabled")

    if resolution.authority_level != ToolAuthorityLevel.DETERMINISTIC.value:
        reasons.append("unsupported_authority_level")

    if resolution.scope != ToolScope.SESSION.value:
        reasons.append("unsupported_scope")

    if tuple(resolution.side_effects) != (ToolSideEffect.NONE.value,):
        reasons.append("side_effects_not_allowed")

    if resolution.can_govern_truth is not False:
        reasons.append("truth_governance_not_allowed")

    if resolution.requires_consent is True and consent_granted is False:
        reasons.append("consent_required")

    if resolution.requires_project is True and project_available is False:
        reasons.append("project_required")

    if resolution.requires_snapshot is True and snapshot_available is False:
        reasons.append("snapshot_required")

    is_eligible = not reasons
    if is_eligible:
        reasons.append("eligible")

    return ToolEligibility(
        tool_id=resolution.tool_id,
        is_eligible=is_eligible,
        decision=(
            ToolEligibilityDecision.ALLOW
            if is_eligible
            else ToolEligibilityDecision.DENY
        ),
        reasons=tuple(reasons),
        warnings=warnings,
        resolution_status=resolution.status.value,
        can_govern_truth=resolution.can_govern_truth,
        requires_consent=resolution.requires_consent,
        consent_granted=consent_granted,
        requires_project=resolution.requires_project,
        project_available=project_available,
        requires_snapshot=resolution.requires_snapshot,
        snapshot_available=snapshot_available,
    )
