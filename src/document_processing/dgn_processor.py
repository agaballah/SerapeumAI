# -*- coding: utf-8 -*-
# Copyright (c) 2025 Ahmed Gaballa
# Licensed under the Apache License, Version 2.0
"""
dgn_processor.py — DGN (MicroStation) file processing module.

Supports:
  • DGN v8 conversion to DXF via ODA File Converter (if installed)
  • XREF link detection in DGN drawings
  • Graceful fallback when ODA Converter is unavailable

Usage:
    from src.document_processing import dgn_processor
    if dgn_processor.can_handle("drawing.dgn"):
        result = dgn_processor.process(file_path, output_dir)
"""

from __future__ import annotations

import os
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional dependency flags
# ---------------------------------------------------------------------------

# Check if ODA Converter is available
try:
    from src.document_processing.oda_converter import ODAConverter, ODAConverterNotFound
    _oda_instance = ODAConverter()
    _HAS_ODA = _oda_instance.is_available()
except Exception:
    _HAS_ODA = False
    ODAConverter = None  # type: ignore

# Check if XREF Detector is available
try:
    from src.document_processing.xref_detector import XREFDetector
    _HAS_XREF_DETECTOR = True
except Exception:
    _HAS_XREF_DETECTOR = False
    XREFDetector = None  # type: ignore

# Supported file extensions
SUPPORTED_EXTENSIONS = {".dgn"}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def can_handle(file_path: str) -> bool:
    """Return True if this processor can handle the given file's extension."""
    ext = os.path.splitext(file_path)[1].lower()
    return ext in SUPPORTED_EXTENSIONS


def process(
    file_path: str,
    output_dir: Optional[str] = None,
    *,
    extract_xrefs: bool = True,
) -> Dict[str, Any]:
    """
    Process a DGN file and return extracted data.

    Args:
        file_path: Absolute path to the .dgn file.
        output_dir: Optional directory for output files (converted DXF, etc.).
        extract_xrefs: Whether to detect XREF links in the file.

    Returns:
        Dict with keys: status, file_path, xrefs, dxf_path, error
    """
    result: Dict[str, Any] = {
        "status": "pending",
        "file_path": file_path,
        "xrefs": [],
        "dxf_path": None,
        "text": "",
        "meta": {},
        "error": None,
    }

    if not os.path.exists(file_path):
        result["status"] = "error"
        result["error"] = f"File not found: {file_path}"
        result["text"] = f"Error: {result['error']}"
        result["meta"] = {"error": True, "source": "dgn_processor"}
        return result

    # Step 1: Convert to DXF using ODA Converter (if available)
    if _HAS_ODA and ODAConverter:
        try:
            converter = ODAConverter()
            dxf_path = converter.convert_to_dxf(file_path)
            if dxf_path and os.path.exists(dxf_path):
                result["dxf_path"] = dxf_path
                logger.info(f"[DGNProcessor] Converted {os.path.basename(file_path)} -> {dxf_path}")
        except Exception as e:
            logger.warning(f"[DGNProcessor] ODA conversion failed: {e}")
    else:
        logger.info("[DGNProcessor] ODA Converter not available — skipping DXF conversion")

    # Step 2: Detect XREFs (if requested)
    if extract_xrefs and _HAS_XREF_DETECTOR and XREFDetector:
        try:
            detector = XREFDetector()
            xrefs = detector.detect_xrefs(file_path)
            result["xrefs"] = xrefs or []
        except Exception as e:
            logger.warning(f"[DGNProcessor] XREF detection failed: {e}")

    result["status"] = "done" if result.get("dxf_path") else "no_oda"
    result["text"] = f"DGN Processing: {result['status']}"
    result["meta"] = {"source": "dgn_processor", "status": result["status"]}
    return result


def get_metadata(file_path: str) -> Dict[str, Any]:
    """Return basic metadata for a DGN file."""
    if not os.path.exists(file_path):
        return {"error": f"File not found: {file_path}"}
    return {
        "file_path": file_path,
        "file_name": os.path.basename(file_path),
        "file_size_bytes": os.path.getsize(file_path),
        "extension": os.path.splitext(file_path)[1].lower(),
        "has_oda_converter": _HAS_ODA,
        "has_xref_detector": _HAS_XREF_DETECTOR,
    }
