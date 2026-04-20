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
import src.utils.geometry_utils as geom_utils

class GeometryAnalyzer:
    def __init__(self):
        pass

    def analyze(self, geometry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze raw geometry to find semantic objects.
        """
        entities = geometry.get("entities", [])
        
        rooms = geom_utils.find_rooms_in_geometry(entities)
        walls = geom_utils.find_walls_in_geometry(entities)
        
        return {
            "rooms": rooms,
            "walls": walls,
            "summary": f"Found {len(rooms)} rooms and {len(walls)} wall segments."
        }
