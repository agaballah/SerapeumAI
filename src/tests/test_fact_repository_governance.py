# -*- coding: utf-8 -*-
"""
test_fact_repository_governance.py

Packet: Evidence Authority Gate (TASK-013)

Enforces the Evidence Quality Contract at the single fact-write path.
Rules:
  - Facts whose method_id maps to an unverified source extractor are demoted
    from VALIDATED to CANDIDATE before persistence.
  - Facts from trusted builders remain untouched.
  - Non-VALIDATED facts pass through unchanged.
"""

from pathlib import Path

from src.domain.facts.models import Fact, FactStatus
from src.domain.facts.repository import FactRepository
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


def _make_fact(fact_id, fact_type, status, method_id, value="test"):
    return Fact(
        fact_id=fact_id,
        project_id="proj1",
        fact_type=fact_type,
        subject_kind="document",
        subject_id="doc1",
        as_of={"file_version_id": "fv1"},
        value=value,
        status=status,
        method_id=method_id,
        created_at=1000,
        updated_at=1000,
    )


def test_save_facts_demotes_system_completion_builder_validated_to_candidate(tmp_path):
    """SystemCompletionBuilder produces VALIDATED from PLACEHOLDER FieldExtractor.
    The governance gate must demote these to CANDIDATE."""
    db = _build_db(tmp_path)
    repo = FactRepository(db)

    fact = _make_fact(
        "fact_field_mock_ir",
        "field.inspection",
        FactStatus.VALIDATED,
        "system_completion_builder_v1",
        value={"status": "APPROVED", "location": "Zone A-101"},
    )

    repo.save_facts([fact])

    row = db.execute(
        "SELECT status FROM facts WHERE fact_id=?", ("fact_field_mock_ir",)
    ).fetchone()
    assert row is not None
    assert row["status"] == FactStatus.CANDIDATE.value


def test_save_facts_preserves_document_builder_structural_validated(tmp_path):
    """DocumentBuilder structural facts come from PRODUCTION PDF extractor.
    These must remain VALIDATED."""
    db = _build_db(tmp_path)
    repo = FactRepository(db)

    fact = _make_fact(
        "fact_doc_page_count",
        "document.page_count",
        FactStatus.VALIDATED,
        "document_builder_v1",
        value=12,
    )

    repo.save_facts([fact])

    row = db.execute(
        "SELECT status FROM facts WHERE fact_id=?", ("fact_doc_page_count",)
    ).fetchone()
    assert row is not None
    assert row["status"] == FactStatus.VALIDATED.value


def test_save_facts_preserves_document_builder_semantic_validated(tmp_path):
    """DocumentBuilder semantic facts come from PRODUCTION PDF extractor.
    These remain VALIDATED (source is verified; regex quality is a separate concern)."""
    db = _build_db(tmp_path)
    repo = FactRepository(db)

    fact = _make_fact(
        "fact_doc_scope",
        "document.scope_item",
        FactStatus.VALIDATED,
        "document_builder.semantic_extract.v1",
        value="Generator room is in scope",
    )

    repo.save_facts([fact])

    row = db.execute(
        "SELECT status FROM facts WHERE fact_id=?", ("fact_doc_scope",)
    ).fetchone()
    assert row is not None
    assert row["status"] == FactStatus.VALIDATED.value


def test_save_facts_preserves_candidate_facts_unchanged(tmp_path):
    """CANDIDATE facts pass through the gate without modification."""
    db = _build_db(tmp_path)
    repo = FactRepository(db)

    fact = _make_fact(
        "fact_sched_act",
        "schedule.activity",
        FactStatus.CANDIDATE,
        "schedule_builder_v1",
        value={"name": "Pour concrete"},
    )

    repo.save_facts([fact])

    row = db.execute(
        "SELECT status FROM facts WHERE fact_id=?", ("fact_sched_act",)
    ).fetchone()
    assert row is not None
    assert row["status"] == FactStatus.CANDIDATE.value


