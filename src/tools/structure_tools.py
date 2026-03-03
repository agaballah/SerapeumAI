# -*- coding: utf-8 -*-
"""
structure_tools.py — Hierarchical Navigation for World-Class Engineering.
Protocol v1.1 compliant: returns structured data only.
"""

from typing import Any, Dict, List, Optional
from src.tools.base_tool import BaseTool
from src.infra.persistence.database_manager import DatabaseManager

class SearchHeadingsTool(BaseTool):
    """Tool for finding sections/headings in the document structure."""
    
    def __init__(self, db: DatabaseManager):
        self.db = db

    @property
    def name(self) -> str:
        return "search_headings"

    @property
    def description(self) -> str:
        return (
            "Search for document sections by heading title (e.g., 'Fire Alarm', '26 00 00'). "
            "Returns a list of matching headings with their IDs and Levels. "
            "Use this to find WHERE a topic is covered before reading it."
        )

    def execute(self, query: str, doc_ids: Optional[List[str]] = None, **kwargs) -> List[Dict[str, Any]]:
        """Search document headings and return structured results.

        Returns:
            List of dicts with keys: doc_id, block_id, heading_number, heading_title, level, snippet, score
            Empty list if no results found.
        """
        try:
            # FTS5 robust query
            fts_query = f'"{query}"' if " " in query and not '"' in query else query
            
            if doc_ids:
                placeholder = ','.join(['?'] * len(doc_ids))
                sql = f"""
                    SELECT b.doc_id, b.block_id, b.heading_number, b.heading_title, b.level, b.text,
                           snippet(doc_blocks_fts, 4, '<b>', '</b>', '...', 32) as snippet,
                           bm25(doc_blocks_fts) as score
                    FROM doc_blocks_fts f
                    JOIN doc_blocks b ON f.doc_id = b.doc_id AND f.block_id = b.block_id
                    WHERE doc_blocks_fts MATCH ? AND b.doc_id IN ({placeholder})
                    ORDER BY score ASC
                    LIMIT 20
                """
                rows = self.db._query(sql, (fts_query, *doc_ids))
            else:
                sql = """
                    SELECT b.doc_id, b.block_id, b.heading_number, b.heading_title, b.level, b.text,
                           snippet(doc_blocks_fts, 4, '<b>', '</b>', '...', 32) as snippet,
                           bm25(doc_blocks_fts) as score
                    FROM doc_blocks_fts f
                    JOIN doc_blocks b ON f.doc_id = b.doc_id AND f.block_id = b.block_id
                    WHERE doc_blocks_fts MATCH ?
                    ORDER BY score ASC
                    LIMIT 20
                """
                rows = self.db._query(sql, (fts_query,))
            
            if not rows:
                return []
                
            results: List[Dict[str, Any]] = []
            for r in rows:
                doc_id, block_id, h_num, h_title, lvl, text, snippet, score = r
                results.append({
                    "doc_id": doc_id,
                    "block_id": block_id,
                    "heading_number": h_num,
                    "heading_title": h_title,
                    "level": lvl,
                    "snippet": snippet,
                    "score": float(score) if score is not None else 0.0,
                })
            return results

        except Exception:
            raise

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The section title or keyword to find."
                },
                "doc_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of document IDs to scope the search."
                }
            },
            "required": ["query"]
        }


class ReadSectionTool(BaseTool):
    """Tool for reading a full section (including children) by Block ID."""
    
    def __init__(self, db: DatabaseManager):
        self.db = db

    @property
    def name(self) -> str:
        return "read_section"

    @property
    def description(self) -> str:
        return (
            "Read a specific section AND its content. "
            "Provide a 'block_id' (found via search_headings). "
            "This returns the section text and the text of immediate children."
        )

    def execute(self, block_id: str, **kwargs) -> Dict[str, Any]:
        """Read a section and return structured content.

        Returns:
            Dict with keys: doc_id, block_id, title, text, children
            Or dict with "error" key if section not found.
        """
        try:
            # 1. Get the target block info
            target = self.db._query_one("SELECT doc_id, heading_number, heading_title, level, text FROM doc_blocks WHERE block_id = ?", (block_id,))
            
            if not target:
                return {"error": "not_found", "block_id": block_id}
                
            doc_id, target_num, target_title, target_lvl, target_text = target
            
            # 2. Get children if heading number exists
            children: List[Dict[str, Any]] = []
            if target_num:
                sql_children = """
                    SELECT heading_number, heading_title, text 
                    FROM doc_blocks 
                    WHERE doc_id = ? 
                    AND heading_number LIKE ? 
                    AND level > ?
                    ORDER BY rowid ASC
                """
                child_rows = self.db._query(sql_children, (doc_id, f"{target_num}%", target_lvl))
                
                for c in child_rows:
                    children.append({
                        "heading_number": c["heading_number"],
                        "heading_title": c["heading_title"],
                        "text": c["text"]
                    })
            
            return {
                "doc_id": doc_id,
                "block_id": block_id,
                "title": f"{target_num or ''} {target_title or ''}".strip(),
                "text": target_text or "",
                "children": children
            }

        except Exception:
            raise

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "block_id": {
                    "type": "string",
                    "description": "The specific Block ID of the section to read."
                }
            },
            "required": ["block_id"]
        }
