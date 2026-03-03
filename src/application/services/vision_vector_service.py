# Vision Vector Index Service
# Indexes vision descriptions into VectorStore for semantic search

import logging
from typing import List, Dict, Any, Optional
from src.infra.persistence.database_manager import DatabaseManager
from src.infra.adapters.vector_store import VectorStore

logger = logging.getLogger(__name__)


class VisionVectorService:
    """
    Service to index vision analysis data into vector store for semantic search.
    Called after vision worker completes analysis.
    """
    
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.vector_store = None
        try:
            self.vector_store = VectorStore()
            if not self.vector_store._initialized:
                logger.warning("[VisionVectorService] VectorStore not initialized, vision indexing disabled")
                self.vector_store = None
        except Exception as e:
            logger.error(f"[VisionVectorService] Failed to initialize VectorStore: {e}")
    
    def index_vision_for_document(self, doc_id: str) -> int:
        """
        Index all vision descriptions for a document into vector store.
        Returns number of pages indexed.
        """
        if not self.vector_store:
            logger.debug(f"[VisionVectorService] Skipping indexing for {doc_id} - VectorStore unavailable")
            return  0
        
        pages = self.db.list_pages(doc_id)
        indexed_count = 0
        
        texts_to_add = []
        metadatas = []
        ids = []
        
        for page in pages:
            vision_detailed = (page.get("vision_detailed") or "").strip()
            vision_general = (page.get("vision_general") or "").strip()
            
            # Use detailed vision if available, fall back to general
            vision_text = vision_detailed or vision_general
            
            if vision_text and len(vision_text) > 20:  # Minimum viable description
                page_index = page.get("page_index", 0)
                vector_id = f"{doc_id}_p{page_index}_vision"
                
                texts_to_add.append(vision_text)
                metadatas.append({
                    "doc_id": doc_id,
                    "page_index": page_index,
                    "source": "vision",
                    "vision_type": "detailed" if vision_detailed else "general"
                })
                ids.append(vector_id)
                indexed_count += 1
        
        # Batch add to vector store
        if texts_to_add:
            try:
                self.vector_store.add_texts(
                    texts=texts_to_add,
                    metadatas=metadatas,
                    ids=ids
                )
                logger.info(f"[VisionVectorService] Indexed {indexed_count} vision descriptions for {doc_id}")
            except Exception as e:
                logger.error(f"[VisionVectorService] Failed to index vision for {doc_id}: {e}")
                indexed_count = 0
        
        return indexed_count
    
    def index_vision_for_project(self, project_id: str, force: bool = False) -> Dict[str, int]:
        """
        Index all vision descriptions for all documents in a project in a large batch.
        """
        if not self.vector_store:
            logger.warning("[VisionVectorService] Cannot index project - VectorStore unavailable")
            return {"documents": 0, "pages": 0}
        
        # Get all pages with vision data that aren't indexed yet
        sql = """
            SELECT p.doc_id, p.page_index, p.vision_detailed, p.vision_general
            FROM pages p
            JOIN documents d ON p.doc_id = d.doc_id
            WHERE d.project_id = ?
              AND (p.vision_detailed IS NOT NULL OR p.vision_general IS NOT NULL)
        """
        if not force:
            sql += " AND (p.vision_indexed = 0 OR p.vision_indexed IS NULL)"
            
        rows = self.db._query(sql, (project_id,))
        
        texts_to_add = []
        metadatas = []
        ids = []
        doc_ids_seen = set()
        
        for row in rows:
            vision_text = (row.get("vision_detailed") or row.get("vision_general") or "").strip()
            if vision_text and len(vision_text) > 20:
                doc_id = row["doc_id"]
                page_index = row["page_index"]
                vector_id = f"{doc_id}_p{page_index}_vision"
                
                texts_to_add.append(vision_text)
                metadatas.append({
                    "doc_id": doc_id,
                    "page_index": page_index,
                    "source": "vision",
                    "vision_type": "detailed" if row.get("vision_detailed") else "general"
                })
                ids.append(vector_id)
                doc_ids_seen.add(doc_id)
        
        # Batch add to vector store
        if texts_to_add:
            try:
                # Process in chunks of 100 to avoid memory/API limits
                chunk_size = 100
                for i in range(0, len(texts_to_add), chunk_size):
                    self.vector_store.add_texts(
                        texts=texts_to_add[i:i+chunk_size],
                        metadatas=metadatas[i:i+chunk_size],
                        ids=ids[i:i+chunk_size]
                    )
                
                # Mark as indexed in DB
                doc_page_pairs = [(row["doc_id"], row["page_index"]) for row in rows]
                with self.db.transaction() as conn:
                    for d, p in doc_page_pairs:
                        conn.execute("UPDATE pages SET vision_indexed = 1 WHERE doc_id = ? AND page_index = ?", (d, p))
                
                logger.info(f"[VisionVectorService] Project {project_id}: Indexed {len(texts_to_add)} pages across {len(doc_ids_seen)} documents")
            except Exception as e:
                logger.error(f"[VisionVectorService] Failed to batch index for {project_id}: {e}")
                return {"documents": 0, "pages": 0}
        
        return {"documents": len(doc_ids_seen), "pages": len(texts_to_add)}
