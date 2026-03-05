# -*- coding: utf-8 -*-
import math
from typing import List, Dict, Any

def calculate_distance(p1: List[float], p2: List[float]) -> float:
    """Calculate Euclidean distance between two points [x, y]."""
    return math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)

def calculate_polygon_area(points: List[List[float]]) -> float:
    """Shoelace formula for polygon area."""
    if len(points) < 3:
        return 0.0
    area = 0.0
    for i in range(len(points)):
        j = (i + 1) % len(points)
        area += points[i][0] * points[j][1]
        area -= points[j][0] * points[i][1]
    return abs(area) / 2.0

def calculate_polygon_perimeter(points: List[List[float]]) -> float:
    """Calculate the perimeter of a polygon."""
    perimeter = 0.0
    for i in range(len(points)):
        j = (i + 1) % len(points)
        perimeter += calculate_distance(points[i], points[j])
    return round(perimeter, 2)

def find_rooms_in_geometry(entities: List[Dict[str, Any]], room_layers: List[str] = None) -> List[Dict[str, Any]]:
    """
    Identify rooms based on closed polylines on specific layers.
    """
    if room_layers is None:
        room_layers = ["ROOM", "SPACE", "AREA", "ZONE", "A-AREA", "A-ROOM"]
    
    room_layers = [layer.upper() for layer in room_layers]
    rooms = []
    
    for e in entities:
        if e.get("type") == "polyline" and e.get("closed"):
            layer = e.get("layer", "").upper()
            if any(x in layer for x in room_layers):
                area = calculate_polygon_area(e["points"])
                if area > 1.0: # Filter out tiny artifacts
                    rooms.append({
                        "type": "room",
                        "layer": layer,
                        "area_m2": round(area, 2),
                        "perimeter_m": calculate_polygon_perimeter(e["points"])
                    })
    return rooms

def find_walls_in_geometry(entities: List[Dict[str, Any]], wall_layers: List[str] = None) -> List[Dict[str, Any]]:
    """
    Identify walls based on parallel lines or specific layers.
    """
    if wall_layers is None:
        wall_layers = ["WALL", "A-WALL", "PARTITION"]
        
    wall_layers = [layer.upper() for layer in wall_layers]
    walls = []
    
    for e in entities:
        if e.get("type") == "line":
            layer = e.get("layer", "").upper()
            if any(x in layer for x in wall_layers):
                length = calculate_distance(e["start"], e["end"])
                walls.append({
                    "type": "wall",
                    "layer": layer,
                    "length_m": round(length, 2)
                })
    return walls
