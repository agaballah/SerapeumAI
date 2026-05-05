# -*- coding: utf-8 -*-
"""
Upgrade 3S-3A: Runtime Manager presenter tests.
"""

from src.infra.services.runtime_provider_discovery import (
    PROVIDER_MODE_DISABLED_LOCAL_REVIEW_ONLY,
    PROVIDER_MODE_LM_STUDIO_CLI_MANAGED,
    PROVIDER_MODE_LM_STUDIO_MANUAL_OPENAI_COMPAT,
    PROVIDER_MODE_OLLAMA_LOCAL,
)
from src.ui.presenters.runtime_manager_presenter import present_runtime_manager_selection


def _provider(name, status, mode, *, models=None):
    return {
        "provider_name": name,
        "status": status,
        "display_status": status.title(),
        "provider_mode": mode,
        "provider_mode_label": mode.replace("_", " ").title(),
        "provider_modes_supported": [mode],
        "listed_models": list(models or []),
    }


def test_presenter_outputs_provider_mode_and_model_choices():
    out = present_runtime_manager_selection(
        {
            "selected_provider": "ollama",
            "selected_provider_mode": PROVIDER_MODE_OLLAMA_LOCAL,
            "selected_chat_model": "llama3.1:8b",
            "selected_analysis_model": "llama3.1:8b",
            "available_models": [{"model_id": "llama3.1:8b"}],
            "model_selection_ready": True,
            "model_readiness": "not_verified",
            "runtime_status": {
                "providers": [
                    _provider("local_review_only", "disabled", PROVIDER_MODE_DISABLED_LOCAL_REVIEW_ONLY),
                    _provider("lm_studio", "reachable", PROVIDER_MODE_LM_STUDIO_MANUAL_OPENAI_COMPAT),
                    _provider("ollama", "reachable", PROVIDER_MODE_OLLAMA_LOCAL, models=[{"model_id": "llama3.1:8b"}]),
                ]
            },
            "model_recommendation": {
                "profile_class": "balanced",
                "model_posture": "balanced_7b_quantized",
            },
        }
    )

    assert out["provider_values"] == ["local_review_only", "lm_studio", "ollama"]
    assert out["selected_provider"] == "ollama"
    assert out["provider_mode_values"] == [PROVIDER_MODE_OLLAMA_LOCAL]
    assert out["selected_provider_mode"] == PROVIDER_MODE_OLLAMA_LOCAL
    assert out["model_values"] == ["llama3.1:8b"]
    assert out["selected_chat_model"] == "llama3.1:8b"
    assert out["selected_analysis_model"] == "llama3.1:8b"
    assert out["model_selection_ready"] is True
    assert out["model_readiness"] == "not_verified"
    assert "Balanced profile" in out["recommendation_summary"]


def test_presenter_keeps_lm_studio_cli_mode_as_choice_when_selected():
    out = present_runtime_manager_selection(
        {
            "selected_provider": "lm_studio",
            "selected_provider_mode": PROVIDER_MODE_LM_STUDIO_CLI_MANAGED,
            "selected_chat_model": "qwen2.5-coder-7b-instruct",
            "selected_analysis_model": "qwen2.5-coder-7b-instruct",
            "available_models": [],
            "runtime_status": {
                "providers": [
                    {
                        **_provider("lm_studio", "reachable", PROVIDER_MODE_LM_STUDIO_MANUAL_OPENAI_COMPAT),
                        "provider_modes_supported": [
                            PROVIDER_MODE_LM_STUDIO_MANUAL_OPENAI_COMPAT,
                            PROVIDER_MODE_LM_STUDIO_CLI_MANAGED,
                        ],
                    }
                ]
            },
            "model_recommendation": {"profile_class": "balanced", "model_posture": "balanced_7b_quantized"},
        }
    )

    assert out["selected_provider"] == "lm_studio"
    assert PROVIDER_MODE_LM_STUDIO_CLI_MANAGED in out["provider_mode_values"]
    assert out["selected_provider_mode"] == PROVIDER_MODE_LM_STUDIO_CLI_MANAGED
    assert out["model_values"] == ["qwen2.5-coder-7b-instruct"]


def test_presenter_handles_no_models_without_fake_ready():
    out = present_runtime_manager_selection(
        {
            "selected_provider": "local_review_only",
            "selected_provider_mode": PROVIDER_MODE_DISABLED_LOCAL_REVIEW_ONLY,
            "runtime_status": {"providers": [_provider("local_review_only", "disabled", PROVIDER_MODE_DISABLED_LOCAL_REVIEW_ONLY)]},
            "model_recommendation": {"profile_class": "conservative", "model_posture": "small_low_vram_models"},
        }
    )

    assert out["selected_provider"] == "local_review_only"
    assert out["model_values"] == ["No local models listed"]
    assert out["selected_chat_model"] == "No local models listed"
    assert out["selected_analysis_model"] == "No local models listed"
    assert out["model_selection_ready"] is False
    assert out["model_readiness"] == "not_verified"
    assert out["side_effects"]["config_mutated"] is False
