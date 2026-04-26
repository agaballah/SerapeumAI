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
page_analysis.py — Optimized page-level analysis
------------------------------------------------
Analyzes documents page-by-page with simplified prompts.

Major optimizations:
- Sequential processing (llama.cpp is NOT thread-safe)
- Single-page context (no 3-page sliding window)
- Shorter prompts and smaller max_tokens for speed
- Robust JSON parsing via LLMService.chat_json
- Entity normalization (handles strings OR objects)
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List

from src.infra.adapters.llm_service import LLMService
from src.infra.persistence.database_manager import DatabaseManager
from src.domain.models.page_record import PageRecord
from src.domain.models.relationship_types import EntityType, RelationshipType
from src.infra.adapters.cancellation import CancellationError

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Prompt + normalization helpers
# ----------------------------------------------------------------------

ANALYSIS_SYSTEM_PROMPT = """
You are an AECO document analyst.

You must analyze the given page and output ONLY valid JSON in this exact shape:

{
  "summary": "One concise sentence describing the page content",
  "type": "contract|drawing|spec|data|form|schedule",
  "entities": ["entity1", "entity2"],
  "relationships": [{"source": "Entity A", "relation": "connected_to", "target": "Entity B"}]
}

Hard rules:
- Output MUST be a single valid JSON object. No text before or after it.
- Use EXACTLY these keys: summary, type, entities, relationships.
- "summary": Maximum 1-2 sentences. Keep it very concise.
- "type": MUST be one of the closed list: contract, drawing, spec, data, form, schedule.
- "entities": JSON Array of short strings (e.g. ["Saudi Electricity Co", "HVAC Unit"]). Maximum 10 entities.
- "relationships": Extract FUNCTIONAL connections.
  - Format: {"source": "Chiller", "relation": "feeds", "target": "AHU-01"}
  - High confidence only.
- Do NOT include comments or markdown.
""".strip()


def _normalize_type(raw_type: Any) -> str:
    """
    Map whatever the model returns into one of: contract, drawing, spec, data.
    """
    if raw_type is None:
        return "data"

    t = str(raw_type).strip().lower()

    # Already valid
    if t in {"contract", "drawing", "spec", "data", "form", "schedule"}:
        return t

    # Heuristics to map noisy labels
    if any(k in t for k in ["contract", "clause", "bid", "tender", "proposal", "instruction", "terms"]):
        return "contract"
    if any(k in t for k in ["drawing", "layout", "plan", "sketch"]):
        return "drawing"
    if any(k in t for k in ["spec", "standard", "tmss", "technical document", "procedure"]):
        return "spec"
    if any(k in t for k in ["form", "sheet", "application", "checklist", "invoice"]):
        return "form"
    if any(k in t for k in ["schedule", "gantt", "timeline", "program"]):
        return "schedule"

    # Default bucket
    return "data"


def _normalize_graph_text_value(raw: Any) -> str:
    """Normalize mixed graph persistence values into safe short strings."""
    if raw is None:
        return ""
    if isinstance(raw, str):
        return raw.strip()
    if isinstance(raw, dict):
        parts = []
        for key, value in raw.items():
            key_text = _normalize_graph_text_value(key)
            value_text = _normalize_graph_text_value(value)
            if key_text and value_text:
                parts.append(f"{key_text}: {value_text}")
            elif value_text:
                parts.append(value_text)
            elif key_text:
                parts.append(key_text)
        return " | ".join(p for p in parts if p).strip()
    if isinstance(raw, (list, tuple, set)):
        parts = [_normalize_graph_text_value(item) for item in raw]
        return " | ".join(p for p in parts if p).strip()
    return str(raw).strip()


def _normalize_entities(raw: Any, max_entities: int = 5) -> List[str]:
    """
    Normalize "entities" into a short list of clean strings.
    Accepts a mixture of strings, dicts, etc.
    """
    if raw is None:
        return []

    entities: List[str] = []

    # Expect list, but be defensive
    if not isinstance(raw, list):
        raw = [raw]

    for item in raw:
        text = ""

        if isinstance(item, str):
            text = item
        elif isinstance(item, dict):
            # Try common keys in your logs
            text = (
                item.get("name")
                or item.get("value")
                or item.get("entity")
                or item.get("label")
                or item.get("text")
                or ""
            )
        else:
            text = str(item)

        text = str(text).strip()
        if not text:
            continue

        # Avoid absurdly long "entities"
        if len(text) > 100:
            text = text[:100].rstrip()

        entities.append(text)

        if len(entities) >= max_entities:
            break

    return entities


