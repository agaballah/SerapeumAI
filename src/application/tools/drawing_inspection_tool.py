"""Metadata-only drawing inspection skill definition.

This module declares the future drawing-inspection tool contract. It does not
inspect files, call OCR, query services, write data, or certify project truth.
"""

from __future__ import annotations

from typing import Any

from src.application.tools.tool_registry import (
    ToolAuthorityLevel,
    ToolDefinition,
    ToolScope,
    ToolSideEffect,
)


TOOL_ID = "drawing_inspection.skill"
TOOL_VERSION = "1.0"

INSPECTION_TYPES = (
    "scale_check",
    "text_legibility",
    "completeness_review",
    "revision_control",
)


class DrawingInspectionToolError(ValueError):
    """Raised when drawing inspection input is invalid."""


def drawing_inspection_tool_definition() -> ToolDefinition:
    """Return the source-defined drawing inspection tool definition."""

    definition = ToolDefinition(
        tool_id=TOOL_ID,
        display_name="Drawing Inspection Skill",
        description=(
            "Declares a bounded project-support skill for drawing inspection "
            "readiness. Results are supporting-only and cannot govern truth."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "inspection_type": {
                    "type": "string",
                    "enum": list(INSPECTION_TYPES),
                    "description": "Drawing inspection support category to request.",
                },
                "document_id": {
                    "type": "string",
                    "description": "Optional project document identifier.",
                },
            },
            "required": ["inspection_type"],
            "additionalProperties": False,
        },
        output_schema={
            "type": "object",
            "properties": {
                "inspection_type": {"type": "string"},
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
                "inspection_type",
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


def build_drawing_inspection_not_executed_result(
    inspection_type: str,
    document_id: str | None = None,
) -> dict[str, Any]:
    """Return an honest non-executed envelope for future tool wiring tests."""

    if inspection_type not in INSPECTION_TYPES:
        raise DrawingInspectionToolError(f"Unsupported inspection type: {inspection_type}")

    provenance = []
    if document_id:
        provenance.append({"kind": "requested_document", "document_id": document_id})

    return {
        "inspection_type": inspection_type,
        "status": "not_executed",
        "findings": [],
        "recommendations": [],
        "provenance": provenance,
        "limitations": [
            "Drawing inspection execution is not implemented in this metadata packet.",
            "This result is supporting-only and cannot certify drawing truth.",
        ],
        "supporting_only": True,
        "can_govern_truth": False,
        "tool_id": TOOL_ID,
        "tool_version": TOOL_VERSION,
    }
