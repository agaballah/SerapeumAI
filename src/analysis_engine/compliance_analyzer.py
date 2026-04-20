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
compliance_analyzer.py — Standards/Spec compliance engine
---------------------------------------------------------

Consumes:
    • Document analysis (entities + relationships)
    • Optional global standards DB
    • Optional LLM for rule interpretation

Produces:
    {
        "requirements": [...],
        "violations": [...],
        "warnings": [...],
        "notes": [...]}

    }

Stored in DB:
    db.save_compliance(doc_id, result)
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from src.infra.adapters.llm_service import LLMService
from src.infra.persistence.database_manager import DatabaseManager


class ComplianceAnalyzer:
    def __init__(self, *, db: DatabaseManager, llm: Optional[LLMService]):
        self.db = db
        self.llm = llm

    # ------------------------------------------------------------------
    def run_project(self, project_id: str, on_progress=None) -> Dict[str, Any]:
        docs = self.db.list_documents(project_id=project_id, limit=100000, offset=0) or []
        out = {}
        
        total = len(docs)
        if on_progress:
            on_progress("compliance.start", f"Starting compliance sweep for {total} documents...")

        for idx, d in enumerate(docs, 1):
            did = d["doc_id"]
            fname = d.get("file_name", did)
            
            if on_progress:
                on_progress("compliance.doc", f"[{idx}/{total}] {fname}")
            
            result = self._analyze_doc(did)
            import time
            self.db.save_compliance(did, result, int(time.time()))
            out[did] = result
        
        if on_progress:
            on_progress("compliance.done", f"Completed {total} documents")

        return out

    # ------------------------------------------------------------------
    def _analyze_doc(self, doc_id: str) -> Dict[str, Any]:
        analysis = self.db.get_analysis(doc_id) or {}
        entities = analysis.get("entities") or []
        rels = analysis.get("relationships") or []
        text = (self.db.get_document_payload(doc_id) or {}).get("text", "")

        # If LLM available → run full structured compliance
        if self.llm:
            return self._llm_compliance(text, entities, rels)

        # Else fallback
        return self._fallback_compliance(text, entities)

    # ------------------------------------------------------------------
    def _llm_compliance(
        self,
        text: str,
        entities: List[Dict[str, Any]],
        rels: List[Dict[str, Any]],
    ) -> Dict[str, Any]:

        # 1. Fetch relevant standards from local DB
        from src.compliance.standards_db import StandardsDatabase
        sdb = StandardsDatabase()
        
        # Heuristic: Search for keywords based on entities
        keywords = set()
        for e in entities:
            if e.get("type") in ["System", "Space", "Equipment"]:
                keywords.add(e.get("value"))
        
        # Also add generic safety terms
        keywords.update(["fire", "egress", "exit", "width", "alarm", "sprinkler"])
        
        relevant_clauses = []
        for kw in list(keywords)[:5]: # Limit queries
            hits = sdb.search_clauses(kw, limit=3)
            relevant_clauses.extend(hits)
            
        # Deduplicate by id
        seen = set()
        unique_clauses = []
        for c in relevant_clauses:
            if c["id"] not in seen:
                seen.add(c["id"])
                unique_clauses.append(c)
        
        # Format for LLM
        stds_text = "\n".join([f"- {c['std_code']} {c['clause_id']} ({c['title']}): {c['text']}" for c in unique_clauses[:15]])

        if not stds_text:
            stds_text = "(No specific standards found in local DB. Rely on general AECO knowledge.)"

        system = (
            "You are a senior AECO codes & standards compliance reviewer.\n"
            "Compare the document content against the provided standards.\n"
            "Return ONLY JSON with keys:\n"
            "{"
            '"requirements":[{"code":string,"clause":string,"summary":string}],'
            '"violations":[{"clause":string,"message":string,"severity":"high|medium|low"}],'
            '"warnings":[string],'
            '"notes":[string]'
            "}"
        )

        user = (
            f"STANDARDS:\n{stds_text}\n\n"
            "DOCUMENT_CONTENT:\n" + text[:8000] +
            "\n\nENTITIES:\n" + json.dumps(entities, ensure_ascii=False)[:3000] +
            "\n\nRELATIONSHIPS:\n" + json.dumps(rels, ensure_ascii=False)[:3000]
        )

        obj = self.llm.chat_json(
            system=system,
            user=user,
            schema_hint="AECOCompliance",
            max_tokens=1200,
        )

        if not isinstance(obj, dict):
            return self._fallback_compliance(text, entities)

        return {
            "requirements": obj.get("requirements") or [],
            "violations": obj.get("violations") or [],
            "warnings": obj.get("warnings") or [],
            "notes": obj.get("notes") or [],
        }

    # ------------------------------------------------------------------
    def _fallback_compliance(self, text: str, entities: List[Dict[str, Any]]):
        """
        Zero-LLM mode: simple heuristics.
        """
        reqs = []
        viol = []
        warns = []

        # Simple heuristic examples:
        if "fire" in text.lower():
            reqs.append({"code": "FireSafety", "clause": "-", "summary": "Mentions fire protection"})
        if any("Room" in (e.get("type") or "") for e in entities):
            reqs.append({"code": "SpaceValidation", "clause": "-", "summary": "Room definitions detected"})

        return {
            "requirements": reqs,
            "violations": viol,
            "warnings": warns,
            "notes": [],
        }
