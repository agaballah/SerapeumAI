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
RAGService — Retrieval Augmented Generation Service

Uses DatabaseManager's FTS capabilities to find relevant context.

NEW:
    - Prefers block-level retrieval from doc_blocks_fts (section-level chunks).
    - Falls back to document-level retrieval from documents_fts if needed.
    - HYBRID RETRIEVAL: Routes queries to semantic or structured tools based on intent.
"""

from typing import List, Dict, Optional, Any

from src.infra.persistence.database_manager import DatabaseManager
from .query_router import QueryRouter, QueryType

import logging
logger = logging.getLogger(__name__)


class RAGService:
    def __init__(self, db: DatabaseManager, global_db: Optional[DatabaseManager] = None):
        self.db = db
        self.global_db = global_db
        self.router = QueryRouter()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def retrieve_context(self, query: str, limit: int = 5) -> str:
        """
        Searches the databases for relevant content and formats it as a context string.

        Strategy:
            1) Try block-level retrieval (doc_blocks_fts) to get precise sections from Project DB.
            2) Fetch relevant standards from Global Standards DB.
            3) Combine both into a unified context.
        """
        query = (query or "").strip()
        if not query:
            return ""

        # 1) Hybrid Retrieval (Vector + Keyword)
        # ------------------------------------------------------------------
        project_ctx = ""
        try:
            from src.infra.adapters.vector_store import VectorStore
            vs = VectorStore(persist_dir=self.db.root_dir)
            
            # A. Semantic Search (The "Pinecone Mimic")
            semantic_hits = []
            if vs._initialized:
                semantic_hits = vs.similarity_search(query, k=limit)
            
            # B. Keyword/Block Search (Existing SQLite FTS)
            keyword_ctx = ""
            try:
                keyword_ctx = self._retrieve_block_level_context(query=query, limit=limit)
                if not keyword_ctx:
                    keyword_ctx = self._retrieve_document_level_context(query=query, limit=limit)
            except Exception:
                pass

			# C. Format & Merge
            # We prioritize Semantic Hits as they find "concepts"
            sections = []
            
            if semantic_hits:
                sections.append("--- SEMANTIC SEARCH RESULTS (CONCEPTUAL) ---")
                for hit in semantic_hits:
                    # hit = {text, metadata, score}
                    meta = hit.get("metadata", {})
                    doc_id = meta.get("doc_id", "??")
                    page = meta.get("page_index", 0) + 1
                    text = hit.get("text", "")
                    
                    # Try to get file name
                    doc = self.db.get_document(doc_id)
                    fname = doc.get("file_name") if doc else doc_id
                    
                    sections.append(f"[{fname} | Page {page}]:\n{text}\n")
            
            if keyword_ctx:
                 sections.append("\n--- KEYWORD SEARCH RESULTS (EXACT MATCH) ---")
                 sections.append(keyword_ctx)
            
            project_ctx = "\n".join(sections)
            
        except Exception as e:
            logger.error(f"Hybrid retrieval failed: {e}")
            # Fallback to pure legacy if vector store explodes
            try:
                project_ctx = self._retrieve_block_level_context(query, limit)
            except Exception:
                project_ctx = ""

        # 2) Global Standards Retrieval
        global_ctx = ""
        if self.global_db:
            try:
                standards = self.global_db.search_standards(query, limit=limit)
                if standards:
                    global_ctx = "\n\n--- RELEVANT GLOBAL CODES & STANDARDS ---\n"
                    for s in standards:
                        global_ctx += f"[{s['standard_id']} | {s['standard_title']} Section {s['path']}]:\n"
                        global_ctx += f"{s['text']}\n\n"
            except Exception as exc:
                logger.warning(f"Global standards retrieval failed: {exc}")

        return f"{project_ctx}\n{global_ctx}".strip()


    def retrieve_evidence(self, query: str, limit: int = 6) -> List[Dict[str, Any]]:
        """
        Return structured evidence rows for query-time candidate fact derivation.

        Phase 1 intentionally stays simple:
        - first pull page-level summaries/text (Layers 1-3)
        - then top up with doc_block text if needed
        - always include file_version_id so fact_inputs lineage can be persisted
        """
        import re

        query = (query or "").strip()
        if not query:
            return []

        terms = [t for t in re.findall(r"[A-Za-z0-9_]+", query.lower()) if len(t) > 2][:8]
        if not terms:
            terms = [query.lower()]

        evidence: List[Dict[str, Any]] = []
        seen = set()

        def _append_row(row: Dict[str, Any], kind: str):
            file_version_id = row.get("file_version_id")
            text = (row.get("evidence_text") or "").strip()
            if not file_version_id or not text:
                return
            key = (file_version_id, row.get("page_index"), text[:120])
            if key in seen:
                return
            seen.add(key)
            evidence.append(
                {
                    "file_version_id": file_version_id,
                    "source_path": row.get("source_path") or "unknown",
                    "page_index": row.get("page_index") or 0,
                    "text": text[:1200],
                    "evidence_kind": kind,
                }
            )

        # A) Page summaries / extracted text (Layers 1-3)
        try:
            page_expr = (
                "LOWER(COALESCE(p.page_summary_detailed,'') || ' ' || "
                "COALESCE(p.page_summary_short,'') || ' ' || "
                "COALESCE(p.py_text,'') || ' ' || "
                "COALESCE(p.ocr_text,''))"
            )
            page_where = " OR ".join([f"{page_expr} LIKE ?" for _ in terms])
            page_sql = f"""
                SELECT
                    p.file_version_id,
                    COALESCE(fv.source_path, 'unknown') AS source_path,
                    COALESCE(p.page_no, p.page_index, 0) AS page_index,
                    SUBSTR(
                        TRIM(
                            COALESCE(
                                NULLIF(p.page_summary_detailed, ''),
                                NULLIF(p.page_summary_short, ''),
                                NULLIF(p.py_text, ''),
                                COALESCE(p.ocr_text, '')
                            )
                        ),
                        1, 1600
                    ) AS evidence_text
                FROM pages p
                LEFT JOIN file_versions fv ON fv.file_version_id = p.file_version_id
                WHERE ({page_where})
                ORDER BY COALESCE(p.page_no, p.page_index, 0)
                LIMIT ?
            """
            page_params = [f"%{t}%" for t in terms] + [limit]
            rows = self.db.execute(page_sql, tuple(page_params)).fetchall()
            for row in rows:
                _append_row(dict(row), "page_summary")
        except Exception as exc:
            logger.debug("RAG retrieve_evidence page query failed: %s", exc)

        # B) Block-level text top-up
        if len(evidence) < limit:
            try:
                block_expr = "LOWER(COALESCE(b.text,'') || ' ' || COALESCE(b.heading_title,''))"
                block_where = " OR ".join([f"{block_expr} LIKE ?" for _ in terms])
                block_sql = f"""
                    SELECT
                        COALESCE(fv.file_version_id, '') AS file_version_id,
                        COALESCE(fv.source_path, d.file_name, d.abs_path, 'unknown') AS source_path,
                        COALESCE(b.page_index, 0) AS page_index,
                        SUBSTR(TRIM(COALESCE(b.text, '')), 1, 1600) AS evidence_text
                    FROM doc_blocks b
                    LEFT JOIN documents d ON d.doc_id = b.doc_id
                    LEFT JOIN file_versions fv
                      ON d.file_name = fv.source_path OR d.abs_path = fv.source_path
                    WHERE ({block_where})
                    ORDER BY COALESCE(b.page_index, 0)
                    LIMIT ?
                """
                block_params = [f"%{t}%" for t in terms] + [max(limit * 2, 10)]
                rows = self.db.execute(block_sql, tuple(block_params)).fetchall()
                for row in rows:
                    _append_row(dict(row), "doc_block")
                    if len(evidence) >= limit:
                        break
            except Exception as exc:
                logger.debug("RAG retrieve_evidence block query failed: %s", exc)

        return evidence[:limit]

    def retrieve_hybrid_context(
        self,
        query: str,
        limit: int = 5,
        query_type: Optional[str] = None,
    ) -> str:
        """
        NEW: Hybrid retrieval that routes queries to appropriate tools.
        
        Args:
            query: User's natural language question
            limit: Max results to return
            query_type: Optional override ("semantic", "structured_bim", "structured_schedule", "auto")
                       If "auto" or None, uses router to classify
        
        Returns:
            Formatted context string combining structured and semantic results
        """
        query = (query or "").strip()
        if not query:
            return ""
        
        # Route the query
        if query_type == "auto" or query_type is None:
            route_result = self.router.route_query(query)
            classified_type = route_result["query_type"]
        else:
            # Manual override
            classified_type = QueryType(query_type)
            route_result = {"query_type": classified_type, "original_query": query}
        
        # Execute based on classification
        if classified_type == QueryType.STRUCTURED_BIM:
            return self._retrieve_bim_context(route_result, limit)
        
        elif classified_type == QueryType.STRUCTURED_SCHEDULE:
            return self._retrieve_schedule_context(route_result, limit)
        
        else:  # SEMANTIC
            return self.retrieve_context(query, limit)

    # ------------------------------------------------------------------
    # Structured Retrieval (NEW)
    # ------------------------------------------------------------------
    def _retrieve_bim_context(self, route_result: Dict, limit: int) -> str:
        """Retrieve BIM elements from IFC staging tables using SQL query."""
        filters = route_result.get("filters", {})
        is_count = route_result.get("is_count", False)
        original_query = route_result.get("original_query", "")
        
        try:
            # Build SQL query for IFC staging tables
            # Query both spatial structure (Site/Building/Storey/Space) and elements (Walls/Doors/etc)
            base_sql = """
                SELECT 
                    s.element_id,
                    s.entity_type,
                    s.name,
                    s.elevation,
                    s.parent_id,
                    p.name as project_name
                FROM ifc_spatial_structure s
                LEFT JOIN ifc_projects p ON s.ifc_project_id = p.global_id
                WHERE 1=1
            """
            
            params = []
            
            # Apply filters from query router
            if filters.get("ifc_type"):
                base_sql += " AND s.entity_type = ?"
                params.append(filters["ifc_type"])
            
            if filters.get("level"):
                base_sql += " AND s.name LIKE ?"
                params.append(f"%{filters['level']}%")
            
            if filters.get("name_contains"):
                base_sql += " AND s.name LIKE ?"
                params.append(f"%{filters['name_contains']}%")
            
            # Count query
            if is_count:
                count_sql = f"SELECT COUNT(*) as cnt FROM ({base_sql})"
                result = self.db.execute(count_sql, tuple(params)).fetchone()
                count = result["cnt"] if result else 0
                return f"--- BIM DATA ---\nFound {count} IFC elements matching criteria.\n"
            
            # Regular query
            base_sql += " ORDER BY s.entity_type, s.name LIMIT ?"
            params.append(limit)
            
            rows = self.db.execute(base_sql, tuple(params)).fetchall()
            
            # Also query ifc_elements if no spatial results
            if not rows:
                elem_sql = """
                    SELECT 
                        e.element_id,
                        e.entity_type,
                        e.name,
                        e.tag,
                        s.name as container_name
                    FROM ifc_elements e
                    LEFT JOIN ifc_spatial_structure s ON e.spatial_container_id = s.element_id
                    WHERE 1=1
                """
                elem_params = []
                
                if filters.get("ifc_type"):
                    elem_sql += " AND e.entity_type = ?"
                    elem_params.append(filters["ifc_type"])
                
                if filters.get("name_contains"):
                    elem_sql += " AND e.name LIKE ?"
                    elem_params.append(f"%{filters['name_contains']}%")
                
                elem_sql += " ORDER BY e.entity_type, e.name LIMIT ?"
                elem_params.append(limit)
                
                rows = self.db.execute(elem_sql, tuple(elem_params)).fetchall()
            
            if not rows:
                logger.debug(f"No IFC elements found for filters: {filters}")
                # Fallback to semantic search
                return self.retrieve_context(original_query, limit=limit)
            
            # Format results for LLM
            lines = ["", "--- BIM DATA (IFC) ---"]
            lines.append(f"Found {len(rows)} elements:\n")
            
            for row in rows:
                entity_type = row.get("entity_type", "Unknown")
                name = row.get("name", "Unnamed")
                element_id = row.get("element_id", "N/A")
                
                lines.append(f"**{entity_type}**: {name}")
                lines.append(f"  - ID: {element_id}")
                
                # Additional fields depending on which table
                if row.get("elevation") is not None:
                    lines.append(f"  - Elevation: {row['elevation']}")
                if row.get("tag"):
                    lines.append(f"  - Tag: {row['tag']}")
                if row.get("container_name"):
                    lines.append(f"  - Location: {row['container_name']}")
                if row.get("parent_id"):
                    lines.append(f"  - Parent: {row['parent_id']}")
                
                lines.append("")
            
            formatted = "\n".join(lines)
            
            # Add semantic context for richer answers
            try:
                semantic_context = self.retrieve_context(original_query, limit=3)
                if semantic_context and len(semantic_context.strip()) > 50:
                    return f"{formatted}\n\n--- RELATED DOCUMENTATION ---\n{semantic_context}"
            except Exception:
                pass
            
            return formatted
        
        except Exception as e:
            logger.exception(f"BIM query failed: {e}")
            # Fallback to semantic search
            return self.retrieve_context(original_query, limit)

    def _retrieve_schedule_context(self, route_result: Dict, limit: int) -> str:
        """Retrieve schedule activities from P6 staging tables using SQL query."""
        filters = route_result.get("filters", {})
        is_count = route_result.get("is_count", False)
        original_query = route_result.get("original_query", "")
        
        try:
            # Build SQL query for P6 staging tables
            base_sql = """
                SELECT 
                    a.activity_id,
                    a.code,
                    a.name,
                    a.start_date,
                    a.finish_date,
                    a.status_code,
                    a.total_float,
                    w.name as wbs_name,
                    p.name as project_name
                FROM p6_activities a
                LEFT JOIN p6_wbs w ON a.wbs_id = w.wbs_id
                LEFT JOIN p6_projects p ON a.p6_project_id = p.p6_project_id
                WHERE 1=1
            """
            
            params = []
            
            # Apply filters from query router
            if filters.get("status"):
                base_sql += " AND a.status_code = ?"
                params.append(filters["status"])
            
            if filters.get("start_after"):
                base_sql += " AND a.start_date >= ?"
                params.append(filters["start_after"])
            
            if filters.get("finish_before"):
                base_sql += " AND a.finish_date <= ?"
                params.append(filters["finish_before"])
            
            if filters.get("critical_path_only"):
                # Critical path heuristic: total_float <= 0
                base_sql += " AND a.total_float <= 0"
            
            if filters.get("activity_contains"):
                base_sql += " AND (a.name LIKE ? OR a.code LIKE ?)"
                search_term = f"%{filters['activity_contains']}%"
                params.extend([search_term, search_term])
            
            # Count query
            if is_count:
                count_sql = f"SELECT COUNT(*) as cnt FROM ({base_sql})"
                result = self.db.execute(count_sql, tuple(params)).fetchone()
                count = result["cnt"] if result else 0
                return f"--- SCHEDULE DATA ---\nFound {count} activities matching criteria.\n"
            
            # Regular query
            base_sql += " ORDER BY a.start_date, a.code LIMIT ?"
            params.append(limit)
            
            rows = self.db.execute(base_sql, tuple(params)).fetchall()
            
            if not rows:
                logger.debug(f"No P6 activities found for filters: {filters}")
                # Fallback to semantic search
                return self.retrieve_context(original_query, limit=limit)
            
            # Format results for LLM
            lines = ["", "--- SCHEDULE DATA (P6) ---"]
            lines.append(f"Found {len(rows)} activities:\n")
            
            for row in rows:
                code = row.get("code", "N/A")
                name = row.get("name", "Unnamed")
                start = row.get("start_date", "N/A")
                finish = row.get("finish_date", "N/A")
                status = row.get("status_code", "N/A")
                float_days = row.get("total_float")
                wbs = row.get("wbs_name", "N/A")
                
                float_str = f"{float_days:.1f} days" if float_days is not None else "N/A"
                critical = " [CRITICAL PATH]" if float_days is not None and float_days <= 0 else ""
                
                lines.append(f"**{code}**: {name}")
                lines.append(f"  - WBS: {wbs}")
                lines.append(f"  - Start: {start} | Finish: {finish}")
                lines.append(f"  - Status: {status} | Float: {float_str}{critical}")
                lines.append("")
            
            formatted = "\n".join(lines)
            
            # Add semantic context for richer answers
            try:
                semantic_context = self.retrieve_context(original_query, limit=3)
                if semantic_context and len(semantic_context.strip()) > 50:
                    return f"{formatted}\n\n--- RELATED DOCUMENTATION ---\n{semantic_context}"
            except Exception:
                pass
            
            return formatted
        
        except Exception as e:
            logger.exception(f"Schedule query failed: {e}")
            # Fallback to semantic search
            return self.retrieve_context(original_query, limit)

    # ------------------------------------------------------------------
    # Block-level retrieval
    # ------------------------------------------------------------------
    def _retrieve_block_level_context(self, query: str, limit: int) -> str:
        """
        Pull top-N blocks and format into a human-readable, LLM-friendly context.
        """
        # Request more blocks than "limit" so the model has rich context
        block_limit = max(limit * 5, limit)

        # DatabaseManager.search_doc_blocks returns:
        #   doc_id, block_id, page_index, heading_title, heading_number, level, text, rank
        blocks: List[Dict] = self.db.search_doc_blocks(query, limit=block_limit)
        if not blocks:
            return ""

        lines: List[str] = []
        lines.append("--- RELEVANT PROJECT SECTIONS ---")

        # Group by doc_id in the order returned
        by_doc: Dict[str, List[Dict]] = {}
        for b in blocks:
            by_doc.setdefault(b["doc_id"], []).append(b)

        for doc_id, doc_blocks in by_doc.items():
            doc = self.db.get_document(doc_id) or {}
            file_name = doc.get("file_name") or doc_id
            doc_title = doc.get("doc_title") or ""

            lines.append("")
            lines.append(f"=== File: {file_name} ===")
            if doc_title:
                lines.append(f"Title: {doc_title}")

            # Keep only a few blocks per document to stay compact
            per_doc_limit = max(3, limit)
            for b in doc_blocks[:per_doc_limit]:
                heading_number = (b.get("heading_number") or "").strip()
                heading_title = (b.get("heading_title") or "").strip()
                page_index = int(b.get("page_index") or 0)

                if heading_number and heading_title:
                    section_label = f"{heading_number} {heading_title}"
                elif heading_title:
                    section_label = heading_title
                else:
                    section_label = f"Page {page_index + 1}"

                lines.append("")
                lines.append(f"[Section: {section_label} | Page {page_index + 1}]")

                text = b.get("text") or ""
                # Truncate long sections to keep prompt tight
                max_chars = 1500
                if len(text) > max_chars:
                    text = text[:max_chars] + " ..."
                lines.append(text)

            # [NEW] Append Vision Data for this Document
            logger.debug(f"Checking vision for doc_id={doc_id}")
            pages = self.db.list_pages(doc_id)
            logger.debug(f"Found {len(pages)} pages")
            vision_segments = []
            for p in pages:
                 v = (p.get("vision_detailed") or "").strip()
                 if v and len(v) > 10:
                     vision_segments.append(f"[Page {p['page_index']+1} Vision]: {v}")
            logger.debug(f"Found {len(vision_segments)} vision segments")
            
            if vision_segments:
                lines.append("")
                lines.append(f"--- Vision Analysis (File: {file_name}) ---")
                lines.append("\n".join(vision_segments))
                # Limit vision context to avoid explosion? 
                # Let's keep it all for now, relying on LLM to sort it out.

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Document-level fallback (your original behavior)
    # ------------------------------------------------------------------
    def _retrieve_document_level_context(self, query: str, limit: int) -> str:
        """
        Original document-level retrieval using documents_fts.

        Kept as a fallback in case block index is empty or not available.
        """
        results = self.db.search_documents(query, limit=limit)
        if not results:
            return ""

        context_parts: List[str] = []
        context_parts.append("--- RELEVANT PROJECT DOCUMENTS ---")
        
        for r in results:
            doc_id = r["doc_id"]
            filename = r["file_name"]

            payload = self.db.get_document_payload(doc_id)
            full_text = payload.get("text", "") or ""
            
            # Simple heuristic: if text is < 2000 chars, include all. 
            # If larger, truncate to keep prompt size under control.
            max_chars = 3000
            if len(full_text) > max_chars:
                display_text = full_text[:max_chars] + "..."
            else:
                display_text = full_text
            
            context_parts.append(f"File: {filename}")
            context_parts.append(f"Content:\n{display_text}\n")
            
            
            # [NEW] Append Vision Data
            logger.debug(f"Checking vision for {doc_id}")
            pages = self.db.list_pages(doc_id)
            logger.debug(f"Found {len(pages)} pages")
            vision_segments = []
            for p in pages:
                 v = (p.get("vision_detailed") or "").strip()
                 if v and len(v) > 10:
                     vision_segments.append(f"[Page {p['page_index']+1} Vision]: {v}")
            
            if vision_segments:
                context_parts.append(f"--- Vision Analysis (File: {filename}) ---")
                context_parts.append("\n".join(vision_segments))
                context_parts.append("")

        return "\n".join(context_parts)
