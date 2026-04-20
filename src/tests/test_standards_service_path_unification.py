from __future__ import annotations

from pathlib import Path

from src.application.services.global_knowledge_service import GlobalKnowledgeService
from src.compliance.standard_enricher import StandardEnricher
from src.compliance.standards_db import StandardsDatabase
from src.compliance.standards_db_initializer import global_db_path as legacy_global_db_path
from src.compliance.standards_service import StandardsService
from src.infra.persistence.global_db_initializer import global_db_path


def test_standards_service_uses_canonical_global_db(tmp_path, monkeypatch):
    monkeypatch.setenv('SERAPEUM_APP_ROOT', str(tmp_path))
    expected = global_db_path()
    svc = StandardsService()
    assert svc.db_path == expected


def test_standard_enricher_uses_same_canonical_global_db(tmp_path, monkeypatch):
    monkeypatch.setenv('SERAPEUM_APP_ROOT', str(tmp_path))
    expected = global_db_path()
    enricher = StandardEnricher()
    assert enricher.svc.db_path == expected


def test_legacy_standards_database_defaults_to_canonical_global_db(tmp_path, monkeypatch):
    monkeypatch.setenv('SERAPEUM_APP_ROOT', str(tmp_path))
    expected = global_db_path()
    db = StandardsDatabase()
    assert str(Path(db.db_path).resolve()) == str(Path(expected).resolve())


def test_legacy_initializer_resolves_to_canonical_global_db(tmp_path, monkeypatch):
    monkeypatch.setenv('SERAPEUM_APP_ROOT', str(tmp_path))
    assert legacy_global_db_path() == global_db_path()


def test_global_knowledge_service_delegates_to_bound_db():
    class DummyDB:
        def search_standards(self, query, limit=5):
            return [{'query': query, 'limit': limit}]

    svc = GlobalKnowledgeService(db=DummyDB())
    assert svc.search_standards('fire', limit=3) == [{'query': 'fire', 'limit': 3}]



def test_seed_from_json_writes_to_canonical_global_db(tmp_path, monkeypatch):
    import json
    import sqlite3
    from src.compliance.standards_db_initializer import seed_from_json

    monkeypatch.setenv("SERAPEUM_APP_ROOT", str(tmp_path))
    payload = {
        "standards": [{"id": 101, "name": "NFPA 101", "region": "US", "meta": {"source": "seed"}}],
        "clauses": [{"id": 201, "standard_id": 101, "path": "1.1", "text": "Means of egress", "meta": {"title": "Intro"}}],
    }
    json_path = tmp_path / "seed.json"
    json_path.write_text(json.dumps(payload), encoding="utf-8")

    db_path = global_db_path()
    added = seed_from_json(str(json_path), app_root=str(tmp_path))
    assert added == 2

    conn = sqlite3.connect(db_path)
    try:
        std_count = conn.execute("SELECT COUNT(*) FROM standards WHERE id = 101").fetchone()[0]
        clause_count = conn.execute("SELECT COUNT(*) FROM clauses WHERE id = 201").fetchone()[0]
    finally:
        conn.close()

    assert std_count == 1
    assert clause_count == 1
