# -*- coding: utf-8 -*-
from src.application.jobs.extract_job import ExtractJob
from src.engine.extractors.p6_extractor import P6Extractor
from src.infra.persistence.database_manager import DatabaseManager


XER_WITH_PARALLEL_RELATIONS = """%T\tPROJECT
%F\tproj_id\tproj_short_name
%R\tP1\tDemo
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


def _seed_db(tmp_path, xer_text):
    db = DatabaseManager(root_dir=str(tmp_path), project_id="ProjectA")
    path = tmp_path / "relations.xer"
    path.write_text(xer_text, encoding="latin-1")

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

    return db, path


def test_parallel_p6_relations_between_same_activities_are_not_collapsed(tmp_path):
    db, path = _seed_db(tmp_path, XER_WITH_PARALLEL_RELATIONS)

    extraction = P6Extractor().extract(str(path))
    assert extraction.success is True

    relation_records = [record for record in extraction.records if record["type"] == "p6_relation"]
    assert len(relation_records) == 2

    job = ExtractJob("job_p6", "ProjectA", "fv_p6", extractor_name="p6")
    for record in extraction.records:
        job._insert_record(db, record, doc_id="doc_p6")

    rows = db.execute(
        """
        SELECT relation_id, pred_activity_id, succ_activity_id, rel_type, lag
        FROM p6_relations
        WHERE file_version_id = ?
        ORDER BY rel_type, lag
        """,
        ("fv_p6",),
    ).fetchall()

    assert len(rows) == 2

    relation_ids = {row["relation_id"] for row in rows}
    assert len(relation_ids) == 2

    relation_pairs = {(row["pred_activity_id"], row["succ_activity_id"]) for row in rows}
    assert relation_pairs == {("A1", "A2")}

    relation_type_lag = {(row["rel_type"], float(row["lag"])) for row in rows}
    assert relation_type_lag == {("FS", 0.0), ("SS", 16.0)}


def test_single_p6_relation_still_persists_with_type_and_lag(tmp_path):
    xer_text = XER_WITH_PARALLEL_RELATIONS.replace("%R\tP1\tA2\tA1\tSS\t16\n", "")
    db, path = _seed_db(tmp_path, xer_text)

    extraction = P6Extractor().extract(str(path))
    assert extraction.success is True

    job = ExtractJob("job_p6", "ProjectA", "fv_p6", extractor_name="p6")
    for record in extraction.records:
        job._insert_record(db, record, doc_id="doc_p6")

    rows = db.execute(
        """
        SELECT relation_id, pred_activity_id, succ_activity_id, rel_type, lag
        FROM p6_relations
        WHERE file_version_id = ?
        """,
        ("fv_p6",),
    ).fetchall()

    assert len(rows) == 1
    row = rows[0]
    assert row["pred_activity_id"] == "A1"
    assert row["succ_activity_id"] == "A2"
    assert row["rel_type"] == "FS"
    assert float(row["lag"]) == 0.0
    assert row["relation_id"].startswith("A1_A2_")

