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
agent_orchestrator.py — SerapeumAI Multi-Agent Coordinator

Agents:
    • TextAgent — pure text Q&A using extracted text
    • LayoutAgent — Qwen-VL reasoning using OCR/vision snippets
    • ComplianceAgent — queries compliance results
    • MetaAgent — merges answers and chooses final response
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from src.domain.intelligence.evidence_builder import EvidencePackBuilder
from src.application.services.artifact_service import ArtifactService
from src.application.services.coverage_gate import CoverageGate
from src.application.api.fact_api import FactQueryAPI

from src.infra.persistence.database_manager import DatabaseManager
from src.infra.adapters.llm_service import LLMService

import logging
logger = logging.getLogger(__name__)


from src.domain.facts.repository import FactRepository


class AgentOrchestrator:
    def __init__(
        self,
        *,
        db: DatabaseManager,
        llm: LLMService,
        rag: Optional[RAGService] = None,
        global_db: Optional[DatabaseManager] = None,
    ) -> None:
        self.db = db
        self.llm = llm
        self.rag = rag
        self.global_db = global_db
        self.evidence_builder = EvidencePackBuilder(db)
        self.fact_repo = FactRepository(db)

        # SSOT Enforcement Layer
        self.coverage_gate = CoverageGate(db)
        self.fact_api = FactQueryAPI(db)

        # Artifact Folder
        import os
        artifact_root = os.path.join(db.root_dir, ".serapeum", "artifacts")
        self.artifact_service = ArtifactService(output_dir=artifact_root)

        # Deep Thinking Agent (for complex multi-step queries)
        try:
            from src.analysis_engine.deep_thinking_agent import DeepThinkingAgent
            self.deep_agent = DeepThinkingAgent(db=db, llm=llm)
            logger.info("[AgentOrchestrator] DeepThinkingAgent initialized.")
        except Exception as e:
            logger.warning(f"[AgentOrchestrator] DeepThinkingAgent unavailable: {e}")
            self.deep_agent = None

    # ------------------------------------------------------------------
    # WORLD-CLASS AGENTIC REASONING (Extended-Thinking Style)
    # ------------------------------------------------------------------

    def answer_question(
        self,
        *,
        query: str,
        context: Optional[str] = None,
        stream: bool = False,
        cancellation_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        SSOT-compliant agentic pipeline (§7 Strict Chat Protocol):

        Step 0: Resolve snapshot (snapshot-bound chat — Feature 3)
        Step 1: CoverageGate — refuse if certified facts missing (Feature 1)
        Step 2: Route to DeepThinkingAgent (complex) or fast path (simple)
        Step 3: FactQueryAPI — retrieve ONLY certified facts (Feature 2)
        Step 4: Conflict disclosure
        Step 5: LLM narrates from certified context only
        """
        project_id = getattr(self.db, 'project_id', None) or "unknown"

        # ── Step 0: Resolve snapshot ─────────────────────────────────────
        snapshot_id: Optional[str] = None
        try:
            snapshot_id = self.db.get_or_create_snapshot(project_id)
            logger.info(f"[AgentOrchestrator] snapshot={snapshot_id} project={project_id}")
        except Exception as e:
            logger.warning(f"[AgentOrchestrator] Snapshot resolution failed: {e}")

        # ── Step 1: Coverage Gate ─────────────────────────────────────────
        try:
            coverage = self.coverage_gate.check(
                query=query,
                project_id=project_id,
                snapshot_id=snapshot_id,
            )
            if not coverage["is_complete"]:
                logger.info(
                    f"[AgentOrchestrator] Coverage gate REFUSED query. "
                    f"Missing: {coverage['missing_fact_types']}"
                )
                return {
                    "answer": coverage["refusal_message"],
                    "thinking": f"Coverage gate refused. Missing: {coverage['missing_fact_types']}",
                    "citations": [],
                    "compliance_status": "COVERAGE_GAP",
                    "suggested_actions": [
                        step["action"] for step in coverage.get("job_plan", [])
                    ],
                    "mode": "refused",
                }
        except Exception as e:
            logger.warning(f"[AgentOrchestrator] Coverage gate error (safe pass): {e}")

        # ── Step 2: Route complex queries to DeepThinkingAgent ────────────
        if self.deep_agent and self._is_complex_query(query):
            logger.info(f"[AgentOrchestrator] Routing to DeepThinkingAgent: {query[:60]}")
            try:
                return self.deep_agent.answer_question(query=query, project_id=project_id)
            except Exception as e:
                logger.error(f"[AgentOrchestrator] DeepThinkingAgent failed, falling back: {e}")

        # ── Step 3: Retrieve certified facts via FactQueryAPI (whitelist) ─
        fact_context = ""
        conflict_notice = ""
        citations = []
        try:
            fact_result = self.fact_api.get_certified_facts(
                query_intent=query,
                project_id=project_id,
                snapshot_id=snapshot_id,
            )
            if fact_result["has_certified_data"]:
                fact_context = fact_result["formatted_context"]
                citations = [
                    {"source": f.get("method_id", "?"), "fact_id": f.get("fact_id")}
                    for f in fact_result["facts"]
                ]
            # ── Step 4: Conflict disclosure ───────────────────────────────
            if fact_result["conflicts"]:
                conflict_notice = (
                    f"\n\n⚠️ WARNING: {len(fact_result['conflicts'])} conflicting certified "
                    f"fact(s) detected. You MUST disclose both values in your answer."
                )
        except Exception as e:
            logger.warning(f"[AgentOrchestrator] FactQueryAPI failed (safe pass): {e}")

        # Legacy RAG context (discovery only — not ground truth per SSOT §5)
        rag_context = ""
        if self.rag and not fact_context:
            try:
                rag_context = self.rag.retrieve_context(query, limit=10)
            except Exception:
                pass

        # ── Step 5: LLM narrates from certified-facts context only ────────
        contract_prompt = (
            "You are a World-Class Agentic Brain for AECO.\n"
            f"as_of snapshot: {snapshot_id or 'latest'}\n"
            "STRICT BEHAVIOR CONTRACT (SSOT §7):\n"
            "1. Answer ONLY from the 'CERTIFIED FACTS' block below. Do NOT invent data.\n"
            "2. If no certified facts are provided, say exactly: "
               "'No certified facts available for this query in the current snapshot.'\n"
            "3. Cite each fact used: [Fact <fact_id>].\n"
            "4. If CONFLICTS are flagged, DISCLOSE both values — never choose silently.\n"
            "5. Respect the user's format exactly. No extra boilerplate.\n"
            "\nOUTPUT FORMAT (JSON):\n"
            "{\n"
            "  'thinking': 'step-by-step reasoning',\n"
            "  'answer': 'final answer (markdown)',\n"
            "  'citations': [{'source': '...', 'quote': '...'}],\n"
            "  'compliance_status': '',\n"
            "  'suggested_actions': []\n"
            "}\n"
            + conflict_notice
        )

        certified_block = (
            fact_context or
            (f"[RAG Discovery Context — not certified]\n{rag_context}" if rag_context else
             "[No certified facts found in this snapshot]")
        )
        user_prompt = (
            f"USER INSTRUCTION: {query}\n\n"
            f"CERTIFIED FACTS:\n{certified_block}"
        )
        # ── Step 5 (continued): Execute LLM with certified-facts context ──

        # 3. ROBUST EXECUTION LOOP
        # Attempt 1: Strict JSON
        try:
            result = self.llm.chat_json(
                system=contract_prompt,
                user=user_prompt,
                task_type="universal",
                temperature=0.3
            )
            if result and result.get("answer"):
                return result
        except Exception:
            pass
            
        # Attempt 2: Strict JSON Retry
        try:
            result = self.llm.chat_json(
                system=contract_prompt + "\n\nRetry: Ensure valid JSON.",
                user=user_prompt,
                task_type="universal",
                temperature=0.5
            )
            if result and result.get("answer"):
                return result
        except Exception:
            pass

        # Attempt 3: TEXT FALLBACK (Fail-Safe)
        # If JSON fails, we ask for the direct answer to ensure the user gets their deliverable.
        fallback_system = (
            "You are a helpful AECO Assistant. The JSON reasoning loop failed.\n"
            "You MUST provide the requested deliverable directly in the requested format.\n"
            "Do NOT output JSON. Output the final answer content only.\n"
            "Strictly follow the user's formatting instruction (e.g. bullets, clean text)."
        )
        try:
            # If caller requested streaming, return a generator under the 'stream' key
            if stream:
                gen = self.llm.chat(
                    messages=[
                        {"role": "system", "content": fallback_system},
                        {"role": "user", "content": user_prompt}
                    ],
                    task_type="universal",
                    temperature=0.3,
                    stream=True,
                    cancellation_token=cancellation_token,
                )
                return {"stream": gen, "thinking": "Streaming fallback"}

            # Non-streaming blocking fallback
            text_response = (self.llm.chat(
                messages=[
                    {"role": "system", "content": fallback_system},
                    {"role": "user", "content": user_prompt}
                ],
                task_type="universal",
                temperature=0.3
            ) or {}).get("choices", [{}])[0].get("message", {}).get("content", "")

            if text_response:
                try:
                    import json
                    # Attempt to fix common LLM formatting issues (e.g. extra text before/after JSON)
                    json_str = text_response[text_response.find("{"):text_response.rfind("}")+1]
                    parsed = json.loads(json_str)
                    if "answer" in parsed:
                        return parsed
                except:
                    pass
                
                # If JSON parsing fails or "answer" not in parsed, but we have text_response
                # We should still try to return it as an answer
                return {
                    "answer": text_response,
                    "thinking": "Parsed from LLM output (JSON or Text)",
                    "citations": [],
                    "compliance_status": "",
                    "suggested_actions": []
                }
        except Exception as e:
            return {
                "answer": f"Partial Failure: Unable to generate full response due to error: {e}. Inputs available: {len(db_context)} chars.",
                "thinking": "Critical Engine Failure",
                "citations": [],
                "compliance_status": "System Error",
                "suggested_actions": []
            }
            
        return {
             "answer": "Status: Partial Failure (Missing inputs or model refusal). I could not generate the specific output format requested, but no exception was raised.",
             "thinking": "Unknown failure state",
             "citations": [],
             "compliance_status": "Unknown",
             "suggested_actions": []
        }

    def _is_complex_query(self, query: str) -> bool:
        """Classify if query requires deep multi-step reasoning."""
        if self.deep_agent:
            return self.deep_agent._classify_intent(query) == "deep"
        return False

    # ------------------------------------------------------------------
    # MAP-REDUCE DETERMINISTIC ENGINE (Phase 2)
    # ------------------------------------------------------------------
    
    def answer_question_map_reduce(
        self,
        *,
        query: str,
        doc_ids: List[str],
        task_mode: str = "Mode B"
    ) -> Dict[str, Any]:
        """
        Deterministic Map-Reduce Process:
        1. Build Evidence Pack (Ladder: Headings -> Pages -> Sections)
        2. Map: Extract facts from each document's evidence.
        3. Reduce: Synthesize facts into a final answer.
        """
        # 1. Build Evidence Pack
        pack = self.evidence_builder.build_pack(query, doc_ids, task_mode)
        
        # 2. Map Phase
        map_results = []
        for doc_ev in pack.get("documents", []):
            if doc_ev.get("status") != "Found Evidence":
                continue
                
            # Extract facts from excerpts
            facts = self._map_document_facts(query, doc_ev)
            if facts:
                map_results.append({
                    "doc_id": doc_ev["doc_id"],
                    "file_name": doc_ev["file_name"],
                    "facts": facts
                })
        
        # Escape Hatch: Not Found
        if not map_results:
            return {
                "answer": "I could not find sufficient evidence in the provided documents to answer your question.",
                "evidence_pack": pack,
                "map_results": []
            }

        # 3. Reduce Phase
        final_answer = self._reduce_facts(query, map_results)
        
        # 4. Generate Artifact (Optional)
        artifact_path = ""
        try:
            artifact_content = {
                "summary": final_answer,
                "evidence": [
                    {"source": m["file_name"], "text": "; ".join(m["facts"])}
                    for m in map_results
                ],
                "thinking": "Generated via Map-Reduce Deterministic Engine."
            }
            # Create a safe filename from query
            safe_name = "".join(c if c.isalnum() else "_" for c in query[:30])
            artifact_path = self.artifact_service.generate_docx_report(
                filename=f"Report_{safe_name}.docx",
                title=f"Analysis: {query}",
                content=artifact_content
            )
        except Exception as e:
            logger.error(f"Artifact generation failed: {e}")

        return {
            "answer": final_answer,
            "evidence_pack": pack,
            "map_results": map_results,
            "artifact_path": artifact_path
        }

    def _map_document_facts(self, query: str, doc_ev: Dict[str, Any]) -> List[str]:
        """Extract key facts from a single document's excerpts."""
        excerpts_text = "\n\n".join([f"[{e['source_field']}] {e['text']}" for e in doc_ev.get("excerpts", [])])
        
        sys = (
            "You are a Forensic Engineering Auditor. Extract specific technical facts relevant to the query. "
            "Return a JSON list of strings: {'facts': ['fact 1', 'fact 2']}."
        )
        user = f"QUERY: {query}\n\nDOCUMENT EVIDENCE ({doc_ev['file_name']}):\n{excerpts_text}"
        
        try:
            out = self.llm.chat_json(system=sys, user=user)
            return out.get("facts", [])
        except Exception:
            return []

    def _reduce_facts(self, query: str, map_results: List[Dict[str, Any]]) -> str:
        """Synthesize facts from multiple documents into a final answer."""
        context = ""
        for item in map_results:
            context += f"\n--- Source: {item['file_name']} ---\n"
            for f in item['facts']:
                context += f"- {f}\n"
        
        sys = (
            "You are a Solution Architect. Synthesize the provided facts into a coherent, engineering-grade answer. "
            "Cite sources in brackets [Source Name]. If facts conflict, note the conflict."
        )
        user = f"QUERY: {query}\n\nEXTRACTED FACTS:\n{context}"
        
        try:
            resp = self.llm.chat(
                messages=[{"role": "system", "content": sys}, {"role": "user", "content": user}],
                temperature=0.3
            )
            return (resp.get("choices") or [{}])[0].get("message", {}).get("content", "Synthesis failed.")
        except Exception as e:
            return f"Error during synthesis: {str(e)}"

    # ------------------------------------------------------------------
    # TEXT AGENT
    # ------------------------------------------------------------------

    def _text_agent(self, doc_id: str, query: str) -> Dict[str, Any]:
        payload = self.db.get_document_payload(doc_id)
        text = payload.get("text") or ""

        sys = (
            "You answer based ONLY on document text. "
            "Be factual. Return JSON: {\"answer\": \"...\", \"confidence\": 0..1}"
        )
        user = f"QUERY:\n{query}\n\nTEXT:\n{text[:6000]}"

        out = self.llm.chat_json(system=sys, user=user)
        return {"source": "text", "data": out}

    # ------------------------------------------------------------------
    # LAYOUT / VISION AGENT
    # ------------------------------------------------------------------

    def _layout_agent(self, doc_id: str, query: str) -> Dict[str, Any]:
        payload = self.db.get_document_payload(doc_id)
        pages = payload.get("pages") or []

        snippets = []
        for p in pages:
            t = (p.get("ocr_text") or "").strip()
            if t:
                snippets.append(t[:1000])

        sys = (
            "You are an AECO spatial reasoning agent. "
            "Use OCR and layout cues. "
            "Return JSON: {\"analysis\": \"...\", \"confidence\": 0..1}"
        )
        user = f"QUERY:\n{query}\n\nOCR SNIPPETS:\n" + "\n\n".join(snippets[:8])

        out = self.llm.chat_json(system=sys, user=user)
        return {"source": "layout", "data": out}

    # ------------------------------------------------------------------
    # COMPLIANCE AGENT
    # ------------------------------------------------------------------

    def _compliance_agent(self, doc_id: str, query: str) -> Dict[str, Any]:
        comp = self.db.get_compliance(doc_id) or {}
        issues = comp.get("gaps") or []
        refs = comp.get("references") or []

        sys = (
            "You are a standards/compliance agent. "
            "Return JSON: {\"compliance\": \"...\", \"confidence\": 0..1}"
        )

        user = f"QUERY:\n{query}\n\nCOMPLIANCE DATA:\n" + json.dumps(
            {"refs": refs, "gaps": issues}, ensure_ascii=False
        )

        out = self.llm.chat_json(system=sys, user=user)
        return {"source": "compliance", "data": out}

    # ------------------------------------------------------------------
    # META AGENT — FINAL ANSWER
    # ------------------------------------------------------------------

    def _meta_agent(
        self,
        query: str,
        text_ans: Dict[str, Any],
        layout_ans: Dict[str, Any],
        comp_ans: Dict[str, Any],
    ) -> Dict[str, Any]:

        sys = (
            "You merge answers from three agents (text, layout, compliance). "
            "Choose the most reliable pieces. "
            "Return: {\"final_answer\": \"...\", \"source\": \"text|layout|compliance\", \"confidence\": 0..1}"
        )

        user = json.dumps(
            {
                "query": query,
                "text_agent": text_ans,
                "layout_agent": layout_ans,
                "compliance_agent": comp_ans,
            },
            ensure_ascii=False,
        )

        out = self.llm.chat_json(system=sys, user=user)
        return out or {"final_answer": "", "source": "none", "confidence": 0.0}
