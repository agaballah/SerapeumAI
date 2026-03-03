# -*- coding: utf-8 -*-
"""
deep_thinking_agent.py — Agentic Supervisor for Complex Queries
---------------------------------------------------------------

The DeepThinkingAgent (DTA) handles queries that require multi-step
reasoning, cross-referencing, and verification. It acts as a "Main Agent"
that:

  1. CLASSIFY: Decides if a query is "Deep" (complex) or "Light" (simple).
  2. PLAN: Breaks the query into executable steps.
  3. EXECUTE: Runs each step using the appropriate tool/model.
  4. VERIFY (Success Gate): Checks if the step yielded valid, relevant data.
     - PASS -> Proceed to next step.
     - FAIL -> Replan or retry with a different approach.
  5. SYNTHESIZE: Compiles all step results into a final coherent answer.

Usage:
    agent = DeepThinkingAgent(db=db_manager, llm=llm_service)
    result = agent.answer_question("Analyze risk in drawings vs. specs")
    # result = {"answer": "...", "thinking": "...", "citations": [...], ...}
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field as dc_field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------

@dataclass
class AgentStep:
    """Represents one step in the agent's execution plan."""
    step_no: int
    description: str
    tool: str   # 'search', 'analyze', 'compare', 'synthesize'
    input_data: Dict[str, Any] = dc_field(default_factory=dict)
    result: Optional[Any] = None
    status: str = "pending"   # pending | running | passed | failed | skipped
    retries: int = 0


@dataclass
class AgentPlan:
    """Full execution plan for a query."""
    query: str
    intent: str  # 'deep' | 'light'
    steps: List[AgentStep] = dc_field(default_factory=list)
    context: Dict[str, Any] = dc_field(default_factory=dict)


# ---------------------------------------------------------------------------
# Deep Thinking Agent
# ---------------------------------------------------------------------------

