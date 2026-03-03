# -*- coding: utf-8 -*-
from __future__ import annotations

import os


import logging

logger = logging.getLogger(__name__)


class GenericProcessor:
    """Route to specialized processors based on file extension."""

    def process(self, abs_path: str, rel_path: str, export_root: str, *, doc_id_override: str | None = None, project_root: str | None = None):
        ext = os.path.splitext(abs_path)[1].lower()

        if ext == ".pdf":
            from .pdf_processor import PDFProcessor
            logger.info(f"   [GenericProcessor] Delegating {rel_path} to PDFProcessor (pypdf + pdf2image)")
            return PDFProcessor().process(abs_path, rel_path, export_root, doc_id_override=doc_id_override)

        if ext in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}:
            from .image_processor import ImageProcessor
            logger.info(f"   [GenericProcessor] Delegating {rel_path} to ImageProcessor (Tesseract OCR)")
            return ImageProcessor().process(abs_path, rel_path, export_root, doc_id_override=doc_id_override)

        if ext in {".dxf", ".dgn"}:
            from .cad_processor import CADProcessor
            logger.info(f"   [GenericProcessor] Delegating {rel_path} to CADProcessor ({ext.upper()})")
            return CADProcessor().process(abs_path, rel_path, export_root, doc_id_override=doc_id_override, project_root=project_root)

        if ext in {".docx", ".doc"}:
            from .word_processor import WordProcessor
            logger.info(f"   [GenericProcessor] Delegating {rel_path} to WordProcessor")
            return WordProcessor().process(abs_path, rel_path, export_root, doc_id_override=doc_id_override)

        if ext in {".xlsx", ".xls", ".xlsm", ".csv", ".tsv"}:
            from .excel_processor import ExcelProcessor
            logger.info(f"   [GenericProcessor] Delegating {rel_path} to ExcelProcessor")
            return ExcelProcessor().process(abs_path, rel_path, export_root, doc_id_override=doc_id_override)

        if ext in {".pptx", ".ppt"}:
            from .ppt_processor import PPTProcessor
            logger.info(f"   [GenericProcessor] Delegating {rel_path} to PPTProcessor")
            return PPTProcessor().process(abs_path, rel_path, export_root, doc_id_override=doc_id_override)

        # Unknown / currently unsupported (e.g., DGN/DWG/RVT/IFC/etc.)
        from .processor_utils import stable_doc_id

        return {
            "doc_id": doc_id_override or stable_doc_id(abs_path, prefix="doc"),
            "text": "",
            "pages": [
                {
                    "page_index": 0,
                    "py_text": f"Unsupported file type for ingestion: {ext}\nFile: {rel_path}",
                    "text_hint": rel_path,
                }
            ],
            "meta": {"source": "generic", "unsupported_ext": ext},
        }
