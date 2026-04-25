# -*- coding: utf-8 -*-
"""
Runtime advisor: read-only provider discovery, hardware profiling, deterministic
recommendation output, and explicit bounded runtime control actions.

Advisory discovery in this module is read-only. Explicit start/stop actions may
be executed only through user-confirmed bounded control paths.
"""

from __future__ import annotations

import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol
from urllib import error, request

try:
    from src.infra.services.benchmark_service import get_machine_hardware_snapshot
except Exception:  # pragma: no cover - compatibility fallback for older publish baselines
    def get_machine_hardware_snapshot() -> Dict[str, Any]:
        gpu_available = False
        gpu_name = "No GPU"
        vram_total_mb = 0
        detection_method = "none"
        try:
            import torch
            if torch.cuda.is_available():
                device = torch.cuda.current_device()
                gpu_available = True
                gpu_name = torch.cuda.get_device_name(device)
                vram_total_mb = int(torch.cuda.get_device_properties(device).total_memory / (1024 * 1024))
                detection_method = "torch"
        except Exception:
            pass
        ram_total_mb = 0
        try:
            import psutil  # type: ignore
            ram_total_mb = int(psutil.virtual_memory().total / (1024 * 1024))
        except Exception:
            pass
        return {
            "gpu_available": gpu_available,
            "gpu_name": gpu_name,
            "vram_total_mb": int(vram_total_mb),
            "vram_free_mb": 0,
            "ram_total_mb": int(ram_total_mb),
            "os_name": os.name,
            "detection_method": detection_method,
        }

from src.infra.services.lm_studio_control_adapter import LMStudioControlAdapter

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProviderStatus:
    name: str
    available: bool
    endpoint: str
    reason: str = ""
    capabilities: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["capabilities"] = list(self.capabilities or [])
        return data


@dataclass(frozen=True)
class HardwareProfile:
    hardware_class: str
    gpu_available: bool
    gpu_name: str
    vram_total_mb: int
    ram_total_mb: int
    os_name: str
    detection_method: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ProviderAdapter(Protocol):
    name: str

    def discover(self) -> ProviderStatus:
        ...


class LMStudioProviderAdapter:
    name = "lm_studio"

    def __init__(self, *, enabled: bool, url: str):
        self.enabled = bool(enabled)
        self.url = (url or "http://127.0.0.1:1234").rstrip("/")

    def discover(self) -> ProviderStatus:
        if not self.enabled:
            return ProviderStatus(self.name, False, self.url, "disabled_in_config", [])
        try:
            req = request.Request(f"{self.url}/v1/models", method="GET")
            with request.urlopen(req, timeout=1.5) as resp:
                code = getattr(resp, "status", 200)
            if 200 <= int(code) < 300:
                return ProviderStatus(
                    self.name,
                    True,
                    self.url,
                    "reachable",
                    ["chat_completions", "model_listing", "local_runtime"],
                )
            return ProviderStatus(self.name, False, self.url, f"http_{code}", [])
        except error.HTTPError as e:
            return ProviderStatus(self.name, False, self.url, f"http_{getattr(e, 'code', 'error')}", [])
        except Exception as e:
            return ProviderStatus(self.name, False, self.url, f"unreachable:{type(e).__name__}", [])


class ProviderRegistry:
    def __init__(self, adapters: Optional[List[ProviderAdapter]] = None):
        self.adapters = list(adapters or [])

    @classmethod
    def from_config(cls, config) -> "ProviderRegistry":
        lm_cfg = (config.get_section("lm_studio") or {}) if config else {}
        return cls([
            LMStudioProviderAdapter(
                enabled=bool(lm_cfg.get("enabled", False)),
                url=str(lm_cfg.get("url", "http://127.0.0.1:1234")),
            )
        ])

    def discover_providers(self) -> List[ProviderStatus]:
        out: List[ProviderStatus] = []
        for adapter in self.adapters:
            try:
                out.append(adapter.discover())
            except Exception as e:
                logger.warning("[ProviderRegistry] discover failed for %s: %s", getattr(adapter, "name", "unknown"), e)
        return sorted(out, key=lambda p: p.name)


