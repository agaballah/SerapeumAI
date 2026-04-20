# -*- coding: utf-8 -*-
"""
fortification_tools.py — Tools for enforcing agent solidity and truthfulness.
"""

from typing import Any, Dict
from src.tools.base_tool import BaseTool
from src.infra.persistence.database_manager import DatabaseManager

class VerifyCitationTool(BaseTool):
    """Tool for verifying if a specific quote exists in a document."""
    
    def __init__(self, db: DatabaseManager):
        self.db = db

    @property
    def name(self) -> str:
        return "verify_citation"

    @property
    def description(self) -> str:
        return (
            "Verify if a specific text quote actually exists in the document. "
            "Use this BEFORE citing a standard or specific requirement to prevent hallucination. "
            "Returns 'Verified' or 'Citation Failed'."
        )

    def execute(self, quote: str, doc_id: str, **kwargs) -> str:
        try:
            # Get full document text
            payload = self.db.get_document_payload(doc_id)
            content = payload.get("text", "")
            
            if not content:
                return f"CITATION FAILED: Document {doc_id} is empty or not found."

            # Normalize strings for comparison (ignore whitespace differences)
            def normalize(s):
                return " ".join(s.split()).lower()

            norm_quote = normalize(quote)
            norm_content = normalize(content)

            if norm_quote in norm_content:
                return f"VERIFIED: Quote found in document {doc_id}."
            else:
                return (
                    f"CITATION FAILED: The quote '{quote}' was NOT found in document {doc_id}. "
                    "Do not cite this text."
                )

        except Exception as e:
            return f"Error verifying citation: {str(e)}"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "quote": {
                    "type": "string",
                    "description": "The exact text segment to verify."
                },
                "doc_id": {
                    "type": "string",
                    "description": "The ID of the document to check against."
                }
            },
            "required": ["quote", "doc_id"]
        }
