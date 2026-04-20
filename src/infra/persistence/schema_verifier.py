# -*- coding: utf-8 -*-
"""Canonical Schema Verifier (Phase 1)
Strict shape verifier for the canonical database schemas.
"""
import sqlite3
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Literal

logger = logging.getLogger(__name__)

SchemaKind = Literal["project", "global"]
VerificationStatus = Literal["exact_match", "empty_fresh", "rebuild_required", "unknown_higher_version", "invalid_shape"]

@dataclass
class SchemaVerificationResult:
    valid: bool = False
    version: int = 0
    status: VerificationStatus = "invalid_shape"
    errors: List[str] = field(default_factory=list)


class SchemaVerifier:
    def verify_schema(
        self, 
        conn: sqlite3.Connection, 
        schema_kind: SchemaKind, 
        expected_version: int, 
        expected_manifest: Dict[str, Any]
    ) -> SchemaVerificationResult:
        result = SchemaVerificationResult()
        
        # Check if DB is totally empty first by looking for any tables
        num_tables = conn.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
        if num_tables == 0:
            result.status = "empty_fresh"
            result.errors.append("No tables found. DB is empty.")
            return result
            
        try:
            row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
            current_ver = row[0] if row and row[0] is not None else 0
            result.version = current_ver
            
            if current_ver == 0:
                 # The table exists but is empty, this is an invalid state, not a fresh DB
                 result.status = "invalid_shape"
                 result.errors.append("schema_version table exists but is empty")
                 return result
        except sqlite3.OperationalError:
            # schema_version table doesn't exist, but other tables do (num_tables > 0)
            result.version = 0
            result.status = "invalid_shape"
            result.errors.append("schema_version table missing in a non-empty DB")
            return result
        except Exception as e:
            result.version = 0
            result.status = "invalid_shape"
            result.errors.append(f"Error querying schema_version: {e}")
            return result
            
        if current_ver > expected_version:
            result.status = "unknown_higher_version"
            result.errors.append(f"Higher schema version detected: {current_ver}, expected {expected_version}")
            return result
            
        if current_ver < expected_version:
            result.status = "rebuild_required"
            result.errors.append(f"Legacy schema version detected: {current_ver}, expected {expected_version}")
            return result

        expected_tables = expected_manifest.get("tables", {})
        expected_fts = set(expected_manifest.get("fts", []))
        expected_indexes = expected_manifest.get("indexes", {})
        expected_fks = expected_manifest.get("foreign_keys", {})
        
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        actual_tables = [r[0] for r in rows if not r[0].startswith("sqlite_")]
        actual_fts_tables = {t for t in actual_tables if t.endswith("_fts")}
        
        # Identify core tables ignoring sqlite internal and fts shadow tables
        actual_data_tables = {
            t for t in actual_tables 
            if not (t.endswith("_fts") or 
                    t.endswith("_fts_data") or 
                    t.endswith("_fts_idx") or 
                    t.endswith("_fts_docsize") or 
                    t.endswith("_fts_config") or 
                    t.endswith("_fts_content"))
        }

        # Check explicit data tables
        for t in expected_tables:
            if t not in actual_data_tables:
                result.errors.append(f"Missing required table: {t}")

        for t in actual_data_tables:
            if t not in expected_tables:
                result.errors.append(f"Unexpected legacy/unknown table present: {t}")

        # Check FTS
        for fts in expected_fts:
            if fts not in actual_fts_tables:
                result.errors.append(f"Missing FTS table: {fts}")
                
        # Check actual columns and constraints (NOT NULL, PK)
        for t, expected_cols_meta in expected_tables.items():
            if t in actual_data_tables:
                col_rows = conn.execute(f"PRAGMA table_info({t})").fetchall()
                actual_cols_meta = {}
                for r in col_rows:
                     # r[1] is name, r[3] is notnull flag, r[5] is pk flag
                     actual_cols_meta[r[1]] = {"notnull": bool(r[3]), "pk": bool(r[5])}
                
                expected_col_names = set(expected_cols_meta.keys())
                actual_col_names = set(actual_cols_meta.keys())
                
                if actual_col_names != expected_col_names:
                    diff_missing = expected_col_names - actual_col_names
                    diff_extra = actual_col_names - expected_col_names
                    result.errors.append(f"Table {t} column mismatch. Missing: {diff_missing}, Extra: {diff_extra}")
                else:
                    for col_name, expected_meta in expected_cols_meta.items():
                         actual_meta = actual_cols_meta[col_name]
                         if expected_meta["notnull"] != actual_meta["notnull"]:
                             result.errors.append(f"Table {t} column {col_name} NOT NULL mismatch: expected {expected_meta['notnull']}, got {actual_meta['notnull']}")
                         if expected_meta["pk"] != actual_meta["pk"]:
                             result.errors.append(f"Table {t} column {col_name} PK mismatch: expected {expected_meta['pk']}, got {actual_meta['pk']}")
        
        # Check explicit indexes and their uniqueness/columns
        raw_idx = conn.execute("SELECT name, tbl_name FROM sqlite_master WHERE type='index'").fetchall()
        # ignore FTS internal indexes and sqlite autoindexes
        actual_indexes = {}
        for r in raw_idx:
            idx_name = r[0]
            tbl_name = r[1]
            if idx_name and not idx_name.endswith("_fts_idx") and not idx_name.startswith("sqlite_autoindex_"):
                 idx_info_rows = conn.execute(f"PRAGMA index_list({tbl_name})").fetchall()
                 is_unique = False
                 for i in idx_info_rows:
                     if i[1] == idx_name:
                         is_unique = bool(i[2])
                 cols_rows = conn.execute(f"PRAGMA index_info({idx_name})").fetchall()
                 cols = [c[2] for c in cols_rows]
                 actual_indexes[idx_name] = {"table": tbl_name, "unique": is_unique, "columns": cols}
                 
        expected_idx_names = set(expected_indexes.keys())
        actual_idx_names = set(actual_indexes.keys())
        
        missing_idx = expected_idx_names - actual_idx_names
        extra_idx = actual_idx_names - expected_idx_names
        
        if missing_idx:
            result.errors.append(f"Missing explicit named indexes: {missing_idx}")
        if extra_idx:
            result.errors.append(f"Unexpected extra named indexes: {extra_idx}")
            
        for idx_name in expected_idx_names.intersection(actual_idx_names):
             expected_meta = expected_indexes[idx_name]
             actual_meta = actual_indexes[idx_name]
             if expected_meta["unique"] != actual_meta["unique"]:
                 result.errors.append(f"Index {idx_name} uniqueness mismatch: expected {expected_meta['unique']}, got {actual_meta['unique']}")
             if expected_meta["columns"] != actual_meta["columns"]:
                 result.errors.append(f"Index {idx_name} columns mismatch: expected {expected_meta['columns']}, got {actual_meta['columns']}")
                
        # Foreign Keys are not used in Phase 1 canonical shape, so state explicitly if expected_fks populated
        if expected_fks:
             result.errors.append("Foreign keys are not supported in Phase 1 strict canonical schema validation yet.")

        if not result.errors:
            result.valid = True
            result.status = "exact_match"
        else:
            result.status = "invalid_shape"

        return result
