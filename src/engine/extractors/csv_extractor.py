# -*- coding: utf-8 -*-
"""
CsvExtractor — BaseExtractor wrapper for .csv and .tsv files.

Extracts deterministic tabular evidence from CSV/TSV files.
"""
from __future__ import annotations

import csv
import io
import logging
import os
from typing import Any, Dict, List, Optional

from src.engine.extractors.base import BaseExtractor, ExtractionResult

logger = logging.getLogger(__name__)


class CsvExtractor(BaseExtractor):
    """Extracts tabular data from .csv and .tsv files."""

    maturity = "PRODUCTION"

    @property
    def id(self) -> str:
        return "csv-extractor-v1"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def supported_extensions(self) -> List[str]:
        return [".csv", ".tsv"]

    def extract(self, file_path: str, context: Optional[Dict[str, Any]] = None) -> ExtractionResult:
        context = context or {}
        source_path = os.path.abspath(file_path or "")
        file_name = os.path.basename(source_path)
        doc_id = context.get("doc_id", "unknown")
        ext = os.path.splitext(source_path)[1].lower()

        def update_stage(stage: str, msg: str = "", **extra: Any) -> None:
            cb = context.get("on_stage")
            if callable(cb):
                cb(stage, msg, **extra)

        try:
            if not os.path.exists(source_path):
                raise FileNotFoundError(f"File not found: {source_path}")

            update_stage("INITIALIZING", "Loading CSV/TSV file", source_path=source_path)

            with open(source_path, "rb") as f:
                raw_bytes = f.read()

            text = raw_bytes.decode("utf-8")
            delimiter = "\t" if ext == ".tsv" else ","

            # Parse with csv module
            reader = csv.reader(io.StringIO(text), delimiter=delimiter)
            rows = list(reader)

            row_count = len(rows)
            col_count = len(rows[0]) if rows else 0
            headers = rows[0] if rows else []

            update_stage("EXTRACTING_TEXT", f"Parsed {row_count} rows, {col_count} columns")

            # Create a single page record for CSV/TSV files
            records: List[Dict[str, Any]] = [
                {
                    "type": "pdf_page",
                    "data": {
                        "page_no": 1,
                        "text_content": text,
                        "metadata": {
                            "delimiter": delimiter,
                            "row_count": row_count,
                            "col_count": col_count,
                            "headers": headers[:20],
                            "source_type": "csv" if ext == ".csv" else "tsv",
                            "extractor": self.id,
                        },
                    },
                    "provenance": {"source": "csv_extractor", "delimiter": delimiter},
                }
            ]

            update_stage("FINALIZING", f"Extracted {row_count} rows, {col_count} columns")

            return ExtractionResult(
                records=records,
                diagnostics=[f"CsvExtractor parsed {row_count} rows, {col_count} columns, delimiter={repr(delimiter)}"],
                metadata={
                    "page_count": 1,
                    "char_count": len(text),
                    "row_count": row_count,
                    "col_count": col_count,
                    "delimiter": delimiter,
                    "doc_id": doc_id,
                    "source_path": source_path,
                    "file_name": file_name,
                    "file_size": self._safe_size(source_path),
                },
                success=True,
            )

        except Exception as exc:
            logger.exception("[CsvExtractor] Failed on %s", source_path)
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