class DeepThinkingAgent:
    """
    The Main Agentic Supervisor.
    Routes simple queries to a simple LLM call, complex queries to a
    full Plan → Execute → Verify → Synthesize loop.
    """

    # Triggers that indicate a "Deep" query requiring the agent loop
    DEEP_TRIGGERS = [
        "analyze", "compare", "contrast", "risk", "safety", "integrity",
        "across", "between", "all", "every", "review", "investigate",
        "cross-reference", "cross reference", "summarize all", "audit",
        "find issues", "what if", "what are the", "list all", "check if",
        "inconsistenc", "discrepanc", "mismatch", "conflict"
    ]

    MAX_RETRIES_PER_STEP = 2
    MAX_STEPS = 7

    def __init__(self, db, llm, fact_api=None):
        self.db = db
        self.llm = llm
        # FactQueryAPI — used as Layer 0 (certified facts before vector discovery)
        if fact_api is not None:
            self._fact_api = fact_api
        else:
            try:
                from src.application.api.fact_api import FactQueryAPI
                self._fact_api = FactQueryAPI(db)
            except Exception:
                self._fact_api = None

    # -----------------------------------------------------------------------
    # Public Entry Point
    # -----------------------------------------------------------------------

    def answer_question(
        self,
        query: str,
        project_id: Optional[str] = None,
        snapshot_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Primary entry point. Classifies the query and routes accordingly.

        Args:
            snapshot_id: When provided, fact retrieval is scoped to this snapshot
                         (SSOT §7 — snapshot-bound certified context).

        Returns:
            {
                "answer": str,
                "thinking": str,          # visible plan/reasoning trace
                "citations": [...],
                "suggested_actions": [...],
                "mode": "deep" | "light"
            }
        """
        intent = self._classify_intent(query)
        logger.info(f"[DeepThinkingAgent] Query intent: {intent} | Query: {query[:80]}")

        if intent == "light":
            return self._light_answer(query, project_id, snapshot_id)
        else:
            return self._deep_answer(query, project_id, snapshot_id)

    # -----------------------------------------------------------------------
    # Intent Classification
    # -----------------------------------------------------------------------

    def _classify_intent(self, query: str) -> str:
        """Classify query as 'deep' or 'light' based on trigger words."""
        q_lower = query.lower()
        if any(trigger in q_lower for trigger in self.DEEP_TRIGGERS):
            return "deep"
        return "light"

    # -----------------------------------------------------------------------
    # Light Path (Simple RAG + LLM)
    # -----------------------------------------------------------------------

    def _light_answer(
        self,
        query: str,
        project_id: Optional[str],
        snapshot_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Fast path: certified facts (layer 0) + optional RAG discovery context."""
        try:
            # ── Layer 0: Certified Facts (SSOT §7) ───────────────────────────────
            certified_block = ""
            certified_citations: List[Dict] = []
            if self._fact_api and project_id:
                try:
                    fact_result = self._fact_api.get_certified_facts(
                        query_intent=query,
                        project_id=project_id,
                        snapshot_id=snapshot_id,
                    )
                    certified_block = fact_result.get("formatted_context", "")
                    # Build citations from fact IDs
                    for f in fact_result.get("facts", []):
                        certified_citations.append({
                            "source": f"Fact {f.get('fact_id', '?')} [{f.get('fact_type', '')}]",
                            "quote": str(f.get("value_json", ""))[:120],
                        })
                    if snapshot_id:
                        logger.info(
                            f"[DeepThinkingAgent] {len(fact_result.get('facts', []))} certified facts "
                            f"retrieved for snapshot {snapshot_id}"
                        )
                except Exception as fe:
                    logger.debug(f"[DeepThinkingAgent] Fact API failed in light path: {fe}")

            # ── Layer 1: Vector / DB Discovery (fallback / supplementary) ────────
            context = self._search(query, project_id, top_k=5)
            discovery_str = self._format_context(context)

            # ── Compose prompt ────────────────────────────────────────────────────
            context_section = ""
            if certified_block:
                context_section = (
                    f"### CERTIFIED FACTS (VALIDATED / HUMAN_CERTIFIED)\n"
                    f"{certified_block}\n\n"
                    f"### DISCOVERY CONTEXT (supplementary)\n"
                    f"{discovery_str or '[No additional context found]'}"
                )
            else:
                context_section = discovery_str or "[No context found]"

            snapshot_note = f" (snapshot: {snapshot_id})" if snapshot_id else ""

            resp = self.llm.chat_json(
                system=(
                    "You are a precise AECO assistant.\n"
                    "STRICT BEHAVIOR CONTRACT (SSOT §7):\n"
                    "1. Answer ONLY from the 'CERTIFIED FACTS' block if present. "
                    "Certified facts take absolute precedence over discovery context.\n"
                    "2. If certified facts are present, cite each used fact: [Fact <id>].\n"
                    "3. If ONLY discovery context is present and certified facts are absent, "
                    "you may use it but label your answer as '[Discovery Context — not certified]'.\n"
                    "4. If no context is available, say exactly: "
                    "'No certified facts or documents found for this query.'"
                ),
                user=(
                    f"Question{snapshot_note}: {query}\n\n"
                    f"{context_section}"
                ),
                task_type="qa",
                max_tokens=1500,
            ) or {}

            answer = (
                resp.get("answer") or resp.get("summary") or
                (str(resp) if resp else "No certified facts or documents found for this query.")
            )

            all_citations = certified_citations + self._extract_citations(context)
            return {
                "answer": answer,
                "thinking": f"Certified facts: {len(certified_citations)} | Discovery hits: {len(context)}",
                "citations": all_citations,
                "suggested_actions": [],
                "mode": "light",
            }
        except Exception as e:
            logger.error(f"[DeepThinkingAgent] Light answer failed: {e}")
            return {"answer": f"Error generating answer: {e}", "thinking": "", "citations": [], "mode": "light"}

    # -----------------------------------------------------------------------
    # Deep Path (Plan → Execute → Verify → Synthesize)
    # -----------------------------------------------------------------------

    def _deep_answer(
        self,
        query: str,
        project_id: Optional[str],
        snapshot_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Full agentic loop:
        1. Create an execution plan.
        2. Execute each step with verification.
        3. Synthesize the final answer.
        """
        thinking_log: List[str] = []

        # ── Layer 0: Certified Facts (SSOT §7) — prefixed into synthesis ─────────
        certified_block = ""
        certified_citations: List[Dict] = []
        if self._fact_api and project_id:
            try:
                fact_result = self._fact_api.get_certified_facts(
                    query_intent=query,
                    project_id=project_id,
                    snapshot_id=snapshot_id,
                )
                certified_block = fact_result.get("formatted_context", "")
                for f in fact_result.get("facts", []):
                    certified_citations.append({
                        "source": f"Fact {f.get('fact_id', '?')} [{f.get('fact_type', '')}]",
                        "quote": str(f.get("value_json", ""))[:120],
                    })
                if certified_block:
                    thinking_log.append(
                        f"🔐 CERTIFIED FACTS ({len(fact_result.get('facts', []))} facts from "
                        f"snapshot {snapshot_id or 'latest'}):"
                    )
                    thinking_log.append(certified_block[:600])
            except Exception as fe:
                logger.debug(f"[DeepThinkingAgent] Fact API failed in deep path: {fe}")

        plan = self._create_plan(query, project_id)
        thinking_log.append(f"📋 PLAN ({len(plan.steps)} steps):")
        for s in plan.steps:
            thinking_log.append(f"  Step {s.step_no}: [{s.tool.upper()}] {s.description}")

        # Execute Plan
        all_results: List[Dict[str, Any]] = []
        for step in plan.steps:
            if len(all_results) >= self.MAX_STEPS:
                break

            thinking_log.append(f"\n⚙️  Executing Step {step.step_no}: {step.description}")
            result, passed = self._execute_and_verify(step, plan, all_results)

            step.result = result
            step.status = "passed" if passed else "failed"
            thinking_log.append(f"  {'✅ PASSED' if passed else '❌ FAILED'}")

            if passed and result:
                all_results.append(result)
            elif not passed and step.retries < self.MAX_RETRIES_PER_STEP:
                # Replan: widen search and retry
                thinking_log.append(f"  🔄 Retrying Step {step.step_no} with broader approach...")
                step.retries += 1
                step.input_data["top_k"] = step.input_data.get("top_k", 5) + 3
                result2, passed2 = self._execute_and_verify(step, plan, all_results)
                step.result = result2
                step.status = "passed" if passed2 else "failed"
                thinking_log.append(f"  {'✅ PASSED (retry)' if passed2 else '❌ Skipping (no data found)'}")
                if passed2 and result2:
                    all_results.append(result2)

        # Synthesize (inject certified facts as high-priority prefix)
        thinking_log.append(f"\n🧠 Synthesizing {len(all_results)} results...")
        final = self._synthesize(query, all_results, certified_block=certified_block)

        # Merge certified citations first
        all_citations = certified_citations + final.get("citations", [])

        return {
            "answer": final.get("answer", "Could not generate final answer."),
            "thinking": "\n".join(thinking_log),
            "citations": all_citations,
            "suggested_actions": final.get("suggested_actions", []),
            "mode": "deep",
        }

    # -----------------------------------------------------------------------
    # Planning
    # -----------------------------------------------------------------------

    def _create_plan(self, query: str, project_id: Optional[str]) -> AgentPlan:
        """
        Ask the LLM to decompose the query into concrete steps.
        Falls back to a default plan if LLM planning fails.
        """
        plan_schema = {
            "steps": [
                {"step_no": 1, "description": "...", "tool": "search|analyze|compare|synthesize", "keywords": "..."}
            ]
        }

        try:
            plan_resp = self.llm.chat_json(
                system=(
                    "You are an expert AECO research planner. "
                    "Decompose the user's query into 3-6 concrete steps. "
                    "Each step must use one tool: 'search', 'analyze', 'compare'. "
                    "Be specific about what to search/compare. "
                    "Output ONLY valid JSON matching the schema."
                ),
                user=(
                    f"Query: {query}\n\n"
                    "Decompose this into concrete research steps. "
                    "For 'search' steps, specify the exact keywords. "
                    "For 'compare' steps, specify which sources to compare."
                ),
                schema=plan_schema,
                task_type="reasoning",
                max_tokens=800,
            )

            if plan_resp and isinstance(plan_resp, dict) and plan_resp.get("steps"):
                steps = []
                for raw_step in plan_resp["steps"][:self.MAX_STEPS]:
                    s = AgentStep(
                        step_no=int(raw_step.get("step_no", len(steps) + 1)),
                        description=str(raw_step.get("description", "Search for relevant data")),
                        tool=str(raw_step.get("tool", "search")).lower(),
                        input_data={
                            "keywords": raw_step.get("keywords", query),
                            "top_k": 5,
                            "project_id": project_id,
                        }
                    )
                    steps.append(s)
                return AgentPlan(query=query, intent="deep", steps=steps)
        except Exception as e:
            logger.warning(f"[DeepThinkingAgent] Plan creation via LLM failed: {e}. Using default plan.")

        # Default plan fallback
        return AgentPlan(
            query=query, intent="deep",
            steps=[
                AgentStep(1, f"Search documents for: {query}", "search",
                          {"keywords": query, "top_k": 8, "project_id": project_id}),
                AgentStep(2, "Analyze retrieved content for key findings", "analyze",
                          {"keywords": query, "top_k": 5, "project_id": project_id}),
                AgentStep(3, "Synthesize findings into coherent answer", "synthesize",
                          {"keywords": query, "project_id": project_id}),
            ]
        )

    # -----------------------------------------------------------------------
    # Execution & Verification
    # -----------------------------------------------------------------------

    def _execute_and_verify(
        self, step: AgentStep, plan: AgentPlan, prior_results: List[Dict]
    ):
        """Execute a step and verify it passes its success gate."""
        step.status = "running"
        try:
            result = self._dispatch_tool(step, plan, prior_results)
            passed = self._verify_step(step, result)
            return result, passed
        except Exception as e:
            logger.error(f"[DeepThinkingAgent] Step {step.step_no} error: {e}")
            return None, False

    def _dispatch_tool(
        self, step: AgentStep, plan: AgentPlan, prior_results: List[Dict]
    ) -> Optional[Dict[str, Any]]:
        """Route step to the right tool implementation."""
        tool = step.tool
        project_id = step.input_data.get("project_id")
        keywords = str(step.input_data.get("keywords", plan.query))
        top_k = int(step.input_data.get("top_k", 5))

        if tool == "search":
            hits = self._search(keywords, project_id, top_k=top_k)
            return {"type": "search", "query": keywords, "hits": hits}

        elif tool == "analyze":
            hits = self._search(keywords, project_id, top_k=top_k)
            if not hits:
                return None
            context_str = self._format_context(hits)
            prior_ctx = self._format_prior_results(prior_results)

            analysis = self.llm.chat_json(
                system=(
                    "You are an AECO technical analyst. "
                    "Analyze the provided context and extract key findings.\n"
                    + (f"Prior research context:\n{prior_ctx}" if prior_ctx else "")
                ),
                user=f"Analyze for: {keywords}\n\n### CONTEXT:\n{context_str}",
                task_type="analysis",
                max_tokens=1200,
            )
            return {"type": "analysis", "query": keywords, "result": analysis, "sources": hits}

        elif tool == "compare":
            all_hits = []
            for pr in prior_results:
                all_hits.extend(pr.get("hits", pr.get("sources", [])))
            if not all_hits:
                all_hits = self._search(keywords, project_id, top_k=top_k * 2)
            context_str = self._format_context(all_hits)

            comparison = self.llm.chat_json(
                system=(
                    "You are an AECO cross-reference expert. "
                    "Compare and identify discrepancies, conflicts, or agreements "
                    "between multiple sources. Be specific and cite source documents."
                ),
                user=f"Compare for: {keywords}\n\n### COMBINED CONTEXT:\n{context_str}",
                task_type="analysis",
                max_tokens=1500,
            )
            return {"type": "compare", "query": keywords, "result": comparison, "sources": all_hits}

        else:
            # Generic fallback: treat as search
            hits = self._search(keywords, project_id, top_k=top_k)
            return {"type": "search", "query": keywords, "hits": hits}

    def _verify_step(self, step: AgentStep, result: Optional[Any]) -> bool:
        """
        Success Gate: Verify the step produced meaningful output.
        
        Rules:
        - search: Must return at least 1 result.
        - analyze: Must produce a non-empty result dict.
        - compare: Must have results and sources.
        """
        if result is None:
            return False

        rtype = result.get("type", "")

        if rtype == "search":
            hits = result.get("hits", [])
            if not hits:
                logger.debug(f"[DeepThinkingAgent] Step {step.step_no} FAIL: no search results")
                return False
            return True

        elif rtype in ("analysis", "compare"):
            res = result.get("result")
            if not res or not isinstance(res, dict):
                logger.debug(f"[DeepThinkingAgent] Step {step.step_no} FAIL: empty analysis")
                return False
            # At least one non-empty value in result
            non_empty = any(v for v in res.values() if v)
            return non_empty

        return bool(result)

    # -----------------------------------------------------------------------
    # Synthesis
    # -----------------------------------------------------------------------

    def _synthesize(
        self,
        query: str,
        results: List[Dict[str, Any]],
        certified_block: str = "",
    ) -> Dict[str, Any]:
        """Combine certified facts + step results into a final coherent answer."""
        if not results:
            return {
                "answer": (
                    "I searched through the project documents but could not find "
                    "sufficient information to answer your question."
                ),
                "citations": [],
                "suggested_actions": [
                    "Try uploading more relevant documents",
                    "Rephrase your question with specific document names"
                ]
            }

        # Build a combined context from results
        synthesis_parts = []
        all_sources = []

        for r in results:
            rtype = r.get("type", "unknown")
            if rtype == "search":
                hits = r.get("hits", [])
                all_sources.extend(hits)
                if hits:
                    synthesis_parts.append(
                        f"### Search Results for '{r.get('query')}':\n"
                        + self._format_context(hits)
                    )
            elif rtype in ("analysis", "compare"):
                res = r.get("result", {})
                sources = r.get("sources", [])
                all_sources.extend(sources)
                if res:
                    synthesis_parts.append(
                        f"### {rtype.title()} Results for '{r.get('query')}':\n"
                        + json.dumps(res, indent=2, ensure_ascii=False)[:2000]
                    )

        combined_context = "\n\n".join(synthesis_parts)[:6000]

        # Prepend certified facts as the highest-priority context block
        if certified_block:
            combined_context = (
                "### CERTIFIED FACTS (VALIDATED / HUMAN_CERTIFIED — takes absolute precedence)\n"
                + certified_block
                + "\n\n### DISCOVERY RESEARCH\n"
                + combined_context
            )

        system_prompt = (
            "You are a senior AECO expert providing a final, comprehensive answer.\n"
            "STRICT CONTRACT (SSOT §7):\n"
            "1. CERTIFIED FACTS above all. If a certified fact contradicts discovery context, "
            "trust the certified fact.\n"
            "2. Cite certified facts as [Fact <id>], discovery sources as [Doc Name, Page X].\n"
            "3. Synthesize ALL provided research into a coherent, well-structured response.\n"
            "Format as: {\"answer\": \"...\", \"key_findings\": [...], \"risks\": [...], "
            "\"recommendations\": [...]}"
        )

        try:
            final_resp = self.llm.chat_json(
                system=system_prompt,
                user=f"Original Question: {query}\n\n### ALL RESEARCH:\n{combined_context}",
                task_type="reasoning",
                max_tokens=2000,
            )
        except Exception as e:
            logger.error(f"[DeepThinkingAgent] Synthesis failed: {e}")
            final_resp = None

        if not final_resp or not isinstance(final_resp, dict):
            # Fallback: format raw results as answer
            answer = f"Based on document analysis:\n\n{combined_context[:2000]}"
        else:
            # Build rich answer from structured response
            answer = final_resp.get("answer", "")
            findings = final_resp.get("key_findings", [])
            risks = final_resp.get("risks", [])
            recs = final_resp.get("recommendations", [])

            if findings:
                answer += "\n\n**Key Findings:**\n" + "\n".join(f"• {f}" for f in findings)
            if risks:
                answer += "\n\n**Risks Identified:**\n" + "\n".join(f"⚠️ {r}" for r in risks)
            if recs:
                answer += "\n\n**Recommendations:**\n" + "\n".join(f"→ {r}" for r in recs)

        citations = self._extract_citations(all_sources)
        suggested_actions = (
            final_resp.get("recommendations", [])[:3] if isinstance(final_resp, dict) else []
        )

        return {
            "answer": answer,
            "citations": citations,
            "suggested_actions": suggested_actions
        }

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    def _search(self, query: str, project_id: Optional[str], top_k: int = 5) -> List[Dict]:
        """Search for relevant documents using vector store and DB."""
        results = []

        # 1. Vector store semantic search
        try:
            from src.infra.adapters.vector_store import VectorStore
            vs = VectorStore()
            if vs._initialized:
                filter_dict = {"project_id": project_id} if project_id else None
                hits = vs.similarity_search(query, k=top_k, filter=filter_dict)
                for h in hits:
                    results.append({
                        "text": h.get("text", ""),
                        "score": h.get("score", 0.0),
                        "source": h.get("metadata", {}).get("doc_id", "unknown"),
                        "page": h.get("metadata", {}).get("page_index"),
                        "source_type": "vector",
                    })
        except Exception as e:
            logger.debug(f"[DeepThinkingAgent] Vector search failed: {e}")

        # 2. DB text search fallback if vector search is empty
        if not results and self.db:
            try:
                rows = self.db.search_pages(query, project_id=project_id, limit=top_k)
                for row in (rows or []):
                    results.append({
                        "text": row.get("py_text") or row.get("ocr_text") or "",
                        "score": 0.5,
                        "source": row.get("doc_id", "unknown"),
                        "page": row.get("page_index"),
                        "source_type": "db_text",
                    })
            except Exception as e:
                logger.debug(f"[DeepThinkingAgent] DB text search failed: {e}")

        return results

    def _format_context(self, results: List[Dict]) -> str:
        parts = []
        for i, r in enumerate(results):
            src = r.get("source", "unknown")
            pg = r.get("page")
            pg_str = f" p.{pg}" if pg is not None else ""
            text = (r.get("text") or "")[:1500]
            score = r.get("score", 0.0)
            parts.append(f"[Source {i+1}: {src}{pg_str} | Score: {score:.2f}]\n{text}")
        return "\n\n---\n\n".join(parts) if parts else "[No context found]"

    def _format_prior_results(self, prior_results: List[Dict]) -> str:
        parts = []
        for r in prior_results:
            rtype = r.get("type", "")
            query = r.get("query", "")
            if rtype == "search":
                hits = r.get("hits", [])
                parts.append(f"Search '{query}': {len(hits)} results found")
            elif rtype in ("analysis", "compare"):
                res = r.get("result", {})
                excerpt = json.dumps(res, ensure_ascii=False)[:300] if res else "no result"
                parts.append(f"{rtype.title()} '{query}': {excerpt}")
        return "\n".join(parts)

    def _extract_citations(self, results: List[Dict]) -> List[Dict[str, Any]]:
        """Extract rich citations from search results."""
        seen = set()
        citations = []
        for r in results:
            src = r.get("source", "")
            if src and src not in seen:
                seen.add(src)
                citations.append({
                    "source": src,
                    "page": r.get("page"),
                    "score": round(r.get("score", 0.0), 3),
                    "quote": (r.get("text") or "")[:200].strip()
                })
        return citations[:10]  # Cap at 10 citations
