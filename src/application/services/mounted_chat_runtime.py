from __future__ import annotations

from typing import Any, Dict

from src.application.services.cad_chat_service import (
    answer_cad_question,
    is_cad_intent,
)


def run_mounted_chat_query(controller: Any, query: str) -> Dict[str, Any]:
    """
    Canonical mounted Expert Chat runtime path.

    Rules:
    - uses the active project only
    - ignores informational imported-date selectors / snapshot widgets
    - calls the orchestrator's sourced multi-lane answer path directly
    - routes CAD-shaped questions (layers / annotations / blocks /
      dimensions / entity counts on a layer) to a deterministic
      project-scoped CAD answer service
    - returns the orchestrator result unchanged apart from a minimal shape fallback
    """
    project_id = getattr(controller, "active_project_id", None)
    db = getattr(controller, "db", None)

    # ── CAD intent shortcut (Iter-4 desktop wiring) ─────────────────
    # CAD questions are answered deterministically from project
    # `cad_*` tables; we never invent structural facts in the LLM.
    if is_cad_intent(query) and project_id and db is not None:
        result = answer_cad_question(db, project_id, query)
        if isinstance(result, dict) and result.get("answer"):
            return result

    orchestrator = getattr(controller, "orchestrator", None)
    if not orchestrator:
        return {
            "answer": "Expert Brain not initialized for this project.",
            "citations": [],
            "support_facts": [],
            "mode": "error",
            "compliance_status": "ORCHESTRATOR_UNAVAILABLE",
        }

    if not project_id:
        return {
            "answer": "No active project is loaded for this chat.",
            "citations": [],
            "support_facts": [],
            "mode": "error",
            "compliance_status": "PROJECT_UNAVAILABLE",
        }

    # Mounted imported-date selector is informational only by contract.
    # Do not pass snapshot-like UI state into the mounted sourced answer path.
    job_manager = getattr(controller, "job_manager", None)
    if job_manager and hasattr(job_manager, "interactive_session"):
        with job_manager.interactive_session():
            result = orchestrator.answer_question(
                query=query,
                project_id=project_id,
                snapshot_id=None,
            )
    else:
        result = orchestrator.answer_question(
            query=query,
            project_id=project_id,
            snapshot_id=None,
        )

    if not isinstance(result, dict):
        return {
            "answer": str(result),
            "citations": [],
            "support_facts": [],
            "mode": "answered",
            "compliance_status": "ANSWERED_WITH_PROVENANCE",
        }

    if not result.get("answer"):
        result = dict(result)
        result["answer"] = "No response from brain."
    return result
