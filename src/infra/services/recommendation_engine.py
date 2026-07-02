# -*- coding: utf-8 -*-
"""
Recommendation Engine - Recommends models for specific roles based on hardware profile.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Dict, Any, Iterable, Tuple

from src.infra.services.runtime_model_catalog import (
    ModelCatalogEntry,
    ModelRole,
    ModelProfileClass,
    ModelFormat,
    ModelSizeClass,
    HardwareSnapshot,
    classify_hardware,
    catalog_for_profile,
    baseline_model_catalog,
)
from src.infra.services.provider_registry import ProviderType, ProviderRegistry
from src.infra.services.provider_adapters import get_adapter_for_provider
from src.infra.persistence.database_manager import DatabaseManager
from src.infra.config.configuration_manager import get_config

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """
    Recommends models for specific roles (router, narrator, etc.) based on hardware profile
    and provider availability.
    """

    def __init__(
        self,
        db: Optional[DatabaseManager] = None,
        provider_registry: Optional[ProviderRegistry] = None,
        model_catalog: Optional[List[ModelCatalogEntry]] = None,
    ):
        self.db = db
        self.provider_registry = provider_registry or ProviderRegistry()
        self.model_catalog = model_catalog or baseline_model_catalog()
        self._logger = logger

        # Optionally register known providers
        self._register_default_providers()

    def _register_default_providers(self) -> None:
        """Register known provider adapters (LM Studio, etc.) if they are available."""
        try:
            lm_studio_adapter = get_adapter_for_provider(
                ProviderType.LM_STUDIO, db=self.db
            )
            if lm_studio_adapter and lm_studio_adapter.is_available():
                self.provider_registry.register_provider(
                    ProviderType.LM_STUDIO, lm_studio_adapter
                )
                self._logger.info(
                    "[RecommendationEngine] Registered LM Studio provider adapter."
                )
        except Exception as e:
            self._logger.debug(
                f"[RecommendationEngine] Failed to register LM Studio adapter: {e}"
            )

        # TODO: Register Ollama, LlamaCpp, etc.

    def recommend_for_role(
        self,
        role: ModelRole,
        *,
        hardware_snapshot: Optional[HardwareSnapshot] = None,
        provider_type: Optional[ProviderType] = None,
    ) -> Optional[ModelCatalogEntry]:
        """
        Recommend a model for the given role based on hardware and provider availability.

        Args:
            role: The model role to recommend for (e.g., ModelRole.NARRATOR).
            hardware_snapshot: Optional hardware snapshot; if not provided, it will be detected.
            provider_type: Optional provider type to prefer; if None, the engine will use the
                           currently selected provider or auto-detect.

        Returns:
            A ModelCatalogEntry recommendation, or None if no suitable model is found.
        """
        # 1. Determine hardware profile
        if hardware_snapshot is None:
            hardware_snapshot = self._detect_hardware_snapshot()
        profile = classify_hardware(hardware_snapshot)
        self._logger.debug(
            f"[RecommendationEngine] Hardware profile: {profile.value} "
            f"(GPU: {hardware_snapshot.gpu_available}, VRAM: {hardware_snapshot.vram_total_mb}MB, "
            f"RAM: {hardware_snapshot.ram_total_mb}MB)"
        )

        # 2. Filter catalog by profile class (allowed profiles)
        allowed_entries = catalog_for_profile(profile, self.model_catalog)
        self._logger.debug(
            f"[RecommendationEngine] {len(allowed_entries)} entries match profile {profile.value}"
        )

        # 3. Further filter by role
        role_entries = [e for e in allowed_entries if e.role == role]
        self._logger.debug(
            f"[RecommendationEngine] {len(role_entries)} entries for role {role.value}"
        )

        if not role_entries:
            self._logger.warning(
                f"[RecommendationEngine] No model catalog entries found for role {role.value} "
                f"and profile {profile.value}"
            )
            return None

        # 4. If a specific provider is requested, try to match provider-managed models
        # For now, we only have local models in the catalog; provider-specific logic can be added later.
        # We'll just return the first entry (could be improved with scoring).
        # Sort by preference: prefer lower quantization (higher quality) for same size?
        # For now just pick first.
        # We'll sort by quantization quality (roughly: higher number or letter is better) and size.
        def _entry_score(entry: ModelCatalogEntry) -> tuple:
            # Prefer higher quantization (e.g., Q6 > Q5 > Q4)
            quant_map = {"Q2": 0, "Q3": 1, "Q4": 2, "Q5": 3, "Q6": 4, "Q8": 5}
            quant_prefix = "".join([c for c in entry.quantization if c.isalpha() or c.isdigit()])
            # Extract number if present
            quant_num = 0
            for part in quant_prefix.split('_'):
                if part.isdigit():
                    quant_num = int(part)
                    break
            # Prefer smaller size for constrained profiles? Actually, we already filtered by profile.
            # For simplicity, we just use quantization and then size class (small < medium < large)
            size_order = {ModelSizeClass.SMALL: 0, ModelSizeClass.MEDIUM: 1, ModelSizeClass.LARGE: 2}
            return (
                -quant_num,  # negative so higher quant is better (lower negative)
                size_order[entry.estimated_size_class],
                entry.model_id,  # tie-breaker
            )

        role_entries.sort(key=_entry_score)
        recommended = role_entries[0]
        self._logger.info(
            f"[RecommendationEngine] Recommended model for {role.value}: {recommended.model_id} "
            f"({recommended.display_name})"
        )
        return recommended

    def recommend_for_all_roles(
        self,
        *,
        hardware_snapshot: Optional[HardwareSnapshot] = None,
        provider_type: Optional[ProviderType] = None,
    ) -> Dict[ModelRole, Optional[ModelCatalogEntry]]:
        """
        Recommend a model for each role in the ModelRole enum.
        """
        result: Dict[ModelRole, Optional[ModelCatalogEntry]] = {}
        for role in ModelRole:
            result[role] = self.recommend_for_role(
                role,
                hardware_snapshot=hardware_snapshot,
                provider_type=provider_type,
            )
        return result

    def _detect_hardware_snapshot(self) -> HardwareSnapshot:
        """
        Detect hardware snapshot using the existing hardware utilities.
        """
        try:
            from src.utils.hardware_utils import get_gpu_info

            gpu_info = get_gpu_info() or {}
            # Note: RAM detection is not in get_gpu_info; we'll need to get it separately.
            # For now, we'll set RAM to 0 and let the caller provide it if needed.
            # We can try to get RAM via psutil or platform, but to avoid extra deps, we'll leave it 0.
            # The classify_hardware function uses ram_total_mb < 16000 for conservative, so if we don't have RAM,
            # it might incorrectly classify as conservative. We'll try to get RAM from virtual memory.
            ram_total_mb = 0
            try:
                import psutil

                ram_total_mb = int(psutil.virtual_memory().total / (1024 * 1024))
            except Exception:
                pass  # Keep 0 if psutil not available

            return HardwareSnapshot(
                gpu_available=bool(gpu_info.get("available", False)),
                vram_total_mb=int(gpu_info.get("vram_total_mb", 0)),
                ram_total_mb=ram_total_mb,
                gpu_name=str(gpu_info.get("gpu_name", "")),
                os_name="",  # Not used in classification
            )
        except Exception as e:
            self._logger.warning(f"[RecommendationEngine] Failed to detect hardware: {e}")
            # Return a conservative default
            return HardwareSnapshot(
                gpu_available=False,
                vram_total_mb=0,
                ram_total_mb=0,
                gpu_name="",
                os_name="",
            )


# Convenience function for quick recommendation
def recommend_model_for_role(
    role: ModelRole,
    *,
    hardware_snapshot: Optional[HardwareSnapshot] = None,
    provider_type: Optional[ProviderType] = None,
    db: Optional[DatabaseManager] = None,
) -> Optional[ModelCatalogEntry]:
    engine = RecommendationEngine(db=db)
    return engine.recommend_for_role(
        role,
        hardware_snapshot=hardware_snapshot,
        provider_type=provider_type,
    )
