# -*- coding: utf-8 -*-
"""
Provider Adapters - Wrapper implementations for various LLM providers.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Dict, Any

from src.infra.services.provider_registry import ProviderAdapter, ProviderType
from src.infra.adapters.lm_studio_service import LMStudioService
from src.infra.config.configuration_manager import get_config
from src.infra.persistence.database_manager import DatabaseManager

logger = logging.getLogger(__name__)


class LMStudioAdapter(ProviderAdapter):
    """Adapter for LM Studio that implements the ProviderAdapter protocol."""

    def __init__(self, db: Optional[DatabaseManager] = None):
        config = get_config()
        self._lm_studio = LMStudioService(config, db=db)

    def list_models(self) -> List[Dict[str, str]]:
        """
        Return list of available models from LM Studio.
        Each dict should have at least 'id' and optionally 'name'.
        """
        try:
            # LMStudioService.list_models returns a list of dicts with 'id' and maybe other keys
            models = self._lm_studio.list_models() or []
            # Ensure each entry has an 'id' field; if not, use 'name' as fallback
            result: List[Dict[str, str]] = []
            for m in models:
                if isinstance(m, dict):
                    model_id = m.get("id") or m.get("name") or ""
                    if model_id:
                        # Normalize to have 'id' and 'name'
                        result.append({
                            "id": model_id,
                            "name": m.get("name", model_id),
                        })
            return result
        except Exception as e:
            logger.warning(f"[LMStudioAdapter] Failed to list models: {e}")
            return []

    def is_available(self) -> bool:
        """Check if LM Studio server is reachable."""
        try:
            return self._lm_studio._is_server_reachable()
        except Exception:
            return False

    def get_default_model(self) -> Optional[str]:
        """
        Get the default model from LM Studio.
        This could be the currently loaded model or the first available.
        """
        try:
            status = self._lm_studio.get_status() or {}
            model = status.get("model") or status.get("loaded_model")
            if model:
                return str(model)
            # Fallback to first available model
            models = self.list_models()
            if models:
                return models[0]["id"]
        except Exception:
            pass
        return None


# TODO: Add OllamaAdapter, LlamaCppAdapter, etc. as needed.

def get_adapter_for_provider(provider_type: ProviderType, db: Optional[DatabaseManager] = None) -> Optional[ProviderAdapter]:
    """
    Factory function to get an adapter instance for a given provider type.
    """
    if provider_type == ProviderType.LM_STUDIO:
        return LMStudioAdapter(db=db)
    # Add other providers here
    return None
