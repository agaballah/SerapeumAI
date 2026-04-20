"""
standards_service.py

Read-only-ish access to the global standards knowledge base (SQLite).

Phase 3 Packet C contract:
- live standards/global lookups resolve through the canonical runtime global owner
- the canonical path is <APP_ROOT>/.serapeum/global.sqlite3
- legacy standards.sqlite3 callers are compatibility-only and must not act as a
  second equal authority
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.infra.persistence.global_db_initializer import (
    ensure_global_db as ensure_runtime_global_db,
    global_db_path as runtime_global_db_path,
)


def _resolve_db_path(explicit_db_path: Optional[str]) -> str:
    """Resolve the effective DB path against the canonical runtime global owner."""
    return str(explicit_db_path) if explicit_db_path else runtime_global_db_path()


@dataclass
class StandardsService:
    """
    Convenience wrapper around the standards SQLite DB.

    Expected tables:
      - standards(id, name, region, meta)
      - clauses(id, standard_id, path, text, meta)
      - mappings(clause_id, concept, meta)
      - xrefs(a, b, kind, meta)

    The schema is ensured on initialization (idempotent).
    """

    db_path: Optional[str] = None

    def __post_init__(self) -> None:
        self.db_path = _resolve_db_path(self.db_path)
        # Ensure the DB file + schema exist (safe to call repeatedly).
        ensure_runtime_global_db(self.db_path)

    def _connect(self) -> sqlite3.Connection:
        assert self.db_path is not None
        db_path = Path(self.db_path)

        # Make sure directory exists (especially for first run or custom env paths).
        db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def list_standards(self, region: Optional[str] = None) -> List[Dict[str, Any]]:
        sql = "SELECT id, name, region, meta FROM standards"
        params: List[Any] = []
        if region:
            sql += " WHERE region = ?"
            params.append(region)
        sql += " ORDER BY name"

        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()

        out: List[Dict[str, Any]] = []
        for r in rows:
            meta = r["meta"]
            out.append(
                {
                    "id": r["id"],
                    "name": r["name"],
                    "region": r["region"],
                    "meta": json.loads(meta) if meta else None,
                }
            )
        return out

    def list_clauses(self, standard_id: int, prefix: Optional[str] = None) -> List[Dict[str, Any]]:
        sql = "SELECT id, standard_id, path, text, meta FROM clauses WHERE standard_id = ?"
        params: List[Any] = [standard_id]
        if prefix:
            sql += " AND path LIKE ?"
            params.append(f"{prefix}%")
        sql += " ORDER BY path"

        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()

        out: List[Dict[str, Any]] = []
        for r in rows:
            meta = r["meta"]
            out.append(
                {
                    "id": r["id"],
                    "standard_id": r["standard_id"],
                    "path": r["path"],
                    "text": r["text"],
                    "meta": json.loads(meta) if meta else None,
                }
            )
        return out

    def get_clause(self, clause_id: int) -> Optional[Dict[str, Any]]:
        sql = "SELECT id, standard_id, path, text, meta FROM clauses WHERE id = ?"
        with self._connect() as conn:
            r = conn.execute(sql, (clause_id,)).fetchone()

        if not r:
            return None

        meta = r["meta"]
        return {
            "id": r["id"],
            "standard_id": r["standard_id"],
            "path": r["path"],
            "text": r["text"],
            "meta": json.loads(meta) if meta else None,
        }

    def list_mappings(self, clause_id: int) -> List[Dict[str, Any]]:
        sql = "SELECT clause_id, concept, meta FROM mappings WHERE clause_id = ? ORDER BY concept"
        with self._connect() as conn:
            rows = conn.execute(sql, (clause_id,)).fetchall()

        out: List[Dict[str, Any]] = []
        for r in rows:
            meta = r["meta"]
            out.append(
                {
                    "clause_id": r["clause_id"],
                    "concept": r["concept"],
                    "meta": json.loads(meta) if meta else None,
                }
            )
        return out

    def list_xref(self, clause_id: int) -> List[Dict[str, Any]]:
        """
        Return outbound xrefs from the given clause_id.
        """
        sql = """
        SELECT a, b, kind, meta
        FROM xrefs
        WHERE a = ?
        ORDER BY kind, b
        """
        with self._connect() as conn:
            rows = conn.execute(sql, (clause_id,)).fetchall()

        out: List[Dict[str, Any]] = []
        for r in rows:
            meta = r["meta"]
            out.append(
                {
                    "a": r["a"],
                    "b": r["b"],
                    "kind": r["kind"],
                    "meta": json.loads(meta) if meta else None,
                }
            )
        return out
