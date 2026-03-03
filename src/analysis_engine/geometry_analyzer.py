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
geometry_analyzer.py — Interpret extracted CAD geometry
-------------------------------------------------------
Identifies semantic objects like Rooms and Walls from raw lines/polylines.
"""

from typing import List, Dict, Any
import math

class GeometryAnalyzer:
    def __init__(self):
        pass

    def analyze(self, geometry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze raw geometry to find semantic objects.
        """
        entities = geometry.get("entities", [])
        
        rooms = self._find_rooms(entities)
        walls = self._find_walls(entities)
        
        return {
            "rooms": rooms,
            "walls": walls,
            "summary": f"Found {len(rooms)} rooms and {len(walls)} wall segments."
        }

    def _find_rooms(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Identify rooms based on closed polylines on specific layers.
        """
        rooms = []
        # Common room layers (heuristic)
        room_layers = {"ROOM", "SPACE", "AREA", "ZONE", "A-AREA", "A-ROOM"}
        
        for e in entities:
            if e["type"] == "polyline" and e.get("closed"):
                layer = e.get("layer", "").upper()
                if any(x in layer for x in room_layers):
                    area = self._calculate_area(e["points"])
                    if area > 1.0: # Filter out tiny artifacts
                        rooms.append({
                            "type": "room",
                            "layer": layer,
                            "area_m2": round(area, 2),
                            "perimeter_m": self._calculate_perimeter(e["points"])
                        })
        return rooms

    def _find_walls(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Identify walls based on parallel lines or specific layers.
        """
        walls = []
        wall_layers = {"WALL", "A-WALL", "PARTITION"}
        
        for e in entities:
            if e["type"] == "line":
                layer = e.get("layer", "").upper()
                if any(x in layer for x in wall_layers):
                    length = self._distance(e["start"], e["end"])
                    walls.append({
                        "type": "wall",
                        "layer": layer,
                        "length_m": round(length, 2)
                    })
        return walls

    def _calculate_area(self, points: List[List[float]]) -> float:
        """Shoelace formula for polygon area."""
        if len(points) < 3:
            return 0.0
        area = 0.0
        for i in range(len(points)):
            j = (i + 1) % len(points)
            area += points[i][0] * points[j][1]
            area -= points[j][0] * points[i][1]
        return abs(area) / 2.0

    def _calculate_perimeter(self, points: List[List[float]]) -> float:
        perimeter = 0.0
        for i in range(len(points)):
            j = (i + 1) % len(points)
            perimeter += self._distance(points[i], points[j])
        return round(perimeter, 2)

    def _distance(self, p1: List[float], p2: List[float]) -> float:
        return math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
