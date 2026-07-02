# -*- coding: utf-8 -*-
"""
Read-only runtime provider discovery for SerapeumAI.

Wave 1B-1 / Upgrade 3S rules:
- no install
- no start/stop
- no model download
- no model load/unload
- no config mutation
- no project data sent
- local endpoint probes only
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Protocol
from urllib import error, request
from urllib.parse import urlparse


STATUS_NOT_DETECTED = "not_detected"
STATUS_DETECTED = "detected"
STATUS_REACHABLE = "reachable"
STATUS_DISABLED = "disabled"
STATUS_UNREACHABLE = "unreachable"
STATUS_UNSUPPORTED = "unsupported"

PROVIDER_MODE_DISABLED_LOCAL_REVIEW_ONLY = "DISABLED_LOCAL_REVIEW_ONLY"
PROVIDER_MODE_LM_STUDIO_MANUAL_OPENAI_COMPAT = "LM_STUDIO_MANUAL_OPENAI_COMPAT"
PROVIDER_MODE_LM_STUDIO_CLI_MANAGED = "LM_STUDIO_CLI_MANAGED"
PROVIDER_MODE_OLLAMA_LOCAL = "OLLAMA_LOCAL"
PROVIDER_MODE_LEGACY_LLAMA_CPP_AVAILABLE_IF_PRESENT = "LEGACY_LLAMA_CPP_AVAILABLE_IF_PRESENT"
PROVIDER_MODE_OPENAI_COMPATIBLE_LOCAL = "OPENAI_COMPATIBLE_LOCAL"


def app_root() -> Path:
    return Path(__file__).resolve().parents[3]


def configured_gguf_search_dirs(config: Any = None) -> List[Path]:
    values: List[Any] = []
    if config is not None:
        configured = None
        get = getattr(config, "get", None)
        if callable(get):
            configured = get("runtime.gguf_model_dirs") or get("models.gguf_search_dirs")
        if isinstance(configured, str):
            values.extend(part.strip() for part in configured.split(os.pathsep))
        elif isinstance(configured, (list, tuple)):
            values.extend(configured)

    values.extend(
        [
            app_root() / "models",
            Path(os.path.expanduser("~")) / ".cache" / "lm-studio" / "models",
        ]
    )

    out: List[Path] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if not text:
            continue
        path = Path(os.path.expandvars(os.path.expanduser(text)))
        if not path.is_absolute():
            path = app_root() / path
        key = os.path.normcase(os.path.normpath(str(path)))
        if key in seen:
            continue
        seen.add(key)
        out.append(path)
    return out


def scan_gguf_models(search_dirs: Iterable[Path]) -> List[Dict[str, Any]]:
    listed_models: List[Dict[str, Any]] = []
    seen_paths: set[str] = set()
    for directory in search_dirs:
        if not directory.exists() or not directory.is_dir():
            continue
        for path in directory.rglob("*.gguf"):
            try:
                abs_path = os.path.normpath(str(path.resolve()))
                if abs_path in seen_paths:
                    continue
                seen_paths.add(abs_path)
                listed_models.append(
                    {
                        "model_id": path.name,
                        "display_name": path.stem,
                        "path": abs_path,
                        "size_bytes": path.stat().st_size,
                    }
                )
            except Exception:
                continue
    return listed_models


def _no_side_effects() -> Dict[str, bool]:
    return {
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


def is_loopback_endpoint(endpoint: str) -> bool:
    parsed = urlparse(str(endpoint or ""))
    host = (parsed.hostname or "").strip().lower()
    return host in {"localhost", "127.0.0.1", "::1"}


@dataclass(frozen=True)
class ProviderDiscoveryResult:
    provider_name: str
    provider_type: str
    endpoint: str
    status: str
    reason: str
    capabilities: List[str] = field(default_factory=list)
    side_effects: Dict[str, bool] = field(default_factory=_no_side_effects)
    details: Dict[str, Any] = field(default_factory=dict)
    provider_mode: str = ""
    provider_modes_supported: List[str] = field(default_factory=list)
    listed_models: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def available(self) -> bool:
        return self.status == STATUS_REACHABLE

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["available"] = self.available
        data["capabilities"] = list(self.capabilities or [])
        data["side_effects"] = dict(self.side_effects or {})
        data["details"] = dict(self.details or {})
        data["provider_modes_supported"] = list(self.provider_modes_supported or [])
        data["listed_models"] = [dict(row) for row in (self.listed_models or []) if isinstance(row, dict)]
        return data


class ProviderDiscoveryAdapter(Protocol):
    name: str

    def discover(self) -> ProviderDiscoveryResult:
        ...


class LocalReviewOnlyDiscoveryAdapter:
    """Explicit no-AI/deterministic review mode.

    This is a valid app mode, but it is not a reachable model provider. It lets
    UI/read-model surfaces show that deterministic review can continue without
    pretending AI runtime readiness.
    """

    name = "local_review_only"

    def discover(self) -> ProviderDiscoveryResult:
        return ProviderDiscoveryResult(
            provider_name=self.name,
            provider_type="local_review_only",
            endpoint="",
            status=STATUS_DISABLED,
            reason="local_review_only_no_ai_mode",
            capabilities=["deterministic_review", "facts", "evidence_lanes", "no_ai"],
            side_effects=_no_side_effects(),
            details={"valid_without_ai": True, "model_listing_supported": False},
            provider_mode=PROVIDER_MODE_DISABLED_LOCAL_REVIEW_ONLY,
            provider_modes_supported=[PROVIDER_MODE_DISABLED_LOCAL_REVIEW_ONLY],
            listed_models=[],
        )


class HttpProviderDiscoveryAdapter:
    def __init__(
        self,
        *,
        name: str,
        provider_type: str,
        endpoint: str,
        enabled: bool = True,
        probe_path: str = "/v1/models",
        capabilities: Optional[Iterable[str]] = None,
        timeout_s: float = 1.5,
        local_only: bool = True,
        provider_mode: str = "",
        provider_modes_supported: Optional[Iterable[str]] = None,
    ) -> None:
        self.name = str(name)
        self.provider_type = str(provider_type)
        self.endpoint = str(endpoint or "").rstrip("/")
        self.enabled = bool(enabled)
        self.probe_path = str(probe_path or "/").lstrip("/")
        self.capabilities = list(capabilities or [])
        self.timeout_s = float(timeout_s)
        self.local_only = bool(local_only)
        self.provider_mode = str(provider_mode or "")
        self.provider_modes_supported = list(provider_modes_supported or ([self.provider_mode] if self.provider_mode else []))

    def _result(
        self,
        status: str,
        reason: str,
        *,
        details: Optional[Dict[str, Any]] = None,
        listed_models: Optional[List[Dict[str, Any]]] = None,
    ) -> ProviderDiscoveryResult:
        merged_details = dict(details or {})
        if self.provider_mode:
            merged_details.setdefault("provider_mode", self.provider_mode)
        if self.provider_modes_supported:
            merged_details.setdefault("provider_modes_supported", list(self.provider_modes_supported))
        merged_details.setdefault("model_listing_supported", "model_listing" in self.capabilities)
        return ProviderDiscoveryResult(
            provider_name=self.name,
            provider_type=self.provider_type,
            endpoint=self.endpoint,
            status=status,
            reason=reason,
            capabilities=list(self.capabilities),
            side_effects=_no_side_effects(),
            details=merged_details,
            provider_mode=self.provider_mode,
            provider_modes_supported=list(self.provider_modes_supported),
            listed_models=[dict(row) for row in (listed_models or []) if isinstance(row, dict)],
        )

    def _probe_url(self) -> str:
        if not self.endpoint:
            return ""
        return f"{self.endpoint}/{self.probe_path}"

    def _listed_models_from_payload(self, payload: Any) -> List[Dict[str, Any]]:
        return []

    def _read_listed_models(self, resp: Any) -> List[Dict[str, Any]]:
        reader = getattr(resp, "read", None)
        if not callable(reader):
            return []
        try:
            raw = reader()
        except Exception:
            return []
        if not raw:
            return []
        try:
            if isinstance(raw, bytes):
                text = raw.decode("utf-8", errors="replace")
            else:
                text = str(raw)
            payload = json.loads(text)
        except Exception:
            return []
        return self._listed_models_from_payload(payload)

    def discover(self) -> ProviderDiscoveryResult:
        if not self.enabled:
            return self._result(STATUS_DISABLED, "disabled_in_config")

        if not self.endpoint:
            return self._result(STATUS_NOT_DETECTED, "endpoint_not_configured")

        if self.local_only and not is_loopback_endpoint(self.endpoint):
            return self._result(
                STATUS_UNSUPPORTED,
                "non_local_endpoint_blocked",
                details={"local_only": True},
            )

        probe_url = self._probe_url()
        try:
            req = request.Request(probe_url, method="GET")
            with request.urlopen(req, timeout=self.timeout_s) as resp:
                code = int(getattr(resp, "status", 200))
                listed_models = self._read_listed_models(resp)
            if 200 <= code < 300:
                return self._result(
                    STATUS_REACHABLE,
                    "probe_ok",
                    details={"http_status": code, "probe_method": "GET", "probe_path": f"/{self.probe_path}"},
                    listed_models=listed_models,
                )
            return self._result(
                STATUS_UNREACHABLE,
                f"http_{code}",
                details={"http_status": code, "probe_method": "GET", "probe_path": f"/{self.probe_path}"},
            )
        except error.HTTPError as exc:
            code = getattr(exc, "code", "error")
            return self._result(
                STATUS_UNREACHABLE,
                f"http_{code}",
                details={"http_status": code, "probe_method": "GET", "probe_path": f"/{self.probe_path}"},
            )
        except Exception as exc:
            return self._result(
                STATUS_UNREACHABLE,
                f"unreachable:{type(exc).__name__}",
                details={"probe_method": "GET", "probe_path": f"/{self.probe_path}"},
            )


class _OpenAICompatibleModelListingMixin:
    def _listed_models_from_payload(self, payload: Any) -> List[Dict[str, Any]]:
        rows = payload.get("data", []) if isinstance(payload, dict) else []
        if not isinstance(rows, list):
            return []
        out: List[Dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            model_id = str(row.get("id") or row.get("name") or "").strip()
            if not model_id:
                continue
            out.append(
                {
                    "model_id": model_id,
                    "display_name": str(row.get("display_name") or row.get("name") or model_id).strip(),
                    "source": self.name,
                    "raw_type": str(row.get("object") or "model").strip(),
                }
            )
        return out


class LMStudioDiscoveryAdapter(_OpenAICompatibleModelListingMixin, HttpProviderDiscoveryAdapter):
    def __init__(self, *, endpoint: str = "http://127.0.0.1:1234", enabled: bool = True, timeout_s: float = 1.5) -> None:
        super().__init__(
            name="lm_studio",
            provider_type="lm_studio",
            endpoint=endpoint,
            enabled=enabled,
            probe_path="/v1/models",
            capabilities=["local_runtime", "openai_compatible", "model_listing", "chat_completions"],
            timeout_s=timeout_s,
            local_only=True,
            provider_mode=PROVIDER_MODE_LM_STUDIO_MANUAL_OPENAI_COMPAT,
            provider_modes_supported=[
                PROVIDER_MODE_LM_STUDIO_MANUAL_OPENAI_COMPAT,
                PROVIDER_MODE_LM_STUDIO_CLI_MANAGED,
            ],
        )


class OllamaDiscoveryAdapter(HttpProviderDiscoveryAdapter):
    def __init__(self, *, endpoint: str = "http://127.0.0.1:11434", enabled: bool = True, timeout_s: float = 1.5) -> None:
        super().__init__(
            name="ollama",
            provider_type="ollama",
            endpoint=endpoint,
            enabled=enabled,
            probe_path="/api/tags",
            capabilities=["local_runtime", "ollama", "model_listing"],
            timeout_s=timeout_s,
            local_only=True,
            provider_mode=PROVIDER_MODE_OLLAMA_LOCAL,
            provider_modes_supported=[PROVIDER_MODE_OLLAMA_LOCAL],
        )

    def _listed_models_from_payload(self, payload: Any) -> List[Dict[str, Any]]:
        rows = payload.get("models", []) if isinstance(payload, dict) else []
        if not isinstance(rows, list):
            return []
        out: List[Dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            model_id = str(row.get("name") or row.get("model") or "").strip()
            if not model_id:
                continue
            out.append(
                {
                    "model_id": model_id,
                    "display_name": model_id,
                    "source": self.name,
                    "size": row.get("size", ""),
                    "modified_at": str(row.get("modified_at") or ""),
                }
            )
        return out


class OpenAICompatibleLocalDiscoveryAdapter(_OpenAICompatibleModelListingMixin, HttpProviderDiscoveryAdapter):
    def __init__(
        self,
        *,
        name: str = "openai_compatible_local",
        endpoint: str = "",
        enabled: bool = False,
        timeout_s: float = 1.5,
    ) -> None:
        super().__init__(
            name=name,
            provider_type="openai_compatible",
            endpoint=endpoint,
            enabled=enabled,
            probe_path="/v1/models",
            capabilities=["openai_compatible", "model_listing", "chat_completions"],
            timeout_s=timeout_s,
            local_only=True,
            provider_mode=PROVIDER_MODE_OPENAI_COMPATIBLE_LOCAL,
            provider_modes_supported=[PROVIDER_MODE_OPENAI_COMPATIBLE_LOCAL],
        )


class LlamaCppDiscoveryAdapter(ProviderDiscoveryAdapter):
    def __init__(self, *, config: Any = None) -> None:
        self.config = config

    @property
    def name(self) -> str:
        return "legacy_llama_cpp"

    def discover(self) -> ProviderDiscoveryResult:
        try:
            from llama_cpp import Llama
            has_llama = True
        except ImportError:
            has_llama = False

        if not has_llama:
            return ProviderDiscoveryResult(
                provider_name="legacy_llama_cpp",
                provider_type="embedded",
                endpoint="in_process",
                status=STATUS_NOT_DETECTED,
                reason="llama-cpp-python package not installed",
                capabilities=[],
                side_effects=_no_side_effects(),
                details={"modes_supported": [PROVIDER_MODE_LEGACY_LLAMA_CPP_AVAILABLE_IF_PRESENT]},
                provider_mode=PROVIDER_MODE_LEGACY_LLAMA_CPP_AVAILABLE_IF_PRESENT,
                provider_modes_supported=[PROVIDER_MODE_LEGACY_LLAMA_CPP_AVAILABLE_IF_PRESENT],
                listed_models=[],
            )

        search_dirs = configured_gguf_search_dirs(self.config)
        listed_models = scan_gguf_models(search_dirs)

        status = STATUS_REACHABLE if listed_models else STATUS_DETECTED
        reason = "" if listed_models else "llama-cpp-python is installed, but no .gguf models were found in configured local model directories."

        return ProviderDiscoveryResult(
            provider_name="legacy_llama_cpp",
            provider_type="embedded",
            endpoint="in_process",
            status=status,
            reason=reason,
            capabilities=["local_runtime", "chat_completions", "embedded_inference"],
            side_effects=_no_side_effects(),
            details={
                "modes_supported": [PROVIDER_MODE_LEGACY_LLAMA_CPP_AVAILABLE_IF_PRESENT],
                "search_dirs": [str(path) for path in search_dirs],
            },
            provider_mode=PROVIDER_MODE_LEGACY_LLAMA_CPP_AVAILABLE_IF_PRESENT,
            provider_modes_supported=[PROVIDER_MODE_LEGACY_LLAMA_CPP_AVAILABLE_IF_PRESENT],
            listed_models=listed_models,
        )


class RuntimeProviderDiscoveryRegistry:
    def __init__(self, adapters: Optional[Iterable[ProviderDiscoveryAdapter]] = None) -> None:
        self.adapters = list(adapters or [])

    @classmethod
    def from_config(cls, config: Any) -> "RuntimeProviderDiscoveryRegistry":
        providers: List[ProviderDiscoveryAdapter] = [
            LocalReviewOnlyDiscoveryAdapter(),
            LlamaCppDiscoveryAdapter(config=config),
        ]

        lm_cfg = config.get_section("lm_studio") if config else {}
        providers.append(
            LMStudioDiscoveryAdapter(
                enabled=bool(lm_cfg.get("enabled", True)),
                endpoint=str(lm_cfg.get("url", "http://127.0.0.1:1234")),
            )
        )

        ollama_cfg = config.get_section("ollama") if config else {}
        providers.append(
            OllamaDiscoveryAdapter(
                enabled=bool(ollama_cfg.get("enabled", True)),
                endpoint=str(ollama_cfg.get("url", "http://127.0.0.1:11434")),
            )
        )

        openai_cfg = config.get_section("openai_compatible") if config else {}
        if not openai_cfg and config:
            runtime_cfg = config.get_section("runtime_providers")
            if isinstance(runtime_cfg.get("openai_compatible"), dict):
                openai_cfg = runtime_cfg.get("openai_compatible", {})

        openai_endpoint = str(openai_cfg.get("url") or openai_cfg.get("endpoint") or "")
        openai_enabled = bool(openai_cfg.get("enabled", False))
        if openai_endpoint or openai_enabled:
            providers.append(
                OpenAICompatibleLocalDiscoveryAdapter(
                    name=str(openai_cfg.get("name", "openai_compatible_local")),
                    endpoint=openai_endpoint,
                    enabled=openai_enabled,
                )
            )

        return cls(providers)

    def discover(self) -> List[ProviderDiscoveryResult]:
        results: List[ProviderDiscoveryResult] = []
        for adapter in self.adapters:
            try:
                results.append(adapter.discover())
            except Exception as exc:
                results.append(
                    ProviderDiscoveryResult(
                        provider_name=getattr(adapter, "name", "unknown"),
                        provider_type="unknown",
                        endpoint="",
                        status=STATUS_UNREACHABLE,
                        reason=f"adapter_error:{type(exc).__name__}",
                        capabilities=[],
                        side_effects=_no_side_effects(),
                    )
                )
        return sorted(results, key=lambda item: (item.provider_name, item.endpoint))

    def discover_dicts(self) -> List[Dict[str, Any]]:
        return [result.to_dict() for result in self.discover()]


class RuntimeProviderDiscoveryService:
    def __init__(self, config: Any = None, registry: Optional[RuntimeProviderDiscoveryRegistry] = None) -> None:
        self.config = config
        self.registry = registry or RuntimeProviderDiscoveryRegistry.from_config(config)

    def discover_providers(self) -> List[Dict[str, Any]]:
        return self.registry.discover_dicts()
