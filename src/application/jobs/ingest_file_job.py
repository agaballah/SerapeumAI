import os
import hashlib
import json
import logging
from typing import Dict, Any
from datetime import datetime
import uuid

from src.application.jobs.job_base import Job
from src.application.jobs.job_queue import JobStatus
from src.application.jobs.extract_job import ExtractJob
from src.application.jobs.file_linker_job import FileLinkerJob

logger = logging.getLogger(__name__)

class IngestFileJob(Job):
    """
    Job: INGEST_FILE
    1. Calculate hash of file at `path`.
    2. Register or update in `file_registry` / `file_versions`.
    3. If new version: spawn subsequent EXTRACT jobs.
    """
    
    TYPE_NAME = "INGEST_FILE"
    
    def __init__(self, job_id: str, project_id: str, file_path: str, rel_path: str = None, force: bool = False, is_global: bool = False):
        super().__init__(job_id, project_id, priority=50) # High priority
        self.file_path = file_path
        self.rel_path = rel_path
        self.force = force
        self.is_global = is_global

    @property
    def type_name(self) -> str:
        return self.TYPE_NAME

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "project_id": self.project_id,
            "file_path": self.file_path,
            "rel_path": self.rel_path,
            "force": self.force,
            "is_global": self.is_global
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Job':
        return cls(
            job_id=data["job_id"],
            project_id=data["project_id"],
            file_path=data["file_path"],
            rel_path=data.get("rel_path"),
            force=data.get("force", False),
            is_global=data.get("is_global", False)
        )

    def run(self, context) -> Any:
        db = context.get("global_db") if self.is_global else context["db"]
        manager = context["manager"]
        
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"File not found: {self.file_path}")
            
        # 1. Get Basic Metadata
        size = os.path.getsize(self.file_path)
        mtime = os.path.getmtime(self.file_path)
        filename = os.path.basename(self.file_path)
        
        # 2. Check Registry and Metadata (Pre-Hash Optimization)
        file_id = hashlib.md5(self.file_path.encode('utf-8')).hexdigest()
        
        # Check if we have a version that matches metadata
        # Optimization: If size and mtime haven't changed, we can safely assume hash hasn't changed.
        meta_row = db.execute(
            """SELECT sha256 FROM file_versions 
               WHERE source_path = ? AND size_bytes = ? AND last_modified_at = ?""",
            (self.file_path, size, mtime)
        ).fetchone()
        
        if meta_row and not self.force:
            logger.info(f"File {filename} matches metadata (mtime/size). Skipping hash check.")
            return {"status": "unchanged", "version_id": meta_row[0]}

        # 3. Compute Hash (Fallback if metadata changed or missing)
        sha256 = self._compute_hash(self.file_path)
        
        # Ensure Registry Entry
        db.execute(
            """INSERT OR IGNORE INTO file_registry (file_id, project_id, first_seen_path, created_at)
               VALUES (?, ?, ?, ?)""",
            (file_id, self.project_id, self.file_path, int(datetime.utcnow().timestamp()))
        )
        
        # Check Version by Hash
        row = db.execute(
            "SELECT file_version_id FROM file_versions WHERE file_id = ? AND sha256 = ?",
            (file_id, sha256)
        ).fetchone()
        
        if row and not self.force:
            # Hash matches but mtime/size didn't (or it was a cold cache). 
            # Update metadata to enable future skipping.
            db.execute(
                "UPDATE file_versions SET size_bytes = ?, last_modified_at = ? WHERE file_version_id = ?",
                (size, mtime, row[0])
            )
            if hasattr(db, "commit"): db.commit()
            logger.info(f"File {filename} is up to date (Version {row[0]}). Skipping.")
            return {"status": "unchanged", "version_id": row[0]}
            
        # 4. Create New Version
        version_id = sha256 # Simple CAS
        
        now = int(datetime.utcnow().timestamp())
        try:
            db.execute(
                """INSERT INTO file_versions 
                   (file_version_id, file_id, sha256, size_bytes, file_ext, imported_at, source_path, last_modified_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (version_id, file_id, sha256, size, os.path.splitext(filename)[1], now, self.file_path, mtime)
            )
        except Exception:
            # Might exist if same content imported from different path, or race condition
            db.execute(
                "UPDATE file_versions SET source_path = ?, imported_at = ?, size_bytes = ?, last_modified_at = ? WHERE file_version_id = ?",
                (self.file_path, now, size, mtime, version_id)
            )

        if hasattr(db, "commit"):
            db.commit()

        # 4.5 Register in 'documents' table for UI and RAG compatibility
        # This ensures the file appears in the document library and is accessible to agents.
        doc_id = f"doc_{file_id[:12]}"
        rel_path = self.rel_path or filename
        db.execute(
            """INSERT OR IGNORE INTO documents 
               (doc_id, project_id, file_name, rel_path, abs_path, file_ext, file_hash, file_size, file_mtime, created, updated)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (doc_id, self.project_id, filename, rel_path, self.file_path, os.path.splitext(filename)[1], sha256, size, mtime, now, now)
        )
        if hasattr(db, "commit"):
            db.commit()

        # 5. Trigger Downstream Jobs
        # A) Extraction (if supported)
        ext = os.path.splitext(filename)[1].lower()
        extractor_map = {
            ".xer": "p6",
            ".ifc": "ifc",
            ".xlsx": "excel_register",
            ".xls": "excel_register",
            ".pdf": "pdf", # Universal PDF Extractor
            ".jpg": "field",
            ".png": "field"
        }
        
        if ext in extractor_map:
            extract_job = ExtractJob(
                job_id=f"extract_{uuid.uuid4().hex[:8]}",
                project_id=self.project_id,
                file_version_id=version_id,
                extractor_name=extractor_map[ext]
            )
            manager.submit(extract_job)
            logger.info(f"Triggered ExtractJob for {filename}")

        # B) File Linking (Representation Strategy)
        linker_job = FileLinkerJob(
            job_id=f"link_{uuid.uuid4().hex[:8]}",
            project_id=self.project_id,
            target_file_id=file_id
        )
        manager.submit(linker_job)
        
        return {"status": "ingested", "version_id": version_id, "file_id": file_id}

    def _compute_hash(self, path: str) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(8192):
                h.update(chunk)
        return h.hexdigest()
