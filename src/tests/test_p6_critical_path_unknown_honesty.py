# -*- coding: utf-8 -*-
from pathlib import Path

from src.application.jobs.extract_job import ExtractJob
from src.engine.builders.schedule_builder import ScheduleBuilder
from src.engine.extractors.p6_extractor import P6Extractor
from src.infra.persistence.database_manager import DatabaseManager


XER_BASE = """%T\tPROJECT
%F\tproj_id\tproj_short_name
%R\tP1\tDemo
%T\tPROJWBS
%F\twbs_id\tproj_id\tparent_wbs_id\twbs_short_name\twbs_name
%R\tW1\tP1\t\tWBS\tMain WBS
%T\tTASK
%F\ttask_id\tproj_id\twbs_id\ttask_code\ttask_name\ttarget_start_date\ttarget_end_date\tstatus_code\ttotal_float_hr_cnt
{task_rows}
%T\tTASKPRED
%F\tproj_id\ttask_id\tpred_task_id\tpred_type\tlag
%R\tP1\tA2\tA1\tFS\t0
"""


def _run_xer_to_facts(tmp_path, task_rows: str):
    db = DatabaseManager(root_dir=str(tmp_path), project_id="ProjectA")
    xer = XER_BASE.format(task_rows=task_rows)
    path = tmp_path / "schedule.xer"
    path.write_text(xer, encoding="latin-1")

    now = db._ts()
    db.execute(
        "INSERT INTO file_registry (file_id, project_id, first_seen_path, created_at) VALUES (?, ?, ?, ?)",
        ("file_p6", "ProjectA", str(path), now),
    )
    db.execute(
        "INSERT INTO file_versions (file_version_id, file_id, sha256, size_bytes, file_ext, imported_at, source_path) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("fv_p6", "file_p6", "hash-p6", path.stat().st_size, ".xer", now, str(path)),
    )
    db.commit()

    job = ExtractJob("job_p6", "ProjectA", "fv_p6", extractor_name="p6")
    result = P6Extractor().extract(str(path))
    assert result.success is True

    for record in result.records:
        job._insert_record(db, record, doc_id="doc_p6")

    facts = ScheduleBuilder(db).build("ProjectA", "fv_p6")
    return db, result, facts


def _facts_by_type(facts, fact_type):
    return [fact for fact in facts if fact.fact_type == fact_type]


def _critical_memberships(facts):
    return _facts_by_type(facts, "schedule.critical_path_membership")


def _critical_counts(facts):
    return _facts_by_type(facts, "schedule.critical_path_activity_count")


def test_valid_negative_and_positive_float_still_emits_known_critical_facts(tmp_path):
    _, _, facts = _run_xer_to_facts(
        tmp_path,
        "\n".join(
            [
                "%R\tA1\tP1\tW1\tA-001\tCritical Activity\t2026-01-01\t2026-01-05\tTK_Complete\t-8",
                "%R\tA2\tP1\tW1\tA-002\tNon Critical Activity\t2026-01-06\t2026-01-10\tTK_Active\t16",
            ]
        ),
    )

    memberships = {fact.subject_id: fact.value for fact in _critical_memberships(facts)}
    assert memberships == {"A-001": True, "A-002": False}

    counts = _critical_counts(facts)
    assert len(counts) == 1
    assert counts[0].value == 1
    assert counts[0].method_id == "schedule_builder_v1_p6_total_float"
    assert all(fact.status.value == "CANDIDATE" for fact in memberships and _critical_memberships(facts))


def test_all_positive_usable_float_is_known_zero_critical_path(tmp_path):
    _, _, facts = _run_xer_to_facts(
        tmp_path,
        "\n".join(
            [
                "%R\tA1\tP1\tW1\tA-001\tPositive Float Activity 1\t2026-01-01\t2026-01-05\tTK_Complete\t8",
                "%R\tA2\tP1\tW1\tA-002\tPositive Float Activity 2\t2026-01-06\t2026-01-10\tTK_Active\t16",
            ]
        ),
    )

    memberships = {fact.subject_id: fact.value for fact in _critical_memberships(facts)}
    assert memberships == {"A-001": False, "A-002": False}

    counts = _critical_counts(facts)
    assert len(counts) == 1
    assert counts[0].value == 0
    assert counts[0].method_id == "schedule_builder_v1_p6_total_float"


def test_missing_and_malformed_float_do_not_emit_false_or_zero_critical_path_facts(tmp_path):
    _, extraction, facts = _run_xer_to_facts(
        tmp_path,
        "\n".join(
            [
                "%R\tA1\tP1\tW1\tA-001\tMissing Float Activity\t2026-01-01\t2026-01-05\tTK_Complete",
                "%R\tA2\tP1\tW1\tA-002\tMalformed Float Activity\t2026-01-06\t2026-01-10\tTK_Active\tnot-a-number",
            ]
        ),
    )

    extracted_activities = [record for record in extraction.records if record["type"] == "p6_activity"]
    assert [activity["data"]["total_float"] for activity in extracted_activities] == [None, None]

    assert _critical_memberships(facts) == []
    assert _critical_counts(facts) == []

    assert _facts_by_type(facts, "schedule.activity")
    assert _facts_by_type(facts, "schedule.dates")
    assert _facts_by_type(facts, "schedule.logic")
    assert _facts_by_type(facts, "schedule.activity_count_by_status")


def test_schedule_builder_helper_reports_unknown_when_no_usable_float(tmp_path):
    db, _, _ = _run_xer_to_facts(
        tmp_path,
        "\n".join(
            [
                "%R\tA1\tP1\tW1\tA-001\tMissing Float Activity\t2026-01-01\t2026-01-05\tTK_Complete",
                "%R\tA2\tP1\tW1\tA-002\tBlank Float Activity\t2026-01-06\t2026-01-10\tTK_Active",
            ]
        ),
    )

    critical_set, known, method = ScheduleBuilder(db)._compute_critical_path("fv_p6")

    assert critical_set == set()
    assert known is False
    assert method == "unknown_no_usable_total_float"


def test_p6_visualizer_label_marks_gantt_as_raw_float_derived_not_certified_truth():
    source = Path("src/ui/panels/p6_visualizer.py").read_text(encoding="utf-8-sig")

    assert "Raw P6 staging Gantt" in source
    assert "float-derived, not certified critical-path truth" in source
    assert "Interactive Gantt | Click any bar to inspect Layer 4 Certified Facts" not in source
