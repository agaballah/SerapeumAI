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
Vision Task Registry
--------------------

Purpose
-------
Central place to define *what* the VLM should do for a given document type + trigger,
and *which fields* the model must return (strict JSON contract).

Key ideas
---------
- Tasks are small, declarative specs: name, fields, and a compact prompt snippet.
- `get_task(doc_type, trigger, page_meta)` returns a normalized task dict:
    { "task": "<instruction>", "fields": [...], "region_hint": {..} | None, "metadata": {...} }
- Built-in tasks cover: description, title block, spatial index, symbol legend, zones, and callouts.
- Region hints (optional) are generated from `page_meta` when possible (e.g., title block location).
- Fields are validated against the allowed schema used across the app.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


# ------------------------------ Schema ------------------------------- #

ALLOWED_FIELDS = {
    "page_caption",
    "title_block",
    "rooms",
    "symbols",
    "equipment",
    "notes",
    "relationships",
}

DEFAULT_DOC_TYPE = "general"


@dataclass
class TaskSpec:
    """
    Declarative spec for a vision task.
    """
    name: str
    fields: List[str]
    prompt: str
    allow_auto: bool = True  # eligible for auto-gap filling
    priority: int = 100      # used if multiple candidates exist
    # Optional function that gets region hint dict from page_meta
    region_hint_fn: Optional[Any] = None

    def normalized(self, page_meta: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "task": self._format_prompt(page_meta),
            "fields": self._validated_fields(),
            "region_hint": self._region_hint(page_meta),
            "metadata": {"task_name": self.name, "priority": self.priority},
        }

    # internal helpers
    def _validated_fields(self) -> List[str]:
        out = [f for f in self.fields if f in ALLOWED_FIELDS]
        return out or ["page_caption"]  # never return empty

    def _format_prompt(self, page_meta: Dict[str, Any]) -> str:
        """
        Interpolate a few commonly useful page metadata hints into the prompt.
        """
        discipline = (page_meta.get("discipline") or "").upper()
        sheet_id = page_meta.get("sheet_id") or page_meta.get("sheet") or ""
        lang = (page_meta.get("language") or "").lower()
        lang_hint = (
            "Document language is Arabic; keep names in original language where appropriate."
            if lang.startswith("ar") else ""
        )
        return self.prompt.format(discipline=discipline, sheet_id=sheet_id, language_hint=lang_hint).strip()

    def _region_hint(self, page_meta: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if self.region_hint_fn:
            try:
                return self.region_hint_fn(page_meta)
            except Exception:
                return None
        return None


# -------------------------- Region hint helpers ---------------------- #

def _title_block_hint(page_meta: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Heuristic for common title block positions.
    Returns {"type":"rect","rect":[x,y,w,h]} in pixels if width/height available.
    """
    w = page_meta.get("width")
    h = page_meta.get("height")
    if not isinstance(w, (int, float)) or not isinstance(h, (int, float)) or w <= 0 or h <= 0:
        return None
    if w >= h:
        tb_w, tb_h = 0.28 * w, 0.22 * h
    else:
        tb_w, tb_h = 0.33 * w, 0.28 * h
    x = max(0.0, w - tb_w)
    y = max(0.0, h - tb_h)
    return {"type": "rect", "rect": [int(x), int(y), int(tb_w), int(tb_h)], "label": "title_block_candidate"}


def _legend_hint(page_meta: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Heuristic: many legends sit along the right margin under/near the title block.
    """
    w = page_meta.get("width")
    h = page_meta.get("height")
    if not isinstance(w, (int, float)) or not isinstance(h, (int, float)) or w <= 0 or h <= 0:
        return None
    l_w, l_h = 0.24 * w, 0.4 * h
    x = max(0.0, w - l_w)
    y = int(0.1 * h)
    return {"type": "rect", "rect": [int(x), int(y), int(l_w), int(l_h)], "label": "legend_candidate"}


# --------------------------- Built-in tasks -------------------------- #

TASK_DESCRIBE = TaskSpec(
    name="describe",
    fields=["page_caption"],
    prompt=("Describe the page at a high level in one concise sentence suitable as a caption. {language_hint}"),
    allow_auto=True,
    priority=10,
)

TASK_TITLE_BLOCK = TaskSpec(
    name="title_block",
    fields=["title_block"],
    prompt=(
        "Read the drawing title block. Return: title_block with keys "
        'project, sheet_id, rev, rev_date, discipline. '
        "If a field is missing, set it to null. {language_hint}"
    ),
    allow_auto=True,
    priority=20,
    region_hint_fn=_title_block_hint,
)

TASK_SPATIAL_INDEX = TaskSpec(
    name="spatial_index",
    fields=["rooms", "symbols", "equipment", "notes", "relationships", "page_caption"],
    prompt=(
        "Create a spatial index for this sheet. "
        "Return rooms (name, polygon, level, attrs), symbols (type, bbox, label, attrs), "
        "equipment (name, bbox, attrs), notes (text, bbox), relationships (type, from, to, attrs). "
        "Polygons should be ordered clockwise and use pixel coordinates. {language_hint}"
    ),
    allow_auto=True,
    priority=30,
)

TASK_LEGEND = TaskSpec(
    name="legend",
    fields=["symbols"],
    prompt=(
        "Extract the legend/symbol table. For each entry, return symbols with type (symbol name), "
        "bbox for the icon area, and label (if present). {language_hint}"
    ),
    allow_auto=False,
    priority=50,
    region_hint_fn=_legend_hint,
)

TASK_ZONES = TaskSpec(
    name="zone_map",
    fields=["rooms", "relationships"],
    prompt=(
        "Identify zones/areas and their boundaries as room-like objects. "
        "Use rooms[] with name and polygon, and add relationships for adjacency "
        'as {"type":"adjacent","from":"zoneA","to":"zoneB"}. {language_hint}'
    ),
    allow_auto=False,
    priority=60,
)

TASK_CALLOUTS = TaskSpec(
    name="detail_callouts",
    fields=["symbols", "relationships"],
    prompt=(
        "Identify detail/callout bubbles or markers. "
        "Return symbols with type (e.g., CALL_OUT), bbox, label (e.g., 5/A-301), "
        'and relationships linking callout -> referenced sheet/detail if visible. {language_hint}'
    ),
    allow_auto=False,
    priority=70,
)


# --------------------------- Registry store -------------------------- #

_REGISTRY: Dict[str, Dict[str, TaskSpec]] = {}


def _register_defaults() -> None:
    general = {"describe": TASK_DESCRIBE}
    drawing = {
        "describe": TASK_DESCRIBE,
        "title_block": TASK_TITLE_BLOCK,
        "spatial_index": TASK_SPATIAL_INDEX,
        "legend": TASK_LEGEND,
        "zone_map": TASK_ZONES,
        "detail_callouts": TASK_CALLOUTS,
    }
    _REGISTRY[DEFAULT_DOC_TYPE] = general
    _REGISTRY["drawing"] = drawing
    _REGISTRY["plan"] = drawing
    _REGISTRY["floor_plan"] = drawing


_register_defaults()


# ------------------------------ API ---------------------------------- #

def register_task(doc_type: str, trigger: str, task_spec: TaskSpec) -> None:
    """
    Add or override a task for a given doc_type + trigger.
    """
    dt = (doc_type or DEFAULT_DOC_TYPE).lower()
    trig = (trigger or "describe").lower()
    d = _REGISTRY.setdefault(dt, {})
    d[trig] = task_spec


def list_tasks(doc_type: Optional[str] = None) -> Dict[str, List[str]]:
    """
    Inspect available triggers per doc_type.
    """
    if doc_type:
        dt = doc_type.lower()
        return {dt: sorted(list((_REGISTRY.get(dt) or {}).keys()))}
    return {k: sorted(list(v.keys())) for k, v in _REGISTRY.items()}


def get_task(doc_type: str, trigger: str, page_meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Resolve a concrete task dict for (doc_type, trigger).
    If not found, falls back to sensible defaults.
    """
    page_meta = page_meta or {}
    dt = (doc_type or DEFAULT_DOC_TYPE).lower()
    trig = (trigger or "describe").lower()

    task_map = _REGISTRY.get(dt) or _REGISTRY.get(DEFAULT_DOC_TYPE, {})
    spec = task_map.get(trig) or task_map.get("describe") or TASK_DESCRIBE
    return spec.normalized(page_meta)


# ----------------------- Convenience decisions ----------------------- #

def auto_trigger_for_doc_type(doc_type: str) -> str:
    """
    If system needs to decide *one* best-effort trigger for a doc_type:
    - drawings/plans → spatial_index
    - everything else → describe
    """
    dt = (doc_type or "").lower()
    if dt in ("drawing", "plan", "floor_plan"):
        return "spatial_index"
    return "describe"
