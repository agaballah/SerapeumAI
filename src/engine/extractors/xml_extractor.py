# -*- coding: utf-8 -*-
"""
XmlExtractor — BaseExtractor wrapper for .xml files.

Extracts deterministic structured evidence from XML files.
"""
from __future__ import annotations

import logging
import os
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

from src.engine.extractors.base import BaseExtractor, ExtractionResult

logger = logging.getLogger(__name__)


class XmlExtractor(BaseExtractor):
    """Extracts structured data from .xml files."""

    maturity = "PRODUCTION"

    @property
    def id(self) -> str:
        return "xml-extractor-v1"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def supported_extensions(self) -> List[str]:
        return [".xml"]

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

            update_stage("INITIALIZING", "Loading XML file", source_path=source_path)

            with open(source_path, "rb") as f:
                raw_bytes = f.read()

            text = raw_bytes.decode("utf-8")
            root = ET.fromstring(text)

            # Get root tag and child count
            root_tag = root.tag
            child_count = len(list(root))

            update_stage("EXTRACTING_TEXT", f"Parsed XML: root={root_tag}, children={child_count}")

            # Create a single page record for XML files
            records: List[Dict[str, Any]] = [
                {
                    "type": "pdf_page",
                    "data": {
                        "page_no": 1,
                        "text_content": text,
                        "metadata": {
                            "root_tag": root_tag,
                            "child_count": child_count,
                            "source_type": "xml",
                            "extractor": self.id,
                        },
                    },
                    "provenance": {"source": "xml_extractor", "root_tag": root_tag},
                }
            ]

            update_stage("FINALIZING", f"Extracted XML: root={root_tag}, children={child_count}")

            return ExtractionResult(
                records=records,
                diagnostics=[f"XmlExtractor parsed root={root_tag}, children={child_count}"],
                metadata={
                    "page_count": 1,
                    "char_count": len(text),
                    "root_tag": root_tag,
                    "child_count": child_count,
                    "doc_id": doc_id,
                    "source_path": source_path,
                    "file_name": file_name,
                    "file_size": self._safe_size(source_path),
                },
                success=True,
            )

        except Exception as exc:
            logger.exception("[XmlExtractor] Failed on %s", source_path)
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
