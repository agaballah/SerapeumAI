# -*- coding: utf-8 -*-
"""
Wave 1B-3: runtime consent state model tests.
"""

import pytest

from src.infra.services.runtime_consent import (
    ConsentAction,
    ConsentDecision,
    ConsentRisk,
    ConsentScope,
    RuntimeConsentPolicy,
    RuntimeConsentState,
    consent_required_for,
)


def test_all_runtime_actions_require_consent_by_default():
    for action in ConsentAction:
        requirement = RuntimeConsentPolicy.requirement_for(action)
        assert requirement.required is True
        assert consent_required_for(action) is True


def test_default_state_denies_every_action():
    state = RuntimeConsentState()

    for action in ConsentAction:
        assert state.is_granted(action) is False


def test_non_local_endpoint_is_high_risk_and_may_send_project_data():
    requirement = RuntimeConsentPolicy.requirement_for(ConsentAction.NON_LOCAL_ENDPOINT_USE)

    assert requirement.risk == ConsentRisk.HIGH
    assert requirement.internet_required is True
    assert requirement.project_data_may_leave_machine is True
    assert requirement.machine_state_changes is False


def test_local_provider_start_changes_machine_state_without_project_data_leaving():
    requirement = RuntimeConsentPolicy.requirement_for(ConsentAction.PROVIDER_START)

    assert requirement.risk == ConsentRisk.MEDIUM
    assert requirement.internet_required is False
    assert requirement.machine_state_changes is True
    assert requirement.project_data_may_leave_machine is False


def test_model_download_requires_internet_and_machine_state_change():
    requirement = RuntimeConsentPolicy.requirement_for(ConsentAction.MODEL_DOWNLOAD)

    assert requirement.internet_required is True
    assert requirement.machine_state_changes is True
    assert requirement.project_data_may_leave_machine is False


def test_session_approval_grants_only_until_session_clear():
    state = RuntimeConsentState()

    grant = state.record_decision(
        ConsentAction.PROVIDER_START,
        ConsentDecision.APPROVED,
        scope=ConsentScope.SESSION,
        reason="user approved start",
    )

    assert grant.granted is True
    assert state.is_granted(ConsentAction.PROVIDER_START) is True

    state.clear_session()

    assert state.is_granted(ConsentAction.PROVIDER_START) is False


def test_persistent_approval_survives_session_clear_in_memory_only():
    state = RuntimeConsentState()

    state.record_decision(
        ConsentAction.MODEL_LOAD,
        ConsentDecision.APPROVED,
        scope=ConsentScope.PERSISTENT,
        reason="user approved persistent load preference",
    )

    state.clear_session()

    assert state.is_granted(ConsentAction.MODEL_LOAD) is True


def test_rejected_decision_never_creates_grant():
    state = RuntimeConsentState()

    grant = state.record_decision(
        ConsentAction.INTERNET_USE,
        ConsentDecision.REJECTED,
        scope=ConsentScope.SESSION,
        reason="user declined internet",
    )

    assert grant.granted is False
    assert state.is_granted(ConsentAction.INTERNET_USE) is False
    assert state.snapshot() == {}


def test_rejection_revokes_existing_grant_in_same_scope():
    state = RuntimeConsentState()

    state.record_decision(ConsentAction.PROVIDER_STOP, ConsentDecision.APPROVED, scope=ConsentScope.SESSION)
    assert state.is_granted(ConsentAction.PROVIDER_STOP) is True

    state.record_decision(ConsentAction.PROVIDER_STOP, ConsentDecision.REJECTED, scope=ConsentScope.SESSION)

    assert state.is_granted(ConsentAction.PROVIDER_STOP) is False


def test_revoke_without_scope_removes_session_and_persistent_grants():
    state = RuntimeConsentState()

    state.record_decision(ConsentAction.MODEL_UNLOAD, ConsentDecision.APPROVED, scope=ConsentScope.SESSION)
    state.record_decision(ConsentAction.MODEL_UNLOAD, ConsentDecision.APPROVED, scope=ConsentScope.PERSISTENT)
    assert state.is_granted(ConsentAction.MODEL_UNLOAD) is True

    state.revoke(ConsentAction.MODEL_UNLOAD)

    assert state.is_granted(ConsentAction.MODEL_UNLOAD) is False


def test_snapshot_prefers_session_grant_over_persistent_for_same_action():
    state = RuntimeConsentState()

    state.record_decision(ConsentAction.RUNTIME_INSTALL, ConsentDecision.APPROVED, scope=ConsentScope.PERSISTENT, reason="persistent")
    state.record_decision(ConsentAction.RUNTIME_INSTALL, ConsentDecision.APPROVED, scope=ConsentScope.SESSION, reason="session")

    snapshot = state.snapshot()

    assert snapshot[ConsentAction.RUNTIME_INSTALL.value]["scope"] == ConsentScope.SESSION.value
    assert snapshot[ConsentAction.RUNTIME_INSTALL.value]["reason"] == "session"


def test_all_requirements_are_serializable_and_sorted_by_action():
    data = RuntimeConsentPolicy.all_requirements()

    assert list(data.keys()) == sorted(action.value for action in ConsentAction)
    for action, row in data.items():
        assert row["action"] == action
        assert row["required"] is True
        assert row["risk"] in {risk.value for risk in ConsentRisk}


def test_invalid_action_is_rejected_loudly():
    with pytest.raises(ValueError):
        RuntimeConsentPolicy.requirement_for("not_a_real_action")
