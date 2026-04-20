import logging
import uuid
import json
from typing import Dict, Any, Type, Optional

from src.application.jobs.job_base import Job
from src.domain.facts.repository import FactRepository
from src.engine.builders.schedule_builder import ScheduleBuilder
from src.engine.builders.bim_builder import BIMBuilder
from src.engine.builders.register_builder import RegisterBuilder
from src.engine.builders.completion_builder import SystemCompletionBuilder
from src.engine.builders.document_builder import DocumentBuilder

logger = logging.getLogger(__name__)

class BuildFactsJob(Job):
    """
    Job: BUILD_FACTS
    Domain Agnostic Builder Orchestrator.
    Input: builder_type (e.g. 'schedule'), snapshot_id (file_version_id)
    """
    
    TYPE_NAME = "BUILD_FACTS"
    
    # Registry of builders
    # In a real system, use dependency injection or plugin scanner
    BUILDERS = {
        "schedule": ScheduleBuilder,
        "bim": BIMBuilder,
        "register": RegisterBuilder,
        "completion": SystemCompletionBuilder,
        "document": DocumentBuilder
    }

    def __init__(self, job_id: str, project_id: str, builder_type: str, snapshot_id: str, priority: Optional[int] = None):
        super().__init__(job_id, project_id, priority=priority if priority is not None else 20)
        self.builder_type = builder_type
        self.snapshot_id = snapshot_id

    @property
    def type_name(self) -> str:
        return self.TYPE_NAME

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "project_id": self.project_id,
            "builder_type": self.builder_type,
            "snapshot_id": self.snapshot_id,
            "priority": self.priority,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Job':
        return cls(
            job_id=data["job_id"],
            project_id=data["project_id"],
            builder_type=data["builder_type"],
            snapshot_id=data["snapshot_id"],
            priority=data.get("priority"),
        )

    def run(self, context) -> Any:
        db = context["db"]
        
        # 1. Resolve Builder
        builder_cls = self.BUILDERS.get(self.builder_type)
        if not builder_cls:
            raise ValueError(f"Unknown builder type: {self.builder_type}")
            
        builder = builder_cls(db)
        repo = FactRepository(db)
        
        logger.info(f"[BUILD_FACTS] Building facts using {self.builder_type} for snapshot {self.snapshot_id}")
        
        # 2. Build Facts
        facts = builder.build(self.project_id, self.snapshot_id)
        
        # 3. Persist
        repo.save_facts(facts)
        
        return {"count": len(facts)}
