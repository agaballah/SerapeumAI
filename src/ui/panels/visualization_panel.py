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
visualization_panel.py — Unified viewer DTO layer
-------------------------------------------------

Purpose:
    • Provide page list DTOs for DocumentViewer
    • Provide overlay DTOs for UI drawing
    • Hide DB schema details
    • Zero UI logic (Tkinter handles rendering)

Output formats:
    list_pages(doc_id) ->
        [
            {
                "page_index": int,
                "image_path": str,
                "char_count": int,
                "text_quality": float,
                "has_vector": bool,
                "has_images": bool
            }
        ]

    page_overlay(project_id, doc_id, page_index) ->
        {
            "entities": [...],
            "relationships": [...],
            "caption": {...} | None
        }
"""

from __future__ import annotations
from typing import Any, Dict, List
from src.infra.persistence.database_manager import DatabaseManager


class VisualizationPanel:
    def __init__(self, db: DatabaseManager):
        self.db = db

    # ------------------------------------------------------------------ #
    def list_pages(self, doc_id: str) -> List[Dict[str, Any]]:
        """
        Normalize pages from the new normalized DB tables.
        """
        pages = []
        rows = self.db.get_vision_pages(doc_id) or []

        for r in rows:
            pages.append({
                "page_index": int(r.get("page_index", 0)),
                "image_path": r.get("image_ref") or r.get("image_path") or "",
                "char_count": int(r.get("char_count", 0)),
                "text_quality": float(r.get("text_quality") or 0.0),
                "has_vector": bool(r.get("has_vector", False)),
                "has_images": bool(r.get("has_images", False)),
            })

        return pages

    # ------------------------------------------------------------------ #
    def page_overlay(
        self,
        *,
        project_id: str,
        doc_id: str,
        page_index: int
    ) -> Dict[str, Any]:
        """
        Unified overlay:
            • Entities (analysis engine)
            • Relationships
            • Caption if present
        """
        # Cross-doc entities and rels (normalized)
        ents_map = self.db.get_kv(f"analysis:entities:{project_id}") or {}
        rels_map = self.db.get_kv(f"analysis:relationships:{project_id}") or {}

        cap = None
        try:
            caps = self.db.get_page_caption(doc_id, page_index)
            if isinstance(caps, dict):
                cap = caps
        except Exception:
            # fallback to KV mirror
            rec = self.db.get_kv(f"captions:{doc_id}") or {}
            pages = rec.get("pages") or {}
            cap = pages.get(str(page_index), {}).get("caption")

        return {
            "entities": ents_map.get(doc_id) or [],
            "relationships": rels_map.get(doc_id) or [],
            "caption": cap,
        }
