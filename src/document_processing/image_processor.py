# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from typing import Any, Dict

import logging
from .processor_utils import stable_doc_id

logger = logging.getLogger(__name__)


class ImageProcessor:
    """Image ingestion: store image path and run best-effort OCR."""

    def process(self, abs_path: str, rel_path: str, export_root: str, *, doc_id_override: str | None = None) -> Dict[str, Any]:
        doc_id = doc_id_override or stable_doc_id(abs_path, prefix="img")
        out_dir = os.path.join(export_root, doc_id)
        os.makedirs(out_dir, exist_ok=True)

        # Keep original image path; also create a normalized PNG copy for consistent downstream vision.
        image_path = abs_path
        try:
            from PIL import Image

            with Image.open(abs_path) as im:
                png_path = os.path.join(out_dir, "page-1.png")
                im.convert("RGB").save(png_path, "PNG")
                image_path = png_path
        except Exception:
            # If Pillow can't read it, keep original path.
            pass

        ocr_text = ""
        try:
            from src.vision.ocr_backends import TesseractBackend

            logger.info(f"   [ImageProcessor] Running Tesseract OCR on {rel_path}...")
            ocr_text = TesseractBackend().recognize(image_path, lang_hint="eng+ara")
            logger.info(f"   [ImageProcessor] OCR completed ({len(ocr_text)} chars extracted)")
        except Exception as e:
            logger.warning(f"   [ImageProcessor] OCR failed: {e}")
            ocr_text = ""

        return {
            "doc_id": doc_id,
            "text": (ocr_text or "").strip(),
            "pages": [
                {
                    "page_index": 0,
                    "ocr_text": (ocr_text or "").strip(),
                    "py_text": "",
                    "text_hint": ((ocr_text or "").strip()[:200]),
                    "image_path": image_path,
                    "has_raster": 1,
                    "quality": "queued",
                }
            ],
            "meta": {"source": "image-processor", "rel_path": rel_path},
        }