class HardwareAdvisor:
    @staticmethod
    def classify_hardware(*, vram_total_mb: int, ram_total_mb: int, gpu_available: bool) -> str:
        if (not gpu_available) or vram_total_mb < 4096 or ram_total_mb < 16000:
            return "CONSERVATIVE"
        if vram_total_mb >= 12288 and ram_total_mb >= 32000:
            return "PERFORMANCE"
        return "BALANCED"

    @classmethod
    def profile_from_snapshot(
        cls,
        *,
        gpu_available: bool,
        gpu_name: str,
        vram_total_mb: int,
        ram_total_mb: int,
        os_name: str,
    ) -> HardwareProfile:
        return HardwareProfile(
            hardware_class=cls.classify_hardware(
                vram_total_mb=int(vram_total_mb or 0),
                ram_total_mb=int(ram_total_mb or 0),
                gpu_available=bool(gpu_available),
            ),
            gpu_available=bool(gpu_available),
            gpu_name=str(gpu_name or "unknown"),
            vram_total_mb=int(vram_total_mb or 0),
            ram_total_mb=int(ram_total_mb or 0),
            os_name=str(os_name or "unknown"),
            detection_method="snapshot",
        )

    @classmethod
    def detect_local_profile(cls) -> HardwareProfile:
        try:
            snap = get_machine_hardware_snapshot() or {}
        except Exception:
            snap = {}
        profile = cls.profile_from_snapshot(
            gpu_available=bool(snap.get("gpu_available", False)),
            gpu_name=str(snap.get("gpu_name", "No GPU")),
            vram_total_mb=int(snap.get("vram_total_mb", 0)),
            ram_total_mb=int(snap.get("ram_total_mb", 0)),
            os_name=str(snap.get("os_name", os.name)),
        )
        return HardwareProfile(
            profile.hardware_class,
            profile.gpu_available,
            profile.gpu_name,
            profile.vram_total_mb,
            profile.ram_total_mb,
            profile.os_name,
            str(snap.get("detection_method", "snapshot")),
        )


class RecommendationEngine:
    @staticmethod
    def recommend(profile: HardwareProfile, providers: List[ProviderStatus]) -> Dict[str, Any]:
        available_names = [p.name for p in providers if p.available]
        if profile.hardware_class == "PERFORMANCE":
            runtime_posture = "local_high_throughput"
            model_posture = "high_quality_7b_to_14b_quantized"
        elif profile.hardware_class == "BALANCED":
            runtime_posture = "local_balanced"
            model_posture = "balanced_7b_quantized"
        else:
            runtime_posture = "local_conservative"
            model_posture = "small_low_vram_models"
        warnings: List[str] = []
        constraints: List[str] = []
        if "lm_studio" not in available_names:
            warnings.append("No reachable local runtime provider detected.")
            constraints.append("Runtime remains advisory-only until provider is reachable.")
        if profile.vram_total_mb < 4096:
            warnings.append("Low VRAM detected; avoid vision-heavy profiles.")
        if profile.ram_total_mb and profile.ram_total_mb < 16000:
            warnings.append("System RAM below 16 GB may limit large context usage.")
        return {
            "detected_providers": [p.to_dict() for p in providers],
            "recommended_profile_class": profile.hardware_class,
            "recommended_runtime_posture": runtime_posture,
            "recommended_model_posture": model_posture,
            "warnings": warnings,
            "constraints": constraints,
        }


