"""
standards_db_initializer.py

Phase 3 Packet C compatibility wrapper. Legacy standards.sqlite3 callers are
redirected to the canonical runtime global owner at
<APP_ROOT>/.serapeum/global.sqlite3.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

from src.infra.persistence.global_db_initializer import (
    ensure_global_db as _ensure_runtime_global_db,
    global_db_path as _runtime_global_db_path,
)

Pathish = Union[str, Path]


def global_db_path(app_root: Optional[Pathish] = None) -> str:
    return _runtime_global_db_path(app_root=app_root)


def ensure_global_db(db_path: Optional[Pathish] = None, app_root: Optional[Pathish] = None) -> str:
    resolved = str(db_path) if db_path else _runtime_global_db_path(app_root=app_root)
    _ensure_runtime_global_db(resolved, app_root=app_root)
    return resolved



def seed_from_json(json_path: Pathish, app_root: Optional[Pathish] = None) -> int:
    """Compatibility seeding helper that writes into the canonical runtime global DB.

    Expects a JSON object with optional keys:
      - standards: list[dict]
      - clauses: list[dict]
    Returns the number of inserted/updated rows best-effort.
    """
    import json
    import sqlite3
    from pathlib import Path

    db_path = ensure_global_db(app_root=app_root)
    payload = json.loads(Path(json_path).read_text(encoding="utf-8"))
    standards = payload.get("standards") or []
    clauses = payload.get("clauses") or []
    inserted = 0

    conn = sqlite3.connect(db_path)
    try:
        for s in standards:
            meta = s.get("meta")
            if isinstance(meta, (dict, list)):
                meta = json.dumps(meta)
            conn.execute(
                "INSERT OR REPLACE INTO standards (id, name, region, meta) VALUES (?, ?, ?, ?)",
                (s.get("id"), s.get("name"), s.get("region"), meta),
            )
            inserted += 1

        for c in clauses:
            meta = c.get("meta")
            if isinstance(meta, (dict, list)):
                meta = json.dumps(meta)
            conn.execute(
                "INSERT OR REPLACE INTO clauses (id, standard_id, path, text, meta) VALUES (?, ?, ?, ?, ?)",
                (c.get("id"), c.get("standard_id"), c.get("path"), c.get("text"), meta),
            )
            inserted += 1

        conn.commit()
    finally:
        conn.close()
    return inserted
