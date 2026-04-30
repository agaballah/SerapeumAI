from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


THEME_ORDER = [
    "Project scope",
    "Contractor responsibilities",
    "Standards / compliance",
    "Systems / works included",
    "Additional trusted facts",
]


RELATION_LABELS = {
    "linked_to": "links",
    "depends_on": "indicates a dependency between",
    "includes": "suggests inclusion of",
    "serves": "connects",
    "relates_to": "relates",
    "supports": "supports",
}


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, dict):
        preferred = [
            "statement",
            "summary",
            "title",
            "description",
            "name",
            "value",
            "component",
            "requirement",
            "scope",
            "text",
        ]
        for key in preferred:
            raw = value.get(key)
            if raw not in (None, "", [], {}):
                return _stringify(raw)
        parts = []
        for key, raw in value.items():
            text = _stringify(raw)
            if text:
                parts.append(f"{key.replace('_', ' ')}: {text}")
        return "; ".join(parts)
    if isinstance(value, list):
        parts = [_stringify(v) for v in value[:5]]
        parts = [p for p in parts if p]
        return "; ".join(parts)
    return str(value)


def _normalize_space(text: Any) -> str:
    return " ".join(_stringify(text).replace("\n", " ").split())


def _trim(text: Any, limit: int = 220) -> str:
    value = _normalize_space(text)
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."


def _source_basename(path_value: Any) -> str:
    path_text = _stringify(path_value)
    if not path_text:
        return "project file"
    try:
        return Path(path_text).name or path_text
    except Exception:
        return path_text


def _page_label(page_index: Any) -> str:
    try:
        return f"p.{int(page_index) + 1}"
    except Exception:
        return ""


def _join_bits(*bits: str) -> str:
    return " · ".join([b for b in bits if b])


def _looks_fragmentary(text: str) -> bool:
    lowered = text.lower().strip(" .;:-")
    if not lowered:
        return True
    bad_endings = (
        " or",
        " and",
        " to",
        " for",
        " with",
        " of",
        " by",
        " in",
        " on",
        " from",
        " than",
        " per",
        " per the",
        " such as",
        " including",
        " include",
        " includes",
        " where",
        " when",
    )
    if any(lowered.endswith(ending) for ending in bad_endings):
        return True
    if len(lowered.split()) < 3:
        return True
    return False


def _as_sentence(text: Any, fallback: str = "") -> str:
    cleaned = _trim(text, 220)
    if not cleaned:
        return fallback
    cleaned = cleaned.strip(" ;:-")
    if _looks_fragmentary(cleaned):
        return fallback or cleaned
    if cleaned and cleaned[-1] not in ".!?":
        cleaned += "."
    return cleaned[0].upper() + cleaned[1:] if cleaned else fallback


def _fact_theme(fact: Dict[str, Any], text: str) -> str:
    fact_type = _stringify(fact.get("fact_type")).lower()
    haystack = f"{fact_type} {text.lower()}"
    if any(term in haystack for term in ("responsib", "contractor", "shall provide", "shall submit", "must provide", "must submit")):
        return "Contractor responsibilities"
    if any(term in haystack for term in ("standard", "code", "comply", "compliance", "specification", "authority", "regulation")):
        return "Standards / compliance"
    if any(term in haystack for term in ("scope", "requirement", "obligation", "profile", "abstract", "purpose", "summary")):
        return "Project scope"
    if any(term in haystack for term in ("component", "system", "includes", "equipment", "structure", "works", "installation", "room", "tank", "ventilation", "generator", "chiller")):
        return "Systems / works included"
    return "Additional trusted facts"


