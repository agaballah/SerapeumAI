# -*- coding: utf-8 -*-
"""
Wave 1B-5: runtime platform read-model aggregate tests.
"""

from src.infra.services.runtime_consent import ConsentAction
from src.infra.services.runtime_model_catalog import ModelProfileClass
from src.infra.services.runtime_platform_read_model import (
    RuntimePlatformReadModelService,
    build_runtime_platform_read_model,
)
from src.infra.services.runtime_status_presenter import (
    SUMMARY_NO_PROVIDER_REACHABLE,
    SUMMARY_PROVIDER_REACHABLE_MODEL_NOT_VERIFIED,
)


NO_PROVIDER_SIDE_EFFECTS = {
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


class _DiscoveryService:
    def __init__(self, rows):
        self.rows = rows
        self.calls = 0

    def discover_providers(self):
        self.calls += 1
        return list(self.rows)


def _provider_row(name, status, *, endpoint="http://127.0.0.1:1234"):
    return {
        "provider_name": name,
        "provider_type": name,
        "endpoint": endpoint,
        "status": status,
        "reason": "probe_ok" if status == "reachable" else "disabled_in_config",
        "capabilities": ["local_runtime", "model_listing"],
        "side_effects": dict(NO_PROVIDER_SIDE_EFFECTS),
        "details": {},
        "available": status == "reachable",
    }


def test_read_model_combines_provider_status_recommendation_and_consent():
    discovery = _DiscoveryService(
        [
            _provider_row("lm_studio", "reachable"),
            _provider_row("ollama", "disabled", endpoint="http://127.0.0.1:11434"),
        ]
    )

    service = RuntimePlatformReadModelService(
        provider_discovery_service=discovery,
        gpu_info_provider=lambda: {
            "available": True,
            "vram_total_mb": 8192,
            "gpu_name": "NVIDIA RTX 4060 Laptop GPU",
        },
        ram_total_mb_provider=lambda: 16384,
    )

    out = service.build_read_model()

    assert discovery.calls == 1
    assert out["schema_version"] == 1
    assert out["runtime_status"]["summary_status"] == SUMMARY_PROVIDER_REACHABLE_MODEL_NOT_VERIFIED
    assert out["runtime_status"]["reachable_provider_count"] == 1
    assert len(out["provider_discovery"]) == 2
    assert out["model_recommendation"]["profile_class"] == ModelProfileClass.BALANCED.value
    assert out["model_recommendation"]["model_posture"] == "balanced_7b_quantized"
    assert ConsentAction.MODEL_DOWNLOAD.value in out["consent_requirements"]


def test_read_model_uses_provider_reachable_to_shape_recommendation_warnings():
    discovery = _DiscoveryService(
        [
            _provider_row("lm_studio", "disabled"),
            _provider_row("ollama", "disabled", endpoint="http://127.0.0.1:11434"),
        ]
    )

    out = build_runtime_platform_read_model(
        provider_discovery_service=discovery,
        gpu_info_provider=lambda: {
            "available": True,
            "vram_total_mb": 8192,
            "gpu_name": "NVIDIA RTX 4060 Laptop GPU",
        },
        ram_total_mb_provider=lambda: 16384,
    )

    assert out["runtime_status"]["summary_status"] == SUMMARY_NO_PROVIDER_REACHABLE
    assert out["runtime_status"]["reachable_provider_count"] == 0
    assert any(
        "No reachable local runtime provider" in warning
        for warning in out["model_recommendation"]["warnings"]
    )


def test_read_model_is_conservative_when_hardware_detection_fails():
    discovery = _DiscoveryService([_provider_row("lm_studio", "reachable")])

    def broken_gpu():
        raise RuntimeError("gpu failed")

    def broken_ram():
        raise RuntimeError("ram failed")

    out = build_runtime_platform_read_model(
        provider_discovery_service=discovery,
        gpu_info_provider=broken_gpu,
        ram_total_mb_provider=broken_ram,
    )

    assert out["model_recommendation"]["profile_class"] == ModelProfileClass.CONSERVATIVE.value
    assert out["model_recommendation"]["runtime_posture"] == "local_conservative"


def test_read_model_side_effects_remain_false_for_clean_inputs():
    discovery = _DiscoveryService([_provider_row("lm_studio", "reachable")])

    out = build_runtime_platform_read_model(
        provider_discovery_service=discovery,
        gpu_info_provider=lambda: {
            "available": True,
            "vram_total_mb": 8192,
            "gpu_name": "NVIDIA RTX 4060 Laptop GPU",
        },
        ram_total_mb_provider=lambda: 16384,
    )

    assert out["side_effects"] == {
        "provider_mutated": False,
        "model_download_attempted": False,
        "model_load_attempted": False,
        "model_unload_attempted": False,
        "runtime_install_attempted": False,
        "config_mutated": False,
        "project_data_sent": False,
        "persistence_written": False,
    }


def test_read_model_surfaces_provider_side_effect_violations():
    row = _provider_row("lm_studio", "reachable")
    row["side_effects"]["start_attempted"] = True
    row["side_effects"]["download_attempted"] = True

    out = build_runtime_platform_read_model(
        provider_discovery_service=_DiscoveryService([row]),
        gpu_info_provider=lambda: {
            "available": True,
            "vram_total_mb": 8192,
            "gpu_name": "NVIDIA RTX 4060 Laptop GPU",
        },
        ram_total_mb_provider=lambda: 16384,
    )

    assert out["side_effects"]["provider_mutated"] is True
    assert out["side_effects"]["model_download_attempted"] is True


def test_read_model_handles_discovery_service_failure_as_structured_status():
    class BrokenDiscovery:
        def discover_providers(self):
            raise RuntimeError("boom")

    out = build_runtime_platform_read_model(
        provider_discovery_service=BrokenDiscovery(),
        gpu_info_provider=lambda: {
            "available": False,
            "vram_total_mb": 0,
            "gpu_name": "No GPU",
        },
        ram_total_mb_provider=lambda: 8192,
    )

    assert out["provider_discovery"][0]["provider_name"] == "runtime_discovery"
    assert out["provider_discovery"][0]["status"] == "unreachable"
    assert out["provider_discovery"][0]["reason"].startswith("discovery_error:")
    assert out["runtime_status"]["reachable_provider_count"] == 0


def test_read_model_has_deterministic_provider_order_from_presenter():
    discovery = _DiscoveryService(
        [
            _provider_row("ollama", "disabled", endpoint="http://127.0.0.1:11434"),
            _provider_row("lm_studio", "reachable", endpoint="http://127.0.0.1:1234"),
        ]
    )

    out = build_runtime_platform_read_model(
        provider_discovery_service=discovery,
        gpu_info_provider=lambda: {
            "available": True,
            "vram_total_mb": 8192,
            "gpu_name": "NVIDIA RTX 4060 Laptop GPU",
        },
        ram_total_mb_provider=lambda: 16384,
    )

    provider_names = [row["provider_name"] for row in out["runtime_status"]["providers"]]
    assert provider_names == ["lm_studio", "ollama"]


def test_read_model_contains_recommendation_entries_but_no_download_execution():
    discovery = _DiscoveryService([_provider_row("lm_studio", "reachable")])

    out = build_runtime_platform_read_model(
        provider_discovery_service=discovery,
        gpu_info_provider=lambda: {
            "available": True,
            "vram_total_mb": 8192,
            "gpu_name": "NVIDIA RTX 4060 Laptop GPU",
        },
        ram_total_mb_provider=lambda: 16384,
    )

    entries = out["model_recommendation"]["recommended_entries"]
    assert entries
    assert any(entry["model_id"] == "balanced-7b-local-q4" for entry in entries)
    assert out["side_effects"]["model_download_attempted"] is False
    assert out["side_effects"]["model_load_attempted"] is False
