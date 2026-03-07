# -*- coding: utf-8 -*-
"""
coverage_gate.py — Pre-LLM Coverage Enforcement (SSOT §7)

SSOT Required Behavior:
  "If required facts/links are missing, the assistant MUST refuse and return
   (a) the coverage gap and (b) a job plan to close it."

This gate runs BEFORE the LLM is ever called. It:
  1. Identifies which fact_types are required to answer the query (intent mapping)
  2. Checks the fact layer for coverage in the current snapshot
  3. Returns is_complete=True → proceed to LLM
     Returns is_complete=False → structured refusal with gap + job plan
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Intent → Required Fact Types mapping
# ---------------------------------------------------------------------------

_INTENT_FACT_REQUIREMENTS: Dict[str, List[str]] = {
    # Schedule / programme queries
    "schedule":     ["schedule.activity", "schedule.milestone", "schedule.baseline"],
    "completion":   ["schedule.milestone", "schedule.completion_date"],
    "delay":        ["schedule.activity", "schedule.baseline", "schedule.actual"],
    "milestone":    ["schedule.milestone"],
    "duration":     ["schedule.activity"],

    # Cost / BOQ
    "cost":         ["cost.line_item", "cost.summary"],
    "budget":       ["cost.summary", "cost.approved_budget"],
    "boq":          ["cost.line_item"],
    "quantity":     ["cost.line_item"],

    # BIM / drawings
    "bim":          ["bim.element", "bim.property"],
    "drawing":      ["bim.element"],
    "element":      ["bim.element", "bim.property"],
    "clash":        ["bim.clash"],

    # Compliance / specs
    "compliance":   ["compliance.check", "spec.requirement"],
    "specification":["spec.requirement"],
    "standard":     ["spec.requirement", "compliance.check"],

    # Register / document
    "register":     ["register.document", "register.revision"],
    "submittal":    ["register.submittal"],
    "rfi":          ["register.rfi"],
}

# SSOT §5 - these fact types can rely on less strict coverage (vector discovery OK)
_DISCOVERY_ONLY_TYPES = {"bim.element", "register.document"}


def _classify_query_intents(query: str) -> List[str]:
    """Extract intent keywords from the query text."""
    q = query.lower()
    matched = []
    for intent_key in _INTENT_FACT_REQUIREMENTS:
        if intent_key in q:
            matched.append(intent_key)
    return matched or ["general"]


# ---------------------------------------------------------------------------
# Coverage Gate
# ---------------------------------------------------------------------------

class CoverageGate:
    """
    Pre-LLM enforcement layer.
    
    Usage:
        gate = CoverageGate(db)
        result = gate.check(query, project_id, snapshot_id)
        if not result["is_complete"]:
            return result["refusal_message"]
    """

    def __init__(self, db):
        self.db = db

    def check(
        self,
        query: str,
        project_id: str,
        snapshot_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Check if the fact layer has sufficient certified data to answer this query.

        Returns:
            {
                "is_complete": bool,
                "intents": [...],                  # detected query intents
                "required_fact_types": [...],      # what we need
                "missing_fact_types": [...],       # what we're missing
                "has_any_facts": bool,             # whether ANY certified facts exist
                "refusal_message": str | None,     # user-facing refusal (if incomplete)
                "job_plan": [...],                 # suggested jobs to close the gap
            }
        """
        intents = _classify_query_intents(query)

        # For "general" intent with no specific requirements, always pass through.
        # The FactQueryAPI will return an empty certified block, and the LLM will
        # respond with "No certified facts available..." per the SSOT §7 prompt contract.
        # We do NOT refuse here — refusal is only valid when we CAN identify what's
        # missing but it's not there. For unclassified queries, we cannot know what's missing.
        if intents == ["general"]:
            has_any = self._has_any_certified_facts(project_id, snapshot_id)
            if not has_any:
                logger.info(f"[CoverageGate] Refusing general query for project {project_id} - no certified facts found.")
                return self._incomplete(
                    intents=intents,
                    required=["any.certified_fact"],
                    missing=["any.certified_fact"],
                    no_facts_at_all=True,
                    project_id=project_id,
                )
            return self._complete(intents, [], [])

        # Resolve required fact types for detected intents
        required_types: List[str] = []
        for intent in intents:
            for ft in _INTENT_FACT_REQUIREMENTS.get(intent, []):
                if ft not in required_types:
                    required_types.append(ft)

        # Check coverage for each required type
        missing_types: List[str] = []
        for ft in required_types:
            if not self._fact_type_has_coverage(ft, project_id, snapshot_id):
                missing_types.append(ft)

        if not missing_types:
            return self._complete(intents, required_types, [])

        return self._incomplete(
            intents=intents,
            required=required_types,
            missing=missing_types,
            no_facts_at_all=False,
            project_id=project_id,
        )

    # -----------------------------------------------------------------------
    # DB helpers
    # -----------------------------------------------------------------------

    def _fact_type_has_coverage(
        self,
        fact_type: str,
        project_id: str,
        snapshot_id: Optional[str],
    ) -> bool:
        """Check if at least one VALIDATED or HUMAN_CERTIFIED fact of this type exists."""
        try:
            sql = (
                "SELECT 1 FROM facts "
                "WHERE fact_type = ? AND project_id = ? "
                "AND status IN ('VALIDATED', 'HUMAN_CERTIFIED') "
                "LIMIT 1"
            )
            params: List[Any] = [fact_type, project_id]

            if snapshot_id:
                sql = sql.replace(
                    "LIMIT 1",
                    "AND (as_of_json LIKE ? OR as_of_json IS NULL) LIMIT 1",
                )
                params.append(f"%{snapshot_id}%")

            row = self.db.execute(sql, tuple(params)).fetchone()
            return row is not None
        except Exception as e:
            logger.debug(f"[CoverageGate] fact_type check failed for {fact_type}: {e}")
            return False

    def _has_any_certified_facts(
        self, project_id: str, snapshot_id: Optional[str]
    ) -> bool:
        """True if ANY certified fact exists for this project."""
        try:
            row = self.db.execute(
                "SELECT 1 FROM facts WHERE project_id = ? "
                "AND status IN ('VALIDATED', 'HUMAN_CERTIFIED') LIMIT 1",
                (project_id,),
            ).fetchone()
            return row is not None
        except Exception as e:
            logger.debug(f"[CoverageGate] has_any_certified_facts failed: {e}")
            return False

    # -----------------------------------------------------------------------
    # Result builders
    # -----------------------------------------------------------------------

    def _complete(
        self,
        intents: List[str],
        required: List[str],
        missing: List[str],
    ) -> Dict[str, Any]:
        return {
            "is_complete": True,
            "intents": intents,
            "required_fact_types": required,
            "missing_fact_types": [],
            "has_any_facts": True,
            "refusal_message": None,
            "job_plan": [],
        }

    def _incomplete(
        self,
        intents: List[str],
        required: List[str],
        missing: List[str],
        no_facts_at_all: bool,
        project_id: str,
    ) -> Dict[str, Any]:
        job_plan = self._propose_job_plan(missing, no_facts_at_all)
        refusal = self._compose_refusal(intents, missing, job_plan, no_facts_at_all)

        return {
            "is_complete": False,
            "intents": intents,
            "required_fact_types": required,
            "missing_fact_types": missing,
            "has_any_facts": not no_facts_at_all,
            "refusal_message": refusal,
            "job_plan": job_plan,
        }

    def _propose_job_plan(
        self, missing_types: List[str], no_facts_at_all: bool
    ) -> List[Dict[str, str]]:
        """Map missing fact types to the jobs needed to produce them."""
        _FACT_TO_JOB: Dict[str, Dict[str, str]] = {
            "schedule":     {"job": "BUILD_FACTS", "builder": "schedule",  "action": "Import a P6 .xer or .xml file then run Build Facts → Schedule"},
            "cost":         {"job": "BUILD_FACTS", "builder": "register",  "action": "Import a BOQ Excel file then run Build Facts → Register"},
            "bim":          {"job": "BUILD_FACTS", "builder": "bim",       "action": "Import an IFC file then run Build Facts → BIM"},
            "compliance":   {"job": "BUILD_FACTS", "builder": "schedule",  "action": "Run compliance analysis on the relevant spec documents"},
            "spec":         {"job": "EXTRACT",     "builder": None,        "action": "Import specification PDF and run Extract"},
            "register":     {"job": "BUILD_FACTS", "builder": "register",  "action": "Import a document register spreadsheet then run Build Facts → Register"},
        }

        if no_facts_at_all:
            return [
                {
                    "job": "INGEST + EXTRACT + BUILD_FACTS",
                    "action": "No certified facts exist for this project. Import project documents and run the full pipeline: Ingest → Extract → Build Facts.",
                }
            ]

        plan = []
        seen_jobs = set()
        for ft in missing_types:
            prefix = ft.split(".")[0]
            job_info = _FACT_TO_JOB.get(prefix, {
                "job": "BUILD_FACTS",
                "builder": "unknown",
                "action": f"Import documents containing '{prefix}' data and run Build Facts.",
            })
            key = job_info["job"]
            if key not in seen_jobs:
                seen_jobs.add(key)
                plan.append(job_info)

        return plan

    def _compose_refusal(
        self,
        intents: List[str],
        missing: List[str],
        job_plan: List[Dict],
        no_facts_at_all: bool,
    ) -> str:
        parts = ["⚠️ **Coverage Gap — Cannot Answer**\n"]

        if no_facts_at_all:
            parts.append(
                "No certified facts have been built for this project. "
                "The assistant can only answer from verified data extracted from your documents.\n"
            )
        else:
            parts.append(
                f"The query requires **{', '.join(missing)}** facts, "
                "but none with `VALIDATED` or `HUMAN_CERTIFIED` status were found in the current snapshot.\n"
            )

        if job_plan:
            parts.append("\n**To close this gap, run:**")
            for i, step in enumerate(job_plan, 1):
                parts.append(f"{i}. {step['action']}")

        parts.append(
            "\nOnce the required facts are certified, re-ask your question and the system will answer from verified data."
        )

        return "\n".join(parts)
