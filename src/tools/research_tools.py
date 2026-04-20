# -*- coding: utf-8 -*-
"""
research_tools.py — Agentic Research Capabilities
-------------------------------------------------
Provides functionality for the LLM to autonomously explore the project data.
Protocol v1.1: SearchPagesTool returns structured data.
"""

from typing import Any, Dict, List, Optional
from src.tools.base_tool import BaseTool
from src.infra.persistence.database_manager import DatabaseManager

class DocumentSearchTool(BaseTool):
    """Tool for searching the project knowledge base."""
    
    def __init__(self, db: DatabaseManager):
        self.db = db

    @property
    def name(self) -> str:
        return "search_documents"

    @property
    def description(self) -> str:
        return (
            "Search for documents or specific content by keywords. "
            "Use this to find relevant files when you don't know the exact document name. "
            "Returns a list of matching documents with snippets."
        )

    def execute(self, query: str, **kwargs) -> str:
        try:
            # 1. Try Block-Level Search (Granular)
            blocks = self.db.search_doc_blocks(query, limit=10)
            if blocks:
                results = ["Found matching content in the following documents:"]
                seen_docs = set()
                
                for b in blocks:
                    doc_id = b["doc_id"]
                    filename = b.get("file_name", f"Doc {doc_id}") 
                    snippet = b.get("text", "")[:200].replace("\n", " ")
                    
                    results.append(f"- [{filename}] (ID: {doc_id}): \"{snippet}...\"")
                    seen_docs.add(doc_id)
                
                return "\n".join(results)

            # 2. Fallback to Document-Level Search
            docs = self.db.search_documents(query, limit=10)
            if docs:
                results = ["Found matching documents:"]
                for d in docs:
                    results.append(f"- {d['file_name']} (ID: {d['doc_id']})")
                return "\n".join(results)
            
            return "No documents found matching that query."

        except Exception as e:
            return f"Error searching documents: {str(e)}"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search keywords or phrase (e.g. 'foundation specifications', 'ground floor plan')"
                }
            },
            "required": ["query"]
        }


class DocumentReadTool(BaseTool):
    """Tool for reading the full content of a specific document."""
    
    def __init__(self, db: DatabaseManager):
        self.db = db

    @property
    def name(self) -> str:
        return "read_document"

    @property
    def description(self) -> str:
        return (
            "Read the full content of a specific document. "
            "Use this AFTER finding a document ID via search_documents. "
            "Returns the full text, including AI vision descriptions of drawings."
        )

    def execute(self, doc_id: str = None, filename: str = None, **kwargs) -> str:
        try:
            target_id = doc_id
            
            # Resolve filename to doc_id if needed
            if not target_id and filename:
                docs = self.db.search_documents(filename, limit=1)
                if docs:
                    target_id = docs[0]["doc_id"]
            
            if not target_id:
                return "Error: You must provide a valid 'doc_id' or exact 'filename'."

            # Use the "Core Fix" payload method which includes Vision
            payload = self.db.get_document_payload(target_id)
            content = payload.get("text", "")
            
            if not content:
                return "The document appears to be empty."
                
            # Truncate slightly to fit context window if massive
            max_len = 50000 
            if len(content) > max_len:
                return f"{content[:max_len]}\n\n[... Document truncated at {max_len} characters ...]"
            
            return content

        except Exception as e:
            return f"Error reading document: {str(e)}"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "doc_id": {
                    "type": "string",
                    "description": "The unique ID of the document to read (preferred)."
                },
                "filename": {
                    "type": "string",
                    "description": "The name of the file to read (if doc_id is unknown)."
                }
            },
            "required": [] 
        }

class WebSearchTool(BaseTool):
    """Tool for performing online research (Google/Bing/etc)."""
    
    def __init__(self, config_manager=None):
        self.config = config_manager

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return (
            "Search the internet for AECO standards, technical benchmarks, or international codes. "
            "Use this when local project documents don't have the answer for a general technical question."
        )

    def execute(self, query: str, **kwargs) -> Dict[str, Any]:
        try:
            print(f"[WebSearch] Querying: {query}")
            
            # MOCK IMPLEMENTATION for demonstration
            if "ANSI-TIA 942" in query:
                return {
                    "source": "web_search",
                    "query": query,
                    "results": [
                        {
                            "title": "ANSI/TIA-942-B (2017)",
                            "description": "Telecommunications Infrastructure Standard for Data Centers. Specifies minimum requirements for telecommunications infrastructure."
                        },
                        {
                            "title": "Tier III Requirements",
                            "description": "Requires 'Concurrently Maintainable' infrastructure. Capacities can be serviced without disruption."
                        },
                        {
                            "title": "HVAC Requirements",
                            "description": "N+1 cooling requirements and humidity ranges (18°C to 27°C)."
                        }
                    ]
                }
            
            return {
                "source": "web_search",
                "query": query,
                "results": [],
                "message": f"No specific online results found for '{query}'."
            }

        except Exception as e:
            return {"error": str(e)}

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The technical query or benchmark to search for."
                }
            },
            "required": ["query"]
        }

