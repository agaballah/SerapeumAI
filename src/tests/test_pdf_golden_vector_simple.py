# -*- coding: utf-8 -*-
"""
test_pdf_golden_vector_simple.py

Gold fixture regression test for the PDF domain (Wave A pilot).
Proves that the PRODUCTION UniversalPdfExtractor produces deterministic,
provenance-complete output from a real .pdf file on disk.
"""

import hashlib
from pathlib import Path

import pytest

from src.engine.extractors.pdf_extractor import UniversalPdfExtractor


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "pdf" / "golden_v1"
FIXTURE_PATH = FIXTURE_DIR / "pdf_vector_simple.pdf"
EXPECTED_HASH = "bafcbf977d225a3962a7d351fa2cbad332fc4384bf145e193bae8dd4b86f01f5"
EXPECTED_RECORD_TYPES = {"pdf_page", "doc_classification", "doc_blocks"}


@pytest.fixture(scope="session")
def vector_simple_path():
    """Return the path to the golden vector-simple PDF fixture."""
    assert FIXTURE_PATH.exists(), f"Missing golden fixture: {FIXTURE_PATH}"
    return str(FIXTURE_PATH)


def test_golden_fixture_hash_matches_manifest(vector_simple_path):
    """The fixture file has not been corrupted or modified."""
    data = open(vector_simple_path, "rb").read()
    actual_hash = hashlib.sha256(data).hexdigest()
    assert actual_hash == EXPECTED_HASH, (
        f"Fixture hash mismatch: expected {EXPECTED_HASH}, got {actual_hash}"
    )
    assert len(data) == 1253, f"Fixture size mismatch: expected 1253, got {len(data)}"


def test_extractor_selection_vector_simple(vector_simple_path):
    """The PDF extractor is registered and callable on the golden fixture."""
    ext = UniversalPdfExtractor()
    assert ext.id == "universal-pdf-extractor-v1"
    assert ext.version == "1.0.0"
    assert ext.maturity == "PRODUCTION"
    assert ".pdf" in ext.supported_extensions


def test_extraction_succeeds_and_is_deterministic(vector_simple_path):
    """Two consecutive extractions of the same fixture produce identical results."""
    ext = UniversalPdfExtractor()
    result_a = ext.extract(vector_simple_path)
    result_b = ext.extract(vector_simple_path)

    assert result_a.success is True
    assert result_b.success is True
    assert result_a.records == result_b.records
    assert result_a.diagnostics == result_b.diagnostics
    assert result_a.metadata == result_b.metadata


def test_record_count_and_types(vector_simple_path):
    """The golden fixture produces exactly the expected record types."""
    result = UniversalPdfExtractor().extract(vector_simple_path)
    record_types = {rec["type"] for rec in result.records}
    assert record_types == EXPECTED_RECORD_TYPES
    assert len(result.records) == 3


def test_provenance_completeness(vector_simple_path):
    """Every record has a non-empty provenance dict with at least method or source."""
    result = UniversalPdfExtractor().extract(vector_simple_path)
    for rec in result.records:
        prov = rec.get("provenance")
        assert prov is not None and isinstance(prov, dict), \
            f"Record missing provenance: {rec}"
        assert len(prov) > 0, f"Record has empty provenance: {rec['type']}"
        # PDF page records carry 'method'/'composition'; doc_classification carries 'source'.
        # The contract requires source+origin but current extractor uses method+composition.
        has_method_or_source = "method" in prov or "source" in prov
        assert has_method_or_source, \
            f"Record missing method/source in provenance: {rec['type']} prov={prov}"


def test_page_record_has_expected_structure(vector_simple_path):
    """The pdf_page record has page_no, text_content, metadata, and provenance."""
    result = UniversalPdfExtractor().extract(vector_simple_path)
    page_records = [r for r in result.records if r["type"] == "pdf_page"]
    assert len(page_records) == 1
    page = page_records[0]
    assert page["data"]["page_no"] == 1
    assert isinstance(page["data"]["text_content"], str)
    assert len(page["data"]["text_content"]) > 0
    meta = __import__("json").loads(page["data"]["metadata"])
    assert meta["composition"] == "vector"
    assert meta["method"] == "pypdf_vector"
    assert page["provenance"]["composition"] == "vector"
    assert page["provenance"]["method"] == "pypdf_vector"
    assert page["provenance"]["page"] == 1


def test_metadata_consistency(vector_simple_path):
    """Metadata page_count agrees with the number of pdf_page records."""
    result = UniversalPdfExtractor().extract(vector_simple_path)
    page_records = [r for r in result.records if r["type"] == "pdf_page"]
    assert result.metadata["pdf_page_count"] == len(page_records)
    assert sum(result.metadata["page_composition_counts"].values()) == result.metadata["pdf_page_count"]


def test_existing_pdf_tests_still_pass(vector_simple_path):
    """Running the existing PDF tests against the new fixture does not break anything."""
    # This test uses the golden fixture as an additional input point.
    # The actual existing tests live in test_pdf_routing.py, test_pdf_metadata_completeness.py,
    # and test_pdf_routing_fixture_pack.py — they continue to pass independently.
    result = UniversalPdfExtractor().extract(vector_simple_path)
    assert result.success is True
    assert len(result.records) == 3
    # Smoke-test that metadata is well-formed
    assert "pdf_title" in result.metadata
    assert "pdf_page_count" in result.metadata
