# -*- coding: utf-8 -*-
"""
test_file_inspector_evidence_lanes.py

Packet 5: File Inspector / document center evidence-lane closure.

Locks the release-critical invariant:

- Consolidated Review can combine high-level deterministic and AI highlights.
- Full Metadata exposes file/document/container metadata.
- Raw Deterministic Extraction contains deterministic parser/OCR/block output only.
- AI Output Only contains AI/VLM output only and is clearly non-governing.
"""

from pathlib import Path

import pytest

from src.application.services.file_inspector_presentation import build_file_inspector_payload
from src.infra.persistence.database_manager import DatabaseManager


@pytest.fixture
def inspector_db(tmp_path):
    db = DatabaseManager(root_dir=str(tmp_path), db_name=":memory:")

    db.execute(
        """
        CREATE TABLE file_versions (
            file_version_id TEXT,
            file_id TEXT,
            source_path TEXT,
            imported_at INTEGER,
            file_ext TEXT,
            sha256 TEXT
        )
        """
    )
    db.execute(
        """
        CREATE TABLE documents (
            doc_id TEXT,
            project_id TEXT,
            file_name TEXT,
            rel_path TEXT,
            abs_path TEXT,
            file_ext TEXT,
            meta_json TEXT,
            file_hash TEXT,
            doc_type TEXT,
            doc_title TEXT
        )
        """
    )
    db.execute(
        """
        CREATE TABLE pages (
            doc_id TEXT,
            page_index INTEGER,
            py_text TEXT,
            ocr_text TEXT,
            page_summary_short TEXT,
            page_summary_detailed TEXT,
            vision_general TEXT,
            vision_detailed TEXT,
            vision_ocr_text TEXT
        )
        """
    )
    db.execute(
        """
        CREATE TABLE doc_blocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id TEXT,
            block_id TEXT,
            page_index INTEGER,
            heading_title TEXT,
            heading_number TEXT,
            level INTEGER,
            text TEXT
        )
        """
    )
    db.execute(
        """
        CREATE TABLE extraction_runs (
            file_version_id TEXT,
            started_at INTEGER,
            status TEXT,
            extractor_id TEXT
        )
        """
    )

    source_path = str(tmp_path / "Pump-Specification.pdf")
    db.execute(
        "INSERT INTO file_versions VALUES (?, ?, ?, ?, ?, ?)",
        ("fv1", "file1", source_path, 1710000000, ".pdf", "abc123"),
    )
    db.execute(
        "INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "doc1",
            "proj1",
            "Pump-Specification.pdf",
            "Pump-Specification.pdf",
            source_path,
            ".pdf",
            '{"producer": "Bluebeam", "creator": "Design Authoring Tool", "software": "PDF Generator 1.0", "title": "Pump Specification"}',
            "abc123",
            "technical_specification",
            "Pump Specification",
        ),
    )
    db.execute(
        "INSERT INTO pages VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "doc1",
            0,
            "PUMP SHALL BE INSTALLED WITH ISOLATION VALVES",
            "OCR TEXT: pump tag P-101 appears in the schedule",
            "AI short summary: pump installation requirements",
            "AI detailed summary: the page appears to describe pump installation and isolation valve requirements",
            "AI vision review: engineering drawing symbols are visible",
            "AI detailed vision: visual inspection suggests pipework around pump skid",
            "AI OCR interpretation: extracted pump label P-101",
        ),
    )
    db.execute(
        "INSERT INTO doc_blocks (doc_id, block_id, page_index, heading_title, heading_number, level, text) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            "doc1",
            "b1",
            0,
            "Installation Requirements",
            "1.0",
            1,
            "Contractor shall verify access clearance before installation.",
        ),
    )
    db.execute(
        "INSERT INTO extraction_runs VALUES (?, ?, ?, ?)",
        ("fv1", 1710000010, "SUCCESS", "native_pdf"),
    )
    db.commit()

    try:
        yield db, "file1", source_path
    finally:
        db.close_all_connections()


def test_file_inspector_payload_has_all_four_required_lanes(inspector_db):
    db, file_id, source_path = inspector_db

    payload = build_file_inspector_payload(db, file_id=file_id, file_path=source_path)

    assert set(payload) >= {
        "title",
        "consolidated_review",
        "full_metadata",
        "raw_deterministic_extraction",
        "ai_output_only",
    }
    assert payload["title"] == "Pump-Specification.pdf"


