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
quality_assessor — unified quality scoring for modern (DeepSeek/OCR + VLA agent) pipeline.

Scores only what still exists in the new architecture:
- text_quality        : extracted text richness (characters, density)
- layout_understanding: VLM semantic understanding (rooms/spaces/relations)
- entity_quality      : entity extraction coverage (EntityAnalyzer output)
- reasoning_quality   : agent-based reasoning completeness (comments, findings)
- compliance_quality  : issues severity snapshot from ComplianceAnalyzer

All scores 0..10.
Overall = average (rounded).
"""

from __future__ import annotations
from typing import Any, Dict, List

def _clip01(x: float) -> float:
    return max(0.0, min(1.0, x))

# ----------------------------------------------------------------------
# TEXT QUALITY (DeepSeek OCR + extraction)
# ----------------------------------------------------------------------
def _score_text(chars: int) -> float:
    # 0 → 0/10
    # >20k → 10/10
    c = _clip01(chars / 20000.0)
    return round(10.0 * c, 2)

# ----------------------------------------------------------------------
# VISION / LAYOUT UNDERSTANDING (Qwen-VL or vision agent)
# ----------------------------------------------------------------------
def _score_layout(layout: Dict[str, Any]) -> float:
    """
    layout = {
      "rooms": [...],
      "walls": [...],
      "connections": [...],
      "comments": [...]
    }
    Missing keys allowed.
    """
    rooms = len(layout.get("rooms", []))
    conns = len(layout.get("connections", []))
    # If model saw rooms + relationships → OK
    base = 0.4 * _clip01(rooms / 10.0) + 0.6 * _clip01(conns / 10.0)
    return round(10.0 * base, 2)

# ----------------------------------------------------------------------
# ENTITY QUALITY
# ----------------------------------------------------------------------
def _score_entities(ents: List[Dict[str, Any]]) -> float:
    """
    Expect canonical entities:
      {"type": "...", "name": "..."}
    """
    count = len(ents)
    # 0 → 0/10
    # >= 40 → 10/10
    return round(10.0 * _clip01(count / 40.0), 2)

# ----------------------------------------------------------------------
# REASONING QUALITY (agent’s findings / design comments)
# ----------------------------------------------------------------------
def _score_reasoning(findings: List[Dict[str, Any]]) -> float:
    """
    findings example:
      [{"severity":"info|warn|error", "message":"..."}]
    """
    if not findings:
        return 0.0
    info = sum(1 for f in findings if str(f.get("severity","")).lower()=="info")
    warn = sum(1 for f in findings if str(f.get("severity","")).lower()=="warning")
    err  = sum(1 for f in findings if str(f.get("severity","")).lower()=="error")
    total = max(1, info + warn + err)
    # fewer high severity → higher score
    penalty = (2*err + warn) / total
    score = 10.0 * (1.0 - _clip01(penalty))
    return round(score, 2)

# ----------------------------------------------------------------------
# COMPLIANCE QUALITY
# ----------------------------------------------------------------------
def _score_compliance(issues: List[Dict[str, Any]]) -> float:
    """
    issues: [{"severity":"warning|error|info", ...}]
    """
    if not issues:
        return 10.0
    warn = sum(1 for i in issues if str(i.get("severity","")).lower() == "warning")
    err  = sum(1 for i in issues if str(i.get("severity","")).lower() == "error")
    total = warn + err
    if total <= 0:
        return 10.0
    return round(10.0 * _clip01(1.0 / (1.0 + total / 5.0)), 2)

# ----------------------------------------------------------------------
# MAIN FUNCTION
# ----------------------------------------------------------------------
def evaluate(
    *,
    document_text: str,
    layout: Dict[str, Any] | None,
    entities: List[Dict[str, Any]] | None,
    findings: List[Dict[str, Any]] | None,
    compliance_issues: List[Dict[str, Any]] | None,
) -> Dict[str, Any]:

    chars = len(document_text or "")
    layout = layout or {}
    entities = list(entities or [])
    findings = list(findings or [])
    compliance = list(compliance_issues or [])

    s_text   = _score_text(chars)
    s_layout = _score_layout(layout)
    s_ents   = _score_entities(entities)
    s_reason = _score_reasoning(findings)
    s_comp   = _score_compliance(compliance)

    dims = {
        "text_quality": s_text,
        "layout_understanding": s_layout,
        "entity_quality": s_ents,
        "reasoning_quality": s_reason,
        "compliance_quality": s_comp,
    }

    overall = round(sum(dims.values()) / len(dims), 1)

    return {
        "score": overall,
        "dimensions": dims,
        "advice": _make_advice(dims)
    }

# ----------------------------------------------------------------------
# ADVICE
# ----------------------------------------------------------------------
def _make_advice(dims: Dict[str, float]) -> List[str]:
    out: List[str] = []

    if dims["text_quality"] < 7.5:
        out.append("Enhance OCR or provide clearer scans for text extraction.")
    if dims["layout_understanding"] < 7.0:
        out.append("Use more pages or higher-quality drawings for layout understanding.")
    if dims["entity_quality"] < 7.0:
        out.append("Improve labeling or provide additional context for entity extraction.")
    if dims["reasoning_quality"] < 7.0:
        out.append("Provide more details so the agent can produce deeper design reasoning.")
    if dims["compliance_quality"] < 7.5:
        out.append("Resolve compliance warnings/errors for a higher score.")

    return out
