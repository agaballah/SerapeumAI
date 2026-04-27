# -*- coding: utf-8 -*-
"""
Runtime Platform UI presenter.

Turns the read-only runtime platform read-model into short UI-safe text.

This presenter is display-only:
- no provider probing
- no provider mutation
- no download/load/install
- no persistence
"""

from __future__ import annotations

from typing import Any, Dict


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except Exception:
        return 0


def _summary_label(summary_status: str) -> str:
    if summary_status == "provider_reachable_model_not_verified":
        return "Runtime: provider reachable - model not verified"
    if summary_status == "no_provider_reachable":
        return "Runtime: no local provider reachable"
    if summary_status == "provider_discovery_unavailable":
        return "Runtime: discovery unavailable"
    return "Runtime: status unavailable"


def _profile_label(profile_class: str, model_posture: str) -> str:
    profile = str(profile_class or "unknown").replace("_", " ").title()
    posture = str(model_posture or "").replace("_", " ").strip()
    if posture:
        return f"{profile} profile / {posture}"
    return f"{profile} profile"


def present_runtime_platform_sidebar(read_model: Dict[str, Any]) -> Dict[str, str]:
    runtime_status = read_model.get("runtime_status") if isinstance(read_model, dict) else {}
    recommendation = read_model.get("model_recommendation") if isinstance(read_model, dict) else {}

    if not isinstance(runtime_status, dict):
        runtime_status = {}
    if not isinstance(recommendation, dict):
        recommendation = {}

    summary_status = str(runtime_status.get("summary_status") or "")
    provider_count = _safe_int(runtime_status.get("provider_count"))
    reachable_count = _safe_int(runtime_status.get("reachable_provider_count"))

    profile_class = str(recommendation.get("profile_class") or "unknown")
    model_posture = str(recommendation.get("model_posture") or "")

    primary = _summary_label(summary_status)
    secondary = f"Providers: {reachable_count}/{provider_count} reachable. Recommendation: {_profile_label(profile_class, model_posture)}."

    if summary_status == "provider_reachable_model_not_verified":
        tone = "warning"
        detail = "A local provider is reachable, but model/task readiness has not been proven."
    elif summary_status == "no_provider_reachable":
        tone = "warning"
        detail = "No local provider is reachable. AI features may remain unavailable."
    elif summary_status == "provider_discovery_unavailable":
        tone = "error"
        detail = "Runtime discovery did not return provider information."
    else:
        tone = "muted"
        detail = "Runtime platform status is unavailable."

    return {
        "primary": primary,
        "secondary": secondary,
        "detail": detail,
        "tone": tone,
    }
