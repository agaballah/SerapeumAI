# -*- coding: utf-8 -*-
"""
Provider Registry - Discovery and management of LLM providers.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Dict, List, Optional, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


class ProviderType(str, Enum):
    """Supported LLM provider types."""
    LM_STUDIO = "lm_studio"
    OLLAMA = "ollama"
    LLAMA_CPP = "llama_cpp"  # Embedded llama.cpp
    PROVIDER_MANAGED = "provider_managed"  # Generic provider-managed models
    LOCAL_REVIEW_ONLY = "local_review_only"  # AI features disabled


@runtime_checkable
class ProviderAdapter(Protocol):
    """Protocol for provider adapters."""

    def list_models(self) -> List[Dict[str, str]]:
        """Return list of available models from the provider."""
        ...

    def is_available(self) -> bool:
        """Check if the provider is available/runnable."""
        ...

    def get_default_model(self) -> Optional[str]:
        """Get the default model for this provider, if any."""
        ...


class ProviderRegistry:
    """
    Registry for discovering and managing LLM providers.
    """

    def __init__(self):
        self._providers: Dict[ProviderType, ProviderAdapter] = {}
        self._selected_provider: Optional[ProviderType] = None

    def register_provider(self, provider_type: ProviderType, adapter: ProviderAdapter) -> None:
        """Register a provider adapter."""
        self._providers[provider_type] = adapter
        logger.info(f"[ProviderRegistry] Registered provider: {provider_type.value}")

    def unregister_provider(self, provider_type: ProviderType) -> None:
        """Unregister a provider."""
        if provider_type in self._providers:
            del self._providers[provider_type]
            logger.info(f"[ProviderRegistry] Unregistered provider: {provider_type.value}")

    def get_provider(self, provider_type: ProviderType) -> Optional[ProviderAdapter]:
        """Get a registered provider adapter."""
        return self._providers.get(provider_type)

    def list_available_providers(self) -> List[ProviderType]:
        """List providers that are currently available."""
        available = []
        for ptype, adapter in self._providers.items():
            if adapter.is_available():
                available.append(ptype)
        return available

    def set_selected_provider(self, provider_type: ProviderType) -> bool:
        """Set the selected provider if it is available."""
        adapter = self.get_provider(provider_type)
        if adapter and adapter.is_available():
            self._selected_provider = provider_type
            logger.info(f"[ProviderRegistry] Selected provider: {provider_type.value}")
            return True
        logger.warning(f"[ProviderRegistry] Provider {provider_type.value} not available for selection.")
        return False

    def get_selected_provider(self) -> Optional[ProviderType]:
        """Get the currently selected provider."""
        return self._selected_provider

    def get_selected_adapter(self) -> Optional[ProviderAdapter]:
        """Get the adapter for the currently selected provider."""
        if self._selected_provider is None:
            return None
        return self.get_provider(self._selected_provider)

    def get_available_models(self) -> List[Dict[str, str]]:
        """
        Get all available models from the selected provider.
        Returns list of dicts with at least {'id': str, 'name': str}.
        """
        adapter = self.get_selected_adapter()
        if adapter is None:
            return []
        return adapter.list_models()

    def get_default_model(self) -> Optional[str]:
        """Get the default model from the selected provider."""
        adapter = self.get_selected_adapter()
        if adapter is None:
            return None
        return adapter.get_default_model()