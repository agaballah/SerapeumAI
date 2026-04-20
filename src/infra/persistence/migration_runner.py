# -*- coding: utf-8 -*-
"""Canonical Migration Runner (Phase 1)
Design-phase simplified runner that initializes fresh DBs to canonical v1
and strictly verifies shape, rejecting legacy drift exactly as requested.
"""
import logging
import os
import sqlite3

logger = logging.getLogger(__name__)

class MigrationRunner:
    def __init__(self):
        pass

    def get_migration_dir(self, schema_kind: str) -> str:
        base_dir = os.path.dirname(__file__)
        if schema_kind == "project":
            return os.path.join(base_dir, "migrations")
        else:
            return os.path.join(base_dir, "global_migrations")

    def create_fresh_db(self, conn: sqlite3.Connection, schema_kind: str) -> None:
        logger.info(f"Initializing fresh {schema_kind} DB from canonical Phase 1 schema.")
        
        if schema_kind == "project":
            from src.infra.persistence.project_schema import build_project_schema_sql, PROJECT_SCHEMA_LABEL
            sql_list = build_project_schema_sql()
            label = PROJECT_SCHEMA_LABEL
        else:
            from src.infra.persistence.global_schema import build_global_schema_sql, GLOBAL_SCHEMA_LABEL
            sql_list = build_global_schema_sql()
            label = GLOBAL_SCHEMA_LABEL
            
        conn.executescript("\n".join(sql_list))
        conn.execute("INSERT INTO schema_version (version, label) VALUES (1, ?)", (label,))
        conn.commit()

    def apply_ordered_migrations(self, conn: sqlite3.Connection, schema_kind: str, from_version: int, to_version: int) -> None:
        raise NotImplementedError("Broad migration engine not active in design Phase 1.")

    def run_startup_schema_flow(self, conn: sqlite3.Connection, schema_kind: str, design_phase: bool = True) -> None:
        from src.infra.persistence.schema_verifier import SchemaVerifier
        
        if schema_kind == "project":
            from src.infra.persistence.project_schema import PROJECT_SCHEMA_VERSION, project_schema_manifest
            expected_ver = PROJECT_SCHEMA_VERSION
            manifest = project_schema_manifest()
        else:
            from src.infra.persistence.global_schema import GLOBAL_SCHEMA_VERSION, global_schema_manifest
            expected_ver = GLOBAL_SCHEMA_VERSION
            manifest = global_schema_manifest()
            
        verifier = SchemaVerifier()
        res = verifier.verify_schema(conn, schema_kind, expected_ver, manifest)
        
        if res.status == "empty_fresh":
            self.create_fresh_db(conn, schema_kind)
            # Re-verify after creation
            res = verifier.verify_schema(conn, schema_kind, expected_ver, manifest)
            if res.status != "exact_match":
                raise RuntimeError(f"Created fresh DB but verification failed [{res.status}]: {res.errors}")
            return
            
        if res.status == "unknown_higher_version":
            raise RuntimeError(f"Unknown higher version ({res.version}); fail closed.")
            
        if res.status == "rebuild_required":
            if design_phase:
                raise RuntimeError(f"Legacy DB version detected ({res.version}); rebuild required.")
            else:
                raise RuntimeError("Legacy DB version detected, but migrations not supported in Phase 1.")

        if res.status != "exact_match":
            raise RuntimeError(f"Schema exact shape validation failed [{res.status}]: {res.errors}")
            
        logger.info(f"Schema for {schema_kind} validated exactly against canonical Phase 1 spec.")
