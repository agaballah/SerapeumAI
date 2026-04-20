from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from src.application.services.rag_service import RAGService
from src.application.services.vision_vector_service import VisionVectorService
from src.infra.adapters.vector_store import VectorStore, resolve_vector_store_dir


class DummyDB:
    def __init__(self, root_dir: str):
        self.root_dir = root_dir


class DummyVectorStore:
    def __init__(self, persist_dir=None):
        self.persist_dir = persist_dir
        self._initialized = True


class DummyVectorStoreForRAG:
    captured = []

    def __init__(self, persist_dir=None):
        type(self).captured.append(persist_dir)
        self.persist_dir = persist_dir
        self._initialized = True

    def similarity_search(self, query, k=5, filter=None):
        return []


def test_resolve_vector_store_dir_defaults_to_app_root(tmp_path, monkeypatch):
    monkeypatch.setenv('SERAPEUM_APP_ROOT', str(tmp_path))
    expected = (tmp_path / '.serapeum' / 'vector_db').resolve()
    assert Path(resolve_vector_store_dir()).resolve() == expected


def test_resolve_vector_store_dir_localizes_project_root(tmp_path):
    expected = (tmp_path / '.serapeum' / 'vector_db').resolve()
    assert Path(resolve_vector_store_dir(str(tmp_path))).resolve() == expected


def test_resolve_vector_store_dir_preserves_existing_serapeum_root(tmp_path):
    serapeum_root = (tmp_path / '.serapeum').resolve()
    expected = serapeum_root / 'vector_db'
    assert Path(resolve_vector_store_dir(str(serapeum_root))).resolve() == expected


def test_default_vector_store_dir_is_not_legacy_cwd_authority(tmp_path, monkeypatch):
    app_root = tmp_path / 'app_root'
    app_root.mkdir()
    legacy_cwd = tmp_path / 'legacy_cwd'
    legacy_cwd.mkdir()

    monkeypatch.setenv('SERAPEUM_APP_ROOT', str(app_root))
    monkeypatch.chdir(legacy_cwd)

    resolved = Path(resolve_vector_store_dir()).resolve()
    legacy = (legacy_cwd / '.serapeum_vectors').resolve()

    assert resolved == (app_root / '.serapeum' / 'vector_db').resolve()
    assert resolved != legacy


def test_vector_store_is_scoped_per_canonical_path(monkeypatch, tmp_path):
    monkeypatch.setenv('SERAPEUM_APP_ROOT', str(tmp_path / 'app'))
    VectorStore._instances = {}

    with patch.object(VectorStore, '_init_db', lambda self: None):
        app_vs_1 = VectorStore(persist_dir=str(tmp_path / 'app'))
        app_vs_2 = VectorStore(persist_dir=str(tmp_path / 'app' / '.serapeum'))
        project_vs = VectorStore(persist_dir=str(tmp_path / 'project'))

    assert app_vs_1 is app_vs_2
    assert app_vs_1 is not project_vs
    assert Path(app_vs_1.persist_dir).name == 'vector_db'
    assert Path(project_vs.persist_dir).name == 'vector_db'


def test_vision_vector_service_binds_to_project_serapeum_root(tmp_path):
    db = DummyDB(str(tmp_path / 'project' / '.serapeum'))
    with patch('src.application.services.vision_vector_service.VectorStore', DummyVectorStore):
        svc = VisionVectorService(db)
    assert svc.vector_store.persist_dir == str(tmp_path / 'project' / '.serapeum')


def test_rag_service_binds_semantic_search_to_project_serapeum_root(tmp_path):
    db = DummyDB(str(tmp_path / 'project' / '.serapeum'))
    DummyVectorStoreForRAG.captured = []

    svc = RAGService(db=db)
    with patch('src.infra.adapters.vector_store.VectorStore', DummyVectorStoreForRAG):
        with patch.object(RAGService, '_retrieve_block_level_context', return_value=''):
            with patch.object(RAGService, '_retrieve_document_level_context', return_value=''):
                svc.retrieve_context('storage topology', limit=1)

    assert DummyVectorStoreForRAG.captured == [str(tmp_path / 'project' / '.serapeum')]
