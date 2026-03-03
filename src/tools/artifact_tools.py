# -*- coding: utf-8 -*-
from typing import Any, Dict
from src.tools.base_tool import BaseTool
from src.document_processing.artifact_service import ArtifactService

class CreateSOWArtifactTool(BaseTool):
    """Tool for generating a Statement of Work (SOW) artifact."""
    
    def __init__(self, project_dir: str):
        self.service = ArtifactService(project_dir)

    @property
    def name(self) -> str:
        return "create_sow_artifact"

    @property
    def description(self) -> str:
        return (
            "Generate a formal Statement of Work (SOW) document (DOCX). "
            "Requires a structured JSON input with sections like purpose, scope_overview, deliverables, etc. "
            "Use this ONLY when 'Mode F' is active and you have consolidated technical evidence."
        )

    def execute(self, content: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        try:
            path = self.service.generate_sow(content)
            return {
                "status": "success",
                "artifact_type": "sow",
                "path": path,
                "message": "SOW Artifact generated successfully."
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "content": {
                    "type": "object",
                    "properties": {
                        "purpose": {"type": "string"},
                        "scope_overview": {"type": "string"},
                        "deliverables": {"type": "string"},
                        "raci": {"type": "string"},
                        "approach": {"type": "string"},
                        "acceptance": {"type": "string"},
                        "handover": {"type": "string"},
                        "training": {"type": "string"},
                        "assumptions": {"type": "string"},
                        "risks": {"type": "string"}
                    },
                    "description": "Structured SOW content mapping to required sections."
                }
            },
            "required": ["content"]
        }
