import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class GlobalKnowledgeService:
    """Compatibility facade over the canonical runtime global knowledge owner."""
    def __init__(self, db: Any = None, app_root: Optional[str] = None):
        self.db = db
        self.app_root = app_root

    def ingest_standard_document(self, standard_id: str, title: str, content: str):
        logger.info(f"Ingesting standard: {title}")

    def search_standards(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        if self.db and hasattr(self.db, "search_standards"):
            return self.db.search_standards(query, limit=limit)
        logger.warning("GlobalKnowledgeService has no canonical global DB bound; returning no results.")
        return []
