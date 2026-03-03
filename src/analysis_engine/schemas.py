# JSON Schema Definitions for Page Analysis
# This file contains strict JSON schemas for enforcing LLM output structure

PAGE_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {
            "type": "string",
            "description": "One concise sentence describing the page content",
            "maxLength": 500
        },
        "type": {
            "type": "string",
            "description": "Document page type classification",
            "enum": ["contract", "drawing", "spec", "data", "form", "schedule", "other"]
        },
        "entities": {
            "type": "array",
            "description": "Key entities mentioned on this page",
            "items": {"type": "string"},
            "maxItems": 10,
            "default": []
        },
        "relationships": {
           "type": "array",
            "description": "Functional connections between entities",
            "items": {
                "type": "object",
                "properties": {
                    "source": {"type": "string"},
                    "relation": {"type": "string"},
                    "target": {"type": "string"}
                },
                "required": ["source", "relation", "target"],
                "additionalProperties": False
            },
            "default": []
        }
    },
    "required": ["summary", "type", "entities"],
    "additionalProperties": False
}

DOCUMENT_ROLLUP_SCHEMA = {
    "type": "object",
    "properties": {
        "short_summary": {
            "type": "string",
            "maxLength": 500
        },
        "detailed_summary": {
            "type": "string",
            "maxLength": 2000
        },
        "doc_type": {
            "type": "string",
            "enum": ["contract", "drawing", "spec", "data", "form", "schedule", "other"]
        }
    },
    "required": ["short_summary", "detailed_summary", "doc_type"],
    "additionalProperties": False
}
