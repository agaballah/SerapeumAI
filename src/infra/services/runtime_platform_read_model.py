# -*- coding: utf-8 -*-
"""
Runtime platform read-model aggregate service.

Combines the read-only runtime platform surfaces into one dashboard-ready
dictionary:

- provider discovery
- provider status presentation
- hardware-based model recommendation
- consent requirements

This module is read-model only:
- no provider start/stop
- no model download
- no model load/unload
- no runtime install
- no config mutation
- no persistence
- no UI side effects
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from src.infra.services.runtime_consent import RuntimeConsentPolicy
from src.infra.services.runtime_model_catalog import (
    recommend_models_from_detected_hardware,
)
from src.infra.services.runtime_provider_discovery import RuntimeProviderDiscoveryService
from src.infra.services.runtime_status_presenter import present_runtime_status


def _no_platform_side_effects() -> Dict[str, bool]:
    return {
        "provider_mutated": False,
        "model_download_attempted": False,
        "model_load_attempted": False,
        "model_unload_attempted": False,
        "runtime_install_attempted": False,
        "config_mutated": False,
        "project_data_sent": False,
        "persistence_written": False,
    }


class RuntimePlatformReadModelService:
    """
    Aggregates runtime platform status for future UI surfaces.

    The service intentionally returns dictionaries so UI/presenter layers can
    consume the result without importing runtime implementation details.
    """

    def __init__(
        self,
        *,
        config: Any = None,
        provider_discovery_service: Optional[Any] = None,
        gpu_info_provider: Optional[Any] = None,
        ram_total_mb_provider: Optional[Any] = None,
    ) -> None:
        self.config = config
        self.provider_discovery_service = provider_discovery_service or RuntimeProviderDiscoveryService(config)
        self.gpu_info_provider = gpu_info_provider
        self.ram_total_mb_provider = ram_total_mb_provider

    def build_read_model(self) -> Dict[str, Any]:
        provider_discovery_rows = self._discover_provider_rows()
        runtime_status = present_runtime_status(provider_discovery_rows)
        provider_reachable = bool(runtime_status.get("reachable_provider_count", 0) > 0)

        recommendation = recommend_models_from_detected_hardware(
            provider_reachable=provider_reachable,
            gpu_info_provider=self.gpu_info_provider,
            ram_total_mb_provider=self.ram_total_mb_provider,
        ).to_dict()

        return {
            "schema_version": 1,
            "runtime_status": runtime_status,
            "provider_discovery": provider_discovery_rows,
            "model_recommendation": recommendation,
            "consent_requirements": RuntimeConsentPolicy.all_requirements(),
            "side_effects": self._combine_side_effects(
                provider_discovery_rows=provider_discovery_rows,
                recommendation=recommendation,
            ),
        }

    def _discover_provider_rows(self) -> list[dict[str, Any]]:
        try:
            rows = self.provider_discovery_service.discover_providers()
        except Exception as exc:
            return [
                {
                    "provider_name": "runtime_discovery",
                    "provider_type": "unknown",
                    "endpoint": "",
                    "status": "unreachable",
                    "reason": f"discovery_error:{type(exc).__name__}",
                    "capabilities": [],
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
                    "details": {},
                    "available": False,
                }
            ]

        return [row for row in rows if isinstance(row, dict)]

    def _combine_side_effects(
        self,
        *,
        provider_discovery_rows: list[dict[str, Any]],
        recommendation: dict[str, Any],
    ) -> Dict[str, bool]:
        side_effects = _no_platform_side_effects()

        # Provider discovery is allowed to do read-only local endpoint probes.
        # Preserve any provider side-effect declaration so future UI/audit code
        # can detect violations.
        for row in provider_discovery_rows:
            declared = row.get("side_effects")
            if not isinstance(declared, dict):
                continue

            if declared.get("install_attempted"):
                side_effects["runtime_install_attempted"] = True
            if declared.get("start_attempted"):
                side_effects["provider_mutated"] = True
            if declared.get("stop_attempted"):
                side_effects["provider_mutated"] = True
            if declared.get("download_attempted"):
                side_effects["model_download_attempted"] = True
            if declared.get("model_load_attempted"):
                side_effects["model_load_attempted"] = True
            if declared.get("model_unload_attempted"):
                side_effects["model_unload_attempted"] = True
            if declared.get("config_mutated"):
                side_effects["config_mutated"] = True
            if declared.get("project_data_sent"):
                side_effects["project_data_sent"] = True

        recommendation_side_effects = recommendation.get("side_effects", {})
        if isinstance(recommendation_side_effects, dict):
            if recommendation_side_effects.get("download_attempted"):
                side_effects["model_download_attempted"] = True
            if recommendation_side_effects.get("model_load_attempted"):
                side_effects["model_load_attempted"] = True
            if recommendation_side_effects.get("runtime_install_attempted"):
                side_effects["runtime_install_attempted"] = True
            if recommendation_side_effects.get("provider_mutated"):
                side_effects["provider_mutated"] = True
            if recommendation_side_effects.get("project_data_sent"):
                side_effects["project_data_sent"] = True

        return side_effects


def build_runtime_platform_read_model(
    *,
    config: Any = None,
    provider_discovery_service: Optional[Any] = None,
    gpu_info_provider: Optional[Any] = None,
    ram_total_mb_provider: Optional[Any] = None,
) -> Dict[str, Any]:
    """Convenience function for callers that do not need service lifetime."""
    service = RuntimePlatformReadModelService(
        config=config,
        provider_discovery_service=provider_discovery_service,
        gpu_info_provider=gpu_info_provider,
        ram_total_mb_provider=ram_total_mb_provider,
    )
    return service.build_read_model()
