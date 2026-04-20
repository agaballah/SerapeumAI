# -*- coding: utf-8 -*-
"""
PPTXExtractor — BaseExtractor wrapper for .pptx files.

Delegates slide extraction to the existing PPTProcessor in
src.document_processing.ppt_processor, emitting one pdf_page record
per slide so that ExtractJob's _upsert_canonical_page pipeline
handles persistence.
"""
from __future__ import annotations

import logging
import os
import tempfile
from typing import Any, Dict, List, Optional

from src.engine.extractors.base import BaseExtractor, ExtractionResult

logger = logging.getLogger(__name__)


class PPTXExtractor(BaseExtractor):
    """Extracts text from .pptx files via PPTProcessor."""

    @property
    def id(self) -> str:
        return "pptx-extractor-v1"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def supported_extensions(self) -> List[str]:
        return [".pptx"]

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

            update_stage("INITIALIZING", "Loading PPTProcessor", source_path=source_path)

            from src.document_processing.ppt_processor import PPTProcessor

            with tempfile.TemporaryDirectory() as export_root:
                result = PPTProcessor().process(
                    abs_path=source_path,
                    rel_path=file_name,
                    export_root=export_root,
                )

            pages: List[Dict[str, Any]] = result.get("pages") or []
            full_text: str = result.get("text") or ""

            if not pages:
                pages = [{"page_index": 0, "py_text": full_text, "quality": "queued"}]

            update_stage("EXTRACTING_TEXT", f"Processing {len(pages)} slide(s)", page_count=len(pages))

            records: List[Dict[str, Any]] = []
            for pg in pages:
                page_no = int(pg.get("page_index", 0)) + 1
                py_text = str(pg.get("py_text") or "")
                records.append(
                    {
                        "type": "pdf_page",
                        "data": {
                            "page_no": page_no,
                            "text_content": py_text,
                            "metadata": None,
                        },
                        "provenance": {"page": page_no, "source": "pptx_extractor"},
                    }
                )

            update_stage("FINALIZING", f"Extracted {len(records)} slide record(s)")

            return ExtractionResult(
                records=records,
                diagnostics=[f"PPTXExtractor processed {len(records)} slide(s)"],
                metadata={
                    "page_count": len(records),
                    "char_count": len(full_text),
                    "doc_id": doc_id,
                    "source_path": source_path,
                    "file_name": file_name,
                    "file_size": self._safe_size(source_path),
                },
                success=True,
            )

        except Exception as exc:
            logger.exception("[PPTXExtractor] Failed on %s", source_path)
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
