
"""
vector_store.py — Local Vector Database Wrapper (The "Pinecone Mimic")
----------------------------------------------------------------------
Provides a simple interface for semantic search using ChromaDB (local) 
and SentenceTransformer embeddings (CPU-friendly).

Features:
- Auto-initialization of local ChromaDB in ./.serapeum_vectors
- Embedding generation using 'all-MiniLM-L6-v2' (384-d, fast)
- Hybrid-ready interface (add_texts, similarity_search)
"""

import os
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Constants
VECTOR_DB_DIR = "./.serapeum_vectors"
COLLECTION_NAME = "serapeum_knowledge"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

class VectorStore:
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(VectorStore, cls).__new__(cls)
        return cls._instance

    def __init__(self, persist_dir: str = VECTOR_DB_DIR):
        if hasattr(self, "_initialized"):
            return
            
        self.persist_dir = persist_dir
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
                
                if gpu_info['available'] and gpu_info['vram_free_mb'] >= VRAM_THRESHOLD_MB:
                    device = "cuda"
                    logger.info(
                        f"Loading embedding model: {EMBEDDING_MODEL} on GPU "
                        f"({gpu_info['vram_free_mb']} MB free VRAM available)"
                    )
                else:
                    if gpu_info['available']:
                        logger.info(
                            f"Loading embedding model: {EMBEDDING_MODEL} on CPU "
                            f"(insufficient VRAM: {gpu_info['vram_free_mb']} MB < {VRAM_THRESHOLD_MB} MB)"
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
                import chromadb
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
            
        except ImportError as e:
            # Silent on validation/missing libs
            self._initialized = False
        except Exception as e:
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
            embeddings = raw.cpu().tolist()
            
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
            query_embedding = raw.cpu().tolist()
            
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
                    # Similiarity score = 1 - distance (cosine distance)
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
        if not self._initialized: return
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
