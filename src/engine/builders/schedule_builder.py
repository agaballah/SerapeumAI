import logging
import json
from typing import List, Dict, Any, Optional, Set, Tuple
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
        critical_path_set, critical_path_known, critical_path_method = self._compute_critical_path(snapshot_id)
        
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
            
            # 3. Critical Path Membership
            # Only emit critical-path membership facts when the source schedule
            # contains usable total-float data. Without usable float and without
            # a CPM engine, critical path is unknown, not false.
            if critical_path_known:
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
                    method_id=f"schedule_builder_v1_{critical_path_method}",
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
        # Emit a zero count only when critical-path availability is known from
        # usable total-float data. If no usable float exists, do not convert
        # unknown critical path into a false zero-count fact.
        if critical_path_known:
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
                method_id=f"schedule_builder_v1_{critical_path_method}",
                created_at=now,
                updated_at=now
            )
            f_cp_count.inputs.append(FactInput(file_version_id=snapshot_id, location={"table": "p6_activities"}))
            facts.append(f_cp_count)
        else:
            logger.warning(
                "[ScheduleBuilder] Critical path facts skipped for snapshot %s because usable total_float data is unavailable.",
                snapshot_id,
            )
        
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
    
    def _compute_critical_path(self, snapshot_id: str) -> Tuple[Set[str], bool, str]:
        """
        Determine critical-path membership from P6-provided total float only.

        Returns:
            (critical_activity_codes, critical_path_known, method)

        This method intentionally does not run a fallback CPM engine. If no
        usable total-float values exist, critical path is unknown and downstream
        fact emission must not turn that into non-critical False / zero-count
        facts.
        """
        activities_rows = self.db.execute(
            "SELECT activity_id, code, total_float FROM p6_activities WHERE file_version_id = ?",
            (snapshot_id,)
        ).fetchall()
        
        if not activities_rows:
            return set(), False, "no_activities"
        
        critical_set: Set[str] = set()
        has_usable_float = False

        for row in activities_rows:
            r_dict = dict(row)
            total_float = r_dict.get("total_float")
            if total_float in (None, ""):
                continue

            try:
                total_float_value = float(total_float)
            except (TypeError, ValueError):
                continue

            has_usable_float = True
            if total_float_value <= 0:
                critical_set.add(r_dict["code"])
        
        if has_usable_float:
            logger.info(
                "[CPM] Using P6-provided total_float: %s critical activities",
                len(critical_set),
            )
            return critical_set, True, "p6_total_float"
        
        logger.warning(
            "[CPM] No usable total_float data from P6; critical path is unknown. "
            "No CPM fallback is enabled in this build."
        )
        return set(), False, "unknown_no_usable_total_float"
