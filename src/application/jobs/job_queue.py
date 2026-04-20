import sqlite3
import json
import logging
from typing import Optional, List, Type
from datetime import datetime
import uuid

from src.application.jobs.job_base import Job, JobStatus

logger = logging.getLogger(__name__)

class SQLiteJobQueue:
    """
    Persistent Job Queue backed by the Project SQLite DB.
    Handles enqueue, dequeue, and status updates.
    """

    def __init__(self, db_manager):
        self.db_manager = db_manager
        self._ensure_table()
        # Registry of known job types for deserialization
        self._job_registry: dict[str, Type[Job]] = {}

    def register_job_type(self, job_cls: Type[Job]):
        # Use the class constant TYPE_NAME, as type_name is an instance property
        if hasattr(job_cls, "TYPE_NAME"):
            self._job_registry[job_cls.TYPE_NAME] = job_cls
        else:
             # Fallback or error? For now assume V02 convention
             pass

    def _ensure_table(self):
        # We might move this to a migration later, but safe to ensure existence here for now
        sql = """
        CREATE TABLE IF NOT EXISTS job_queue (
            job_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            type_name TEXT NOT NULL,
            priority INTEGER DEFAULT 10,
            status TEXT DEFAULT 'PENDING',
            payload_json TEXT,
            result_json TEXT,
            error_text TEXT,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_jobs_status_priority ON job_queue(status, priority DESC);
        """
        self.db_manager.execute_script(sql)

    def enqueue(self, job: Job):
        payload = json.dumps(job.to_dict())
        sql = """
        INSERT INTO job_queue (job_id, project_id, type_name, priority, status, payload_json, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        now = datetime.utcnow()
        self.db_manager.execute(
            sql, 
            (job.job_id, job.project_id, job.type_name, job.priority, JobStatus.PENDING, payload, now, now)
        )
        self.db_manager.commit()

    def pick_next(self, project_id: str) -> Optional[Job]:
        """
        Atomic pick of the next highest priority PENDING job.
        """
        # 1. Find candidate
        sql_find = """
        SELECT job_id, type_name, payload_json 
        FROM job_queue 
        WHERE project_id = ? AND status = 'PENDING' 
        ORDER BY priority DESC, created_at ASC 
        LIMIT 1
        """
        row = self.db_manager.execute(sql_find, (project_id,)).fetchone()
        
        if not row:
            return None
            
        job_id, type_name, payload_str = row
        
        # 2. Mark RUNNING
        sql_update = """
        UPDATE job_queue 
        SET status = 'RUNNING', updated_at = ? 
        WHERE job_id = ? AND status = 'PENDING'
        """
        now = datetime.utcnow()
        cursor = self.db_manager.execute(sql_update, (now, job_id))
        self.db_manager.commit()
        
        if cursor.rowcount == 0:
            # Race condition lost
            return None
            
        # 3. Deserialize
        if type_name not in self._job_registry:
            logger.error(f"Unknown job type {type_name} for job {job_id}")
            # Mark failed to avoid infinite loop
            self.mark_failed(job_id, Exception(f"Unknown job type: {type_name}"))
            return None
            
        job_cls = self._job_registry[type_name]
        try:
            data = json.loads(payload_str)
            job = job_cls.from_dict(data)
            # Ensure runtime state matches DB
            job.job_id = job_id
            job.status = JobStatus.RUNNING
            return job
        except Exception as e:
            logger.error(f"Failed to deserialize job {job_id}: {e}")
            self.mark_failed(job_id, e)
            return None

    def mark_completed(self, job_id: str, result: dict):
        sql = """
        UPDATE job_queue 
        SET status = 'COMPLETED', result_json = ?, updated_at = ? 
        WHERE job_id = ?
        """
        self.db_manager.execute(sql, (json.dumps(result), datetime.utcnow(), job_id))
        self.db_manager.commit()

    def mark_failed(self, job_id: str, error: Exception):
        sql = """
        UPDATE job_queue 
        SET status = 'FAILED', error_text = ?, updated_at = ? 
        WHERE job_id = ?
        """
        self.db_manager.execute(sql, (str(error), datetime.utcnow(), job_id))
        self.db_manager.commit()

    def mark_pending(self, job_id: str):
        sql = """
        UPDATE job_queue
        SET status = 'PENDING', updated_at = ?
        WHERE job_id = ? AND status = 'RUNNING'
        """
        self.db_manager.execute(sql, (datetime.utcnow(), job_id))
        self.db_manager.commit()

    def mark_cancelled(self, job_id: str, reason: str = "Cancelled"):
        sql = """
        UPDATE job_queue
        SET status = 'CANCELLED', error_text = ?, updated_at = ?
        WHERE job_id = ? AND status IN ('PENDING', 'RUNNING')
        """
        self.db_manager.execute(sql, (reason, datetime.utcnow(), job_id))
        self.db_manager.commit()

    def cancel_incomplete_for_project(self, project_id: str, reason: str = "Cancelled by operator"):
        sql = """
        UPDATE job_queue
        SET status = 'CANCELLED', error_text = ?, updated_at = ?
        WHERE project_id = ? AND status IN ('PENDING', 'RUNNING')
        """
        self.db_manager.execute(sql, (reason, datetime.utcnow(), project_id))
        self.db_manager.commit()
