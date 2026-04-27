# -*- coding: utf-8 -*-
"""
Wave 1B-9: runtime action eligibility presenter tests.
"""

from src.infra.services.runtime_action_eligibility_presenter import present_runtime_action_eligibility
from src.infra.services.runtime_consent import ConsentAction, ConsentDecision, ConsentScope, RuntimeConsentState
from src.infra.services.runtime_provisioning_contract import (
    ProvisioningActionType,
    build_provisioning_step,
)


def test_missing_consent_produces_blocked_status_with_copy():
    state = RuntimeConsentState()
    step = build_provisioning_step(
        ProvisioningActionType.MODEL_DOWNLOAD,
        title="Download model",
        description="Future model download.",
        target="balanced-7b-local-q4",
    )

    out = present_runtime_action_eligibility([step], state)

    assert out["status"] == "blocked"
    assert out["display_status"] == "Blocked - consent required"
    assert out["eligible"] is False
    assert out["can_execute"] is False
    assert out["executes"] is False
    assert out["missing_consent_actions"] == [
        ConsentAction.INTERNET_USE.value,
        ConsentAction.MODEL_DOWNLOAD.value,
    ]
    assert len(out["missing_consent_copy"]) == 2
    assert any("Download" in row["title"] for row in out["missing_consent_copy"])


def test_full_consent_produces_eligible_but_non_executing_status():
    state = RuntimeConsentState()
    state.record_decision(ConsentAction.PROVIDER_START, ConsentDecision.APPROVED, scope=ConsentScope.SESSION)

    step = build_provisioning_step(
        ProvisioningActionType.PROVIDER_START,
        title="Start local provider",
        description="Future provider start.",
        target="lm_studio",
    )

    out = present_runtime_action_eligibility([step], state)

    assert out["status"] == "eligible"
    assert out["display_status"] == "Eligible after consent"
    assert out["eligible"] is True
    assert out["can_execute"] is False
    assert out["executes"] is False
    assert "never executes" in out["execution_message"]


def test_side_effect_summary_discloses_download_and_local_write():
    state = RuntimeConsentState()
    step = build_provisioning_step(
        ProvisioningActionType.MODEL_DOWNLOAD,
        title="Download model",
        description="Future model download.",
    )

    out = present_runtime_action_eligibility([step], state)

    assert "Uses internet" in out["side_effect_summary"]
    assert "Downloads model files" in out["side_effect_summary"]
    assert "Writes local state" in out["side_effect_summary"]


def test_non_local_endpoint_discloses_project_data_boundary_risk():
    state = RuntimeConsentState()
    step = build_provisioning_step(
        ProvisioningActionType.NON_LOCAL_ENDPOINT_ENABLE,
        title="Use non-local endpoint",
        description="Future endpoint enablement.",
        target="https://example.invalid/v1",
    )

    out = present_runtime_action_eligibility([step], state)

    assert out["highest_risk"] == "high"
    assert "Project data may leave this machine" in out["side_effect_summary"]
    assert ConsentAction.NON_LOCAL_ENDPOINT_USE.value in out["missing_consent_actions"]


def test_empty_plan_is_blocked_and_non_executing():
    out = present_runtime_action_eligibility([], RuntimeConsentState())

    assert out["status"] == "blocked"
    assert out["eligible"] is False
    assert out["can_execute"] is False
    assert out["executes"] is False
    assert out["step_count"] == 0
    assert "No provisioning steps were supplied." in out["reasons"]


def test_output_never_implies_automatic_execution_or_approval():
    state = RuntimeConsentState()
    state.record_decision(ConsentAction.MODEL_LOAD, ConsentDecision.APPROVED, scope=ConsentScope.SESSION)

    step = build_provisioning_step(
        ProvisioningActionType.MODEL_LOAD,
        title="Load model",
        description="Future model load.",
    )

    out = present_runtime_action_eligibility([step], state)
    text = str(out).lower()

    forbidden = [
        "automatically approved",
        "without asking",
        "silently",
        "will proceed",
        "executing now",
    ]

    for phrase in forbidden:
        assert phrase not in text
    assert out["executes"] is False
    assert out["can_execute"] is False


def test_action_rows_include_action_target_and_required_consent():
    step = build_provisioning_step(
        ProvisioningActionType.RUNTIME_INSTALL,
        title="Install runtime",
        description="Future runtime install.",
        target="ollama",
    )

    out = present_runtime_action_eligibility([step], RuntimeConsentState())

    assert out["action_rows"] == [
        {
            "action_type": "runtime_install",
            "title": "Install runtime",
            "target": "ollama",
            "description": "Future runtime install.",
            "consent_actions_required": [
                ConsentAction.INTERNET_USE.value,
                ConsentAction.RUNTIME_INSTALL.value,
            ],
            "side_effects_declared": {
                "internet_used": True,
                "provider_mutated": False,
                "model_download_attempted": False,
                "model_load_attempted": False,
                "model_unload_attempted": False,
                "runtime_install_attempted": True,
                "config_mutated": True,
                "persistence_written": True,
                "project_data_may_leave_machine": False,
            },
        }
    ]
