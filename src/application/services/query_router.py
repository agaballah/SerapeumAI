# -*- coding: utf-8 -*-
from enum import Enum
from typing import Dict, Any

class QueryType(Enum):
    SEMANTIC = "semantic"
    STRUCTURED_BIM = "structured_bim"
    STRUCTURED_SCHEDULE = "structured_schedule"
    AUTO = "auto"

class QueryRouter:
    """Minimal restoration of QueryRouter"""
    def route_query(self, query: str) -> Dict[str, Any]:
        return {"query_type": QueryType.SEMANTIC, "original_query": query}

    def format_structured_result(self, route_result: Dict, data: Any) -> str:
        return f"Structured Result: {data}"