def _rank_entities_by_importance(
    entities: List[str],
    page_text: str,
    max_entities: int = 5
) -> List[str]:
    """
    Rank entities by importance using frequency-based scoring (simple TF approach).
    
    Args:
        entities: List of entity strings to rank
        page_text: Full page text for frequency analysis
        max_entities: Maximum number of entities to return
        
    Returns:
        Ranked list of entities (most important first)
    """
    if not entities or not page_text:
        return entities[:max_entities]
    
    from collections import Counter
    
    # Normalize text for counting
    text_lower = page_text.lower()
    words = text_lower.split()
    word_counts = Counter(words)
    
    # Score each entity
    scores = []
    for entity in entities:
        entity_lower = entity.lower()
        
        # Count exact matches (full phrase)
        exact_count = text_lower.count(entity_lower)
        
        # Count partial matches (entity words appear in text)
        entity_words = entity_lower.split()
        partial_count = sum(word_counts.get(word, 0) for word in entity_words)
        
        # Prefer longer phrase exact matches by scaling exact match weight
        entity_words = entity_lower.split()
        exact_weight = 10 * max(1, len(entity_words))
        total_score = (exact_count * exact_weight) + partial_count
        
        scores.append((entity, total_score))
    
    # Sort by score descending
    scores.sort(key=lambda x: x[1], reverse=True)
    
    # Return top N entities
    return [entity for entity, score in scores[:max_entities]]


# ----------------------------------------------------------------------
# Main analyzer
# ----------------------------------------------------------------------


