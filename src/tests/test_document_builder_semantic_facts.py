import json
from pathlib import Path

from src.engine.builders.document_builder import DocumentBuilder
from src.infra.persistence.database_manager import DatabaseManager


def _setup_db(tmp_path):
    db = DatabaseManager(root_dir=str(tmp_path), db_name=":memory:")
    base = Path("src/infra/persistence/migrations")
    db.execute_script((base / "001_baseline_v14.sql").read_text())
    v16 = base / "016_fix_missing_column.sql"
    if v16.exists():
        db.execute_script(v16.read_text())
    db.execute_script((base / "017_truth_engine_v2.sql").read_text())
    v18 = base / "018_fact_snapshots.sql"
    if v18.exists():
        db.execute_script(v18.read_text())
    db.project_id = "proj1"
    return db


def test_document_builder_emits_semantic_document_facts(tmp_path):
    db = _setup_db(tmp_path)
    snapshot_id = "fv_doc_001"
    doc_id = "doc_001"

    db.execute(
        "INSERT INTO file_registry (file_id, project_id, first_seen_path, created_at) VALUES (?, ?, ?, strftime('%s','now'))",
        ("file_001", "proj1", "generator_room_scope.pdf"),
    )
    db.execute(
        "INSERT INTO file_versions (file_version_id, file_id, source_path, sha256, size_bytes, file_ext, imported_at) VALUES (?, ?, ?, ?, ?, ?, strftime('%s','now'))",
        (snapshot_id, "file_001", "generator_room_scope.pdf", "abc", 1024, ".pdf"),
    )
    db.execute(
        "INSERT INTO documents (doc_id, project_id, file_name, abs_path, file_ext, file_hash, file_size, file_mtime, doc_title, doc_type, created, updated) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, strftime('%s','now'), strftime('%s','now'))",
        (doc_id, "proj1", "generator_room_scope.pdf", "generator_room_scope.pdf", ".pdf", "abc", 1024, 0.0, "Generator Room Scope", "pdf"),
    )
    db.execute(
        "INSERT INTO pdf_pages (page_id, file_version_id, page_no, text_content, metadata_json) VALUES (?, ?, ?, ?, ?)",
        (
            "pg1",
            snapshot_id,
            1,
            """Generator room is inscope\nGenerator room area is 377 sqm Approx.\nGenerator room scope includes the underground diesel tank\nContractor shall consider actual Generators size as per SEC approved vendor.""",
            json.dumps({"source": "unit-test"}),
        ),
    )
    db.execute(
        "INSERT INTO doc_blocks (doc_id, block_id, page_index, heading_title, heading_number, level, text, source_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (doc_id, "b1", 0, None, None, 0, "Generator room is inscope", "pdf"),
    )
    db.execute(
        "INSERT INTO doc_blocks (doc_id, block_id, page_index, heading_title, heading_number, level, text, source_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (doc_id, "b2", 0, None, None, 0, "Generator room area is 377 sqm Approx.", "pdf"),
    )
    db.execute(
        "INSERT INTO doc_blocks (doc_id, block_id, page_index, heading_title, heading_number, level, text, source_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (doc_id, "b3", 0, None, None, 0, "Generator room scope includes the underground diesel tank", "pdf"),
    )
    db.execute(
        "INSERT INTO doc_blocks (doc_id, block_id, page_index, heading_title, heading_number, level, text, source_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (doc_id, "b4", 0, None, None, 0, "Contractor shall consider actual Generators size as per SEC approved vendor.", "pdf"),
    )

    facts = DocumentBuilder(db).build("proj1", snapshot_id)
    fact_types = {f.fact_type for f in facts}

    assert "document.scope_item" in fact_types
    assert "document.area_approx" in fact_types
    assert "document.includes_component" in fact_types
    assert "document.requirement" in fact_types
    assert "document.vendor_basis" in fact_types

    area_fact = next(f for f in facts if f.fact_type == "document.area_approx")
    assert area_fact.status.value == "VALIDATED"
    assert area_fact.value["area"] == 377.0
    assert area_fact.value["approx"] is True
