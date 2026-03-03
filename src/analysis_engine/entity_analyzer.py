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
entity_analyzer.py — Extracts entities from text with optional LLM assistance.

Public API expected by AnalysisEngine:
  - class EntityAnalyzer(db: DatabaseManager, llm: Optional[LLMService], language_hint: str)
  - extract(text: str, *, ext: str = "") -> List[Dict[str, Any]]

Notes:
- Works without an LLM (regex/heuristics fallback).
- If LLM is provided, uses it to normalize & enrich entities.
- Emits a CANONICAL shape for downstream tools:
    {
      "type": "sheet|room|zone|spec_section|material|organization|...",
      "name": "<primary string>",       # <- always present
      "value": "<alias of name>",       # <- kept for back-compat
      "span": [start, end] | None       # optional
    }
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from src.infra.persistence.database_manager import DatabaseManager
from src.infra.adapters.llm_service import LLMService, LLMServiceError


# ----------------------------- Heuristics ----------------------------- #

_SHEET_RE = re.compile(r"\b([ASMPE]-\d{2,4})\b", re.I)  # A-101, S-301, M-02...
_ROOM_EN_RE = re.compile(r"\bROOM\s+([A-Z]?\d{1,4})\b", re.I)
_ZONE_EN_RE = re.compile(r"\bZONE\s+([A-Z]\d{0,2})\b", re.I)
_SPEC_RE = re.compile(r"\b(\d{2}\s\d{2}\s\d{2})\b")     # 07 21 00 etc.

# Light Arabic signals (very tolerant)
_ROOM_AR_RE = re.compile(r"\b(?:غرفة|قاعة|مساحة)\s*([A-Za-z\u0621-\u064A]?\d{1,4})\b")
_ZONE_AR_RE = re.compile(r"\b(?:منطقة|زون)\s*([A-Za-z\u0621-\u064A]\d{0,2})\b")


def _append(ents: List[Dict[str, Any]], *, type_: str, name: str, span: Optional[Tuple[int, int]] = None) -> None:
    ents.append({
        "type": type_,
        "name": name,
        "value": name,                         # keep alias for older callers
        "span": list(span) if span else None,
    })


def _simple_entity_heuristics(text: str) -> List[Dict[str, Any]]:
    """
    Very light heuristics for AEC-like entities (EN + basic AR):
      - Sheet/drawing numbers: e.g., A-101, M-02, S-301 → type: 'sheet'
      - Rooms / Zones in EN & AR → type: 'room' / 'zone'
      - Spec sections: 07 21 00 → type: 'spec_section'
    """
    ents: List[Dict[str, Any]] = []

    for m in _SHEET_RE.finditer(text):
        _append(ents, type_="sheet", name=m.group(1), span=(m.start(), m.end()))

    for m in _ROOM_EN_RE.finditer(text):
        _append(ents, type_="room", name=f"ROOM {m.group(1)}", span=(m.start(), m.end()))
    for m in _ROOM_AR_RE.finditer(text):
        _append(ents, type_="room", name=f"غرفة {m.group(1)}", span=(m.start(), m.end()))

    for m in _ZONE_EN_RE.finditer(text):
        _append(ents, type_="zone", name=f"ZONE {m.group(1)}", span=(m.start(), m.end()))
    for m in _ZONE_AR_RE.finditer(text):
        _append(ents, type_="zone", name=f"منطقة {m.group(1)}", span=(m.start(), m.end()))

    for m in _SPEC_RE.finditer(text):
        _append(ents, type_="spec_section", name=m.group(1), span=(m.start(), m.end()))

    return ents


def _canonize_list(items: Any) -> List[Dict[str, Any]]:
    """
    Bring any LLM-returned list into our canonical entity shape.
    Accepts:
      - {"type":"room","name":"ROOM 101"} or {"type":"room","value":"ROOM 101"}
      - {"kind":"drawing_no","text":"A-101"}  (we map kind/text heuristically)
    """
    out: List[Dict[str, Any]] = []
    if not isinstance(items, list):
        return out

    def pick_str(*vals) -> str:
        for v in vals:
            if isinstance(v, str) and v.strip():
                return v.strip()
        return ""

    for it in items:
        if not isinstance(it, dict):
            continue
        t = pick_str(it.get("type"), it.get("kind"))
        n = pick_str(it.get("name"), it.get("value"), it.get("text"), it.get("label"))
        # map common aliases
        if t.lower() in {"drawing_no", "drawing", "sheet_no"}:
            t = "sheet"
        if n:
            out.append({
                "type": t or "other",
                "name": n,
                "value": n,
                "span": it.get("span") if isinstance(it.get("span"), (list, tuple)) else None,
            })
    return out


# ------------------------------ Analyzer ------------------------------ #

class EntityAnalyzer:
    def __init__(self, db: DatabaseManager, llm: Optional[LLMService] = None, *, language_hint: str = "auto") -> None:
        self.db = db
        self.llm = llm
        self.language_hint = language_hint

    def extract(self, text: str, *, ext: str = "") -> List[Dict[str, Any]]:
        """
        Returns a list of CANONICAL entity dicts.
        """
        text = text or ""
        base = _simple_entity_heuristics(text)

        if not self.llm:
            return base

        # Use the LLM to normalize & (optionally) enrich entities.
        try:
            prompt = {
                "instruction": "Normalize and enrich AECO entities from text. Prefer 'type' ∈ {sheet, room, zone, spec_section, material, organization}. Use 'name' for primary string.",
                "language_hint": self.language_hint,
                "file_ext": ext,
                "candidates": base,
                "text_window_sample": text[:4000],  # safety bound
            }
            result = self.llm.entities_from_text(prompt)
            # Accept both list and {"entities":[...]} forms
            if isinstance(result, list):
                return _canonize_list(result)
            if isinstance(result, dict):
                cand = result.get("entities") if isinstance(result.get("entities"), list) else result.get("items")
                if isinstance(cand, list):
                    return _canonize_list(cand)
        except LLMServiceError:
            pass
        except Exception:
            # Be resilient; if LLM path fails, still return base.
            pass

        return base
