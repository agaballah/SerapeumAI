import logging
import json
from enum import Enum
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from src.infra.persistence.database_manager import DatabaseManager
from src.domain.facts.models import Fact, FactStatus

logger = logging.getLogger(__name__)

class RuleSeverity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"

@dataclass
class ValidationResult:
    rule_id: str
    target_id: str
    pass_fail: bool
    details: Dict[str, Any]
    severity: RuleSeverity

class RuleRunner:
    """
    Engine for executing validation rules against facts.
    V02 Principle: "If it's not in certified facts, we do not answer."
    """
    
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    def validate_fact(self, fact: Fact) -> List[ValidationResult]:
        """
        Run all applicable rules for this fact.
        For Phase 0/1: Hardcoded rules. Phase 2: DB-stored dynamic rules.
        """
        results = []
        
        # 1. Structural Validation (Generic)
        if not fact.value and fact.value != False and fact.value != 0:
             results.append(ValidationResult(
                 rule_id="CORE_001",
                 target_id=fact.fact_id,
                 pass_fail=False,
                 details={"msg": "Fact value is null/empty"},
                 severity=RuleSeverity.ERROR
             ))

        # 2. Type-Specific Validation
        if fact.fact_type.startswith("schedule."):
            from src.engine.validation.rules.p6_rules import P6ValidationRules
            results.extend(P6ValidationRules.validate_dates(fact))
            
        return results

    def _validate_schedule_fact(self, fact: Fact) -> List[ValidationResult]:
        # Deprecated by P6ValidationRules, removing local implementation if preferred
        # or keeping as legacy stub. 
        return []

    def commit_results(self, results: List[ValidationResult]):
        """Persist validation runs to DB"""
        now = self.db._ts()
        for r in results:
            self.db.execute(
                """INSERT INTO validation_runs 
                   (run_id, target_id, rule_id, pass_fail, details_json, run_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (f"val_{now}_{r.target_id[:8]}", r.target_id, r.rule_id, 1 if r.pass_fail else 0, json.dumps(r.details), now)
            )
            
            # Auto-reject if ERROR
            if not r.pass_fail and r.severity == RuleSeverity.ERROR:
                self.db.execute(
                    "UPDATE facts SET status='REJECTED' WHERE fact_id=?", 
                    (r.target_id,)
                )
                logger.info(f"Fact {r.target_id} REJECTED by rule {r.rule_id}")