class PageAnalyzer:
    def __init__(self, db: DatabaseManager, llm: LLMService):
        self.db = db
        self.llm = llm
        from src.analysis_engine.adaptive_analysis import AdaptiveAnalysisEngine
        self.adaptive_engine = AdaptiveAnalysisEngine(db, llm)

    def analyze_document_pages(self, doc_id: str, fast_mode: bool = False, cancellation_token=None, interactive_event=None) -> None:
        """
        Public wrapper for document analysis.
        Analyzes all pages in a document sequentially.
        """
        return self._analyze_document(doc_id, fast_mode=fast_mode, cancellation_token=cancellation_token, interactive_event=interactive_event)

    def _check_cancel(self, cancellation_token) -> None:
        if cancellation_token is not None and hasattr(cancellation_token, "is_set") and cancellation_token.is_set():
            raise CancellationError("Page analysis cancelled because the app session is closing.")

    def _analyze_document(self, doc_id: str, fast_mode: bool = False, cancellation_token=None, interactive_event=None) -> None:
        """
        Analyze all pages in a document sequentially.
        Sequential processing is required because llama.cpp is NOT thread-safe.
        """
        print(f"[DEBUG] _analyze_document called for doc_id={doc_id}, fast_mode={fast_mode}")

        pages = self.db.list_pages(doc_id)
        if not pages:
            print(f"[DEBUG] No pages found for doc_id={doc_id}")
            return

        print(f"[DEBUG] Starting Sequential Page Analysis for {doc_id}...")

        # Process pages sequentially
        for page in pages:
            self._check_cancel(cancellation_token)
            if interactive_event is not None and hasattr(interactive_event, "is_set"):
                while interactive_event.is_set():
                    self._check_cancel(cancellation_token)
                    time.sleep(0.25)
            self._analyze_single_page(page, pages, cancellation_token=cancellation_token)
            self._check_cancel(cancellation_token)

        # Print health summary for this document
        from src.analysis_engine.health_tracker import get_health_tracker

        tracker = get_health_tracker()
        tracker.print_summary()

    def _analyze_single_page(self, page: Dict[str, Any], all_pages: List[Dict[str, Any]], cancellation_token=None):
        """
        Analyze a single page using the Adaptive Analysis Engine.
        """
        from src.analysis_engine.health_tracker import (
            get_health_tracker,
            HealthStatus,
        )

        tracker = get_health_tracker()
        page_idx = page["page_index"]
        doc_id = page["doc_id"]

        start_time = time.time()

        print("\n" + "=" * 80)
        print(f"[ADAPTIVE ANALYSIS] Page {page_idx}")
        print("=" * 80)

        try:
            self._check_cancel(cancellation_token)
            # NO SIGNAL GUARD
            current_text = page.get("py_text") or ""
            vision_summary = page.get("vision_general") or ""
            
            if len(current_text.strip()) < 50 and not vision_summary:
                print(f"[ANALYSIS] Page {page_idx} skipped (No Signal)")
                result = {
                    "summary": "Unreadable/No Content",
                    "type": "data",
                    "entities": [],
                    "relationships": [],
                    "analyst_profile": "generic",
                    "status": "skipped"
                }
            else:
                # Use the new Adaptive Engine
                result = self.adaptive_engine.analyze_page(page)
                self._check_cancel(cancellation_token)

            elapsed = time.time() - start_time

            print("\n" + "=" * 80)
            print(f"[ANALYSIS] Page {page_idx} ({elapsed:.2f}s | Profile: {result.get('analyst_profile')})")
            print("=" * 80)

            if result.get("status") == "error":
                tracker.record_failure(
                    doc_id, page_idx, HealthStatus.UNHEALTHY_LLM, "Engine failure", elapsed
                )
                return

            # Normalize response fields
            summary = result.get("summary", "").strip()
            page_type = _normalize_type(result.get("type", ""))
            
            # Use original ranking/normalization for consistency
            normalized_entities = _normalize_entities(result.get("entities", []), max_entities=10)
            context_for_ranking = self._build_context(page, all_pages)
            ranked_entities = _rank_entities_by_importance(
                entities=normalized_entities,
                page_text=context_for_ranking,
                max_entities=5
            )

            # Save to database
            try:
                self._save_result(
                    doc_id=doc_id,
                    page_index=page_idx,
                    summary=summary,
                    page_type=page_type,
                    entities=ranked_entities,
                    relationships=result.get("relationships", []),
                )
                tracker.record_success(doc_id, page_idx, summary, elapsed)
            except Exception as save_err:
                tracker.record_failure(
                    doc_id, page_idx, HealthStatus.UNHEALTHY_SAVE, str(save_err), elapsed
                )
                raise

            print("=" * 80 + "\n")

        except CancellationError as e:
            # Cooperative cancellation is expected during app/session close.
            # It must not be recorded as an unhealthy LLM failure or emitted as
            # an ERROR traceback in packaged shutdown logs.
            elapsed = time.time() - start_time
            print(f"\n[INFO] Page {page_idx} analysis cancelled: {e}\n")
            logger.info("Page %s analysis cancelled: %s", page_idx, e)
            return

        except Exception as e:
            elapsed = time.time() - start_time
            print(f"\n[ERROR] Page {page_idx} failed: {e}\n")
            logger.error(f"Page {page_idx} analysis failed: {e}", exc_info=True)
            tracker.record_failure(doc_id, page_idx, HealthStatus.UNHEALTHY_LLM, str(e), elapsed)

    def _build_context(self, page: Dict[str, Any], all_pages: List[Dict[str, Any]]) -> str:
        """
        Build unified context: previous summary + current page text + VISION DETAILS + SPATIAL LAYOUT.
        """
        parts: List[str] = []

        # Add previous page summary (1 line) if available
        page_idx = page["page_index"]
        if page_idx > 0:
            prev_page = all_pages[page_idx - 1]
            prev_summary = prev_page.get("page_summary_short", "")
            if prev_summary:
                parts.append(f"Previous Page Context: {prev_summary[:150]}")

        # 1. Native/OCR text
        text = page.get("py_text") or ""
        if not text.strip():
            text = page.get("ocr_text") or page.get("text_hint") or "[No direct text]"
        
        parts.append(f"#### TEXT CONTENT (OCR/PDF):\n{text[:2000]}")

        # 2. VISION CONTENT (High Value)
        v_det = page.get("vision_detailed") or ""
        if v_det:
            parts.append(f"#### VISION EXTRACTION (VLM):\n{v_det[:2000]}")

        # 3. SPATIAL LAYOUT
        layout_json = page.get("layout_json")
        if layout_json:
            try:
                layout_data = json.loads(layout_json)
                if layout_data:
                    layout_str = self._format_layout(layout_data)
                    parts.append(f"#### SPATIAL LAYOUT:\n{layout_str}")
            except Exception:
                pass

        return "\n\n".join(parts)

    def _format_layout(self, layout_data: List[Dict[str, Any]]) -> str:
        """
        Convert layout items into a spatial description.
        Group by Y-coordinate to simulate lines/rows.
        Markdown table-like structure.
        """
        if not layout_data:
            return ""

        # Sort by Y (inverted in PDF usually, but let's assume top-down flow or sort by Y descending)
        # pypdf Y is bottom-left (0,0). So higher Y is top.
        # We sort by Y DESC, then X ASC.
        sorted_items = sorted(layout_data, key=lambda i: (-i.get("y", 0), i.get("x", 0)))

        # Group items that are on roughly the same line (within 5 units)
        lines = []
        current_line = []
        current_y = None

        for item in sorted_items:
            y = item.get("y", 0)
            text = item.get("text", "").strip()
            if not text:
                continue
            
            if current_y is None:
                current_y = y
                current_line.append(item)
            elif abs(y - current_y) < 10: # Threshold for "same line"
                current_line.append(item)
            else:
                lines.append(current_line)
                current_line = [item]
                current_y = y
        
        if current_line:
            lines.append(current_line)

        # Render
        output = []
        for line_items in lines[:50]: # Limit to top 50 lines to avoid token explosion
            # Sort by X
            line_items.sort(key=lambda i: i.get("x", 0))
            
            line_str = ""
            for item in line_items:
                # Approximate positioning?
                # Just join with spaces for now, but maybe denote columns?
                val = item.get("text", "")
                if len(val) > 50: val = val[:50] + "..."
                
                # Check if it looks like a header (larger font?)
                size = item.get("size", 10)
                if size > 14:
                    val = f"**{val}**"
                
                line_str += f"[{val}]  "
            
            if line_str.strip():
                output.append(line_str.strip())

        return "\n".join(output)

    def _save_result(
        self,
        doc_id: str,
        page_index: int,
        summary: str,
        page_type: str,
        entities: List[str],
        relationships: List[Dict[str, str]] = None,
    ):
        """
        Save analysis result to database AND persist graph nodes/links.
        """
        relationships = relationships or []
        
        # 1. Update Page Metadata
        try:
            normalized_entities = [_normalize_graph_text_value(ent) for ent in (entities or [])]
            normalized_entities = [ent for ent in normalized_entities if ent]
            page_rec = PageRecord(
                doc_id=doc_id,
                page_index=page_index,
                page_summary_short=summary,
                page_summary_detailed=(summary + ("\n\nEntities: " + ", ".join(normalized_entities[:10]) if normalized_entities else "")),
                page_entities=json.dumps(normalized_entities),
                ai_summary_generated=True,
                ai_model_used="Mistral-7B-Optimized"
            )
            # Add page_type if it exists in schema (it was in my proposed but maybe not in current DB)
            # Actually, I added it to the model.
            setattr(page_rec, "page_type", page_type) # Future support/flexibility
            
            self.db.upsert_page(page_rec)
        except Exception as e:
            logger.error(f"Failed to save page result {page_index}: {e}", exc_info=True)
            raise

        # 2. Graph Persistence (Phase 2)
        try:
            doc = self.db.get_document(doc_id)
            if not doc: return
            project_id = doc.get("project_id", "default")
            
            # A. Save standalone entities
            for normalized_entity in normalized_entities:
                    self.db.upsert_entity_node(project_id, doc_id, EntityType.ENTITY, normalized_entity)
                
            # B. Save relationships
            for rel in relationships:
                src = _normalize_graph_text_value(rel.get("source"))
                dst = _normalize_graph_text_value(rel.get("target"))
                raw_rel = _normalize_graph_text_value(rel.get("relation", "related_to")) or "related_to"
                
                # Heuristic mapping for common relations
                rtype = RelationshipType.RELATED_TO
                raw_lower = str(raw_rel).lower()
                if "power" in raw_lower: rtype = RelationshipType.POWERS
                elif "feed" in raw_lower: rtype = RelationshipType.FEEDS
                elif "drain" in raw_lower: rtype = RelationshipType.DRAINS_INTO
                elif "control" in raw_lower: rtype = RelationshipType.CONTROLS
                elif "contain" in raw_lower or "part" in raw_lower: rtype = RelationshipType.CONTAINS
                elif "locate" in raw_lower: rtype = RelationshipType.LOCATED_IN
                elif "connect" in raw_lower: rtype = RelationshipType.CONNECTS_TO
                
                if src and dst:
                    # Upsert nodes first (use generic ENTITY for now, or detect from text)
                    src_id = self.db.upsert_entity_node(project_id, doc_id, EntityType.ENTITY, src)
                    dst_id = self.db.upsert_entity_node(project_id, doc_id, EntityType.ENTITY, dst)
                    
                    # Insert link
                    self.db.insert_entity_link(project_id, doc_id, src_id, dst_id, rtype)
                    
            print(f"Graph: Saved {len(entities)} nodes, {len(relationships)} edges.")
            
        except Exception as ge:
            logger.error(f"Graph persistence failed: {ge}")
