import json
import logging
from typing import List, Dict, Any, Optional
from src.domain.facts.models import Fact, Link, FactStatus, normalize_rejection_status
from src.infra.persistence.database_manager import DatabaseManager

logger = logging.getLogger(__name__)

class FactRepository:
    def __init__(self, db: DatabaseManager):
        self.db = db

    def update_fact_status(self, fact_id: str, new_status: str) -> bool:
        """
        Canonical human-review state transition for facts.

        This is the single domain path used by UI review actions so that
        Certify/Reject update the same fact.status values consumed by
        FactQueryAPI, CoverageGate, and chat.
        """
        status = normalize_rejection_status(str(new_status or "").upper())
        allowed = {s.value for s in FactStatus}
        if status not in allowed:
            raise ValueError(f"Unsupported fact status: {new_status}")

        existing = self.db.execute(
            "SELECT fact_id FROM facts WHERE fact_id = ?",
            (fact_id,),
        ).fetchone()
        if not existing:
            return False

        self.db.execute(
            "UPDATE facts SET status = ?, updated_at = ? WHERE fact_id = ?",
            (status, self.db._ts(), fact_id),
        )
        self.db.commit()
        logger.info("Fact %s review status updated to %s", fact_id, status)
        return True

    def certify_fact(self, fact_id: str) -> bool:
        """Promote a fact to HUMAN_CERTIFIED so it becomes governing truth."""
        return self.update_fact_status(fact_id, FactStatus.HUMAN_CERTIFIED.value)

    def reject_fact(self, fact_id: str) -> bool:
        """Reject a fact so it is excluded from trusted answer paths."""
        return self.update_fact_status(fact_id, FactStatus.REJECTED.value)

    def save_facts(self, facts: List[Fact]):
        if not facts:
            return

        with self.db.transaction():
            for fact in facts:
                # 1. Upsert Fact
                # We overwrite if ID exists? V02 says immutable? 
                # Schema has fact_id PK. 
                # If builder runs twice, it produces same IDs?
                # Usually we want consistent IDs for same subject.
                # Let's assume UPSERT for Candidate/Draft status.
                
                val_json = None
                if isinstance(fact.value, (dict, list)):
                    val_json = json.dumps(fact.value)
                else:
                    val_json = str(fact.value) # Fallback?
                
                self.db.execute(
                    """
                    INSERT OR REPLACE INTO facts 
                    (fact_id, project_id, fact_type, subject_kind, subject_id, 
                     value_type, value_json, status, method_id, created_at, updated_at, as_of_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        fact.fact_id, fact.project_id, fact.fact_type, fact.subject_kind, fact.subject_id,
                        fact.value_type.value, val_json, fact.status.value, fact.method_id, 
                        fact.created_at, fact.updated_at, json.dumps(fact.as_of)
                    )
                )

                # 2. Fact Inputs (Lineage)
                # clear old inputs for this fact
                self.db.execute("DELETE FROM fact_inputs WHERE fact_id=?", (fact.fact_id,))
                
                for inp in fact.inputs:
                    self.db.execute(
                        """
                        INSERT INTO fact_inputs (fact_id, file_version_id, location_json, input_kind)
                        VALUES (?, ?, ?, ?)
                        """,
                        (fact.fact_id, inp.file_version_id, json.dumps(inp.location), inp.input_kind)
                    )

    def save_links(self, links: List[Link]):
        if not links:
            return

        with self.db.transaction():
            for link in links:
                self.db.execute(
                    """
                    INSERT OR REPLACE INTO links 
                    (link_id, project_id, link_type, from_kind, from_id, to_kind, to_id, 
                     status, confidence, confidence_tier, method_id, created_at, validated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        link.link_id, link.project_id, link.link_type, link.from_kind, link.from_id,
                        link.to_kind, link.to_id, link.status.value, link.confidence, 
                        link.confidence_tier, link.method_id, link.created_at, link.validated_at
                    )
                )
    
    def query_facts(
        self,
        fact_type: Optional[str] = None,
        subject_id: Optional[str] = None,
        subject_kind: Optional[str] = None,
        status: str = "CANDIDATE",
        project_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Query facts with filters.
        Returns list of fact records as dicts.
        """
        sql = "SELECT * FROM facts WHERE 1=1"
        params = []
        
        if fact_type:
            sql += " AND fact_type = ?"
            params.append(fact_type)
        
        if subject_id:
            sql += " AND subject_id = ?"
            params.append(subject_id)
        
        if subject_kind:
            sql += " AND subject_kind = ?"
            params.append(subject_kind)
        
        if status:
            sql += " AND status = ?"
            params.append(status)
        
        if project_id:
            sql += " AND project_id = ?"
            params.append(project_id)
        
        sql += f" ORDER BY created_at DESC LIMIT {limit}"
        
        rows = self.db.execute(sql, tuple(params)).fetchall()
        return [dict(row) for row in rows]
    
    def get_fact_lineage(self, fact_id: str) -> List[Dict[str, Any]]:
        """Get lineage/provenance for a fact."""
        rows = self.db.execute(
            """
            SELECT fi.*, fv.source_path, fv.file_ext
            FROM fact_inputs fi
            JOIN file_versions fv ON fi.file_version_id = fv.file_version_id
            WHERE fi.fact_id = ?
            """,
            (fact_id,)
        ).fetchall()
        return [dict(row) for row in rows]
