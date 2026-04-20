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
schedule_query_tool.py — Schedule Query Tool for LLM Tool Calling
------------------------------------------------------------------

Enables the LLM to query structured schedule data from the database.
Part of Sprint 3: The "Thinker" (Chat UI & Agentic Workflows).
"""

from typing import Any, Dict, Optional
from src.tools.base_tool import BaseTool


class ScheduleQueryTool(BaseTool):
    """Tool for querying schedule activities from the database."""
    
    def __init__(self, db):
        """
        Initialize schedule query tool.
        
        Args:
            db: DatabaseManager instance
        """
        self.db = db
    
    @property
    def name(self) -> str:
        return "query_schedule"
    
    @property
    def description(self) -> str:
        return (
            "Query construction schedule activities from Primavera P6 or MS Project files. "
            "Use this to find critical path activities, delayed tasks, or get activity counts. "
            "Can filter by criticality status."
        )
    
    def execute(
        self,
        is_critical: Optional[bool] = None,
        count_only: bool = False,
        **kwargs
    ) -> str:
        """
        Execute schedule query.
        
        Args:
            is_critical: Filter by critical path (True for critical activities only)
            count_only: If True, return count only; if False, return list
            
        Returns:
            Formatted string with query results
        """
        try:
            # Build filters
            filters = {}
            if is_critical is not None:
                filters["is_critical"] = is_critical
            
            # Execute query
            if count_only:
                count = self.db.count_schedule_activities(**filters)
                
                # Format response
                if is_critical:
                    return f"Found {count} critical path activities."
                else:
                    return f"Found {count} schedule activities in total."
            
            else:
                # Return list of activities
                activities = self.db.query_schedule_activities(**filters, limit=20)
                
                if not activities:
                    return "No schedule activities found matching the criteria."
                
                lines = []
                if is_critical:
                    lines.append(f"Found {len(activities)} critical path activities:")
                else:
                    lines.append(f"Found {len(activities)} schedule activities:")
                
                for i, act in enumerate(activities[:15], 1):
                    name = act.get("activity_name", "Unnamed")
                    code = act.get("activity_code", "")
                    is_crit = act.get("is_critical", 0)
                    start = act.get("start_date", "")
                    finish = act.get("finish_date", "")
                    
                    crit_marker = " [CRITICAL]" if is_crit else ""
                    date_range = f"{start} to {finish}" if start and finish else ""
                    
                    if code:
                        lines.append(f"{i}. {code}: {name}{crit_marker}")
                    else:
                        lines.append(f"{i}. {name}{crit_marker}")
                    
                    if date_range:
                        lines.append(f"   Dates: {date_range}")
                
                if len(activities) > 15:
                    lines.append(f"... and {len(activities) - 15} more")
                
                return "\n".join(lines)
        
        except Exception as e:
            return f"Error querying schedule data: {str(e)}"
    
    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "is_critical": {
                    "type": "boolean",
                    "description": (
                        "Filter by critical path status. "
                        "Set to true to get only critical path activities, "
                        "false for non-critical, or omit to get all activities."
                    )
                },
                "count_only": {
                    "type": "boolean",
                    "description": "If true, return only the count; if false, return a list of activities",
                    "default": False
                }
            },
            "required": []
        }
