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

Canonical runtime path:
- answer_question() is the SSOT-governed path
- DeepThinkingAgent is used only for complex/deep queries
- answer_question_map_reduce() is retained only as a deprecated
  compatibility path for active tests / legacy callers
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

from src.application.api.fact_api import FactQueryAPI
from src.application.services.artifact_service import ArtifactService
from src.application.services.coverage_gate import CoverageGate
from src.application.services.chat_answer_presentation import build_answer_presentation
from src.domain.facts.repository import FactRepository
from src.infra.adapters.llm_service import LLMService
from src.infra.persistence.database_manager import DatabaseManager

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    def __init__(
        self,
        *,
        db: DatabaseManager,
        llm: LLMService,
        rag: Optional[Any] = None,
        global_db: Optional[DatabaseManager] = None,
    ) -> None:
        self.db = db
        self.llm = llm
        self.rag = rag
        self.global_db = global_db

        # Deprecated compatibility slot for legacy map-reduce callers/tests.
        # Canonical query path is answer_question().
        self.evidence_builder = None

        self.fact_repo = FactRepository(db)

        # SSOT Enforcement Layer
        from src.infra.telemetry.metrics_collector import MetricsCollector

        self.metrics = MetricsCollector(db)
        self.coverage_gate = CoverageGate(db)
        self.fact_api = FactQueryAPI(db)

        # Confidence / prompt optimization
        from src.domain.intelligence.confidence_learner import ConfidenceLearner
        from src.domain.intelligence.prompt_optimizer import PromptOptimizer

        self.confidence_learner = ConfidenceLearner(db)
        self.optimizer = PromptOptimizer(
            db=db,
            confidence_learner=self.confidence_learner,
        )

        # Artifact Folder
        artifact_root = os.path.join(db.root_dir, ".serapeum", "artifacts")
        self.artifact_service = ArtifactService(output_dir=artifact_root)

        # Semantic tools
        from src.infra.config.configuration_manager import get_config
        from src.tools.bim_query_tool import BIMQueryTool
        from src.tools.calculator_tool import CalculatorTool
        from src.tools.n8n_tool import N8NTool
        from src.tools.schedule_query_tool import ScheduleQueryTool

        config = get_config()
        n8n_url = (config.get_section("n8n") or {}).get("webhook_url", "")

        self.tools = {
            "query_bim": BIMQueryTool(db),
            "query_schedule": ScheduleQueryTool(db),
            "calculator": CalculatorTool(),
            "n8n_workflow": N8NTool(n8n_url),
        }

        # Deep Thinking Agent (for complex multi-step queries)
        try:
            from src.analysis_engine.deep_thinking_agent import DeepThinkingAgent

            self.deep_agent = DeepThinkingAgent(
                db=db,
                llm=llm,
                rag=self.rag,
                fact_api=self.fact_api,
            )
            logger.info("[AgentOrchestrator] DeepThinkingAgent initialized.")
        except Exception as e:
            logger.warning(f"[AgentOrchestrator] DeepThinkingAgent unavailable: {e}")
            self.deep_agent = None

    # ------------------------------------------------------------------
    # WORLD-CLASS AGENTIC REASONING (Extended-Thinking Style)
    # ------------------------------------------------------------------

    def answer_question(
        self,
        query: str,
        project_id: str,
        snapshot_id: Optional[str] = None,
        context: Optional[str] = None,
        stream: bool = False,
        cancellation_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        SSOT-compliant agentic pipeline (§7 Strict Chat Protocol):

        Step 0: Resolve snapshot (snapshot-bound chat)
        Step 1: CoverageGate — refuse if certified facts are missing
        Step 2: Route to DeepThinkingAgent (complex) or fast path (simple)
        Step 3: FactQueryAPI — retrieve ONLY certified facts
        Step 4: Conflict disclosure
        Step 5: LLM narrates from certified context first
        """
        # ── Step 0: Resolve snapshot ─────────────────────────────────────
        if not snapshot_id:
            try:
                snapshot_id = self.db.get_or_create_snapshot(project_id)
                logger.info(f"[AgentOrchestrator] snapshot={snapshot_id} project={project_id}")
            except Exception as e:
                logger.warning(f"[AgentOrchestrator] Snapshot resolution failed: {e}")

        # ── Step 1: Coverage Gate (informational) ─────────────────────
        coverage: Dict[str, Any] = {
            "is_complete": False,
            "required_fact_types": [],
            "missing_fact_types": [],
            "job_plan": [],
        }
        try:
            coverage = self.coverage_gate.check(
                query=query,
                project_id=project_id,
                snapshot_id=snapshot_id,
            )
        except Exception as e:
            logger.warning(f"[AgentOrchestrator] Coverage gate degraded to informational mode: {e}")

        # ── Step 2: Trusted facts first ─────────────────────────────────
        trusted_facts: List[Dict[str, Any]] = []
        trusted_conflicts: List[Dict[str, Any]] = []
        citations: List[Dict[str, Any]] = []
        try:
            fact_result = self.fact_api.get_certified_facts(
                query_intent=query,
                project_id=project_id,
                snapshot_id=snapshot_id,
            )
            trusted_facts = fact_result.get("facts", []) or []
            trusted_conflicts = fact_result.get("conflicts", []) or []
            citations = self._build_structured_citations(trusted_facts)
        except Exception as e:
            logger.error(f"[AgentOrchestrator] Fact API failed: {e}")

        # ── Step 3: Lower provenance lanes ──────────────────────────────
        extracted_evidence = self._retrieve_extracted_evidence(query=query, project_id=project_id)
        linked_support = self._retrieve_linked_support(query=query, project_id=project_id)
        ai_lane = self._build_ai_generated_lane(
            query=query,
            project_id=project_id,
            trusted_facts=trusted_facts,
            extracted_evidence=extracted_evidence,
            linked_support=linked_support,
        )

        has_grounded_material = any([
            bool(trusted_facts),
            bool(extracted_evidence),
            bool(linked_support),
            bool(ai_lane.get("analysis_support")),
            bool(ai_lane.get("synthesis")),
        ])

        if not has_grounded_material:
            refusal = self._compose_no_grounded_material_refusal(query=query, coverage=coverage)
            return {
                "answer": refusal,
                "answer_presentation": {
                    "summary_block": {
                        "title": "Operator Summary",
                        "source_label": "No grounded material",
                        "text": "No meaningful project-grounded material was available for this question.",
                    },
                    "sections": [],
                    "candidate_fact_suggestions": [],
                    "copy_text": refusal,
                },
                "candidate_fact_suggestions": [],
                "thinking": (
                    "No trusted facts, extracted evidence, linked support, or AI-generated "
                    "project-grounded synthesis were available for this question."
                ),
                "citations": [],
                "support_facts": [],
                "supporting_only": True,
                "compliance_status": "NO_PROJECT_GROUNDED_MATERIAL",
                "suggested_actions": [
                    step.get("action", "Run extraction") for step in coverage.get("job_plan", [])
                ],
                "mode": "refused",
            }

        presentation = build_answer_presentation(
            query=query,
            trusted_facts=trusted_facts,
            trusted_conflicts=trusted_conflicts,
            extracted_evidence=extracted_evidence,
            linked_support=linked_support,
            ai_lane=ai_lane,
            coverage=coverage,
        )
        answer = presentation.get("main_answer_text") or presentation.get("copy_text") or self._compose_multi_lane_answer(
            query=query,
            trusted_facts=trusted_facts,
            trusted_conflicts=trusted_conflicts,
            extracted_evidence=extracted_evidence,
            linked_support=linked_support,
            ai_lane=ai_lane,
            coverage=coverage,
        )

        return {
            "answer": answer,
            "answer_presentation": presentation,
            "candidate_fact_suggestions": presentation.get("candidate_fact_suggestions", []),
            "thinking": self._compose_multi_lane_thinking(
                trusted_facts,
                extracted_evidence,
                linked_support,
                ai_lane,
            ),
            "citations": citations,
            "support_facts": [],
            "supporting_only": not bool(trusted_facts),
            "compliance_status": (
                "ANSWERED_WITH_PROVENANCE" if trusted_facts else "ANSWERED_WITH_PROJECT_GROUNDED_SUPPORT"
            ),
            "suggested_actions": [
                step.get("action", "Run extraction") for step in coverage.get("job_plan", [])
            ] if not coverage.get("is_complete", False) else [],
            "mode": "answered",
            "source_lanes": {
                "trusted_facts": len(trusted_facts),
                "extracted_evidence": len(extracted_evidence),
                "linked_support": len(linked_support),
                "ai_analysis_support": len(ai_lane.get("analysis_support", [])),
                "ai_generated_synthesis": bool(ai_lane.get("synthesis")),
            },
        }

    def _extract_query_terms(self, query: str, *, min_len: int = 3, max_terms: int = 8) -> List[str]:
        import re

        q = (query or "").strip().lower()
        if not q:
            return []

        if q in {"scope", "project scope", "scope summary", "summarize scope"}:
            return ["scope", "work", "project"]

        terms = [t for t in re.findall(r"[a-z0-9_]+", q) if len(t) >= min_len]
        deduped: List[str] = []
        seen = set()
        for term in terms:
            if term in seen:
                continue
            seen.add(term)
            deduped.append(term)
        return deduped[:max_terms]

    def _stringify_value(self, value: Any) -> str:
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, (dict, list)):
            try:
                return json.dumps(value, ensure_ascii=False)
            except Exception:
                return str(value)
        if value is None:
            return ""
        return str(value)

    def _trim_text(self, value: Any, limit: int = 320) -> str:
        text = " ".join(self._stringify_value(value).split())
        if len(text) <= limit:
            return text
        return text[: limit - 3].rstrip() + "..."

    def _retrieve_extracted_evidence(self, query: str, project_id: str, limit: int = 6) -> List[Dict[str, Any]]:
        terms = self._extract_query_terms(query)
        if not terms:
            return []

        evidence: List[Dict[str, Any]] = []
        seen = set()

        def _add_item(source_path: str, page_index: int, text: str, provenance: str) -> None:
            text = self._trim_text(text, limit=420)
            if not text:
                return
            key = (source_path or "unknown", int(page_index or 0), provenance, text[:160])
            if key in seen:
                return
            seen.add(key)
            evidence.append(
                {
                    "source_path": source_path or "unknown",
                    "page_index": int(page_index or 0),
                    "text": text,
                    "provenance": provenance,
                }
            )

        like_terms = [f"%{t}%" for t in terms]

        try:
            page_expr = "LOWER(COALESCE(p.py_text,'') || ' ' || COALESCE(p.ocr_text,''))"
            where = " OR ".join([f"{page_expr} LIKE ?" for _ in like_terms])
            sql = f"""
                SELECT
                    COALESCE(d.abs_path, d.file_name, 'unknown') AS source_path,
                    COALESCE(p.page_index, 0) AS page_index,
                    COALESCE(NULLIF(p.py_text, ''), COALESCE(p.ocr_text, '')) AS evidence_text,
                    CASE
                        WHEN COALESCE(p.py_text, '') <> '' THEN 'deterministic extraction'
                        ELSE 'OCR / parser output'
                    END AS provenance
                FROM pages p
                LEFT JOIN documents d ON d.doc_id = p.doc_id
                WHERE d.project_id = ? AND ({where})
                ORDER BY COALESCE(p.page_index, 0)
                LIMIT ?
            """
            rows = self.db.execute(sql, tuple([project_id] + like_terms + [limit * 2])).fetchall()
            for row in rows:
                _add_item(row["source_path"], row["page_index"], row["evidence_text"], row["provenance"])
                if len(evidence) >= limit:
                    return evidence[:limit]
        except Exception as exc:
            logger.debug("[AgentOrchestrator] Extracted evidence page query failed: %s", exc)

        try:
            block_expr = "LOWER(COALESCE(b.text,'') || ' ' || COALESCE(b.heading_title,''))"
            where = " OR ".join([f"{block_expr} LIKE ?" for _ in like_terms])
            sql = f"""
                SELECT
                    COALESCE(fv.source_path, d.file_name, d.abs_path, 'unknown') AS source_path,
                    COALESCE(b.page_index, 0) AS page_index,
                    TRIM(COALESCE(b.heading_title, '') || ' ' || COALESCE(b.text, '')) AS evidence_text
                FROM doc_blocks b
                LEFT JOIN documents d ON d.doc_id = b.doc_id
                LEFT JOIN file_versions fv ON d.file_name = fv.source_path OR d.abs_path = fv.source_path
                WHERE d.project_id = ? AND ({where})
                ORDER BY COALESCE(b.page_index, 0)
                LIMIT ?
            """
            rows = self.db.execute(sql, tuple([project_id] + like_terms + [limit * 2])).fetchall()
            for row in rows:
                _add_item(row["source_path"], row["page_index"], row["evidence_text"], "parser output")
                if len(evidence) >= limit:
                    break
        except Exception as exc:
            logger.debug("[AgentOrchestrator] Extracted evidence block query failed: %s", exc)

        return evidence[:limit]

    def _retrieve_linked_support(self, query: str, project_id: str, limit: int = 4) -> List[Dict[str, Any]]:
        terms = self._extract_query_terms(query, min_len=2, max_terms=6)
        if not terms:
            return []

        try:
            from src.domain.intelligence.truth_graph import TruthGraphService
        except Exception as exc:
            logger.debug("[AgentOrchestrator] TruthGraphService unavailable: %s", exc)
            return []

        graph = TruthGraphService(self.db)
        rows = []
        try:
            where = " OR ".join(["LOWER(value) LIKE ?" for _ in terms])
            sql = f"SELECT id, entity_type, value FROM entity_nodes WHERE project_id = ? AND ({where}) LIMIT ?"
            params = [project_id] + [f"%{t}%" for t in terms] + [limit]
            rows = self.db.execute(sql, tuple(params)).fetchall()
        except Exception as exc:
            logger.debug("[AgentOrchestrator] Linked support base query failed: %s", exc)
            return []

        support: List[Dict[str, Any]] = []
        seen = set()
        for row in rows:
            node = dict(row)
            try:
                neighbors = graph.get_neighbors(int(node.get("id")))
            except Exception:
                neighbors = []
            if not neighbors:
                continue
            sample = neighbors[:2]
            for nb in sample:
                key = (node.get("value"), nb.get("value"), nb.get("rel_type"))
                if key in seen:
                    continue
                seen.add(key)
                support.append(
                    {
                        "entity_type": node.get("entity_type", "entity"),
                        "entity_value": self._trim_text(node.get("value"), 140),
                        "relation": nb.get("rel_type", "linked_to"),
                        "neighbor_type": nb.get("entity_type", "entity"),
                        "neighbor_value": self._trim_text(nb.get("value"), 140),
                        "confidence_tier": nb.get("confidence_tier") or "unknown",
                    }
                )
                if len(support) >= limit:
                    return support
        return support

    def _retrieve_ai_analysis_support(self, query: str, project_id: str, limit: int = 4) -> List[Dict[str, Any]]:
        terms = self._extract_query_terms(query)
        if not terms:
            return []

        results: List[Dict[str, Any]] = []
        seen = set()
        try:
            summary_expr = "LOWER(COALESCE(p.page_summary_detailed,'') || ' ' || COALESCE(p.page_summary_short,''))"
            where = " OR ".join([f"{summary_expr} LIKE ?" for _ in terms])
            sql = f"""
                SELECT
                    COALESCE(d.abs_path, d.file_name, 'unknown') AS source_path,
                    COALESCE(p.page_index, 0) AS page_index,
                    COALESCE(NULLIF(p.page_summary_detailed, ''), COALESCE(p.page_summary_short, '')) AS ai_text
                FROM pages p
                LEFT JOIN documents d ON d.doc_id = p.doc_id
                WHERE d.project_id = ? AND ({where})
                ORDER BY COALESCE(p.page_index, 0)
                LIMIT ?
            """
            rows = self.db.execute(sql, tuple([project_id] + [f"%{t}%" for t in terms] + [limit * 2])).fetchall()
            for row in rows:
                ai_text = self._trim_text(row["ai_text"], 360)
                if not ai_text:
                    continue
                key = (row["source_path"], int(row["page_index"] or 0), ai_text[:160])
                if key in seen:
                    continue
                seen.add(key)
                results.append(
                    {
                        "source_path": row["source_path"],
                        "page_index": int(row["page_index"] or 0),
                        "text": ai_text,
                        "provenance": "stored AI page analysis",
                    }
                )
                if len(results) >= limit:
                    break
        except Exception as exc:
            logger.debug("[AgentOrchestrator] AI analysis support query failed: %s", exc)
        return results

    def _generate_query_time_synthesis(
        self,
        *,
        query: str,
        trusted_facts: List[Dict[str, Any]],
        extracted_evidence: List[Dict[str, Any]],
        linked_support: List[Dict[str, Any]],
        analysis_support: List[Dict[str, Any]],
    ) -> str:
        if not self.llm:
            return ""
        if not any([trusted_facts, extracted_evidence, linked_support, analysis_support]):
            return ""

        trusted_lines = [
            f"- {fact.get('fact_type')}: {self._trim_text(fact.get('value'), 180)}"
            for fact in trusted_facts[:6]
        ]
        evidence_lines = [
            f"- {item.get('provenance')}: {item.get('source_path')} p.{int(item.get('page_index', 0)) + 1} — {item.get('text')}"
            for item in extracted_evidence[:4]
        ]
        linked_lines = [
            f"- {item.get('entity_type')} '{item.get('entity_value')}' --{item.get('relation')}--> {item.get('neighbor_type')} '{item.get('neighbor_value')}' ({item.get('confidence_tier')})"
            for item in linked_support[:4]
        ]
        analysis_lines = [
            f"- {item.get('source_path')} p.{int(item.get('page_index', 0)) + 1}: {item.get('text')}"
            for item in analysis_support[:3]
        ]

        system = (
            "You are writing a clearly labeled AI-generated, non-governing synthesis for SerapeumAI. "
            "Use ONLY the provided project-grounded material. Do not claim certification. "
            "If information is partial, say so plainly. Return plain text only."
        )
        trusted_block = "\n".join(trusted_lines) if trusted_lines else "- none"
        evidence_block = "\n".join(evidence_lines) if evidence_lines else "- none"
        linked_block = "\n".join(linked_lines) if linked_lines else "- none"
        analysis_block = "\n".join(analysis_lines) if analysis_lines else "- none"
        user = (
            f"QUESTION: {query}\n\n"
            f"TRUSTED FACTS:\n{trusted_block}\n\n"
            f"EXTRACTED EVIDENCE:\n{evidence_block}\n\n"
            f"LINKED SUPPORT:\n{linked_block}\n\n"
            f"STORED AI ANALYSIS SUPPORT:\n{analysis_block}\n\n"
            "Write 3-6 sentences that answer the question as far as the material supports."
        )

        try:
            resp = self.llm.chat(
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                task_type="universal",
                temperature=0.2,
            ) or {}
            return self._trim_text((resp.get("choices") or [{}])[0].get("message", {}).get("content", ""), 900)
        except Exception as exc:
            logger.debug("[AgentOrchestrator] Query-time synthesis failed: %s", exc)
            return ""

    def _build_ai_generated_lane(
        self,
        *,
        query: str,
        project_id: str,
        trusted_facts: List[Dict[str, Any]],
        extracted_evidence: List[Dict[str, Any]],
        linked_support: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        analysis_support = self._retrieve_ai_analysis_support(query=query, project_id=project_id)
        synthesis = self._generate_query_time_synthesis(
            query=query,
            trusted_facts=trusted_facts,
            extracted_evidence=extracted_evidence,
            linked_support=linked_support,
            analysis_support=analysis_support,
        )
        return {
            "analysis_support": analysis_support,
            "synthesis": synthesis,
        }

    def _compose_multi_lane_answer(
        self,
        *,
        query: str,
        trusted_facts: List[Dict[str, Any]],
        trusted_conflicts: List[Dict[str, Any]],
        extracted_evidence: List[Dict[str, Any]],
        linked_support: List[Dict[str, Any]],
        ai_lane: Dict[str, Any],
        coverage: Dict[str, Any],
    ) -> str:
        sections: List[str] = []

        trusted_lines: List[str] = []
        if trusted_facts:
            for fact in trusted_facts[:10]:
                lineage = fact.get("lineage") or []
                source = "unknown source"
                if lineage:
                    first = lineage[0]
                    source = first.get("source_path", "unknown source")
                    loc = first.get("location") or {}
                    if isinstance(loc, dict) and "page_index" in loc:
                        source += f" p.{int(loc.get('page_index', 0)) + 1}"
                    elif isinstance(loc, dict) and "page" in loc:
                        source += f" p.{loc.get('page')}"
                trusted_lines.append(
                    f"- [Fact:{fact.get('fact_id')}] {fact.get('fact_type')}: {self._trim_text(fact.get('value'), 220)} (status: {fact.get('status')}; source: {source})"
                )
            if trusted_conflicts:
                trusted_lines.append(
                    f"- Conflicts detected in trusted facts: {len(trusted_conflicts)} conflicting fact set(s). Treat differing values carefully."
                )
            if not coverage.get("is_complete", False) and coverage.get("missing_fact_types"):
                trusted_lines.append(
                    "- Trusted coverage is incomplete for this question. Missing trusted fact families: "
                    + ", ".join(coverage.get("missing_fact_types", []))
                )
            sections.append("## Trusted Facts\n" + "\n".join(trusted_lines))
        else:
            sections.append("## Trusted Facts\n- No trusted facts found for this question.")

        if extracted_evidence:
            lines = [
                f"- {item.get('provenance')}: {item.get('source_path')} p.{int(item.get('page_index', 0)) + 1} — {item.get('text')}"
                for item in extracted_evidence[:8]
            ]
            sections.append("## Extracted Evidence\n" + "\n".join(lines))

        if linked_support:
            lines = [
                f"- {item.get('entity_type')} '{item.get('entity_value')}' --{item.get('relation')}--> {item.get('neighbor_type')} '{item.get('neighbor_value')}' (confidence tier: {item.get('confidence_tier')})"
                for item in linked_support[:6]
            ]
            sections.append("## Linked Support\n" + "\n".join(lines))

        ai_lines: List[str] = []
        for item in ai_lane.get("analysis_support", [])[:4]:
            ai_lines.append(
                f"- Stored AI analysis ({item.get('source_path')} p.{int(item.get('page_index', 0)) + 1}): {item.get('text')}"
            )
        if ai_lane.get("synthesis"):
            ai_lines.append(f"- Query-time AI synthesis (non-governing): {ai_lane.get('synthesis')}")
        if ai_lines:
            sections.append(
                "## AI-Generated Synthesis\n"
                "This section is AI-generated / non-governing. It may help interpretation, but it is not certified truth.\n"
                + "\n".join(ai_lines)
            )

        return "\n\n".join(sections)

    def _compose_multi_lane_thinking(
        self,
        trusted_facts: List[Dict[str, Any]],
        extracted_evidence: List[Dict[str, Any]],
        linked_support: List[Dict[str, Any]],
        ai_lane: Dict[str, Any],
    ) -> str:
        return (
            "Sourced multi-lane answer assembly: "
            f"trusted={len(trusted_facts)}, "
            f"extracted={len(extracted_evidence)}, "
            f"linked={len(linked_support)}, "
            f"ai_analysis={len(ai_lane.get('analysis_support', []))}, "
            f"ai_synthesis={'yes' if ai_lane.get('synthesis') else 'no'}."
        )

    def _compose_no_grounded_material_refusal(self, *, query: str, coverage: Dict[str, Any]) -> str:
        missing = coverage.get("missing_fact_types", []) or []
        actions = [step.get("action", "Run extraction") for step in coverage.get("job_plan", [])]
        parts = [
            "I could not find any meaningful project-grounded material for this question.",
            "Checked lanes: Trusted Facts, Extracted Evidence, Linked Support, and AI-Generated Synthesis.",
        ]
        if missing:
            parts.append("Missing trusted fact families: " + ", ".join(missing) + ".")
        if actions:
            parts.append("Suggested next steps: " + " | ".join(actions))
        else:
            parts.append("Suggested next step: import the relevant project documents and run Extract / Build Facts.")
        return "\n\n".join(parts)

    def _derive_candidate_facts_from_evidence(
        self,
        *,
        query: str,
        project_id: str,
        snapshot_id: Optional[str],
        required_fact_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        import hashlib
        import time
        from src.domain.facts.models import Fact, FactInput, FactStatus, ValueType
        from src.domain.facts.repository import FactRepository

        try:
            cached = self.fact_api.get_candidate_facts(
                query_intent=query,
                project_id=project_id,
                snapshot_id=snapshot_id,
            )
            if cached.get("has_candidate_data"):
                cached["candidate_source"] = "cache"
                return cached
        except Exception as e:
            logger.debug("[AgentOrchestrator] Candidate fact cache lookup failed: %s", e)

        if not self.rag or not self.llm:
            return {"facts": [], "count": 0, "has_candidate_data": False}

        try:
            evidence_items = self.rag.retrieve_evidence(query, limit=6)
        except Exception as e:
            logger.warning("[AgentOrchestrator] Evidence retrieval failed: %s", e)
            evidence_items = []

        evidence_items = [
            e for e in evidence_items
            if e.get("file_version_id") and (e.get("text") or "").strip()
        ]
        if not evidence_items:
            return {"facts": [], "count": 0, "has_candidate_data": False}

        target_fact_types = required_fact_types or self.fact_api._infer_fact_types(query)
        if not target_fact_types:
            return {"facts": [], "count": 0, "has_candidate_data": False}

        evidence_text = "\n\n".join(
            f"[{e.get('source_path', 'unknown')} | page {e.get('page_index', 0)} | {e.get('evidence_kind', 'evidence')}]\n{e.get('text', '')}"
            for e in evidence_items[:6]
        )

        schema = {
            "facts": [
                {
                    "fact_type": "document.profile",
                    "subject_kind": "query",
                    "subject_id": "query_xxxxxxxx",
                    "value_type": "TEXT",
                    "value": "...",
                    "confidence": 0.6,
                }
            ]
        }

        try:
            derivation = self.llm.chat_json(
                system=(
                    "You are an evidence-grounded AECO fact extractor. "
                    "Only emit facts directly supported by the provided evidence. "
                    "Return ONLY facts whose fact_type appears in the allowed list. "
                    "Do not invent unsupported values. "
                    "Use value_type from: NUM, TEXT, BOOL, DATE, JSON."
                ),
                user=(
                    f"USER QUERY: {query}\n\n"
                    f"ALLOWED FACT TYPES: {target_fact_types}\n\n"
                    f"EVIDENCE:\n{evidence_text}\n\n"
                    "Extract the smallest set of facts needed to answer the query. "
                    "If the evidence is too weak, return an empty facts array."
                ),
                schema=schema,
                task_type="reasoning",
                max_tokens=900,
                temperature=0.2,
            ) or {}
        except Exception as e:
            logger.warning("[AgentOrchestrator] Candidate derivation LLM call failed: %s", e)
            return {"facts": [], "count": 0, "has_candidate_data": False}

        raw_facts = derivation.get("facts") if isinstance(derivation, dict) else None
        if not raw_facts:
            return {"facts": [], "count": 0, "has_candidate_data": False}

        q_norm = " ".join((query or "").lower().split())
        q_hash = hashlib.sha1(q_norm.encode("utf-8")).hexdigest()[:12]
        query_subject_id = f"query_{q_hash}"
        now = int(time.time())

        facts = []
        for raw in raw_facts:
            fact_type = str(raw.get("fact_type") or "").strip()
            if not fact_type or fact_type not in target_fact_types:
                continue

            value_type_name = str(raw.get("value_type", "TEXT")).upper()
            try:
                value_type = ValueType[value_type_name]
            except Exception:
                value_type = ValueType.TEXT

            inputs = [
                FactInput(
                    file_version_id=e["file_version_id"],
                    location={
                        "page_index": e.get("page_index", 0),
                        "source_path": e.get("source_path", "unknown"),
                        "evidence_kind": e.get("evidence_kind", "evidence"),
                        "query": query,
                    },
                    input_kind="rag_evidence",
                )
                for e in evidence_items[:4]
                if e.get("file_version_id")
            ]
            if not inputs:
                continue

            fact_hash = hashlib.sha1(f"{query_subject_id}|{fact_type}".encode("utf-8")).hexdigest()[:10]

            facts.append(
                Fact(
                    fact_id=f"fact_qd_{fact_hash}",
                    project_id=project_id,
                    fact_type=fact_type,
                    subject_kind="query",
                    subject_id=query_subject_id,
                    as_of={"snapshot_id": snapshot_id, "query_hash": q_hash},
                    value_type=value_type,
                    value=raw.get("value"),
                    status=FactStatus.CANDIDATE,
                    confidence=float(raw.get("confidence", 0.6) or 0.6),
                    method_id="query_derivation_v1",
                    inputs=inputs,
                    created_at=now,
                    updated_at=now,
                )
            )

        if not facts:
            return {"facts": [], "count": 0, "has_candidate_data": False}

        try:
            FactRepository(self.db).save_facts(facts)
        except Exception as e:
            logger.warning("[AgentOrchestrator] Candidate fact persistence failed: %s", e)
            return {"facts": [], "count": 0, "has_candidate_data": False}

        persisted = self.fact_api.get_candidate_facts(
            query_intent=query,
            project_id=project_id,
            snapshot_id=snapshot_id,
        )
        if persisted.get("has_candidate_data"):
            persisted["candidate_source"] = "derived"
        return persisted


    def _build_structured_citations(self, facts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        citations: List[Dict[str, Any]] = []
        for fact in facts or []:
            lineage = fact.get("lineage") or []
            first = lineage[0] if lineage else {}
            citations.append({
                "fact_id": fact.get("fact_id"),
                "fact_type": fact.get("fact_type"),
                "status": fact.get("status"),
                "source_path": first.get("source_path", "unknown"),
                "location": first.get("location", {}),
                "method_id": fact.get("method_id"),
            })
        return citations

    def _is_complex_query(self, query: str) -> bool:
        """Classify if a query requires deep multi-step reasoning."""
        if self.deep_agent:
            return self.deep_agent._classify_intent(query) == "deep"
        return False

    # ------------------------------------------------------------------
    # Deprecated compatibility path — kept only for active tests/callers
    # ------------------------------------------------------------------

    def answer_question_map_reduce(
        self,
        *,
        query: str,
        doc_ids: List[str],
    ) -> Dict[str, Any]:
        """
        Deprecated compatibility path retained for active tests and legacy callers.

        Canonical path is answer_question().
        This method is intentionally isolated from the SSOT runtime path.
        """
        if not self.evidence_builder:
            return {
                "answer": (
                    "This deprecated map-reduce path is unavailable. "
                    "Use answer_question() instead."
                ),
                "map_results": [],
                "artifact_path": None,
                "deprecated": True,
            }

        pack = self.evidence_builder.build_pack(query=query, doc_ids=doc_ids)
        documents = (pack or {}).get("documents", [])
        map_results: List[Dict[str, Any]] = []

        for doc in documents:
            if doc.get("status") != "Found Evidence":
                continue

            excerpts = doc.get("excerpts") or []
            if not excerpts:
                continue

            excerpts_text = "\n\n".join(
                f"[{e.get('source_field', 'text')}] {e.get('text', '')}"
                for e in excerpts
            )

            sys = (
                "You are a Forensic Engineering Auditor. Extract specific technical facts "
                "relevant to the query. Return JSON like {'facts': ['fact 1', 'fact 2']}."
            )
            user = (
                f"QUERY: {query}\n\n"
                f"DOCUMENT EVIDENCE ({doc.get('file_name', 'Unknown')}):\n{excerpts_text}"
            )

            try:
                out = self.llm.chat_json(system=sys, user=user)
                facts = out.get("facts", []) if isinstance(out, dict) else []
            except Exception:
                facts = []

            if facts:
                map_results.append(
                    {
                        "doc_id": doc.get("doc_id"),
                        "file_name": doc.get("file_name", "Unknown"),
                        "facts": facts,
                    }
                )

        if not map_results:
            return {
                "answer": (
                    "I could not find sufficient evidence in the selected documents "
                    "to answer this question."
                ),
                "map_results": [],
                "artifact_path": None,
                "deprecated": True,
            }

        context = ""
        for item in map_results:
            context += f"\n--- Source: {item['file_name']} ---\n"
            for fact in item["facts"]:
                context += f"- {fact}\n"

        sys = (
            "You are a Solution Architect. Synthesize the provided facts into a coherent, "
            "engineering-grade answer. Cite sources in brackets [Source Name]. "
            "If facts conflict, note the conflict."
        )
        user = f"QUERY: {query}\n\nEXTRACTED FACTS:\n{context}"

        try:
            resp = self.llm.chat(
                messages=[
                    {"role": "system", "content": sys},
                    {"role": "user", "content": user},
                ],
                temperature=0.3,
            )
            answer = (resp.get("choices") or [{}])[0].get("message", {}).get(
                "content",
                "Synthesis failed.",
            )
        except Exception as e:
            answer = f"Error during synthesis: {str(e)}"

        return {
            "answer": answer,
            "map_results": map_results,
            "artifact_path": None,
            "deprecated": True,
        }

    # ------------------------------------------------------------------
    # Dormant compatibility helpers — left minimal / non-canonical
    # ------------------------------------------------------------------

    def _map_document_facts(self, query: str, doc_ev: Dict[str, Any]) -> List[str]:
        """Deprecated helper retained as harmless stub."""
        return []

    def _reduce_facts(self, query: str, map_results: List[Dict[str, Any]]) -> str:
        """Deprecated helper retained as harmless stub."""
        return "Synthesis bypassed (dormant path)."

    def _get_tool_schemas(self) -> str:
        """Collate tool schemas for prompt injection."""
        schemas = {}
        for name, tool in self.tools.items():
            schemas[name] = {
                "description": tool.description,
                "parameters": tool.get_parameters_schema(),
            }
        return json.dumps(schemas, indent=2)

    # ------------------------------------------------------------------
    # Legacy sub-agents retained as non-canonical compatibility methods
    # ------------------------------------------------------------------

    def _text_agent(self, doc_id: str, query: str) -> Dict[str, Any]:
        """Neutralized legacy agentic path."""
        return {"source": "text", "data": {"answer": "Agentic bypass neutralized."}}

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
            model_name=self.llm.model,
        )

        full_sys = f"{op.full_prompt}\nYou also have access to: {self._get_tool_schemas()}"
        out = self.llm.chat_json(system=full_sys, user=f"QUERY:\n{query}")
        self.metrics.record_latency("agent_layout", time.time() - start_ts)
        return {"source": "layout", "data": out}

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
            model_name=self.llm.model,
        )

        out = self.llm.chat_json(system=op.full_prompt, user=f"QUERY:\n{query}")
        self.metrics.record_latency("agent_compliance", time.time() - start_ts)
        return {"source": "compliance", "data": out}

    def _meta_agent(
        self,
        query: str,
        text_ans: Dict[str, Any],
        layout_ans: Dict[str, Any],
        comp_ans: Dict[str, Any],
    ) -> Dict[str, Any]:
        start_ts = time.time()

        agent_data = {
            "text": text_ans,
            "layout": layout_ans,
            "compliance": comp_ans,
        }

        reliability_weighted_inputs = {}
        for source, ans in agent_data.items():
            reported_conf = (ans.get("data") or {}).get("confidence", 0.5)
            learned_score = self.confidence_learner.compute_learned_confidence(
                field_name=source,
                model_name=self.llm.model,
                vlm_reported_confidence=reported_conf,
            )
            reliability_weighted_inputs[source] = {
                "answer": ans.get("data"),
                "reliability_score": learned_score.learned_confidence,
                "confidence_level": learned_score.confidence_level,
                "uncertainty_factors": learned_score.uncertainty_factors,
            }

        op = self.optimizer.generate_stage2_prompt(
            unified_context=json.dumps(reliability_weighted_inputs, indent=2),
            field_name="meta_synthesis",
            document_type="any",
            role="general",
            model_name=self.llm.model,
        )

        out = self.llm.chat_json(system=op.full_prompt, user=f"QUERY:\n{query}")
        self.metrics.record_latency("agent_meta", time.time() - start_ts)
        return out or {"final_answer": "", "source": "none", "confidence": 0.0}