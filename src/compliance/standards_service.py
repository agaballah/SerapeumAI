"""
standards_service.py

Read-only-ish access to the global standards knowledge base (SQLite).

DB location resolution (highest to lowest priority):
1) Explicit db_path passed to StandardsService(...)
2) Environment variable SERAPEUM_STANDARDS_DB
3) <APP_ROOT>/.serapeum/standards.sqlite3  where APP_ROOT defaults to the current working directory

Notes
- If SERAPEUM_STANDARDS_DB is set, it may point to a non-existent file; the directory will be created as needed.
- If SERAPEUM_STANDARDS_DB points to a directory (or ends with a path separator), 'standards.sqlite3' is used inside it.
"""

from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    # Package import
    from .standards_db_initializer import ensure_global_db
except ImportError:  # pragma: no cover
    # Script / local import fallback
    from standards_db_initializer import ensure_global_db


def _app_root() -> Path:
    """
    Returns the application root used for resolving relative DB paths.

    We intentionally default to the current working directory because this code
    may be imported as a library (where __file__ could be inside site-packages
    and not writable).
    """
    return Path(os.getcwd()).resolve()


def _normalize_db_path(raw: str) -> Path:
    """
    Normalizes a DB path:
    - expands ~ and environment variables
    - resolves relative paths against APP_ROOT
    - if a directory (or endswith / or \\), appends 'standards.sqlite3'
    """
    if raw is None:
        raise ValueError("db path is None")

    s = os.path.expandvars(os.path.expanduser(str(raw).strip()))
    if not s:
        raise ValueError("db path is empty")

    # If user provided a directory, place DB file inside it.
    if s.endswith(("/", "\\")):
        p = Path(s) / "standards.sqlite3"
    else:
        p = Path(s)

    if not p.is_absolute():
        p = _app_root() / p

    # If an existing path is a directory, also place DB file inside it.
    try:
        if p.exists() and p.is_dir():
            p = p / "standards.sqlite3"
    except OSError:
        # If the filesystem check fails (e.g., permissions), keep as-is.
        pass

    return p.resolve()


def _resolve_db_path(explicit_db_path: Optional[str]) -> str:
    """
    Resolve the effective DB path using the documented priority order.
    """
    if explicit_db_path:
        return str(_normalize_db_path(explicit_db_path))

    env = os.getenv("SERAPEUM_STANDARDS_DB")
    if env and env.strip():
        return str(_normalize_db_path(env))

    default_path = _app_root() / ".serapeum" / "standards.sqlite3"
    return str(default_path.resolve())


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
        ensure_global_db(self.db_path)

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
