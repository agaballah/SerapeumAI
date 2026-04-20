from typing import List, Dict, Any, Optional
from src.domain.facts.models import Fact, FactStatus
from src.engine.validation.rule_runner import ValidationResult, RuleSeverity
from src.infra.persistence.database_manager import DatabaseManager

class P6ValidationRules:
    """
    Validation logic specific to Schedule Facts.
    """
    
    @staticmethod
    def validate_dates(fact: Fact) -> List[ValidationResult]:
        results = []
        if fact.fact_type == "schedule.dates":
            val = fact.value
            if not isinstance(val, dict): return results
            
            start = val.get("start")
            finish = val.get("finish")
            float_val = val.get("total_float")
            
            # Rule 1: Finish >= Start
            if start and finish and start > finish:
                results.append(ValidationResult(
                    rule_id="SCHED_001",
                    target_id=fact.fact_id,
                    pass_fail=False,
                    details={"msg": f"Negative duration: Start {start} > Finish {finish}"},
                    severity=RuleSeverity.ERROR
                ))
            
            # Rule 2: Negative Float (Warning)
            if float_val is not None:
                try:
                    f = float(float_val)
                    if f < 0:
                         results.append(ValidationResult(
                            rule_id="SCHED_002",
                            target_id=fact.fact_id,
                            pass_fail=False, # It's a failure of "Good Schedule" but maybe not "Valid Fact"?
                                            # V02 Philosophy: "Facts" are what exists. 
                                            # If schedule HAS neg float, it is a FACT that it has neg float.
                                            # So this rule validates the SCHEDULE QUALITY, not the Fact Integrity.
                                            # BUT, if we want to "Certify" the schedule for use, we might flag it.
                                            # Let's mark as WARNING.
                            details={"msg": f"Negative Total Float: {f}"},
                            severity=RuleSeverity.WARNING
                        ))
                except:
                    pass
        return results

    @staticmethod
    def validate_logic_loops(db: DatabaseManager, project_id: str, snapshot_id: str) -> List[ValidationResult]:
        """
        Expensive check: Detect loops in logic facts.
        Run once per snapshot, not per fact?
        This doesn't fit 'validate_fact' signature well.
        It should be a 'Batch Validation' step.
        For now, we skip complex loop detection in Phase 1 or implement as a separate Job.
        """
        return []
