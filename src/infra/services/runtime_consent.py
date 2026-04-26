# -*- coding: utf-8 -*-
"""
Runtime consent state model.

This module defines consent requirements and in-memory consent grants before
SerapeumAI implements provider mutation, model download, runtime install,
model load/unload, or non-local endpoint behavior.

It performs no runtime action itself.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Dict, Optional


class ConsentAction(str, Enum):
    INTERNET_USE = "internet_use"
    MODEL_DOWNLOAD = "model_download"
    PROVIDER_START = "provider_start"
    PROVIDER_STOP = "provider_stop"
    MODEL_LOAD = "model_load"
    MODEL_UNLOAD = "model_unload"
    NON_LOCAL_ENDPOINT_USE = "non_local_endpoint_use"
    RUNTIME_INSTALL = "runtime_install"


class ConsentDecision(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"


class ConsentScope(str, Enum):
    SESSION = "session"
    PERSISTENT = "persistent"


class ConsentRisk(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class ConsentRequirement:
    action: ConsentAction
    required: bool
    risk: ConsentRisk
    internet_required: bool
    machine_state_changes: bool
    project_data_may_leave_machine: bool
    reason: str

    def to_dict(self) -> Dict[str, object]:
        data = asdict(self)
        data["action"] = self.action.value
        data["risk"] = self.risk.value
        return data


@dataclass(frozen=True)
class ConsentGrant:
    action: ConsentAction
    scope: ConsentScope
    granted: bool
    reason: str = ""

    def to_dict(self) -> Dict[str, object]:
        data = asdict(self)
        data["action"] = self.action.value
        data["scope"] = self.scope.value
        return data


class RuntimeConsentPolicy:
    """Static consent policy for runtime platform actions."""

    _REQUIREMENTS: Dict[ConsentAction, ConsentRequirement] = {
        ConsentAction.INTERNET_USE: ConsentRequirement(
            action=ConsentAction.INTERNET_USE,
            required=True,
            risk=ConsentRisk.MEDIUM,
            internet_required=True,
            machine_state_changes=False,
            project_data_may_leave_machine=False,
            reason="Internet access must be explicitly approved.",
        ),
        ConsentAction.MODEL_DOWNLOAD: ConsentRequirement(
            action=ConsentAction.MODEL_DOWNLOAD,
            required=True,
            risk=ConsentRisk.MEDIUM,
            internet_required=True,
            machine_state_changes=True,
            project_data_may_leave_machine=False,
            reason="Model downloads use internet and write large local artifacts.",
        ),
        ConsentAction.PROVIDER_START: ConsentRequirement(
            action=ConsentAction.PROVIDER_START,
            required=True,
            risk=ConsentRisk.MEDIUM,
            internet_required=False,
            machine_state_changes=True,
            project_data_may_leave_machine=False,
            reason="Starting a local provider changes machine runtime state.",
        ),
        ConsentAction.PROVIDER_STOP: ConsentRequirement(
            action=ConsentAction.PROVIDER_STOP,
            required=True,
            risk=ConsentRisk.LOW,
            internet_required=False,
            machine_state_changes=True,
            project_data_may_leave_machine=False,
            reason="Stopping a local provider changes machine runtime state.",
        ),
        ConsentAction.MODEL_LOAD: ConsentRequirement(
            action=ConsentAction.MODEL_LOAD,
            required=True,
            risk=ConsentRisk.MEDIUM,
            internet_required=False,
            machine_state_changes=True,
            project_data_may_leave_machine=False,
            reason="Loading a model consumes local machine resources.",
        ),
        ConsentAction.MODEL_UNLOAD: ConsentRequirement(
            action=ConsentAction.MODEL_UNLOAD,
            required=True,
            risk=ConsentRisk.LOW,
            internet_required=False,
            machine_state_changes=True,
            project_data_may_leave_machine=False,
            reason="Unloading a model changes local runtime state.",
        ),
        ConsentAction.NON_LOCAL_ENDPOINT_USE: ConsentRequirement(
            action=ConsentAction.NON_LOCAL_ENDPOINT_USE,
            required=True,
            risk=ConsentRisk.HIGH,
            internet_required=True,
            machine_state_changes=False,
            project_data_may_leave_machine=True,
            reason="Non-local endpoints may receive project text, prompts, or metadata.",
        ),
        ConsentAction.RUNTIME_INSTALL: ConsentRequirement(
            action=ConsentAction.RUNTIME_INSTALL,
            required=True,
            risk=ConsentRisk.HIGH,
            internet_required=True,
            machine_state_changes=True,
            project_data_may_leave_machine=False,
            reason="Runtime installation uses internet and changes this machine.",
        ),
    }

    @classmethod
    def requirement_for(cls, action: ConsentAction | str) -> ConsentRequirement:
        normalized = ConsentAction(action)
        return cls._REQUIREMENTS[normalized]

    @classmethod
    def all_requirements(cls) -> Dict[str, Dict[str, object]]:
        return {action.value: requirement.to_dict() for action, requirement in sorted(cls._REQUIREMENTS.items(), key=lambda item: item[0].value)}


class RuntimeConsentState:
    """
    In-memory consent state.

    Persistence is intentionally out of scope for Wave 1B-3.
    """

    def __init__(self) -> None:
        self._session_grants: Dict[ConsentAction, ConsentGrant] = {}
        self._persistent_grants: Dict[ConsentAction, ConsentGrant] = {}

    def is_granted(self, action: ConsentAction | str) -> bool:
        normalized = ConsentAction(action)
        session = self._session_grants.get(normalized)
        persistent = self._persistent_grants.get(normalized)
        return bool((session and session.granted) or (persistent and persistent.granted))

    def record_decision(
        self,
        action: ConsentAction | str,
        decision: ConsentDecision | str,
        *,
        scope: ConsentScope | str = ConsentScope.SESSION,
        reason: str = "",
    ) -> ConsentGrant:
        normalized_action = ConsentAction(action)
        normalized_decision = ConsentDecision(decision)
        normalized_scope = ConsentScope(scope)

        grant = ConsentGrant(
            action=normalized_action,
            scope=normalized_scope,
            granted=(normalized_decision == ConsentDecision.APPROVED),
            reason=str(reason or ""),
        )

        if not grant.granted:
            self.revoke(normalized_action, scope=normalized_scope)
            return grant

        if normalized_scope == ConsentScope.SESSION:
            self._session_grants[normalized_action] = grant
        else:
            self._persistent_grants[normalized_action] = grant

        return grant

    def revoke(self, action: ConsentAction | str, *, scope: Optional[ConsentScope | str] = None) -> None:
        normalized_action = ConsentAction(action)
        if scope is None:
            self._session_grants.pop(normalized_action, None)
            self._persistent_grants.pop(normalized_action, None)
            return

        normalized_scope = ConsentScope(scope)
        if normalized_scope == ConsentScope.SESSION:
            self._session_grants.pop(normalized_action, None)
        else:
            self._persistent_grants.pop(normalized_action, None)

    def clear_session(self) -> None:
        self._session_grants.clear()

    def snapshot(self) -> Dict[str, Dict[str, object]]:
        rows: Dict[str, Dict[str, object]] = {}
        for action, grant in sorted(self._persistent_grants.items(), key=lambda item: item[0].value):
            rows[action.value] = grant.to_dict()
        for action, grant in sorted(self._session_grants.items(), key=lambda item: item[0].value):
            rows[action.value] = grant.to_dict()
        return rows


def consent_required_for(action: ConsentAction | str) -> bool:
    return RuntimeConsentPolicy.requirement_for(action).required
