import abc
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class JobStatus:
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class Job(abc.ABC):
    """
    Base class for all idempotent jobs in the V02 architecture.
    Jobs must be serializable to JSON/DB and reconstructible.
    """
    
    def __init__(self, job_id: str, project_id: str, priority: int = 10):
        self.job_id = job_id
        self.project_id = project_id
        self.priority = priority
        self.status = JobStatus.PENDING
        self.created_at = datetime.utcnow()
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None

    @property
    @abc.abstractmethod
    def type_name(self) -> str:
        """Unique type identifier for this job class (e.g. 'INGEST_FILE')"""
        pass

    @abc.abstractmethod
    def run(self, context) -> Any:
        """
        Execute the job logic.
        :param context: Application context (DB, Service Provider)
        """
        pass

    @abc.abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Serialize job parameters"""
        pass

    @classmethod
    @abc.abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Job':
        """Deserialize job parameters"""
        pass

    def mark_started(self):
        self.status = JobStatus.RUNNING
        logger.info(f"[{self.type_name}] Started Job {self.job_id}")

    def mark_completed(self, result: Any = None):
        self.status = JobStatus.COMPLETED
        self.result = result
        logger.info(f"[{self.type_name}] Completed Job {self.job_id}")

    def mark_failed(self, error: Exception):
        self.status = JobStatus.FAILED
        self.error = str(error)
        logger.error(f"[{self.type_name}] Failed Job {self.job_id}: {self.error}")
