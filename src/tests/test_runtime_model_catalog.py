# -*- coding: utf-8 -*-
"""
Wave 1B-4: model catalog and hardware recommendation skeleton tests.
"""

from src.infra.services.runtime_consent import ConsentAction
from src.infra.services.runtime_model_catalog import (
    HardwareSnapshot,
    ModelFormat,
    ModelProfileClass,
    ModelRole,
    classify_hardware,
    baseline_model_catalog,
    catalog_for_profile,
    recommend_models_for_hardware,
)


def test_8gb_vram_16gb_ram_maps_to_balanced_profile():
    snapshot = HardwareSnapshot(
        gpu_available=True,
        gpu_name="NVIDIA RTX 4060 Laptop GPU",
        vram_total_mb=8192,
        ram_total_mb=16384,
        os_name="nt",
    )

    assert classify_hardware(snapshot) == ModelProfileClass.BALANCED


def test_no_gpu_maps_to_conservative_profile():
    snapshot = HardwareSnapshot(
        gpu_available=False,
        vram_total_mb=0,
        ram_total_mb=32768,
    )

    assert classify_hardware(snapshot) == ModelProfileClass.CONSERVATIVE


def test_high_vram_high_ram_maps_to_performance_profile():
    snapshot = HardwareSnapshot(
        gpu_available=True,
        vram_total_mb=16384,
        ram_total_mb=65536,
    )

    assert classify_hardware(snapshot) == ModelProfileClass.PERFORMANCE


def test_every_catalog_entry_has_required_metadata_and_consent_shape():
    for entry in baseline_model_catalog():
        row = entry.to_dict()

        assert row["model_id"]
        assert row["display_name"]
        assert row["role"] in {role.value for role in ModelRole}
        assert row["profile_class"] in {profile.value for profile in ModelProfileClass}
        assert row["format"] in {fmt.value for fmt in ModelFormat}
        assert row["quantization"]
        assert row["estimated_size_class"]
        assert "source_label" in row
        assert "consent_actions_required" in row


def test_optional_downloadable_models_require_internet_and_model_download_consent():
    downloadable = [
        entry
        for entry in baseline_model_catalog()
        if ConsentAction.MODEL_DOWNLOAD in entry.consent_actions_required
    ]

    assert downloadable
    for entry in downloadable:
        assert ConsentAction.INTERNET_USE in entry.consent_actions_required
        assert ConsentAction.MODEL_DOWNLOAD in entry.consent_actions_required


def test_embedding_entry_has_no_download_consent_requirement_in_skeleton():
    embeddings = [entry for entry in baseline_model_catalog() if entry.role == ModelRole.EMBEDDING]

    assert embeddings
    for entry in embeddings:
        assert ConsentAction.MODEL_DOWNLOAD not in entry.consent_actions_required


def test_balanced_catalog_includes_balanced_7b_quantized_guidance():
    entries = catalog_for_profile(ModelProfileClass.BALANCED)
    ids = {entry.model_id for entry in entries}

    assert "balanced-7b-local-q4" in ids
    assert "balanced-structured-json-q5" in ids
    assert "performance-14b-local-q4" not in ids


def test_recommendation_for_8gb_vram_16gb_ram_is_balanced_7b_posture():
    rec = recommend_models_for_hardware(
        HardwareSnapshot(
            gpu_available=True,
            gpu_name="NVIDIA RTX 4060 Laptop GPU",
            vram_total_mb=8192,
            ram_total_mb=16384,
            os_name="nt",
        ),
        provider_reachable=True,
    )

    row = rec.to_dict()

    assert row["profile_class"] == ModelProfileClass.BALANCED.value
    assert row["runtime_posture"] == "local_balanced"
    assert row["model_posture"] == "balanced_7b_quantized"
    assert any(entry["model_id"] == "balanced-7b-local-q4" for entry in row["recommended_entries"])


def test_conservative_recommendation_warns_against_heavy_models():
    rec = recommend_models_for_hardware(
        HardwareSnapshot(gpu_available=False, vram_total_mb=0, ram_total_mb=8192),
        provider_reachable=False,
    )

    row = rec.to_dict()

    assert row["profile_class"] == ModelProfileClass.CONSERVATIVE.value
    assert row["runtime_posture"] == "local_conservative"
    assert row["model_posture"] == "small_low_vram_models"
    assert any("avoid vision-heavy" in warning for warning in row["warnings"])


def test_performance_recommendation_includes_performance_entry():
    rec = recommend_models_for_hardware(
        HardwareSnapshot(gpu_available=True, vram_total_mb=24576, ram_total_mb=65536),
        provider_reachable=True,
    )

    ids = {entry["model_id"] for entry in rec.to_dict()["recommended_entries"]}

    assert "performance-14b-local-q4" in ids


def test_recommendation_has_no_runtime_side_effects():
    rec = recommend_models_for_hardware(
        HardwareSnapshot(gpu_available=True, vram_total_mb=8192, ram_total_mb=16384),
        provider_reachable=False,
    )

    assert rec.to_dict()["side_effects"] == {
        "internet_used": False,
        "download_attempted": False,
        "model_load_attempted": False,
        "runtime_install_attempted": False,
        "provider_mutated": False,
        "project_data_sent": False,
    }


def test_recommendation_discloses_provider_missing_constraint():
    rec = recommend_models_for_hardware(
        HardwareSnapshot(gpu_available=True, vram_total_mb=8192, ram_total_mb=16384),
        provider_reachable=False,
    )

    row = rec.to_dict()

    assert any("No reachable local runtime provider" in warning for warning in row["warnings"])
    assert any("provider must be configured" in constraint.lower() for constraint in row["constraints"])
