# -*- coding: utf-8 -*-
import logging
from typing import List, Dict, Any, Optional
from src.infra.persistence.database_manager import DatabaseManager

logger = logging.getLogger(__name__)

class AuthorityService:
    """
    Service to manage and enforce certification authority policies.
    Determines if a role has the right to certify or validate facts in a specific domain.
    """
    
    def __init__(self, db: DatabaseManager):
        self.db = db

    def can_certify(self, project_id: str, role_id: str, domain: str) -> bool:
        """Check if a role can certify facts in a domain."""
        sql = """
            SELECT can_certify FROM authority_policies 
            WHERE (project_id = ? OR project_id = 'GLOBAL') 
            AND role_id = ? AND domain = ?
        """
        row = self.db.execute(sql, (project_id, role_id, domain)).fetchone()
        return bool(row["can_certify"]) if row else False

    def can_validate(self, project_id: str, role_id: str, domain: str) -> bool:
        """Check if a role can validate facts (lower than certification) in a domain."""
        sql = """
            SELECT can_validate FROM authority_policies 
            WHERE (project_id = ? OR project_id = 'GLOBAL') 
            AND role_id = ? AND domain = ?
        """
        row = self.db.execute(sql, (project_id, role_id, domain)).fetchone()
        return bool(row["can_validate"]) if row else False

    def get_authorized_domains(self, project_id: str, role_id: str) -> List[str]:
        """Get all domains this role is authorized to certify."""
        sql = """
            SELECT domain FROM authority_policies 
            WHERE (project_id = ? OR project_id = 'GLOBAL') 
            AND role_id = ? AND can_certify = 1
        """
        rows = self.db.execute(sql, (project_id, role_id)).fetchall()
        return [row["domain"] for row in rows]

    def authorize_certificate(self, fact_id: str, role_id: str, cert_type: str = "HUMAN_CERTIFIED") -> bool:
        """
        Attempts to certify a fact. Checks authority first.
        """
        # 1. Get fact context
        fact_sql = "SELECT project_id, domain FROM facts WHERE fact_id = ?"
        fact = self.db.execute(fact_sql, (fact_id,)).fetchone()
        
        if not fact:
            return False
            
        # 2. Check authority
        if not self.can_certify(fact["project_id"], role_id, fact["domain"]):
            logger.warning(f"Role {role_id} is not authorized to certify domain {fact['domain']}")
            return False
            
        # 3. Update fact status
        update_sql = "UPDATE facts SET status = ?, updated_at = ? WHERE fact_id = ?"
        import time
        self.db.execute(update_sql, (cert_type, int(time.time()), fact_id))
        self.db.commit()
        
        return True
