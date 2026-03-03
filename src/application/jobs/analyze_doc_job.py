import logging
import uuid
from typing import Dict, Any
from src.application.jobs.job_base import Job
from src.analysis_engine.page_analysis import PageAnalyzer
from src.infra.adapters.llm_service import LLMService

logger = logging.getLogger(__name__)

class AnalyzeDocJob(Job):
    """
    Job: ANALYZE_DOC
    Performs heavy page-by-page analysis (VLM + Adaptive Logic) for a document.
    """
    
    TYPE_NAME = "ANALYZE_DOC"
    
    def __init__(self, job_id: str, project_id: str, doc_id: str, fast_mode: bool = False):
        super().__init__(job_id, project_id, priority=50) # Higher priority than extraction? No, lower (50).
        self.doc_id = doc_id
        self.fast_mode = fast_mode

    @property
    def type_name(self) -> str:
        return self.TYPE_NAME

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "project_id": self.project_id,
            "doc_id": self.doc_id,
            "fast_mode": self.fast_mode
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Job':
        return cls(
            job_id=data["job_id"],
            project_id=data["project_id"],
            doc_id=data["doc_id"],
            fast_mode=data.get("fast_mode", False)
        )

    def run(self, context) -> Any:
        db = context["db"]
        llm = context.get("llm") or LLMService() # Fallback if not injected
        
        logger.info(f"Starting AnalyzeDocJob for doc_id={self.doc_id}")
        
        analyzer = PageAnalyzer(db, llm)
        analyzer.analyze_document_pages(self.doc_id, fast_mode=self.fast_mode)
        
        # After analysis, trigger vision indexing into vector store
        try:
            from src.application.services.vision_vector_service import VisionVectorService
            vvs = VisionVectorService(db)
            vvs.index_vision_for_document(self.doc_id)
            logger.info(f"Triggered vision indexing for doc_id={self.doc_id}")
        except Exception as e:
            logger.error(f"Vision indexing failed for doc_id={self.doc_id}: {e}")
            
        return {"doc_id": self.doc_id, "status": "COMPLETED"}
