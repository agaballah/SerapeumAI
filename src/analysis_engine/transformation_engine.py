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
transformation_engine.py — Normalize VLM outputs into unified taxonomy entities.

Input:
    - Page-level captions from Vision worker (run_vision_worker)
    - Page metadata from DocumentService (vision_pages)
    - Optional text agents or OCR hints

Output:
    - Normalized entity list
    - Normalized relationships list

This module does NOT call any LLM. It is purely structural.
"""

from __future__ import annotations

from typing import Any, Dict, List

from src.taxonomy.entities import BaseEntity
from src.taxonomy.zone_entity import ZoneEntity


class TransformationEngine:
    """
    Converts raw VLM caption JSON into normalized entity structures.
    """

    def __init__(self) -> None:
        pass

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------
    def transform_page(self, *, doc_id: str, page_index: int, caption: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert a VLM caption into:
            { "entities": [...], "relationships": [...] }
        """
        ents: List[Any] = []
        rels: List[Dict[str, Any]] = []

        # High-level classification
        page_type = str(caption.get("type") or "other")
        title = str(caption.get("title") or "").strip()
        notes = caption.get("notes") or []
        rooms = caption.get("rooms") or []

        # Page entity itself
        ents.append(
            BaseEntity(
                type="page",
                value=title or page_type,
                attributes={"doc_id": doc_id, "page_index": page_index},
                page_index=page_index,
                confidence=1.0,
            ).to_dict()
        )

        # Notes → simple BaseEntity
        for n in notes:
            if not n:
                continue
            ents.append(
                BaseEntity(
                    type="note",
                    value=str(n),
                    attributes={},
                    page_index=page_index,
                    confidence=0.9,
                ).to_dict()
            )

        # Rooms → ZoneEntity
        for r in rooms:
            name = str(r.get("name") or "").strip()
            area = r.get("area_m2")
            polygon = r.get("polygon") or None

            ents.append(
                ZoneEntity(
                    name=name or "Room",
                    level=None,
                    polygon=polygon,
                    attrs={"area_m2": area},
                    page_index=page_index,
                    confidence=0.9,
                ).to_dict()
            )

        # No explicit relationships yet → placeholders
        # (User can build adjacency, containment, etc. later.)
        return {"entities": ents, "relationships": rels}