class RuntimeAdvisorService:
    def __init__(self, config):
        self.config = config
        self.registry = ProviderRegistry.from_config(config)
        self._default_lm_studio_url = "http://127.0.0.1:1234"
        lm_cfg = (config.get_section("lm_studio") or {}) if config else {}
        self._lm_studio_cfg = {
            "enabled": bool(lm_cfg.get("enabled", False)),
            "url": str(lm_cfg.get("url", self._default_lm_studio_url)),
            "lms_path": lm_cfg.get("lms_path"),
        }
        self._control_adapter = LMStudioControlAdapter(url=self._lm_studio_cfg["url"], lms_path=self._lm_studio_cfg["lms_path"])
        self._latest_control_status: Optional[Dict[str, Any]] = None

    @staticmethod
    def _requires_confirmation(action_id: str) -> bool:
        return action_id in {
            "enable_lm_studio_provider",
            "apply_default_lm_studio_url",
            "probe_provider_health",
            "start_lm_studio_server",
            "stop_lm_studio_server",
        }

    @staticmethod
    def _build_action_plan(providers: List[ProviderStatus], recommendation: Dict[str, Any]) -> Dict[str, Any]:
        signals: List[str] = []
        notes: List[str] = []
        available = [p for p in providers if p.available]
        lm = next((p for p in providers if p.name == "lm_studio"), None)
        if available:
            signals.append("provider_reachable")
            notes.append("At least one local provider is reachable.")
            consent_required = False
            status = "no_action_needed"
        else:
            if lm and lm.reason == "disabled_in_config":
                signals.append("provider_disabled_in_config")
                notes.append("LM Studio is disabled in config.")
                status = "provider_disabled_in_config"
            elif lm:
                signals.append("provider_configured_but_unreachable")
                notes.append(f"LM Studio configured but unreachable ({lm.reason}).")
                status = "provider_configured_but_unreachable"
            else:
                signals.append("runtime_missing")
                notes.append("No runtime provider is currently configured/detected.")
                status = "runtime_missing"
            signals.append("user_consent_required_for_next_step")
            consent_required = True
        if recommendation.get("recommended_model_posture"):
            signals.append("model_posture_recommended_but_not_verified")
            notes.append("Model posture is advisory and not execution-verified in this phase.")
        return {
            "status": status,
            "signals": signals,
            "consent_required": consent_required,
            "planned_next_step": "read_only_planning_only",
            "notes": notes,
        }

    def _build_runtime_control_capability(self, providers: List[ProviderStatus]) -> Dict[str, Any]:
        lm_provider = next((p for p in providers if p.name == "lm_studio"), None)
        provider_reachable_now = bool(lm_provider.available) if lm_provider else False
        lm_enabled = bool(self._lm_studio_cfg.get("enabled", False))
        cli_probe = self._control_adapter.detect_cli()
        lms_cli_detected = bool(cli_probe.get("lms_cli_detected", False))
        control_execution_supported = bool(lm_provider and lm_enabled and lms_cli_detected)
        blockers: List[Dict[str, str]] = []
        if lm_provider:
            blockers.extend([
                {"seam": "LMStudioService.__init__", "reason": "Instantiating enabled service can mutate machine state."},
                {"seam": "LMStudioService._find_lms_cli", "reason": "Missing CLI path can call auto-install in legacy service."},
                {"seam": "LMStudioService._ensure_server_running", "reason": "Legacy service can execute runtime-control side effects."},
            ])
        if not lm_enabled:
            blockers.append({"seam": "lm_studio.enabled", "reason": "LM Studio provider is disabled in config; bounded control actions remain hidden."})
        if not lms_cli_detected:
            blockers.append({"seam": "LMStudioControlAdapter.detect_cli", "reason": "lms CLI was not detected locally; no install is attempted by Runtime Advisor."})
        if control_execution_supported:
            blockers.append({
                "seam": "runtime_state",
                "reason": "LM Studio is currently reachable; start action is hidden and stop action is exposable." if provider_reachable_now else "LM Studio is currently unreachable; stop action is hidden and start action is exposable.",
            })
        return {
            "runtime_control_supported": control_execution_supported,
            "control_execution_supported": control_execution_supported,
            "start_supported": bool(control_execution_supported and not provider_reachable_now),
            "stop_supported": bool(control_execution_supported and provider_reachable_now),
            "start_action_exposable": bool(control_execution_supported and not provider_reachable_now),
            "stop_action_exposable": bool(control_execution_supported and provider_reachable_now),
            "advisory_probe_supported": True,
            "safe_control_seam_available": True,
            "lms_cli_detected": lms_cli_detected,
            "lms_cli_path": str(cli_probe.get("lms_cli_path", "")),
            "provider_reachable_now": provider_reachable_now,
            "explicit_confirmation_required_for_control": True,
            "limitations": ["Legacy LMStudioService control path remains intentionally isolated."],
            "blockers": blockers,
            "provider_scope": [p.name for p in providers],
        }

    def _build_available_actions(self, action_plan: Dict[str, Any], capability: Dict[str, Any]) -> List[Dict[str, Any]]:
        signals = set(action_plan.get("signals", []))
        actions = [
            {"id": "recheck_provider", "label": "Re-check provider status", "requires_confirmation": False, "mutates_config": False},
            {"id": "probe_provider_health", "label": "Run provider health/details probe", "requires_confirmation": True, "mutates_config": False},
        ]
        if "provider_disabled_in_config" in signals:
            actions.append({"id": "enable_lm_studio_provider", "label": "Enable LM Studio provider in local config", "requires_confirmation": True, "mutates_config": True})
        if "provider_configured_but_unreachable" in signals or "runtime_missing" in signals:
            actions.append({"id": "apply_default_lm_studio_url", "label": "Apply default LM Studio URL in local config", "requires_confirmation": True, "mutates_config": True})
        if capability.get("start_action_exposable"):
            actions.append({"id": "start_lm_studio_server", "label": "Start LM Studio server (bounded control)", "requires_confirmation": True, "mutates_config": False})
        if capability.get("stop_action_exposable"):
            actions.append({"id": "stop_lm_studio_server", "label": "Stop LM Studio server (bounded control)", "requires_confirmation": True, "mutates_config": False})
        return actions

    def _provider_health_probe(self) -> Dict[str, Any]:
        return {"providers": [p.to_dict() for p in self.registry.discover_providers()]}

    def _provider_reachability_now(self) -> bool:
        lm = next((p for p in self.registry.discover_providers() if p.name == "lm_studio"), None)
        return bool(lm.available) if lm else False

    def _build_control_status(self, action: str, control_result: Dict[str, Any]) -> Dict[str, Any]:
        recheck_reachable = self._provider_reachability_now()
        dispatch_executed = bool(control_result.get("executed", False))
        if action == "start_lm_studio_server":
            msg = "Start command dispatched; provider reachable on immediate re-check." if dispatch_executed and recheck_reachable else "Start command dispatched; provider not yet reachable on immediate re-check." if dispatch_executed else "Start command dispatch failed; provider reachable on immediate re-check." if recheck_reachable else "Start command dispatch failed; provider not reachable on immediate re-check."
        else:
            msg = "Stop command dispatched; provider unreachable on immediate re-check." if dispatch_executed and not recheck_reachable else "Stop command dispatched; provider still reachable on immediate re-check." if dispatch_executed else "Stop command dispatch failed; provider unreachable on immediate re-check." if not recheck_reachable else "Stop command dispatch failed; provider still reachable on immediate re-check."
        status = {
            "last_control_action": action,
            "last_control_dispatch_executed": dispatch_executed,
            "last_control_dispatch_reason": str(control_result.get("reason", "unknown")),
            "last_control_recheck_reachable": recheck_reachable,
            "last_control_checked_at_utc": datetime.now(timezone.utc).isoformat(),
            "last_control_message": msg,
        }
        self._latest_control_status = status
        return status

    def _blocked_control_status(self, action: str, msg: str, reachable: bool) -> Dict[str, Any]:
        status = {
            "last_control_action": action,
            "last_control_dispatch_executed": False,
            "last_control_dispatch_reason": "blocked_by_gating_truth",
            "last_control_recheck_reachable": bool(reachable),
            "last_control_checked_at_utc": datetime.now(timezone.utc).isoformat(),
            "last_control_message": msg,
        }
        self._latest_control_status = status
        return status

    def execute_safe_action(self, action_id: str, *, confirmed: bool = False) -> Dict[str, Any]:
        action = str(action_id or "").strip()
        if self._requires_confirmation(action) and not confirmed:
            return {"action": action, "executed": False, "requires_confirmation": True, "mutated_config": False, "message": "Confirmation required before applying this action."}
        try:
            if action == "recheck_provider":
                return {"action": action, "executed": True, "requires_confirmation": False, "mutated_config": False, "message": "Provider check will be refreshed."}
            if action == "probe_provider_health":
                return {"action": action, "executed": True, "requires_confirmation": True, "mutated_config": False, "message": "Provider health/details probe completed.", "diagnostics": self._provider_health_probe()}
            if action == "enable_lm_studio_provider":
                self.config.set("lm_studio.enabled", True, scope="local")
                saved_path = self.config.save(scope="local")
                return {"action": action, "executed": True, "requires_confirmation": True, "mutated_config": True, "message": "LM Studio provider enabled in local config.", "saved_path": saved_path}
            if action == "apply_default_lm_studio_url":
                self.config.set("lm_studio.url", self._default_lm_studio_url, scope="local")
                saved_path = self.config.save(scope="local")
                return {"action": action, "executed": True, "requires_confirmation": True, "mutated_config": True, "message": f"LM Studio URL set to {self._default_lm_studio_url} in local config.", "saved_path": saved_path}
            if action in {"start_lm_studio_server", "stop_lm_studio_server"}:
                providers = self.registry.discover_providers()
                capability = self._build_runtime_control_capability(providers)
                key = "start_action_exposable" if action.startswith("start") else "stop_action_exposable"
                if not capability.get(key, False):
                    msg = "Start action is blocked because LM Studio is already reachable." if action.startswith("start") and capability.get("provider_reachable_now") else "Stop action is blocked because LM Studio is already unreachable." if action.startswith("stop") and not capability.get("provider_reachable_now") else f"{action} is blocked by runtime control gating truth."
                    return {"action": action, "executed": False, "requires_confirmation": True, "mutated_config": False, "message": msg, "blockers": capability.get("blockers", []), "latest_control_status": self._blocked_control_status(action, msg, bool(capability.get("provider_reachable_now", False)))}
                control_result = self._control_adapter.start_server() if action.startswith("start") else self._control_adapter.stop_server()
                status = self._build_control_status(action, control_result)
                return {"action": action, "executed": bool(control_result.get("executed", False)), "requires_confirmation": True, "mutated_config": False, "message": status["last_control_message"], "control_result": control_result, "latest_control_status": status, "execution_path": "LMStudioControlAdapter.start_server" if action.startswith("start") else "LMStudioControlAdapter.stop_server"}
            return {"action": action, "executed": False, "requires_confirmation": False, "mutated_config": False, "message": "Unsupported runtime advisor action."}
        except Exception as e:
            return {"action": action, "executed": False, "requires_confirmation": self._requires_confirmation(action), "mutated_config": False, "message": f"Action failed: {e}"}

    def get_advisory(self) -> Dict[str, Any]:
        profile = HardwareAdvisor.detect_local_profile()
        providers = self.registry.discover_providers()
        rec = RecommendationEngine.recommend(profile, providers)
        plan = self._build_action_plan(providers, rec)
        capability = self._build_runtime_control_capability(providers)
        return {
            "hardware_profile": profile.to_dict(),
            "recommendation": rec,
            "action_plan": plan,
            "available_actions": self._build_available_actions(plan, capability),
            "runtime_control_capability": capability,
            "latest_control_status": dict(self._latest_control_status or {}),
        }
