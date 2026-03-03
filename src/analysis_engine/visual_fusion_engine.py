# -*- coding: utf-8 -*-
# Copyright (c) 2025 Ahmed Gaballa
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
visual_fusion_engine.py — Combine python extraction + VLM descriptions into
a unified page-level representation.

Inputs:
    - Python extractors (pdf_processor, image_processor)
    - VLM captions (from run_vision_worker)
    - OCR text (DeepSeek)

Outputs:
    - A single authoritative dict describing page-level understanding.
"""

from __future__ import annotations

from typing import Any, Dict


class VisualFusionEngine:
    """
    Simple deterministic fusion module.
    Rules:
        1) OCR text (DeepSeek) always overrides Python text, if available.
        2) VLM-rooms override any geometry-based simple room detection.
        3) Title/caption: VLM always wins if provided.
        4) Notes: merge python + VLM, deduplicate.
    """

    def __init__(self) -> None:
        pass

    # ------------------------------------------------------------------
    def fuse_page(
        self,
        *,
        python_page: Dict[str, Any],
        vlm_page: Dict[str, Any],
        doc_id: str,
        page_index: int,
    ) -> Dict[str, Any]:
        """
        Returns unified representation:
        {
            "doc_id": str,
            "page_index": int,
            "text": "...",
            "rooms": [...],
            "notes": [...],
            "caption": "...",
            ...
        }
        """

        # ------------------------------
        # TEXT
        # ------------------------------
        ocr_text = (python_page.get("ocr_text") or "").strip()
        py_text = (python_page.get("text") or "").strip()

        final_text = ocr_text if ocr_text else py_text

        # ------------------------------
        # ROOMS
        # ------------------------------
        vlm_rooms = vlm_page.get("rooms") or []
        py_rooms = python_page.get("rooms") or []

        final_rooms = vlm_rooms or py_rooms

        # ------------------------------
        # NOTES
        # ------------------------------
        vlm_notes = [n for n in (vlm_page.get("notes") or []) if n]
        py_notes = [n for n in (python_page.get("notes") or []) if n]

        final_notes = list(dict.fromkeys(vlm_notes + py_notes))

        # ------------------------------
        # CAPTION (title)
        # ------------------------------
        caption = vlm_page.get("title") or vlm_page.get("summary") or ""

        # ------------------------------
        # Build unified dict
        # ------------------------------
        return {
            "doc_id": doc_id,
            "page_index": page_index,
            "text": final_text,
            "rooms": final_rooms,
            "notes": final_notes,
            "caption": caption,
            "page_type": vlm_page.get("type") or python_page.get("type") or "other",
            "language": vlm_page.get("language") or "mixed",
        }
