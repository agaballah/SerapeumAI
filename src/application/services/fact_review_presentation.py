from __future__ import annotations

import json
import ntpath
import os
from typing import Any, Dict, Iterable, List, Optional


FAMILY_LABELS = {
    "document": "Document",
    "schedule": "Schedule",
    "cost": "Cost",
    "bim": "BIM",
    "compliance": "Compliance",
    "procurement": "Procurement",
    "field": "Field",
    "risk": "Risk",
    "register": "Register",
}

STATUS_META = {
    "CANDIDATE": {
        "label": "Candidate",
        "explanation": "Candidate — machine-produced support awaiting human review before it can govern answers.",
        "actions": "Certify promotes this candidate fact to Human Certified after manual review. Reject marks it as rejected and excluded from trusted use.",
    },
    "VALIDATED": {
        "label": "Validated",
        "explanation": "Validated — system-validated trusted fact. Review it carefully before deciding whether it also needs human certification.",
        "actions": "This fact is already trusted. Certify can elevate it to Human Certified if you want explicit human approval. Reject removes it from trusted use.",
    },
    "HUMAN_CERTIFIED": {
        "label": "Human Certified",
        "explanation": "Human Certified — approved by a reviewer and treated as the strongest trusted fact state.",
        "actions": "This fact is already human certified. Reject only if you want to explicitly withdraw it from trusted use.",
    },
    "REJECTED": {
        "label": "Rejected",
        "explanation": "Rejected — excluded from trusted use and should not govern answers.",
        "actions": "A rejected fact should remain rejected unless it is rebuilt or corrected outside this review packet.",
    },
}

INPUT_KIND_LABELS = {
    "deterministic": "Deterministic extraction",
    "structured": "Structured source",
    "ocr": "OCR / parser extraction",
    "parser": "OCR / parser extraction",
    "table": "Structured source",
    "graph": "Linked support",
    "analysis": "AI-supported origin",
    "ai": "AI-supported origin",
}


