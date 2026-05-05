# -*- coding: utf-8 -*-
"""
Runtime Manager selection presenter.

Turns the Upgrade 3S runtime platform read model into UI-safe provider,
mode, and model choices for the Runtime Manager dialog.

Presenter only:
- no provider probing
- no config mutation
- no install/start/stop/download/load/unload
- no project data sent
"""

from __future__ import annotations

from typing import Any, Dict, List

from src.infra.services.runtime_provider_discovery import (
    PROVIDER_MODE_DISABLED_LOCAL_REVIEW_ONLY,
)


def _safe_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _provider_label(row: Dict[str, Any]) -> str:
    name = str(row.get("provider_name") or "").strip()
    mode_label = str(row.get("provider_mode_label") or row.get("provider_mode") or "").strip()
    status = str(row.get("display_status") or row.get("status") or "").strip()
    parts = [name]
    if mode_label:
        parts.append(mode_label)
    if status:
        parts.append(status)
    return " | ".join(part for part in parts if part)


def _model_values(models: List[Dict[str, Any]]) -> List[str]:
    values: List[str] = []
    seen: set[str] = set()
    for row in models:
        if not isinstance(row, dict):
            continue
        model_id = str(row.get("model_id") or row.get("model_key") or row.get("id") or row.get("name") or "").strip()
        if not model_id or model_id in seen:
            continue
        seen.add(model_id)
        values.append(model_id)
    return values


def present_runtime_manager_selection(read_model: Dict[str, Any]) -> Dict[str, Any]:
    """Return deterministic provider/mode/model options for the Runtime Manager UI."""
    if not isinstance(read_model, dict):
        read_model = {}

    runtime_status = read_model.get("runtime_status") if isinstance(read_model.get("runtime_status"), dict) else {}
    provider_rows = _safe_list(runtime_status.get("providers"))
    discovery_rows = _safe_list(read_model.get("provider_discovery"))

    # Prefer presented rows because they include display labels; fall back to raw discovery rows.
    rows = [row for row in provider_rows if isinstance(row, dict)] or [row for row in discovery_rows if isinstance(row, dict)]

    providers: List[Dict[str, str]] = []
    for row in rows:
        provider_name = str(row.get("provider_name") or "").strip()
        if not provider_name:
            continue
        providers.append(
            {
                "value": provider_name,
                "label": _provider_label(row),
                "status": str(row.get("status") or ""),
                "provider_mode": str(row.get("provider_mode") or ""),
            }
        )

    selected_provider = str(read_model.get("selected_provider") or "local_review_only").strip()
    selected_provider_mode = str(read_model.get("selected_provider_mode") or PROVIDER_MODE_DISABLED_LOCAL_REVIEW_ONLY).strip()
    selected_chat_model = str(read_model.get("selected_chat_model") or "").strip()
    selected_analysis_model = str(read_model.get("selected_analysis_model") or "").strip()

    selected_row = None
    for row in rows:
        if str(row.get("provider_name") or "").strip() == selected_provider:
            selected_row = row
            break

    mode_values = []
    if selected_row:
        mode_values = [str(mode) for mode in _safe_list(selected_row.get("provider_modes_supported")) if str(mode or "").strip()]
    if selected_provider_mode and selected_provider_mode not in mode_values:
        mode_values.insert(0, selected_provider_mode)
    if not mode_values:
        mode_values = [PROVIDER_MODE_DISABLED_LOCAL_REVIEW_ONLY]

    available_models = _safe_list(read_model.get("available_models"))
    if not available_models and selected_row:
        available_models = _safe_list(selected_row.get("listed_models"))
    model_values = _model_values([row for row in available_models if isinstance(row, dict)])

    if selected_chat_model and selected_chat_model not in model_values:
        model_values.insert(0, selected_chat_model)
    if selected_analysis_model and selected_analysis_model not in model_values:
        model_values.insert(0, selected_analysis_model)

    no_models_label = "No local models listed"
    model_choices = model_values or [no_models_label]

    recommendation = read_model.get("model_recommendation") if isinstance(read_model.get("model_recommendation"), dict) else {}
    profile = str(recommendation.get("profile_class") or "unknown").replace("_", " ").title()
    posture = str(recommendation.get("model_posture") or "").replace("_", " ")
    recommendation_summary = f"{profile} profile"
    if posture:
        recommendation_summary = f"{recommendation_summary} / {posture}"

    return {
        "providers": providers,
        "provider_values": [row["value"] for row in providers] or ["local_review_only"],
        "selected_provider": selected_provider,
        "provider_mode_values": mode_values,
        "selected_provider_mode": selected_provider_mode,
        "model_values": model_choices,
        "selected_chat_model": selected_chat_model or model_choices[0],
        "selected_analysis_model": selected_analysis_model or model_choices[0],
        "no_models_label": no_models_label,
        "model_selection_ready": bool(read_model.get("model_selection_ready", False)),
        "model_readiness": str(read_model.get("model_readiness") or "not_verified"),
        "recommendation_summary": recommendation_summary,
        "side_effects": {
            "internet_used": False,
            "install_attempted": False,
            "start_attempted": False,
            "stop_attempted": False,
            "download_attempted": False,
            "model_load_attempted": False,
            "model_unload_attempted": False,
            "config_mutated": False,
            "project_data_sent": False,
        },
    }
