# -*- coding: utf-8 -*-
"""
test_database_manager_storage_topology.py

Packet 1: Storage topology freeze.

Proves DatabaseManager canonicalizes normal SQLite DBs under the approved
symbolic .serapeum root without fragile directory-listing behavior.
"""

from pathlib import Path

from src.infra.persistence.database_manager import DatabaseManager


def _close(db: DatabaseManager) -> None:
    try:
        db.close_all_connections()
    except Exception:
        db.close_connection()


def test_root_dir_is_canonicalized_under_serapeum(tmp_path):
    project_root = tmp_path / "Project A"

    db = DatabaseManager(root_dir=str(project_root), db_name="project.sqlite3")
    try:
        expected_root = project_root / ".serapeum"
        assert Path(db.root_dir) == expected_root.resolve()
        assert Path(db.db_path) == expected_root.resolve() / "project.sqlite3"
        assert expected_root.exists()
    finally:
        _close(db)


def test_existing_serapeum_root_is_not_nested(tmp_path):
    serapeum_root = tmp_path / "Project A" / ".serapeum"

    db = DatabaseManager(root_dir=str(serapeum_root), db_name="project.sqlite3")
    try:
        assert Path(db.root_dir) == serapeum_root.resolve()
        assert Path(db.db_path) == serapeum_root.resolve() / "project.sqlite3"
        assert ".serapeum/.serapeum" not in db.db_path.replace("\\", "/")
    finally:
        _close(db)


def test_positional_project_db_file_is_localized_under_serapeum(tmp_path):
    project_root = tmp_path / "Project A"
    requested_db_path = project_root / "outside.sqlite3"

    db = DatabaseManager(str(requested_db_path))
    try:
        expected_root = project_root / ".serapeum"
        assert Path(db.root_dir) == expected_root.resolve()
        assert Path(db.db_path) == expected_root.resolve() / "outside.sqlite3"
    finally:
        _close(db)


def test_positional_serapeum_db_file_stays_under_serapeum(tmp_path):
    serapeum_root = tmp_path / "Project A" / ".serapeum"
    requested_db_path = serapeum_root / "inside.sqlite3"

    db = DatabaseManager(str(requested_db_path))
    try:
        assert Path(db.root_dir) == serapeum_root.resolve()
        assert Path(db.db_path) == serapeum_root.resolve() / "inside.sqlite3"
    finally:
        _close(db)


def test_memory_database_preserves_memory_path(tmp_path):
    db = DatabaseManager(root_dir=str(tmp_path), db_name=":memory:")
    try:
        assert db.db_path == ":memory:"
    finally:
        _close(db)
