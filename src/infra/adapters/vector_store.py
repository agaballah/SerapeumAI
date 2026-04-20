"""
vector_store.py — Local Vector Database Wrapper (The "Pinecone Mimic")
----------------------------------------------------------------------
Provides a simple interface for semantic search using ChromaDB (local)
and SentenceTransformer embeddings (CPU-friendly).

Features:
- Canonical vector-store localization under approved .serapeum roots only
- Global fallback store under <APP_ROOT>/.serapeum/vector_db
- Project-scoped stores under <PROJECT_ROOT>/.serapeum/vector_db
- Embedding generation using 'all-MiniLM-L6-v2' (384-d, fast)
- Hybrid-ready interface (add_texts, similarity_search)
"""

from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Constants
VECTOR_DB_FOLDER_NAME = "vector_db"
COLLECTION_NAME = "serapeum_knowledge"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def _infer_app_root() -> Path:
    """Infer the application root from runtime pinning or source layout."""
    env_root = os.environ.get("SERAPEUM_APP_ROOT", "").strip()
    if env_root:
        return Path(env_root).resolve()

    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "src").is_dir():
            return parent

    return Path.cwd().resolve()


def _canonical_serapeum_root(root: Optional[str | os.PathLike[str]] = None) -> Path:
    """
    Resolve a storage root to the approved .serapeum authority folder.

    Accepted inputs:
    - None -> <APP_ROOT>/.serapeum
    - <project_root> -> <project_root>/.serapeum
    - <project_root>/.serapeum -> unchanged
    - <db_file>.sqlite3 -> parent folder, then localized to .serapeum if needed
    """
    if root is None:
        return (_infer_app_root() / ".serapeum").resolve()

    candidate = Path(root).expanduser()
    if not candidate.is_absolute():
        candidate = (_infer_app_root() / candidate).resolve()
    else:
        candidate = candidate.resolve()

    if candidate.suffix.lower() == ".sqlite3":
        candidate = candidate.parent

    if candidate.name == ".serapeum":
        return candidate.resolve()

    return (candidate / ".serapeum").resolve()


def resolve_vector_store_dir(root: Optional[str | os.PathLike[str]] = None) -> str:
    """Return the canonical vector-store directory under an approved .serapeum root."""
    return str((_canonical_serapeum_root(root) / VECTOR_DB_FOLDER_NAME).resolve())


def _normalize_embedding_batch(raw: Any) -> List[List[float]]:
    """Normalize tensor/numpy/list embedding outputs to a Chroma-safe list-of-lists."""

    def _materialize(value: Any) -> Any:
        current = value
        if current is None:
            return None
        if isinstance(current, tuple):
            current = list(current)
        for attr in ("detach", "cpu", "numpy", "tolist"):
            if hasattr(current, attr):
                try:
                    current = getattr(current, attr)()
                except Exception:
                    pass
        if hasattr(current, "item") and not isinstance(current, (str, bytes, list, tuple, dict)):
            try:
                current = current.item()
            except Exception:
                pass
        if isinstance(current, tuple):
            current = list(current)
        return current

    def _is_list_like(value: Any) -> bool:
        return isinstance(value, list)

    def _coerce_scalar(value: Any) -> float:
        current = _materialize(value)
        if isinstance(current, list):
            if len(current) == 1:
                return _coerce_scalar(current[0])
            raise TypeError(f"Embedding scalar expected, got sequence: {current!r}")
        return float(current)

    def _normalize_row(row: Any) -> List[float]:
        current = _materialize(row)
        if current is None:
            return []
        if not isinstance(current, list):
            return [_coerce_scalar(current)]

        if len(current) == 1:
            first = _materialize(current[0])
            if isinstance(first, list) and not any(isinstance(_materialize(item), list) for item in first):
                current = first

        out: List[float] = []
        for item in current:
            materialized = _materialize(item)
            if isinstance(materialized, list):
                if not materialized:
                    continue
                if any(isinstance(_materialize(sub), list) for sub in materialized):
                    for sub in materialized:
                        out.extend(_normalize_row(sub))
                else:
                    out.extend(_normalize_row(materialized))
            else:
                out.append(_coerce_scalar(materialized))
        return out

    value = _materialize(raw)
    if value is None:
        return []
    if not isinstance(value, list):
        return [_normalize_row(value)]
    if not value:
        return []

    first = _materialize(value[0])
    if isinstance(first, list):
        return [_normalize_row(row) for row in value]

    return [_normalize_row(value)]



