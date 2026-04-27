# -*- coding: utf-8 -*-
"""
Wave 1B-6: Runtime Platform UI presenter tests.
"""

from src.ui.presenters.runtime_platform_presenter import present_runtime_platform_sidebar


def test_sidebar_presenter_shows_reachable_without_ready_overclaim():
    out = present_runtime_platform_sidebar(
        {
            "runtime_status": {
                "summary_status": "provider_reachable_model_not_verified",
                "provider_count": 2,
                "reachable_provider_count": 1,
            },
            "model_recommendation": {
                "profile_class": "balanced",
                "model_posture": "balanced_7b_quantized",
            },
        }
    )

    assert out["tone"] == "warning"
    assert out["primary"] == "Runtime: provider reachable - model not verified"
    assert "1/2 reachable" in out["secondary"]
    assert "Balanced profile" in out["secondary"]
    assert "model/task readiness has not been proven" in out["detail"]
    assert "ready" not in out["primary"].lower()


def test_sidebar_presenter_handles_no_provider_reachable():
    out = present_runtime_platform_sidebar(
        {
            "runtime_status": {
                "summary_status": "no_provider_reachable",
                "provider_count": 2,
                "reachable_provider_count": 0,
            },
            "model_recommendation": {
                "profile_class": "balanced",
                "model_posture": "balanced_7b_quantized",
            },
        }
    )

    assert out["tone"] == "warning"
    assert out["primary"] == "Runtime: no local provider reachable"
    assert "0/2 reachable" in out["secondary"]
    assert "AI features may remain unavailable" in out["detail"]


def test_sidebar_presenter_handles_discovery_unavailable():
    out = present_runtime_platform_sidebar(
        {
            "runtime_status": {
                "summary_status": "provider_discovery_unavailable",
                "provider_count": 0,
                "reachable_provider_count": 0,
            },
            "model_recommendation": {
                "profile_class": "conservative",
                "model_posture": "small_low_vram_models",
            },
        }
    )

    assert out["tone"] == "error"
    assert out["primary"] == "Runtime: discovery unavailable"
    assert "Conservative profile" in out["secondary"]


def test_sidebar_presenter_handles_empty_input_safely():
    out = present_runtime_platform_sidebar({})

    assert out["tone"] == "muted"
    assert out["primary"] == "Runtime: status unavailable"
    assert "0/0 reachable" in out["secondary"]
