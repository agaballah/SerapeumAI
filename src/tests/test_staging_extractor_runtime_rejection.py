# -*- coding: utf-8 -*-
"""
test_staging_extractor_runtime_rejection.py

Verifies that staging (EXPERIMENTAL/PLACEHOLDER) extractors are rejected
at runtime by ExtractJob. This is the second layer of defense beyond the
registry split — even if someone constructs an ExtractJob with a staging
extractor name, the job refuses it immediately.
"""

import pytest
from pathlib import Path

from src.application.jobs.extract_job import ExtractJob
from src.infra.persistence.database_manager import DatabaseManager


def _build_db(tmp_path):
    db = DatabaseManager(root_dir=str(tmp_path), db_name=":memory:")
    base = Path("src/infra/persistence/migrations")
    db.execute_script((base / "001_baseline_v14.sql").read_text(encoding="utf-8-sig"))
    v16 = base / "016_fix_missing_column.sql"
    if v16.exists():
        db.execute_script(v16.read_text(encoding="utf-8-sig"))
    v17 = base / "017_truth_engine_v2.sql"
    if v17.exists():
        db.execute_script(v17.read_text(encoding="utf-8-sig"))
    v18 = base / "018_fact_snapshots.sql"
    if v18.exists():
        db.execute_script(v18.read_text(encoding="utf-8-sig"))
    return db


@pytest.mark.parametrize("staging_key", ["field", "excel_register", "dgn"])
def test_extract_job_refuses_staging_extractors_at_runtime(tmp_path, staging_key):
    """Staging extractors must raise ValueError when referenced in ExtractJob.
    
    The registry lookup (line 108) fires after the file_version lookup (line 97),
    so we seed a valid file_version to reach the extractor check.
    """
    db = _build_db(tmp_path)
    now = db._ts()
    # file_versions has FK to file_registry — insert both rows
    db.execute(
        "INSERT INTO file_registry (file_id, project_id, first_seen_path, created_at) VALUES (?, ?, ?, ?)",
        ("file_test", "proj1", f"{tmp_path}/dummy", now),
    )
    db.execute(
        "INSERT INTO file_versions (file_version_id, file_id, sha256, size_bytes, file_ext, imported_at, source_path) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("fv_test", "file_test", "sha-test", 0, ".tmp", now, f"{tmp_path}/dummy"),
    )
    db.commit()

    job = ExtractJob(
        job_id="job_test",
        project_id="proj1",
        file_version_id="fv_test",
        extractor_name=staging_key,
    )
    with pytest.raises(ValueError, match="Unknown extractor"):
        job.run({"db": db})


def test_extract_job_accepts_trusted_extractors(tmp_path):
    """Trusted extractors must NOT raise 'Unknown extractor' for a valid name.
    They may fail later (missing file, etc.) but the registry lookup succeeds."""
    db = _build_db(tmp_path)
    job = ExtractJob(
        job_id="job_test",
        project_id="proj1",
        file_version_id="fv_nonexistent",
        extractor_name="pdf",
    )
    # Should NOT raise ValueError about unknown extractor — will fail on
    # file_version lookup instead, which is expected.
    with pytest.raises(ValueError, match="File Version not found"):
        job.run({"db": db})


def test_extract_job_accepts_all_trusted_keys(tmp_path):
    """All keys in EXTRACTORS must be accepted at the registry lookup stage."""
    db = _build_db(tmp_path)
    for key in ExtractJob.EXTRACTORS:
        job = ExtractJob(
            job_id=f"job_{key}",
            project_id="proj1",
            file_version_id="fv_nonexistent",
            extractor_name=key,
        )
        with pytest.raises(ValueError, match="File Version not found"):
            job.run({"db": db})
