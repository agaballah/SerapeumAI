# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List

from .processor_utils import stable_doc_id

logger = logging.getLogger(__name__)


class CADProcessor:
    """CAD document processor — V01 compatibility wrapper.

    Delegates all deterministic .dxf extraction to DXFExtractor (V02 registry
    authority). DGN conversion remains handled here via ODAConverter.

    The V01 response contract (doc_id/text/pages/structured_data/xrefs/meta)
    is preserved for backward compatibility with callers in the document
    processing pipeline.
    """

    def process(
        self,
        abs_path: str,
        rel_path: str,
        export_root: str,
        *,
        doc_id_override: str | None = None,
        project_root: str | None = None,
    ) -> Dict[str, Any]:
        doc_id = doc_id_override or stable_doc_id(abs_path, prefix="cad")
        ext = os.path.splitext(abs_path)[1].lower()
        found_xrefs: List[Any] = []

        # ── DGN conversion path (unchanged) ────────────────────────────────
        target_path: str | None = abs_path
        if ext == ".dgn":
            from .oda_converter import ODAConverter
            converter = ODAConverter()
            if converter.is_available():
                logger.info("[CADProcessor] Converting DGN to DXF: %s", rel_path)
                converted_path = converter.convert_to_dxf(abs_path)
                if converted_path:
                    target_path = converted_path
                else:
                    return _error_result(doc_id, rel_path, f"DGN conversion failed for {rel_path}")
            else:
                return _error_result(
                    doc_id, rel_path,
                    f"ODA File Converter not found. Cannot process DGN: {rel_path}",
                )

        # ── DXF path: delegate to authoritative DXFExtractor ───────────────
        if target_path and os.path.exists(target_path):
            from src.engine.extractors.dxf_extractor import DXFExtractor

            extractor = DXFExtractor()
            result = extractor.extract(target_path, context={})

            if not result.success:
                diag_text = "; ".join(result.diagnostics)
                return _error_result(doc_id, rel_path, diag_text)

            # Build flat text summary for V01 compatibility
            text_parts = list(result.diagnostics)
            drawing_rec = next(
                (r for r in result.records if r["type"] == "dxf_drawing"), None
            )
            if drawing_rec:
                d = drawing_rec["data"]
                text_parts.append(
                    f"DXF v{d.get('drawing_version','?')} | "
                    f"{d.get('modelspace_entity_count',0)} entities | "
                    f"{d.get('layer_count',0)} layers | "
                    f"{d.get('layout_count',0)} layouts"
                )

            # Collect XREF records for V01 xrefs field
            xref_recs = [r for r in result.records if r["type"] == "dxf_xref"]
            if project_root:
                try:
                    from .xref_detector import XREFDetector
                    detector = XREFDetector(project_root)
                    raw_xrefs = detector.scan(target_path)
                    if raw_xrefs:
                        found_xrefs = raw_xrefs
                        text_parts.append(f"Detected {len(raw_xrefs)} XREF(s)")
                except Exception as exc:
                    logger.debug("[CADProcessor] XREF scan best-effort fallback: %s", exc)

            # structured_data: flat list of deterministic entity dicts for V01
            # Each entry includes 'type' (backward-compat) and 'cad_type' (explicit).
            structured_data = []
            for rec in result.records:
                if rec["type"] == "dxf_drawing":
                    continue  # drawing metadata goes into meta, not structured_data
                d = dict(rec["data"])
                d["type"] = rec["type"].replace("dxf_", "")
                d["cad_type"] = d["type"]
                structured_data.append(d)

            return {
                "doc_id": doc_id,
                "text": "\n".join(text_parts).strip(),
                "pages": [
                    {
                        "page_index": 0,
                        "py_text": "\n".join(text_parts).strip(),
                        "text_hint": rel_path,
                        "has_vector": 1,
                        "quality": "queued",
                    }
                ],
                "structured_data": structured_data,
                "xrefs": [
                    {"rel_path": x.ref_rel_path, "abs_path": x.ref_abs_path}
                    for x in found_xrefs
                ],
                "meta": {
                    "source": "cad-processor",
                    "rel_path": rel_path,
                    "original_ext": ext,
                    "dxftype": "dxf",
                    "cap_reached": result.metadata.get("cap_reached", False),
                    "entity_count": result.metadata.get("entity_count", 0),
                    "status_diagnostic": (
                        "PARTIAL"
                        if result.metadata.get("cap_reached")
                        else "SUCCESS"
                    ),
                },
            }

        # Fallback: path does not exist
        return _error_result(doc_id, rel_path, f"Target path not found: {target_path}")


def _error_result(doc_id: str, rel_path: str, message: str) -> Dict[str, Any]:
    return {
        "doc_id": doc_id,
        "text": f"[cad] {message}",
        "pages": [
            {
                "page_index": 0,
                "py_text": f"[cad] {message}",
                "text_hint": rel_path,
                "has_vector": 0,
                "quality": "failed",
            }
        ],
        "structured_data": [],
        "xrefs": [],
        "meta": {
            "source": "cad-processor",
            "rel_path": rel_path,
            "original_ext": "",
            "status_diagnostic": "FAILED",
        },
    }
