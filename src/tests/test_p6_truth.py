from src.application.jobs.extract_job import ExtractJob
from src.engine.extractors.p6_extractor import P6Extractor
from src.engine.builders.schedule_builder import ScheduleBuilder
from src.infra.persistence.database_manager import DatabaseManager
from src.domain.models.page_record import PageRecord


XER_SAMPLE = """%T\tPROJECT\n%F\tproj_id\tproj_short_name\n%R\tP1\tDemo\n%T\tPROJWBS\n%F\twbs_id\tproj_id\tparent_wbs_id\twbs_short_name\twbs_name\n%R\tW1\tP1\t\tWBS\tMain WBS\n%T\tTASK\n%F\ttask_id\tproj_id\twbs_id\ttask_code\ttask_name\ttarget_start_date\ttarget_end_date\tstatus_code\ttotal_float_hr_cnt\n%R\tA1\tP1\tW1\tA-001\tCritical Activity\t2026-01-01\t2026-01-05\tTK_Complete\t-8\n%R\tA2\tP1\tW1\tA-002\tNon Critical Activity\t2026-01-06\t2026-01-10\tTK_Active\t16\n%T\tTASKPRED\n%F\tproj_id\ttask_id\tpred_task_id\tpred_type\tlag\n%R\tP1\tA2\tA1\tFS\t0\n"""


def test_p6_extractor_normalizes_float_days_and_criticality(tmp_path):
    path = tmp_path / 'demo.xer'
    path.write_text(XER_SAMPLE, encoding='latin-1')
    res = P6Extractor().extract(str(path))
    acts = [r for r in res.records if r['type'] == 'p6_activity']
    assert acts[0]['data']['total_float'] == -1.0
    assert acts[0]['data']['is_critical'] is True
    assert acts[1]['data']['total_float'] == 2.0
    assert acts[1]['data']['is_critical'] is False


def test_extract_job_persists_normalized_total_float_and_schedule_builder_uses_it(tmp_path):
    db = DatabaseManager(root_dir=str(tmp_path), project_id='ProjectA')
    path = tmp_path / 'demo.xer'
    path.write_text(XER_SAMPLE, encoding='latin-1')
    db.execute("INSERT INTO file_registry (file_id, project_id, first_seen_path, created_at) VALUES (?, ?, ?, ?)", ('file1', 'ProjectA', str(path), db._ts()))
    db.execute("INSERT INTO file_versions (file_version_id, file_id, sha256, size_bytes, file_ext, imported_at, source_path) VALUES (?, ?, ?, ?, ?, ?, ?)", ('fv1', 'file1', 'hash', path.stat().st_size, '.xer', db._ts(), str(path)))
    db.commit()
    job = ExtractJob('job1', 'ProjectA', 'fv1', extractor_name='p6')
    job.file_version_id = 'fv1'
    for rec in P6Extractor().extract(str(path)).records:
        job._insert_record(db, rec, doc_id='doc1')
    rows = db.execute('SELECT code, total_float FROM p6_activities ORDER BY code').fetchall()
    floats = {row['code']: row['total_float'] for row in rows}
    assert floats['A-001'] == -1.0
    assert floats['A-002'] == 2.0
    facts = ScheduleBuilder(db).build('ProjectA', 'fv1')
    critical = [f for f in facts if f.fact_type == 'schedule.critical_path_membership' and f.value is True]
    assert critical and critical[0].subject_id == 'A-001'
