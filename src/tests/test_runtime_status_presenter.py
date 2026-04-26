# -*- coding: utf-8 -*-
"""
Wave 1B-2: runtime status presenter tests.
"""

from src.infra.services.runtime_status_presenter import (
    SUMMARY_NO_PROVIDER_REACHABLE,
    SUMMARY_PROVIDER_DISCOVERY_UNAVAILABLE,
    SUMMARY_PROVIDER_REACHABLE_MODEL_NOT_VERIFIED,
    present_runtime_provider_rows,
    present_runtime_status,
)


NO_SIDE_EFFECTS = {
    "internet_used": False,
    "install_attempted": False,
    "start_attempted": False,
    "stop_attempted": False,
    "download_attempted": False,
    "model_load_attempted": False,
    "model_unload_attempted": False,
    "config_mutated": False,
    "project_data_sent": False,
}


def _row(name, status, *, endpoint="http://127.0.0.1:1234", reason="", available=None):
    if available is None:
        available = status == "reachable"
    return {
        "provider_name": name,
        "provider_type": name,
        "endpoint": endpoint,
        "status": status,
        "reason": reason,
        "capabilities": ["local_runtime", "model_listing"],
        "side_effects": dict(NO_SIDE_EFFECTS),
        "available": available,
        "details": {},
    }


def test_presenter_returns_discovery_unavailable_for_empty_input():
    out = present_runtime_status([])

    assert out["summary_status"] == SUMMARY_PROVIDER_DISCOVERY_UNAVAILABLE
    assert out["provider_count"] == 0
    assert out["reachable_provider_count"] == 0
    assert out["providers"] == []


def test_presenter_summarizes_no_reachable_provider_without_app_failure_language():
    out = present_runtime_status(
        [
            _row("lm_studio", "disabled", reason="disabled_in_config"),
            _row("ollama", "unreachable", endpoint="http://127.0.0.1:11434", reason="unreachable:URLError"),
        ]
    )

    assert out["summary_status"] == SUMMARY_NO_PROVIDER_REACHABLE
    assert out["reachable_provider_count"] == 0

    rows = {row["provider_name"]: row for row in out["providers"]}
    assert rows["lm_studio"]["display_status"] == "Disabled"
    assert "not an application failure" in rows["lm_studio"]["warning"]
    assert rows["ollama"]["display_status"] == "Unreachable"
    assert "AI features may remain unavailable" in rows["ollama"]["warning"]


def test_presenter_summarizes_reachable_provider_without_model_ready_overclaim():
    out = present_runtime_status(
        [
            _row("lm_studio", "reachable", reason="probe_ok"),
            _row("ollama", "disabled", endpoint="http://127.0.0.1:11434", reason="disabled_in_config"),
        ]
    )

    assert out["summary_status"] == SUMMARY_PROVIDER_REACHABLE_MODEL_NOT_VERIFIED
    assert out["reachable_provider_count"] == 1
    assert "Model readiness is not yet verified" in out["summary_text"]

    reachable = [row for row in out["providers"] if row["provider_name"] == "lm_studio"][0]
    assert reachable["display_status"] == "Reachable"
    assert reachable["model_readiness"] == "not_verified"
    assert "Model/task readiness is not yet verified" in reachable["warning"]
    assert "ready" not in reachable["display_status"].lower()


def test_non_local_endpoint_is_presented_as_blocked_unsupported():
    rows = present_runtime_provider_rows(
        [
            _row(
                "openai_compatible_local",
                "unsupported",
                endpoint="https://api.openai.com",
                reason="non_local_endpoint_blocked",
                available=False,
            )
        ]
    )

    assert rows[0]["display_status"] == "Unsupported"
    assert "not local" in rows[0]["warning"]
    assert "localhost" in rows[0]["action_hint"]


def test_rows_are_sorted_deterministically():
    rows = present_runtime_provider_rows(
        [
            _row("ollama", "disabled", endpoint="http://127.0.0.1:11434"),
            _row("lm_studio", "disabled", endpoint="http://127.0.0.1:1234"),
        ]
    )

    assert [row["provider_name"] for row in rows] == ["lm_studio", "ollama"]


def test_side_effect_flags_are_preserved_and_summarized():
    dirty = _row("lm_studio", "reachable")
    dirty["side_effects"]["download_attempted"] = True

    rows = present_runtime_provider_rows([dirty])

    assert rows[0]["side_effects"]["download_attempted"] is True
    assert rows[0]["side_effect_free"] is False


def test_side_effect_free_rows_report_true_when_all_flags_false():
    rows = present_runtime_provider_rows([_row("lm_studio", "reachable")])

    assert rows[0]["side_effect_free"] is True


def test_provider_rows_never_claim_ready_in_wave_1b_2():
    rows = present_runtime_provider_rows(
        [
            _row("lm_studio", "reachable"),
            _row("ollama", "unreachable"),
            _row("openai_compatible_local", "unsupported", endpoint="https://api.openai.com"),
        ]
    )

    for row in rows:
        assert row["model_readiness"] == "not_verified"
        assert row["display_status"].lower() != "ready"
