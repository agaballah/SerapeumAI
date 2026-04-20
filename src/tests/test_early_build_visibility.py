from pathlib import Path
import sys

sys.path.insert(0, str(Path('.').resolve()))

from src.application.jobs.analyze_doc_job import AnalyzeDocJob
from src.application.jobs.build_facts_job import BuildFactsJob
from src.application.jobs.job_queue import SQLiteJobQueue
from src.infra.persistence.database_manager import DatabaseManager


def test_early_document_build_job_beats_analysis_in_queue(tmp_path):
    db = DatabaseManager(root_dir=str(tmp_path), db_name=':memory:')
    queue = SQLiteJobQueue(db)
    queue.register_job_type(BuildFactsJob)
    queue.register_job_type(AnalyzeDocJob)

    analyze = AnalyzeDocJob(job_id='analyze_1', project_id='proj1', doc_id='doc_1')
    early_build = BuildFactsJob(
        job_id='build_1',
        project_id='proj1',
        builder_type='document',
        snapshot_id='fv_1',
        priority=60,
    )

    queue.enqueue(analyze)
    queue.enqueue(early_build)

    next_job = queue.pick_next('proj1')
    assert next_job is not None
    assert next_job.type_name == 'BUILD_FACTS'
    assert next_job.builder_type == 'document'
    assert next_job.priority == 60


def test_build_facts_job_priority_round_trips_in_payload():
    job = BuildFactsJob(
        job_id='build_2',
        project_id='proj1',
        builder_type='document',
        snapshot_id='fv_2',
        priority=60,
    )

    payload = job.to_dict()
    rebuilt = BuildFactsJob.from_dict(payload)

    assert rebuilt.priority == 60
    assert rebuilt.builder_type == 'document'
    assert rebuilt.snapshot_id == 'fv_2'
