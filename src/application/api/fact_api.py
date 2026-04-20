# -*- coding: utf-8 -*-
"""
fact_api.py — Whitelisted Fact Query Interface (SSOT §5, §7)

SSOT Required Behavior:
  "The LLM is a query planner + narrator. It must never answer from raw files,
   embeddings, or unstaged text. It may only retrieve information via a
   whitelisted fact query interface over Certified Facts and VALIDATED links."

All retrieval for LLM consumption MUST go through this class.
No direct DB queries or vector store calls are permitted in the orchestrator.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from src.engine.validation.rule_runner import RuleRunner
from src.compliance.standard_enricher import StandardEnricher
from src.domain.facts.models import Fact, FactStatus, TRUSTED_FACT_STATUSES, TRUSTED_FACT_STATUSES_SQL, AI_GENERATED_PROVENANCE

logger = logging.getLogger(__name__)

class FactQueryAPI:
    """
    The STRICT whitelisted interface for LLM fact retrieval.

    SSOT Contract:
    - Only returns VALIDATED or HUMAN_CERTIFIED facts.
    - Always includes lineage (fact_id → file_version → page/cell).
    - Detects and surfaces conflicts between certified facts.
    - LLM is NEVER given raw document text via this interface.
    """

    CERTIFIED_STATUSES = TRUSTED_FACT_STATUSES

    def __init__(self, db):
        self.db = db
        self.rule_runner = RuleRunner(db)
        self.standard_enricher = StandardEnricher()

    # -----------------------------------------------------------------------
    # Primary entry point — used by AgentOrchestrator
    # -----------------------------------------------------------------------

    def get_certified_facts(
        self,
        query_intent: str,
        project_id: str,
        snapshot_id: Optional[str] = None,
        fact_types: Optional[List[str]] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """
        Retrieve certified facts for LLM consumption.

        Returns:
            {
                "facts": [
                    {
                        "fact_id": str,
                        "fact_type": str,
                        "subject_id": str,
                        "value": <parsed>,
                        "status": "VALIDATED"|"HUMAN_CERTIFIED",
                        "method_id": str,
                        "as_of": {...},
                        "lineage": [{"file_version_id", "source_path", "location"}]
                    },
                    ...
                ],
                "count": int,
                "has_certified_data": bool,
                "conflicts": [{...}],          # if any conflicting facts found
                "formatted_context": str,      # ready-to-inject LLM context string
            }
        """
        # Resolve which fact_types to query
        if not fact_types:
            fact_types = self._infer_fact_types(query_intent)

        all_facts = []
        for ft in fact_types:
            rows = self._query_certified(ft, project_id, snapshot_id, limit)
            all_facts.extend(rows)

        # Detect conflicts
        conflicts = self._detect_conflicts(all_facts)

        # Build rich fact records with lineage
        enriched = [self._enrich_with_lineage(f) for f in all_facts]

        # Deterministic rule fortification
        violations = self._validate_with_rules(enriched)

        # Compliance Standards Enrichment
        standards = self._enrich_with_standards(all_facts)

        return {
            "facts": enriched,
            "count": len(enriched),
            "has_certified_data": len(enriched) > 0,
            "conflicts": conflicts,
            "rule_violations": violations,
            "relevant_standards": standards,
            "formatted_context": self._format_for_llm(enriched, conflicts, violations, standards),
        }

    # -----------------------------------------------------------------------
    # Individual query methods (also public for direct use)
    # -----------------------------------------------------------------------

    def fact_get(self, fact_type: str, subject_id: str) -> Dict[str, Any]:
        """Get a single certified fact bundle by type and subject."""
        rows = self._query_certified_raw(
            f"SELECT * FROM facts WHERE fact_type=? AND subject_id=? "
            f"AND status IN ({TRUSTED_FACT_STATUSES_SQL}) "
            "ORDER BY created_at DESC LIMIT 1",
            (fact_type, subject_id),
        )
        enriched = [self._enrich_with_lineage(r) for r in rows]
        return {"facts": enriched, "count": len(enriched)}

    def fact_list(
        self,
        fact_type: str,
        project_id: Optional[str] = None,
        snapshot_id: Optional[str] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """List all certified facts of a type for a project."""
        rows = self._query_certified(fact_type, project_id, snapshot_id, limit)
        enriched = [self._enrich_with_lineage(r) for r in rows]
        return {
            "facts": enriched,
            "count": len(enriched),
            "formatted_context": self._format_for_llm(enriched, []),
        }

    def coverage_check(
        self,
        requirements: List[str],
        subject_ids: List[str],
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Check if we have required certified facts for a set of subjects.
        Returns missing coverage to allow LLM to enforce REFUSE logic.
        """
        missing: Dict[str, List[str]] = {}
        for subj in subject_ids:
            for req_type in requirements:
                sql = (
                    f"SELECT 1 FROM facts WHERE fact_type=? AND subject_id=? "
                    f"AND status IN ({TRUSTED_FACT_STATUSES_SQL})"
                )
                params: tuple = (req_type, subj)
                if project_id:
                    sql += " AND project_id=?"
                    params += (project_id,)
                sql += " LIMIT 1"

                exists = self.db.execute(sql, params).fetchone()
                if not exists:
                    missing.setdefault(subj, []).append(req_type)

        return {
            "is_complete": len(missing) == 0,
            "missing": missing,
        }

    def detect_conflicts(
        self, fact_type: str, subject_ids: List[str], project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Detect conflicting certified facts for the same subject.
        Conflict = multiple VALIDATED facts for same subject with different values.
        
        Now enriches with standard clauses for the fact type.
        """
        conflicts = []
        for subj in subject_ids:
            sql = (
                "SELECT fact_id, value_json, method_id, status, created_at "
                "FROM facts WHERE fact_type=? AND subject_id=? "
                f"AND status IN ({TRUSTED_FACT_STATUSES_SQL})"
            )
            params: tuple = (fact_type, subj)
            if project_id:
                sql += " AND project_id=?"
                params += (project_id,)

            rows = self.db.execute(sql, params).fetchall()
            if len(rows) > 1:
                values = [r[1] for r in rows]
                if len(set(values)) > 1:  # Different values → conflict
                    conflicts.append({
                        "fact_type": fact_type,
                        "subject_id": subj,
                        "conflicting_facts": [
                            {
                                "fact_id": r[0],
                                "value": r[1],
                                "method_id": r[2],
                                "status": r[3],
                                "created_at": r[4],
                            }
                            for r in rows
                        ],
                    })
        
        # Cross-reference with compliance module (new fortification)
        standards = []
        try:
            standards = self.standard_enricher.lookup_clauses_by_concept(fact_type)
        except Exception as e:
            logger.debug(f"[FactQueryAPI] Standards lookup failed in detect_conflicts: {e}")

        return {
            "conflicts": conflicts,
            "relevant_standards": standards
        }

    def get_candidate_facts(
        self,
        query_intent: str,
        project_id: Optional[str] = None,
        snapshot_id: Optional[str] = None,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """Retrieve cached query-derived candidate facts for the normalized query."""
        import hashlib

        q = " ".join((query_intent or "").lower().split())
        if not q or not project_id:
            return {
                "facts": [],
                "count": 0,
                "has_candidate_data": False,
                "formatted_context": "",
                "governs_answers": False,
                "supporting_only": True,
                "provenance_class": AI_GENERATED_PROVENANCE,
                "requires_trust_promotion": True,
            }

        subject_id = f"query_{hashlib.sha1(q.encode('utf-8')).hexdigest()[:12]}"
        fact_types = self._infer_fact_types(query_intent)

        all_facts: List[Dict[str, Any]] = []
        for fact_type in fact_types:
            try:
                rows = self.db.execute(
                    """
                    SELECT * FROM facts
                    WHERE fact_type = ?
                      AND project_id = ?
                      AND status = 'CANDIDATE'
                      AND subject_kind = 'query'
                      AND subject_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (fact_type, project_id, subject_id, limit),
                ).fetchall()
                all_facts.extend(dict(r) for r in rows)
            except Exception as e:
                logger.debug("[FactQueryAPI] Candidate fact query failed for %s: %s", fact_type, e)

        deduped: List[Dict[str, Any]] = []
        seen = set()
        for fact in all_facts:
            fid = fact.get("fact_id")
            if fid in seen:
                continue
            seen.add(fid)
            deduped.append(fact)

        enriched = [self._enrich_with_lineage(f) for f in deduped]

        for fact in enriched:
            fact.setdefault("governs_answers", False)
            fact.setdefault("supporting_only", True)
            fact.setdefault("provenance_class", AI_GENERATED_PROVENANCE)
            fact.setdefault("requires_trust_promotion", True)

        return {
            "facts": enriched,
            "count": len(enriched),
            "has_candidate_data": len(enriched) > 0,
            "formatted_context": self._format_candidate_for_llm(enriched),
            "governs_answers": False,
            "supporting_only": True,
            "provenance_class": AI_GENERATED_PROVENANCE,
            "requires_trust_promotion": True,
        }

    def _format_candidate_for_llm(self, facts: List[Dict[str, Any]]) -> str:
        """Format candidate facts with explicit lower-trust framing for narration."""
        import json

        if not facts:
            return ""

        lines = ["[AI-GENERATED CANDIDATE SUPPORT - NOT ANSWER-GOVERNING]"]
        for fact in facts:
            value = fact.get("value")
            if isinstance(value, (dict, list)):
                value_str = json.dumps(value, ensure_ascii=False)
            else:
                value_str = str(value)

            lines.append(f"- {fact.get('fact_type')}: {value_str}")

            lineage = fact.get("lineage") or []
            if lineage:
                first = lineage[0]
                lines.append(
                    f"  source: {first.get('source_path', 'unknown')} | "
                    f"location: {json.dumps(first.get('location', {}), ensure_ascii=False)}"
                )

        return "\n".join(lines)

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

    def _infer_fact_types(self, query_intent: str) -> List[str]:
        """Map a query intent string to relevant fact types."""
        q = " ".join((query_intent or "").lower().split())

        _DOC_PHRASES = [
            "summarize this document",
            "summarize document",
            "page count",
            "has text",
            "document profile",
            "how many pages",
            "about this file",
            "about this document",
            "what is this document",
            "what is this file",
            "what is this pdf",
            "tell me about this document",
            "tell me about this file",
            "metadata",
            "file info",
            "document analysis",
            "analyze this document",
            "pdf properties",
            "is this scanned",
            "does it have ocr",
        ]
        _BROAD_DOCUMENT_SUMMARY_PHRASES = [
            "provide project scope summary",
            "summarize project scope",
            "project scope summary",
            "scope summary",
            "scope of work summary",
            "summarize scope of work",
            "project summary of scope",
            "summarize scope",
            "project scope",
            "scope",
        ]
        _NON_DOCUMENT_DOMAIN_CUES = [
            "schedule", "delay", "milestone", "cost", "budget", "boq",
            "bim", "drawing", "element", "compliance", "standard",
            "register", "submittal", "rfi",
        ]

        is_broad_document_summary = any(phrase in q for phrase in _BROAD_DOCUMENT_SUMMARY_PHRASES)
        if not is_broad_document_summary:
            has_scope = any(token in q for token in ["scope", "scope of work"])
            has_summary = any(token in q for token in ["summary", "summarize", "overview"])
            if has_scope and has_summary and not any(token in q for token in _NON_DOCUMENT_DOMAIN_CUES):
                is_broad_document_summary = True

        is_document_query = any(phrase in q for phrase in _DOC_PHRASES)
        if not is_document_query and (("document" in q) or ("pdf" in q) or ("file" in q)):
            if any(token in q for token in ["what is", "about", "summarize", "tell me", "page", "text", "ocr", "scanned"]):
                is_document_query = True

        semantic_doc_cues = ["in scope", "scope includes", "sqm", "square meter", "approved vendor", "detailed design", "shall consider", "generator room"]
        if any(cue in q for cue in semantic_doc_cues):
            is_document_query = True

        if is_broad_document_summary:
            inferred = [
                "document.scope_item",
                "document.requirement",
                "document.includes_component",
                "document.design_obligation",
                "document.vendor_basis",
                "document.area_approx",
                "document.abstract",
                "document.profile",
            ]
            ordered: List[str] = []
            seen: set[str] = set()
            for item in inferred:
                if item not in seen:
                    seen.add(item)
                    ordered.append(item)
            return ordered

        if is_document_query:
            inferred: List[str] = ["document.page_count", "document.has_text", "document.profile"]
            if any(k in q for k in ["summarize", "abstract", "about", "what is"]):
                inferred.append("document.abstract")
            if any(k in q for k in ["scope", "in scope", "inscope"]):
                inferred.append("document.scope_item")
            if any(k in q for k in ["area", "sqm", "square meter", "m2", "m²"]):
                inferred.append("document.area_approx")
            if any(k in q for k in ["include", "includes", "tank", "component"]):
                inferred.append("document.includes_component")
            if any(k in q for k in ["design", "detailed design", "obligation"]):
                inferred.append("document.design_obligation")
            if any(k in q for k in ["vendor", "approved vendor", "as per", "basis"]):
                inferred.append("document.vendor_basis")
            if any(k in q for k in ["shall", "must", "requirement", "required", "consider"]):
                inferred.append("document.requirement")
            ordered: List[str] = []
            seen: set[str] = set()
            for item in inferred:
                if item not in seen:
                    seen.add(item)
                    ordered.append(item)
            return ordered

        intent_map: Dict[str, List[str]] = {
            "schedule": ["schedule.activity", "schedule.milestone"],
            "completion": ["schedule.milestone", "schedule.completion_date"],
            "delay": ["schedule.activity", "schedule.baseline"],
            "cost": ["cost.line_item", "cost.summary"],
            "bim": ["bim.element", "bim.property"],
            "compliance": ["compliance.check", "spec.requirement"],
            "register": ["register.document", "register.revision"],
        }
        for key, types in intent_map.items():
            if key in q:
                return types

        return ["schedule.milestone", "cost.summary", "bim.element", "compliance.check"]

    def _query_certified(
        self,
        fact_type: str,
        project_id: Optional[str],
        snapshot_id: Optional[str],
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Low-level certified fact query via snapshot registry with bounded document fallback."""
        params: List[Any] = [fact_type]
        sql = f"SELECT * FROM facts WHERE fact_type=? AND status IN ({TRUSTED_FACT_STATUSES_SQL})"

        if snapshot_id:
            # 3.2 Strict 4-Layer Chat Gating: prefer snapshot-locked retrieval.
            sql += " AND fact_id IN (SELECT fact_id FROM fact_snapshot_registry WHERE snapshot_id = ?)"
            params.append(snapshot_id)
        elif project_id:
            sql += " AND project_id=?"
            params.append(project_id)

        sql += f" ORDER BY created_at DESC LIMIT {limit}"
        rows = self._query_certified_raw(sql, tuple(params))

        # Document facts on the live runtime path are often persisted with
        # document/file-version scope, while the mounted truth surfaces still
        # display them as trusted project facts. When the snapshot registry is
        # absent or stale for document.* records, fall back to project-scoped
        # trusted retrieval so the answer path stays aligned with the mounted
        # validated fact surfaces.
        if rows or not snapshot_id or not project_id or not str(fact_type).startswith("document."):
            return rows

        fallback_sql = (
            f"SELECT * FROM facts WHERE fact_type=? AND project_id=? "
            f"AND status IN ({TRUSTED_FACT_STATUSES_SQL}) "
            f"ORDER BY created_at DESC LIMIT {limit}"
        )
        fallback_rows = self._query_certified_raw(fallback_sql, (fact_type, project_id))
        if fallback_rows:
            logger.info(
                "[FactQueryAPI] Document fact fallback used for %s (project=%s snapshot=%s)",
                fact_type,
                project_id,
                snapshot_id,
            )
        return fallback_rows

    def _query_certified_raw(self, sql: str, params: tuple) -> List[Dict[str, Any]]:
        try:
            rows = self.db.execute(sql, params).fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"[FactQueryAPI] Query failed: {e}")
            return []

    def _enrich_with_lineage(self, fact: Dict[str, Any]) -> Dict[str, Any]:
        """Attach file lineage to a fact record."""
        fact_id = fact.get("fact_id")
        lineage = []
        if fact_id:
            try:
                rows = self.db.execute(
                    """
                    SELECT fi.file_version_id, fi.location_json, fi.input_kind,
                           fv.source_path
                    FROM fact_inputs fi
                    LEFT JOIN file_versions fv ON fi.file_version_id = fv.file_version_id
                    WHERE fi.fact_id = ?
                    """,
                    (fact_id,),
                ).fetchall()
                lineage = [
                    {
                        "file_version_id": r[0],
                        "location": self._safe_json(r[1]),
                        "input_kind": r[2],
                        "source_path": r[3] or "unknown",
                    }
                    for r in rows
                ]
            except Exception as e:
                logger.debug(f"[FactQueryAPI] Lineage fetch failed for {fact_id}: {e}")

        # Parse value_json for display
        value_raw = fact.get("value_json") or ""
        value = self._safe_json(value_raw) if value_raw else value_raw

        return {
            **fact,
            "value": value,
            "lineage": lineage,
        }

    def _detect_conflicts(self, facts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect conflicts within a set of already-retrieved facts."""
        # Group by (fact_type, subject_id)
        grouped: Dict[Tuple[str, str], List[Dict]] = {}
        for f in facts:
            key = (f.get("fact_type", ""), f.get("subject_id", ""))
            grouped.setdefault(key, []).append(f)

        conflicts = []
        for (ft, subj), group in grouped.items():
            if len(group) > 1:
                values = {f.get("value_json", "") for f in group}
                if len(values) > 1:
                    conflicts.append({
                        "fact_type": ft,
                        "subject_id": subj,
                        "conflicting_facts": group,
                    })

        if conflicts:
            logger.warning(f"[FactQueryAPI] {len(conflicts)} conflict(s) detected in result set")

        return conflicts

    def _format_for_llm(
        self, 
        facts: List[Dict[str, Any]], 
        conflicts: List[Dict[str, Any]], 
        violations: List[Dict[str, Any]] = None,
        standards: List[Dict[str, Any]] = None
    ) -> str:
        """
        Build a structured, LLM-injectable context block from certified facts.
        This is the ONLY way fact data enters the LLM prompt.
        """
        if not facts:
            return "[No certified facts available for this query]"

        parts = ["### TRUSTED FACTS (VALIDATED / HUMAN_CERTIFIED)\n"]
        parts.append(
            "Answer ONLY from these facts. Do not invent or infer data not listed here.\n"
        )

        for f in facts:
            fact_id = f.get("fact_id", "?")
            fact_type = f.get("fact_type", "?")
            subject_id = f.get("subject_id", "?")
            status = f.get("status", "?")
            value = f.get("value", f.get("value_json", "?"))
            method = f.get("method_id", "?")
            lineage = f.get("lineage", [])

            citation = "unknown source"
            if lineage:
                src = lineage[0].get("source_path", "unknown")
                loc = lineage[0].get("location", {})
                citation = f"{src}"
                if isinstance(loc, dict):
                    if "page" in loc:
                        citation += f" p.{loc['page']}"
                    elif "row" in loc:
                        citation += f" row {loc['row']}"
                    elif "activity_id" in loc:
                        citation += f" act:{loc['activity_id']}"

            parts.append(
                f"[Fact {fact_id}] {fact_type} | {subject_id} | {status}\n"
                f"  Value: {value}\n"
                f"  Method: {method} | Source: {citation}\n"
            )

        if conflicts:
            parts.append("\n### ⚠️ CONFLICTS DETECTED — DISCLOSE TO USER\n")
            parts.append(
                "The following facts have CONFLICTING values for the same subject. "
                "You MUST disclose both values and NOT silently choose one.\n"
            )
            for c in conflicts:
                parts.append(
                    f"CONFLICT [{c['fact_type']} / {c['subject_id']}]: "
                    f"{len(c['conflicting_facts'])} contradicting certified facts found."
                )

        if violations:
            parts.append("\n### ⚠️ DETERMINISTIC RULE VIOLATIONS\n")
            parts.append(
                "The following 'Certified' facts failed deterministic verification rules. "
                "Disclose these risks when answering.\n"
            )
            for v in violations:
                parts.append(
                    f"VIOLATION [Fact {v['fact_id']}]: {v['rule_id']} - {v['message']} ({v['severity']})"
                )

        if standards:
            parts.append("\n### 📜 RELEVANT REGULATORY STANDARDS / CODES\n")
            parts.append(
                "The following standards clauses relate to the technical facts above. "
                "Cross-reference these when performing compliance reasoning.\n"
            )
            for s in standards:
                parts.append(
                    f"STANDARD [{s['standard_id']} § {s['path']}]:\n"
                    f"  {s['text'].strip()[:500]}..."
                )

        return "\n".join(parts)

    def _validate_with_rules(self, enriched_facts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Run legacy deterministic rules against the retrieved facts."""
        violations = []
        for f in enriched_facts:
            try:
                fact_obj = Fact(
                    fact_id=f.get("fact_id", ""),
                    project_id=f.get("project_id", ""),
                    fact_type=f.get("fact_type", ""),
                    subject_id=f.get("subject_id", ""),
                    subject_kind=f.get("subject_kind", "unknown"),
                    value=f.get("value"),
                    as_of=f.get("as_of", {}),
                    status=FactStatus(f.get("status", "CANDIDATE"))
                )
                results = self.rule_runner.validate_fact(fact_obj)
                for r in results:
                    if not r.pass_fail:
                        violations.append({
                            "fact_id": f.get("fact_id"),
                            "rule_id": r.rule_id,
                            "message": r.details.get("msg", "Validation failed"),
                            "severity": r.severity
                        })
            except Exception as e:
                logger.error(f"Error validating fact {f.get('fact_id')}: {e}")
        return violations

    def _enrich_with_standards(self, facts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Cross-reference facts with standard clauses via concepts."""
        if not facts:
            return []
            
        # Extract unique fact types as concepts
        concepts = set(f.get("fact_type", "") for f in facts)
        
        all_clauses = []
        for concept in concepts:
            if not concept: continue
            try:
                # Use StandardEnricher for deterministic lookup
                clauses = self.standard_enricher.lookup_clauses_by_concept(concept)
                all_clauses.extend(clauses)
            except Exception as e:
                logger.debug(f"[FactQueryAPI] Standards lookup failed for {concept}: {e}")
        
        # Deduplicate clauses by ID
        unique_clauses = {}
        for c in all_clauses:
            unique_clauses[c["id"]] = c
            
        return list(unique_clauses.values())

    @staticmethod
    def _safe_json(value: Any) -> Any:
        """Safely parse JSON, returning the original string on failure."""
        if isinstance(value, str):
            try:
                return json.loads(value)
            except Exception:
                return value
        return value
