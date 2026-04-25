# -*- coding: utf-8 -*-
"""
test_build_facts_evidence_closure.py

Packet 7: Extractor proof / build-facts evidence closure.

Locks the release-critical invariant:

- Persisted deterministic extraction evidence can produce VALIDATED document facts.
- BuildFactsJob can build and persist those facts without chat/runtime/LLM.
- FactQueryAPI can retrieve the produced trusted facts for the answer path.
- Fact lineage points back to the source file_version / extraction tables.
"""

from pathlib import Path

import pytest

from src.application.api.fact_api import FactQueryAPI
from src.application.jobs.build_facts_job import BuildFactsJob
from src.engine.builders.document_builder import DocumentBuilder
from src.infra.persistence.database_manager import DatabaseManager


def _load_schema(db: DatabaseManager) -> None:
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
def extracted_document_db(tmp_path):
    db = DatabaseManager(root_dir=str(tmp_path), db_name=":memory:")
    _load_schema(db)

    project_id = "proj_extractor_proof"
    file_id = "file_mechanical_scope"
    file_version_id = "fv_mechanical_scope_001"
    doc_id = "doc_mechanical_scope"
    source_path = str(tmp_path / "Mechanical-Scope.pdf")
    now = db._ts()

    db.execute(
        """
        INSERT INTO projects (project_id, name, root, created, updated)
        VALUES (?, ?, ?, ?, ?)
        """,
        (project_id, "Extractor Proof Project", str(tmp_path), now, now),
    )
    db.execute(
        """
        INSERT INTO file_registry (file_id, project_id, first_seen_path, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (file_id, project_id, source_path, now),
    )
    db.execute(
        """
        INSERT INTO file_versions
            (file_version_id, file_id, sha256, size_bytes, file_ext, imported_at, source_path)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (file_version_id, file_id, "sha-mechanical-scope", 12345, ".pdf", now, source_path),
    )
    db.execute(
        """
        INSERT INTO documents
            (doc_id, project_id, file_name, rel_path, abs_path, file_ext,
             file_hash, doc_type, doc_title, content_text, meta_json, created, updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            doc_id,
            project_id,
            "Mechanical-Scope.pdf",
            "Mechanical-Scope.pdf",
            source_path,
            ".pdf",
            "sha-mechanical-scope",
            "technical_specification",
            "Mechanical Scope",
            "Mechanical scope extracted content",
            '{"producer": "deterministic-parser"}',
            now,
            now,
        ),
    )
    db.execute(
        """
        INSERT INTO pdf_pages (page_id, file_version_id, page_no, text_content, metadata_json)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            "page_mech_001",
            file_version_id,
            1,
            "Generator room is in scope. Scope includes underground diesel tank. "
            "Contractor shall consider approved vendor requirements as per Vendor Manual. "
            "Detailed design required. Area is 45 square meters approx.",
            '{"source": "native_pdf_text"}',
        ),
    )
    db.execute(
        """
        INSERT INTO doc_blocks
            (doc_id, block_id, page_index, heading_title, heading_number, level, text, source_type, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            doc_id,
            "block_scope_001",
            0,
            "Mechanical Scope Requirements",
            "1.0",
            1,
            "Generator room is in scope.\n"
            "Scope includes underground diesel tank.\n"
            "Contractor shall consider approved vendor requirements as per Vendor Manual.\n"
            "Detailed design required.\n"
            "Area is 45 square meters approx.",
            "pdf",
            now,
        ),
    )
    db.commit()

    try:
        yield db, project_id, file_version_id, doc_id, source_path
    finally:
        db.close_all_connections()


def test_document_builder_builds_validated_facts_from_persisted_extraction_evidence(
    extracted_document_db,
):
    db, project_id, file_version_id, doc_id, _source_path = extracted_document_db

    facts = DocumentBuilder(db).build(project_id, file_version_id)
    fact_by_type = {fact.fact_type: fact for fact in facts}

    assert fact_by_type["document.page_count"].status.value == "VALIDATED"
    assert fact_by_type["document.has_text"].status.value == "VALIDATED"
    assert fact_by_type["document.profile"].status.value == "VALIDATED"

    assert fact_by_type["document.page_count"].value == 1
    assert fact_by_type["document.has_text"].value is True
    assert fact_by_type["document.profile"].value["doc_title"] == "Mechanical Scope"

    assert "document.scope_item" in fact_by_type
    assert "document.includes_component" in fact_by_type
    assert "document.requirement" in fact_by_type
    assert "document.area_approx" in fact_by_type
    assert "document.design_obligation" in fact_by_type
    assert "document.vendor_basis" in fact_by_type

    for fact in facts:
        assert fact.project_id == project_id
        assert fact.subject_kind == "document"
        assert fact.subject_id == doc_id
        assert fact.as_of["file_version_id"] == file_version_id
        assert fact.inputs, f"Missing lineage input for {fact.fact_id}"
        assert fact.inputs[0].file_version_id == file_version_id


def test_build_facts_job_persists_document_facts_without_chat_or_runtime(
    extracted_document_db,
):
    db, project_id, file_version_id, _doc_id, _source_path = extracted_document_db

    job = BuildFactsJob(
        job_id="build_doc_facts_001",
        project_id=project_id,
        builder_type="document",
        snapshot_id=file_version_id,
    )
    result = job.run({"db": db})

    assert result["count"] >= 8

    rows = db.execute(
        """
        SELECT fact_id, fact_type, status, method_id
        FROM facts
        WHERE project_id = ?
        ORDER BY fact_type
        """,
        (project_id,),
    ).fetchall()
    persisted_types = {row["fact_type"] for row in rows}

    assert "document.page_count" in persisted_types
    assert "document.has_text" in persisted_types
    assert "document.profile" in persisted_types
    assert "document.scope_item" in persisted_types
    assert "document.requirement" in persisted_types

    trusted_rows = [row for row in rows if row["status"] == "VALIDATED"]
    assert trusted_rows
    assert all(row["method_id"].startswith("document_builder") for row in trusted_rows)

    lineage_count = db.execute("SELECT count(*) FROM fact_inputs").fetchone()[0]
    assert lineage_count >= len(rows)


def test_fact_query_api_can_retrieve_build_facts_output_as_trusted_context(
    extracted_document_db,
):
    db, project_id, file_version_id, _doc_id, source_path = extracted_document_db

    BuildFactsJob(
        job_id="build_doc_facts_002",
        project_id=project_id,
        builder_type="document",
        snapshot_id=file_version_id,
    ).run({"db": db})

    result = FactQueryAPI(db).get_certified_facts(
        query_intent="provide project scope summary",
        project_id=project_id,
        snapshot_id=file_version_id,
    )

    assert result["has_certified_data"] is True
    assert result["count"] >= 4

    facts = result["facts"]
    fact_types = {fact["fact_type"] for fact in facts}
    assert "document.scope_item" in fact_types
    assert "document.includes_component" in fact_types
    assert "document.requirement" in fact_types

    context = result["formatted_context"]
    assert "### TRUSTED FACTS" in context
    assert "document.scope_item" in context
    assert "document.requirement" in context
    assert "Generator room" in context or "generator room" in context

    for fact in facts:
        assert fact["status"] in {"VALIDATED", "HUMAN_CERTIFIED"}
        assert fact["lineage"], f"Missing lineage for {fact['fact_id']}"
        assert fact["lineage"][0]["file_version_id"] == file_version_id
        assert fact["lineage"][0]["source_path"] == source_path


def test_unknown_build_facts_builder_type_fails_loudly(extracted_document_db):
    db, project_id, file_version_id, _doc_id, _source_path = extracted_document_db

    job = BuildFactsJob(
        job_id="build_unknown_001",
        project_id=project_id,
        builder_type="not_a_builder",
        snapshot_id=file_version_id,
    )

    with pytest.raises(ValueError, match="Unknown builder type"):
        job.run({"db": db})