def _safe_json(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    if value in (None, ""):
        return None
    if isinstance(value, (int, float, bool)):
        return value
    try:
        return json.loads(str(value))
    except Exception:
        return value


def _humanize_code(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    text = text.replace("_", " ").replace("-", " ")
    if text.lower() == text:
        text = " ".join(token.capitalize() for token in text.split())
    return text


def _family_and_type(fact_type: str) -> tuple[str, str, str]:
    raw = str(fact_type or "")
    if "." in raw:
        family, subtype = raw.split(".", 1)
    else:
        family, subtype = raw, raw
    family_label = FAMILY_LABELS.get(family, _humanize_code(family) or "General")
    type_label = _humanize_code(subtype) or _humanize_code(raw) or "Fact"
    return family, family_label, type_label


def _value_to_summary(value: Any, max_items: int = 4) -> str:
    parsed = _safe_json(value)
    if parsed is None:
        return "No recorded value."
    if isinstance(parsed, dict):
        parts: List[str] = []
        for key, val in parsed.items():
            if val in (None, "", [], {}):
                continue
            parts.append(f"{_humanize_code(key)}: {_value_to_summary(val, max_items=2)}")
            if len(parts) >= max_items:
                break
        return "; ".join(parts) if parts else "Structured fact value recorded."
    if isinstance(parsed, list):
        items = [str(_value_to_summary(item, max_items=2)) for item in parsed[:max_items] if item not in (None, "")]
        if not items:
            return "Listed value recorded."
        suffix = " …" if len(parsed) > max_items else ""
        return "; ".join(items) + suffix
    text = str(parsed).strip()
    if not text:
        return "No recorded value."
    return text


def _source_label(source_path: str | None, location_json: Any) -> str:
    source_name = ntpath.basename(str(source_path or "").replace("/", "\\")).strip() or os.path.basename(str(source_path or "")).strip() or "Unknown source"
    location = _safe_json(location_json)
    if isinstance(location, dict):
        if "page" in location:
            return f"{source_name} p.{location['page']}"
        if "row" in location:
            return f"{source_name} row {location['row']}"
        if "activity_id" in location:
            return f"{source_name} activity {location['activity_id']}"
    return source_name


def _origin_label(input_kind: Any, method_id: Any) -> str:
    key = str(input_kind or "").strip().lower()
    if key in INPUT_KIND_LABELS:
        return INPUT_KIND_LABELS[key]
    method_text = str(method_id or "").strip().lower()
    if "ocr" in method_text or "parser" in method_text:
        return "OCR / parser extraction"
    if "graph" in method_text or "link" in method_text:
        return "Linked / structured support"
    if "analysis" in method_text or "ai" in method_text or "llm" in method_text:
        return "AI-supported origin"
    if method_text:
        return _humanize_code(method_text)
    return "Origin not recorded"


def build_fact_review_view(row: Dict[str, Any]) -> Dict[str, str]:
    family, family_label, type_label = _family_and_type(str(row.get("fact_type") or ""))
    subject = _humanize_code(row.get("subject_id")) or "Project item"
    status = str(row.get("status") or "").strip().upper() or "CANDIDATE"
    status_meta = STATUS_META.get(status, STATUS_META["CANDIDATE"])

    value_candidate = row.get("value_text")
    if value_candidate in (None, ""):
        num = row.get("value_num")
        unit = str(row.get("unit") or "").strip()
        if num not in (None, ""):
            value_candidate = f"{num} {unit}".strip()
        else:
            value_candidate = row.get("value_json")

    value_summary = _value_to_summary(value_candidate)
    source_label = _source_label(row.get("source_path"), row.get("location_json"))
    origin_label = _origin_label(row.get("input_kind"), row.get("method_id"))

    title = f"{type_label} — {subject}" if subject and subject != type_label else type_label
    meaning = f"This {family_label.lower()} fact records {type_label.lower()} for {subject.lower()}: {value_summary}"

    return {
        "fact_id": str(row.get("fact_id") or ""),
        "fact_type": str(row.get("fact_type") or ""),
        "family_key": family,
        "family_label": family_label,
        "type_label": type_label,
        "title": title,
        "meaning": meaning,
        "value_summary": value_summary,
        "status_code": status,
        "status_label": status_meta["label"],
        "status_explanation": status_meta["explanation"],
        "action_explanation": status_meta["actions"],
        "source_label": source_label,
        "source_document": ntpath.basename(str(row.get("source_path") or "").replace("/", "\\").strip()) or os.path.basename(str(row.get("source_path") or "").strip()) or "Unknown source",
        "origin_label": origin_label,
        "subject_label": subject,
        "location_label": _format_location(row.get("location_json")),
        "type_code": str(row.get("fact_type") or ""),
    }


def _format_location(location_json: Any) -> str:
    location = _safe_json(location_json)
    if isinstance(location, dict):
        parts: List[str] = []
        for key in ("page", "row", "activity_id", "sheet", "bbox"):
            if key in location and location[key] not in (None, ""):
                parts.append(f"{_humanize_code(key)}: {location[key]}")
        return "; ".join(parts) if parts else "Location not recorded"
    return "Location not recorded"


def filter_fact_rows(
    rows: Iterable[Dict[str, Any]],
    family_filter: str = "All families",
    type_filter: str = "All fact types",
    status_filter: str = "All states",
    source_filter: str = "All sources",
) -> List[Dict[str, Any]]:
    filtered: List[Dict[str, Any]] = []
    for row in rows:
        view = build_fact_review_view(row)
        if family_filter != "All families" and view["family_label"] != family_filter:
            continue
        if type_filter != "All fact types" and view["type_code"] != type_filter:
            continue
        if status_filter != "All states" and view["status_code"] != status_filter:
            continue
        if source_filter != "All sources" and view["source_document"] != source_filter:
            continue
        merged = dict(row)
        merged.update(view)
        filtered.append(merged)
    return filtered


def build_filter_options(rows: Iterable[Dict[str, Any]]) -> Dict[str, List[str]]:
    families = {"All families"}
    types = {"All fact types"}
    states = {"All states"}
    sources = {"All sources"}

    for row in rows:
        view = build_fact_review_view(row)
        families.add(view["family_label"])
        types.add(view["type_code"])
        states.add(view["status_code"])
        sources.add(view["source_document"])

    return {
        "families": sorted(families, key=str.lower),
        "types": sorted(types, key=str.lower),
        "states": sorted(states, key=str.lower),
        "sources": sorted(sources, key=str.lower),
    }
