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
        from src.infra.telemetry.metrics_collector import MetricsCollector
        self.metrics = MetricsCollector(db)
        self.coverage_gate = CoverageGate(db)
        self.fact_api = FactQueryAPI(db)
        
        # Integration Phase logic: Confidence Learning
        from src.domain.intelligence.confidence_learner import ConfidenceLearner
        from src.domain.intelligence.prompt_optimizer import PromptOptimizer
        self.confidence_learner = ConfidenceLearner(db)
        self.optimizer = PromptOptimizer(db=db, confidence_learner=self.confidence_learner)

        # Artifact Folder
        import os
        artifact_root = os.path.join(db.root_dir, ".serapeum", "artifacts")
        self.artifact_service = ArtifactService(output_dir=artifact_root)

        # Semantic Tools (Fortification Phase)
        from src.tools.bim_query_tool import BIMQueryTool
        from src.tools.schedule_query_tool import ScheduleQueryTool
        from src.tools.calculator_tool import CalculatorTool
        from src.tools.n8n_tool import N8NTool
        from src.infra.config.configuration_manager import get_config
        
        config = get_config()
        n8n_url = (config.get_section("n8n") or {}).get("webhook_url", "")

        self.tools = {
            "query_bim": BIMQueryTool(db),
            "query_schedule": ScheduleQueryTool(db),
            "calculator": CalculatorTool(),
            "n8n_workflow": N8NTool(n8n_url)
        }

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
        # ── Step 5: LLM narrates from certified-facts context only ────────
        certified_block = (
            fact_context or
            (f"[RAG Discovery Context — not certified]\n{rag_context}" if rag_context else
             "[No certified facts found in this snapshot]")
        )

        # Fortified SSOT Contract via Optimizer
        # Resolve user role from DB if available, default to general
        user_role = getattr(self.db, 'user_role', 'general')
        
        op = self.optimizer.generate_stage2_prompt(
            unified_context=certified_block,
            field_name="main_contract",
            document_type="any",
            role=user_role,
            model_name=self.llm.model
        )
        
        contract_prompt = op.full_prompt
        if conflict_notice:
            contract_prompt += f"\n\n{conflict_notice}"

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

    def _get_tool_schemas(self) -> str:
        """Collate tool schemas for prompt injection."""
        schemas = {}
        for name, tool in self.tools.items():
            schemas[name] = {
                "description": tool.description,
                "parameters": tool.get_parameters_schema()
            }
        return json.dumps(schemas, indent=2)

    # ------------------------------------------------------------------
    # TEXT AGENT
    # ------------------------------------------------------------------

    def _text_agent(self, doc_id: str, query: str) -> Dict[str, Any]:
        start_ts = time.time()
        payload = self.db.get_document_payload(doc_id)
        text = payload.get("text") or ""

        # Using Optimizer for Fortified Prompting
        op = self.optimizer.generate_stage2_prompt(
            unified_context=text[:6000],
            field_name="text",
            document_type="doc",
            role="general",
            model_name=self.llm.model
        )
        
        # Inject tool schemas manually as PromptOptimizer currently formats instructions separately
        full_sys = f"{op.full_prompt}\nYou also have access to: {self._get_tool_schemas()}"

        out = self.llm.chat_json(system=full_sys, user=f"QUERY:\n{query}")
        self.metrics.record_latency("agent_text", time.time() - start_ts)
        return {"source": "text", "data": out}

    # ------------------------------------------------------------------
    # LAYOUT / VISION AGENT
    # ------------------------------------------------------------------

    def _layout_agent(self, doc_id: str, query: str) -> Dict[str, Any]:
        start_ts = time.time()
        payload = self.db.get_document_payload(doc_id)
        pages = payload.get("pages") or []

        snippets = []
        for p in pages:
            t = (p.get("ocr_text") or "").strip()
            if t:
                snippets.append(t[:1000])

        op = self.optimizer.generate_stage2_prompt(
            unified_context="\n\n".join(snippets[:8]),
            field_name="layout",
            document_type="doc",
            role="general",
            model_name=self.llm.model
        )
        
        full_sys = f"{op.full_prompt}\nYou also have access to: {self._get_tool_schemas()}"

        out = self.llm.chat_json(system=full_sys, user=f"QUERY:\n{query}")
        self.metrics.record_latency("agent_layout", time.time() - start_ts)
        return {"source": "layout", "data": out}

    # ------------------------------------------------------------------
    # COMPLIANCE AGENT
    # ------------------------------------------------------------------

    def _compliance_agent(self, doc_id: str, query: str) -> Dict[str, Any]:
        start_ts = time.time()
        comp = self.db.get_compliance(doc_id) or {}
        issues = comp.get("gaps") or []
        refs = comp.get("references") or []

        context = json.dumps({"refs": refs, "gaps": issues}, ensure_ascii=False)
        op = self.optimizer.generate_stage2_prompt(
            unified_context=context,
            field_name="compliance",
            document_type="doc",
            role="general",
            model_name=self.llm.model
        )

        out = self.llm.chat_json(system=op.full_prompt, user=f"QUERY:\n{query}")
        self.metrics.record_latency("agent_compliance", time.time() - start_ts)
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
        start_ts = time.time()
        
        # Integration Phase logic: Use ConfidenceLearner to weight inputs
        agent_data = {
            "text": text_ans,
            "layout": layout_ans,
            "compliance": comp_ans
        }
        
        reliability_weighted_inputs = {}
        for source, ans in agent_data.items():
            reported_conf = (ans.get("data") or {}).get("confidence", 0.5)
            learned_score = self.confidence_learner.compute_learned_confidence(
                field_name=source,
                model_name=self.llm.model,
                vlm_reported_confidence=reported_conf
            )
            reliability_weighted_inputs[source] = {
                "answer": ans.get("data"),
                "reliability_score": learned_score.learned_confidence,
                "confidence_level": learned_score.confidence_level,
                "uncertainty_factors": learned_score.uncertainty_factors
            }

        op = self.optimizer.generate_stage2_prompt(
            unified_context=json.dumps(reliability_weighted_inputs, indent=2),
            field_name="meta_synthesis",
            document_type="any",
            role="general",
            model_name=self.llm.model
        )

        out = self.llm.chat_json(system=op.full_prompt, user=f"QUERY:\n{query}")
        self.metrics.record_latency("agent_meta", time.time() - start_ts)
        return out or {"final_answer": "", "source": "none", "confidence": 0.0}
