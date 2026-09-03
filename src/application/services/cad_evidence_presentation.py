# -*- coding: utf-8 -*-
"""
cad_evidence_presentation.py — Iter-4 desktop CAD review presenter.

Pure-Python presenter (no UI imports). Builds a deterministic
view-model consumed by the CAD tab in FileDetailPanel and by the
CAD chat routing service.

The presenter only reads the project-scoped `cad_*` tables via
FactRepository. It NEVER writes to or reads from the global DB
(standards/codes). The two databases remain visibly distinct.

View-model contract (dict keys):
- status: one of {QUEUED, PROCESSING, SUCCESS, PARTIAL, FAILED}
- status_reason: short human-readable explanation (no stack traces)
- drawing: {filename, dxf_version, units, layouts, entity_count, extraction_status}
- layers: [{layer_name, color, linetype, on, locked, frozen, entity_count}]
- blocks: [{name, reference_count, sample_insert: {location, rotation, scale}}]
- annotations: [{entity_type, layer, text}]
- dimensions: [{dimension_type, measurement, text_override, layer, dimstyle}]
- entity_count_by_type: {LINE: n, CIRCLE: m, ...}
- provenance: {source_filename, file_version_id, handle_summary, layout}
- is_dxf: bool
- scope_authority: always "PROJECT_EVIDENCE"
- empty: True if the file has no cad_* rows yet
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from src.domain.facts.repository import FactRepository


SUPPORTED_STATUSES = ("QUEUED", "PROCESSING", "SUCCESS", "PARTIAL", "FAILED")
DEFAULT_LAYER_LIMIT = 200
DEFAULT_BLOCK_LIMIT = 200
DEFAULT_ANNOTATION_LIMIT = 200
DEFAULT_DIMENSION_LIMIT = 200
DEFAULT_ENTITY_TYPE_LIMIT = 50


def _row_dict(row: Any) -> Dict[str, Any]:
    if row is None:
        return {}
    if isinstance(row, dict):
        return row
    try:
        return dict(row)
    except Exception:
        return {}


def _safe_json(value: Any) -> Any:
    if value in (None, ""):
        return None
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(str(value))
    except Exception:
        return value


def _coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _derive_units(drawing_version: str, raw: Any) -> str:
    raw_dict = _safe_json(raw) or {}
    explicit = raw_dict.get("units") if isinstance(raw_dict, dict) else None
    if explicit:
        return str(explicit)
    # AutoCAD drawing version AC codes mapped to year labels
    mapping = {
        "AC1009": "Pre-R12 (legacy)",
        "AC1012": "R12",
        "AC1014": "R14",
        "AC1015": "AutoCAD 2000",
        "AC1018": "AutoCAD 2004",
        "AC1021": "AutoCAD 2007",
        "AC1024": "AutoCAD 2010",
        "AC1027": "AutoCAD 2013",
        "AC1032": "AutoCAD 2018",
        "AC1036": "AutoCAD 2024",
    }
    return mapping.get(str(drawing_version or "").strip(), "Unknown (header $INSUNITS not parsed)")


def _resolve_extraction_run(
    db: Any, file_version_id: Optional[str]
) -> Dict[str, Any]:
    if not file_version_id:
        return {}
    try:
        row = db.execute(
            """
            SELECT status, diagnostics_json
              FROM extraction_runs
             WHERE file_version_id = ?
             ORDER BY started_at DESC
             LIMIT 1
            """,
            (file_version_id,),
        ).fetchone()
    except Exception:
        return {}
    return _row_dict(row)


def _status_from_run_meta(run: Dict[str, Any], drawing: Dict[str, Any]) -> str:
    raw_status = (run.get("status") or "").upper()
    if raw_status.startswith("RUNNING"):
        return "PROCESSING"
    if raw_status in {"SUCCESS"}:
        return "SUCCESS"
    if raw_status in {"FAILED", "ERROR"}:
        return "FAILED"
    if raw_status in {"PARTIAL"}:
        return "PARTIAL"
    if raw_status in {"QUEUED", "PENDING"}:
        return "QUEUED"
    # Infer from drawing row when no extraction_run yet
    if drawing and _coerce_int(drawing.get("cap_reached")):
        return "PARTIAL"
    if drawing and drawing.get("file_version_id"):
        return "SUCCESS"
    return "QUEUED"


def _status_reason(
    status: str, run: Dict[str, Any], drawing: Dict[str, Any]
) -> str:
    if status == "PARTIAL":
        cap = _coerce_int(drawing.get("cap_reached"))
        if cap:
            return "Drawing extraction was partial: entity safety limit reached."
        return "Drawing extraction was partial."
    if status == "FAILED":
        diag_raw = run.get("diagnostics_json") or ""
        if diag_raw:
            try:
                d = json.loads(diag_raw)
                err = d.get("error") or d.get("message") or diag_raw
            except Exception:
                err = diag_raw
        else:
            err = "DXF could not be parsed."
        return f"DXF could not be parsed. No CAD evidence was admitted. ({err})"
    if status == "PROCESSING":
        return "DXF is being processed."
    if status == "QUEUED":
        return "DXF is queued for extraction."
    if status == "SUCCESS":
        return "DXF was processed and CAD evidence is available."
    return "DXF processing status is not yet determined."


def _list_layers(
    fact_repo: FactRepository,
    project_id: str,
    file_version_id: str,
    limit: int = DEFAULT_LAYER_LIMIT,
) -> List[Dict[str, Any]]:
    rows = fact_repo.query_cad_layers(project_id, file_version_id) or []
    out: List[Dict[str, Any]] = []
    for r in rows[:limit]:
        out.append(
            {
                "layer_name": r.get("layer_name", ""),
                "color": r.get("color"),
                "linetype": r.get("linetype"),
                "on": bool(r.get("on_flag")),
                "locked": bool(r.get("locked")),
                "frozen": bool(r.get("frozen")),
                "entity_count": _coerce_int(r.get("entity_count")),
            }
        )
    return out


def _list_blocks(
    fact_repo: FactRepository,
    project_id: str,
    file_version_id: str,
    limit: int = DEFAULT_BLOCK_LIMIT,
) -> List[Dict[str, Any]]:
    db = fact_repo.db
    # Block definitions (cad_blocks table) provide the canonical block inventory.
    try:
        def_rows = db.execute(
            """
            SELECT block_name, entity_count, insert_references, is_xref, raw_json
              FROM cad_blocks
             WHERE file_version_id = ?
             ORDER BY block_name
             LIMIT ?
            """,
            (file_version_id, limit),
        ).fetchall()
    except Exception:
        def_rows = []
    # INSERT locations are stored in cad_entities.raw_json for INSERT entity_type.
    try:
        insert_rows = db.execute(
            """
            SELECT layer, raw_json
              FROM cad_entities
             WHERE file_version_id = ? AND entity_type = 'INSERT'
             ORDER BY handle
             LIMIT ?
            """,
            (file_version_id, limit * 4),
        ).fetchall()
    except Exception:
        insert_rows = []

    inserts_by_block: Dict[str, List[Dict[str, Any]]] = {}
    for r in insert_rows:
        try:
            d = json.loads(r["raw_json"]) if r["raw_json"] else {}
        except Exception:
            d = {}
        block_name = d.get("block_name") or d.get("name") or ""
        if not block_name:
            continue
        item = {
            "location": {
                "x": d.get("x"),
                "y": d.get("y"),
                "z": d.get("z"),
            },
            "rotation_deg": d.get("rotation_deg"),
            "scale": {
                "x": d.get("scale_x"),
                "y": d.get("scale_y"),
                "z": d.get("scale_z"),
            },
            "layer": r["layer"] if hasattr(r, "keys") else r[0],
        }
        inserts_by_block.setdefault(block_name, []).append(item)

    out: List[Dict[str, Any]] = []
    seen_names = set()
    for r in def_rows:
        name = r["block_name"]
        seen_names.add(name)
        inserts = inserts_by_block.get(name, [])
        sample = inserts[0] if inserts else {}
        out.append(
            {
                "name": name,
                "is_xref": bool(r["is_xref"]),
                "definition_entity_count": int(r["entity_count"] or 0),
                "reference_count": int(r["insert_references"] or 0) or len(inserts),
                "sample_insert": {
                    "location": sample.get("location", {}),
                    "rotation_deg": sample.get("rotation_deg"),
                    "scale": sample.get("scale", {}),
                    "layer": sample.get("layer", ""),
                },
            }
        )
    # Some files have INSERT entities but no separate block row (e.g. $MODEL_SPACE
    # implicit block). Surface those as derived blocks for visibility.
    for name, inserts in inserts_by_block.items():
        if name in seen_names:
            continue
        sample = inserts[0]
        out.append(
            {
                "name": name,
                "is_xref": False,
                "definition_entity_count": 0,
                "reference_count": len(inserts),
                "sample_insert": {
                    "location": sample.get("location", {}),
                    "rotation_deg": sample.get("rotation_deg"),
                    "scale": sample.get("scale", {}),
                    "layer": sample.get("layer", ""),
                },
            }
        )
    return out


def _list_annotations(
    fact_repo: FactRepository,
    project_id: str,
    file_version_id: str,
    limit: int = DEFAULT_ANNOTATION_LIMIT,
) -> List[Dict[str, Any]]:
    rows = fact_repo.list_cad_text_annotations(project_id, file_version_id) or []
    out: List[Dict[str, Any]] = []
    for r in rows[:limit]:
        out.append(
            {
                "entity_type": r.get("entity_type", ""),
                "layer": r.get("layer", ""),
                "text": r.get("text_content", ""),
                "handle": r.get("handle", ""),
            }
        )
    return out


def _list_dimensions(
    fact_repo: FactRepository,
    project_id: str,
    file_version_id: str,
    limit: int = DEFAULT_DIMENSION_LIMIT,
) -> List[Dict[str, Any]]:
    rows = fact_repo.list_cad_dimensions(project_id, file_version_id) or []
    out: List[Dict[str, Any]] = []
    for r in rows[:limit]:
        out.append(
            {
                "dimension_type": r.get("dimension_type", ""),
                "measurement": r.get("measurement"),
                "text_override": r.get("text_override"),
                "layer": r.get("layer", ""),
                "dimstyle": r.get("dimstyle"),
                "handle": r.get("handle", ""),
            }
        )
    return out


def _entity_count_by_type(
    fact_repo: FactRepository,
    project_id: str,
    file_version_id: str,
) -> Dict[str, int]:
    db = fact_repo.db
    try:
        rows = db.execute(
            """
            SELECT entity_type, COUNT(*) AS cnt
              FROM cad_entities
             WHERE file_version_id = ?
             GROUP BY entity_type
             ORDER BY entity_type
            """,
            (file_version_id,),
        ).fetchall()
    except Exception:
        return {}
    return {str(r["entity_type"]): _coerce_int(r["cnt"]) for r in rows}


def build_cad_evidence_view(
    db: Any,
    *,
    file_id: Optional[str] = None,
    file_path: Optional[str] = None,
    file_version_id: Optional[str] = None,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build a deterministic CAD review view-model for one file.

    db must be the active project's DatabaseManager. The function reads only
    project-scoped tables (file_versions, extraction_runs, cad_*). It never
    touches the global DB.
    """
    empty_view: Dict[str, Any] = {
        "is_dxf": False,
        "status": "QUEUED",
        "status_reason": "No DXF evidence is available yet.",
        "scope_authority": "PROJECT_EVIDENCE",
        "drawing": {},
        "layers": [],
        "blocks": [],
        "annotations": [],
        "dimensions": [],
        "entity_count_by_type": {},
        "provenance": {
            "source_filename": "",
            "file_version_id": "",
            "handle_summary": "",
            "layout": "modelspace",
        },
        "empty": True,
    }

    if db is None:
        return empty_view

    # Resolve file_version
    file_version: Dict[str, Any] = {}
    try:
        if file_version_id:
            row = db.execute(
                "SELECT * FROM file_versions WHERE file_version_id = ? LIMIT 1",
                (file_version_id,),
            ).fetchone()
            file_version = _row_dict(row)
        if not file_version and file_id:
            row = db.execute(
                "SELECT * FROM file_versions WHERE file_id = ? ORDER BY imported_at DESC LIMIT 1",
                (file_id,),
            ).fetchone()
            file_version = _row_dict(row)
        if not file_version and file_path:
            row = db.execute(
                "SELECT * FROM file_versions WHERE source_path = ? ORDER BY imported_at DESC LIMIT 1",
                (file_path,),
            ).fetchone()
            file_version = _row_dict(row)
    except Exception:
        file_version = {}

    if not file_version:
        return empty_view

    file_version_id = file_version.get("file_version_id", "")
    source_path = file_version.get("source_path") or file_path or ""
    file_ext = (file_version.get("file_ext") or "").lower()
    filename = os.path.basename(source_path) if source_path else "Unknown"

    is_dxf = file_ext == ".dxf"
    if not is_dxf:
        return {
            **empty_view,
            "is_dxf": False,
            "status_reason": "This file is not a DXF drawing; CAD evidence is not applicable.",
            "provenance": {
                "source_filename": filename,
                "file_version_id": file_version_id,
                "handle_summary": "",
                "layout": "modelspace",
            },
            "empty": True,
        }

    fact_repo = FactRepository(db)
    drawing_raw = fact_repo.get_cad_drawing_summary(
        project_id or "", file_version_id
    ) or {}
    run = _resolve_extraction_run(db, file_version_id)
    status = _status_from_run_meta(run, drawing_raw)

    drawing_view = {
        "filename": filename,
        "dxf_version": drawing_raw.get("drawing_version", ""),
        "units": _derive_units(
            drawing_raw.get("drawing_version", ""),
            drawing_raw.get("raw_json"),
        ),
        "layouts": _coerce_int(drawing_raw.get("layout_count")),
        "layer_count": _coerce_int(drawing_raw.get("layer_count")),
        "entity_count": _coerce_int(drawing_raw.get("modelspace_entity_count")),
        "extraction_status": status,
    }

    layers = _list_layers(fact_repo, project_id or "", file_version_id)
    blocks = _list_blocks(fact_repo, project_id or "", file_version_id)
    annotations = _list_annotations(fact_repo, project_id or "", file_version_id)
    dimensions = _list_dimensions(fact_repo, project_id or "", file_version_id)
    entity_counts = _entity_count_by_type(fact_repo, project_id or "", file_version_id)

    empty = (
        not drawing_view.get("dxf_version")
        and not layers
        and not blocks
        and not annotations
        and not dimensions
        and not entity_counts
    )

    return {
        "is_dxf": True,
        "status": status,
        "status_reason": _status_reason(status, run, drawing_raw),
        "scope_authority": "PROJECT_EVIDENCE",
        "drawing": drawing_view,
        "layers": layers,
        "blocks": blocks,
        "annotations": annotations,
        "dimensions": dimensions,
        "entity_count_by_type": entity_counts,
        "provenance": {
            "source_filename": filename,
            "file_version_id": file_version_id,
            "handle_summary": (
                f"{drawing_view['entity_count']} entities across "
                f"{drawing_view['layer_count']} layers"
            ),
            "layout": "modelspace",
        },
        "empty": empty,
    }


