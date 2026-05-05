# -*- coding: utf-8 -*-
"""
Runtime status presenter.

Converts read-only runtime provider discovery results into deterministic,
honest status rows for future UI surfaces.

This module is presentation-only:
- no install
- no start/stop
- no download
- no model load/unload
- no config mutation
- no provider probing
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List


SUMMARY_NO_PROVIDER_REACHABLE = "no_provider_reachable"
SUMMARY_PROVIDER_REACHABLE_MODEL_NOT_VERIFIED = "provider_reachable_model_not_verified"
SUMMARY_PROVIDER_DISCOVERY_UNAVAILABLE = "provider_discovery_unavailable"


_STATUS_DISPLAY = {
    "disabled": "Disabled",
    "not_detected": "Not detected",
    "detected": "Detected",
    "reachable": "Reachable",
    "unreachable": "Unreachable",
    "unsupported": "Unsupported",
    "needs_consent": "Needs consent",
}

_PROVIDER_MODE_DISPLAY = {
    "DISABLED_LOCAL_REVIEW_ONLY": "Local review only / AI disabled",
    "LM_STUDIO_MANUAL_OPENAI_COMPAT": "LM Studio manual OpenAI-compatible",
    "LM_STUDIO_CLI_MANAGED": "LM Studio CLI-managed",
    "OLLAMA_LOCAL": "Ollama local",
    "LEGACY_LLAMA_CPP_AVAILABLE_IF_PRESENT": "Legacy llama.cpp if present",
    "OPENAI_COMPATIBLE_LOCAL": "Local OpenAI-compatible endpoint",
}


def _as_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _safe_side_effects(row: Dict[str, Any]) -> Dict[str, bool]:
    value = row.get("side_effects")
    if not isinstance(value, dict):
        return {}

    return {
        "internet_used": bool(value.get("internet_used", False)),
        "install_attempted": bool(value.get("install_attempted", False)),
        "start_attempted": bool(value.get("start_attempted", False)),
        "stop_attempted": bool(value.get("stop_attempted", False)),
        "download_attempted": bool(value.get("download_attempted", False)),
        "model_load_attempted": bool(value.get("model_load_attempted", False)),
        "model_unload_attempted": bool(value.get("model_unload_attempted", False)),
        "config_mutated": bool(value.get("config_mutated", False)),
        "project_data_sent": bool(value.get("project_data_sent", False)),
    }


def _capability_summary(capabilities: Iterable[Any]) -> str:
    caps = [str(item).replace("_", " ").strip() for item in _as_list(capabilities)]
    caps = [item for item in caps if item]
    return ", ".join(caps) if caps else "No capabilities reported"


def _mode_label(mode: str) -> str:
    mode = str(mode or "").strip()
    if not mode:
        return "Provider mode not declared"
    return _PROVIDER_MODE_DISPLAY.get(mode, mode.replace("_", " ").title())


def _safe_listed_models(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    value = row.get("listed_models")
    if not isinstance(value, list):
        return []
    out: List[Dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        model_id = str(item.get("model_id") or item.get("id") or item.get("name") or "").strip()
        if not model_id:
            continue
        copied = dict(item)
        copied.setdefault("model_id", model_id)
        copied.setdefault("display_name", model_id)
        out.append(copied)
    return out


def _status_warning(status: str, reason: str, provider_mode: str = "") -> str:
    status = str(status or "")
    reason = str(reason or "")
    provider_mode = str(provider_mode or "")

    if provider_mode == "DISABLED_LOCAL_REVIEW_ONLY":
        return "AI runtime is disabled for this mode. Deterministic review and evidence surfaces can still be used."
    if status == "reachable":
        return "Provider endpoint is reachable. Model/task readiness is not yet verified."
    if status == "disabled":
        return "Provider is disabled by configuration. This is not an application failure."
    if status == "unreachable":
        return "Provider is configured but unreachable. AI features may remain unavailable until the provider is started by the user."
    if status == "unsupported" and reason == "non_local_endpoint_blocked":
        return "Endpoint is not local and is blocked by the local-first runtime policy."
    if status == "not_detected":
        return "Provider was not detected or no endpoint is configured."
    if status == "needs_consent":
        return "User consent is required before this action can proceed."
    return ""


def _action_hint(status: str, reason: str, provider_mode: str = "") -> str:
    status = str(status or "")
    reason = str(reason or "")
    provider_mode = str(provider_mode or "")

    if provider_mode == "DISABLED_LOCAL_REVIEW_ONLY":
        return "Use this mode when you want deterministic review without model-backed AI features."
    if status == "reachable":
        return "Select or verify a model in a later model-readiness step."
    if status == "disabled":
        return "Enable this provider only if you want SerapeumAI to use it."
    if status == "unreachable":
        return "Open or configure the local provider outside SerapeumAI, then refresh status."
    if status == "unsupported" and reason == "non_local_endpoint_blocked":
        return "Use a localhost endpoint or explicitly configure a future non-local/cloud lane."
    if status == "not_detected":
        return "Install/configure this optional provider only if needed."
    return "No action required."


def present_runtime_provider_rows(discovery_rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    for item in discovery_rows or []:
        if not isinstance(item, dict):
            continue

        provider_name = str(item.get("provider_name") or "unknown")
        endpoint = str(item.get("endpoint") or "")
        status = str(item.get("status") or "unknown")
        reason = str(item.get("reason") or "")
        capabilities = _as_list(item.get("capabilities"))
        side_effects = _safe_side_effects(item)
        details = item.get("details") if isinstance(item.get("details"), dict) else {}
        provider_mode = str(item.get("provider_mode") or details.get("provider_mode") or "").strip()
        provider_modes_supported = _as_list(item.get("provider_modes_supported") or details.get("provider_modes_supported"))
        listed_models = _safe_listed_models(item)

        rows.append(
            {
                "provider_name": provider_name,
                "provider_type": str(item.get("provider_type") or ""),
                "endpoint": endpoint,
                "status": status,
                "display_status": _STATUS_DISPLAY.get(status, status.replace("_", " ").title() if status else "Unknown"),
                "reason": reason,
                "provider_mode": provider_mode,
                "provider_mode_label": _mode_label(provider_mode),
                "provider_modes_supported": [str(mode) for mode in provider_modes_supported if str(mode or "").strip()],
                "listed_models": listed_models,
                "listed_model_count": len(listed_models),
                "capability_summary": _capability_summary(capabilities),
                "warning": _status_warning(status, reason, provider_mode),
                "action_hint": _action_hint(status, reason, provider_mode),
                "available": bool(item.get("available", status == "reachable")),
                "model_readiness": "not_verified",
                "side_effects": side_effects,
                "side_effect_free": not any(side_effects.values()) if side_effects else False,
            }
        )

    return sorted(rows, key=lambda row: (row["provider_name"], row["endpoint"]))


def present_runtime_status(discovery_rows: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    provider_rows = present_runtime_provider_rows(discovery_rows)

    if not provider_rows:
        summary_status = SUMMARY_PROVIDER_DISCOVERY_UNAVAILABLE
        summary_text = "Runtime provider discovery is unavailable."
    elif any(row["available"] for row in provider_rows):
        summary_status = SUMMARY_PROVIDER_REACHABLE_MODEL_NOT_VERIFIED
        summary_text = "At least one local runtime provider is reachable. Model readiness is not yet verified."
    else:
        summary_status = SUMMARY_NO_PROVIDER_REACHABLE
        summary_text = "No local runtime provider is currently reachable."

    return {
        "summary_status": summary_status,
        "summary_text": summary_text,
        "provider_count": len(provider_rows),
        "reachable_provider_count": sum(1 for row in provider_rows if row["available"]),
        "providers": provider_rows,
    }
