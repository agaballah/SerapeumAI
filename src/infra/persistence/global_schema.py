# -*- coding: utf-8 -*-
"""Canonical Global Database Schema (Phase 1)
Defines the minimal canonical schema for the global SerapeumAI database.
Exposes the schema definition and its expected verification manifest.
"""
from typing import Dict, Any, List

GLOBAL_SCHEMA_VERSION = 1
GLOBAL_SCHEMA_LABEL = "canonical_v1_global"

def build_global_schema_sql() -> List[str]:
    return [
        """
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
            label TEXT NOT NULL
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS global_meta (
            instance_id TEXT PRIMARY KEY,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS global_documents (
            doc_id TEXT PRIMARY KEY,
            scope TEXT NOT NULL,
            doc_key TEXT NOT NULL,
            title TEXT NOT NULL,
            source_type TEXT NOT NULL,
            jurisdiction TEXT,
            authority TEXT,
            language TEXT,
            status TEXT NOT NULL,
            current_file_version_id TEXT,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        );
        """,
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_global_documents_key 
        ON global_documents(doc_key);
        """,
        """
        CREATE TABLE IF NOT EXISTS global_file_versions (
            file_version_id TEXT PRIMARY KEY,
            doc_id TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            file_name TEXT NOT NULL,
            file_ext TEXT NOT NULL,
            abs_path_snapshot TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            file_mtime REAL NOT NULL,
            source_channel TEXT NOT NULL,
            created_at INTEGER NOT NULL
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS global_sections (
            section_id TEXT PRIMARY KEY,
            file_version_id TEXT NOT NULL,
            section_path TEXT NOT NULL,
            section_label TEXT NOT NULL,
            title TEXT NOT NULL,
            text TEXT NOT NULL,
            tags_json TEXT,
            meta_json TEXT
        );
        """,
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS global_sections_fts
        USING fts5(section_id, text);
        """,
        """
        CREATE TABLE IF NOT EXISTS global_xrefs (
            xref_id TEXT PRIMARY KEY,
            from_section_id TEXT NOT NULL,
            to_section_id TEXT,
            xref_text TEXT NOT NULL,
            xref_type TEXT NOT NULL,
            meta_json TEXT
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS global_index_runs (
            index_run_id TEXT PRIMARY KEY,
            doc_id TEXT,
            file_version_id TEXT,
            stage TEXT NOT NULL,
            status TEXT NOT NULL,
            started_at INTEGER NOT NULL,
            finished_at INTEGER,
            duration_ms INTEGER,
            error_text TEXT,
            telemetry_json TEXT
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS persona_templates (
            template_id TEXT PRIMARY KEY,
            role TEXT NOT NULL,
            discipline TEXT NOT NULL,
            intent TEXT NOT NULL,
            system_instructions TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        );
        """,
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_persona_templates_unique 
        ON persona_templates(role, discipline, intent);
        """
    ]

def global_schema_manifest() -> Dict[str, Any]:
    return {
        "tables": {
            "schema_version": {"version": {"notnull": False, "pk": True}, "applied_at": {"notnull": True, "pk": False}, "label": {"notnull": True, "pk": False}},
            "global_meta": {"instance_id": {"notnull": False, "pk": True}, "created_at": {"notnull": True, "pk": False}, "updated_at": {"notnull": True, "pk": False}},
            "global_documents": {"doc_id": {"notnull": False, "pk": True}, "scope": {"notnull": True, "pk": False}, "doc_key": {"notnull": True, "pk": False}, "title": {"notnull": True, "pk": False}, "source_type": {"notnull": True, "pk": False}, "jurisdiction": {"notnull": False, "pk": False}, "authority": {"notnull": False, "pk": False}, "language": {"notnull": False, "pk": False}, "status": {"notnull": True, "pk": False}, "current_file_version_id": {"notnull": False, "pk": False}, "created_at": {"notnull": True, "pk": False}, "updated_at": {"notnull": True, "pk": False}},
            "global_file_versions": {"file_version_id": {"notnull": False, "pk": True}, "doc_id": {"notnull": True, "pk": False}, "content_hash": {"notnull": True, "pk": False}, "file_name": {"notnull": True, "pk": False}, "file_ext": {"notnull": True, "pk": False}, "abs_path_snapshot": {"notnull": True, "pk": False}, "file_size": {"notnull": True, "pk": False}, "file_mtime": {"notnull": True, "pk": False}, "source_channel": {"notnull": True, "pk": False}, "created_at": {"notnull": True, "pk": False}},
            "global_sections": {"section_id": {"notnull": False, "pk": True}, "file_version_id": {"notnull": True, "pk": False}, "section_path": {"notnull": True, "pk": False}, "section_label": {"notnull": True, "pk": False}, "title": {"notnull": True, "pk": False}, "text": {"notnull": True, "pk": False}, "tags_json": {"notnull": False, "pk": False}, "meta_json": {"notnull": False, "pk": False}},
            "global_xrefs": {"xref_id": {"notnull": False, "pk": True}, "from_section_id": {"notnull": True, "pk": False}, "to_section_id": {"notnull": False, "pk": False}, "xref_text": {"notnull": True, "pk": False}, "xref_type": {"notnull": True, "pk": False}, "meta_json": {"notnull": False, "pk": False}},
            "global_index_runs": {"index_run_id": {"notnull": False, "pk": True}, "doc_id": {"notnull": False, "pk": False}, "file_version_id": {"notnull": False, "pk": False}, "stage": {"notnull": True, "pk": False}, "status": {"notnull": True, "pk": False}, "started_at": {"notnull": True, "pk": False}, "finished_at": {"notnull": False, "pk": False}, "duration_ms": {"notnull": False, "pk": False}, "error_text": {"notnull": False, "pk": False}, "telemetry_json": {"notnull": False, "pk": False}},
            "persona_templates": {"template_id": {"notnull": False, "pk": True}, "role": {"notnull": True, "pk": False}, "discipline": {"notnull": True, "pk": False}, "intent": {"notnull": True, "pk": False}, "system_instructions": {"notnull": True, "pk": False}, "created_at": {"notnull": True, "pk": False}, "updated_at": {"notnull": True, "pk": False}}
        },
        "indexes": {
            "idx_global_documents_key": {"table": "global_documents", "unique": True, "columns": ["doc_key"]},
            "idx_persona_templates_unique": {"table": "persona_templates", "unique": True, "columns": ["role", "discipline", "intent"]}
        },
        "fts": ["global_sections_fts"],
        "foreign_keys": {}
    }
