import logging
import json
import uuid
from typing import Dict, Any, Type
from datetime import datetime

from src.application.jobs.job_base import Job
from src.engine.extractors.base import BaseExtractor
from src.engine.extractors.p6_extractor import P6Extractor
from src.engine.extractors.ifc_extractor import IFCExtractor
from src.engine.extractors.register_extractor import ExcelRegisterExtractor
from src.engine.extractors.pdf_extractor import UniversalPdfExtractor
from src.engine.extractors.field_extractor import FieldExtractor

logger = logging.getLogger(__name__)

class ExtractJob(Job):
    """
    Job: EXTRACT
    Orchestrates the extraction process:
    1. Resolve file path from Version ID.
    2. Select Extractor.
    3. Run Extractor.
    4. Persist 'staging' records (e.g. p6_activities) to DB.
    """
    
    TYPE_NAME = "EXTRACT"
    
    # Registry of available extractors
    EXTRACTORS: Dict[str, Type[BaseExtractor]] = {
        "p6": P6Extractor,
        "ifc": IFCExtractor,
        "excel_register": ExcelRegisterExtractor,
        "pdf": UniversalPdfExtractor,
        "field": FieldExtractor
    }

    # ... (existing code for init/to_dict/from_dict) ...

    # ... (skipping to _insert_record to keep context small if possible, but replace_file_content works on blocks)
    # Actually, I'll just replace the whole top part and the bottom part in two chunks if possible, or one big chunk if they overlap.
    # But wait, replace_file_content replaces a CONTIGUOUS block.
    # Imports are at lines 7-11.
    # Registry is at lines 28-32.
    # _insert_record is at 146+.
    # This acts on multiple parts. I must use multi_replace_file_content.
    

    # ... (existing code)



    def __init__(self, job_id: str, project_id: str, file_version_id: str, extractor_name: str = "p6"):
        super().__init__(job_id, project_id, priority=30)
        self.file_version_id = file_version_id
        self.extractor_name = extractor_name

    @property
    def type_name(self) -> str:
        return self.TYPE_NAME

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "project_id": self.project_id,
            "file_version_id": self.file_version_id,
            "extractor_name": self.extractor_name
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Job':
        return cls(
            job_id=data["job_id"],
            project_id=data["project_id"],
            file_version_id=data["file_version_id"],
            extractor_name=data.get("extractor_name", "p6")
        )

    def run(self, context) -> Any:
        db = context["db"]
        
        # 1. Get File Path
        row = db.execute(
            "SELECT source_path, file_ext FROM file_versions WHERE file_version_id = ?",
            (self.file_version_id,)
        ).fetchone()
        
        if not row:
            raise ValueError(f"File Version not found: {self.file_version_id}")
            
        source_path = row["source_path"]
        
        # 2. Instantiate Extractor
        extractor_cls = self.EXTRACTORS.get(self.extractor_name)
        if not extractor_cls:
            raise ValueError(f"Unknown extractor: {self.extractor_name}")
            
        extractor = extractor_cls()
        
        # 3. Log Start
        run_id = uuid.uuid4().hex
        start_ts = db._ts()
        db.execute(
            """INSERT INTO extraction_runs 
               (run_id, file_version_id, extractor_id, extractor_version, started_at, status)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (run_id, self.file_version_id, extractor.id, extractor.version, start_ts, "RUNNING")
        )
        db.commit()
        
        try:
            # 4. Get doc_id for context (needed for block extraction)
            doc_id_row = db.execute(
                """SELECT d.doc_id FROM documents d
                   JOIN file_versions fv ON d.file_name = fv.source_path 
                      OR d.abs_path = fv.source_path
                   WHERE fv.file_version_id = ?
                   LIMIT 1""",
                (self.file_version_id,)
            ).fetchone()
            doc_id = doc_id_row["doc_id"] if doc_id_row else f"doc_{self.file_version_id}"
            
            # 5. Run Extraction with context
            def _on_stage(stage_name, message=""):
                db.execute(
                    "UPDATE extraction_runs SET status=?, diagnostics_json=? WHERE run_id=?",
                    (f"RUNNING:{stage_name}", json.dumps({"message": message}), run_id)
                )
                db.commit()

            extraction_context = {
                "doc_id": doc_id,
                "file_version_id": self.file_version_id,
                "on_stage": _on_stage
            }
            result = extractor.extract(source_path, context=extraction_context)
            
            if not result.success:
                raise Exception(f"Extraction failed: {result.diagnostics}")
                
            # 5. Persist Records (Staging)
            _on_stage("PERSISTING", f"Saving {len(result.records)} items")
            # This logic depends on the record 'type' returned by P6Extractor
            with db.transaction():
                for rec in result.records:
                    self._insert_record(db, rec)
            
            # 6. Success
            end_ts = db._ts()
            db.execute(
                "UPDATE extraction_runs SET status='SUCCESS', ended_at=?, diagnostics_json=? WHERE run_id=?",
                (end_ts, json.dumps(result.metadata), run_id)
            )
            db.commit()
            
            # 7. Trigger Logic
            # Map extractor to builder (p6 -> schedule, ifc -> bim)
            builder_map = {
                "p6": "schedule",
                "ifc": "bim",
                "excel_register": "register",
                "field": "completion"
            }
            if self.extractor_name in builder_map:
                from src.application.jobs.build_facts_job import BuildFactsJob
                build_job = BuildFactsJob(
                    job_id=f"build_{uuid.uuid4().hex[:8]}",
                    project_id=self.project_id,
                    builder_type=builder_map[self.extractor_name],
                    snapshot_id=self.file_version_id
                )
                context["manager"].submit(build_job)
                logger.info(f"Triggered BuildFactsJob ({builder_map[self.extractor_name]})")

            # PDF Analysis Trigger (NEW)
            if self.extractor_name == "pdf":
                from src.application.jobs.analyze_doc_job import AnalyzeDocJob
                analysis_job = AnalyzeDocJob(
                    job_id=f"analyze_{uuid.uuid4().hex[:8]}",
                    project_id=self.project_id,
                    doc_id=doc_id
                )
                context["manager"].submit(analysis_job)
                logger.info(f"Triggered AnalyzeDocJob for doc_id={doc_id}")

            return {"run_id": run_id, "record_count": len(result.records)}
            
        except Exception as e:
            end_ts = db._ts()
            error_details = {
                "error": str(e),
                "type": type(e).__name__,
                "ts": end_ts
            }
            db.execute(
                "UPDATE extraction_runs SET status='FAILED', ended_at=?, diagnostics_json=? WHERE run_id=?",
                (end_ts, json.dumps(error_details), run_id)
            )
            db.commit()
            raise

    def _insert_record(self, db, rec):
        rtype = rec["type"]
        data = rec["data"]
        vid = self.file_version_id
        
        # P6 Logic
        if rtype.startswith("p6_"):
            if rtype == "p6_project":
                 db.execute("INSERT OR REPLACE INTO p6_projects (p6_project_id, file_version_id, short_name, name, raw_json) VALUES (?, ?, ?, ?, ?)", (data.get("proj_id"), vid, data.get("proj_short_name"), data.get("proj_short_name"), json.dumps(data)))
            elif rtype == "p6_wbs":
                 db.execute("INSERT OR REPLACE INTO p6_wbs (wbs_id, file_version_id, p6_project_id, parent_wbs_id, code, name) VALUES (?, ?, ?, ?, ?, ?)", (data.get("wbs_id"), vid, data.get("proj_id"), data.get("parent_wbs_id"), data.get("wbs_short_name"), data.get("wbs_name")))
            elif rtype == "p6_activity":
                 db.execute("INSERT OR REPLACE INTO p6_activities (activity_id, file_version_id, p6_project_id, wbs_id, code, name, start_date, finish_date, status_code, total_float, raw_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (data.get("task_id"), vid, data.get("proj_id"), data.get("wbs_id"), data.get("task_code"), data.get("task_name"), data.get("target_start_date"), data.get("target_end_date"), data.get("status_code"), data.get("total_float"), json.dumps(data)))
            elif rtype == "p6_relation":
                 pid = data.get("pred_task_id")
                 sid = data.get("task_id")
                 rel_id = f"{pid}_{sid}"
                 db.execute("INSERT OR REPLACE INTO p6_relations (relation_id, file_version_id, p6_project_id, pred_activity_id, succ_activity_id, rel_type, lag) VALUES (?, ?, ?, ?, ?, ?, ?)", (rel_id, vid, data.get("proj_id"), pid, sid, data.get("pred_type"), data.get("lag", 0)))

        # IFC Logic
        elif rtype == "ifc_project":
             db.execute("INSERT OR REPLACE INTO ifc_projects (global_id, file_version_id, name) VALUES (?, ?, ?)", (data["GlobalId"], vid, data["Name"]))
        elif rtype == "ifc_spatial":
             db.execute("INSERT OR REPLACE INTO ifc_spatial_structure (element_id, file_version_id, entity_type, name) VALUES (?, ?, ?, ?)", (data["GlobalId"], vid, data["EntityType"], data["Name"]))
             
        # Register Logic
        elif rtype == "register_row":
            row_id = f"row_{vid}_{data['sheet_name']}_{data['row_index']}"
            db.execute(
                "INSERT OR REPLACE INTO register_rows (row_id, file_version_id, sheet_name, row_index, raw_data_json) VALUES (?, ?, ?, ?, ?)",
                (row_id, vid, data["sheet_name"], data["row_index"], json.dumps(data["content"]))
            )

        # Field Logic
        elif rtype == "field_request":
             db.execute(
                """INSERT OR REPLACE INTO field_requests 
                   (request_id, file_version_id, req_type, discp_code, location_text, status, inspection_date, raw_vlm_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (data["request_id"], vid, data["type"], data["discp_code"], data["location_text"], data["status"], data["inspection_date"], json.dumps(data.get("raw_json", {})))
             )
             
        # PDF Logic (NEW)
        elif rtype == "pdf_page":
            pg_id = f"pg_{vid}_{data['page_no']}"
            db.execute(
                "INSERT OR REPLACE INTO pdf_pages (page_id, file_version_id, page_no, text_content, metadata_json) VALUES (?, ?, ?, ?, ?)",
                (pg_id, vid, data["page_no"], data["text_content"], data["metadata"])
            )
        elif rtype == "doc_classification":
            cls_id = f"cls_{vid}"
            db.execute(
                "INSERT OR REPLACE INTO doc_classifications (class_id, file_version_id, doc_type, confidence, keywords_json) VALUES (?, ?, ?, ?, ?)",
                (cls_id, vid, data["doc_type"], data["confidence"], json.dumps(data.get("keywords_found", [])))
            )
        
        # Doc Blocks Logic (NEW - for RAG)
        elif rtype == "doc_blocks":
            doc_id = data.get("doc_id")
            blocks = data.get("blocks", [])
            if doc_id and blocks:
                db.insert_doc_blocks(
                    doc_id=doc_id,
                    blocks=blocks,
                    source_type="pdf"
                )
                logger.info(f"Inserted {len(blocks)} blocks for doc {doc_id}")
