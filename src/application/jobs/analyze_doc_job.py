import logging
import uuid
from typing import Dict, Any
from src.application.jobs.job_base import Job
from src.analysis_engine.page_analysis import PageAnalyzer
from src.infra.adapters.llm_service import LLMService
from src.infra.config.configuration_manager import get_config
from src.infra.services.runtime_setup_service import LocalRuntimeSetupService
from src.infra.adapters.cancellation import CancellationError

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
        stop_event = context.get("stop_event")
        interactive_event = context.get("interactive_event")

        def _check_cancel():
            if stop_event is not None and hasattr(stop_event, "is_set") and stop_event.is_set():
                raise CancellationError("Analysis cancelled because the app session is closing.")
        global_db = context.get("global_db")
        llm = context.get("llm") or LLMService(db=db, global_db=global_db)  # Fallback if not injected

        logger.info(f"Starting AnalyzeDocJob for doc_id={self.doc_id}")
        _check_cancel()

        # Fail fast before page-by-page analysis if the local runtime is not ready.
        try:
            runtime_service = LocalRuntimeSetupService(get_config())
            runtime_service.verify_ready()
        except Exception as e:
            raise RuntimeError(f"Local runtime not ready before analysis: {e}") from e

        if hasattr(llm, "verify_runtime_ready"):
            try:
                llm.verify_runtime_ready(task_type="analysis")
            except Exception as e:
                raise RuntimeError(f"LM Studio runtime preflight failed: {e}") from e

        analyzer = PageAnalyzer(db, llm)
        analyzer.analyze_document_pages(
            self.doc_id,
            fast_mode=self.fast_mode,
            cancellation_token=stop_event,
            interactive_event=interactive_event,
        )
        _check_cancel()

        # After analysis, trigger canonical document fact building
        try:
            snapshot_id = None
            # Live v14 schema: file_versions has (file_version_id, file_id, source_path, ...);
            # it has no doc_id column.  The only usable join is the one ExtractJob itself uses:
            #   documents.(file_name|abs_path) = file_versions.source_path
            # We reverse that join: given doc_id, find file_version_id.
            lookup_sqls = [
                (
                    """
                    SELECT fv.file_version_id
                    FROM file_versions fv
                    JOIN documents d
                      ON d.file_name = fv.source_path OR d.abs_path = fv.source_path
                    WHERE d.doc_id = ?
                    ORDER BY fv.imported_at DESC LIMIT 1
                    """,
                    (self.doc_id,)
                ),
            ]

            for sql, params in lookup_sqls:
                try:
                    row = db.execute(sql, params).fetchone()
                    if row:
                        try:
                            snapshot_id = row["file_version_id"]
                        except Exception:
                            snapshot_id = row[0]
                    if snapshot_id:
                        break
                except Exception:
                    continue

            # Fallback: ExtractJob uses f"doc_{file_version_id}" when its own join fails.
            # If self.doc_id has that shape, extract the embedded file_version_id directly.
            if not snapshot_id and isinstance(self.doc_id, str) and self.doc_id.startswith("doc_"):
                candidate = self.doc_id[4:]
                try:
                    row = db.execute(
                        "SELECT 1 FROM file_versions WHERE file_version_id = ? LIMIT 1",
                        (candidate,)
                    ).fetchone()
                    if row:
                        snapshot_id = candidate
                except Exception:
                    pass

            manager = context.get("manager")
            _check_cancel()
            if snapshot_id and manager:
                from src.application.jobs.build_facts_job import BuildFactsJob
                build_job = BuildFactsJob(
                    job_id=f"build_{uuid.uuid4().hex[:8]}",
                    project_id=self.project_id,
                    builder_type="document",
                    snapshot_id=snapshot_id
                )
                manager.submit(build_job)
                logger.info(
                    "Triggered document fact build for doc_id=%s snapshot_id=%s",
                    self.doc_id, snapshot_id
                )
            else:
                logger.warning(
                    "Skipped document fact build for doc_id=%s; snapshot_id=%s manager=%s",
                    self.doc_id, snapshot_id, bool(manager)
                )
        except Exception as e:
            logger.error(f"Document fact build trigger failed for doc_id={self.doc_id}: {e}")
        
        # After analysis, trigger vision indexing into vector store
        try:
            _check_cancel()
            from src.application.services.vision_vector_service import VisionVectorService
            vvs = VisionVectorService(db)
            vvs.index_vision_for_document(self.doc_id)
            logger.info(f"Triggered vision indexing for doc_id={self.doc_id}")
        except Exception as e:
            logger.error(f"Vision indexing failed for doc_id={self.doc_id}: {e}")
            
        return {"doc_id": self.doc_id, "status": "COMPLETED"}
