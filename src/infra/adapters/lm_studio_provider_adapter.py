# -*- coding: utf-8 -*-
"""LM Studio provider adapter for the ProviderRegistry."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.infra.adapters.lm_studio_service import LMStudioService
from src.infra.services.provider_registry import ProviderAdapter, ProviderType


class LMStudioProviderAdapter(ProviderAdapter):
    """Adapter that wraps LMStudioService to conform to ProviderAdapter protocol."""

    def __init__(self, lm_studio_service: LMStudioService):
        self._lm_studio = lm_studio_service
        self._provider_type = ProviderType.LM_STUDIO

    def list_models(self) -> List[Dict[str, str]]:
        """Return list of available models from LM Studio."""
        models = self._lm_studio.list_models()
        # Ensure each model has at least an 'id' and 'name' for consistency
        result: List[Dict[str, str]] = []
        for m in models:
            model_id = m.get("id", "")
            if not model_id:
                continue
            result.append({
                "id": model_id,
                "name": m.get("id", model_id),  # fallback to id as name
            })
        return result

    def is_available(self) -> bool:
        """Check if LM Studio is enabled and reachable."""
        if not self._lm_studio.enabled:
            return False
        try:
            # Use the existing reachability check
            return self._lm_studio._is_server_reachable()
        except Exception:
            return False

    def get_default_model(self) -> Optional[str]:
        """Get the default model from LM Studio, if any."""
        try:
            return self._lm_studio.get_default_model()
        except Exception:
            return None

    @property
    def provider_type(self) -> ProviderType:
        return self._provider_type