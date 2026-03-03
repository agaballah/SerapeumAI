# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from typing import Any, Dict, List

import logging
from .processor_utils import stable_doc_id
from src.domain.intelligence.text_chunker import TextChunker

logger = logging.getLogger(__name__)


class PDFProcessor:
    """PDF ingestion: extract per-page text, optionally render page images."""

    def process(self, abs_path: str, rel_path: str, export_root: str, *, doc_id_override: str | None = None) -> Dict[str, Any]:
        doc_id = doc_id_override or stable_doc_id(abs_path, prefix="pdf")
        out_dir = os.path.join(export_root, doc_id)
        os.makedirs(out_dir, exist_ok=True)

        pages: List[Dict[str, Any]] = []
        full_text_parts: List[str] = []

        # 1) Text extraction (fast path)
        page_sizes: Dict[int, Dict[str, float]] = {}
        try:
            from pypdf import PdfReader

            reader = PdfReader(abs_path)
            for i, p in enumerate(reader.pages):
                text = ""
                try:
                    text = p.extract_text() or ""
                except Exception:
                    text = ""

                # page dimensions (points), if available
                try:
                    w = float(p.mediabox.width)  # type: ignore[attr-defined]
                    h = float(p.mediabox.height)  # type: ignore[attr-defined]
                    page_sizes[i] = {"width": w, "height": h}
                except Exception:
                    page_sizes[i] = {}

                if text.strip():
                    full_text_parts.append(text.strip())

                pages.append(
                    {
                        "page_index": i,
                        "py_text": text,
                        "py_text_len": len(text or ""),
                        "py_text_extracted": bool(text.strip()),
                        "text_hint": (text.strip()[:200] if text else ""),
                        "width": page_sizes[i].get("width"),
                        "height": page_sizes[i].get("height"),
                        "has_raster": 0,
                        "has_vector": 0,
                        "quality": "queued",
                    }
                )
            
            # Log summary of text extraction
            n_text_pages = sum(1 for p in pages if p["py_text_extracted"])
            total_chars = sum(p["py_text_len"] for p in pages)
            logger.info(f"   [PDFProcessor] Extracted native text from {n_text_pages}/{len(reader.pages)} pages (Total chars: {total_chars})")

        except Exception as e:
            logger.warning(f"   [PDFProcessor] Text extraction failed: {e}")
            # Can't read PDF for any reason; still create a single placeholder page
            pages = [] # Reset to empty to force OCR path if rendering follows? 
            # Actually, let's keep the error placeholder logic but allow OCR to overwrite if it works.
            pages = [
                {
                    "page_index": 0,
                    "py_text": "",
                    "text_hint": f"[pdf] failed to extract text: {e}",
                    "has_raster": 1,
                    "quality": "queued",
                }
            ]

        # [P0-2] OCR Fallback Logic
        # Check if we have enough native text. If not, we SHOULD try OCR on rendered images.
        native_text_total = sum(len(p.get("py_text", "")) for p in pages)
        needs_ocr = native_text_total < 100
        if needs_ocr:
            logger.info(f"   [PDFProcessor] Low native text ({native_text_total} chars). Enabling OCR fallback.")

        # 2) Render page images (optional; requires poppler for pdf2image)
        # If rendering fails, vision can still work for native-text PDFs.
        try:
            from pdf2image import convert_from_path

            rendered = convert_from_path(abs_path, dpi=200)
            
            # Prepare OCR
            try:
                from src.vision.ocr_backends import TesseractBackend
                ocr_engine = TesseractBackend()
            except ImportError:
                ocr_engine = None

            for i, img in enumerate(rendered):
                png_path = os.path.join(out_dir, f"page-{i+1}.png")
                img.save(png_path, "PNG")
                
                # If page index exists in 'pages', update it, else create new
                if i < len(pages):
                    page_rec = pages[i]
                else:
                    page_rec = {
                        "page_index": i, 
                        "py_text": "", 
                        "has_raster": 0, 
                        "quality": "queued",
                        "width": img.width,
                        "height": img.height
                    }
                    pages.append(page_rec)

                page_rec["image_path"] = png_path
                page_rec["has_raster"] = 1
                
                # Run OCR if needed
                if needs_ocr and ocr_engine:
                    try:
                        # Only OCR if this page didn't have good text? Or just overwrite?
                        # Fallback means we assume native is bad.
                        page_ocr = ocr_engine.recognize(png_path, lang_hint="eng+ara")
                        if page_ocr and len(page_ocr) > 10:
                            page_rec["ocr_text"] = page_ocr
                            full_text_parts.append(page_ocr) # Add to full document text
                            logger.info(f"   [PDFProcessor] OCR p{i+1}: {len(page_ocr)} chars")
                    except Exception as oe:
                        logger.warning(f"   [PDFProcessor] OCR failed for p{i+1}: {oe}")

        except Exception:
            # Rendering is best-effort only
            logger.warning(f"   [PDFProcessor] Failed to render page images (pdf2image/poppler missing?)")
            pass

        full_text = "\n\n".join(full_text_parts).strip()
        
        # [P0-1] Restore blocks
        blocks = TextChunker.chunk_text(full_text, source_type="pdf")

        return {
            "doc_id": doc_id,
            "text": full_text,
            "pages": pages,
            "blocks": blocks,
            "structured_data": [],
            "meta": {"source": "pdf-processor", "pages": len(pages), "rel_path": rel_path},
        }
