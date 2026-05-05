# -*- coding: utf-8 -*-
"""
Upgrade 3S-2: runtime provider/model selection persistence tests.
"""

import pytest

from src.infra.services.runtime_platform_read_model import build_runtime_platform_read_model
from src.infra.services.runtime_provider_discovery import (
    PROVIDER_MODE_DISABLED_LOCAL_REVIEW_ONLY,
    PROVIDER_MODE_LM_STUDIO_CLI_MANAGED,
    PROVIDER_MODE_LM_STUDIO_MANUAL_OPENAI_COMPAT,
    PROVIDER_MODE_OLLAMA_LOCAL,
)
from src.infra.services.runtime_provider_selection import (
    PROVIDER_LOCAL_REVIEW_ONLY,
    PROVIDER_LM_STUDIO,
    PROVIDER_OLLAMA,
    RuntimeProviderSelectionService,
    save_runtime_provider_selection,
    supported_provider_modes,
    validate_provider_mode,
)


class _Config:
    def __init__(self):
        self.values = {}
        self.set_calls = []
        self.save_calls = []

    def get(self, key, default=None):
        return self.values.get(key, default)

    def set(self, key, value, *, scope="local"):
        self.set_calls.append((key, value, scope))
        self.values[key] = value

    def save(self, *, scope="local"):
        self.save_calls.append(scope)
        return f"/fake/{scope}/config.yaml"


class _DiscoveryService:
    def __init__(self, rows):
        self.rows = rows

    def discover_providers(self):
        return list(self.rows)


def _provider_row(name, status, *, mode, models=None, endpoint="http://127.0.0.1:1234"):
    return {
        "provider_name": name,
        "provider_type": name,
        "endpoint": endpoint,
        "status": status,
        "reason": "probe_ok" if status == "reachable" else "disabled_in_config",
        "capabilities": ["local_runtime", "model_listing"],
        "side_effects": {
            "internet_used": False,
            "install_attempted": False,
            "start_attempted": False,
            "stop_attempted": False,
            "download_attempted": False,
            "model_load_attempted": False,
            "model_unload_attempted": False,
            "config_mutated": False,
            "project_data_sent": False,
        },
        "available": status == "reachable",
        "details": {"provider_mode": mode},
        "provider_mode": mode,
        "provider_modes_supported": [mode],
        "listed_models": list(models or []),
    }


def test_supported_provider_modes_are_explicit():
    assert supported_provider_modes("local_review_only") == [PROVIDER_MODE_DISABLED_LOCAL_REVIEW_ONLY]
    assert supported_provider_modes("ollama") == [PROVIDER_MODE_OLLAMA_LOCAL]
    assert PROVIDER_MODE_LM_STUDIO_MANUAL_OPENAI_COMPAT in supported_provider_modes("lm_studio")
    assert PROVIDER_MODE_LM_STUDIO_CLI_MANAGED in supported_provider_modes("lm_studio")


def test_invalid_provider_mode_pair_is_rejected():
    with pytest.raises(ValueError, match="Unsupported provider mode"):
        validate_provider_mode("ollama", PROVIDER_MODE_LM_STUDIO_MANUAL_OPENAI_COMPAT)

    with pytest.raises(ValueError, match="Unsupported runtime provider"):
        validate_provider_mode("cloud_vendor", "CLOUD")


def test_local_review_only_can_be_saved_without_models():
    config = _Config()

    result = RuntimeProviderSelectionService(config).save_selection(
        provider="local_review_only",
        provider_mode=PROVIDER_MODE_DISABLED_LOCAL_REVIEW_ONLY,
    ).to_dict()

    assert result["ok"] is True
    assert result["selected_provider"] == PROVIDER_LOCAL_REVIEW_ONLY
    assert result["selected_provider_mode"] == PROVIDER_MODE_DISABLED_LOCAL_REVIEW_ONLY
    assert result["selected_chat_model"] == ""
    assert result["selected_analysis_model"] == ""
    assert result["side_effects"]["config_mutated"] is True
    assert result["side_effects"]["download_attempted"] is False
    assert result["side_effects"]["model_load_attempted"] is False
    assert config.values["runtime.selected_provider"] == PROVIDER_LOCAL_REVIEW_ONLY
    assert config.save_calls == ["local"]


