# -*- coding: utf-8 -*-
"""Canonical Project Database Schema (Phase 1)
All tables required for the project database are defined here.
Exposes the schema definition and its expected verification manifest.
"""
from typing import Dict, Any, List

PROJECT_SCHEMA_VERSION = 1
PROJECT_SCHEMA_LABEL = "canonical_v1_project"

def build_project_schema_sql() -> List[str]:
    return [
        """
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
            label TEXT NOT NULL
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS project_meta (
            project_id TEXT PRIMARY KEY,
            project_name TEXT NOT NULL,
            root_path TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS documents (
            doc_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            scope TEXT NOT NULL,
            doc_key TEXT NOT NULL,
            title TEXT,
            doc_type TEXT,
            discipline TEXT,
            status TEXT NOT NULL,
            current_file_version_id TEXT,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        );
        """,
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_documents_key 
        ON documents(project_id, doc_key);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_documents_type 
        ON documents(project_id, doc_type);
        """,
        """
        CREATE TABLE IF NOT EXISTS file_versions (
            file_version_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            doc_id TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            file_name TEXT NOT NULL,
            file_ext TEXT NOT NULL,
            rel_path TEXT NOT NULL,
            abs_path_snapshot TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            file_mtime REAL NOT NULL,
            source_channel TEXT NOT NULL,
            created_at INTEGER NOT NULL
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_file_versions_created 
        ON file_versions(project_id, doc_id, created_at DESC);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_file_versions_hash 
        ON file_versions(project_id, content_hash);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_file_versions_rel 
        ON file_versions(project_id, rel_path);
        """,
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_file_versions_uniq 
        ON file_versions(project_id, doc_id, content_hash);
        """,
        """
        CREATE TABLE IF NOT EXISTS pages (
            page_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            file_version_id TEXT NOT NULL,
            page_number INTEGER NOT NULL,
            page_kind TEXT NOT NULL,
            width REAL,
            height REAL,
            render_ref TEXT,
            ocr_status TEXT NOT NULL,
            created_at INTEGER NOT NULL
        );
        """,
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_pages_fv_num 
        ON pages(file_version_id, page_number);
        """,
        """
        CREATE TABLE IF NOT EXISTS blocks (
            block_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            file_version_id TEXT NOT NULL,
            page_id TEXT NOT NULL,
            block_type TEXT NOT NULL,
            block_order INTEGER NOT NULL,
            text TEXT NOT NULL,
            bbox_json TEXT,
            meta_json TEXT,
            created_at INTEGER NOT NULL
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_blocks_order 
        ON blocks(file_version_id, page_id, block_order);
        """,
        """
        CREATE TABLE IF NOT EXISTS extraction_runs (
            extraction_run_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            file_version_id TEXT NOT NULL,
            extractor_name TEXT NOT NULL,
            status TEXT NOT NULL,
            started_at INTEGER NOT NULL,
            finished_at INTEGER,
            duration_ms INTEGER,
            error_text TEXT,
            telemetry_json TEXT
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS analysis_runs (
            analysis_run_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            file_version_id TEXT NOT NULL,
            run_type TEXT NOT NULL,
            status TEXT NOT NULL,
            started_at INTEGER NOT NULL,
            finished_at INTEGER,
            duration_ms INTEGER,
            error_text TEXT,
            telemetry_json TEXT
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS facts (
            fact_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            fact_type TEXT NOT NULL,
            subject_kind TEXT NOT NULL,
            subject_id TEXT NOT NULL,
            domain TEXT,
            as_of_json TEXT NOT NULL, -- Core SSOT Requirement
            value_type TEXT NOT NULL,
            value_json TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'CANDIDATE',
            confidence REAL DEFAULT 1.0,
            method_id TEXT NOT NULL,
            authority_role TEXT,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS fact_inputs (
            fact_id TEXT NOT NULL,
            file_version_id TEXT NOT NULL,
            location_json TEXT,
            input_kind TEXT NOT NULL,
            PRIMARY KEY (fact_id, file_version_id, location_json)
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_inputs_fact ON fact_inputs(fact_id);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_inputs_fv ON fact_inputs(file_version_id);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_inputs_kind ON fact_inputs(input_kind);
        """,
        """
        CREATE TABLE IF NOT EXISTS global_source_refs (
            ref_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            global_doc_id TEXT NOT NULL,
            global_file_version_id TEXT NOT NULL,
            linked_from_channel TEXT NOT NULL,
            linked_at INTEGER NOT NULL,
            note TEXT
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS chat_sessions (
            session_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL,
            meta_json TEXT
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS chat_messages (
            message_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            meta_json TEXT
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS chat_message_attachments (
            attachment_id TEXT PRIMARY KEY,
            message_id TEXT NOT NULL,
            attachment_scope TEXT NOT NULL,
            project_file_version_id TEXT,
            global_file_version_id TEXT,
            display_name TEXT NOT NULL,
            created_at INTEGER NOT NULL
        );
        """,
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS blocks_fts 
        USING fts5(block_id, text);
        """,
        """
        CREATE TABLE IF NOT EXISTS fact_snapshots (
            snapshot_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            label TEXT,
            created_at INTEGER NOT NULL
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS fact_snapshot_registry (
            snapshot_id TEXT NOT NULL,
            fact_id TEXT NOT NULL,
            PRIMARY KEY (snapshot_id, fact_id)
        );
        """
    ]

def project_schema_manifest() -> Dict[str, Any]:
    return {
        "tables": {
            "schema_version": {"version": {"notnull": False, "pk": True}, "applied_at": {"notnull": True, "pk": False}, "label": {"notnull": True, "pk": False}},
            "project_meta": {"project_id": {"notnull": False, "pk": True}, "project_name": {"notnull": True, "pk": False}, "root_path": {"notnull": True, "pk": False}, "created_at": {"notnull": True, "pk": False}, "updated_at": {"notnull": True, "pk": False}},
            "documents": {"doc_id": {"notnull": False, "pk": True}, "project_id": {"notnull": True, "pk": False}, "scope": {"notnull": True, "pk": False}, "doc_key": {"notnull": True, "pk": False}, "title": {"notnull": False, "pk": False}, "doc_type": {"notnull": False, "pk": False}, "discipline": {"notnull": False, "pk": False}, "status": {"notnull": True, "pk": False}, "current_file_version_id": {"notnull": False, "pk": False}, "created_at": {"notnull": True, "pk": False}, "updated_at": {"notnull": True, "pk": False}},
            "file_versions": {"file_version_id": {"notnull": False, "pk": True}, "project_id": {"notnull": True, "pk": False}, "doc_id": {"notnull": True, "pk": False}, "content_hash": {"notnull": True, "pk": False}, "file_name": {"notnull": True, "pk": False}, "file_ext": {"notnull": True, "pk": False}, "rel_path": {"notnull": True, "pk": False}, "abs_path_snapshot": {"notnull": True, "pk": False}, "file_size": {"notnull": True, "pk": False}, "file_mtime": {"notnull": True, "pk": False}, "source_channel": {"notnull": True, "pk": False}, "created_at": {"notnull": True, "pk": False}},
            "pages": {"page_id": {"notnull": False, "pk": True}, "project_id": {"notnull": True, "pk": False}, "file_version_id": {"notnull": True, "pk": False}, "page_number": {"notnull": True, "pk": False}, "page_kind": {"notnull": True, "pk": False}, "width": {"notnull": False, "pk": False}, "height": {"notnull": False, "pk": False}, "render_ref": {"notnull": False, "pk": False}, "ocr_status": {"notnull": True, "pk": False}, "created_at": {"notnull": True, "pk": False}},
            "blocks": {"block_id": {"notnull": False, "pk": True}, "project_id": {"notnull": True, "pk": False}, "file_version_id": {"notnull": True, "pk": False}, "page_id": {"notnull": True, "pk": False}, "block_type": {"notnull": True, "pk": False}, "block_order": {"notnull": True, "pk": False}, "text": {"notnull": True, "pk": False}, "bbox_json": {"notnull": False, "pk": False}, "meta_json": {"notnull": False, "pk": False}, "created_at": {"notnull": True, "pk": False}},
            "extraction_runs": {"extraction_run_id": {"notnull": False, "pk": True}, "project_id": {"notnull": True, "pk": False}, "file_version_id": {"notnull": True, "pk": False}, "extractor_name": {"notnull": True, "pk": False}, "status": {"notnull": True, "pk": False}, "started_at": {"notnull": True, "pk": False}, "finished_at": {"notnull": False, "pk": False}, "duration_ms": {"notnull": False, "pk": False}, "error_text": {"notnull": False, "pk": False}, "telemetry_json": {"notnull": False, "pk": False}},
            "analysis_runs": {"analysis_run_id": {"notnull": False, "pk": True}, "project_id": {"notnull": True, "pk": False}, "file_version_id": {"notnull": True, "pk": False}, "run_type": {"notnull": True, "pk": False}, "status": {"notnull": True, "pk": False}, "started_at": {"notnull": True, "pk": False}, "finished_at": {"notnull": False, "pk": False}, "duration_ms": {"notnull": False, "pk": False}, "error_text": {"notnull": False, "pk": False}, "telemetry_json": {"notnull": False, "pk": False}},
            "facts": {"fact_id": {"notnull": False, "pk": True}, "project_id": {"notnull": True, "pk": False}, "fact_type": {"notnull": True, "pk": False}, "subject_kind": {"notnull": True, "pk": False}, "subject_id": {"notnull": True, "pk": False}, "domain": {"notnull": False, "pk": False}, "as_of_json": {"notnull": True, "pk": False}, "value_type": {"notnull": True, "pk": False}, "value_json": {"notnull": True, "pk": False}, "status": {"notnull": True, "pk": False}, "confidence": {"notnull": False, "pk": False}, "method_id": {"notnull": True, "pk": False}, "authority_role": {"notnull": False, "pk": False}, "created_at": {"notnull": True, "pk": False}, "updated_at": {"notnull": True, "pk": False}},
            "fact_inputs": {"fact_id": {"notnull": True, "pk": True}, "file_version_id": {"notnull": True, "pk": True}, "location_json": {"notnull": False, "pk": True}, "input_kind": {"notnull": True, "pk": False}},
            "global_source_refs": {"ref_id": {"notnull": False, "pk": True}, "project_id": {"notnull": True, "pk": False}, "global_doc_id": {"notnull": True, "pk": False}, "global_file_version_id": {"notnull": True, "pk": False}, "linked_from_channel": {"notnull": True, "pk": False}, "linked_at": {"notnull": True, "pk": False}, "note": {"notnull": False, "pk": False}},
            "chat_sessions": {"session_id": {"notnull": False, "pk": True}, "project_id": {"notnull": True, "pk": False}, "created_at": {"notnull": True, "pk": False}, "updated_at": {"notnull": True, "pk": False}, "meta_json": {"notnull": False, "pk": False}},
            "chat_messages": {"message_id": {"notnull": False, "pk": True}, "session_id": {"notnull": True, "pk": False}, "role": {"notnull": True, "pk": False}, "content": {"notnull": True, "pk": False}, "created_at": {"notnull": True, "pk": False}, "meta_json": {"notnull": False, "pk": False}},
            "chat_message_attachments": {"attachment_id": {"notnull": False, "pk": True}, "message_id": {"notnull": True, "pk": False}, "attachment_scope": {"notnull": True, "pk": False}, "project_file_version_id": {"notnull": False, "pk": False}, "global_file_version_id": {"notnull": False, "pk": False}, "display_name": {"notnull": True, "pk": False}, "created_at": {"notnull": True, "pk": False}},
            "fact_snapshots": {"snapshot_id": {"notnull": False, "pk": True}, "project_id": {"notnull": True, "pk": False}, "label": {"notnull": False, "pk": False}, "created_at": {"notnull": True, "pk": False}},
            "fact_snapshot_registry": {"snapshot_id": {"notnull": True, "pk": True}, "fact_id": {"notnull": True, "pk": True}}
        },
        "indexes": {
            "idx_documents_key": {"table": "documents", "unique": True, "columns": ["project_id", "doc_key"]},
            "idx_documents_type": {"table": "documents", "unique": False, "columns": ["project_id", "doc_type"]},
            "idx_file_versions_created": {"table": "file_versions", "unique": False, "columns": ["project_id", "doc_id", "created_at"]},
            "idx_file_versions_hash": {"table": "file_versions", "unique": False, "columns": ["project_id", "content_hash"]},
            "idx_file_versions_rel": {"table": "file_versions", "unique": False, "columns": ["project_id", "rel_path"]},
            "idx_file_versions_uniq": {"table": "file_versions", "unique": True, "columns": ["project_id", "doc_id", "content_hash"]},
            "idx_pages_fv_num": {"table": "pages", "unique": True, "columns": ["file_version_id", "page_number"]},
            "idx_blocks_order": {"table": "blocks", "unique": False, "columns": ["file_version_id", "page_id", "block_order"]},
            "idx_lineage_fact": {"table": "fact_lineage", "unique": False, "columns": ["fact_id"]},
            "idx_lineage_fv": {"table": "fact_lineage", "unique": False, "columns": ["file_version_id"]},
            "idx_lineage_page": {"table": "fact_lineage", "unique": False, "columns": ["page_id"]},
            "idx_lineage_block": {"table": "fact_lineage", "unique": False, "columns": ["block_id"]}
        },
        "fts": ["blocks_fts"],
        "foreign_keys": {}
    }
