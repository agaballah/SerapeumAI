# -*- coding: utf-8 -*-
"""
cad_chat_service.py — Iter-4 deterministic CAD chat routing.

Routes CAD-shaped expert-chat questions to deterministic CAD evidence
lookups scoped to the active project. Returns a grounded answer when
project evidence is available and a clear refusal when it is not.

Supported question families (regex-based detection):

  A. "Which layers exist in this drawing?"
  B. "How many INSERT entities are on layer A-DOOR?" (entity count on layer)
  C. "What text annotations are present?"
  D. "Which blocks are referenced?"
  E. "What dimensions are shown?"

The service reads ONLY the project database (DatabaseManager) and the
project's `cad_*` tables. The global standards/knowledge database is
NEVER consulted here, keeping project evidence and global knowledge
visibly separate.

Refusal semantics:

  When the project has no DXF version yet, the service returns a
  refusal that points the engineer to the Add DXF action — without
  inventing any underlying structured answer.

  When the project has DXF evidence but the question is out of scope
  (e.g. "fire rating" of a door), the service returns a refusal
  stating the available evidence does not establish the requested
  property.

The service does NOT use the LLM to derive any structural fact. The
LLM may be invoked by the orchestrator to narrate a grounded answer,
but only after the structured evidence is returned here.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from src.domain.facts.repository import FactRepository


CAD_AUTHORITY = "PROJECT_EVIDENCE"

# Detection patterns for supported question families.
LAYERS_PATTERN = re.compile(
    r"\b(layers?|layer\s+list|which\s+layers)\b", re.IGNORECASE
)
ANNOTATIONS_PATTERN = re.compile(
    r"\b(text\s+annotations?|annotations?|labels?|mtext|texts?)\b", re.IGNORECASE
)
BLOCKS_PATTERN = re.compile(
    r"\b(blocks?|block\s+references?|referenced\s+blocks?)\b", re.IGNORECASE
)
DIMENSIONS_PATTERN = re.compile(
    r"\b(dimensions?|dim\s+measurements?|measurements?)\b", re.IGNORECASE
)
# entity count on a layer e.g. "how many INSERT entities are on layer A-DOOR"
ENTITY_COUNT_LAYER_PATTERN = re.compile(
    r"\b(?:how\s+many|count|number\s+of)\s+"
    r"(?P<entity_type>[A-Za-z0-9_-]+)\s+"
    r"(?:entities?|items?|objects?)\s+"
    r"(?:are\s+|is\s+)?"
    r"(?:on|in|of)\s+"
    r"layer\s+(?P<layer>[A-Za-z0-9_.-]+)",
    re.IGNORECASE,
)
# generic "how many X on layer Y" (X is type)
GENERIC_COUNT_LAYER_PATTERN = re.compile(
    r"\b(?:how\s+many|count|number\s+of)\s+"
    r"(?P<entity_type>[A-Za-z0-9_-]+)\s+"
    r"(?:are\s+|is\s+)?"
    r"(?:on|in)\s+"
    r"layer\s+(?P<layer>[A-Za-z0-9_.-]+)",
    re.IGNORECASE,
)

CAD_INTENT_KEYWORDS = (
    "layer",
    "layers",
    "annotation",
    "annotations",
    "mtext",
    "block",
    "blocks",
    "dimension",
    "dimensions",
    "entities",
    "insert",
    "drawing",
    "dxf",
)


def is_cad_intent(query: str) -> bool:
    """Return True if the query is shaped like a supported CAD question."""
    if not query:
        return False
    q = query.lower()
    return any(kw in q for kw in CAD_INTENT_KEYWORDS)


def _resolve_active_dxf_version(
    db: Any, project_id: str
) -> Optional[Dict[str, Any]]:
    """Return the most recently imported DXF file_version row (and its drawing row)."""
    if db is None:
        return None
    try:
        row = db.execute(
            """
            SELECT fv.file_version_id, fv.source_path, fv.file_ext, fv.imported_at,
                   cd.drawing_version, cd.modelspace_entity_count, cd.layer_count,
                   cd.layout_count, cd.cap_reached
              FROM file_versions fv
              JOIN file_registry fr ON fr.file_id = fv.file_id
              LEFT JOIN cad_drawings cd ON cd.file_version_id = fv.file_version_id
             WHERE (fv.file_ext = '.dxf' OR fv.file_ext = 'dxf')
               AND fr.project_id = ?
             ORDER BY fv.imported_at DESC
             LIMIT 1
            """,
            (project_id,),
        ).fetchone()
    except Exception:
        return None
    if not row:
        return None
    return dict(row)


def _refusal_no_dxf(query: str) -> Dict[str, Any]:
    return {
        "answer": (
            "No DXF drawing is available in the active project. "
            "Add a DXF file from Project Document Center to make this "
            "question answerable from project evidence."
        ),
        "answer_presentation": {
            "summary_block": {
                "title": "Refusal — no project evidence",
                "source_label": "Project DXF (missing)",
                "text": (
                    "The available evidence does not establish an answer. "
                    "No DXF drawing has been added to the active project."
                ),
            },
            "sections": [],
            "candidate_fact_suggestions": [],
            "copy_text": (
                "The available evidence does not establish an answer. "
                "No DXF drawing has been added to the active project."
            ),
        },
        "citations": [],
        "support_facts": [],
        "supporting_only": True,
        "compliance_status": "NO_PROJECT_GROUNDED_MATERIAL",
        "truth_authority": "PROJECT_GROUNDED_SUPPORT_ONLY",
        "mode": "refused",
        "source_lanes": {
            "trusted_facts": 0,
            "extracted_evidence": 0,
            "linked_support": 0,
            "ai_analysis_support": 0,
            "ai_generated_synthesis": False,
        },
        "scope_authority": CAD_AUTHORITY,
    }


def _refusal_out_of_scope(query: str, target: str) -> Dict[str, Any]:
    return {
        "answer": (
            f"The available evidence does not establish {target}. "
            "Project CAD evidence covers drawing structure "
            "(layers, blocks, annotations, dimensions, entity counts). "
            "It does not establish design properties (e.g. fire rating, "
            "acoustic class, structural capacity) — those require "
            "project documents or human certification, not drawing "
            "structure alone."
        ),
        "answer_presentation": {
            "summary_block": {
                "title": "Refusal — evidence not established",
                "source_label": "Project CAD evidence",
                "text": (
                    f"The available evidence does not establish {target}."
                ),
            },
            "sections": [],
            "candidate_fact_suggestions": [],
            "copy_text": (
                f"The available evidence does not establish {target}. "
                "Drawing structure alone does not establish design "
                "properties such as fire rating."
            ),
        },
        "citations": [],
        "support_facts": [],
        "supporting_only": True,
        "compliance_status": "NO_PROJECT_GROUNDED_MATERIAL",
        "truth_authority": "PROJECT_GROUNDED_SUPPORT_ONLY",
        "mode": "refused",
        "source_lanes": {
            "trusted_facts": 0,
            "extracted_evidence": 0,
            "linked_support": 0,
            "ai_analysis_support": 0,
            "ai_generated_synthesis": False,
        },
        "scope_authority": CAD_AUTHORITY,
    }


def _answer_layers(
    fact_repo: FactRepository, project_id: str, file_version_id: str, source_filename: str
) -> Dict[str, Any]:
    layers = fact_repo.query_cad_layers(project_id, file_version_id) or []
    if not layers:
        return _refusal_no_dxf("layers")
    layer_names = [l.get("layer_name", "") for l in layers if l.get("layer_name")]
    body_lines = [f"Layers in {source_filename}:"]
    body_lines.extend(f"  - {name}" for name in layer_names)
    body = "\n".join(body_lines)
    return {
        "answer": body,
        "answer_presentation": {
            "summary_block": {
                "title": "Project CAD evidence",
                "source_label": f"{source_filename} (project)",
                "text": f"Found {len(layer_names)} layer(s).",
            },
            "sections": [
                {
                    "title": "Layers",
                    "source_label": "cad_layers",
                    "rows": [
                        {"layer_name": l.get("layer_name", ""), "entity_count": l.get("entity_count", 0)}
                        for l in layers
                    ],
                }
            ],
            "candidate_fact_suggestions": [],
            "copy_text": body,
        },
        "citations": [
            {
                "source": "project",
                "file": source_filename,
                "table": "cad_layers",
                "file_version_id": file_version_id,
                "layout": "modelspace",
            }
        ],
        "support_facts": [
            {
                "method_id": "cad_chat_v1",
                "authority_role": CAD_AUTHORITY,
                "kind": "layer_inventory",
                "file_version_id": file_version_id,
                "count": len(layer_names),
            }
        ],
        "supporting_only": True,
        "compliance_status": "ANSWERED_WITH_PROJECT_GROUNDED_SUPPORT",
        "truth_authority": "PROJECT_GROUNDED_SUPPORT_ONLY",
        "mode": "answered",
        "source_lanes": {
            "trusted_facts": 0,
            "extracted_evidence": len(layer_names),
            "linked_support": 0,
            "ai_analysis_support": 0,
            "ai_generated_synthesis": False,
        },
        "scope_authority": CAD_AUTHORITY,
    }


def _answer_entity_count_on_layer(
    fact_repo: FactRepository,
    project_id: str,
    file_version_id: str,
    source_filename: str,
    entity_type: str,
    layer_name: str,
) -> Dict[str, Any]:
    count = fact_repo.count_cad_entities_on_layer(
        project_id, file_version_id, layer_name
    )
    type_count = fact_repo.count_cad_entities_by_type(
        project_id, file_version_id, entity_type.upper()
    )
    if count == 0:
        # No entities on that layer at all
        body = (
            f"There are 0 entities on layer '{layer_name}' in "
            f"{source_filename}. (Project evidence: cad_entities.)"
        )
    else:
        body = (
            f"Layer '{layer_name}' contains {count} entity/entities in "
            f"{source_filename}. {entity_type.upper()} count on this "
            f"layer: {type_count}. (Project evidence: cad_entities.)"
        )
    return {
        "answer": body,
        "answer_presentation": {
            "summary_block": {
                "title": "Project CAD evidence",
                "source_label": f"{source_filename} (project)",
                "text": body,
            },
            "sections": [],
            "candidate_fact_suggestions": [],
            "copy_text": body,
        },
        "citations": [
            {
                "source": "project",
                "file": source_filename,
                "table": "cad_entities",
                "file_version_id": file_version_id,
                "layer": layer_name,
                "layout": "modelspace",
            }
        ],
        "support_facts": [
            {
                "method_id": "cad_chat_v1",
                "authority_role": CAD_AUTHORITY,
                "kind": "entity_count_on_layer",
                "layer": layer_name,
                "entity_type": entity_type.upper(),
                "count": count,
                "file_version_id": file_version_id,
            }
        ],
        "supporting_only": True,
        "compliance_status": "ANSWERED_WITH_PROJECT_GROUNDED_SUPPORT",
        "truth_authority": "PROJECT_GROUNDED_SUPPORT_ONLY",
        "mode": "answered",
        "source_lanes": {
            "trusted_facts": 0,
            "extracted_evidence": 1,
            "linked_support": 0,
            "ai_analysis_support": 0,
            "ai_generated_synthesis": False,
        },
        "scope_authority": CAD_AUTHORITY,
    }


def _answer_annotations(
    fact_repo: FactRepository,
    project_id: str,
    file_version_id: str,
    source_filename: str,
) -> Dict[str, Any]:
    rows = fact_repo.list_cad_text_annotations(project_id, file_version_id) or []
    if not rows:
        return _refusal_no_dxf("annotations")
    body_lines = [f"Text annotations in {source_filename} ({len(rows)}):"]
    for r in rows:
        text = (r.get("text_content") or "").replace("\n", " ").strip()
        if len(text) > 80:
            text = text[:77] + "..."
        body_lines.append(
            f"  - [{r.get('entity_type','')}] {r.get('layer','')}: {text}"
        )
    body = "\n".join(body_lines)
    return {
        "answer": body,
        "answer_presentation": {
            "summary_block": {
                "title": "Project CAD evidence",
                "source_label": f"{source_filename} (project)",
                "text": f"Found {len(rows)} text annotation(s).",
            },
            "sections": [
                {
                    "title": "Annotations",
                    "source_label": "cad_text_annotations",
                    "rows": [
                        {
                            "entity_type": r.get("entity_type", ""),
                            "layer": r.get("layer", ""),
                            "text": r.get("text_content", ""),
                        }
                        for r in rows
                    ],
                }
            ],
            "candidate_fact_suggestions": [],
            "copy_text": body,
        },
        "citations": [
            {
                "source": "project",
                "file": source_filename,
                "table": "cad_text_annotations",
                "file_version_id": file_version_id,
                "layout": "modelspace",
            }
        ],
        "support_facts": [
            {
                "method_id": "cad_chat_v1",
                "authority_role": CAD_AUTHORITY,
                "kind": "text_annotations",
                "count": len(rows),
                "file_version_id": file_version_id,
            }
        ],
        "supporting_only": True,
        "compliance_status": "ANSWERED_WITH_PROJECT_GROUNDED_SUPPORT",
        "truth_authority": "PROJECT_GROUNDED_SUPPORT_ONLY",
        "mode": "answered",
        "source_lanes": {
            "trusted_facts": 0,
            "extracted_evidence": len(rows),
            "linked_support": 0,
            "ai_analysis_support": 0,
            "ai_generated_synthesis": False,
        },
        "scope_authority": CAD_AUTHORITY,
    }


def _answer_blocks(
    fact_repo: FactRepository,
    project_id: str,
    file_version_id: str,
    source_filename: str,
) -> Dict[str, Any]:
    db = fact_repo.db
    try:
        rows = db.execute(
            """
            SELECT block_name, insert_references, is_xref
              FROM cad_blocks
             WHERE file_version_id = ?
             ORDER BY block_name
            """,
            (file_version_id,),
        ).fetchall()
    except Exception:
        rows = []
    if not rows:
        return _refusal_no_dxf("blocks")
    body_lines = [f"Blocks referenced in {source_filename} ({len(rows)}):"]
    for r in rows:
        body_lines.append(
            f"  - {r['block_name']} (refs={int(r['insert_references'] or 0)}, "
            f"xref={'yes' if r['is_xref'] else 'no'})"
        )
    body = "\n".join(body_lines)
    return {
        "answer": body,
        "answer_presentation": {
            "summary_block": {
                "title": "Project CAD evidence",
                "source_label": f"{source_filename} (project)",
                "text": f"Found {len(rows)} block definition(s).",
            },
            "sections": [
                {
                    "title": "Blocks",
                    "source_label": "cad_blocks",
                    "rows": [
                        {
                            "block_name": r["block_name"],
                            "insert_references": int(r["insert_references"] or 0),
                            "is_xref": bool(r["is_xref"]),
                        }
                        for r in rows
                    ],
                }
            ],
            "candidate_fact_suggestions": [],
            "copy_text": body,
        },
        "citations": [
            {
                "source": "project",
                "file": source_filename,
                "table": "cad_blocks",
                "file_version_id": file_version_id,
                "layout": "modelspace",
            }
        ],
        "support_facts": [
            {
                "method_id": "cad_chat_v1",
                "authority_role": CAD_AUTHORITY,
                "kind": "block_inventory",
                "count": len(rows),
                "file_version_id": file_version_id,
            }
        ],
        "supporting_only": True,
        "compliance_status": "ANSWERED_WITH_PROJECT_GROUNDED_SUPPORT",
        "truth_authority": "PROJECT_GROUNDED_SUPPORT_ONLY",
        "mode": "answered",
        "source_lanes": {
            "trusted_facts": 0,
            "extracted_evidence": len(rows),
            "linked_support": 0,
            "ai_analysis_support": 0,
            "ai_generated_synthesis": False,
        },
        "scope_authority": CAD_AUTHORITY,
    }


def _answer_dimensions(
    fact_repo: FactRepository,
    project_id: str,
    file_version_id: str,
    source_filename: str,
) -> Dict[str, Any]:
    rows = fact_repo.list_cad_dimensions(project_id, file_version_id) or []
    if not rows:
        return _refusal_no_dxf("dimensions")
    body_lines = [f"Dimensions in {source_filename} ({len(rows)}):"]
    for r in rows:
        meas = r.get("measurement")
        override = r.get("text_override")
        value = override if override else meas
        body_lines.append(
            f"  - {r.get('dimension_type','?')} ({r.get('layer','')}) = {value}"
        )
    body = "\n".join(body_lines)
    return {
        "answer": body,
        "answer_presentation": {
            "summary_block": {
                "title": "Project CAD evidence",
                "source_label": f"{source_filename} (project)",
                "text": f"Found {len(rows)} dimension(s).",
            },
            "sections": [
                {
                    "title": "Dimensions",
                    "source_label": "cad_dimensions",
                    "rows": [
                        {
                            "dimension_type": r.get("dimension_type", ""),
                            "measurement": r.get("measurement"),
                            "text_override": r.get("text_override"),
                            "layer": r.get("layer", ""),
                        }
                        for r in rows
                    ],
                }
            ],
            "candidate_fact_suggestions": [],
            "copy_text": body,
        },
        "citations": [
            {
                "source": "project",
                "file": source_filename,
                "table": "cad_dimensions",
                "file_version_id": file_version_id,
                "layout": "modelspace",
            }
        ],
        "support_facts": [
            {
                "method_id": "cad_chat_v1",
                "authority_role": CAD_AUTHORITY,
                "kind": "dimension_inventory",
                "count": len(rows),
                "file_version_id": file_version_id,
            }
        ],
        "supporting_only": True,
        "compliance_status": "ANSWERED_WITH_PROJECT_GROUNDED_SUPPORT",
        "truth_authority": "PROJECT_GROUNDED_SUPPORT_ONLY",
        "mode": "answered",
        "source_lanes": {
            "trusted_facts": 0,
            "extracted_evidence": len(rows),
            "linked_support": 0,
            "ai_analysis_support": 0,
            "ai_generated_synthesis": False,
        },
        "scope_authority": CAD_AUTHORITY,
    }


def answer_cad_question(
    db: Any,
    project_id: str,
    query: str,
) -> Dict[str, Any]:
    """
    Return a deterministic CAD answer (or refusal) for the given query,
    scoped to the active project database only. Caller is expected to have
    already verified the question is CAD-shaped.
    """
    if db is None or not project_id:
        return _refusal_no_dxf(query)

    active = _resolve_active_dxf_version(db, project_id)
    if not active:
        return _refusal_no_dxf(query)

    file_version_id = active["file_version_id"]
    source_filename = (active.get("source_path") or "").split("\\")[-1] or "drawing.dxf"
    fact_repo = FactRepository(db)

    q = (query or "").strip()
    # entity count on a layer (most specific)
    m = ENTITY_COUNT_LAYER_PATTERN.search(q) or GENERIC_COUNT_LAYER_PATTERN.search(q)
    if m and "layer" in q.lower():
        entity_type = m.group("entity_type")
        layer_name = m.group("layer")
        return _answer_entity_count_on_layer(
            fact_repo, project_id, file_version_id, source_filename, entity_type, layer_name
        )

    if ANNOTATIONS_PATTERN.search(q):
        return _answer_annotations(fact_repo, project_id, file_version_id, source_filename)
    if BLOCKS_PATTERN.search(q):
        return _answer_blocks(fact_repo, project_id, file_version_id, source_filename)
    if DIMENSIONS_PATTERN.search(q):
        return _answer_dimensions(fact_repo, project_id, file_version_id, source_filename)
    if LAYERS_PATTERN.search(q):
        return _answer_layers(fact_repo, project_id, file_version_id, source_filename)

    # Out-of-scope CAD-shaped question (e.g. "fire rating" framed as a DXF
    # property): refuse explicitly.
    return _refusal_out_of_scope(q, "the requested drawing property")