class SearchPagesTool(BaseTool):
    """Tool for granular page-level full-text search. Protocol v1.1 compliant."""
    
    def __init__(self, db: DatabaseManager):
        self.db = db

    @property
    def name(self) -> str:
        return "search_pages"

    @property
    def description(self) -> str:
        return (
            "Highly granular search within individual pages. "
            "Use this as a last resort if search_documents and search_headings yield no results. "
            "It searches the raw extracted text (py_text, ocr_text, vision_ocr_text) for every page."
        )

    def execute(self, query: str, doc_ids: Optional[List[str]] = None, **kwargs) -> List[Dict[str, Any]]:
        """Search pages and return structured results.

        Returns:
            List of dicts with keys: doc_id, page_index, file_name, source_field, snippet, score
            Empty list if no results found.
        """
        try:
            like_q = f"%{query}%"
            if doc_ids:
                placeholder = ','.join(['?'] * len(doc_ids))
                sql = f"""
                    SELECT p.doc_id, p.page_index, d.file_name, p.py_text, p.ocr_text, 
                           p.vision_ocr_text, p.vision_general, p.vision_detailed
                    FROM pages p
                    JOIN documents d ON p.doc_id = d.doc_id
                    WHERE (p.py_text LIKE ? OR p.ocr_text LIKE ? OR p.vision_ocr_text LIKE ? 
                           OR p.vision_general LIKE ? OR p.vision_detailed LIKE ?)
                    AND p.doc_id IN ({placeholder})
                    ORDER BY p.doc_id, p.page_index ASC
                    LIMIT 10
                """
                rows = self.db._query(sql, (like_q, like_q, like_q, like_q, like_q, *doc_ids))
            else:
                sql = """
                    SELECT p.doc_id, p.page_index, d.file_name, p.py_text, p.ocr_text, 
                           p.vision_ocr_text, p.vision_general, p.vision_detailed
                    FROM pages p
                    JOIN documents d ON p.doc_id = d.doc_id
                    WHERE p.py_text LIKE ? OR p.ocr_text LIKE ? OR p.vision_ocr_text LIKE ?
                          OR p.vision_general LIKE ? OR p.vision_detailed LIKE ?
                    ORDER BY p.doc_id, p.page_index ASC
                    LIMIT 10
                """
                rows = self.db._query(sql, (like_q, like_q, like_q, like_q, like_q))
            
            if not rows:
                return []
                
            results: List[Dict[str, Any]] = []
            q_lower = query.lower()
            
            for r in rows:
                doc_id, p_idx, fname, py_txt, ocr_txt, vis_txt, vis_gen, vis_det = r
                
                # Determine source field and text
                source_field = "py_text"
                text = py_txt or ""
                
                if vis_det and q_lower in vis_det.lower():
                    source_field = "vision_detailed"
                    text = vis_det
                elif vis_gen and q_lower in vis_gen.lower():
                    source_field = "vision_general"
                    text = vis_gen
                elif vis_txt and q_lower in vis_txt.lower():
                    source_field = "vision_ocr_text"
                    text = vis_txt
                elif ocr_txt and q_lower in ocr_txt.lower():
                    source_field = "ocr_text"
                    text = ocr_txt
                
                # If query not in py_text, check others
                if q_lower not in text.lower():
                    if q_lower in (ocr_txt or "").lower():
                        text = ocr_txt
                        source_field = "ocr_text"
                    elif q_lower in (vis_txt or "").lower():
                        text = vis_txt
                        source_field = "vision_ocr_text"
                
                # Find a snippet around the query
                idx = text.lower().find(q_lower)
                start = max(0, idx - 100)
                end = min(len(text), idx + 200)
                snippet = text[start:end].replace("\n", " ")
                
                results.append({
                    "doc_id": doc_id,
                    "page_index": p_idx,
                    "file_name": fname,
                    "source_field": source_field,
                    "snippet": snippet,
                    "score": 0.0  # Simple LIKE search has no ranking
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
                    "description": "The keyword or phrase to search for on individual pages."
                },
                "doc_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of document IDs to scope the search."
                }
            },
            "required": ["query"]
        }
