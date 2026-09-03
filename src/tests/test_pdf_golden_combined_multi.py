# -*- coding: utf-8 -*-
"""
test_pdf_golden_combined_multi.py

Gold fixture regression test for multi-page PDF extraction.
Proves that the PRODUCTION UniversalPdfExtractor handles a 4-page real
.pdf file correctly: record counts, composition metadata, provenance,
and determinism.
"""

import hashlib
from pathlib import Path

from src.engine.extractors.pdf_extractor import UniversalPdfExtractor


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "pdf" / "golden_v1"
FIXTURE_PATH = FIXTURE_DIR / "pdf_combined_multi.pdf"
EXPECTED_HASH = "a8f5bcc22464484657483d68d1027e8149ce4af5145799544ea1744839bcc639"


def test_golden_fixture_hash_matches_manifest():
    """The fixture file has not been corrupted or modified."""
    assert FIXTURE_PATH.exists(), f"Missing golden fixture: {FIXTURE_PATH}"
    data = FIXTURE_PATH.read_bytes()
    actual_hash = hashlib.sha256(data).hexdigest()
    assert actual_hash == EXPECTED_HASH, (
        f"Fixture hash mismatch: expected {EXPECTED_HASH}, got {actual_hash}"
    )
    assert len(data) == 2521, f"Fixture size mismatch: expected 2521, got {len(data)}"


def test_extractor_selection_combined_multi():
    """The PDF extractor is registered and callable."""
    ext = UniversalPdfExtractor()
    assert ext.id == "universal-pdf-extractor-v1"
    assert ext.maturity == "PRODUCTION"
    assert ".pdf" in ext.supported_extensions


def test_extraction_succeeds_and_is_deterministic():
    """Two consecutive extractions produce identical results."""
    ext = UniversalPdfExtractor()
    result_a = ext.extract(str(FIXTURE_PATH))
    result_b = ext.extract(str(FIXTURE_PATH))

    assert result_a.success is True
    assert result_b.success is True
    assert result_a.records == result_b.records
    assert result_a.diagnostics == result_b.diagnostics
    assert result_a.metadata == result_b.metadata


def test_record_count_multi_page():
    """A 4-page PDF produces at least 4 pdf_page records plus classification and blocks."""
    result = UniversalPdfExtractor().extract(str(FIXTURE_PATH))
    page_records = [r for r in result.records if r["type"] == "pdf_page"]
    assert len(page_records) == 4
    # Plus doc_classification and doc_blocks
    all_types = {r["type"] for r in result.records}
    assert "doc_classification" in all_types
    assert "doc_blocks" in all_types


def test_all_pages_routed_as_vector():
    """All 4 pages in this fixture are vector composition (no images)."""
    result = UniversalPdfExtractor().extract(str(FIXTURE_PATH))
    for rec in result.records:
        if rec["type"] == "pdf_page":
            import json
            meta = json.loads(rec["data"]["metadata"])
            assert meta["composition"] == "vector", \
                f"Page {rec['data']['page_no']} expected 'vector', got '{meta['composition']}'"
            assert meta["method"] == "pypdf_vector"
            assert rec["provenance"]["composition"] == "vector"
            assert rec["provenance"]["method"] == "pypdf_vector"


def test_provenance_completeness_all_records():
    """Every record has a non-empty provenance dict with at least method or source."""
    result = UniversalPdfExtractor().extract(str(FIXTURE_PATH))
    for rec in result.records:
        prov = rec.get("provenance")
        assert prov is not None and isinstance(prov, dict), \
            f"Record missing provenance: {rec}"
        assert len(prov) > 0, f"Record has empty provenance: {rec['type']}"
        has_method_or_source = "method" in prov or "source" in prov
        assert has_method_or_source, \
            f"Record missing method/source in provenance: {rec['type']} prov={prov}"


def test_metadata_page_count_agrees():
    """metadata.pdf_page_count equals the number of pdf_page records."""
    result = UniversalPdfExtractor().extract(str(FIXTURE_PATH))
    page_records = [r for r in result.records if r["type"] == "pdf_page"]
    assert result.metadata["pdf_page_count"] == 4
    assert len(page_records) == 4
    counts = result.metadata["page_composition_counts"]
    assert counts["vector"] == 4
    assert counts["empty"] == 0
    assert counts["scanned"] == 0
    assert counts["combined"] == 0
    assert sum(counts.values()) == 4


def test_existing_behavior_preserved():
    """Golden fixture extraction does not introduce unexpected metadata fields."""
    result = UniversalPdfExtractor().extract(str(FIXTURE_PATH))
    assert result.success is True
    # These keys must exist (regression guard)
    assert "pdf_page_count" in result.metadata
    assert "page_composition_counts" in result.metadata
    assert "pdf_raw_metadata" in result.metadata
    # Page records must have required fields
    for rec in result.records:
        if rec["type"] == "pdf_page":
            assert "page_no" in rec["data"]
            assert "text_content" in rec["data"]
            assert "metadata" in rec["data"]