class VectorStore:
    _instances: Dict[str, "VectorStore"] = {}

    def __new__(cls, persist_dir: Optional[str] = None):
        resolved_dir = resolve_vector_store_dir(persist_dir)
        instance = cls._instances.get(resolved_dir)
        if instance is None:
            instance = super(VectorStore, cls).__new__(cls)
            cls._instances[resolved_dir] = instance
        return instance

    def __init__(self, persist_dir: Optional[str] = None):
        resolved_dir = resolve_vector_store_dir(persist_dir)
        if getattr(self, "_store_key", None) == resolved_dir and hasattr(self, "_initialized"):
            return

        self.persist_dir = resolved_dir
        self._store_key = resolved_dir
        self.client = None
        self.collection = None
        self.embedder = None
        self._initialized = False

        self._init_db()

    def _init_db(self):
        """Initialize ChromaDB client and Embedding model lazily."""
        try:
            import chromadb
            from sentence_transformers import SentenceTransformer

            # 1. Setup Embedding Model (Lazy Load) with dynamic GPU allocation
            # Check available VRAM and conditionally use GPU
            device = "cpu"  # Default to CPU
            try:
                from src.utils.hardware_utils import get_gpu_info
                gpu_info = get_gpu_info()

                # Require 2GB free VRAM for embeddings (conservative threshold)
                VRAM_THRESHOLD_MB = 2048

                from src.utils.hardware_utils import reserve_vram
                if gpu_info['available'] and reserve_vram(VRAM_THRESHOLD_MB):
                    device = "cuda"
                    logger.info(
                        f"Loading embedding model: {EMBEDDING_MODEL} on GPU "
                        f"({gpu_info['vram_free_mb']} MB free VRAM available)"
                    )
                else:
                    if gpu_info['available']:
                        logger.info(
                            f"Loading embedding model: {EMBEDDING_MODEL} on CPU "
                            f"(VRAM reserved or insufficient: {gpu_info['vram_free_mb']} MB)"
                        )
                    else:
                        logger.info(f"Loading embedding model: {EMBEDDING_MODEL} on CPU (no GPU detected)")
            except Exception as e:
                logger.warning(f"Failed to detect GPU, defaulting to CPU: {e}")

            self.embedder = SentenceTransformer(EMBEDDING_MODEL, device=device)

            # 2. Setup ChromaDB (telemetry disabled — no outbound PostHog traffic)
            os.makedirs(self.persist_dir, exist_ok=True)
            logger.info(f"Initializing Vector Store at {self.persist_dir}...")

            try:
                from chromadb.config import Settings
                self.client = chromadb.PersistentClient(
                    path=self.persist_dir,
                    settings=Settings(anonymized_telemetry=False),
                )
            except TypeError:
                # Older chromadb versions that don't accept settings kwarg
                self.client = chromadb.PersistentClient(path=self.persist_dir)

            self.collection = self.client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"}
            )

            self._initialized = True
            logger.info("Vector Store initialized successfully.")

        except ImportError:
            # Silent on validation/missing libs
            self._initialized = False
        except Exception:
            self._initialized = False

    def add_texts(
        self,
        texts: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str]
    ) -> bool:
        """
        Embed and upsert texts to the vector store.
        """
        if not self._initialized:
            return False

        if not texts:
            return True

        try:
            # Generate Embeddings
            # Use convert_to_numpy=False to get a torch tensor, then call .tolist()
            # directly — avoids RuntimeError: Numpy is not available on some torch builds.
            raw = self.embedder.encode(texts, convert_to_numpy=False)
            embeddings = _normalize_embedding_batch(raw)

            # Upsert to Chroma
            self.collection.upsert(
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"Upserted {len(texts)} vectors to store.")
            return True

        except Exception as e:
            logger.error(f"Vector upsert failed: {e}", exc_info=True)
            return False

    def similarity_search(
        self,
        query: str,
        k: int = 5,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search.
        Returns list of dicts: {'text': ..., 'metadata': ..., 'score': ...}
        """
        if not self._initialized:
            return []

        try:
            # Embed query (torch path — avoids .numpy() compatibility issues)
            raw = self.embedder.encode([query], convert_to_numpy=False)
            query_embedding = _normalize_embedding_batch(raw)

            # Query Chroma
            results = self.collection.query(
                query_embeddings=query_embedding,
                n_results=k,
                where=filter
            )

            # Format results
            out = []
            if results["documents"]:
                # Access first result set (since we only sent one query)
                docs = results["documents"][0]
                metas = results["metadatas"][0]
                distances = results["distances"][0]
                ids = results["ids"][0]

                for i in range(len(docs)):
                    # Similarity score = 1 - distance (cosine distance)
                    score = 1 - distances[i]
                    out.append({
                        "text": docs[i],
                        "metadata": metas[i],
                        "id": ids[i],
                        "score": max(0.0, score)
                    })

            return out

        except Exception as e:
            logger.error(f"Vector search failed: {e}", exc_info=True)
            return []

    def delete(self, ids: List[str]):
        """Delete vectors by ID."""
        if not self._initialized:
            return
        try:
            self.collection.delete(ids=ids)
        except Exception:
            pass

    def reset(self):
        """Wipe the collection."""
        if self._initialized and self.client:
            self.client.delete_collection(COLLECTION_NAME)
            self.collection = self.client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"}
            )
