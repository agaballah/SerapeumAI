# -*- coding: utf-8 -*-
"""
ImageExtractor — BaseExtractor wrapper for image files.

Extracts deterministic metadata and properties from image files using Pillow.
"""
from __future__ import annotations

import imghdr
import logging
import os
from typing import Any, Dict, List, Optional

from src.engine.extractors.base import BaseExtractor, ExtractionResult

logger = logging.getLogger(__name__)


class ImageExtractor(BaseExtractor):
    """Extracts metadata from image files (.png, .jpg, .jpeg, .bmp, .tif, .tiff, .webp)."""

    maturity = "PRODUCTION"

    @property
    def id(self) -> str:
        return "image-extractor-v1"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def supported_extensions(self) -> List[str]:
        return [".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"]

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

            update_stage("INITIALIZING", "Loading image file", source_path=source_path)

            with open(source_path, "rb") as f:
                raw_bytes = f.read()

            # Use imghdr for independent format detection
            detected_format = imghdr.what(None, h=raw_bytes)

            # Use Pillow for detailed metadata (with fallback)
            width = None
            height = None
            mode = None
            format_name = None
            exif_data = {}
            pillow_error = None

            try:
                from PIL import Image
                img = Image.open(source_path)
                width, height = img.size
                mode = img.mode
                format_name = img.format

                # Get EXIF data if available
                try:
                    exif = img._getexif()
                    if exif:
                        # Convert to serializable format
                        exif_data = {str(k): str(v) for k, v in exif.items() if k is not None and v is not None}
                except Exception:
                    pass
            except Exception as exc:
                pillow_error = str(exc)
                logger.warning("[ImageExtractor] Pillow failed for %s: %s", source_path, exc)

            update_stage("EXTRACTING_TEXT", f"Image: {width}x{height}, {mode}, {detected_format}")

            # Create a single page record for image files
            text_content = f"Image file: {file_name}\nDetected format: {detected_format}\n"
            if format_name:
                text_content += f"Pillow format: {format_name}\n"
            if width and height:
                text_content += f"Size: {width}x{height}\n"
            if mode:
                text_content += f"Mode: {mode}\n"
            if pillow_error:
                text_content += f"Pillow error: {pillow_error}\n"

            records: List[Dict[str, Any]] = [
                {
                    "type": "pdf_page",
                    "data": {
                        "page_no": 1,
                        "text_content": text_content,
                        "metadata": {
                            "detected_format": detected_format,
                            "pillow_format": format_name,
                            "width": width,
                            "height": height,
                            "mode": mode,
                            "exif_count": len(exif_data),
                            "pillow_error": pillow_error,
                            "source_type": "image",
                            "extractor": self.id,
                        },
                    },
                    "provenance": {"source": "image_extractor", "format": detected_format},
                }
            ]

            update_stage("FINALIZING", f"Extracted image: {width}x{height}, {detected_format}")

            return ExtractionResult(
                records=records,
                diagnostics=[f"ImageExtractor processed {width}x{height} {mode} {detected_format}"],
                metadata={
                    "page_count": 1,
                    "char_count": 0,
                    "detected_format": detected_format,
                    "pillow_format": format_name,
                    "width": width,
                    "height": height,
                    "mode": mode,
                    "exif_count": len(exif_data),
                    "pillow_error": pillow_error,
                    "doc_id": doc_id,
                    "source_path": source_path,
                    "file_name": file_name,
                    "file_size": self._safe_size(source_path),
                },
                success=True,
            )

        except Exception as exc:
            logger.exception("[ImageExtractor] Failed on %s", source_path)
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
