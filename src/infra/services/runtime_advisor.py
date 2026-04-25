# -*- coding: utf-8 -*-
"""
Runtime advisor: read-only provider discovery, hardware profiling,
and deterministic recommendation output.

Advisory discovery in this module is read-only.
Explicit start and stop actions may be executed only through bounded,
user-confirmed control paths.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Protocol
from urllib import error, request

from src.infra.services.benchmark_service import get_machine_hardware_snapshot
from src.infra.services.lm_studio_control_adapter import LMStudioControlAdapter

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProviderStatus:
    name: str
    available: bool
    endpoint: str
    reason: str = ""
    capabilities: List[str] = None

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
            return ProviderStatus(
                name=self.name,
                available=False,
                endpoint=self.url,
                reason="disabled_in_config",
                capabilities=[],
            )
        try:
            req = request.Request(f"{self.url}/v1/models", method="GET")
            with request.urlopen(req, timeout=1.5) as resp:
                code = getattr(resp, "status", 200)
            if 200 <= int(code) < 300:
                return ProviderStatus(
                    name=self.name,
                    available=True,
                    endpoint=self.url,
                    reason="reachable",
                    capabilities=["chat_completions", "model_listing", "local_runtime"],
                )
            return ProviderStatus(
                name=self.name,
                available=False,
                endpoint=self.url,
                reason=f"http_{code}",
                capabilities=[],
            )
        except error.HTTPError as e:
            return ProviderStatus(
                name=self.name,
                available=False,
                endpoint=self.url,
                reason=f"http_{getattr(e, 'code', 'error')}",
                capabilities=[],
            )
        except Exception as e:
            return ProviderStatus(
                name=self.name,
                available=False,
                endpoint=self.url,
                reason=f"unreachable:{type(e).__name__}",
                capabilities=[],
            )


class ProviderRegistry:
    def __init__(self, adapters: Optional[List[ProviderAdapter]] = None):
        self.adapters = list(adapters or [])

    @classmethod
    def from_config(cls, config) -> "ProviderRegistry":
        lm_cfg = (config.get_section("lm_studio") or {}) if config else {}
        adapter = LMStudioProviderAdapter(
            enabled=bool(lm_cfg.get("enabled", False)),
            url=str(lm_cfg.get("url", "http://127.0.0.1:1234")),
        )
        return cls(adapters=[adapter])

    def discover_providers(self) -> List[ProviderStatus]:
        out: List[ProviderStatus] = []
        for adapter in self.adapters:
            try:
                out.append(adapter.discover())
            except Exception as e:
                logger.warning(f"[ProviderRegistry] discover failed for {getattr(adapter, 'name', 'unknown')}: {e}")
        return sorted(out, key=lambda p: p.name)


class HardwareAdvisor:
    @staticmethod
    def _detect_ram_mb() -> int:
        try:
            pages = os.sysconf("SC_PHYS_PAGES")
            page_size = os.sysconf("SC_PAGE_SIZE")
            if pages and page_size:
                return int((pages * page_size) / (1024 * 1024))
        except Exception:
            pass
        try:
            import psutil  # type: ignore
            return int(psutil.virtual_memory().total / (1024 * 1024))
        except Exception:
            return 0

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
        hw_class = cls.classify_hardware(vram_total_mb=vram_total_mb, ram_total_mb=ram_total_mb, gpu_available=gpu_available)
        return HardwareProfile(
            hardware_class=hw_class,
            gpu_available=bool(gpu_available),
            gpu_name=str(gpu_name or "unknown"),
            vram_total_mb=int(vram_total_mb or 0),
            ram_total_mb=int(ram_total_mb or 0),
            os_name=str(os_name or "unknown"),
            detection_method="snapshot",
        )

    @staticmethod
    def classify_hardware(*, vram_total_mb: int, ram_total_mb: int, gpu_available: bool) -> str:
        if (not gpu_available) or vram_total_mb < 4096 or ram_total_mb < 16000:
            return "CONSERVATIVE"
        if vram_total_mb >= 12288 and ram_total_mb >= 32000:
            return "PERFORMANCE"
        return "BALANCED"

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
            ram_total_mb=int(snap.get("ram_total_mb", cls._detect_ram_mb())),
            os_name=str(snap.get("os_name", os.name)),
        )
        return HardwareProfile(
            hardware_class=profile.hardware_class,
            gpu_available=profile.gpu_available,
            gpu_name=profile.gpu_name,
            vram_total_mb=profile.vram_total_mb,
            ram_total_mb=profile.ram_total_mb,
            os_name=profile.os_name,
            detection_method=str(snap.get("detection_method", "snapshot")),
        )


class RecommendationEngine:
    @staticmethod
    def recommend(profile: HardwareProfile, providers: List[ProviderStatus]) -> Dict[str, Any]:
        available_names = [p.name for p in providers if p.available]
        has_lm_studio = "lm_studio" in available_names

        profile_class = profile.hardware_class
        if profile_class == "PERFORMANCE":
            model_posture = "high_quality_7b_to_14b_quantized"
            runtime_posture = "local_high_throughput"
        elif profile_class == "BALANCED":
            model_posture = "balanced_7b_quantized"
            runtime_posture = "local_balanced"
        else:
            model_posture = "small_low_vram_models"
            runtime_posture = "local_conservative"

        warnings: List[str] = []
        constraints: List[str] = []

        if not has_lm_studio:
            warnings.append("No reachable local runtime provider detected.")
            constraints.append("Runtime remains advisory-only until provider is reachable.")
        if profile.vram_total_mb < 4096:
            warnings.append("Low VRAM detected; avoid vision-heavy profiles.")
        if profile.ram_total_mb and profile.ram_total_mb < 16000:
            warnings.append("System RAM below 16 GB may limit large context usage.")

        return {
            "detected_providers": [p.to_dict() for p in providers],
            "recommended_profile_class": profile_class,
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
        self._control_adapter = LMStudioControlAdapter(
            url=self._lm_studio_cfg["url"],
            lms_path=self._lm_studio_cfg["lms_path"],
        )
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
        consent_required = False

        available = [p for p in providers if p.available]
        lm = next((p for p in providers if p.name == "lm_studio"), None)

        if available:
            signals.append("provider_reachable")
            notes.append("At least one local provider is reachable.")
        else:
            if lm and lm.reason == "disabled_in_config":
                signals.append("provider_disabled_in_config")
                notes.append("LM Studio is disabled in config.")
            elif lm:
                signals.append("provider_configured_but_unreachable")
                notes.append(f"LM Studio configured but unreachable ({lm.reason}).")
            else:
                signals.append("runtime_missing")
                notes.append("No runtime provider is currently configured or detected.")

        if recommendation.get("recommended_model_posture"):
            signals.append("model_posture_recommended_but_not_verified")
            notes.append("Model posture is advisory and not execution-verified in this phase.")

        action_needed_markers = {
            "provider_configured_but_unreachable",
            "provider_disabled_in_config",
            "runtime_missing",
        }
        if any(s in action_needed_markers for s in signals):
            signals.append("user_consent_required_for_next_step")
            consent_required = True

        status = "no_action_needed" if not consent_required else next(
            (s for s in signals if s in action_needed_markers),
            "runtime_missing",
        )

        return {
            "status": status,
            "signals": signals,
            "consent_required": consent_required,
            "planned_next_step": "read_only_planning_only",
            "notes": notes,
        }

    def _build_available_actions(self, action_plan: Dict[str, Any], runtime_control_capability: Dict[str, Any]) -> List[Dict[str, Any]]:
        signals = set(action_plan.get("signals", []) if isinstance(action_plan, dict) else [])
        actions: List[Dict[str, Any]] = [
            {
                "id": "recheck_provider",
                "label": "Re-check provider status",
                "requires_confirmation": False,
                "mutates_config": False,
            },
            {
                "id": "probe_provider_health",
                "label": "Run provider health/details probe",
                "requires_confirmation": True,
                "mutates_config": False,
            },
        ]
        if "provider_disabled_in_config" in signals:
            actions.append(
                {
                    "id": "enable_lm_studio_provider",
                    "label": "Enable LM Studio provider in local config",
                    "requires_confirmation": True,
                    "mutates_config": True,
                }
            )
        if "provider_configured_but_unreachable" in signals or "runtime_missing" in signals:
            actions.append(
                {
                    "id": "apply_default_lm_studio_url",
                    "label": "Apply default LM Studio URL in local config",
                    "requires_confirmation": True,
                    "mutates_config": True,
                }
            )
        if bool(runtime_control_capability.get("start_action_exposable", False)):
            actions.append(
                {
                    "id": "start_lm_studio_server",
                    "label": "Start LM Studio server (bounded control)",
                    "requires_confirmation": True,
                    "mutates_config": False,
                }
            )
        if bool(runtime_control_capability.get("stop_action_exposable", False)):
            actions.append(
                {
                    "id": "stop_lm_studio_server",
                    "label": "Stop LM Studio server (bounded control)",
                    "requires_confirmation": True,
                    "mutates_config": False,
                }
            )
        return actions

    def _build_runtime_control_capability(self, providers: List[ProviderStatus]) -> Dict[str, Any]:
        provider_names = [p.name for p in providers]
        lm_provider = next((p for p in providers if p.name == "lm_studio"), None)
        has_lm_studio = lm_provider is not None
        provider_reachable_now = bool(lm_provider.available) if lm_provider else False
        lm_enabled = bool(self._lm_studio_cfg.get("enabled", False))
        cli_probe = self._control_adapter.detect_cli()
        lms_cli_detected = bool(cli_probe.get("lms_cli_detected", False))

        limitations: List[str] = []
        blockers: List[Dict[str, str]] = []
        control_paths = {
            "advisory_probe_path": "LMStudioProviderAdapter.discover -> HTTP GET /v1/models",
            "control_path_status": "safe_seam_extracted_conditionally_exposed",
            "control_path_reference": "LMStudioControlAdapter provides explicit control methods with no install/autostart during construction",
            "legacy_control_path_reference": "LMStudioService is intentionally not used for control actions here",
        }

        if has_lm_studio:
            limitations.append("Legacy LMStudioService control path remains intentionally isolated.")
            blockers.extend(
                [
                    {
                        "seam": "LMStudioService.__init__",
                        "reason": "Instantiating enabled service can mutate local machine state.",
                    },
                    {
                        "seam": "LMStudioService._find_lms_cli",
                        "reason": "This path is intentionally isolated from Runtime Advisor actions.",
                    },
                    {
                        "seam": "LMStudioService._ensure_server_running",
                        "reason": "This path can change runtime state and is intentionally isolated.",
                    },
                ]
            )
        else:
            limitations.append("No LM Studio provider configured; control execution cannot be exposed.")
            blockers.append(
                {
                    "seam": "ProviderRegistry.from_config",
                    "reason": "No lm_studio provider configured; no bounded control seam is available to expose.",
                }
            )
        if not lm_enabled:
            blockers.append(
                {
                    "seam": "lm_studio.enabled",
                    "reason": "LM Studio provider is disabled in config; bounded control actions remain hidden.",
                }
            )
        if not lms_cli_detected:
            blockers.append(
                {
                    "seam": "LMStudioControlAdapter.detect_cli",
                    "reason": "lms CLI was not detected locally; no install is attempted by Runtime Advisor.",
                }
            )

        control_execution_supported = bool(has_lm_studio and lm_enabled and lms_cli_detected)
        start_action_exposable = bool(control_execution_supported and not provider_reachable_now)
        stop_action_exposable = bool(control_execution_supported and provider_reachable_now)

        if control_execution_supported and provider_reachable_now:
            blockers.append(
                {
                    "seam": "runtime_state",
                    "reason": "LM Studio is currently reachable; start action is hidden and stop action is exposable.",
                }
            )
        if control_execution_supported and not provider_reachable_now:
            blockers.append(
                {
                    "seam": "runtime_state",
                    "reason": "LM Studio is currently unreachable; stop action is hidden and start action is exposable.",
                }
            )

        return {
            "runtime_control_supported": control_execution_supported,
            "control_execution_supported": control_execution_supported,
            "start_supported": start_action_exposable,
            "stop_supported": stop_action_exposable,
            "start_action_exposable": start_action_exposable,
            "stop_action_exposable": stop_action_exposable,
            "advisory_probe_supported": True,
            "safe_control_seam_available": True,
            "lms_cli_detected": lms_cli_detected,
            "lms_cli_path": str(cli_probe.get("lms_cli_path", "")),
            "provider_reachable_now": provider_reachable_now,
            "explicit_confirmation_required_for_control": True,
            "limitations": limitations,
            "blockers": blockers,
            "provider_scope": provider_names,
            "paths": control_paths,
        }

    def _provider_health_probe(self) -> Dict[str, Any]:
        providers = self.registry.discover_providers()
        details = []
        for p in providers:
            details.append(
                {
                    "name": p.name,
                    "endpoint": p.endpoint,
                    "available": p.available,
                    "reason": p.reason,
                    "capabilities": list(p.capabilities or []),
                }
            )
        return {"providers": details}

    def _provider_reachability_now(self) -> bool:
        providers = self.registry.discover_providers()
        lm = next((p for p in providers if p.name == "lm_studio"), None)
        return bool(lm.available) if lm else False

    def _build_control_status(self, action: str, control_result: Dict[str, Any]) -> Dict[str, Any]:
        recheck_reachable = self._provider_reachability_now()
        dispatch_executed = bool(control_result.get("executed", False))
        dispatch_reason = str(control_result.get("reason", "unknown"))
        checked_at_utc = datetime.now(timezone.utc).isoformat()

        if action == "start_lm_studio_server":
            if dispatch_executed and recheck_reachable:
                msg = "Start command dispatched; provider reachable on immediate re-check."
            elif dispatch_executed and not recheck_reachable:
                msg = "Start command dispatched; provider not yet reachable on immediate re-check."
            elif not dispatch_executed and recheck_reachable:
                msg = "Start command dispatch failed; provider reachable on immediate re-check."
            else:
                msg = "Start command dispatch failed; provider not reachable on immediate re-check."
        else:
            if dispatch_executed and not recheck_reachable:
                msg = "Stop command dispatched; provider unreachable on immediate re-check."
            elif dispatch_executed and recheck_reachable:
                msg = "Stop command dispatched; provider still reachable on immediate re-check."
            elif not dispatch_executed and not recheck_reachable:
                msg = "Stop command dispatch failed; provider unreachable on immediate re-check."
            else:
                msg = "Stop command dispatch failed; provider still reachable on immediate re-check."

        status = {
            "last_control_action": action,
            "last_control_dispatch_executed": dispatch_executed,
            "last_control_dispatch_reason": dispatch_reason,
            "last_control_recheck_reachable": recheck_reachable,
            "last_control_checked_at_utc": checked_at_utc,
            "last_control_message": msg,
        }
        self._latest_control_status = status
        return status

    def execute_safe_action(self, action_id: str, *, confirmed: bool = False) -> Dict[str, Any]:
        action = str(action_id or "").strip()
        requires_confirmation = self._requires_confirmation(action)
        if requires_confirmation and not confirmed:
            return {
                "action": action,
                "executed": False,
                "requires_confirmation": requires_confirmation,
                "mutated_config": False,
                "message": "Confirmation required before applying this action.",
            }

        try:
            if action == "recheck_provider":
                return {
                    "action": action,
                    "executed": True,
                    "requires_confirmation": False,
                    "mutated_config": False,
                    "message": "Provider check will be refreshed.",
                }

            if action == "probe_provider_health":
                probe = self._provider_health_probe()
                return {
                    "action": action,
                    "executed": True,
                    "requires_confirmation": True,
                    "mutated_config": False,
                    "message": "Provider health/details probe completed.",
                    "diagnostics": probe,
                }

            if action == "enable_lm_studio_provider":
                self.config.set("lm_studio.enabled", True, scope="local")
                saved_path = self.config.save(scope="local")
                return {
                    "action": action,
                    "executed": True,
                    "requires_confirmation": True,
                    "mutated_config": True,
                    "message": "LM Studio provider enabled in local config.",
                    "saved_path": saved_path,
                }

            if action == "apply_default_lm_studio_url":
                self.config.set("lm_studio.url", self._default_lm_studio_url, scope="local")
                saved_path = self.config.save(scope="local")
                return {
                    "action": action,
                    "executed": True,
                    "requires_confirmation": True,
                    "mutated_config": True,
                    "message": f"LM Studio URL set to {self._default_lm_studio_url} in local config.",
                    "saved_path": saved_path,
                }

            if action == "start_lm_studio_server":
                providers = self.registry.discover_providers()
                capability = self._build_runtime_control_capability(providers)
                if not capability.get("start_action_exposable", False):
                    msg = "Start action is blocked by runtime control gating truth."
                    if capability.get("provider_reachable_now", False):
                        msg = "Start action is blocked because LM Studio is already reachable."
                    blocked_status = {
                        "last_control_action": action,
                        "last_control_dispatch_executed": False,
                        "last_control_dispatch_reason": "blocked_by_gating_truth",
                        "last_control_recheck_reachable": bool(capability.get("provider_reachable_now", False)),
                        "last_control_checked_at_utc": datetime.now(timezone.utc).isoformat(),
                        "last_control_message": msg,
                    }
                    self._latest_control_status = blocked_status
                    return {
                        "action": action,
                        "executed": False,
                        "requires_confirmation": True,
                        "mutated_config": False,
                        "message": msg,
                        "blockers": capability.get("blockers", []),
                        "latest_control_status": blocked_status,
                    }
                control_result = self._control_adapter.start_server()
                control_status = self._build_control_status(action, control_result)
                return {
                    "action": action,
                    "executed": bool(control_result.get("executed", False)),
                    "requires_confirmation": True,
                    "mutated_config": False,
                    "message": "LM Studio start command dispatched via bounded control adapter." if control_result.get("executed") else "LM Studio start command failed via bounded control adapter.",
                    "control_result": control_result,
                    "latest_control_status": control_status,
                    "execution_path": "LMStudioControlAdapter.start_server",
                }

            if action == "stop_lm_studio_server":
                providers = self.registry.discover_providers()
                capability = self._build_runtime_control_capability(providers)
                if not capability.get("stop_action_exposable", False):
                    msg = "Stop action is blocked by runtime control gating truth."
                    if not capability.get("provider_reachable_now", False):
                        msg = "Stop action is blocked because LM Studio is already unreachable."
                    blocked_status = {
                        "last_control_action": action,
                        "last_control_dispatch_executed": False,
                        "last_control_dispatch_reason": "blocked_by_gating_truth",
                        "last_control_recheck_reachable": bool(capability.get("provider_reachable_now", False)),
                        "last_control_checked_at_utc": datetime.now(timezone.utc).isoformat(),
                        "last_control_message": msg,
                    }
                    self._latest_control_status = blocked_status
                    return {
                        "action": action,
                        "executed": False,
                        "requires_confirmation": True,
                        "mutated_config": False,
                        "message": msg,
                        "blockers": capability.get("blockers", []),
                        "latest_control_status": blocked_status,
                    }
                control_result = self._control_adapter.stop_server()
                control_status = self._build_control_status(action, control_result)
                return {
                    "action": action,
                    "executed": bool(control_result.get("executed", False)),
                    "requires_confirmation": True,
                    "mutated_config": False,
                    "message": "LM Studio stop command dispatched via bounded control adapter." if control_result.get("executed") else "LM Studio stop command failed via bounded control adapter.",
                    "control_result": control_result,
                    "latest_control_status": control_status,
                    "execution_path": "LMStudioControlAdapter.stop_server",
                }

            return {
                "action": action,
                "executed": False,
                "requires_confirmation": False,
                "mutated_config": False,
                "message": "Unsupported runtime advisor action.",
            }
        except Exception as e:
            return {
                "action": action,
                "executed": False,
                "requires_confirmation": requires_confirmation,
                "mutated_config": False,
                "message": f"Action failed: {e}",
            }

    def get_advisory(self) -> Dict[str, Any]:
        profile = HardwareAdvisor.detect_local_profile()
        providers = self.registry.discover_providers()
        rec = RecommendationEngine.recommend(profile, providers)
        action_plan = self._build_action_plan(providers, rec)
        runtime_control_capability = self._build_runtime_control_capability(providers)
        available_actions = self._build_available_actions(action_plan, runtime_control_capability)
        return {
            "hardware_profile": profile.to_dict(),
            "recommendation": rec,
            "action_plan": action_plan,
            "available_actions": available_actions,
            "runtime_control_capability": runtime_control_capability,
            "latest_control_status": dict(self._latest_control_status or {}),
        }