def render_cad_evidence_text(view: Dict[str, Any]) -> str:
    """Render a CAD view-model to a multi-section plain-text payload.

    Used by FileDetailPanel text-tab fallback and by chat when a more
    narrative answer is preferred. Authority labels are explicit.
    """
    if not view.get("is_dxf"):
        return view.get("status_reason", "Not a DXF file.")

    lines: List[str] = []
    lines.append(f"Status: {view.get('status','QUEUED')}")
    lines.append(f"Reason: {view.get('status_reason','')}")
    lines.append(f"Authority: {view.get('scope_authority','PROJECT_EVIDENCE')}")
    drawing = view.get("drawing") or {}
    if drawing:
        lines.append("")
        lines.append("DRAWING")
        lines.append(f"  Filename        : {drawing.get('filename','')}")
        lines.append(f"  DXF version     : {drawing.get('dxf_version','unknown')}")
        lines.append(f"  Units           : {drawing.get('units','')}")
        lines.append(f"  Layouts         : {drawing.get('layouts',0)}")
        lines.append(f"  Layers          : {drawing.get('layer_count',0)}")
        lines.append(f"  Entity count    : {drawing.get('entity_count',0)}")
        lines.append(f"  Extraction      : {drawing.get('extraction_status','')}")
    layers = view.get("layers") or []
    if layers:
        lines.append("")
        lines.append(f"LAYERS ({len(layers)})")
        for lyr in layers:
            flags = []
            if lyr.get("on") is False:
                flags.append("off")
            if lyr.get("locked"):
                flags.append("locked")
            if lyr.get("frozen"):
                flags.append("frozen")
            flag_str = f" [{','.join(flags)}]" if flags else ""
            lines.append(
                f"  - {lyr.get('layer_name','')}: "
                f"{lyr.get('entity_count',0)} entities{flag_str}"
            )
    blocks = view.get("blocks") or []
    if blocks:
        lines.append("")
        lines.append(f"BLOCKS ({len(blocks)})")
        for blk in blocks:
            si = blk.get("sample_insert") or {}
            loc = si.get("location") or {}
            scale = si.get("scale") or {}
            lines.append(
                f"  - {blk.get('name','')} (refs={blk.get('reference_count',0)}) "
                f"@ ({loc.get('x')},{loc.get('y')},{loc.get('z')}) "
                f"rot={si.get('rotation_deg')} scale={scale.get('x')}"
            )
    annotations = view.get("annotations") or []
    if annotations:
        lines.append("")
        lines.append(f"ANNOTATIONS ({len(annotations)})")
        for ann in annotations:
            text = (ann.get("text") or "").replace("\n", " ").strip()
            if len(text) > 80:
                text = text[:77] + "..."
            lines.append(
                f"  - [{ann.get('entity_type','')}] {ann.get('layer','')}: {text}"
            )
    dimensions = view.get("dimensions") or []
    if dimensions:
        lines.append("")
        lines.append(f"DIMENSIONS ({len(dimensions)})")
        for dim in dimensions:
            meas = dim.get("measurement")
            override = dim.get("text_override")
            value = override if override else meas
            lines.append(
                f"  - {dim.get('dimension_type','')} ({dim.get('layer','')}) = {value}"
            )
    entity_counts = view.get("entity_count_by_type") or {}
    if entity_counts:
        lines.append("")
        lines.append("ENTITIES BY TYPE")
        for k, v in entity_counts.items():
            lines.append(f"  - {k}: {v}")
    prov = view.get("provenance") or {}
    if prov:
        lines.append("")
        lines.append("PROVENANCE")
        lines.append(f"  Source file     : {prov.get('source_filename','')}")
        lines.append(f"  File version id : {prov.get('file_version_id','')}")
        lines.append(f"  Layout          : {prov.get('layout','modelspace')}")
        lines.append(f"  Handle summary  : {prov.get('handle_summary','')}")
    if view.get("empty"):
        lines.append("")
        lines.append("No CAD evidence rows yet — extraction may still be running.")
    return "\n".join(lines)
