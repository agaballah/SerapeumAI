# -*- coding: utf-8 -*-
"""
Read-only runtime provider discovery for SerapeumAI.

Wave 1B-1 rules:
- no install
- no start/stop
- no model download
- no model load/unload
- no config mutation
- no project data sent
- local endpoint probes only
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Protocol
from urllib import error, request
from urllib.parse import urlparse


STATUS_NOT_DETECTED = "not_detected"
STATUS_DETECTED = "detected"
STATUS_REACHABLE = "reachable"
STATUS_DISABLED = "disabled"
STATUS_UNREACHABLE = "unreachable"
STATUS_UNSUPPORTED = "unsupported"


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

    @property
    def available(self) -> bool:
        return self.status == STATUS_REACHABLE

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["available"] = self.available
        data["capabilities"] = list(self.capabilities or [])
        data["side_effects"] = dict(self.side_effects or {})
        data["details"] = dict(self.details or {})
        return data


class ProviderDiscoveryAdapter(Protocol):
    name: str

    def discover(self) -> ProviderDiscoveryResult:
        ...


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
    ) -> None:
        self.name = str(name)
        self.provider_type = str(provider_type)
        self.endpoint = str(endpoint or "").rstrip("/")
        self.enabled = bool(enabled)
        self.probe_path = str(probe_path or "/").lstrip("/")
        self.capabilities = list(capabilities or [])
        self.timeout_s = float(timeout_s)
        self.local_only = bool(local_only)

    def _result(self, status: str, reason: str, *, details: Optional[Dict[str, Any]] = None) -> ProviderDiscoveryResult:
        return ProviderDiscoveryResult(
            provider_name=self.name,
            provider_type=self.provider_type,
            endpoint=self.endpoint,
            status=status,
            reason=reason,
            capabilities=list(self.capabilities),
            side_effects=_no_side_effects(),
            details=dict(details or {}),
        )

    def _probe_url(self) -> str:
        if not self.endpoint:
            return ""
        return f"{self.endpoint}/{self.probe_path}"

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
            if 200 <= code < 300:
                return self._result(
                    STATUS_REACHABLE,
                    "probe_ok",
                    details={"http_status": code, "probe_method": "GET", "probe_path": f"/{self.probe_path}"},
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


class LMStudioDiscoveryAdapter(HttpProviderDiscoveryAdapter):
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
        )


class OpenAICompatibleLocalDiscoveryAdapter(HttpProviderDiscoveryAdapter):
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
        )


class RuntimeProviderDiscoveryRegistry:
    def __init__(self, adapters: Optional[Iterable[ProviderDiscoveryAdapter]] = None) -> None:
        self.adapters = list(adapters or [])

    @classmethod
    def from_config(cls, config: Any) -> "RuntimeProviderDiscoveryRegistry":
        providers: List[ProviderDiscoveryAdapter] = []

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
