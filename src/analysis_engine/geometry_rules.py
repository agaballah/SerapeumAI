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
geometry_rules — centralized CAD heuristics & geometric helpers.

All geometry assumptions live here to keep the extractor clean.
"""

from __future__ import annotations

import math
from typing import Dict, Sequence

# ----------------------------- tolerances ----------------------------- #

TOL = 1e-9
PARALLEL_TOL_DEG = 3.0
CLOSE_PT_TOL = 1e-3  # drawing units

# Thickness banding (in mm)
# Tune these to your region/practice.
THICKNESS_BANDS_MM = [
    (0, 20,  "glass"),        # 6–12 mm double-line on GL layer often glass
    (40, 90, "light_partition"),
    (90, 150, "blockwork"),   # ~100–150 mm
    (150, 260, "concrete"),   # ~200–250 mm walls
    (260, 500, "heavy_concrete"),
]

# Layer name → material hint
LAYER_MATERIAL_HINTS: Dict[str, str] = {
    "GLASS": "glass",
    "GLZ": "glass",
    "ALUM": "aluminum",
    "WALL": "wall",
    "MASON": "blockwork",
    "BLOCK": "blockwork",
    "BRK": "brick",
    "CONC": "concrete",
    "RC": "concrete",
    "SLAB": "concrete",
    "STR": "structural",
}


# --------------------------- basic geometry --------------------------- #

def line_length(p1: Sequence[float], p2: Sequence[float]) -> float:
    return math.hypot(float(p2[0]) - float(p1[0]), float(p2[1]) - float(p1[1]))

def line_angle_deg(p1: Sequence[float], p2: Sequence[float]) -> float:
    dx = float(p2[0]) - float(p1[0])
    dy = float(p2[1]) - float(p1[1])
    ang = math.degrees(math.atan2(dy, dx))
    return ang % 180.0  # parallel invariant under 180° flip

def angle_diff_deg(a: float, b: float) -> float:
    d = abs((a - b) % 180.0)
    return min(d, 180.0 - d)

def is_parallel(line_a, line_b, tol_deg: float = PARALLEL_TOL_DEG) -> bool:
    a = line_angle_deg(line_a.p1, line_a.p2)
    b = line_angle_deg(line_b.p1, line_b.p2)
    return angle_diff_deg(a, b) <= tol_deg

def lines_min_distance(a1, a2, b1, b2) -> float:
    """Minimal distance between two segments (drawing units)."""
    # Using endpoint-to-segment distances (good enough here)
    return min(
        _pt_seg_dist(a1, b1, b2),
        _pt_seg_dist(a2, b1, b2),
        _pt_seg_dist(b1, a1, a2),
        _pt_seg_dist(b2, a1, a2),
    )

def _pt_seg_dist(p, a, b) -> float:
    ax, ay = float(a[0]), float(a[1])
    bx, by = float(b[0]), float(b[1])
    px, py = float(p[0]), float(p[1])
    vx, vy = bx - ax, by - ay
    wx, wy = px - ax, py - ay
    vv = vx * vx + vy * vy
    if vv <= TOL:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, (wx * vx + wy * vy) / vv))
    cx, cy = ax + t * vx, ay + t * vy
    return math.hypot(px - cx, py - cy)

def should_close_polyline(pts: Sequence[Sequence[float]]) -> bool:
    if not pts:
        return False
    d = math.hypot(float(pts[0][0]) - float(pts[-1][0]), float(pts[0][1]) - float(pts[-1][1]))
    return d <= CLOSE_PT_TOL

def polygon_area(pts: Sequence[Sequence[float]]) -> float:
    if len(pts) < 3:
        return 0.0
    s = 0.0
    for i in range(len(pts)):
        x1, y1 = float(pts[i][0]), float(pts[i][1])
        x2, y2 = float(pts[(i + 1) % len(pts)][0]), float(pts[(i + 1) % len(pts)][1])
        s += x1 * y2 - x2 * y1
    return 0.5 * s


# --------------------------- unit inference --------------------------- #

def infer_units_from_extents(minxy, maxxy) -> tuple[str, float]:
    """
    Guess units from drawing extents (extremely heuristic):
    - Small extents (~tens) look like meters.
    - Large extents (~thousands) look like millimeters.
    Returns (label, scale_to_mm).
    """
    dx = abs(float(maxxy[0]) - float(minxy[0]))
    dy = abs(float(maxxy[1]) - float(minxy[1]))
    ref = max(dx, dy)
    if ref <= 0:
        return "drawing", 1.0
    if ref < 150.0:           # <= ~150 → meters-ish
        return "m", 1000.0
    if ref < 150_000.0:       # 150 .. 150k → millimeters-ish
        return "mm", 1.0
    return "drawing", 1.0


# ---------------------------- wall heuristics -------------------------- #

def parallel_thickness_mm(a1, a2, b1, b2, units_scale_to_mm: float) -> float:
    """
    Estimate wall thickness from two parallel segments (minimal distance).
    """
    d_units = lines_min_distance(a1, a2, b1, b2)
    return float(d_units) * float(units_scale_to_mm)

def classify_wall_kind(thickness_mm: float, layer_name: str) -> tuple[str, float, list[str]]:
    """
    Map thickness + layer hints to a (kind, confidence, reasons).
    """
    lname = (layer_name or "").upper()
    hints = []
    if lname:
        for key, mat in LAYER_MATERIAL_HINTS.items():
            if key in lname:
                hints.append(f"layer:{key}->{mat}")

    # Band lookup
    label = "unknown"
    for lo, hi, tag in THICKNESS_BANDS_MM:
        if lo <= thickness_mm < hi:
            label = tag
            break

    conf = 0.55 if label != "unknown" else 0.35
    if hints:
        conf += 0.2
    conf = max(0.0, min(0.98, conf))
    return label, conf, hints

def thickness_band_debug(thk: float) -> str:
    return f"thickness={thk:.1f}mm bands={THICKNESS_BANDS_MM}"
