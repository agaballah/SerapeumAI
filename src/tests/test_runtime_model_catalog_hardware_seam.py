# -*- coding: utf-8 -*-
"""
Wave 1B-4B: hardware seam integration tests.
"""

from src.infra.services.runtime_model_catalog import (
    HardwareSnapshot,
    ModelProfileClass,
    detect_hardware_snapshot,
    hardware_snapshot_from_mapping,
    recommend_models_from_detected_hardware,
)


def test_hardware_snapshot_from_existing_gpu_info_mapping():
    snapshot = hardware_snapshot_from_mapping(
        {
            "available": True,
            "vram_total_mb": 8192,
            "gpu_name": "NVIDIA RTX 4060 Laptop GPU",
            "method": "pynvml",
        },
        ram_total_mb=16384,
    )

    assert snapshot == HardwareSnapshot(
        gpu_available=True,
        vram_total_mb=8192,
        ram_total_mb=16384,
        gpu_name="NVIDIA RTX 4060 Laptop GPU",
        os_name="",
    )


def test_detect_hardware_snapshot_uses_injected_read_only_providers():
    calls = {"gpu": 0, "ram": 0}

    def fake_gpu_info():
        calls["gpu"] += 1
        return {
            "available": True,
            "vram_total_mb": 8192,
            "gpu_name": "NVIDIA RTX 4060 Laptop GPU",
        }

    def fake_ram_total_mb():
        calls["ram"] += 1
        return 16384

    snapshot = detect_hardware_snapshot(
        gpu_info_provider=fake_gpu_info,
        ram_total_mb_provider=fake_ram_total_mb,
    )

    assert calls == {"gpu": 1, "ram": 1}
    assert snapshot.gpu_available is True
    assert snapshot.vram_total_mb == 8192
    assert snapshot.ram_total_mb == 16384


def test_detect_hardware_snapshot_degrades_safely_when_detection_fails():
    def broken_gpu_info():
        raise RuntimeError("hardware detection failed")

    def broken_ram_total_mb():
        raise RuntimeError("ram detection failed")

    snapshot = detect_hardware_snapshot(
        gpu_info_provider=broken_gpu_info,
        ram_total_mb_provider=broken_ram_total_mb,
    )

    assert snapshot.gpu_available is False
    assert snapshot.vram_total_mb == 0
    assert snapshot.ram_total_mb == 0


def test_recommend_models_from_detected_hardware_maps_4060_laptop_to_balanced():
    recommendation = recommend_models_from_detected_hardware(
        provider_reachable=True,
        gpu_info_provider=lambda: {
            "available": True,
            "vram_total_mb": 8192,
            "gpu_name": "NVIDIA RTX 4060 Laptop GPU",
        },
        ram_total_mb_provider=lambda: 16384,
    )

    row = recommendation.to_dict()

    assert row["profile_class"] == ModelProfileClass.BALANCED.value
    assert row["runtime_posture"] == "local_balanced"
    assert row["model_posture"] == "balanced_7b_quantized"
    assert any(entry["model_id"] == "balanced-7b-local-q4" for entry in row["recommended_entries"])


def test_recommend_models_from_detected_hardware_no_gpu_is_conservative():
    recommendation = recommend_models_from_detected_hardware(
        provider_reachable=False,
        gpu_info_provider=lambda: {
            "available": False,
            "vram_total_mb": 0,
            "gpu_name": "No GPU",
        },
        ram_total_mb_provider=lambda: 32768,
    )

    row = recommendation.to_dict()

    assert row["profile_class"] == ModelProfileClass.CONSERVATIVE.value
    assert row["runtime_posture"] == "local_conservative"
    assert any("No reachable local runtime provider" in warning for warning in row["warnings"])


def test_hardware_seam_recommendation_has_no_runtime_side_effects():
    recommendation = recommend_models_from_detected_hardware(
        provider_reachable=False,
        gpu_info_provider=lambda: {
            "available": True,
            "vram_total_mb": 8192,
            "gpu_name": "NVIDIA RTX 4060 Laptop GPU",
        },
        ram_total_mb_provider=lambda: 16384,
    )

    assert recommendation.to_dict()["side_effects"] == {
        "internet_used": False,
        "download_attempted": False,
        "model_load_attempted": False,
        "runtime_install_attempted": False,
        "provider_mutated": False,
        "project_data_sent": False,
    }
