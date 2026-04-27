# -*- coding: utf-8 -*-
"""
Wave 1B-8: runtime consent UX copy contract tests.
"""

from src.infra.services.runtime_consent import ConsentAction
from src.infra.services.runtime_consent_copy import (
    all_consent_copy,
    consent_copy_for,
    provisioning_plan_copy_summary,
)
from src.infra.services.runtime_provisioning_contract import (
    ProvisioningActionType,
    build_provisioning_step,
)


def test_every_consent_action_has_copy():
    copy = all_consent_copy()

    assert set(copy.keys()) == {action.value for action in ConsentAction}
    for action, row in copy.items():
        assert row["action"] == action
        assert row["title"]
        assert row["body"]
        assert row["confirm_label"]
        assert row["cancel_label"] == "Cancel"
        assert row["warning"]


def test_internet_copy_does_not_claim_project_upload():
    copy = consent_copy_for(ConsentAction.INTERNET_USE)

    assert "internet" in copy.body.lower()
    assert "project documents will not be uploaded by this permission alone" in copy.body.lower()
    assert "fully offline" in copy.warning.lower()


def test_model_download_copy_mentions_internet_and_local_disk_change():
    copy = consent_copy_for(ConsentAction.MODEL_DOWNLOAD)

    body = copy.body.lower()
    assert "download" in body
    assert "internet" in body
    assert "local disk" in body
    assert "license" in copy.warning.lower()


def test_runtime_install_copy_mentions_internet_and_machine_state_change():
    copy = consent_copy_for(ConsentAction.RUNTIME_INSTALL)

    body = copy.body.lower()
    assert "install" in body
    assert "internet" in body
    assert "local machine state" in body


def test_provider_start_copy_mentions_local_machine_resources_not_upload():
    copy = consent_copy_for(ConsentAction.PROVIDER_START)

    assert "local runtime provider" in copy.body.lower()
    assert "does not upload project data by itself" in copy.body.lower()
    assert "gpu" in copy.warning.lower()


def test_model_load_copy_mentions_local_runtime_resources():
    copy = consent_copy_for(ConsentAction.MODEL_LOAD)

    body = copy.body.lower()
    assert "local runtime" in body
    assert "cpu" in body
    assert "gpu" in body


def test_non_local_endpoint_copy_explicitly_warns_project_data_may_leave_machine():
    copy = consent_copy_for(ConsentAction.NON_LOCAL_ENDPOINT_USE)

    body = copy.body.lower()
    warning = copy.warning.lower()
    assert "not local" in body
    assert "project text" in body
    assert "may leave the machine" in body
    assert "cloud" in warning or "external" in warning


def test_copy_never_implies_automatic_approval_or_hidden_execution():
    forbidden = [
        "automatically approved",
        "without asking",
        "silently",
        "background download",
        "will proceed",
    ]

    for row in all_consent_copy().values():
        text = " ".join(
            [
                row["title"],
                row["body"],
                row["confirm_label"],
                row["cancel_label"],
                row["warning"],
            ]
        ).lower()
        for phrase in forbidden:
            assert phrase not in text


def test_plan_copy_summary_is_non_executing_and_collects_copy():
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

    summary = provisioning_plan_copy_summary(steps)

    assert summary["schema_version"] == 1
    assert summary["step_count"] == 2
    assert summary["requires_user_approval"] is True
    assert summary["executes"] is False
    assert summary["consent_actions"] == [
        ConsentAction.INTERNET_USE.value,
        ConsentAction.MODEL_DOWNLOAD.value,
        ConsentAction.MODEL_LOAD.value,
    ]
    assert any("download" in title.lower() for title in summary["titles"])
    assert summary["warnings"]


def test_empty_plan_copy_summary_requires_no_approval_and_never_executes():
    summary = provisioning_plan_copy_summary([])

    assert summary["step_count"] == 0
    assert summary["requires_user_approval"] is False
    assert summary["executes"] is False
    assert summary["consent_actions"] == []
