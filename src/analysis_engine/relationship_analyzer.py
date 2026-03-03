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
relationship_analyzer.py — Builds simple relationships between extracted entities.

- Collocation, sheet-to-room references, material usage to rooms.
- Arabic/English agnostic; uses normalized strings produced by EntityAnalyzer.

Location: D:\\SerapeumAI\\src\\analysis_engine\\relationship_analyzer.py
"""

from __future__ import annotations

from typing import Any, Dict, List


def _name_of(e: Dict[str, Any]) -> str:
    """Tolerate either 'name' or 'value' as the primary string."""
    v = e.get("name")
    if isinstance(v, str) and v.strip():
        return v.strip()
    v = e.get("value")
    return v.strip() if isinstance(v, str) else ""


def _type_of(e: Dict[str, Any]) -> str:
    """Map historical/variant types to the canonical set."""
    t = (e.get("type") or "").lower()
    if t in {"drawing_no", "drawing", "sheet_no"}:
        return "sheet"
    return t


def _co_window(text: str, a: str, b: str, *, radius: int = 200) -> bool:
    """
    Co-occurrence within a sliding window: if 'a' and 'b' occur within
    ~radius characters, treat as 'referenced together'.
    """
    if not a or not b:
        return False
    t = text or ""
    ai = t.lower().find(a.lower())
    if ai < 0:
        return False
    bi = t.lower().find(b.lower())
    if bi < 0:
        return False
    return abs(ai - bi) <= max(40, radius)


def _dedupe(objs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out: List[Dict[str, Any]] = []
    for o in objs:
        key = tuple(sorted(o.items()))
        if key in seen:
            continue
        seen.add(key)
        out.append(o)
    return out


class RelationshipAnalyzer:
    def __init__(self, *, language_hint: str = "auto") -> None:
        self.language_hint = language_hint

    def link(self, entities: List[Dict[str, Any]], *, text: str = "") -> List[Dict[str, Any]]:
        """
        Build lightweight relationships:
          - sheet_refers_room: sheet <-> room co-mentioned nearby in text
          - material_in_room: every material + room pair (very permissive baseline)
        """
        rels: List[Dict[str, Any]] = []

        # Index by (normalized) type
        rooms = [e for e in entities if _type_of(e) == "room"]
        sheets = [e for e in entities if _type_of(e) == "sheet"]
        materials = [e for e in entities if _type_of(e) == "material"]

        # Sheet ↔ Room (by co-mention)
        for r in rooms:
            rname = _name_of(r)
            for s in sheets:
                sname = _name_of(s)
                if rname and sname and _co_window(text, rname, sname):
                    rels.append({
                        "type": "sheet_refers_room",
                        "sheet": sname,
                        "room": rname,
                    })

        # Material ↔ Room (baseline: if both exist, assume usage)
        for r in rooms:
            rname = _name_of(r)
            for m in materials:
                mname = _name_of(m)
                if rname and mname:
                    rels.append({
                        "type": "material_in_room",
                        "material": mname,
                        "room": rname,
                    })

        return _dedupe(rels)
