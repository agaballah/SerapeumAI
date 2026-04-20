import logging
import json
from typing import List, Dict, Any, Optional

from src.domain.facts.models import Fact, FactStatus, FactInput, ValueType
from src.infra.persistence.database_manager import DatabaseManager

logger = logging.getLogger(__name__)

class RegisterBuilder:
    """
    Builder: Register
    Consumes: register_rows
    Produces: 
      - Facts(procurement.submittal) if 'Submittal No' found
      - Facts(link.related_to) if 'Activity ID' found (Crosswalk)
    """
    
    # Heuristics for column mapping (Normalized -> Possible Headers)
    COL_MAP = {
        "ID": ["submittal no", "submittal id", "rfi no", "rfi id", "item no"],
        "TITLE": ["title", "description", "subject", "item description"],
        "ACTIVITY_ID": ["activity id", "activity code", "p6 activity", "schedule id"],
        "STATUS": ["status", "current status", "review status"]
    }

    def __init__(self, db: DatabaseManager):
        self.db = db

    def _normalize_header(self, header: str) -> str:
        h = str(header).lower().strip().replace(".", "").replace("_", " ")
        for key, variants in self.COL_MAP.items():
            if h in variants:
                return key
        return h

    def build(self, project_id: str, snapshot_id: str) -> List[Fact]:
        facts = []
        now = self.db._ts()
        
        # 1. Fetch Rows
        rows = self.db.execute(
            "SELECT * FROM register_rows WHERE file_version_id=? ORDER BY sheet_name, row_index", 
            (snapshot_id,)
        ).fetchall()
        
        if not rows:
            return []

        # Process per sheet (assuming schema consistency per sheet)
        # We need to detect headers? 
        # For this generic builder, we assume the Extractor already gave us Key-Value pairs 
        # where Keys are the headers.
        
        for r in rows:
            raw = json.loads(r["raw_data_json"]) # Dict[ColName, Value]
            
            # Map columns
            normalized_data = {}
            for k, v in raw.items():
                norm_k = self._normalize_header(k)
                normalized_data[norm_k] = v
                
            # Heuristic: Is this a Submittal?
            subj_id = normalized_data.get("ID")
            if not subj_id:
                # Fallback: Hash of row content if it's a "List" but no clear ID?
                # For now skip.
                continue
                
            # Create Core Fact (e.g. Submittal)
            # Default to generic "procurement.item" unless we detect "Submittal" text
            fact_type = "procurement.item"
            # Basic check if sheet name implies type?
            if "subm" in str(r["sheet_name"]).lower(): fact_type = "procurement.submittal"
            elif "rfi" in str(r["sheet_name"]).lower(): fact_type = "rfi.item"
            
            f_main = Fact(
                fact_id=f"fact_regr_{r['row_id']}",
                project_id=project_id,
                fact_type=fact_type,
                subject_kind="register_item",
                subject_id=subj_id,
                as_of={"file_version_id": snapshot_id},
                value_type=ValueType.JSON,
                value={
                    "title": normalized_data.get("TITLE", ""),
                    "status": normalized_data.get("STATUS", ""),
                    "raw": raw
                },
                status=FactStatus.CANDIDATE,
                method_id="register_builder_v1",
                created_at=now,
                updated_at=now,
                inputs=[FactInput(file_version_id=snapshot_id, location={"row_id": r["row_id"]})]
            )
            facts.append(f_main)
            
            # CROSSWALK: Link to Activity
            act_id = normalized_data.get("ACTIVITY_ID")
            if act_id:
                # We assert a link: This Item -> Related To -> Activity match?
                # We can create a 'link.related_to' fact.
                # Subject: This Item. Value: Activity ID.
                # Later, a linker Job could verify if that Activity ID exists.
                # Or we state the Fact that "Register says it relates to A100".
                
                f_link = Fact(
                    fact_id=f"fact_link_{r['row_id']}_act",
                    project_id=project_id,
                    fact_type="link.related_to",
                    subject_kind="register_item",
                    subject_id=subj_id,
                    as_of={"file_version_id": snapshot_id},
                    value_type=ValueType.TEXT,
                    value=act_id,  # The target Activity ID
                    status=FactStatus.CANDIDATE,
                    method_id="register_builder_v1_crosswalk",
                    created_at=now,
                    updated_at=now,
                    inputs=[FactInput(file_version_id=snapshot_id, location={"row_id": r["row_id"]})]
                )
                facts.append(f_link)
                
        return facts
