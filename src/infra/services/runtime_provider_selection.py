# -*- coding: utf-8 -*-
"""
Runtime provider/model selection persistence contract.

Upgrade 3S rules:
- explicit user action only
- config mutation only
- no provider probing
- no provider start/stop
- no model download
- no model load/unload
- no internet use
- no project data sent
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, Optional

from src.infra.services.runtime_provider_discovery import (
    PROVIDER_MODE_DISABLED_LOCAL_REVIEW_ONLY,
    PROVIDER_MODE_LEGACY_LLAMA_CPP_AVAILABLE_IF_PRESENT,
    PROVIDER_MODE_LM_STUDIO_CLI_MANAGED,
    PROVIDER_MODE_LM_STUDIO_MANUAL_OPENAI_COMPAT,
    PROVIDER_MODE_OLLAMA_LOCAL,
    PROVIDER_MODE_OPENAI_COMPATIBLE_LOCAL,
)

PROVIDER_LOCAL_REVIEW_ONLY = "local_review_only"
PROVIDER_LM_STUDIO = "lm_studio"
PROVIDER_OLLAMA = "ollama"
PROVIDER_OPENAI_COMPATIBLE_LOCAL = "openai_compatible_local"
PROVIDER_LEGACY_LLAMA_CPP = "legacy_llama_cpp"

_ALLOWED_MODES_BY_PROVIDER = {
    PROVIDER_LOCAL_REVIEW_ONLY: {PROVIDER_MODE_DISABLED_LOCAL_REVIEW_ONLY},
    PROVIDER_LM_STUDIO: {
        PROVIDER_MODE_LM_STUDIO_MANUAL_OPENAI_COMPAT,
        PROVIDER_MODE_LM_STUDIO_CLI_MANAGED,
    },
    PROVIDER_OLLAMA: {PROVIDER_MODE_OLLAMA_LOCAL},
    PROVIDER_OPENAI_COMPATIBLE_LOCAL: {PROVIDER_MODE_OPENAI_COMPATIBLE_LOCAL},
    PROVIDER_LEGACY_LLAMA_CPP: {PROVIDER_MODE_LEGACY_LLAMA_CPP_AVAILABLE_IF_PRESENT},
}


def _selection_side_effects(*, config_mutated: bool = False) -> Dict[str, bool]:
    return {
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
        "config_mutated": bool(config_mutated),
    }


def normalize_provider_name(provider: str) -> str:
    value = str(provider or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "disabled": PROVIDER_LOCAL_REVIEW_ONLY,
        "no_ai": PROVIDER_LOCAL_REVIEW_ONLY,
        "local_review": PROVIDER_LOCAL_REVIEW_ONLY,
        "local_review_only": PROVIDER_LOCAL_REVIEW_ONLY,
        "lmstudio": PROVIDER_LM_STUDIO,
        "lm_studio": PROVIDER_LM_STUDIO,
        "lm_studio_cli": PROVIDER_LM_STUDIO,
        "lm_studio_ui": PROVIDER_LM_STUDIO,
        "ollama": PROVIDER_OLLAMA,
        "openai_compatible": PROVIDER_OPENAI_COMPATIBLE_LOCAL,
        "openai_compatible_local": PROVIDER_OPENAI_COMPATIBLE_LOCAL,
        "llama_cpp": PROVIDER_LEGACY_LLAMA_CPP,
        "legacy_llama_cpp": PROVIDER_LEGACY_LLAMA_CPP,
    }
    return aliases.get(value, value)


def normalize_provider_mode(mode: str) -> str:
    return str(mode or "").strip().upper().replace("-", "_").replace(" ", "_")


def supported_provider_modes(provider: str) -> list[str]:
    normalized = normalize_provider_name(provider)
    return sorted(_ALLOWED_MODES_BY_PROVIDER.get(normalized, set()))


def validate_provider_mode(provider: str, mode: str) -> tuple[str, str]:
    provider_name = normalize_provider_name(provider)
    provider_mode = normalize_provider_mode(mode)

    allowed = _ALLOWED_MODES_BY_PROVIDER.get(provider_name)
    if not allowed:
        raise ValueError(f"Unsupported runtime provider: {provider}")
    if provider_mode not in allowed:
        allowed_text = ", ".join(sorted(allowed))
        raise ValueError(f"Unsupported provider mode '{mode}' for provider '{provider_name}'. Allowed: {allowed_text}")
    return provider_name, provider_mode


def _clean_model(value: Optional[str]) -> str:
    return str(value or "").strip()


@dataclass(frozen=True)
class RuntimeProviderSelectionResult:
    ok: bool
    selected_provider: str
    selected_provider_mode: str
    selected_chat_model: str
    selected_analysis_model: str
    scope: str
    config_path: str
    message: str
    side_effects: Dict[str, bool]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RuntimeProviderSelectionService:
    """Persist runtime provider/model selection through ConfigurationManager."""

    def __init__(self, config: Any) -> None:
        self.config = config

    def save_selection(
        self,
        *,
        provider: str,
        provider_mode: str,
        chat_model: Optional[str] = "",
        analysis_model: Optional[str] = "",
        scope: str = "local",
    ) -> RuntimeProviderSelectionResult:
        provider_name, mode = validate_provider_mode(provider, provider_mode)
        chat = _clean_model(chat_model)
        analysis = _clean_model(analysis_model)

        if provider_name != PROVIDER_LOCAL_REVIEW_ONLY and (not chat or not analysis):
            raise ValueError("Chat and analysis model selections are required for model-backed providers.")

        setter = getattr(self.config, "set", None)
        saver = getattr(self.config, "save", None)
        if not callable(setter) or not callable(saver):
            raise RuntimeError("Configuration object must provide set(...) and save(...).")

        setter("runtime.selected_provider", provider_name, scope=scope)
        setter("runtime.selected_provider_mode", mode, scope=scope)
        setter("runtime.selected_chat_model", chat, scope=scope)
        setter("runtime.selected_analysis_model", analysis, scope=scope)

        # Mirror to existing model keys so current LM Studio paths can read the
        # selected models while later packets add provider-aware invocation.
        if provider_name != PROVIDER_LOCAL_REVIEW_ONLY:
            setter("models.chat.model", chat, scope=scope)
            setter("models.analysis.model", analysis, scope=scope)
            setter("models.chat.backend", provider_name, scope=scope)
            setter("models.analysis.backend", provider_name, scope=scope)

        config_path = str(saver(scope=scope) or "")
        return RuntimeProviderSelectionResult(
            ok=True,
            selected_provider=provider_name,
            selected_provider_mode=mode,
            selected_chat_model=chat,
            selected_analysis_model=analysis,
            scope=str(scope),
            config_path=config_path,
            message="Runtime provider/model selection saved. No provider or model runtime action was performed.",
            side_effects=_selection_side_effects(config_mutated=True),
        )


def save_runtime_provider_selection(
    *,
    config: Any,
    provider: str,
    provider_mode: str,
    chat_model: Optional[str] = "",
    analysis_model: Optional[str] = "",
    scope: str = "local",
) -> Dict[str, Any]:
    return RuntimeProviderSelectionService(config).save_selection(
        provider=provider,
        provider_mode=provider_mode,
        chat_model=chat_model,
        analysis_model=analysis_model,
        scope=scope,
    ).to_dict()