def test_save_facts_preserves_human_certified_unchanged(tmp_path):
    """HUMAN_CERTIFIED facts are not touched by the gate."""
    db = _build_db(tmp_path)
    repo = FactRepository(db)

    fact = _make_fact(
        "fact_manual_cert",
        "schedule.activity",
        FactStatus.HUMAN_CERTIFIED,
        "authority_service",
        value={"name": "Manual cert test"},
    )

    repo.save_facts([fact])

    row = db.execute(
        "SELECT status FROM facts WHERE fact_id=?", ("fact_manual_cert",)
    ).fetchone()
    assert row is not None
    assert row["status"] == FactStatus.HUMAN_CERTIFIED.value


def test_save_facts_demotes_unknown_builder_validated(tmp_path):
    """Any VALIDATED fact from a method_id that is NOT in the allowlist is demoted.
    This prevents future builders from accidentally producing untrusted VALIDATED facts."""
    db = _build_db(tmp_path)
    repo = FactRepository(db)

    fact = _make_fact(
        "fact_future_unsafe",
        "some.future.type",
        FactStatus.VALIDATED,
        "unknown_future_builder_v1",
        value="test",
    )

    repo.save_facts([fact])

    row = db.execute(
        "SELECT status FROM facts WHERE fact_id=?", ("fact_future_unsafe",)
    ).fetchone()
    assert row is not None
    assert row["status"] == FactStatus.CANDIDATE.value


def test_save_facts_batch_mixed_statuses(tmp_path):
    """A mixed batch: some demoted, some preserved, some untouched."""
    db = _build_db(tmp_path)
    repo = FactRepository(db)

    facts = [
        _make_fact("f1", "field.inspection", FactStatus.VALIDATED, "system_completion_builder_v1"),
        _make_fact("f2", "document.page_count", FactStatus.VALIDATED, "document_builder_v1"),
        _make_fact("f3", "schedule.activity", FactStatus.CANDIDATE, "schedule_builder_v1"),
        _make_fact("f4", "bim.project", FactStatus.VALIDATED, "bim_builder_v1"),
        _make_fact("f5", "quality.ncr", FactStatus.VALIDATED, "system_completion_builder_v1"),
    ]

    repo.save_facts(facts)

    rows = {
        r["fact_id"]: r["status"]
        for r in db.execute("SELECT fact_id, status FROM facts ORDER BY fact_id").fetchall()
    }

    assert rows["f1"] == FactStatus.CANDIDATE.value   # demoted: system completion
    assert rows["f2"] == FactStatus.VALIDATED.value    # preserved: document structural
    assert rows["f3"] == FactStatus.CANDIDATE.value    # untouched: already CANDIDATE
    assert rows["f4"] == FactStatus.CANDIDATE.value    # demoted: bim_builder not in allowlist
    assert rows["f5"] == FactStatus.CANDIDATE.value    # demoted: system completion


def test_save_facts_empty_list_noop(tmp_path):
    """Saving an empty list is a no-op and does not raise."""
    db = _build_db(tmp_path)
    repo = FactRepository(db)
    repo.save_facts([])
    count = db.execute("SELECT COUNT(*) as c FROM facts").fetchone()["c"]
    assert count == 0


def test_save_facts_demotion_logs_warning(caplog, tmp_path):
    """The governance gate emits a logger.warning when demoting a fact."""
    import logging
    caplog.set_level(logging.WARNING)

    db = _build_db(tmp_path)
    repo = FactRepository(db)

    fact = _make_fact(
        "fact_warn_test",
        "field.inspection",
        FactStatus.VALIDATED,
        "system_completion_builder_v1",
    )

    with caplog.at_level(logging.WARNING, logger="src.domain.facts.repository"):
        repo.save_facts([fact])

    assert any("Evidence Authority Gate" in record.message for record in caplog.records)
    assert any("system_completion_builder_v1" in record.message for record in caplog.records)
