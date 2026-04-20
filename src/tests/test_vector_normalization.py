from pathlib import Path
from unittest.mock import patch

from src.infra.adapters.vector_store import VectorStore, _normalize_embedding_batch


class FakeTensor:
    def __init__(self, value):
        self.value = value

    def cpu(self):
        return self

    def tolist(self):
        return self.value


class FakeNumpyArray:
    def __init__(self, value):
        self.value = value

    def tolist(self):
        return self.value


class FakeEmbedder:
    def __init__(self, value):
        self.value = value

    def encode(self, *_args, **_kwargs):
        return self.value


class FakeCollection:
    def __init__(self):
        self.upsert_calls = []
        self.query_calls = []

    def upsert(self, **kwargs):
        self.upsert_calls.append(kwargs)

    def query(self, **kwargs):
        self.query_calls.append(kwargs)
        return {
            'documents': [['doc']],
            'metadatas': [[{'kind': 'fact'}]],
            'distances': [[0.1]],
            'ids': [['id-1']],
        }


def _build_store(tmp_path):
    with patch.object(VectorStore, '_init_db', lambda self: None):
        store = VectorStore(persist_dir=str(tmp_path / 'project'))
    store._initialized = True
    store.collection = FakeCollection()
    return store


def test_normalize_embedding_batch_accepts_python_lists():
    assert _normalize_embedding_batch([[0.1, 0.2], [0.3, 0.4]]) == [[0.1, 0.2], [0.3, 0.4]]


def test_normalize_embedding_batch_accepts_tensor_like_values():
    assert _normalize_embedding_batch(FakeTensor([[0.1, 0.2]])) == [[0.1, 0.2]]


def test_normalize_embedding_batch_accepts_numpy_like_values():
    assert _normalize_embedding_batch(FakeNumpyArray([[0.1, 0.2]])) == [[0.1, 0.2]]


def test_similarity_search_accepts_list_embeddings_without_cpu(tmp_path):
    store = _build_store(tmp_path)
    store.embedder = FakeEmbedder([[0.25, 0.75]])

    out = store.similarity_search('scope summary', k=1)

    assert out and out[0]['id'] == 'id-1'
    assert store.collection.query_calls[0]['query_embeddings'] == [[0.25, 0.75]]


def test_add_texts_accepts_tensor_like_embeddings(tmp_path):
    store = _build_store(tmp_path)
    store.embedder = FakeEmbedder(FakeTensor([[0.5, 0.6]]))

    ok = store.add_texts(['scope item'], [{'kind': 'fact'}], ['id-1'])

    assert ok is True
    assert store.collection.upsert_calls[0]['embeddings'] == [[0.5, 0.6]]



def test_normalize_embedding_batch_accepts_tensor_row():
    assert _normalize_embedding_batch(FakeTensor([0.1, 0.2])) == [[0.1, 0.2]]


def test_normalize_embedding_batch_accepts_tensor_batch():
    assert _normalize_embedding_batch(FakeTensor([[0.1, 0.2], [0.3, 0.4]])) == [[0.1, 0.2], [0.3, 0.4]]


def test_normalize_embedding_batch_accepts_list_of_tensor_rows():
    raw = [FakeTensor([0.1, 0.2]), FakeTensor([0.3, 0.4])]
    assert _normalize_embedding_batch(raw) == [[0.1, 0.2], [0.3, 0.4]]


def test_normalize_embedding_batch_accepts_numpy_like_row_and_batch():
    assert _normalize_embedding_batch(FakeNumpyArray([0.1, 0.2])) == [[0.1, 0.2]]
    assert _normalize_embedding_batch(FakeNumpyArray([[0.1, 0.2], [0.3, 0.4]])) == [[0.1, 0.2], [0.3, 0.4]]
