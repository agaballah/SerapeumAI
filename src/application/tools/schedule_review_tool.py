"""Metadata-only schedule review skill definition.

This module declares the future schedule-review tool contract. It does not
query schedule files, execute schedulers, write data, or certify project truth.
"""

from __future__ import annotations

from typing import Any

from src.application.tools.tool_registry import (
    ToolAuthorityLevel,
    ToolDefinition,
    ToolScope,
    ToolSideEffect,
)


TOOL_ID = "schedule_review.skill"
TOOL_VERSION = "1.0"

REVIEW_TYPES = (
    "logic_check",
    "float_analysis",
    "duration_reasonableness",
    "milestone_review",
)


class ScheduleReviewToolError(ValueError):
    """Raised when schedule review input is invalid."""


def schedule_review_tool_definition() -> ToolDefinition:
    """Return the source-defined schedule review tool definition."""

    definition = ToolDefinition(
        tool_id=TOOL_ID,
        display_name="Schedule Review Skill",
        description=(
            "Declares a bounded project-support skill for schedule review "
            "readiness. Results are supporting-only and cannot govern truth."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "review_type": {
                    "type": "string",
                    "enum": list(REVIEW_TYPES),
                    "description": "Schedule review support category to request.",
                },
                "threshold_days": {
                    "type": "number",
                    "description": "Optional day threshold supplied by the operator.",
                    "default": 0,
                },
            },
            "required": ["review_type"],
            "additionalProperties": False,
        },
        output_schema={
            "type": "object",
            "properties": {
                "review_type": {"type": "string"},
                "status": {"type": "string"},
                "findings": {"type": "array"},
                "recommendations": {"type": "array"},
                "provenance": {"type": "array"},
                "limitations": {"type": "array"},
                "supporting_only": {"type": "boolean"},
                "can_govern_truth": {"type": "boolean"},
                "tool_id": {"type": "string"},
                "tool_version": {"type": "string"},
            },
            "required": [
                "review_type",
                "status",
                "findings",
                "recommendations",
                "provenance",
                "limitations",
                "supporting_only",
                "can_govern_truth",
                "tool_id",
                "tool_version",
            ],
            "additionalProperties": False,
        },
        authority_level=ToolAuthorityLevel.SUPPORT_RETRIEVAL,
        scope=ToolScope.PROJECT,
        side_effects=(ToolSideEffect.READ_PROJECT_DB,),
        requires_consent=False,
        can_govern_truth=False,
        audit_log_required=True,
        enabled_by_default=False,
        requires_project=True,
        requires_snapshot=False,
        result_provenance_required=True,
        version=TOOL_VERSION,
    )
    definition.validate()
    return definition


def build_schedule_review_not_executed_result(
    review_type: str,
    threshold_days: float = 0,
) -> dict[str, Any]:
    """Return an honest non-executed envelope for future tool wiring tests."""

    if review_type not in REVIEW_TYPES:
        raise ScheduleReviewToolError(f"Unsupported review type: {review_type}")

    return {
        "review_type": review_type,
        "status": "not_executed",
        "findings": [],
        "recommendations": [],
        "provenance": [{"kind": "operator_parameter", "threshold_days": threshold_days}],
        "limitations": [
            "Schedule review execution is not implemented in this metadata packet.",
            "This result is supporting-only and cannot certify schedule truth.",
        ],
        "supporting_only": True,
        "can_govern_truth": False,
        "tool_id": TOOL_ID,
        "tool_version": TOOL_VERSION,
    }