def _humanize_fact(fact: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    lineage = fact.get("lineage") or []
    source_name = ""
    location_page = ""
    if lineage:
        first = lineage[0] or {}
        source_name = _source_basename(first.get("source_path"))
        loc = first.get("location") or {}
        if isinstance(loc, dict):
            if "page_index" in loc:
                location_page = _page_label(loc.get("page_index"))
            elif "page" in loc:
                location_page = f"p.{loc.get('page')}"
    raw_fact_type = _stringify(fact.get("fact_type"))
    readable_fact_type = raw_fact_type.replace("document.", "").replace("_", " ")
    sentence = _as_sentence(fact.get("value"), fallback="")
    if not sentence:
        fallback = readable_fact_type.capitalize() if readable_fact_type else "Trusted fact available"
        sentence = _as_sentence(fallback, fallback=fallback + ".")
    theme = _fact_theme(fact, sentence)
    details = _join_bits(_join_bits(source_name, location_page), _stringify(fact.get("status")))
    return {
        "chip": "Trusted Fact",
        "text": sentence,
        "details": details,
        "fact_id": fact.get("fact_id"),
        "source_class": "trusted_facts",
        "copy_text": sentence,
        "theme": theme,
        "fact_type": raw_fact_type,
    }


def _score_text_for_query(query: str, text: str) -> int:
    score = 0
    lowered = text.lower()
    tokens = [t for t in query.lower().replace("_", " ").split() if len(t) > 2]
    for token in tokens:
        if token in lowered:
            score += 2
    score -= max(0, len(text) - 180) // 40
    return score


def _humanize_extraction(item: Dict[str, Any], query: str) -> Dict[str, Any]:
    page = _page_label(item.get("page_index"))
    source_name = _source_basename(item.get("source_path"))
    chip = f"Extraction {page}".strip()
    excerpt = _trim(item.get("text"), 150)
    if excerpt and excerpt[-1] not in ".!?":
        excerpt += "..." if not excerpt.endswith("...") else ""
    provenance = _stringify(item.get("provenance")) or "Extraction"
    return {
        "chip": chip,
        "text": excerpt,
        "details": _join_bits(provenance, source_name),
        "source_class": "extracted_evidence",
        "copy_text": _trim(item.get("text"), 320),
        "score": _score_text_for_query(query, excerpt),
    }


def _humanize_linked(item: Dict[str, Any]) -> Dict[str, Any]:
    entity_value = _trim(item.get("entity_value"), 100)
    neighbor_value = _trim(item.get("neighbor_value"), 100)
    relation_key = _stringify(item.get("relation")) or "linked_to"
    relation = RELATION_LABELS.get(relation_key, relation_key.replace("_", " "))
    confidence = (_stringify(item.get("confidence_tier")) or "candidate").replace("_", " ").lower()
    text = f"Candidate support {relation} {entity_value} and {neighbor_value}."
    details = _join_bits("non-trusted support", confidence)
    return {
        "chip": "Linked Support",
        "text": text,
        "details": details,
        "source_class": "linked_support",
        "copy_text": text,
    }


def _humanize_ai_analysis(item: Dict[str, Any]) -> Dict[str, Any]:
    page = _page_label(item.get("page_index"))
    source_name = _source_basename(item.get("source_path"))
    text = _trim(item.get("text"), 150)
    if text and text[-1] not in ".!?":
        text += "."
    return {
        "chip": f"AI Analysis {page}".strip(),
        "text": text,
        "details": _join_bits("AI-generated / non-governing", source_name),
        "source_class": "ai_analysis",
        "copy_text": _trim(item.get("text"), 260),
    }


def _humanize_ai_synthesis(text: str) -> Dict[str, Any]:
    summary = _trim(text, 180)
    if summary and summary[-1] not in ".!?":
        summary += "."
    return {
        "chip": "AI Synthesis",
        "text": summary,
        "details": "AI-generated / non-governing",
        "source_class": "ai_synthesis",
        "copy_text": summary,
    }


def _group_trusted_items(items: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    grouped: List[Dict[str, Any]] = []
    counts: Dict[str, int] = {}
    for theme in THEME_ORDER:
        themed_items = [item for item in items if item.get("theme") == theme]
        if not themed_items:
            continue
        counts[theme] = len(themed_items)
        grouped.append({
            "chip": "Trusted Fact",
            "text": theme,
            "details": None,
            "source_class": "trusted_facts",
            "copy_text": theme,
            "is_group_heading": True,
        })
        for item in themed_items[:2]:
            grouped.append(item)
    omitted = max(0, len(items) - sum(min(count, 2) for count in counts.values()))
    note = None
    if omitted > 0:
        note = f"Additional trusted facts exist beyond the strongest grouped claims shown here ({omitted} more)."
    return grouped, note


def _select_extracted_items(query: str, extracted_evidence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    items = [_humanize_extraction(item, query) for item in extracted_evidence]
    items.sort(key=lambda item: (-item.get("score", 0), item.get("chip", "")))
    return items[:5]


def _select_linked_items(linked_support: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [_humanize_linked(item) for item in linked_support[:4]]


def _select_ai_items(ai_lane: Dict[str, Any]) -> List[Dict[str, Any]]:
    ai_items = [_humanize_ai_analysis(item) for item in ai_lane.get("analysis_support", [])[:2]]
    if ai_lane.get("synthesis"):
        ai_items.append(_humanize_ai_synthesis(ai_lane.get("synthesis")))
    return ai_items[:3]




def _join_source_parts(parts: List[str]) -> str:
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2:
        return f"{parts[0]} + {parts[1]}"
    return ", ".join(parts[:-1]) + f" + {parts[-1]}"


def _build_support_only_notice(*, extracted_items: List[Dict[str, Any]], linked_items: List[Dict[str, Any]], ai_items: List[Dict[str, Any]]) -> str:
    parts: List[str] = []
    if extracted_items:
        parts.append("extracted project evidence")
    if linked_items:
        parts.append("linked project support")
    if ai_items:
        parts.append("AI-generated non-governing synthesis")
    joined = _join_source_parts(parts)
    if not joined:
        return ""
    return f"Support-only answer — based on {joined}, not yet certified as trusted fact."


def _build_source_basis_banner(*, trusted_items: List[Dict[str, Any]], extracted_items: List[Dict[str, Any]], linked_items: List[Dict[str, Any]], ai_items: List[Dict[str, Any]]) -> str:
    has_trusted = any(not item.get("is_group_heading") for item in trusted_items)
    if not has_trusted:
        support_notice = _build_support_only_notice(
            extracted_items=extracted_items,
            linked_items=linked_items,
            ai_items=ai_items,
        )
        if support_notice:
            return support_notice

    parts: List[str] = []
    if has_trusted:
        parts.append("trusted facts")
    if extracted_items:
        parts.append("extracted evidence")
    if linked_items:
        parts.append("linked support")
    if ai_items:
        parts.append("AI synthesis")
    if not parts:
        return "No grounded project material found."
    return f"Based on {_join_source_parts(parts)}."

def _first_ai_synthesis(ai_items: List[Dict[str, Any]]) -> str:
    for item in ai_items:
        if item.get("source_class") == "ai_synthesis":
            return _as_sentence(item.get("copy_text") or item.get("text"), fallback="")
    return ""


def _first_ai_analysis(ai_items: List[Dict[str, Any]]) -> str:
    for item in ai_items:
        if item.get("source_class") == "ai_analysis":
            text = _as_sentence(item.get("copy_text") or item.get("text"), fallback="")
            if text and not _looks_fragmentary(text):
                return text
    return ""


def _recover_fragmentary_scope_lines(trusted_items: List[Dict[str, Any]]) -> List[str]:
    corpus = " ".join((item.get("copy_text") or item.get("text") or "") for item in trusted_items if not item.get("is_group_heading")).lower()
    lines: List[str] = []
    if "working and operating condition" in corpus or "satisfactorily working" in corpus:
        lines.append("The scope requires the delivered works to be in satisfactory working and operating condition.")
    if "cost effective proposal" in corpus:
        lines.append("The contractor is expected to provide a cost-effective proposal while complying with the project requirements.")
    if "shall provide" in corpus and not lines:
        lines.append("The trusted project material assigns defined contractor delivery obligations within the scope of work.")
    return lines


def _coherent_paragraph(lines: List[str], max_sentences: int = 3) -> str:
    clean: List[str] = []
    for line in lines:
        text = _as_sentence(line, fallback="")
        if not text or _looks_fragmentary(text):
            continue
        if text not in clean:
            clean.append(text)
    if not clean:
        return ""
    paragraph = " ".join(clean[:max_sentences]).strip()
    return _trim(paragraph, 420)


def _trusted_theme_summary_lines(trusted_items: List[Dict[str, Any]]) -> List[str]:
    themed: Dict[str, List[str]] = {}
    for item in trusted_items:
        if item.get("is_group_heading"):
            themed.setdefault(item.get("text", "Additional trusted facts"), [])
            continue
        theme = item.get("theme") or "Additional trusted facts"
        sentence = _as_sentence(item.get("copy_text") or item.get("text"), fallback="")
        if sentence and not _looks_fragmentary(sentence):
            themed.setdefault(theme, []).append(sentence)
    lines: List[str] = []
    scope = themed.get("Project scope", [])
    works = themed.get("Systems / works included", [])
    responsibilities = themed.get("Contractor responsibilities", [])
    standards = themed.get("Standards / compliance", [])
    if scope:
        lines.append(scope[0])
    if works:
        lines.append(works[0])
    if responsibilities:
        lines.append(responsibilities[0])
    if standards:
        lines.append(standards[0])
    if not lines:
        for values in themed.values():
            if values:
                lines.append(values[0])
            if len(lines) >= 3:
                break
    return lines[:4]


def _compose_extraction_summary(extracted_items: List[Dict[str, Any]]) -> List[str]:
    if not extracted_items:
        return []
    snippets = [item.get("copy_text") or item.get("text") for item in extracted_items[:2]]
    snippets = [s for s in (_as_sentence(s, fallback="") for s in snippets) if s]
    if not snippets:
        return []
    lead = "The currently extracted project material supports the following scope summary."
    return [lead] + snippets[:2]


def _build_direct_answer_lines(
    *,
    trusted_items: List[Dict[str, Any]],
    extracted_items: List[Dict[str, Any]],
    linked_items: List[Dict[str, Any]],
    ai_items: List[Dict[str, Any]],
    coverage: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    coverage = coverage or {}

    visible_trusted = [item for item in trusted_items if not item.get("is_group_heading")]
    ai_synthesis = _first_ai_synthesis(ai_items)
    ai_analysis = _first_ai_analysis(ai_items)

    if visible_trusted:
        strongest_source = "Trusted Facts"
        if ai_synthesis and not _looks_fragmentary(ai_synthesis):
            return {
                "source": strongest_source,
                "text": _coherent_paragraph([ai_synthesis], max_sentences=2),
            }
        if ai_analysis and not _looks_fragmentary(ai_analysis):
            return {
                "source": strongest_source,
                "text": _coherent_paragraph([ai_analysis], max_sentences=2),
            }
        paragraph = _coherent_paragraph(_trusted_theme_summary_lines(trusted_items), max_sentences=3)
        if paragraph:
            return {
                "source": strongest_source,
                "text": paragraph,
            }
        recovered = _coherent_paragraph(_recover_fragmentary_scope_lines(trusted_items), max_sentences=2)
        if recovered:
            return {
                "source": strongest_source,
                "text": recovered,
            }
        if extracted_items:
            paragraph = _coherent_paragraph(_compose_extraction_summary(extracted_items), max_sentences=3)
            if paragraph:
                return {
                    "source": strongest_source,
                    "text": paragraph,
                }

    if extracted_items:
        strongest_source = "Extracted Evidence"
        if ai_synthesis and not _looks_fragmentary(ai_synthesis):
            return {
                "source": strongest_source,
                "text": _coherent_paragraph([ai_synthesis], max_sentences=2),
            }
        if ai_analysis and not _looks_fragmentary(ai_analysis):
            return {
                "source": strongest_source,
                "text": _coherent_paragraph([ai_analysis], max_sentences=2),
            }
        paragraph = _coherent_paragraph(_compose_extraction_summary(extracted_items), max_sentences=3)
        if paragraph:
            return {
                "source": strongest_source,
                "text": paragraph,
            }

    if linked_items:
        strongest_source = "Linked Support"
        paragraph = _coherent_paragraph(
            ["Project-linked support is available, but trusted facts and stronger extraction are limited for this question."]
            + [_as_sentence(item.get("text"), fallback="") for item in linked_items[:2]],
            max_sentences=3,
        )
        if paragraph:
            return {
                "source": strongest_source,
                "text": paragraph,
            }

    if ai_items:
        strongest_source = "AI-Generated Synthesis"
        ai_lines = [ai_synthesis] if ai_synthesis else [_as_sentence(item.get("text"), fallback="") for item in ai_items[:2]]
        paragraph = _coherent_paragraph(ai_lines, max_sentences=2)
        if paragraph:
            return {
                "source": strongest_source,
                "text": paragraph,
            }

    return {
        "source": "No grounded material",
        "text": "No meaningful project-grounded material was available for this question.",
    }

def _build_candidate_fact_suggestions(
    *,
    trusted_facts: List[Dict[str, Any]],
    extracted_evidence: List[Dict[str, Any]],
    linked_support: List[Dict[str, Any]],
    ai_lane: Dict[str, Any],
) -> List[Dict[str, Any]]:
    suggestions: List[Dict[str, Any]] = []
    for fact in trusted_facts[:6]:
        suggestions.append({
            "source_class": "trusted_facts",
            "fact_type_hint": fact.get("fact_type"),
            "statement": _trim(fact.get("value"), 220),
            "governing": True,
            "status": fact.get("status"),
            "fact_id": fact.get("fact_id"),
        })
    for item in extracted_evidence[:4]:
        suggestions.append({
            "source_class": "extracted_evidence",
            "fact_type_hint": None,
            "statement": _trim(item.get("text"), 220),
            "governing": False,
            "status": item.get("provenance"),
            "fact_id": None,
        })
    for item in linked_support[:3]:
        suggestions.append({
            "source_class": "linked_support",
            "fact_type_hint": None,
            "statement": _trim(f"{item.get('entity_value')} {item.get('relation')} {item.get('neighbor_value')}", 220),
            "governing": False,
            "status": item.get("confidence_tier") or "candidate",
            "fact_id": None,
        })
    if ai_lane.get("synthesis"):
        suggestions.append({
            "source_class": "ai_synthesis",
            "fact_type_hint": None,
            "statement": _trim(ai_lane.get("synthesis"), 220),
            "governing": False,
            "status": "AI-generated / non-governing",
            "fact_id": None,
        })
    return suggestions[:12]


def build_answer_presentation(
    *,
    query: str,
    trusted_facts: List[Dict[str, Any]],
    trusted_conflicts: List[Dict[str, Any]],
    extracted_evidence: List[Dict[str, Any]],
    linked_support: List[Dict[str, Any]],
    ai_lane: Dict[str, Any],
    coverage: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    coverage = coverage or {}
    trusted_raw_items = [item for item in (_humanize_fact(f) for f in trusted_facts[:12]) if item]
    trusted_items, trusted_overflow_note = _group_trusted_items(trusted_raw_items)
    extracted_items = _select_extracted_items(query, extracted_evidence)
    linked_items = _select_linked_items(linked_support)
    ai_items = _select_ai_items(ai_lane)

    sections: List[Dict[str, Any]] = []

    trusted_note_parts: List[str] = []
    if trusted_conflicts:
        trusted_note_parts.append(
            f"Conflict notice: {len(trusted_conflicts)} trusted conflict set(s) remain visible and should be reviewed carefully."
        )
    elif not coverage.get("is_complete", False) and coverage.get("missing_fact_types"):
        trusted_note_parts.append(
            "Trusted coverage is partial for this question. Missing trusted fact families: "
            + ", ".join(coverage.get("missing_fact_types", []))
            + "."
        )
    if trusted_overflow_note:
        trusted_note_parts.append(trusted_overflow_note)

    sections.append({
        "title": "Trusted Facts",
        "kind": "trusted",
        "items": trusted_items,
        "empty_message": "No trusted facts found for this question.",
        "note": " ".join(trusted_note_parts) if trusted_note_parts else None,
    })

    sections.append({
        "title": "Extracted Evidence",
        "kind": "extracted",
        "items": extracted_items,
        "empty_message": None,
        "note": "Deterministic project excerpts are shown here as compact supporting evidence." if extracted_items else None,
    })

    sections.append({
        "title": "Linked Support",
        "kind": "linked",
        "items": linked_items,
        "empty_message": None,
        "note": "Linked support is non-trusted project context and should be treated as candidate support only." if linked_items else None,
    })

    sections.append({
        "title": "AI-Generated Synthesis",
        "kind": "ai",
        "items": ai_items,
        "empty_message": None,
        "note": "AI-generated / non-governing. Use this lane as interpretation support, not as certified truth." if ai_items else "AI-generated / non-governing.",
    })

    candidate_fact_suggestions = _build_candidate_fact_suggestions(
        trusted_facts=trusted_facts,
        extracted_evidence=extracted_evidence,
        linked_support=linked_support,
        ai_lane=ai_lane,
    )

    summary = _build_direct_answer_lines(
        trusted_items=trusted_items,
        extracted_items=extracted_items,
        linked_items=linked_items,
        ai_items=ai_items,
        coverage=coverage,
    )

    source_basis_banner = _build_source_basis_banner(
        trusted_items=trusted_items,
        extracted_items=extracted_items,
        linked_items=linked_items,
        ai_items=ai_items,
    )

    support_only_notice = ""
    if not any(not item.get("is_group_heading") for item in trusted_items):
        support_only_notice = _build_support_only_notice(
            extracted_items=extracted_items,
            linked_items=linked_items,
            ai_items=ai_items,
        )

    main_answer_text = summary["text"]
    if support_only_notice and not main_answer_text.startswith("Support-only answer"):
        main_answer_text = f"{support_only_notice}\n\n{main_answer_text}"

    summary_block = {
        "title": "Direct Answer",
        "source_label": summary["source"],
        "text": main_answer_text,
        "source_basis_banner": source_basis_banner,
    }

    copy_lines = [
        "## Direct Answer",
        main_answer_text,
    ]
    for section in sections:
        if not section.get("items") and not section.get("empty_message"):
            continue
        copy_lines.append(f"\n## {section['title']}")
        if section.get("note"):
            copy_lines.append(section["note"])
        if section.get("items"):
            for item in section["items"]:
                if item.get("is_group_heading"):
                    copy_lines.append(f"- {item['text']}")
                    continue
                detail = f" ({item['details']})" if item.get("details") else ""
                copy_lines.append(f"- [{item['chip']}] {item['text']}{detail}")
        elif section.get("empty_message"):
            copy_lines.append(f"- {section['empty_message']}")

    return {
        "query": query,
        "summary_block": summary_block,
        "main_answer_text": main_answer_text,
        "source_basis_banner": source_basis_banner,
        "details_button_label": "Show Evidence",
        "details_copy_text": "\n".join(copy_lines),
        "sections": sections,
        "candidate_fact_suggestions": candidate_fact_suggestions,
        "copy_text": main_answer_text,
    }
