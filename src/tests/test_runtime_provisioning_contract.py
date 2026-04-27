# -*- coding: utf-8 -*-
"""
Wave 1B-7: runtime provisioning design contract tests.
"""

from src.infra.services.runtime_consent import (
    ConsentAction,
    ConsentDecision,
    ConsentRisk,
    ConsentScope,
    RuntimeConsentState,
)
from src.infra.services.runtime_provisioning_contract import (
    ProvisioningActionType,
    ProvisioningPlanStatus,
    build_design_only_plan_summary,
    build_provisioning_step,
    consent_actions_for_provisioning,
    declared_side_effects_for,
    validate_provisioning_plan,
)


def test_every_provisioning_action_maps_to_explicit_consent():
    for action_type in ProvisioningActionType:
        actions = consent_actions_for_provisioning(action_type)
        assert actions
        assert all(isinstance(action, ConsentAction) for action in actions)


def test_model_download_requires_internet_and_model_download_consent():
    actions = consent_actions_for_provisioning(ProvisioningActionType.MODEL_DOWNLOAD)

    assert actions == [ConsentAction.INTERNET_USE, ConsentAction.MODEL_DOWNLOAD]


def test_runtime_install_requires_internet_and_runtime_install_consent():
    actions = consent_actions_for_provisioning(ProvisioningActionType.RUNTIME_INSTALL)

    assert actions == [ConsentAction.INTERNET_USE, ConsentAction.RUNTIME_INSTALL]


def test_non_local_endpoint_requires_high_risk_boundary_consent():
    actions = consent_actions_for_provisioning(ProvisioningActionType.NON_LOCAL_ENDPOINT_ENABLE)
    effects = declared_side_effects_for(ProvisioningActionType.NON_LOCAL_ENDPOINT_ENABLE)

    assert actions == [ConsentAction.INTERNET_USE, ConsentAction.NON_LOCAL_ENDPOINT_USE]
    assert effects.internet_used is True
    assert effects.project_data_may_leave_machine is True
    assert effects.config_mutated is True


def test_action_side_effects_are_distinguishable():
    assert declared_side_effects_for(ProvisioningActionType.PROVIDER_START).provider_mutated is True
    assert declared_side_effects_for(ProvisioningActionType.MODEL_LOAD).model_load_attempted is True
    assert declared_side_effects_for(ProvisioningActionType.MODEL_UNLOAD).model_unload_attempted is True
    assert declared_side_effects_for(ProvisioningActionType.RUNTIME_INSTALL).runtime_install_attempted is True
    assert declared_side_effects_for(ProvisioningActionType.MODEL_DOWNLOAD).model_download_attempted is True


def test_plan_validation_is_deny_by_default_without_consent():
    state = RuntimeConsentState()
    step = build_provisioning_step(
        ProvisioningActionType.MODEL_DOWNLOAD,
        title="Download model",
        description="Future model download plan.",
        target="balanced-7b-local-q4",
    )

    validation = validate_provisioning_plan([step], state)

    assert validation.status == ProvisioningPlanStatus.BLOCKED
    assert validation.can_execute is False
    assert validation.missing_consent_actions == [ConsentAction.INTERNET_USE, ConsentAction.MODEL_DOWNLOAD]
    assert validation.highest_risk == ConsentRisk.MEDIUM


def test_plan_becomes_eligible_only_after_all_required_consents_are_granted():
    state = RuntimeConsentState()
    step = build_provisioning_step(
        ProvisioningActionType.PROVIDER_START,
        title="Start provider",
        description="Future provider start plan.",
        target="lm_studio",
    )

    blocked = validate_provisioning_plan([step], state)
    assert blocked.can_execute is False

    state.record_decision(ConsentAction.PROVIDER_START, ConsentDecision.APPROVED, scope=ConsentScope.SESSION)

    allowed = validate_provisioning_plan([step], state)
    assert allowed.status == ProvisioningPlanStatus.ELIGIBLE
    assert allowed.can_execute is True
    assert allowed.missing_consent_actions == []


def test_rejected_consent_keeps_plan_blocked():
    state = RuntimeConsentState()
    state.record_decision(ConsentAction.RUNTIME_INSTALL, ConsentDecision.REJECTED, scope=ConsentScope.SESSION)

    step = build_provisioning_step(
        ProvisioningActionType.RUNTIME_INSTALL,
        title="Install runtime",
        description="Future runtime install plan.",
        target="ollama",
    )

    validation = validate_provisioning_plan([step], state)

    assert validation.status == ProvisioningPlanStatus.BLOCKED
    assert validation.can_execute is False
    assert ConsentAction.RUNTIME_INSTALL in validation.missing_consent_actions


def test_empty_plan_is_blocked_and_non_executing():
    validation = validate_provisioning_plan([], RuntimeConsentState())

    assert validation.status == ProvisioningPlanStatus.BLOCKED
    assert validation.can_execute is False
    assert "No provisioning steps were supplied." in validation.reasons


def test_design_only_summary_never_executes():
    step = build_provisioning_step(
        ProvisioningActionType.MODEL_LOAD,
        title="Load model",
        description="Future model load plan.",
        target="chat",
    )

    summary = build_design_only_plan_summary([step])

    assert summary["schema_version"] == 1
    assert summary["step_count"] == 1
    assert summary["executes"] is False
    assert summary["declared_side_effects"]["model_load_attempted"] is True
    assert summary["declared_side_effects"]["provider_mutated"] is True


def test_multi_step_summary_merges_consent_and_side_effects():
    steps = [
        build_provisioning_step(
            ProvisioningActionType.MODEL_DOWNLOAD,
            title="Download model",
            description="Future model download.",
        ),
        build_provisioning_step(
            ProvisioningActionType.MODEL_LOAD,
            title="Load model",
            description="Future model load.",
        ),
    ]

    summary = build_design_only_plan_summary(steps)

    assert summary["consent_actions_required"] == [
        ConsentAction.INTERNET_USE.value,
        ConsentAction.MODEL_DOWNLOAD.value,
        ConsentAction.MODEL_LOAD.value,
    ]
    assert summary["declared_side_effects"]["internet_used"] is True
    assert summary["declared_side_effects"]["model_download_attempted"] is True
    assert summary["declared_side_effects"]["model_load_attempted"] is True
    assert summary["executes"] is False
