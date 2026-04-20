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
bim_query_tool.py — BIM Query Tool for LLM Tool Calling
--------------------------------------------------------

Enables the LLM to query structured BIM data from the database.
Part of Sprint 3: The "Thinker" (Chat UI & Agentic Workflows).
"""

from typing import Any, Dict, Optional
from src.tools.base_tool import BaseTool


class BIMQueryTool(BaseTool):
    """Tool for querying BIM elements from the database."""
    
    def __init__(self, db):
        """
        Initialize BIM query tool.
        
        Args:
            db: DatabaseManager instance
        """
        self.db = db
    
    @property
    def name(self) -> str:
        return "query_bim"
    
    @property
    def description(self) -> str:
        return (
            "Query BIM (Building Information Model) elements from IFC files. "
            "Use this to count or list building elements like doors, windows, walls, columns, etc. "
            "Can filter by element type and level/floor."
        )
    
    def execute(
        self,
        element_type: Optional[str] = None,
        level: Optional[str] = None,
        count_only: bool = False,
        **kwargs
    ) -> str:
        """
        Execute BIM query.
        
        Args:
            element_type: IFC element type (e.g., "IfcDoor", "IfcWindow")
            level: Building level (e.g., "Level 1", "Level 3")
            count_only: If True, return count only; if False, return list
            
        Returns:
            Formatted string with query results
        """
        try:
            # Build filters
            filters = {}
            if element_type:
                filters["element_type"] = element_type
            if level:
                filters["level"] = level
            
            # Execute query
            if count_only:
                count = self.db.count_bim_elements(**filters)
                
                # Format response
                if element_type and level:
                    return f"Found {count} {element_type} on {level}."
                elif element_type:
                    return f"Found {count} {element_type} in the project."
                elif level:
                    return f"Found {count} elements on {level}."
                else:
                    return f"Found {count} BIM elements in total."
            
            else:
                # Return list of elements
                elements = self.db.query_bim_elements(**filters, limit=20)
                
                if not elements:
                    return "No BIM elements found matching the criteria."
                
                lines = [f"Found {len(elements)} BIM elements:"]
                for i, elem in enumerate(elements[:10], 1):
                    name = elem.get("name", "Unnamed")
                    elem_type = elem.get("element_type", "Unknown")
                    elem_level = elem.get("level", "Unknown")
                    lines.append(f"{i}. {name} ({elem_type}) - {elem_level}")
                
                if len(elements) > 10:
                    lines.append(f"... and {len(elements) - 10} more")
                
                return "\n".join(lines)
        
        except Exception as e:
            return f"Error querying BIM data: {str(e)}"
    
    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "element_type": {
                    "type": "string",
                    "description": (
                        "IFC element type to filter by. Common types: "
                        "IfcDoor, IfcWindow, IfcWall, IfcColumn, IfcBeam, IfcSlab, IfcStair, IfcRoof"
                    ),
                    "enum": [
                        "IfcDoor", "IfcWindow", "IfcWall", "IfcColumn",
                        "IfcBeam", "IfcSlab", "IfcStair", "IfcRoof", "IfcSpace"
                    ]
                },
                "level": {
                    "type": "string",
                    "description": "Building level/floor to filter by (e.g., 'Level 1', 'Level 3')"
                },
                "count_only": {
                    "type": "boolean",
                    "description": "If true, return only the count; if false, return a list of elements",
                    "default": False
                }
            },
            "required": []
        }
