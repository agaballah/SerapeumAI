import logging
import json
from typing import List, Dict, Any

from src.domain.facts.models import Fact, FactStatus, FactInput, ValueType
from src.infra.persistence.database_manager import DatabaseManager

logger = logging.getLogger(__name__)

class SystemCompletionBuilder:
    """
    Builder: System Completion
    Consumes: field_requests (Staging)
    Produces:
      - Facts(field.inspection)
      - Facts(quality.ncr)
    """

    def __init__(self, db: DatabaseManager):
        self.db = db

    def build(self, project_id: str, snapshot_id: str) -> List[Fact]:
        facts = []
        now = self.db._ts()
        
        # 1. Fetch Field Requests
        rows = self.db.execute(
            "SELECT * FROM field_requests WHERE file_version_id=?", 
            (snapshot_id,)
        ).fetchall()
        
        for r in rows:
            # Fact ID
            fid = f"fact_field_{r['request_id']}"
            
            # Determine Fact Type
            ftype = "field.inspection"
            if r["req_type"] == "NCR":
                ftype = "quality.ncr"
                
            # Value
            val = {
                "status": r["status"],
                "discipline": r["discp_code"],
                "date": r["inspection_date"],
                "location": r["location_text"]
            }
            
            f = Fact(
                fact_id=fid,
                project_id=project_id,
                fact_type=ftype,
                subject_kind="location_ref", # Ideally verified against BIM
                subject_id=r["location_text"], # "Zone A-101"
                as_of={"file_version_id": snapshot_id},
                value_type=ValueType.JSON,
                value=val,
                status=FactStatus.VALIDATED, # Signed document = Validated Fact
                method_id="system_completion_builder_v1",
                created_at=now,
                updated_at=now,
                inputs=[FactInput(file_version_id=snapshot_id, location={"request_id": r["request_id"]})]
            )
            facts.append(f)
            
        return facts
