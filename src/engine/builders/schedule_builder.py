import logging
import json
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta

from src.domain.facts.models import Fact, FactStatus, FactInput, ValueType
from src.infra.persistence.database_manager import DatabaseManager

logger = logging.getLogger(__name__)

class ScheduleBuilder:
    """
    Builder: SCHEDULE
    Consumes: p6_activities, p6_relations
    Produces: Fact(schedule.activity), Fact(schedule.logic), Fact(schedule.critical_path_membership)
    """
    
    def __init__(self, db: DatabaseManager):
        self.db = db

    def build(self, project_id: str, snapshot_id: str) -> List[Fact]:
        """
        :param snapshot_id: Here, we interpret snapshot_id as the file_version_id of the XER.
                            In a full system, a snapshot might define a specific data date across multiple files.
        """
        facts = []
        
        # 1. Load Activities
        activities = self.db.execute(
            "SELECT * FROM p6_activities WHERE file_version_id = ?", 
            (snapshot_id,)
        ).fetchall()
        
        if not activities:
            logger.warning(f"No activities found for snapshot {snapshot_id}")
            return []
        
        now = self.db._ts()
        
        # 2. Compute Critical Path
        critical_path_set = self._compute_critical_path(snapshot_id)
        
        # 3. Activity-Level Facts
        status_counts = {}
        milestone_activities = []
        
        for row in activities:
            r_dict = dict(row)
            act_id = r_dict["activity_id"]
            code = r_dict["code"]
            name = r_dict["name"]
            status = r_dict.get("status_code", "TK_NotStart")
            
            # Track status for aggregate facts
            status_counts[status] = status_counts.get(status, 0) + 1
            
            # Detect milestones (0-day duration heuristic)
            start = r_dict.get("start_date")
            finish = r_dict.get("finish_date")
            is_milestone = (start == finish) if (start and finish) else False
            if is_milestone:
                milestone_activities.append({"code": code, "name": name, "date": finish})
            
            # 1. Activity Definition
            f_def = Fact(
                fact_id=f"fact_sched_act_{act_id}",
                project_id=project_id,
                fact_type="schedule.activity",
                subject_kind="activity",
                subject_id=code,
                as_of={"file_version_id": snapshot_id},
                value_type=ValueType.JSON,
                value={"name": name, "wbs_id": row["wbs_id"]},
                status=FactStatus.CANDIDATE,
                method_id="schedule_builder_v1",
                created_at=now,
                updated_at=now
            )
            f_def.inputs.append(FactInput(file_version_id=snapshot_id, location={"table": "TASK", "row_id": act_id}))
            facts.append(f_def)
            
            # 2. Activity Dates
            f_dates = Fact(
                fact_id=f"fact_sched_dates_{act_id}",
                project_id=project_id,
                fact_type="schedule.dates",
                subject_kind="activity",
                subject_id=code,
                as_of={"file_version_id": snapshot_id},
                value_type=ValueType.JSON,
                value={
                    "start": row["start_date"],
                    "finish": row["finish_date"],
                    "total_float": row["total_float"]
                },
                status=FactStatus.CANDIDATE,
                method_id="schedule_builder_v1",
                created_at=now,
                updated_at=now
            )
            f_dates.inputs.append(FactInput(file_version_id=snapshot_id, location={"table": "TASK", "row_id": act_id}))
            facts.append(f_dates)
            
            # 3. NEW: Critical Path Membership
            is_critical = code in critical_path_set
            f_critical = Fact(
                fact_id=f"fact_sched_critical_{act_id}",
                project_id=project_id,
                fact_type="schedule.critical_path_membership",
                subject_kind="activity",
                subject_id=code,
                as_of={"file_version_id": snapshot_id},
                value_type=ValueType.BOOL,
                value=is_critical,
                status=FactStatus.CANDIDATE,
                method_id="schedule_builder_v1_cpm",
                created_at=now,
                updated_at=now
            )
            f_critical.inputs.append(FactInput(file_version_id=snapshot_id, location={"table": "TASK", "row_id": act_id}))
            facts.append(f_critical)
            
            #4. NEW: Total Float as separate fact
            if r_dict.get("total_float") is not None:
                f_float = Fact(
                    fact_id=f"fact_sched_float_{act_id}",
                    project_id=project_id,
                    fact_type="schedule.activity_total_float_days",
                    subject_kind="activity",
                    subject_id=code,
                    as_of={"file_version_id": snapshot_id},
                    value_type=ValueType.NUM,
                    value=float(row["total_float"]),
                    unit="days",
                    status=FactStatus.CANDIDATE,
                    method_id="schedule_builder_v1",
                    created_at=now,
                    updated_at=now
                )
                f_float.inputs.append(FactInput(file_version_id=snapshot_id, location={"table": "TASK", "row_id": act_id}))
                facts.append(f_float)

        # 4. Logic (Relationships)
        relations = self.db.execute(
            """
            SELECT r.*, p.code as pred_code, s.code as succ_code 
            FROM p6_relations r
            JOIN p6_activities p ON r.pred_activity_id = p.activity_id
            JOIN p6_activities s ON r.succ_activity_id = s.activity_id
            WHERE r.file_version_id = ?
            """,
            (snapshot_id,)
        ).fetchall()
        
        for row in relations:
            rel_id = row["relation_id"]
            
            f_logic = Fact(
                fact_id=f"fact_sched_logic_{rel_id}",
                project_id=project_id,
                fact_type="schedule.logic",
                subject_kind="activity",
                subject_id=row["succ_code"], # The successor 'owns' the dependency usually in P6 logic
                as_of={"file_version_id": snapshot_id},
                value_type=ValueType.JSON,
                value={
                    "predecessor": row["pred_code"],
                    "type": row["rel_type"],
                    "lag": row["lag"]
                },
                status=FactStatus.CANDIDATE,
                method_id="schedule_builder_v1",
                created_at=now,
                updated_at=now
            )
            f_logic.inputs.append(FactInput(file_version_id=snapshot_id, location={"table": "TASKPRED", "row_id": rel_id}))
            facts.append(f_logic)
        
        # 5. NEW: Aggregate/Computed Facts
        
        # 5a. Activity count by status
        for status_code, count in status_counts.items():
            f_status_count = Fact(
                fact_id=f"fact_sched_count_status_{status_code}_{snapshot_id[:8]}",
                project_id=project_id,
                fact_type="schedule.activity_count_by_status",
                subject_kind="project",
                subject_id=project_id,
                scope={"status": status_code},
                as_of={"file_version_id": snapshot_id},
                value_type=ValueType.NUM,
                value=count,
                unit="activities",
                status=FactStatus.CANDIDATE,
                method_id="schedule_builder_v1_aggregate",
                created_at=now,
                updated_at=now
            )
            f_status_count.inputs.append(FactInput(file_version_id=snapshot_id, location={"table": "p6_activities"}))
            facts.append(f_status_count)
        
        # 5b. Critical path activity count
        f_cp_count = Fact(
            fact_id=f"fact_sched_critical_count_{snapshot_id[:8]}",
            project_id=project_id,
            fact_type="schedule.critical_path_activity_count",
            subject_kind="project",
            subject_id=project_id,
            as_of={"file_version_id": snapshot_id},
            value_type=ValueType.NUM,
            value=len(critical_path_set),
            unit="activities",
            status=FactStatus.CANDIDATE,
            method_id="schedule_builder_v1_cpm",
            created_at=now,
            updated_at=now
        )
        f_cp_count.inputs.append(FactInput(file_version_id=snapshot_id, location={"table": "p6_activities"}))
        facts.append(f_cp_count)
        
        # 5c. Milestone forecast dates
        for milestone in milestone_activities:
            f_milestone = Fact(
                fact_id=f"fact_sched_milestone_{milestone['code']}_{snapshot_id[:8]}",
                project_id=project_id,
                fact_type="schedule.milestone_forecast_date",
                subject_kind="activity",
                subject_id=milestone["code"],
                as_of={"file_version_id": snapshot_id},
                value_type=ValueType.DATE,
                value=milestone["date"],
                status=FactStatus.CANDIDATE,
                method_id="schedule_builder_v1",
                created_at=now,
                updated_at=now
            )
            f_milestone.inputs.append(FactInput(file_version_id=snapshot_id, location={"table": "TASK"}))
            facts.append(f_milestone)

        logger.info(f"[ScheduleBuilder] Generated {len(facts)} facts ({len(critical_path_set)} critical activities)")
        return facts
    
    def _compute_critical_path(self, snapshot_id: str) -> Set[str]:
        """
        Compute critical path using CPM algorithm (forward/backward pass).
        Returns set of activity codes on the critical path.
        """
        # Load activities and relations
        activities_rows = self.db.execute(
            "SELECT activity_id, code, start_date, finish_date, total_float FROM p6_activities WHERE file_version_id = ?",
            (snapshot_id,)
        ).fetchall()
        
        relations_rows = self.db.execute(
            """
            SELECT 
                p.code as pred_code, 
                s.code as succ_code,
                r.rel_type,
                r.lag
            FROM p6_relations r
            JOIN p6_activities p ON r.pred_activity_id = p.activity_id
            JOIN p6_activities s ON r.succ_activity_id = s.activity_id
            WHERE r.file_version_id = ?
            """,
            (snapshot_id,)
        ).fetchall()
        
        if not activities_rows:
            return set()
        
        # Strategy 1: Use P6-provided total_float (most reliable if P6 computed correctly)
        # Activities with total_float <= 0 are on critical path
        critical_set = set()
        for row in activities_rows:
            r_dict = dict(row)
            total_float = r_dict.get("total_float")
            if total_float is not None and total_float <= 0:
                critical_set.add(r_dict["code"])
        
        # If P6 float is available and we found critical activities, trust it
        if critical_set:
            logger.info(f"[CPM] Using P6-provided float: {len(critical_set)} critical activities")
            return critical_set
        
        # Strategy 2: Fallback CPM calculation (if P6 float missing)
        # This is complex and requires proper forward/backward pass
        # For now, return empty set if P6 float not available
        logger.warning("[CPM] No total_float data from P6, critical path unknown")
        return set()
