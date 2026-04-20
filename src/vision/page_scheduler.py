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
page_scheduler — SMART page picker for Vision queueing.

Goals
-----
- "force" policy: pass-through first N pages (bounded by max_pages).
- "smart" policy: prioritize pages that likely need vision help:
    * lower text_quality  -> higher priority
    * image-like pages    -> boost
    * pages missing OCR   -> boost
    * short/no text hints -> small boost
- Stable + idempotent: ties break by page_index.

Inputs
------
- vpages: List[Dict] as produced by extractors; expected keys:
    page_index:int, text_quality:float (0..1), optional:
    - is_image_page: bool
    - images / image_path / preview_path / raster_path: str/list
    - ocr_text: str (may be empty if missing)
    - text_hint: str (short text sample)
- config: PageSchedulerConfig (see below)

Outputs
-------
- List[Dict]: a subset of the *original* vpage dicts, in final queueing order.

Notes
-----
- This module is deliberately lightweight and has zero dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Sequence


__all__ = ["PageSchedulerConfig", "select_pages"]


# ---------------------------- configuration ---------------------------- #

@dataclass
class PageSchedulerConfig:
    max_pages: int = 200
    text_quality_threshold: float = 0.55
    prefer_unocr: bool = True          # prefer pages that lack ocr_text
    boost_image_pages: float = 0.15    # additive boost if page looks image-like
    boost_missing_ocr: float = 0.20    # additive boost if no/empty ocr_text
    boost_low_quality: float = 0.25    # additive boost when below threshold
    boost_short_hint: float = 0.05     # tiny boost if text_hint very short
    clamp_min_quality: float = 0.0
    clamp_max_quality: float = 1.0


# ------------------------------ utilities ----------------------------- #

_CAND_IMAGE_KEYS = ("image_path", "raster_path", "preview_path", "png", "jpg", "image", "images")

def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default

def _safe_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except Exception:
        return default

def _looks_image_like(vp: Dict[str, Any]) -> bool:
    if vp.get("is_image_page") is True:
        return True
    for k in _CAND_IMAGE_KEYS:
        if k in vp:
            return True
    txt = vp.get("text") or ""
    if isinstance(txt, str) and len(txt.strip()) < 15:
        return True
    return False

def _has_ocr(vp: Dict[str, Any]) -> bool:
    t = vp.get("ocr_text")
    return isinstance(t, str) and len(t.strip()) > 0

def _short_hint(vp: Dict[str, Any]) -> bool:
    h = vp.get("text_hint")
    return isinstance(h, str) and len(h.strip()) < 20


# ---------------------------- scoring logic ---------------------------- #

def _score_page(vp: Dict[str, Any], cfg: PageSchedulerConfig) -> float:
    """
    Convert page features to a priority score in [0, 1.5]-ish.
    Higher => should enqueue earlier.
    Base score inverts text_quality so that lower quality => higher base.
    """
    q = _safe_float(vp.get("text_quality"), 0.0)
    if q < cfg.clamp_min_quality:
        q = cfg.clamp_min_quality
    if q > cfg.clamp_max_quality:
        q = cfg.clamp_max_quality

    # base priority: inverse quality
    base = 1.0 - q

    # boosts
    boost = 0.0
    if q < cfg.text_quality_threshold:
        boost += cfg.boost_low_quality
    if _looks_image_like(vp):
        boost += cfg.boost_image_pages
    if cfg.prefer_unocr and not _has_ocr(vp):
        boost += cfg.boost_missing_ocr
    if _short_hint(vp):
        boost += cfg.boost_short_hint

    return base + boost


# ------------------------------ API surface --------------------------- #

def select_pages(vpages: Sequence[Dict[str, Any]] | None,
                 *,
                 policy: str = "smart",
                 config: PageSchedulerConfig | None = None) -> List[Dict[str, Any]]:
    """
    Choose which pages to enqueue for Vision.

    Parameters
    ----------
    vpages : sequence of page dicts
    policy : "smart" | "force"
    config : PageSchedulerConfig

    Returns
    -------
    List[Dict[str, Any]]  # original items in the chosen order
    """
    vpages = list(vpages or [])
    cfg = config or PageSchedulerConfig()
    cap = max(0, int(cfg.max_pages))

    if not vpages or cap == 0:
        return []

    if policy == "force":
        # maintain natural order, just cap
        out = vpages[:cap]
        # sanity: ensure page_index is int for downstream users
        for vp in out:
            vp["page_index"] = _safe_int(vp.get("page_index"), 0)
        return out

    # SMART policy: score & sort desc by score, asc by page_index for tie-breaks
    scored = []
    for vp in vpages:
        idx = _safe_int(vp.get("page_index"), 0)
        score = _score_page(vp, cfg)
        scored.append((score, idx, vp))

    # sort: highest score first, then lowest page index
    scored.sort(key=lambda t: (-t[0], t[1]))

    picked: List[Dict[str, Any]] = []
    seen = set()
    for _score, _idx, vp in scored:
        idx = _safe_int(vp.get("page_index"), 0)
        if idx in seen:
            continue
        seen.add(idx)
        vp["page_index"] = idx  # normalize
        picked.append(vp)
        if len(picked) >= cap:
            break

    return picked
