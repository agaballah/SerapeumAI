# -*- coding: utf-8 -*-
"""
deep_thinking_agent.py — Agentic Supervisor for Complex Queries
---------------------------------------------------------------

The DeepThinkingAgent (DTA) handles queries that require multi-step
reasoning, cross-referencing, and verification.

Current canonical contract:
- AgentOrchestrator is the primary gatekeeper and routes only deep/complex
  queries here.
- This class remains deep-only for execution, but keeps a tiny
  `_classify_intent()` compatibility stub so older callers do not break.
- Certified facts remain mandatory for final answer synthesis.
- Raw discovery context is supplementary only.
"""

from __future__ import annotations

import json
import logging
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
    Main agentic supervisor for complex queries.

    Canonical behavior:
    - AgentOrchestrator decides whether a query is deep enough to reach DTA.
    - DTA executes deep reasoning only.
    - `_classify_intent()` is retained as a small compatibility helper for any
      remaining legacy callers such as orchestrator-side complexity checks.
    """

    DEEP_TRIGGERS = [
        "analyze", "compare", "contrast", "risk", "safety", "integrity",
        "across", "between", "all", "every", "review", "investigate",
        "cross-reference", "cross reference", "summarize all", "audit",
        "find issues", "what if", "what are the", "list all", "check if",
        "inconsistenc", "discrepanc", "mismatch", "conflict",
    ]

    MAX_RETRIES_PER_STEP = 2
    MAX_STEPS = 7

    def __init__(self, db, llm, fact_api=None, rag=None):
        self.db = db
        self.llm = llm
        self.rag = rag

        # FactQueryAPI — Layer 0 (certified facts before discovery context)
        if fact_api is not None:
            self._fact_api = fact_api
        else:
            try:
                from src.application.api.fact_api import FactQueryAPI
                self._fact_api = FactQueryAPI(db)
            except Exception:
                self._fact_api = None

    # -----------------------------------------------------------------------
    # Public Entry Points / Compatibility
    # -----------------------------------------------------------------------

    def _classify_intent(self, query: str) -> str:
        """
        Compatibility stub retained for older callers.

        This does NOT reintroduce the old light-answer path; it only classifies
        whether a query looks deep enough for agentic processing.
        """
        q_lower = query.lower()
        return "deep" if any(trigger in q_lower for trigger in self.DEEP_TRIGGERS) else "light"

    def answer_question(
        self,
        query: str,
        project_id: Optional[str] = None,
        snapshot_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Primary entry point for deep reasoning tasks.

        AgentOrchestrator is expected to route only complex queries here.
        """
        logger.info(
            "[DeepThinkingAgent] Deep reasoning path triggered | Query: %s",
            query[:80],
        )
        return self._deep_answer(query, project_id, snapshot_id)

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

        # ── Layer 0: Certified Facts (SSOT) — prefixed into synthesis ───────
        certified_block = ""
        certified_citations: List[Dict[str, Any]] = []

        if self._fact_api and project_id:
            try:
                fact_result = self._fact_api.get_certified_facts(
                    query_intent=query,
                    project_id=project_id,
                    snapshot_id=snapshot_id,
                )
                certified_block = fact_result.get("formatted_context", "")

                for f in fact_result.get("facts", []):
                    certified_citations.append(
                        {
                            "source": f"Fact {f.get('fact_id', '?')} [{f.get('fact_type', '')}]",
                            "quote": str(f.get("value_json", ""))[:120],
                        }
                    )

                if certified_block:
                    thinking_log.append(
                        f"🔐 CERTIFIED FACTS ({len(fact_result.get('facts', []))} facts from "
                        f"snapshot {snapshot_id or 'latest'}):"
                    )
                    thinking_log.append(certified_block[:600])

            except Exception as fe:
                logger.debug("[DeepThinkingAgent] Fact API failed in deep path: %s", fe)

        plan = self._create_plan(query, project_id)
        thinking_log.append(f"📋 PLAN ({len(plan.steps)} steps):")
        for s in plan.steps:
            thinking_log.append(f"  Step {s.step_no}: [{s.tool.upper()}] {s.description}")

        # Execute plan
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
                thinking_log.append(f"  🔄 Retrying Step {step.step_no} with broader approach...")
                step.retries += 1
                step.input_data["top_k"] = step.input_data.get("top_k", 5) + 3
                result2, passed2 = self._execute_and_verify(step, plan, all_results)
                step.result = result2
                step.status = "passed" if passed2 else "failed"
                thinking_log.append(
                    f"  {'✅ PASSED (retry)' if passed2 else '❌ Skipping (no data found)'}"
                )
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
                {
                    "step_no": 1,
                    "description": "...",
                    "tool": "search|analyze|compare|synthesize",
                    "keywords": "...",
                }
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
                steps: List[AgentStep] = []
                for raw_step in plan_resp["steps"][: self.MAX_STEPS]:
                    steps.append(
                        AgentStep(
                            step_no=int(raw_step.get("step_no", len(steps) + 1)),
                            description=str(
                                raw_step.get("description", "Search for relevant data")
                            ),
                            tool=str(raw_step.get("tool", "search")).lower(),
                            input_data={
                                "keywords": raw_step.get("keywords", query),
                                "top_k": 5,
                                "project_id": project_id,
                            },
                        )
                    )
                return AgentPlan(query=query, intent="deep", steps=steps)

        except Exception as e:
            logger.warning(
                "[DeepThinkingAgent] Plan creation via LLM failed: %s. Using default plan.",
                e,
            )

        # Default plan fallback
        return AgentPlan(
            query=query,
            intent="deep",
            steps=[
                AgentStep(
                    1,
                    f"Search documents for: {query}",
                    "search",
                    {"keywords": query, "top_k": 8, "project_id": project_id},
                ),
                AgentStep(
                    2,
                    "Analyze retrieved content for key findings",
                    "analyze",
                    {"keywords": query, "top_k": 5, "project_id": project_id},
                ),
                AgentStep(
                    3,
                    "Synthesize findings into coherent answer",
                    "synthesize",
                    {"keywords": query, "project_id": project_id},
                ),
            ],
        )

    # -----------------------------------------------------------------------
    # Execution & Verification
    # -----------------------------------------------------------------------

    def _execute_and_verify(
        self,
        step: AgentStep,
        plan: AgentPlan,
        prior_results: List[Dict[str, Any]],
    ):
        """Execute a step and verify it passes its success gate."""
        step.status = "running"
        try:
            result = self._dispatch_tool(step, plan, prior_results)
            passed = self._verify_step(step, result)
            return result, passed
        except Exception as e:
            logger.error("[DeepThinkingAgent] Step %s error: %s", step.step_no, e)
            return None, False

    def _dispatch_tool(
        self,
        step: AgentStep,
        plan: AgentPlan,
        prior_results: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Route step to the right tool implementation."""
        tool = step.tool
        project_id = step.input_data.get("project_id")
        keywords = str(step.input_data.get("keywords", plan.query))
        top_k = int(step.input_data.get("top_k", 5))

        if tool == "search":
            hits = self._search(keywords, project_id, top_k=top_k)
            return {"type": "search", "query": keywords, "hits": hits}

        if tool == "analyze":
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

        if tool == "compare":
            all_hits: List[Dict[str, Any]] = []
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
                logger.debug("[DeepThinkingAgent] Step %s FAIL: no search results", step.step_no)
                return False
            return True

        if rtype in ("analysis", "compare"):
            res = result.get("result")
            if not res or not isinstance(res, dict):
                logger.debug("[DeepThinkingAgent] Step %s FAIL: empty analysis", step.step_no)
                return False
            return any(v for v in res.values() if v)

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
                    "Rephrase your question with specific document names",
                ],
            }

        synthesis_parts: List[str] = []
        all_sources: List[Dict[str, Any]] = []

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

        # SSOT Enforcement: refuse if no certified facts
        if not certified_block:
            return {
                "answer": (
                    "I cannot answer this question because no certified facts are "
                    "available in the current snapshot."
                ),
                "citations": [],
                "suggested_actions": ["Run 'Build Facts' on project documents"],
            }

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
            "\"recommendations\": [...]}",
        )

        try:
            final_resp = self.llm.chat_json(
                system=system_prompt,
                user=f"Original Question: {query}\n\n### ALL RESEARCH:\n{combined_context}",
                task_type="reasoning",
                max_tokens=2000,
            )
        except Exception as e:
            logger.error("[DeepThinkingAgent] Synthesis failed: %s", e)
            final_resp = None

        if not final_resp or not isinstance(final_resp, dict):
            answer = f"Based on document analysis:\n\n{combined_context[:2000]}"
        else:
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
            "suggested_actions": suggested_actions,
        }

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    def _search(self, query: str, project_id: Optional[str], top_k: int = 5) -> List[Dict]:
        """Search for relevant documents using centralized RAGService."""
        results: List[Dict[str, Any]] = []

        if not self.rag:
            logger.warning(
                "[DeepThinkingAgent] Search requested but RAGService is unavailable. Refusing bypass."
            )
            return []

        try:
            raw_context = self.rag.retrieve_context(query, limit=top_k)
            if raw_context:
                results.append(
                    {
                        "text": raw_context,
                        "score": 1.0,
                        "source": "centralized_rag",
                        "page": "various",
                        "source_type": "rag_service",
                    }
                )
        except Exception as e:
            logger.error("[DeepThinkingAgent] Centralized RAG search failed: %s", e)

        return results

    def _format_context(self, results: List[Dict]) -> str:
        parts: List[str] = []
        for i, r in enumerate(results):
            src = r.get("source", "unknown")
            pg = r.get("page")
            pg_str = f" p.{pg}" if pg is not None else ""
            text = (r.get("text") or "")[:1500]
            score = r.get("score", 0.0)
            parts.append(f"[Source {i + 1}: {src}{pg_str} | Score: {score:.2f}]\n{text}")
        return "\n\n---\n\n".join(parts) if parts else "[No context found]"

    def _format_prior_results(self, prior_results: List[Dict]) -> str:
        parts: List[str] = []
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
        citations: List[Dict[str, Any]] = []

        for r in results:
            src = r.get("source", "")
            if src and src not in seen:
                seen.add(src)
                citations.append(
                    {
                        "source": src,
                        "page": r.get("page"),
                        "score": round(r.get("score", 0.0), 3),
                        "quote": (r.get("text") or "")[:200].strip(),
                    }
                )

        return citations[:10]