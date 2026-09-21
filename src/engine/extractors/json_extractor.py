# -*- coding: utf-8 -*-
"""
JsonExtractor — BaseExtractor wrapper for .json files.

Extracts deterministic structured evidence from JSON files.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

from src.engine.extractors.base import BaseExtractor, ExtractionResult

logger = logging.getLogger(__name__)


class JsonExtractor(BaseExtractor):
    """Extracts structured data from .json files."""

    maturity = "PRODUCTION"

    @property
    def id(self) -> str:
        return "json-extractor-v1"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def supported_extensions(self) -> List[str]:
        return [".json"]

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

            update_stage("INITIALIZING", "Loading JSON file", source_path=source_path)

            with open(source_path, "rb") as f:
                raw_bytes = f.read()

            text = raw_bytes.decode("utf-8")
            data = json.loads(text)

            # Determine top-level structure
            if isinstance(data, dict):
                top_keys = list(data.keys())
                key_count = len(top_keys)
                sample_key = top_keys[0] if top_keys else ""
                structure_type = "object"
            elif isinstance(data, list):
                key_count = len(data)
                sample_key = ""
                structure_type = "array"
            else:
                key_count = 1
                sample_key = ""
                structure_type = type(data).__name__

            update_stage("EXTRACTING_TEXT", f"Parsed JSON: {structure_type}, {key_count} keys/items")

            # Create a single page record for JSON files
            records: List[Dict[str, Any]] = [
                {
                    "type": "pdf_page",
                    "data": {
                        "page_no": 1,
                        "text_content": text,
                        "metadata": {
                            "structure_type": structure_type,
                            "key_count": key_count,
                            "sample_key": sample_key,
                            "source_type": "json",
                            "extractor": self.id,
                        },
                    },
                    "provenance": {"source": "json_extractor", "structure_type": structure_type},
                }
            ]

            update_stage("FINALIZING", f"Extracted JSON: {structure_type}, {key_count} keys/items")

            return ExtractionResult(
                records=records,
                diagnostics=[f"JsonExtractor parsed {structure_type} with {key_count} keys/items"],
                metadata={
                    "page_count": 1,
                    "char_count": len(text),
                    "structure_type": structure_type,
                    "key_count": key_count,
                    "doc_id": doc_id,
                    "source_path": source_path,
                    "file_name": file_name,
                    "file_size": self._safe_size(source_path),
                },
                success=True,
            )

        except Exception as exc:
            logger.exception("[JsonExtractor] Failed on %s", source_path)
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
