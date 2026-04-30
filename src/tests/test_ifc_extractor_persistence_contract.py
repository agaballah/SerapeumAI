# -*- coding: utf-8 -*-
from pathlib import Path

from src.application.jobs.extract_job import ExtractJob
from src.infra.persistence.database_manager import DatabaseManager


def _build_db(tmp_path):
    db = DatabaseManager(root_dir=str(tmp_path), db_name=":memory:")
    migration = Path("src/infra/persistence/migrations/001_baseline_v14.sql")
    db.execute_script(migration.read_text(encoding="utf-8-sig"))

    now = db._ts()
    source_path = str(tmp_path / "model.ifc")

    db.execute(
        "INSERT INTO file_registry (file_id, project_id, first_seen_path, created_at) VALUES (?, ?, ?, ?)",
        ("file_ifc", "ProjectA", source_path, now),
    )
    db.execute(
        "INSERT INTO file_versions (file_version_id, file_id, sha256, size_bytes, file_ext, imported_at, source_path) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("fv_ifc", "file_ifc", "hash-ifc", 1, ".ifc", now, source_path),
    )
    db.commit()

    return db


def test_ifc_element_metadata_records_are_persisted_to_ifc_elements(tmp_path):
    db = _build_db(tmp_path)
    job = ExtractJob("job_ifc", "ProjectA", "fv_ifc", extractor_name="ifc")

    job._insert_record(
        db,
        {
            "type": "ifc_element_metadata",
            "data": {
                "EntityType": "IfcWall",
                "ElementId": "wall-guid-001",
                "PSetName": "Pset_WallCommon",
                "Properties": {"FireRating": "2HR"},
                "IsQuantity": False,
            },
            "provenance": {"entity": "IfcWall", "pset": "Pset_WallCommon"},
        },
        doc_id="doc_ifc",
    )

    row = db.execute(
        "SELECT element_id, entity_type, raw_properties_json FROM ifc_elements WHERE element_id=?",
        ("wall-guid-001",),
    ).fetchone()

    assert row is not None
    assert row["entity_type"] == "IfcWall"
    assert "Pset_WallCommon" in row["raw_properties_json"]
    assert "FireRating" in row["raw_properties_json"]


def test_ifc_connection_records_are_persisted_to_links(tmp_path):
    db = _build_db(tmp_path)
    job = ExtractJob("job_ifc", "ProjectA", "fv_ifc", extractor_name="ifc")

    job._insert_record(
        db,
        {
            "type": "ifc_connection",
            "data": {
                "RelType": "Connectivity",
                "Element1Id": "wall-guid-001",
                "Element2Id": "slab-guid-002",
            },
            "provenance": {"entity": "IfcRelConnectsElements"},
        },
        doc_id="doc_ifc",
    )

    row = db.execute(
        "SELECT project_id, link_type, from_kind, from_id, to_kind, to_id, status FROM links WHERE link_type=?",
        ("ifc.connection",),
    ).fetchone()

    assert row is not None
    assert row["project_id"] == "ProjectA"
    assert row["from_kind"] == "ifc_element"
    assert row["from_id"] == "wall-guid-001"
    assert row["to_kind"] == "ifc_element"
    assert row["to_id"] == "slab-guid-002"
    assert row["status"] == "CANDIDATE"