def test_raw_deterministic_lane_excludes_ai_and_vlm_output(inspector_db):
    db, file_id, source_path = inspector_db

    payload = build_file_inspector_payload(db, file_id=file_id, file_path=source_path)
    raw = payload["raw_deterministic_extraction"]

    assert "Deterministic / parser extraction only" in raw
    assert "No AI narrative is included in this tab." in raw
    assert "[Direct Text]" in raw
    assert "PUMP SHALL BE INSTALLED WITH ISOLATION VALVES" in raw
    assert "[OCR / Parser Text]" in raw
    assert "OCR TEXT: pump tag P-101 appears in the schedule" in raw
    assert "[Structured Sections]" in raw
    assert "[Section] Installation Requirements" in raw

    assert "AI short summary" not in raw
    assert "AI detailed summary" not in raw
    assert "AI vision review" not in raw
    assert "AI detailed vision" not in raw
    assert "AI OCR interpretation" not in raw


def test_ai_output_lane_contains_only_ai_vlm_and_non_governing_warning(inspector_db):
    db, file_id, source_path = inspector_db

    payload = build_file_inspector_payload(db, file_id=file_id, file_path=source_path)
    ai = payload["ai_output_only"]

    assert "AI-generated / non-governing output only" in ai
    assert "does not represent certified truth by itself" in ai
    assert "[AI Summary]" in ai
    assert "[AI Detailed Summary]" in ai
    assert "[AI Vision Review]" in ai
    assert "[AI Detailed Vision]" in ai
    assert "[AI OCR Interpretation]" in ai

    assert "PUMP SHALL BE INSTALLED WITH ISOLATION VALVES" not in ai
    assert "OCR TEXT: pump tag P-101 appears in the schedule" not in ai
    assert "Contractor shall verify access clearance before installation." not in ai


def test_full_metadata_lane_exposes_file_document_and_container_metadata(inspector_db):
    db, file_id, source_path = inspector_db

    payload = build_file_inspector_payload(db, file_id=file_id, file_path=source_path)
    meta = payload["full_metadata"]

    assert '"file"' in meta
    assert '"document"' in meta
    assert '"container_metadata"' in meta
    assert '"ingestion"' in meta
    assert "Pump-Specification.pdf" in meta
    assert "technical_specification" in meta
    assert "Bluebeam" in meta
    assert "Design Authoring Tool" in meta
    assert "PDF Generator 1.0" in meta
    assert "abc123" in meta


def test_consolidated_review_combines_lanes_but_labels_extraction_and_ai_highlights(inspector_db):
    db, file_id, source_path = inspector_db

    payload = build_file_inspector_payload(db, file_id=file_id, file_path=source_path)
    review = payload["consolidated_review"]

    assert "File: Pump-Specification.pdf" in review
    assert "Document type: technical_specification" in review
    assert "Deterministic extraction coverage:" in review
    assert "AI interpretation coverage:" in review
    assert "Latest extraction run: SUCCESS using native_pdf" in review
    assert "Structured deterministic blocks: 1" in review
    assert "Readable review highlights" in review
    assert "Extraction p.1:" in review
    assert "AI review p.1:" in review


def test_file_inspector_payload_handles_missing_optional_tables_without_crashing(tmp_path):
    db = DatabaseManager(root_dir=str(tmp_path), db_name=":memory:")
    db.execute(
        """
        CREATE TABLE file_versions (
            file_version_id TEXT,
            file_id TEXT,
            source_path TEXT,
            imported_at INTEGER,
            file_ext TEXT,
            sha256 TEXT
        )
        """
    )
    db.execute(
        """
        CREATE TABLE documents (
            doc_id TEXT,
            project_id TEXT,
            file_name TEXT,
            rel_path TEXT,
            abs_path TEXT,
            file_ext TEXT,
            meta_json TEXT,
            file_hash TEXT,
            doc_type TEXT,
            doc_title TEXT
        )
        """
    )
    db.execute(
        """
        CREATE TABLE pages (
            doc_id TEXT,
            page_index INTEGER,
            py_text TEXT,
            ocr_text TEXT,
            page_summary_short TEXT,
            page_summary_detailed TEXT,
            vision_general TEXT,
            vision_detailed TEXT,
            vision_ocr_text TEXT
        )
        """
    )

    source_path = str(tmp_path / "Metadata-Only.pdf")
    db.execute(
        "INSERT INTO file_versions VALUES (?, ?, ?, ?, ?, ?)",
        ("fv_meta", "file_meta", source_path, 1710000000, ".pdf", "hash-meta"),
    )
    db.execute(
        "INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "doc_meta",
            "proj1",
            "Metadata-Only.pdf",
            "Metadata-Only.pdf",
            source_path,
            ".pdf",
            "{}",
            "hash-meta",
            "general_document",
            "Metadata Only",
        ),
    )
    db.commit()

    try:
        payload = build_file_inspector_payload(db, file_id="file_meta", file_path=source_path)
    finally:
        db.close_all_connections()

    assert payload["title"] == "Metadata-Only.pdf"
    assert "No readable review highlights recorded yet." in payload["consolidated_review"]
    assert "No deterministic extraction has been recorded yet." in payload["raw_deterministic_extraction"]
    assert "No AI-generated outputs have been recorded yet." in payload["ai_output_only"]
