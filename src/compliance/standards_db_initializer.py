"""
standards_db_initializer.py

Owns the (idempotent) creation of the global standards SQLite DB.

This module is safe to import and call from multiple places:
- ensure_global_db(...) creates the file (if missing), creates tables (if missing),
  and creates indexes (if missing).

DB location resolution helper:
- global_db_path() resolves SERAPEUM_STANDARDS_DB if set, otherwise
  <APP_ROOT>/.serapeum/standards.sqlite3 where APP_ROOT defaults to CWD.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path


def _app_root() -> Path:
    # See standards_service._app_root for rationale.
    return Path(os.getcwd()).resolve()


def _normalize_db_path(raw: str) -> Path:
    """
    Normalize a DB path:
    - expands ~ and environment variables
    - resolves relative paths against APP_ROOT
    - if a directory (or endswith / or \\), appends 'standards.sqlite3'
    """
    if raw is None:
        raise ValueError("db path is None")

    s = os.path.expandvars(os.path.expanduser(str(raw).strip()))
    if not s:
        raise ValueError("db path is empty")

    if s.endswith(("/", "\\")):
        p = Path(s) / "standards.sqlite3"
    else:
        p = Path(s)

    if not p.is_absolute():
        p = _app_root() / p

    try:
        if p.exists() and p.is_dir():
            p = p / "standards.sqlite3"
    except OSError:
        pass

    return p.resolve()


def global_db_path() -> str:
    """
    Default global DB path, allowing an env override.

    Resolution (priority):
    1) SERAPEUM_STANDARDS_DB
    2) <APP_ROOT>/.serapeum/standards.sqlite3
    """
    env = os.getenv("SERAPEUM_STANDARDS_DB")
    if env and env.strip():
        return str(_normalize_db_path(env))
    return str((_app_root() / ".serapeum" / "standards.sqlite3").resolve())


def ensure_global_db(db_path: str) -> None:
    """
    Create the global standards DB file + tables + indexes, if missing.
    Safe to call multiple times.
    """
    p = _normalize_db_path(db_path)
    p.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(p))
    try:
        conn.execute("PRAGMA foreign_keys = ON;")

        # standards: top-level container
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS standards (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                region TEXT NOT NULL,
                meta TEXT
            );
            """
        )

        # clauses: hierarchical entries for a given standard
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS clauses (
                id INTEGER PRIMARY KEY,
                standard_id INTEGER NOT NULL,
                path TEXT NOT NULL,
                text TEXT NOT NULL,
                meta TEXT
            );
            """
        )

        # mappings: clause -> concept tags (for semantic lookup)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS mappings (
                clause_id INTEGER NOT NULL,
                concept TEXT NOT NULL,
                meta TEXT,
                PRIMARY KEY (clause_id, concept)
            );
            """
        )

        # xrefs: explicit relationships between clauses
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS xrefs (
                a INTEGER NOT NULL,
                b INTEGER NOT NULL,
                kind TEXT NOT NULL,
                meta TEXT,
                PRIMARY KEY (a, b, kind)
            );
            """
        )

        # Helpful indexes (safe even for existing DBs).
        conn.execute("CREATE INDEX IF NOT EXISTS idx_standards_region ON standards(region);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_clauses_standard_path ON clauses(standard_id, path);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_mappings_concept ON mappings(concept);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_mappings_clause ON mappings(clause_id);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_xrefs_a ON xrefs(a);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_xrefs_b ON xrefs(b);")

        conn.commit()
    finally:
        conn.close()
