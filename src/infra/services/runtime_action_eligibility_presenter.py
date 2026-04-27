# -*- coding: utf-8 -*-
"""
Runtime action eligibility presenter.

Converts design-only provisioning plans into UI-safe eligibility rows.

This module never executes provisioning. It only explains:
- whether future actions are blocked or eligible
- which consent actions are missing
- what side effects would occur
- which consent copy should be shown
"""

from __future__ import annotations

from typing import Dict, Iterable, List

from src.infra.services.runtime_consent import ConsentAction, RuntimeConsentState
from src.infra.services.runtime_consent_copy import consent_copy_for
from src.infra.services.runtime_provisioning_contract import (
    ProvisioningPlanStatus,
    ProvisioningStep,
    build_design_only_plan_summary,
    validate_provisioning_plan,
)


def _display_status(status: ProvisioningPlanStatus) -> str:
    if status == ProvisioningPlanStatus.ELIGIBLE:
        return "Eligible after consent"
    return "Blocked - consent required"


def _side_effect_summary(declared_side_effects: Dict[str, bool]) -> List[str]:
    effects: List[str] = []

    if declared_side_effects.get("internet_used"):
        effects.append("Uses internet")
    if declared_side_effects.get("provider_mutated"):
        effects.append("Changes local provider/runtime state")
    if declared_side_effects.get("model_download_attempted"):
        effects.append("Downloads model files")
    if declared_side_effects.get("model_load_attempted"):
        effects.append("Loads a model into local runtime")
    if declared_side_effects.get("model_unload_attempted"):
        effects.append("Unloads a model from local runtime")
    if declared_side_effects.get("runtime_install_attempted"):
        effects.append("Installs runtime components")
    if declared_side_effects.get("config_mutated"):
        effects.append("Changes configuration")
    if declared_side_effects.get("persistence_written"):
        effects.append("Writes local state")
    if declared_side_effects.get("project_data_may_leave_machine"):
        effects.append("Project data may leave this machine")

    return effects or ["No side effects declared"]


def present_runtime_action_eligibility(
    steps: Iterable[ProvisioningStep],
    consent_state: RuntimeConsentState,
) -> Dict[str, object]:
    rows = list(steps or [])
    validation = validate_provisioning_plan(rows, consent_state)
    summary = build_design_only_plan_summary(rows)

    missing_actions = list(validation.missing_consent_actions)
    missing_copy = [consent_copy_for(action).to_dict() for action in missing_actions]

    all_consent_actions = [ConsentAction(action) for action in summary.get("consent_actions_required", [])]
    consent_rows = [consent_copy_for(action).to_dict() for action in all_consent_actions]

    side_effects = summary.get("declared_side_effects", {})
    if not isinstance(side_effects, dict):
        side_effects = {}

    eligible = bool(validation.can_execute)

    return {
        "schema_version": 1,
        "status": validation.status.value,
        "display_status": _display_status(validation.status),
        "eligible": eligible,
        "can_execute": False,
        "executes": False,
        "execution_message": "This presenter never executes runtime actions.",
        "step_count": len(rows),
        "reasons": list(validation.reasons),
        "missing_consent_actions": [action.value for action in missing_actions],
        "missing_consent_copy": missing_copy,
        "consent_copy": consent_rows,
        "declared_side_effects": dict(side_effects),
        "side_effect_summary": _side_effect_summary(side_effects),
        "highest_risk": validation.highest_risk.value,
        "action_rows": [
            {
                "action_type": step.action_type.value,
                "title": step.title,
                "target": step.target,
                "description": step.description,
                "consent_actions_required": [action.value for action in step.consent_actions_required],
                "side_effects_declared": step.side_effects_declared.to_dict(),
            }
            for step in rows
        ],
    }
