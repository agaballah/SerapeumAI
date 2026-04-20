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
linking_rules — fuzzy links between text/vision names and CAD room polygons.
Also includes small unit-normalization/quantity helpers used for cross-checks.
"""

from __future__ import annotations

import re
from typing import Dict, Iterable, List, Optional, Sequence


# --------------------------- text normalization --------------------------- #

_WS_RE = re.compile(r"\s+")

STOP_WORDS = {
    "room", "bed", "bedroom", "master", "bath", "wc", "toilet", "hall", "corridor",
    "kitchen", "living", "dining", "stor", "store", "store room", "office", "lobby",
}

def norm(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"[^\w\s\-']", " ", s)
    s = _WS_RE.sub(" ", s).strip()
    return s

def tokens(s: str) -> List[str]:
    return [t for t in norm(s).split() if t and t not in STOP_WORDS]


# ---------------------------- fuzzy similarity ---------------------------- #

def jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    A, B = set(a), set(b)
    if not A and not B:
        return 0.0
    return len(A & B) / max(1, len(A | B))

def char_trigram_score(a: str, b: str) -> float:
    def _tri(s: str) -> set[str]:
        s2 = f" {s} "
        return {s2[i:i+3] for i in range(max(0, len(s2)-2))}
    ta, tb = _tri(norm(a)), _tri(norm(b))
    if not ta and not tb:
        return 0.0
    return len(ta & tb) / max(1, len(ta | tb))

def name_similarity(a: str, b: str) -> float:
    return 0.6 * jaccard(tokens(a), tokens(b)) + 0.4 * char_trigram_score(a, b)


# ----------------------------- unit helpers ------------------------------ #

from src.domain.intelligence.quantity_parser import PhysicalQuantityParser

_parser = PhysicalQuantityParser()

def normalize_value_to_m(value_with_unit: str) -> Optional[float]:
    """
    Standardize various engineering units to meters.
    Uses PhysicalQuantityParser for robust unit-awareness.
    """
    q = _parser.parse(value_with_unit)
    if q is None:
        return None
    
    # If it's a Pint quantity, convert to meters
    if hasattr(q, 'to'):
        try:
            return float(q.to('m').magnitude)
        except Exception:
            return float(q.magnitude) if hasattr(q, 'magnitude') else float(q)
            
    return float(q)


# ------------------------------ linking core ----------------------------- #

def link_text_to_rooms(
    *,
    text_items: Sequence[Dict[str, str]],
    cad_rooms: Sequence[Dict[str, object]],
    min_score: float = 0.52,
) -> List[Dict[str, object]]:
    """
    text_items: [{"text":"Master Bedroom", "page_index":0, ...}, ...]
    cad_rooms:  [{"name":None|"...","polygon":[[x,y],...],"area":float}, ...]
    Returns matches: [{"text":"...","room_index":i,"score":0.8}]
    """
    matches: List[Dict[str, object]] = []
    for idx_r, room in enumerate(cad_rooms or []):
        rname = str(room.get("name") or "")
        for ti in (text_items or []):
            s = name_similarity(rname or ti.get("text", ""), ti.get("text", ""))
            if s >= min_score:
                matches.append({"text": ti.get("text", ""), "room_index": int(idx_r), "score": float(s)})
    # Sometimes CAD rooms are unnamed; link by proximity of “BEDROOM” etc. to area ranges can be added later.
    matches.sort(key=lambda x: x["score"], reverse=True)
    # de-duplicate text labels → keep best match
    best_for_text: Dict[str, Dict[str, object]] = {}
    for m in matches:
        key = str(m["text"])
        if key not in best_for_text or best_for_text[key]["score"] < m["score"]:
            best_for_text[key] = m
    return list(best_for_text.values())


# ------------------------------ BOQ checks ------------------------------- #

def reconcile_boq_vs_drawing(
    *,
    boq: Sequence[Dict[str, object]],
    cad_rooms: Sequence[Dict[str, object]],
    tol_ratio: float = 0.15,
) -> Dict[str, object]:
    """
    Rough quantity sanity check:
    boq: [{"name":"Master Bedroom","area_m2": 14.2}, ...]
    cad_rooms: [{"name":None|"Master Bedroom","area": 14.0}, ...]
    Returns {"ok":bool,"mismatches":[{"name":"...","boq":x,"cad":y,"delta":d},...]}
    """
    out = {"ok": True, "mismatches": []}  # type: ignore
    # Build simple name → area map from CAD (if names exist)
    cad_map: Dict[str, float] = {}
    for r in cad_rooms or []:
        rn = str(r.get("name") or "").strip().lower()
        if rn and isinstance(r.get("area"), (int, float)):
            cad_map[rn] = float(r["area"])

    for item in boq or []:
        name = str(item.get("name") or "").strip().lower()
        if not name or "area_m2" not in item:
            continue
        bv = float(item["area_m2"])
        cv = cad_map.get(name)
        if cv is None:
            out["ok"] = False
            out["mismatches"].append({"name": item.get("name"), "boq": bv, "cad": None, "delta": None})
            continue
        if cv <= 0:
            continue
        rdiff = abs(bv - cv) / max(cv, 1e-6)
        if rdiff > tol_ratio:
            out["ok"] = False
            out["mismatches"].append({"name": item.get("name"), "boq": bv, "cad": cv, "delta": bv - cv})
    return out
