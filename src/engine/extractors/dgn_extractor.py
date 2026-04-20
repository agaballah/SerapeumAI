# -*- coding: utf-8 -*-
"""
DGNExtractor — BaseExtractor wrapper for .dgn (MicroStation) files.

Delegates processing to src.document_processing.dgn_processor.
Since DGN files are binary CAD formats, text extraction is minimal:
we surface XREF links and ODA conversion status as a metadata record.
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
from typing import Any, Dict, List, Optional

from src.engine.extractors.base import BaseExtractor, ExtractionResult

logger = logging.getLogger(__name__)


class DGNExtractor(BaseExtractor):
    """Extracts metadata and XREF links from .dgn files via dgn_processor."""

    @property
    def id(self) -> str:
        return "dgn-extractor-v1"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def supported_extensions(self) -> List[str]:
        return [".dgn"]

    def extract(self, file_path: str, context: Optional[Dict[str, Any]] = None) -> ExtractionResult:
        context = context or {}
        source_path = os.path.abspath(file_path or "")
        file_name = os.path.basename(source_path)
        doc_id = context.get("doc_id", "unknown")

        def update_stage(stage: str, msg: str = "", **extra: Any) -> None:
            cb = context.get("on_stage")
            if callable(cb):
                cb(stage, msg, **extra)

        try:
            if not os.path.exists(source_path):
                raise FileNotFoundError(f"File not found: {source_path}")

            update_stage("INITIALIZING", "Loading DGN processor", source_path=source_path)

            from src.document_processing import dgn_processor

            with tempfile.TemporaryDirectory() as output_dir:
                result = dgn_processor.process(
                    file_path=source_path,
                    output_dir=output_dir,
                    extract_xrefs=True,
                )

            status = result.get("status", "unknown")
            xrefs: List[str] = result.get("xrefs") or []
            dxf_path: Optional[str] = result.get("dxf_path")

            # Build a human-readable summary as the page text
            parts = [f"DGN file: {file_name}", f"Processing status: {status}"]
            if dxf_path:
                parts.append(f"Converted DXF: {os.path.basename(dxf_path)}")
            if xrefs:
                parts.append(f"XREF links ({len(xrefs)}):")
                for xref in xrefs[:50]:
                    parts.append(f"  - {xref}")
            else:
                parts.append("No XREF links detected.")

            summary_text = "\n".join(parts)

            update_stage("EXTRACTING_TEXT", f"DGN status={status}, xrefs={len(xrefs)}")

            records: List[Dict[str, Any]] = [
                {
                    "type": "pdf_page",
                    "data": {
                        "page_no": 1,
                        "text_content": summary_text,
                        "metadata": json.dumps(
                            {
                                "dgn_status": status,
                                "xref_count": len(xrefs),
                                "has_dxf": bool(dxf_path),
                                "source_type": "dgn",
                                "extractor": self.id,
                            }
                        ),
                    },
                    "provenance": {"source": "dgn_extractor"},
                }
            ]

            update_stage("FINALIZING", "DGN extraction complete")

            return ExtractionResult(
                records=records,
                diagnostics=[f"DGNExtractor: status={status}, xrefs={len(xrefs)}"],
                metadata={
                    "page_count": 1,
                    "char_count": len(summary_text),
                    "dgn_status": status,
                    "xref_count": len(xrefs),
                    "doc_id": doc_id,
                    "source_path": source_path,
                    "file_name": file_name,
                    "file_size": self._safe_size(source_path),
                },
                success=True,
            )

        except Exception as exc:
            logger.exception("[DGNExtractor] Failed on %s", source_path)
            return ExtractionResult(
                success=False,
                diagnostics=[str(exc)],
                metadata={
                    "page_count": 0,
                    "char_count": 0,
                    "doc_id": doc_id,
                    "source_path": source_path,
                    "file_name": file_name,
                    "file_size": self._safe_size(source_path),
                },
            )

    # ------------------------------------------------------------------
    def _safe_size(self, path: str) -> int:
        try:
            return int(os.path.getsize(path))
        except Exception:
            return 0
