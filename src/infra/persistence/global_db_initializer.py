"""
global_db_initializer.py

Owns the (idempotent) creation of the global Serapeum SQLite DB.
Contains standards, model benchmarks, and global preferences.
"""

from __future__ import annotations

import os
import sqlite3
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def _app_root() -> Path:
    env_root = os.environ.get("SERAPEUM_APP_ROOT", "").strip()
    if env_root:
        return Path(env_root).resolve()

    # Fallback to the installation root where the `src` folder lives.
    # This avoids cwd-sensitive global DB resolution when the mounted app
    # already has a real application root.
    return Path(__file__).resolve().parents[3]


def _normalize_db_path(raw: str, app_root: Optional[Path | str] = None) -> Path:
    if raw is None:
        raise ValueError("db path is None")

    s = os.path.expandvars(os.path.expanduser(str(raw).strip()))
    if not s:
        raise ValueError("db path is empty")

    if s.endswith(("/", "\\")):
        p = Path(s) / "global.sqlite3"
    else:
        p = Path(s)

    if not p.is_absolute():
        root = Path(app_root).resolve() if app_root else _app_root()
        p = root / p

    try:
        if p.exists() and p.is_dir():
            p = p / "global.sqlite3"
    except OSError:
        pass

    return p.resolve()


def global_db_path(app_root: Optional[Path | str] = None) -> str:
    """
    Default global DB path.
    Resolution: <APP_ROOT>/.serapeum/global.sqlite3
    """
    env = os.environ.get("SERAPEUM_GLOBAL_DB", "")
    if env and env.strip():
        return str(_normalize_db_path(env, app_root=app_root))

    root = Path(app_root).resolve() if app_root else _app_root()
    return str((root / ".serapeum" / "global.sqlite3").resolve())


def ensure_global_db(db_path: str, app_root: Optional[Path | str] = None) -> None:
    """
    Create the global DB file and apply migrations.
    """
    p = _normalize_db_path(db_path, app_root=app_root)
    p.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(p))
    try:
        conn.execute("PRAGMA foreign_keys = ON;")

        # Ensure schema_version table exists
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY, applied_at DATETIME DEFAULT CURRENT_TIMESTAMP)"
        )

        # Apply global migrations
        migrations_dir = Path(__file__).parent / "global_migrations"
        if migrations_dir.exists():
            migration_files = sorted(migrations_dir.glob("*.sql"))

            # Get current version
            row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
            current_version = row[0] if row and row[0] is not None else 0

            for m_file in migration_files:
                try:
                    v_str = m_file.name.split("_")[0]
                    v_num = int(v_str)
                    if v_num > current_version:
                        logger.info(f"Applying global migration {m_file.name} (v{v_num}).")
                        with open(m_file, "r", encoding="utf-8") as f:
                            sql = f.read()
                            conn.executescript(sql)

                        conn.execute(
                            "INSERT OR IGNORE INTO schema_version (version) VALUES (?)",
                            (v_num,),
                        )
                        conn.commit()
                        logger.info(f"✓ Global migration {m_file.name} applied.")
                except (ValueError, IndexError):
                    continue

        conn.commit()
    finally:
        conn.close()