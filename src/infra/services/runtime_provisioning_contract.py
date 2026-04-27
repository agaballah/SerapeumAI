# -*- coding: utf-8 -*-
"""
Runtime provisioning design contract.

This module defines future provisioning plans without executing them.

Wave 1B-7 rules:
- no operational provisioning
- no provider start/stop
- no model download
- no model load/unload
- no runtime install
- no internet use
- no config mutation
- no persistence
- no UI action behavior

It is a design/source contract only.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Dict, Iterable, List, Optional

from src.infra.services.runtime_consent import (
    ConsentAction,
    ConsentRisk,
    RuntimeConsentPolicy,
    RuntimeConsentState,
)


class ProvisioningActionType(str, Enum):
    INTERNET_CHECK = "internet_check"
    MODEL_DOWNLOAD = "model_download"
    RUNTIME_INSTALL = "runtime_install"
    PROVIDER_START = "provider_start"
    PROVIDER_STOP = "provider_stop"
    MODEL_LOAD = "model_load"
    MODEL_UNLOAD = "model_unload"
    NON_LOCAL_ENDPOINT_ENABLE = "non_local_endpoint_enable"


class ProvisioningPlanStatus(str, Enum):
    BLOCKED = "blocked"
    ELIGIBLE = "eligible"


@dataclass(frozen=True)
class ProvisioningSideEffects:
    internet_used: bool = False
    provider_mutated: bool = False
    model_download_attempted: bool = False
    model_load_attempted: bool = False
    model_unload_attempted: bool = False
    runtime_install_attempted: bool = False
    config_mutated: bool = False
    persistence_written: bool = False
    project_data_may_leave_machine: bool = False

    def to_dict(self) -> Dict[str, bool]:
        return asdict(self)


@dataclass(frozen=True)
class ProvisioningStep:
    action_type: ProvisioningActionType
    title: str
    description: str
    consent_actions_required: List[ConsentAction]
    side_effects_declared: ProvisioningSideEffects
    target: str = ""
    metadata: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        data = asdict(self)
        data["action_type"] = self.action_type.value
        data["consent_actions_required"] = [action.value for action in self.consent_actions_required]
        data["side_effects_declared"] = self.side_effects_declared.to_dict()
        return data


@dataclass(frozen=True)
class ProvisioningPlanValidation:
    status: ProvisioningPlanStatus
    missing_consent_actions: List[ConsentAction]
    highest_risk: ConsentRisk
    can_execute: bool
    reasons: List[str]

    def to_dict(self) -> Dict[str, object]:
        return {
            "status": self.status.value,
            "missing_consent_actions": [action.value for action in self.missing_consent_actions],
            "highest_risk": self.highest_risk.value,
            "can_execute": self.can_execute,
            "reasons": list(self.reasons),
        }


_RISK_ORDER = {
    ConsentRisk.LOW: 1,
    ConsentRisk.MEDIUM: 2,
    ConsentRisk.HIGH: 3,
}


_ACTION_CONSENT_MAP = {
    ProvisioningActionType.INTERNET_CHECK: [ConsentAction.INTERNET_USE],
    ProvisioningActionType.MODEL_DOWNLOAD: [ConsentAction.INTERNET_USE, ConsentAction.MODEL_DOWNLOAD],
    ProvisioningActionType.RUNTIME_INSTALL: [ConsentAction.INTERNET_USE, ConsentAction.RUNTIME_INSTALL],
    ProvisioningActionType.PROVIDER_START: [ConsentAction.PROVIDER_START],
    ProvisioningActionType.PROVIDER_STOP: [ConsentAction.PROVIDER_STOP],
    ProvisioningActionType.MODEL_LOAD: [ConsentAction.MODEL_LOAD],
    ProvisioningActionType.MODEL_UNLOAD: [ConsentAction.MODEL_UNLOAD],
    ProvisioningActionType.NON_LOCAL_ENDPOINT_ENABLE: [
        ConsentAction.INTERNET_USE,
        ConsentAction.NON_LOCAL_ENDPOINT_USE,
    ],
}


def consent_actions_for_provisioning(action_type: ProvisioningActionType | str) -> List[ConsentAction]:
    normalized = ProvisioningActionType(action_type)
    return list(_ACTION_CONSENT_MAP[normalized])


def declared_side_effects_for(action_type: ProvisioningActionType | str) -> ProvisioningSideEffects:
    normalized = ProvisioningActionType(action_type)

    if normalized == ProvisioningActionType.INTERNET_CHECK:
        return ProvisioningSideEffects(internet_used=True)

    if normalized == ProvisioningActionType.MODEL_DOWNLOAD:
        return ProvisioningSideEffects(
            internet_used=True,
            model_download_attempted=True,
            persistence_written=True,
        )

    if normalized == ProvisioningActionType.RUNTIME_INSTALL:
        return ProvisioningSideEffects(
            internet_used=True,
            runtime_install_attempted=True,
            config_mutated=True,
            persistence_written=True,
        )

    if normalized in {ProvisioningActionType.PROVIDER_START, ProvisioningActionType.PROVIDER_STOP}:
        return ProvisioningSideEffects(provider_mutated=True)

    if normalized == ProvisioningActionType.MODEL_LOAD:
        return ProvisioningSideEffects(model_load_attempted=True, provider_mutated=True)

    if normalized == ProvisioningActionType.MODEL_UNLOAD:
        return ProvisioningSideEffects(model_unload_attempted=True, provider_mutated=True)

    if normalized == ProvisioningActionType.NON_LOCAL_ENDPOINT_ENABLE:
        return ProvisioningSideEffects(
            internet_used=True,
            config_mutated=True,
            persistence_written=True,
            project_data_may_leave_machine=True,
        )

    return ProvisioningSideEffects()


def build_provisioning_step(
    action_type: ProvisioningActionType | str,
    *,
    title: str,
    description: str,
    target: str = "",
    metadata: Optional[Dict[str, str]] = None,
) -> ProvisioningStep:
    normalized = ProvisioningActionType(action_type)
    return ProvisioningStep(
        action_type=normalized,
        title=str(title or normalized.value),
        description=str(description or ""),
        consent_actions_required=consent_actions_for_provisioning(normalized),
        side_effects_declared=declared_side_effects_for(normalized),
        target=str(target or ""),
        metadata=dict(metadata or {}),
    )


def _highest_risk_for(consent_actions: Iterable[ConsentAction]) -> ConsentRisk:
    highest = ConsentRisk.LOW
    for action in consent_actions:
        requirement = RuntimeConsentPolicy.requirement_for(action)
        if _RISK_ORDER[requirement.risk] > _RISK_ORDER[highest]:
            highest = requirement.risk
    return highest


def validate_provisioning_plan(
    steps: Iterable[ProvisioningStep],
    consent_state: RuntimeConsentState,
) -> ProvisioningPlanValidation:
    rows = list(steps or [])
    required_actions: List[ConsentAction] = []
    reasons: List[str] = []

    for step in rows:
        for action in step.consent_actions_required:
            if action not in required_actions:
                required_actions.append(action)

    missing = [action for action in required_actions if not consent_state.is_granted(action)]

    if not rows:
        reasons.append("No provisioning steps were supplied.")
    for action in missing:
        reasons.append(f"Missing consent: {action.value}")

    highest = _highest_risk_for(required_actions) if required_actions else ConsentRisk.LOW
    can_execute = bool(rows) and not missing

    return ProvisioningPlanValidation(
        status=ProvisioningPlanStatus.ELIGIBLE if can_execute else ProvisioningPlanStatus.BLOCKED,
        missing_consent_actions=missing,
        highest_risk=highest,
        can_execute=can_execute,
        reasons=reasons,
    )


def build_design_only_plan_summary(steps: Iterable[ProvisioningStep]) -> Dict[str, object]:
    """
    Return a serializable provisioning plan summary.

    This function never executes the plan.
    """
    rows = list(steps or [])
    all_actions: List[ConsentAction] = []
    for step in rows:
        for action in step.consent_actions_required:
            if action not in all_actions:
                all_actions.append(action)

    side_effects = ProvisioningSideEffects()
    merged = side_effects.to_dict()
    for step in rows:
        declared = step.side_effects_declared.to_dict()
        for key, value in declared.items():
            merged[key] = bool(merged.get(key, False) or value)

    return {
        "schema_version": 1,
        "step_count": len(rows),
        "steps": [step.to_dict() for step in rows],
        "consent_actions_required": [action.value for action in all_actions],
        "declared_side_effects": merged,
        "executes": False,
    }