def test_lm_studio_manual_provider_and_models_persist():
    config = _Config()

    result = save_runtime_provider_selection(
        config=config,
        provider="lm_studio",
        provider_mode=PROVIDER_MODE_LM_STUDIO_MANUAL_OPENAI_COMPAT,
        chat_model="qwen2.5-coder-7b-instruct",
        analysis_model="qwen2.5-coder-7b-instruct",
    )

    assert result["selected_provider"] == PROVIDER_LM_STUDIO
    assert result["selected_provider_mode"] == PROVIDER_MODE_LM_STUDIO_MANUAL_OPENAI_COMPAT
    assert config.values["runtime.selected_chat_model"] == "qwen2.5-coder-7b-instruct"
    assert config.values["models.chat.model"] == "qwen2.5-coder-7b-instruct"
    assert config.values["models.chat.backend"] == PROVIDER_LM_STUDIO
    assert result["side_effects"] == {
        "internet_used": False,
        "install_attempted": False,
        "start_attempted": False,
        "stop_attempted": False,
        "download_attempted": False,
        "model_load_attempted": False,
        "model_unload_attempted": False,
        "provider_mutated": False,
        "runtime_install_attempted": False,
        "project_data_sent": False,
        "config_mutated": True,
    }


def test_lm_studio_cli_mode_persists_separately_from_manual_mode():
    config = _Config()

    result = save_runtime_provider_selection(
        config=config,
        provider="lm_studio",
        provider_mode=PROVIDER_MODE_LM_STUDIO_CLI_MANAGED,
        chat_model="qwen2.5-coder-7b-instruct",
        analysis_model="qwen2.5-coder-7b-instruct",
    )

    assert result["selected_provider"] == PROVIDER_LM_STUDIO
    assert result["selected_provider_mode"] == PROVIDER_MODE_LM_STUDIO_CLI_MANAGED
    assert config.values["runtime.selected_provider_mode"] == PROVIDER_MODE_LM_STUDIO_CLI_MANAGED


def test_ollama_provider_and_model_selection_persist():
    config = _Config()

    result = save_runtime_provider_selection(
        config=config,
        provider="ollama",
        provider_mode=PROVIDER_MODE_OLLAMA_LOCAL,
        chat_model="llama3.1:8b",
        analysis_model="llama3.1:8b",
    )

    assert result["selected_provider"] == PROVIDER_OLLAMA
    assert result["selected_provider_mode"] == PROVIDER_MODE_OLLAMA_LOCAL
    assert config.values["models.analysis.backend"] == PROVIDER_OLLAMA
    assert config.values["models.analysis.model"] == "llama3.1:8b"


def test_model_backed_provider_requires_chat_and_analysis_models():
    config = _Config()

    with pytest.raises(ValueError, match="Chat and analysis model selections are required"):
        save_runtime_provider_selection(
            config=config,
            provider="ollama",
            provider_mode=PROVIDER_MODE_OLLAMA_LOCAL,
            chat_model="llama3.1:8b",
            analysis_model="",
        )


def test_saved_selection_is_visible_through_runtime_platform_read_model():
    config = _Config()
    save_runtime_provider_selection(
        config=config,
        provider="ollama",
        provider_mode=PROVIDER_MODE_OLLAMA_LOCAL,
        chat_model="llama3.1:8b",
        analysis_model="llama3.1:8b",
    )

    out = build_runtime_platform_read_model(
        config=config,
        provider_discovery_service=_DiscoveryService(
            [
                _provider_row(
                    "ollama",
                    "reachable",
                    mode=PROVIDER_MODE_OLLAMA_LOCAL,
                    endpoint="http://127.0.0.1:11434",
                    models=[{"model_id": "llama3.1:8b"}],
                )
            ]
        ),
        gpu_info_provider=lambda: {"available": True, "vram_total_mb": 8192, "gpu_name": "GPU"},
        ram_total_mb_provider=lambda: 16384,
    )

    assert out["selected_provider"] == "ollama"
    assert out["selected_provider_mode"] == PROVIDER_MODE_OLLAMA_LOCAL
    assert out["selected_chat_model"] == "llama3.1:8b"
    assert out["selected_analysis_model"] == "llama3.1:8b"
    assert out["available_models"][0]["model_id"] == "llama3.1:8b"
    assert out["model_selection_ready"] is True
    assert out["model_readiness"] == "not_verified"


def test_saving_selection_does_not_create_fake_ready_state():
    config = _Config()
    save_runtime_provider_selection(
        config=config,
        provider="ollama",
        provider_mode=PROVIDER_MODE_OLLAMA_LOCAL,
        chat_model="llama3.1:8b",
        analysis_model="llama3.1:8b",
    )

    out = build_runtime_platform_read_model(
        config=config,
        provider_discovery_service=_DiscoveryService(
            [
                _provider_row(
                    "ollama",
                    "reachable",
                    mode=PROVIDER_MODE_OLLAMA_LOCAL,
                    endpoint="http://127.0.0.1:11434",
                    models=[{"model_id": "llama3.1:8b"}],
                )
            ]
        ),
        gpu_info_provider=lambda: {"available": True, "vram_total_mb": 8192, "gpu_name": "GPU"},
        ram_total_mb_provider=lambda: 16384,
    )

    assert out["runtime_status"]["summary_status"] == "provider_reachable_model_not_verified"
    assert out["model_readiness"] == "not_verified"
    for row in out["runtime_status"]["providers"]:
        assert row["display_status"].lower() != "ready"
