# -*- coding: utf-8 -*-
"""
test_full_production_evidence_path.py

End-to-end integration proof that the production evidence path works
through the Evidence Authority Gate:

  BuildFactsJob(document)
    → DocumentBuilder produces VALIDATED facts
      → FactRepository.save_facts() gate preserves them
        → CoverageGate sees trusted facts
          → QueryAPI returns certified data
"""

from pathlib import Path

import pytest

from src.application.api.fact_api import FactQueryAPI
from src.application.jobs.build_facts_job import BuildFactsJob
from src.application.services.coverage_gate import CoverageGate
from src.domain.facts.models import FactStatus
from src.engine.builders.document_builder import DocumentBuilder
from src.infra.persistence.database_manager import DatabaseManager


def _load_schema(db):
    base = Path("src/infra/persistence/migrations")
    db.execute_script((base / "001_baseline_v14.sql").read_text(encoding="utf-8"))
    v16 = base / "016_fix_missing_column.sql"
    if v16.exists():
        db.execute_script(v16.read_text(encoding="utf-8"))
    v17 = base / "017_truth_engine_v2.sql"
    if v17.exists():
        db.execute_script(v17.read_text(encoding="utf-8"))
    v18 = base / "018_fact_snapshots.sql"
    if v18.exists():
        db.execute_script(v18.read_text(encoding="utf-8"))


@pytest.fixture
def production_pipeline_db(tmp_path):
    db = DatabaseManager(root_dir=str(tmp_path), db_name=":memory:")
    _load_schema(db)

    project_id = "proj_prod_path"
    file_version_id = "fv_prod_001"
    doc_id = "doc_prod_001"
    now = db._ts()

    db.execute(
        "INSERT INTO projects (project_id, name, root, created, updated) VALUES (?, ?, ?, ?, ?)",
        (project_id, "Production Path Project", str(tmp_path), now, now),
    )
    db.execute(
        "INSERT INTO file_registry (file_id, project_id, first_seen_path, created_at) VALUES (?, ?, ?, ?)",
        ("file_prod", project_id, f"{tmp_path}/scope.pdf", now),
    )
    db.execute(
        "INSERT INTO file_versions (file_version_id, file_id, sha256, size_bytes, file_ext, imported_at, source_path) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (file_version_id, "file_prod", "sha-prod", 100, ".pdf", now, f"{tmp_path}/scope.pdf"),
    )
    db.execute(
        "INSERT INTO documents (doc_id, project_id, file_name, rel_path, abs_path, file_ext, file_hash, doc_title, content_text, created, updated) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (doc_id, project_id, "scope.pdf", "scope.pdf", f"{tmp_path}/scope.pdf", ".pdf", "sha-prod", "Scope Doc", "Scope content", now, now),
    )
    db.execute(
        "INSERT INTO pdf_pages (page_id, file_version_id, page_no, text_content, metadata_json) VALUES (?, ?, ?, ?, ?)",
        ("pg1", file_version_id, 1,
         "Generator room is inscope.\nGenerator room area is 377 sqm Approx.\nScope includes underground diesel tank.\nContractor shall consider approved vendor requirements.\nDetailed design required.",
         '{"source": "native_pdf_text"}'),
    )
    db.execute(
        "INSERT INTO doc_blocks (doc_id, block_id, page_index, heading_title, heading_number, level, text, source_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (doc_id, "b1", 0, None, None, 0, "Generator room is inscope", "pdf"),
    )
    db.execute(
        "INSERT INTO doc_blocks (doc_id, block_id, page_index, heading_title, heading_number, level, text, source_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (doc_id, "b2", 0, None, None, 0, "Generator room area is 377 sqm Approx.", "pdf"),
    )
    db.commit()
    return db, project_id, file_version_id, doc_id


def test_build_facts_job_produces_validated_facts_through_governance_gate(production_pipeline_db):
    """BuildFactsJob → DocumentBuilder → save_facts() gate → VALIDATED persisted."""
    db, project_id, file_version_id, doc_id = production_pipeline_db

    result = BuildFactsJob(
        job_id="build_prod_001",
        project_id=project_id,
        builder_type="document",
        snapshot_id=file_version_id,
    ).run({"db": db})

    assert result["count"] >= 5

    rows = db.execute(
        "SELECT fact_id, fact_type, status, method_id FROM facts WHERE project_id = ?",
        (project_id,),
    ).fetchall()

    validated = [r for r in rows if r["status"] == "VALIDATED"]
    assert validated, "At least one VALIDATED fact must be persisted through the gate"
    assert all(r["method_id"].startswith("document_builder") for r in validated)


def test_coverage_gate_passes_for_document_query_after_production_pipeline(production_pipeline_db):
    """CoverageGate must see the VALIDATED facts produced by the production path."""
    db, project_id, file_version_id, _doc_id = production_pipeline_db

    BuildFactsJob(
        job_id="build_prod_002",
        project_id=project_id,
        builder_type="document",
        snapshot_id=file_version_id,
    ).run({"db": db})

    gate = CoverageGate(db)
    result = gate.check("what is this document", project_id=project_id)

    assert result["is_complete"] is True
    assert result["missing_fact_types"] == []


def test_fact_query_api_returns_trusted_facts_from_production_pipeline(production_pipeline_db):
    """FactQueryAPI.get_certified_facts() must return the VALIDATED facts."""
    db, project_id, file_version_id, doc_id = production_pipeline_db

    BuildFactsJob(
        job_id="build_prod_003",
        project_id=project_id,
        builder_type="document",
        snapshot_id=file_version_id,
    ).run({"db": db})

    api = FactQueryAPI(db)
    result = api.get_certified_facts(
        query_intent="provide project scope summary",
        project_id=project_id,
        snapshot_id=file_version_id,
    )

    assert result["has_certified_data"] is True
    assert result["count"] >= 3

    fact_types = {f["fact_type"] for f in result["facts"]}
    assert "document.scope_item" in fact_types
    assert "document.requirement" in fact_types

    for fact in result["facts"]:
        assert fact["status"] in {"VALIDATED", "HUMAN_CERTIFIED"}, \
            f"Certified fact must be trusted status, got: {fact['status']}"
        assert fact["lineage"], f"Missing lineage for {fact['fact_id']}"
