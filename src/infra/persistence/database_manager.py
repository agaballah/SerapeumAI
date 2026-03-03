# -*- coding: utf-8 -*-
# Copyright (c) 2025 Ahmed Gaballa
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
DatabaseManager — Pure SQLite (DB-A Recommended)
Fully compatible with ProjectService + Pipeline + Vision + UI.

Key points:
- One SQLite file per project folder (DB lives under the project root).
- Optional project_id used to customize DB file name.
- list_documents supports limit + offset for AnalysisEngine pagination.

Block-level RAG support:
- doc_blocks table to store semantic blocks (heading + body).
- doc_blocks_fts FTS5 index for fast block-level search.
- helper methods:
    * insert_doc_blocks(...)
    * search_doc_blocks(...)

FORTIFIED (SQLite locking resilience):
- Consistent per-connection PRAGMAs:
    * busy_timeout
    * journal_mode=WAL
    * synchronous=NORMAL
    * foreign_keys=ON
    * wal_autocheckpoint
- Thread-local connection pooling so execute()+commit() semantics work reliably.
- transaction() uses BEGIN IMMEDIATE by default to acquire write intent early.
"""

import os
import sqlite3
import threading
import logging
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple

from src.domain.models.page_record import PageRecord
from src.domain.models.relationship_types import EntityType, RelationshipType


DB_NAME = "serapeum.sqlite3"
logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Database manager with thread-local connection pooling.
    Each thread gets its own connection that persists for the thread's lifetime.
    """

    def __init__(
        self,
        *args,
        root_dir: str = None,
        project_id: Optional[str] = None,
        db_name: Optional[str] = None,
        migrations_dir: Optional[str] = None,
    ):
        """
        root_dir       : folder where the DB file lives
        project_id     : logical project id (optional)
        db_name        : explicit file name
        migrations_dir : optional custom folder for .sql migrations
        """
        self.migrations_dir = migrations_dir
        # Backwards-compat: allow positional single arg as a DB file path or root dir
        if args and not root_dir:
            first = args[0]
            try:
                first = str(first)
            except Exception:
                first = None

            if first:
                base = os.path.basename(first)
                dirn = os.path.dirname(first) or os.getcwd()
                if os.path.splitext(base)[1]:
                    # caller passed a full file path
                    root_dir = dirn
                    db_name = base
                else:
                    # treat as root dir
                    root_dir = first

        if not root_dir:
            raise ValueError("root_dir must be provided")

        os.makedirs(root_dir, exist_ok=True)
        self.root_dir = os.path.abspath(root_dir)

        if db_name is None:
            if project_id:
                safe_pid = "".join(
                    c if c.isalnum() or c in ("-", "_") else "_" for c in project_id
                )
                db_name = f"serapeum_{safe_pid}.sqlite3"
            else:
                db_name = DB_NAME

        if db_name == ":memory:":
            self.db_path = ":memory:"
        else:
            self.db_path = os.path.join(self.root_dir, db_name)

        # Thread-local storage for connections
        self._local = threading.local()

        # Current transaction connection is now stored in self._local.tx_conn

        # Global lock for multi-statement write operations (blocks, BIM, schedule)
        self._lock = threading.Lock()

        # Tunables
        self._timeout_seconds: int = 30
        self._busy_timeout_ms: int = 30_000  # explicit PRAGMA; Python timeout already helps too
        self._wal_autocheckpoint: int = 1000

        self._init_db()

    # --------------------------------------------------------------
    # Global Standards / Codes (Shared Layer)
    # --------------------------------------------------------------

    def search_standards(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search for relevant clauses in the standards database.
        Note: This expects to be called on a Global DB instance.
        """
        # Simple keyword search on clauses and standards
        sql = """
            SELECT
                c.id as clause_id,
                s.name as standard_title,
                s.id as standard_id,
                c.path,
                c.text
            FROM clauses c
            JOIN standards s ON c.standard_id = s.id
            WHERE c.text LIKE ? OR s.name LIKE ?
            LIMIT ?
        """
        search = f"%{query}%"
        rows = self.execute(sql, (search, search, limit)).fetchall()
        return [dict(r) for r in rows]

    def get_standard(self, standard_id: int) -> Optional[Dict[str, Any]]:
        row = self.execute("SELECT * FROM standards WHERE id = ?", (standard_id,)).fetchone()
        return dict(row) if row else None

    # --------------------------------------------------------------
    # Connection Management
    # --------------------------------------------------------------

    def _configure_connection(self, conn: sqlite3.Connection) -> None:
        """
        Apply consistent connection settings to reduce SQLITE_BUSY and improve concurrency.
        Must be called for every new connection.
        """
        conn.row_factory = sqlite3.Row
        try:
            # Important: foreign keys are per-connection in SQLite
            conn.execute("PRAGMA foreign_keys=ON")

            # WAL improves concurrency (readers don't block writers)
            conn.execute("PRAGMA journal_mode=WAL")

            # WAL + NORMAL is a common performance/durability balance
            conn.execute("PRAGMA synchronous=NORMAL")

            # Explicit busy timeout (ms). Python's timeout also sets a busy handler,
            # but we keep this for clarity/consistency.
            conn.execute(f"PRAGMA busy_timeout={int(self._busy_timeout_ms)}")

            # Keep WAL file from growing without bound
            conn.execute(f"PRAGMA wal_autocheckpoint={int(self._wal_autocheckpoint)}")
        except Exception:
            # Never fail startup due to a PRAGMA on odd FS / permissions.
            pass

    def _open_new_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=self._timeout_seconds)
        self._configure_connection(conn)
        return conn

    def _get_connection(self) -> sqlite3.Connection:
        """
        Thread-local pooled connection.
        - If inside db.transaction(): reuse the transaction connection.
        - Else: reuse a per-thread pooled connection so execute()+commit() work correctly.
        """
        tx_conn = getattr(self._local, "tx_conn", None)
        if tx_conn is not None:
            return tx_conn

        conn = getattr(self._local, "conn", None)
        if conn is not None:
            return conn

        conn = self._open_new_connection()
        self._local.conn = conn
        return conn

    def get_connection(self) -> sqlite3.Connection:
        """Public alias for tool compatibility."""
        return self._get_connection()

    def close_connection(self) -> None:
        """
        Close the current thread's pooled connection.
        Call this at thread end (worker shutdown / app exit).
        """
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
            self._local.conn = None

    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """
        Execute a SQL statement and return cursor.
        This uses the pooled connection, so caller can fetch and/or call commit().
        """
        conn = self._get_connection()
        return conn.execute(query, params)

    def execute_script(self, sql_script: str) -> sqlite3.Cursor:
        conn = self._get_connection()
        return conn.executescript(sql_script)

    def commit(self) -> None:
        """Commit on the current thread's pooled connection (or active transaction conn)."""
        conn = self._get_connection()
        conn.commit()

    def rollback(self) -> None:
        """Rollback on the current thread's pooled connection (or active transaction conn)."""
        conn = self._get_connection()
        conn.rollback()

    @contextmanager
    def transaction(self, *, immediate: bool = True):
        """
        Context manager for atomic transactions.
        """
        conn = self._get_connection()
        # Use thread-local to avoid cross-thread transaction leakage
        self._local.tx_conn = conn
        try:
            if immediate:
                try:
                    conn.execute("BEGIN IMMEDIATE")
                except Exception:
                    # If BEGIN IMMEDIATE fails, fall back to default deferred transaction.
                    pass
            yield conn
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            raise
        finally:
            self._local.tx_conn = None

    # --------------------------------------------------------------
    # Internal Helpers (legacy-compatible)
    # --------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        """Legacy method - returns pooled connection."""
        return self._get_connection()

    def _exec(self, sql: str, params: Tuple = ()) -> None:
        """
        Execute a single statement with auto-commit, unless inside db.transaction().
        """
        conn = self._get_connection()
        in_tx = getattr(self._local, "tx_conn", None) is not None
        conn.execute(sql, params)
        if not in_tx:
            conn.commit()

    def _query(self, sql: str, params: Tuple = ()) -> List[sqlite3.Row]:
        conn = self._get_connection()
        cur = conn.execute(sql, params)
        return cur.fetchall()

    def _query_one(self, sql: str, params: Tuple = ()) -> Optional[sqlite3.Row]:
        cur = self._get_connection().execute(sql, params)
        return cur.fetchone()

    def _ts(self) -> int:
        import time
        return int(time.time())

    # --------------------------------------------------------------
    # Schema / Migrations
    # --------------------------------------------------------------

    def _init_db(self) -> None:
        """
        Initialize database using versioned SQL migrations.
        Automatically discovers and applies all .sql files in the migrations directory.
        """
        conn = sqlite3.connect(self.db_path, timeout=self._timeout_seconds)
        try:
            self._configure_connection(conn)

            # 1) Ensure version tracking table exists
            conn.execute(
                "CREATE TABLE IF NOT EXISTS schema_version ("
                "version INTEGER PRIMARY KEY, "
                "applied_at DATETIME DEFAULT CURRENT_TIMESTAMP)"
            )
            conn.commit()

            # 2) Get applied versions
            applied = {
                row[0]
                for row in conn.execute("SELECT version FROM schema_version").fetchall()
            }

            # 3) Discover migration files
            m_dir = self.migrations_dir or os.path.join(os.path.dirname(__file__), "migrations")
            if not os.path.exists(m_dir):
                logger.debug(f"Migrations directory not found (skipping): {m_dir}")
                return

            migration_files = sorted(
                [f for f in os.listdir(m_dir) if f.endswith(".sql")]
            )

            for filename in migration_files:
                try:
                    version = int(filename.split("_")[0])
                except Exception:
                    continue

                if version in applied:
                    continue

                logger.info(f"Applying migration {filename} (v{version})...")
                path = os.path.join(m_dir, filename)
                with open(path, "r", encoding="utf-8") as f:
                    sql = f.read()

                try:
                    conn.executescript(sql)
                    conn.execute(
                        "INSERT OR IGNORE INTO schema_version (version) VALUES (?)",
                        (version,),
                    )
                    conn.commit()
                    logger.info(f"✓ Migration {filename} applied successfully.")
                except Exception as e:
                    logger.error(f"Failed to apply migration {filename}: {e}")
                    raise

            # 4) Perform legacy FTS sync if needed
            self._ensure_fts_sync(conn)
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def _ensure_fts_sync(self, conn: sqlite3.Connection) -> None:
        """Populate FTS if empty but data exists (safe baseline)."""
        try:
            count = conn.execute("SELECT count(*) FROM documents_fts").fetchone()[0]
            if count == 0:
                conn.execute(
                    "INSERT INTO documents_fts(doc_id, content_text) "
                    "SELECT doc_id, content_text FROM documents WHERE content_text IS NOT NULL"
                )
                conn.commit()
        except Exception:
            pass

    # --------------------------------------------------------------
    # KV Store (single canonical implementation)
    # --------------------------------------------------------------

    def set_kv(self, key: str, value: Any) -> None:
        """Store a JSON-serializable value in the kv table."""
        import json as _json
        val_json = _json.dumps(value, ensure_ascii=False)
        now = self._ts()
        # Prefer updated_at if schema has it; otherwise fallback to simple kv
        try:
            self._exec(
                "INSERT OR REPLACE INTO kv (key, value_json, updated_at) VALUES (?, ?, ?)",
                (key, val_json, now),
            )
        except Exception:
            self._exec(
                "INSERT INTO kv(key, value_json) VALUES(?,?) "
                "ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json",
                (key, val_json),
            )

    def get_kv(self, key: str, default: Any = None) -> Any:
        row = self._query_one("SELECT value_json FROM kv WHERE key=?", (key,))
        if not row:
            return default
        import json as _json
        try:
            return _json.loads(row["value_json"])
        except Exception:
            return row["value_json"] if "value_json" in row.keys() else default

    # --------------------------------------------------------------
    # Pages
    # --------------------------------------------------------------

    def upsert_page(self, page: PageRecord) -> None:
        """
        Structured page upsert using PageRecord dataclass.
        Handles nested dictionaries and automatic timestamp updates.
        """
        import json as _json
        p_dict = page.to_dict()

        fields = list(p_dict.keys())
        values = list(p_dict.values())

        processed_values: List[Any] = []
        for v in values:
            if isinstance(v, (dict, list)):
                processed_values.append(_json.dumps(v, ensure_ascii=False))
            else:
                processed_values.append(v)

        placeholders = ",".join(["?"] * len(fields))
        update_set = ",".join(
            [f"{f}=excluded.{f}" for f in fields if f not in ["doc_id", "page_index"]]
        )

        sql = f"""
            INSERT INTO pages ({",".join(fields)})
            VALUES ({placeholders})
            ON CONFLICT(doc_id, page_index) DO UPDATE SET
                {update_set}
        """
        self._exec(sql, tuple(processed_values))

    def get_page(self, doc_id: str, page_index: int) -> Optional[Dict[str, Any]]:
        row = self._query_one(
            "SELECT * FROM pages WHERE doc_id=? AND page_index=?",
            (doc_id, page_index),
        )
        return dict(row) if row else None

    def list_pages(self, doc_id: str) -> List[Dict[str, Any]]:
        rows = self._query(
            "SELECT * FROM pages WHERE doc_id=? ORDER BY page_index ASC",
            (doc_id,),
        )
        return [dict(r) for r in rows]

    def save_page_caption(self, doc_id: str, page_index: int, caption: Dict[str, Any]) -> None:
        import json as _json

        js = _json.dumps(caption, ensure_ascii=False)

        # Merge with existing safely (avoid duplicate kwargs for doc_id/page_index)
        existing = self.get_page(doc_id, page_index) or {}
        existing.pop("doc_id", None)
        existing.pop("page_index", None)

        p = PageRecord(doc_id=doc_id, page_index=page_index, **existing)
        p.caption_json = js
        self.upsert_page(p)

    # --------------------------------------------------------------
    # VLM Audit Trail
    # --------------------------------------------------------------

    def log_vlm_call(
        self,
        *,
        task_type: str,
        system_prompt: str,
        user_prompt: str,
        response_raw: str,
        duration_ms: int,
        model: str,
        status: str = "success",
        error_msg: Optional[str] = None,
    ) -> None:
        self._exec(
            """
            INSERT INTO vlm_audit_trail
                (task_type, system_prompt, user_prompt, response_raw, duration_ms, model, status, error_msg)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            (task_type, system_prompt, user_prompt, response_raw, duration_ms, model, status, error_msg),
        )

    # --------------------------------------------------------------
    # Vision Queue Management (v2 - SQL-based)
    # --------------------------------------------------------------

    def enqueue_vision_page(self, doc_id: str, page_index: int, priority: int = 0) -> None:
        """Add a page to the vision processing queue."""
        sql = """
            INSERT OR IGNORE INTO vision_queue (doc_id, page_index, priority, status, created_at)
            VALUES (?, ?, ?, 'queued', ?)
        """
        self._exec(sql, (doc_id, page_index, priority, self._ts()))

    def pop_vision_queue_batch(self, limit: int = 1) -> List[Dict[str, Any]]:
        """
        Pop a batch of pages from the queue.
        Marks them as 'processing' atomically using BEGIN IMMEDIATE.
        """
        batch = []
        with self._lock, self.transaction(immediate=True) as conn:
            # Query next items
            sql_select = """
                SELECT queue_id, doc_id, page_index 
                FROM vision_queue 
                WHERE status = 'queued' 
                ORDER BY priority DESC, created_at ASC 
                LIMIT ?
            """
            rows = conn.execute(sql_select, (limit,)).fetchall()
            
            if not rows:
                return []
                
            ids = [row["queue_id"] for row in rows]
            placeholders = ",".join("?" * len(ids))
            
            # Mark as processing
            sql_update = f"UPDATE vision_queue SET status = 'processing' WHERE queue_id IN ({placeholders})"
            conn.execute(sql_update, tuple(ids))
            
            batch = [dict(r) for r in rows]
            
        return batch

    def update_vision_queue_status(self, queue_id: int, status: str, error: Optional[str] = None) -> None:
        """Update status or remove from queue if successful."""
        if status == "done":
            self._exec("DELETE FROM vision_queue WHERE queue_id = ?", (queue_id,))
        else:
            self._exec("UPDATE vision_queue SET status = ?, retry_count = retry_count + 1 WHERE queue_id = ?", (status, queue_id))

    # --------------------------------------------------------------
    # Document CRUD
    # --------------------------------------------------------------

    def upsert_project(self, *, project_id: str, name: str, root: str) -> None:
        self._exec(
            """
            INSERT INTO projects(project_id, name, root, created, updated)
            VALUES(?,?,?,?,?)
            ON CONFLICT(project_id) DO UPDATE SET
                name=excluded.name,
                root=excluded.root,
                updated=excluded.updated
            """,
            (project_id, name, root, self._ts(), self._ts()),
        )

    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        row = self._query_one("SELECT * FROM projects WHERE project_id=?", (project_id,))
        return dict(row) if row else None

    def upsert_document(
        self,
        *,
        doc_id: str,
        project_id: str,
        file_name: str,
        rel_path: str,
        abs_path: str,
        file_ext: str,
        created: int,
        updated: int,
        meta_json: str = "{}",
        content_text: str = "",
        file_hash: Optional[str] = None,
        file_size: Optional[int] = None,
        file_mtime: Optional[float] = None,
        doc_title: Optional[str] = None,
        doc_type: Optional[str] = "general_document",
    ) -> None:
        self._exec(
            """
            INSERT INTO documents(
                doc_id, project_id, file_name, rel_path, abs_path, file_ext,
                created, updated, meta_json, content_text,
                file_hash, file_size, file_mtime, doc_title, doc_type
            )
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(doc_id) DO UPDATE SET
                updated=excluded.updated,
                meta_json=excluded.meta_json,
                content_text=excluded.content_text,
                file_hash=excluded.file_hash,
                file_size=excluded.file_size,
                file_mtime=excluded.file_mtime,
                doc_title=excluded.doc_title,
                doc_type=excluded.doc_type
            """,
            (
                doc_id,
                project_id,
                file_name,
                rel_path,
                abs_path,
                file_ext,
                created,
                updated,
                meta_json,
                content_text,
                file_hash,
                file_size,
                file_mtime,
                doc_title,
                doc_type,
            ),
        )

    def create_document(
        self,
        abs_path: str,
        project_id: str,
        file_name: str,
        rel_path: Optional[str] = None,
        doc_id: Optional[str] = None,
    ) -> str:
        """Convenience helper used by tests to create a minimal document record."""
        import uuid

        if not rel_path:
            rel_path = file_name
        if not doc_id:
            doc_id = uuid.uuid4().hex
        now = self._ts()
        ext = os.path.splitext(file_name)[1].lower()

        self.upsert_document(
            doc_id=doc_id,
            project_id=project_id,
            file_name=file_name,
            rel_path=rel_path,
            abs_path=abs_path,
            file_ext=ext,
            created=now,
            updated=now,
            meta_json="{}",
            content_text="",
        )
        return doc_id

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        row = self._query_one("SELECT * FROM documents WHERE doc_id=?", (doc_id,))
        return dict(row) if row else None

    def get_document_by_hash(self, project_id: str, rel_path: str, file_hash: str) -> Optional[Dict[str, Any]]:
        row = self._query_one(
            "SELECT * FROM documents WHERE project_id=? AND rel_path=? AND file_hash=?",
            (project_id, rel_path, file_hash),
        )
        return dict(row) if row else None

    def get_documents_batch(self, doc_ids: List[str]) -> List[Dict[str, Any]]:
        if not doc_ids:
            return []
        placeholders = ",".join("?" * len(doc_ids))
        sql = f"SELECT * FROM documents WHERE doc_id IN ({placeholders})"
        rows = self._query(sql, tuple(doc_ids))
        return [dict(row) for row in rows]

    def list_documents(
        self,
        project_id: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM documents"
        params: List[Any] = []
        where: List[str] = []

        if project_id:
            where.append("project_id=?")
            params.append(project_id)

        if where:
            sql += " WHERE " + " AND ".join(where)

        sql += " ORDER BY created ASC"

        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            params.extend([int(limit), int(offset or 0)])

        rows = self._query(sql, tuple(params))
        return [dict(r) for r in rows]

    def count_documents(self, project_id: Optional[str] = None) -> int:
        """Efficiently count documents in a project."""
        sql = "SELECT COUNT(*) as count FROM documents"
        params = []
        if project_id:
            sql += " WHERE project_id=?"
            params.append(project_id)
        
        row = self._query_one(sql, tuple(params))
        return int(row["count"]) if row else 0

    def search_documents(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        if not query.strip():
            return []

        sql = """
            SELECT
                d.doc_id,
                d.file_name,
                d.abs_path,
                snippet(documents_fts, 1, '<b>', '</b>', '...', 64) as snippet,
                bm25(documents_fts) as rank
            FROM documents_fts f
            JOIN documents d ON f.doc_id = d.doc_id
            WHERE documents_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """
        try:
            rows = self._query(sql, (query, limit))
            return [dict(r) for r in rows]
        except Exception:
            return []

    # --------------------------------------------------------------
    # Block-level CRUD / RAG support
    # --------------------------------------------------------------

    def insert_doc_blocks(
        self,
        doc_id: str,
        blocks: List[Dict[str, Any]],
        source_type: str = "pdf",
    ) -> None:
        """
        Replace all blocks for a document with the provided list.

        Expected block dict keys:
            - block_id        (str, required)
            - page_index      (int)
            - heading_title   (str or None)
            - heading_number  (str or None)
            - level           (int)
            - text            (str, required)
        """
        with self._lock, self.transaction(immediate=True) as conn:
            conn.execute("DELETE FROM doc_blocks WHERE doc_id=?", (doc_id,))

            if not blocks:
                return

            rows = []
            ts = self._ts()
            for b in blocks:
                block_id = str(b.get("block_id") or "")
                text = (b.get("text") or "").strip()
                if not block_id or not text:
                    continue

                rows.append(
                    (
                        doc_id,
                        block_id,
                        int(b.get("page_index") or 0),
                        b.get("heading_title"),
                        b.get("heading_number"),
                        int(b.get("level") or 0),
                        text,
                        source_type,
                        ts,
                    )
                )

            if rows:
                conn.executemany(
                    """
                    INSERT OR REPLACE INTO doc_blocks(
                        doc_id, block_id, page_index,
                        heading_title, heading_number, level,
                        text, source_type, created_at
                    )
                    VALUES (?,?,?,?,?,?,?,?,?)
                    """,
                    rows,
                )

    def search_doc_blocks(
        self,
        query: str,
        limit: int = 20,
        doc_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if not query.strip():
            return []

        base_sql = """
            SELECT
                b.doc_id       AS doc_id,
                b.block_id     AS block_id,
                b.page_index   AS page_index,
                b.heading_title,
                b.heading_number,
                b.level,
                b.text,
                bm25(doc_blocks_fts) AS rank
            FROM doc_blocks_fts
            JOIN doc_blocks b
              ON b.doc_id = doc_blocks_fts.doc_id
             AND b.block_id = doc_blocks_fts.block_id
            WHERE doc_blocks_fts MATCH ?
        """
        params: List[Any] = [query]

        if doc_id:
            base_sql += " AND b.doc_id = ?"
            params.append(doc_id)

        base_sql += " ORDER BY rank LIMIT ?"
        params.append(limit)

        try:
            rows = self._query(base_sql, tuple(params))
            return [dict(r) for r in rows]
        except Exception:
            return []

    # --------------------------------------------------------------
    # Analysis + Compliance
    # --------------------------------------------------------------

    def save_analysis(self, doc_id: str, payload: Dict[str, Any], ts: int) -> None:
        import json as _json
        self._exec(
            """
            INSERT INTO analysis(doc_id, payload_json, ts)
            VALUES(?,?,?)
            ON CONFLICT(doc_id) DO UPDATE SET
                payload_json=excluded.payload_json,
                ts=excluded.ts
            """,
            (doc_id, _json.dumps(payload, ensure_ascii=False), ts),
        )

    def get_analysis(self, doc_id: str) -> Optional[Dict[str, Any]]:
        row = self._query_one("SELECT payload_json FROM analysis WHERE doc_id=?", (doc_id,))
        if not row:
            return None
        import json as _json
        return _json.loads(row["payload_json"])

    def save_compliance(self, doc_id: str, payload: Dict[str, Any], ts: int) -> None:
        import json as _json
        self._exec(
            """
            INSERT INTO compliance(doc_id, payload_json, ts)
            VALUES(?,?,?)
            ON CONFLICT(doc_id) DO UPDATE SET
                payload_json=excluded.payload_json,
                ts=excluded.ts
            """,
            (doc_id, _json.dumps(payload, ensure_ascii=False), ts),
        )

    def get_compliance(self, doc_id: str) -> Optional[Dict[str, Any]]:
        row = self._query_one("SELECT payload_json FROM compliance WHERE doc_id=?", (doc_id,))
        if not row:
            return None
        import json as _json
        return _json.loads(row["payload_json"])

    def get_document_payload(self, doc_id: str) -> Dict[str, Any]:
        """
        Helper to fetch aggregated text/content for a document.
        Used by ComplianceAnalyzer.
        """
        doc = self._query_one("SELECT content_text FROM documents WHERE doc_id=?", (doc_id,))
        native_text = (doc["content_text"] if doc else "") or ""

        pages = self.list_pages(doc_id)
        pages.sort(key=lambda p: p.get("page_index", 0))
        ocr_text = "\n\n".join(p.get("ocr_text") or "" for p in pages)

        vision_segments: List[str] = []
        for p in pages:
            v = (p.get("vision_detailed") or "").strip()
            if v and len(v) > 10:
                vision_segments.append(f"[Page {int(p.get('page_index', 0)) + 1} Vision]: {v}")
        vision_text = "\n\n".join(vision_segments) if vision_segments else ""

        full_text = native_text
        if vision_text:
            full_text += "\n\n--- VISION CONTENT ---\n\n" + vision_text
        if ocr_text:
            full_text += "\n\n--- OCR CONTENT ---\n\n" + ocr_text

        # Analysis Results (optional)
        try:
            import json as _json
            ar_row = self._query_one(
                "SELECT result_json FROM analysis_results WHERE doc_id=? ORDER BY created_at DESC LIMIT 1",
                (doc_id,),
            )
            if ar_row and ar_row.get("result_json"):
                try:
                    ar_data = _json.loads(ar_row["result_json"])
                    ar_str = _json.dumps(ar_data, indent=2, ensure_ascii=False)
                    full_text += f"\n\n--- AI ANALYSIS SUMMARY ---\n\n{ar_str}"
                except Exception:
                    pass
        except Exception:
            pass

        return {"text": full_text, "page_count": len(pages)}

    # --------------------------------------------------------------
    # Chat Messages
    # --------------------------------------------------------------

    def save_chat_message(
        self,
        project_id: str,
        role: str,
        content: str,
        attachments: Optional[List[str]] = None,
    ) -> None:
        import json as _json
        att_json = _json.dumps(attachments or [])
        self._exec(
            """
            INSERT INTO chat_history (project_id, role, content, attachments_json)
            VALUES (?, ?, ?, ?)
            """,
            (project_id, role, content, att_json),
        )

    def get_chat_history(self, project_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        rows = self._query(
            """
            SELECT id, project_id, role, content, attachments_json, timestamp
            FROM chat_history
            WHERE project_id=?
            ORDER BY id ASC
            LIMIT ?
            """,
            (project_id, limit),
        )
        return [dict(r) for r in rows]

    # --------------------------------------------------------------
    # Graph Tables CRUD (Phase 2)
    # --------------------------------------------------------------

    def upsert_entity_node(self, project_id: str, doc_id: str, entity_type: Any, value: str) -> int:
        if isinstance(entity_type, EntityType):
            e_type = entity_type.value
        else:
            e_type = str(entity_type).lower()

        value = (value or "").strip()
        if not value:
            return -1

        row = self._query_one(
            "SELECT id FROM entity_nodes WHERE project_id=? AND entity_type=? AND value=? AND doc_id=?",
            (project_id, e_type, value, doc_id),
        )
        if row:
            return row["id"]

        try:
            self._exec(
                """
                INSERT INTO entity_nodes(project_id, doc_id, entity_type, value, created_ts)
                VALUES(?,?,?,?,?)
                """,
                (project_id, doc_id, e_type, value, self._ts()),
            )
            rid = self._query_one("SELECT last_insert_rowid() as id")
            return int(rid["id"]) if rid else -1
        except Exception:
            return -1

    def insert_link(self, project_id: str, from_kind: str, from_id: str, to_kind: str, to_id: str, link_type: str, confidence: float = 1.0) -> None:
        """
        Generic relationship linker (Phase 3 architecture).
        Used for XREFs, document linking, or cross-domain relationships.
        """
        import uuid
        link_id = uuid.uuid4().hex
        try:
            self._exec(
                """
                INSERT INTO links (link_id, project_id, from_kind, from_id, to_kind, to_id, link_type, confidence, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (link_id, project_id, from_kind, from_id, to_kind, to_id, link_type, confidence, self._ts()),
            )
        except Exception as e:
            # If already exists or error, handle gracefully
            logger.debug(f"[DatabaseManager] Could not insert link: {e}")

    def insert_entity_link(self, project_id: str, doc_id: str, src_id: int, dst_id: int, rel: Any) -> None:
        if src_id < 0 or dst_id < 0:
            return

        if isinstance(rel, RelationshipType):
            r_type = rel.value
        else:
            r_type = str(rel).lower()

        try:
            self._exec(
                """
                INSERT INTO entity_links(project_id, source_doc_id, from_entity_id, to_entity_id, rel_type, created_ts)
                VALUES(?,?,?,?,?,?)
                """,
                (project_id, doc_id, src_id, dst_id, r_type, self._ts()),
            )
        except Exception:
            pass

    def list_entities(self, project_id: str, entity_type: Optional[str] = None) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM entity_nodes WHERE project_id=?"
        params: List[Any] = [project_id]
        if entity_type:
            sql += " AND entity_type=?"
            params.append(entity_type)
        rows = self._query(sql, tuple(params))
        return [dict(r) for r in rows]

    def get_analysis_result(self, doc_id: str, result_type: str = "project_summary") -> Optional[Dict[str, Any]]:
        row = self._query_one(
            "SELECT result_json FROM analysis_results WHERE doc_id=? AND result_type=?",
            (doc_id, result_type),
        )
        if not row:
            return None
        import json as _json
        try:
            return _json.loads(row[0])
        except Exception:
            return {"raw": row[0]}

    # --------------------------------------------------------------
    # BIM Elements (Structured Data)
    # --------------------------------------------------------------

    def insert_bim_elements(self, doc_id: str, elements: List[Dict[str, Any]]) -> None:
        import json as _json

        with self._lock, self.transaction(immediate=True) as conn:
            conn.execute("DELETE FROM bim_elements WHERE doc_id=?", (doc_id,))
            if not elements:
                return

            rows = []
            ts = self._ts()
            for elem in elements:
                element_id = str(elem.get("element_id") or "")
                element_type = str(elem.get("element_type") or "")
                if not element_id or not element_type:
                    continue

                properties_json = _json.dumps(elem.get("properties", {}), ensure_ascii=False)
                spatial_relations_json = _json.dumps(elem.get("spatial_relations", []), ensure_ascii=False)

                rows.append(
                    (
                        doc_id,
                        element_id,
                        element_type,
                        elem.get("name"),
                        elem.get("level"),
                        properties_json,
                        spatial_relations_json,
                        ts,
                    )
                )

            if rows:
                conn.executemany(
                    """
                    INSERT INTO bim_elements(
                        doc_id, element_id, element_type, name, level,
                        properties_json, spatial_relations_json, created_at
                    )
                    VALUES (?,?,?,?,?,?,?,?)
                    """,
                    rows,
                )

    def query_bim_elements(
        self,
        doc_id: Optional[str] = None,
        element_type: Optional[str] = None,
        level: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM bim_elements WHERE 1=1"
        params: List[Any] = []
        if doc_id:
            sql += " AND doc_id=?"
            params.append(doc_id)
        if element_type:
            sql += " AND element_type=?"
            params.append(element_type)
        if level:
            sql += " AND level=?"
            params.append(level)
        sql += " LIMIT ?"
        params.append(limit)
        rows = self._query(sql, tuple(params))
        return [dict(r) for r in rows]

    def count_bim_elements(
        self,
        doc_id: Optional[str] = None,
        element_type: Optional[str] = None,
        level: Optional[str] = None,
    ) -> int:
        sql = "SELECT COUNT(*) as count FROM bim_elements WHERE 1=1"
        params: List[Any] = []
        if doc_id:
            sql += " AND doc_id=?"
            params.append(doc_id)
        if element_type:
            sql += " AND element_type=?"
            params.append(element_type)
        if level:
            sql += " AND level=?"
            params.append(level)
        row = self._query_one(sql, tuple(params))
        return int(row["count"]) if row else 0

    # --------------------------------------------------------------
    # PHASE 1 FORTIFICATION: Data Reconciliation & Resilience
    # --------------------------------------------------------------

    def log_conflict(
        self,
        conflict_id: str,
        doc_id: str,
        page_num: int,
        field_name: str,
        native_val: str,
        vlm_val: str,
        spatial_val: str,
        conflict_type: str,
        confidence: float,
    ) -> None:
        self._exec(
            """
            INSERT INTO data_conflicts
            (conflict_id, doc_id, page_num, field_name, native_value, vlm_value,
             spatial_value, conflict_type, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (conflict_id, doc_id, page_num, field_name, native_val, vlm_val, spatial_val, conflict_type, confidence),
        )

    def log_failed_extraction(
        self,
        failure_id: str,
        doc_id: str,
        page_num: int,
        stage: str,
        error_msg: str,
        error_type: str,
    ) -> None:
        self._exec(
            """
            INSERT INTO failed_extractions
            (failure_id, doc_id, page_num, stage, error_message, error_type, status)
            VALUES (?, ?, ?, ?, ?, ?, 'pending')
            ON CONFLICT(failure_id) DO UPDATE SET
                status = 'pending',
                failed_at = CURRENT_TIMESTAMP
            """,
            (failure_id, doc_id, page_num, stage, error_msg, error_type),
        )

    def log_failure_payload(self, failure_id: str, payload: Dict[str, Any]) -> None:
        import json as _json
        import gzip
        try:
            data = _json.dumps(payload, ensure_ascii=False).encode("utf-8")
            compressed = gzip.compress(data)
            self._exec(
                """
                INSERT OR REPLACE INTO failure_payloads (failure_id, payload_blob, size_bytes)
                VALUES (?, ?, ?)
                """,
                (failure_id, compressed, len(compressed)),
            )
        except Exception as e:
            logger.error(f"Failed to log failure payload: {e}")

    def get_failure_payload(self, failure_id: str) -> Optional[Dict[str, Any]]:
        import json as _json
        import gzip
        row = self._query_one("SELECT payload_blob FROM failure_payloads WHERE failure_id = ?", (failure_id,))
        if not row:
            return None
        try:
            decompressed = gzip.decompress(row["payload_blob"])
            return _json.loads(decompressed.decode("utf-8"))
        except Exception as e:
            logger.error(f"Failed to retrieve failure payload: {e}")
            return None

    def get_pending_failures(self) -> List[Dict]:
        rows = self._query(
            """
            SELECT * FROM failed_extractions
            WHERE status IN ('pending', 'retrying')
            ORDER BY next_retry_at ASC
            LIMIT 10
            """
        )
        return [dict(row) for row in rows]

    def update_extraction_accuracy(
        self,
        doc_type: str,
        source: str,
        total: int,
        correct: int,
        confidence_avg: float,
    ) -> None:
        from datetime import datetime
        period = datetime.now().strftime("%Y-%m")
        metric_id = f"{doc_type}_{source}_{period}"

        self._exec(
            """
            INSERT INTO extraction_accuracy
            (metric_id, document_type, data_source, total_samples, correct_samples,
             accuracy_percent, confidence_avg, period_start, period_end)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(document_type, data_source, period_start) DO UPDATE SET
                total_samples = total_samples + ?,
                correct_samples = correct_samples + ?,
                accuracy_percent = (CAST(correct_samples + ? AS REAL) /
                                   CAST(total_samples + ? AS REAL) * 100.0),
                confidence_avg = ?,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                metric_id,
                doc_type,
                source,
                total,
                correct,
                (100.0 * correct / total) if total > 0 else 0.0,
                confidence_avg,
                f"{period}-01",
                f"{period}-31",
                total,
                correct,
                correct,
                total,
                confidence_avg,
            ),
        )

    # --------------------------------------------------------------
    # Schedule Activities (Structured Data)
    # --------------------------------------------------------------

    def insert_schedule_activities(self, doc_id: str, activities: List[Dict[str, Any]]) -> None:
        import json as _json

        with self._lock, self.transaction(immediate=True) as conn:
            conn.execute("DELETE FROM schedule_activities WHERE doc_id=?", (doc_id,))
            if not activities:
                return

            rows = []
            ts = self._ts()
            for act in activities:
                activity_id = str(act.get("activity_id") or act.get("task_id") or "")
                if not activity_id:
                    continue

                properties = {
                    k: v
                    for k, v in act.items()
                    if k
                    not in [
                        "activity_id",
                        "task_id",
                        "activity_name",
                        "task_name",
                        "activity_code",
                        "task_code",
                        "start_date",
                        "finish_date",
                        "duration",
                        "is_critical",
                        "total_float",
                        "percent_complete",
                    ]
                }
                properties_json = _json.dumps(properties, ensure_ascii=False)

                rows.append(
                    (
                        doc_id,
                        activity_id,
                        act.get("activity_name") or act.get("task_name"),
                        act.get("activity_code") or act.get("task_code"),
                        act.get("start_date") or act.get("start"),
                        act.get("finish_date") or act.get("finish"),
                        float(act.get("duration", 0)) if act.get("duration") else None,
                        1 if act.get("is_critical") else 0,
                        float(act.get("total_float", 0)) if act.get("total_float") else None,
                        float(act.get("percent_complete", 0)) if act.get("percent_complete") else None,
                        properties_json,
                        ts,
                    )
                )

            if rows:
                conn.executemany(
                    """
                    INSERT INTO schedule_activities(
                        doc_id, activity_id, activity_name, activity_code,
                        start_date, finish_date, duration, is_critical,
                        total_float, percent_complete, properties_json, created_at
                    )
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    rows,
                )

    def query_schedule_activities(
        self,
        doc_id: Optional[str] = None,
        is_critical: Optional[bool] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM schedule_activities WHERE 1=1"
        params: List[Any] = []
        if doc_id:
            sql += " AND doc_id=?"
            params.append(doc_id)
        if is_critical is not None:
            sql += " AND is_critical=?"
            params.append(1 if is_critical else 0)
        sql += " ORDER BY start_date ASC LIMIT ?"
        params.append(limit)
        rows = self._query(sql, tuple(params))
        return [dict(r) for r in rows]

    def count_schedule_activities(
        self,
        doc_id: Optional[str] = None,
        is_critical: Optional[bool] = None,
    ) -> int:
        sql = "SELECT COUNT(*) as count FROM schedule_activities WHERE 1=1"
        params: List[Any] = []
        if doc_id:
            sql += " AND doc_id=?"
            params.append(doc_id)
        if is_critical is not None:
            sql += " AND is_critical=?"
            params.append(1 if is_critical else 0)
        row = self._query_one(sql, tuple(params))
        return int(row["count"]) if row else 0

    # --------------------------------------------------------------
    # Snapshot Management (SSOT §4 — Snapshot layer)
    # Snapshots are stored in the KV table to avoid schema migrations.
    # Key format: snapshot:{project_id}:latest → {snapshot_id, created_at, status}
    # --------------------------------------------------------------

    def get_latest_snapshot(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        Return the latest VALIDATED snapshot for a project, or None.
        Used by the chat layer to scope all fact queries to a coherent as-of state.
        """
        key = f"snapshot:{project_id}:latest"
        snap = self.get_kv(key)
        if snap and isinstance(snap, dict):
            return snap
        return None

    def create_snapshot(self, project_id: str, status: str = "VALIDATED") -> str:
        """
        Create a new snapshot for the project and store it as the latest.
        Returns the new snapshot_id.

        This should be called:
          - After BUILD_FACTS completes successfully
          - When the user manually requests a snapshot update
        """
        import uuid
        snapshot_id = f"snap_{project_id[:8]}_{uuid.uuid4().hex[:8]}"
        now = self._ts()

        payload = {
            "snapshot_id": snapshot_id,
            "project_id": project_id,
            "status": status,
            "created_at": now,
        }

        key = f"snapshot:{project_id}:latest"
        self.set_kv(key, payload)
        logger.info(f"[DatabaseManager] Created snapshot {snapshot_id} for project {project_id}")
        return snapshot_id

    def get_or_create_snapshot(self, project_id: str) -> str:
        """
        Return the latest snapshot_id, creating an initial one if none exists.
        Used by AgentOrchestrator at the start of every chat call.
        """
        snap = self.get_latest_snapshot(project_id)
        if snap:
            return snap["snapshot_id"]
        return self.create_snapshot(project_id, status="VALIDATED")
