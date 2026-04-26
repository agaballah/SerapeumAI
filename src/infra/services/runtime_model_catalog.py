# -*- coding: utf-8 -*-
"""
Runtime model catalog and hardware recommendation skeleton.

Wave 1B-4 rules:
- recommendation only
- no model download
- no provider model load/unload
- no runtime install
- no internet use
- no UI
- no persistence
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Callable, Dict, Iterable, List, Optional

from src.infra.services.runtime_consent import ConsentAction


class ModelRole(str, Enum):
    ROUTER = "router"
    NARRATOR = "narrator"
    STRUCTURED_JSON = "structured_json"
    EVIDENCE_COMPRESSOR = "evidence_compressor"
    VISION_HELPER = "vision_helper"
    EMBEDDING = "embedding"
    RERANKER = "reranker"


class ModelProfileClass(str, Enum):
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    PERFORMANCE = "performance"


class ModelFormat(str, Enum):
    GGUF = "gguf"
    ONNX = "onnx"
    PROVIDER_MANAGED = "provider_managed"


class ModelSizeClass(str, Enum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


@dataclass(frozen=True)
class HardwareSnapshot:
    gpu_available: bool
    vram_total_mb: int
    ram_total_mb: int
    gpu_name: str = ""
    os_name: str = ""

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ModelCatalogEntry:
    model_id: str
    display_name: str
    role: ModelRole
    profile_class: ModelProfileClass
    format: ModelFormat
    quantization: str
    estimated_size_class: ModelSizeClass
    source_label: str
    consent_actions_required: List[ConsentAction]
    notes: str = ""

    def to_dict(self) -> Dict[str, object]:
        data = asdict(self)
        data["role"] = self.role.value
        data["profile_class"] = self.profile_class.value
        data["format"] = self.format.value
        data["estimated_size_class"] = self.estimated_size_class.value
        data["consent_actions_required"] = [action.value for action in self.consent_actions_required]
        return data


@dataclass(frozen=True)
class ModelRecommendation:
    profile_class: ModelProfileClass
    runtime_posture: str
    model_posture: str
    recommended_entries: List[ModelCatalogEntry]
    warnings: List[str]
    constraints: List[str]
    side_effects: Dict[str, bool]

    def to_dict(self) -> Dict[str, object]:
        return {
            "profile_class": self.profile_class.value,
            "runtime_posture": self.runtime_posture,
            "model_posture": self.model_posture,
            "recommended_entries": [entry.to_dict() for entry in self.recommended_entries],
            "warnings": list(self.warnings),
            "constraints": list(self.constraints),
            "side_effects": dict(self.side_effects),
        }


def _no_side_effects() -> Dict[str, bool]:
    return {
        "internet_used": False,
        "download_attempted": False,
        "model_load_attempted": False,
        "runtime_install_attempted": False,
        "provider_mutated": False,
        "project_data_sent": False,
    }


def classify_hardware(snapshot: HardwareSnapshot) -> ModelProfileClass:
    if (not snapshot.gpu_available) or snapshot.vram_total_mb < 4096 or snapshot.ram_total_mb < 16000:
        return ModelProfileClass.CONSERVATIVE
    if snapshot.vram_total_mb >= 12288 and snapshot.ram_total_mb >= 32000:
        return ModelProfileClass.PERFORMANCE
    return ModelProfileClass.BALANCED


def baseline_model_catalog() -> List[ModelCatalogEntry]:
    consent_for_optional_model = [ConsentAction.INTERNET_USE, ConsentAction.MODEL_DOWNLOAD]

    return [
        ModelCatalogEntry(
            model_id="safe-small-local-q4",
            display_name="Safe Small Local Q4",
            role=ModelRole.NARRATOR,
            profile_class=ModelProfileClass.CONSERVATIVE,
            format=ModelFormat.GGUF,
            quantization="Q4_K_M",
            estimated_size_class=ModelSizeClass.SMALL,
            source_label="user-selected local model source",
            consent_actions_required=consent_for_optional_model,
            notes="Conservative low-resource text model posture.",
        ),
        ModelCatalogEntry(
            model_id="balanced-7b-local-q4",
            display_name="Balanced 7B Local Q4",
            role=ModelRole.NARRATOR,
            profile_class=ModelProfileClass.BALANCED,
            format=ModelFormat.GGUF,
            quantization="Q4_K_M",
            estimated_size_class=ModelSizeClass.MEDIUM,
            source_label="user-selected local model source",
            consent_actions_required=consent_for_optional_model,
            notes="Balanced 7B quantized text model posture for common 6-8 GB VRAM laptops.",
        ),
        ModelCatalogEntry(
            model_id="balanced-structured-json-q5",
            display_name="Balanced Structured JSON Q5",
            role=ModelRole.STRUCTURED_JSON,
            profile_class=ModelProfileClass.BALANCED,
            format=ModelFormat.GGUF,
            quantization="Q5_K_M",
            estimated_size_class=ModelSizeClass.MEDIUM,
            source_label="user-selected local model source",
            consent_actions_required=consent_for_optional_model,
            notes="Structured output helper posture for fact/tool JSON tasks.",
        ),
        ModelCatalogEntry(
            model_id="performance-14b-local-q4",
            display_name="Performance 14B Local Q4",
            role=ModelRole.NARRATOR,
            profile_class=ModelProfileClass.PERFORMANCE,
            format=ModelFormat.GGUF,
            quantization="Q4_K_M",
            estimated_size_class=ModelSizeClass.LARGE,
            source_label="user-selected local model source",
            consent_actions_required=consent_for_optional_model,
            notes="Higher-quality local model posture for high VRAM/RAM machines.",
        ),
        ModelCatalogEntry(
            model_id="local-embedding-small",
            display_name="Small Local Embedding Model",
            role=ModelRole.EMBEDDING,
            profile_class=ModelProfileClass.CONSERVATIVE,
            format=ModelFormat.ONNX,
            quantization="INT8-or-small-fp",
            estimated_size_class=ModelSizeClass.SMALL,
            source_label="bundled-or-user-selected local embedding source",
            consent_actions_required=[],
            notes="Embedding posture remains derived retrieval support only.",
        ),
    ]


def catalog_for_profile(profile_class: ModelProfileClass, catalog: Optional[Iterable[ModelCatalogEntry]] = None) -> List[ModelCatalogEntry]:
    rows = list(catalog or baseline_model_catalog())
    allowed_profiles = {ModelProfileClass.CONSERVATIVE}

    if profile_class == ModelProfileClass.BALANCED:
        allowed_profiles.add(ModelProfileClass.BALANCED)
    elif profile_class == ModelProfileClass.PERFORMANCE:
        allowed_profiles.update({ModelProfileClass.BALANCED, ModelProfileClass.PERFORMANCE})

    return [entry for entry in rows if entry.profile_class in allowed_profiles]


def recommend_models_for_hardware(
    snapshot: HardwareSnapshot,
    *,
    provider_reachable: bool = False,
    catalog: Optional[Iterable[ModelCatalogEntry]] = None,
) -> ModelRecommendation:
    profile = classify_hardware(snapshot)
    entries = catalog_for_profile(profile, catalog)

    warnings: List[str] = []
    constraints: List[str] = []

    if not provider_reachable:
        warnings.append("No reachable local runtime provider detected; recommendations are advisory only.")
        constraints.append("A provider must be configured/reachable before model use.")

    if profile == ModelProfileClass.CONSERVATIVE:
        runtime_posture = "local_conservative"
        model_posture = "small_low_vram_models"
        warnings.append("Conservative profile selected; avoid vision-heavy or large-context models.")
    elif profile == ModelProfileClass.BALANCED:
        runtime_posture = "local_balanced"
        model_posture = "balanced_7b_quantized"
    else:
        runtime_posture = "local_high_throughput"
        model_posture = "high_quality_7b_to_14b_quantized"

    constraints.append("Recommendations never download, install, or load models automatically.")

    return ModelRecommendation(
        profile_class=profile,
        runtime_posture=runtime_posture,
        model_posture=model_posture,
        recommended_entries=entries,
        warnings=warnings,
        constraints=constraints,
        side_effects=_no_side_effects(),
    )

def hardware_snapshot_from_mapping(data: Dict[str, Any], *, ram_total_mb: int = 0) -> HardwareSnapshot:
    """
    Convert existing hardware utility output into the model-catalog HardwareSnapshot.

    Expected GPU keys are compatible with src.utils.hardware_utils.get_gpu_info():
    - available
    - vram_total_mb
    - gpu_name

    RAM is supplied separately so tests and future platform-specific collectors can
    inject it without depending on host hardware.
    """
    data = data or {}
    return HardwareSnapshot(
        gpu_available=bool(data.get("available", data.get("gpu_available", False))),
        vram_total_mb=int(data.get("vram_total_mb", 0) or 0),
        ram_total_mb=int(ram_total_mb or data.get("ram_total_mb", 0) or 0),
        gpu_name=str(data.get("gpu_name", "") or ""),
        os_name=str(data.get("os_name", "") or ""),
    )


def detect_hardware_snapshot(
    *,
    gpu_info_provider: Optional[Callable[[], Dict[str, Any]]] = None,
    ram_total_mb_provider: Optional[Callable[[], int]] = None,
) -> HardwareSnapshot:
    """
    Read-only hardware snapshot adapter.

    This function does not benchmark, load models, start providers, download, or
    mutate config. It only adapts the existing hardware detection seam into the
    recommendation skeleton's HardwareSnapshot shape.
    """
    try:
        if gpu_info_provider is None:
            from src.utils.hardware_utils import get_gpu_info
            gpu_info_provider = get_gpu_info

        gpu_info = gpu_info_provider() or {}
    except Exception:
        gpu_info = {}

    try:
        ram_total_mb = int(ram_total_mb_provider() if ram_total_mb_provider else 0)
    except Exception:
        ram_total_mb = 0

    return hardware_snapshot_from_mapping(gpu_info, ram_total_mb=ram_total_mb)


def recommend_models_from_detected_hardware(
    *,
    provider_reachable: bool = False,
    gpu_info_provider: Optional[Callable[[], Dict[str, Any]]] = None,
    ram_total_mb_provider: Optional[Callable[[], int]] = None,
    catalog: Optional[Iterable[ModelCatalogEntry]] = None,
) -> ModelRecommendation:
    """
    Convenience wrapper for model recommendation using the read-only hardware seam.

    Side-effect rule:
    - detects hardware only,
    - returns advisory recommendations,
    - does not download/install/load/start anything.
    """
    snapshot = detect_hardware_snapshot(
        gpu_info_provider=gpu_info_provider,
        ram_total_mb_provider=ram_total_mb_provider,
    )
    return recommend_models_for_hardware(
        snapshot,
        provider_reachable=provider_reachable,
        catalog=catalog,
    )

