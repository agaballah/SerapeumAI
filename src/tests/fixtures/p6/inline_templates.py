# -*- coding: utf-8 -*-
"""
P6/XER test templates — shared inline XER content for golden-fixture and unit tests.

Templates are written in latin-1 encoding to match production P6 export behavior.
Each template is a complete valid XER that can be fed directly to P6Extractor.
"""

# ── Standard project: 5 activities, full predecessor logic, mixed float values ──
XER_STANDARD = """\
%T\tPROJECT
%F\tproj_id\tproj_short_name
%R\tP1\tStandard Project
%T\tPROJWBS
%F\twbs_id\tproj_id\tparent_wbs_id\twbs_short_name\twbs_name
%R\tW1\tP1\t\tWBS\tMain WBS
%T\tTASK
%F\ttask_id\tproj_id\twbs_id\ttask_code\ttask_name\ttarget_start_date\ttarget_end_date\tstatus_code\ttotal_float_hr_cnt
%R\tA1\tP1\tW1\tA-001\tFoundation Work\t2026-01-01\t2026-01-05\tTK_Complete\t-8
%R\tA2\tP1\tW1\tA-002\tStructural Frame\t2026-01-06\t2026-01-15\tTK_Active\t0
%R\tA3\tP1\tW1\tA-003\tMEP Rough-in\t2026-01-16\t2026-01-25\tTK_Active\t16
%R\tA4\tP1\tW1\tA-004\tInterior Finishes\t2026-01-26\t2026-02-10\tTK_NotStarted\t40
%R\tA5\tP1\tW1\tA-005\tCommissioning\t2026-02-11\t2026-02-20\tTK_NotStarted\t80
%T\tTASKPRED
%F\tproj_id\ttask_id\tpred_task_id\tpred_type\tlag
%R\tP1\tA2\tA1\tFS\t0
%R\tP1\tA3\tA2\tFS\t0
%R\tP1\tA4\tA3\tFS\t0
%R\tP1\tA5\tA4\tFS\t0
"""

# ── Malformed float project: missing and non-numeric float values ──
XER_MALFORMED_FLOAT = """\
%T\tPROJECT
%F\tproj_id\tproj_short_name
%R\tP1\tMalformed Float Project
%T\tPROJWBS
%F\twbs_id\tproj_id\tparent_wbs_id\twbs_short_name\twbs_name
%R\tW1\tP1\t\tWBS\tMain WBS
%T\tTASK
%F\ttask_id\tproj_id\twbs_id\ttask_code\ttask_name\ttarget_start_date\ttarget_end_date\tstatus_code\ttotal_float_hr_cnt
%R\tA1\tP1\tW1\tA-001\tMissing Float Activity\t2026-01-01\t2026-01-05\tTK_Complete
%R\tA2\tP1\tW1\tA-002\tNonNumeric Float Activity\t2026-01-06\t2026-01-10\tTK_Active\tnot-a-number
%R\tA3\tP1\tW1\tA-003\tBlank Float Activity\t2026-01-11\t2026-01-15\tTK_Active\t
%T\tTASKPRED
%F\tproj_id\ttask_id\tpred_task_id\tpred_type\tlag
%R\tP1\tA2\tA1\tFS\t0
%R\tP1\tA3\tA2\tFS\t0
"""

# ── Parallel relations: two TASKPRED rows between same activity pair ──
XER_PARALLEL_RELATIONS = """\
%T\tPROJECT
%F\tproj_id\tproj_short_name
%R\tP1\tParallel Relations Project
%T\tPROJWBS
%F\twbs_id\tproj_id\tparent_wbs_id\twbs_short_name\twbs_name
%R\tW1\tP1\t\tWBS\tMain WBS
%T\tTASK
%F\ttask_id\tproj_id\twbs_id\ttask_code\ttask_name\ttarget_start_date\ttarget_end_date\tstatus_code\ttotal_float_hr_cnt
%R\tA1\tP1\tW1\tA-001\tPredecessor\t2026-01-01\t2026-01-05\tTK_Complete\t0
%R\tA2\tP1\tW1\tA-002\tSuccessor\t2026-01-06\t2026-01-10\tTK_Active\t8
%T\tTASKPRED
%F\tproj_id\ttask_id\tpred_task_id\tpred_type\tlag
%R\tP1\tA2\tA1\tFS\t0
%R\tP1\tA2\tA1\tSS\t16
"""

# ── Empty task list: valid headers but zero activity rows ──
XER_EMPTY_TASKS = """\
%T\tPROJECT
%F\tproj_id\tproj_short_name
%R\tP1\tEmpty Project
%T\tPROJWBS
%F\twbs_id\tproj_id\tparent_wbs_id\twbs_short_name\twbs_name
%R\tW1\tP1\t\tWBS\tMain WBS
%T\tTASK
%F\ttask_id\tproj_id\twbs_id\ttask_code\ttask_name\ttarget_start_date\ttarget_end_date\tstatus_code\ttotal_float_hr_cnt
%T\tTASKPRED
%F\tproj_id\ttask_id\tpred_task_id\tpred_type\tlag
"""
