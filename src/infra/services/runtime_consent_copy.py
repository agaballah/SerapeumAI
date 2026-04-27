# -*- coding: utf-8 -*-
"""
Runtime consent UX copy contract.

This module freezes user-facing consent language before future runtime
provisioning actions are wired.

It is copy/contract only:
- no operational provisioning
- no UI action buttons
- no provider mutation
- no model download/load/unload
- no runtime install
- no internet use
- no persistence
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, Iterable, List

from src.infra.services.runtime_consent import ConsentAction, RuntimeConsentPolicy
from src.infra.services.runtime_provisioning_contract import ProvisioningStep


@dataclass(frozen=True)
class ConsentCopy:
    action: ConsentAction
    title: str
    body: str
    confirm_label: str
    cancel_label: str
    warning: str

    def to_dict(self) -> Dict[str, str]:
        data = asdict(self)
        data["action"] = self.action.value
        return data


_COPY: Dict[ConsentAction, ConsentCopy] = {
    ConsentAction.INTERNET_USE: ConsentCopy(
        action=ConsentAction.INTERNET_USE,
        title="Allow internet access?",
        body=(
            "SerapeumAI can use the internet for this requested runtime action. "
            "Project documents will not be uploaded by this permission alone."
        ),
        confirm_label="Allow internet for this action",
        cancel_label="Cancel",
        warning="Do not continue if this project must remain fully offline.",
    ),
    ConsentAction.MODEL_DOWNLOAD: ConsentCopy(
        action=ConsentAction.MODEL_DOWNLOAD,
        title="Download a local AI model?",
        body=(
            "SerapeumAI can download the selected model file and store it on this computer. "
            "This uses the internet and changes local disk state."
        ),
        confirm_label="Download model",
        cancel_label="Cancel",
        warning="Model files may be large. Confirm the source, size, and license before continuing.",
    ),
    ConsentAction.PROVIDER_START: ConsentCopy(
        action=ConsentAction.PROVIDER_START,
        title="Start local runtime provider?",
        body=(
            "SerapeumAI can start the selected local runtime provider on this computer. "
            "This changes local machine runtime state but does not upload project data by itself."
        ),
        confirm_label="Start local provider",
        cancel_label="Cancel",
        warning="Starting a provider may consume CPU, RAM, or GPU resources.",
    ),
    ConsentAction.PROVIDER_STOP: ConsentCopy(
        action=ConsentAction.PROVIDER_STOP,
        title="Stop local runtime provider?",
        body=(
            "SerapeumAI can stop the selected local runtime provider on this computer. "
            "This changes local machine runtime state."
        ),
        confirm_label="Stop local provider",
        cancel_label="Cancel",
        warning="Stopping a provider may interrupt running local AI tasks.",
    ),
    ConsentAction.MODEL_LOAD: ConsentCopy(
        action=ConsentAction.MODEL_LOAD,
        title="Load model into local runtime?",
        body=(
            "SerapeumAI can ask the local runtime to load the selected model. "
            "This changes local runtime state and may consume CPU, RAM, or GPU resources."
        ),
        confirm_label="Load model",
        cancel_label="Cancel",
        warning="Large models may make the computer slower while loaded.",
    ),
    ConsentAction.MODEL_UNLOAD: ConsentCopy(
        action=ConsentAction.MODEL_UNLOAD,
        title="Unload model from local runtime?",
        body=(
            "SerapeumAI can ask the local runtime to unload the selected model. "
            "This changes local runtime state."
        ),
        confirm_label="Unload model",
        cancel_label="Cancel",
        warning="Unloading a model may stop active local AI tasks that depend on it.",
    ),
    ConsentAction.NON_LOCAL_ENDPOINT_USE: ConsentCopy(
        action=ConsentAction.NON_LOCAL_ENDPOINT_USE,
        title="Use a non-local AI endpoint?",
        body=(
            "This endpoint is not local to this computer. Project text, prompts, metadata, "
            "or extracted content may leave the machine if this endpoint is used."
        ),
        confirm_label="Use non-local endpoint",
        cancel_label="Cancel",
        warning="Use only if your project rules allow external or cloud processing.",
    ),
    ConsentAction.RUNTIME_INSTALL: ConsentCopy(
        action=ConsentAction.RUNTIME_INSTALL,
        title="Install runtime component?",
        body=(
            "SerapeumAI can install the selected runtime component on this computer. "
            "This uses the internet and changes local machine state."
        ),
        confirm_label="Install runtime component",
        cancel_label="Cancel",
        warning="Only install components from trusted sources and with permission for this workstation.",
    ),
}


def consent_copy_for(action: ConsentAction | str) -> ConsentCopy:
    normalized = ConsentAction(action)
    return _COPY[normalized]


def all_consent_copy() -> Dict[str, Dict[str, str]]:
    return {action.value: _COPY[action].to_dict() for action in sorted(_COPY, key=lambda item: item.value)}


def provisioning_plan_copy_summary(steps: Iterable[ProvisioningStep]) -> Dict[str, object]:
    rows = list(steps or [])
    consent_actions: List[ConsentAction] = []

    for step in rows:
        for action in step.consent_actions_required:
            if action not in consent_actions:
                consent_actions.append(action)

    warnings = [consent_copy_for(action).warning for action in consent_actions]
    requirements = [RuntimeConsentPolicy.requirement_for(action).to_dict() for action in consent_actions]

    return {
        "schema_version": 1,
        "step_count": len(rows),
        "requires_user_approval": bool(consent_actions),
        "executes": False,
        "consent_actions": [action.value for action in consent_actions],
        "titles": [consent_copy_for(action).title for action in consent_actions],
        "warnings": warnings,
        "requirements": requirements,
    }
