# -*- coding: utf-8 -*-
"""
Runtime Wizard read-model presenter.

Transforms the existing runtime platform read-model dictionary into
deterministic display sections for a future wizard surface.

Presenter only:
- no UI imports
- no provider probing
- no config mutation
- no runtime actions
- no benchmarks
"""

from __future__ import annotations

from typing import Any, Mapping


SECTION_ORDER = (
    "status",
    "provider",
    "model_selection",
    "recommendation",
    "consent_side_effects",
    "next_steps",
)


def _safe_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _safe_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    return []


def _text(value: Any, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else default


def _number(value: Any) -> int:
    try:
        return int(value or 0)
    except Exception:
        return 0


def _bool_fact(value: Any) -> bool:
    return bool(value) if isinstance(value, bool) else False


def _section(section_id: str, title: str, status: str, summary: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "id": section_id,
        "title": title,
        "status": status,
        "summary": summary,
        "rows": rows,
    }


def _status_section(runtime_status: Mapping[str, Any]) -> dict[str, Any]:
    summary_status = _text(runtime_status.get("summary_status"), "unknown")
    provider_count = _number(runtime_status.get("provider_count"))
    reachable_count = _number(runtime_status.get("reachable_provider_count"))

    if summary_status == "provider_reachable_model_not_verified":
        status = "needs_model_verification"
        summary = "A provider is reachable, but model/task readiness is not verified."
    elif summary_status == "no_provider_reachable":
        status = "not_ready"
        summary = "No local provider is reachable."
    elif summary_status == "provider_discovery_unavailable":
        status = "unknown"
        summary = "Runtime discovery did not return provider information."
    else:
        status = "unknown"
        summary = "Runtime platform status is unknown."

    return _section(
        "status",
        "Status",
        status,
        summary,
        [
            {"label": "Summary status", "value": summary_status},
            {"label": "Reachable providers", "value": f"{reachable_count}/{provider_count}"},
        ],
    )


def _provider_section(read_model: Mapping[str, Any], runtime_status: Mapping[str, Any]) -> dict[str, Any]:
    selected_provider = _text(read_model.get("selected_provider"), "local_review_only")
    selected_mode = _text(read_model.get("selected_provider_mode"), "unknown")
    providers = [
        row
        for row in _safe_list(runtime_status.get("providers"))
        if isinstance(row, Mapping)
    ]

    rows: list[dict[str, Any]] = [
        {"label": "Selected provider", "value": selected_provider},
        {"label": "Selected provider mode", "value": selected_mode},
    ]
    for provider in providers:
        name = _text(provider.get("provider_name"), "unknown")
        provider_status = _text(provider.get("display_status") or provider.get("status"), "unknown")
        mode_label = _text(provider.get("provider_mode_label") or provider.get("provider_mode"), "unknown")
        rows.append(
            {
                "label": name,
                "value": provider_status,
                "detail": mode_label,
            }
        )

    status = "not_ready" if selected_provider == "local_review_only" else "display_only"
    summary = (
        "Provider information is display-only. No provider action is performed."
    )
    if not providers and selected_provider == "local_review_only":
        summary = "No provider details were supplied. Runtime remains not ready for model-backed work."

    return _section("provider", "Provider", status, summary, rows)


def _model_selection_section(read_model: Mapping[str, Any]) -> dict[str, Any]:
    selected_chat = _text(read_model.get("selected_chat_model"), "unknown")
    selected_analysis = _text(read_model.get("selected_analysis_model"), "unknown")
    readiness = _text(read_model.get("model_readiness"), "not_verified")
    selection_ready = _bool_fact(read_model.get("model_selection_ready"))

    models = [
        row
        for row in _safe_list(read_model.get("available_models"))
        if isinstance(row, Mapping)
    ]

    rows: list[dict[str, Any]] = [
        {"label": "Chat model", "value": selected_chat},
        {"label": "Analysis model", "value": selected_analysis},
        {"label": "Model readiness", "value": readiness},
        {"label": "Selection complete", "value": selection_ready},
    ]
    for model in models:
        model_id = _text(model.get("model_id") or model.get("id") or model.get("name"), "unknown")
        display = _text(model.get("display_name"), model_id)
        rows.append({"label": display, "value": model_id})

    status = "selection_present" if selection_ready else "not_ready"
    summary = "Selected model values are shown as configuration facts, not runtime actions."
    if selected_chat == "unknown" or selected_analysis == "unknown":
        summary = "Model selection is incomplete; unknown models are not treated as locally available."

    return _section("model_selection", "Model Selection", status, summary, rows)


def _recommendation_section(read_model: Mapping[str, Any]) -> dict[str, Any]:
    recommendation = _safe_mapping(read_model.get("model_recommendation"))
    profile = _text(recommendation.get("profile_class"), "unknown")
    posture = _text(recommendation.get("model_posture"), "unknown")

    rows: list[dict[str, Any]] = [
        {"label": "Profile", "value": profile},
        {"label": "Posture", "value": posture},
    ]

    for item in _safe_list(recommendation.get("recommended_entries")):
        if not isinstance(item, Mapping):
            continue
        label = _text(item.get("display_name") or item.get("model_id"), "unknown")
        model_id = _text(item.get("model_id"), "unknown")
        role = _text(item.get("role"), "unspecified")
        quantization = _text(item.get("quantization"), "")
        detail = role if not quantization else f"{role} / {quantization}"
        rows.append({"label": label, "value": model_id, "detail": detail})

    for warning in _safe_list(recommendation.get("warnings")):
        text = _text(warning)
        if text:
            rows.append({"label": "Warning", "value": text})

    for constraint in _safe_list(recommendation.get("constraints")):
        text = _text(constraint)
        if text:
            rows.append({"label": "Constraint", "value": text})

    return _section(
        "recommendation",
        "Recommendation",
        "guidance_only",
        "Recommendation data is guidance only; it does not perform runtime actions.",
        rows,
    )


def _consent_side_effects_section(read_model: Mapping[str, Any]) -> dict[str, Any]:
    consent_requirements = [_text(item) for item in _safe_list(read_model.get("consent_requirements")) if _text(item)]
    side_effects = _safe_mapping(read_model.get("side_effects"))

    rows: list[dict[str, Any]] = []
    for item in consent_requirements:
        rows.append({"label": "Consent requirement", "value": item})
    for key in sorted(str(name) for name in side_effects):
        rows.append({"label": key, "value": _bool_fact(side_effects.get(key))})

    if not rows:
        rows.append({"label": "Consent and side effects", "value": "not supplied"})

    return _section(
        "consent_side_effects",
        "Consent / Side Effects",
        "display_only",
        "Consent and side-effect values are displayed facts only; this presenter never executes actions.",
        rows,
    )


def _next_steps_section(sections_by_id: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    status = _text(sections_by_id.get("status", {}).get("status"), "unknown")
    model_status = _text(sections_by_id.get("model_selection", {}).get("status"), "unknown")

    steps: list[str] = []
    if status in {"unknown", "not_ready"}:
        steps.append("Review local provider availability before model-backed work.")
    if model_status == "not_ready":
        steps.append("Select explicit chat and analysis model values before relying on model-backed features.")
    if not steps:
        steps.append("Review the displayed guidance and keep runtime actions user-triggered.")

    rows = [{"label": f"Step {index}", "value": step} for index, step in enumerate(steps, start=1)]
    return _section(
        "next_steps",
        "Next Steps",
        "advisory",
        "Next steps are advisory display text, not executable actions.",
        rows,
    )


def present_runtime_wizard_sections(read_model: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return deterministic wizard display sections from an existing read model."""

    model = _safe_mapping(read_model)
    runtime_status = _safe_mapping(model.get("runtime_status"))

    sections = [
        _status_section(runtime_status),
        _provider_section(model, runtime_status),
        _model_selection_section(model),
        _recommendation_section(model),
        _consent_side_effects_section(model),
    ]
    sections_by_id = {section["id"]: section for section in sections}
    sections.append(_next_steps_section(sections_by_id))

    return {
        "schema_version": 1,
        "source": "runtime_wizard_presenter",
        "executed": False,
        "can_execute": False,
        "section_order": list(SECTION_ORDER),
        "sections": sections,
    }
