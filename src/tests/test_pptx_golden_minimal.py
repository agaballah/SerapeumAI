# -*- coding: utf-8 -*-
"""
test_pptx_golden_minimal.py

Gold fixture regression test for the PPTX domain (Wave A pilot).
Proves that the VERIFIED PPTXExtractor emits only flattened pdf_page
records — one per slide — with no typed PPTX persistence claims.
"""

import hashlib
from pathlib import Path

from src.engine.extractors.pptx_extractor import PPTXExtractor


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "office" / "golden_v1"
FIXTURE_PATH = FIXTURE_DIR / "minimal.pptx"
EXPECTED_HASH = "831e55f7a8abfe26e57fccb80b903e18ca1fbe8614d3c8f2a0c44819232a32a8"
EXPECTED_SIZE = 29307


def test_golden_fixture_hash_matches_manifest():
    """The fixture file has not been corrupted or modified."""
    assert FIXTURE_PATH.exists(), f"Missing golden fixture: {FIXTURE_PATH}"
    data = FIXTURE_PATH.read_bytes()
    actual_hash = hashlib.sha256(data).hexdigest()
    assert actual_hash == EXPECTED_HASH, \
        "Fixture hash mismatch: expected %s, got %s" % (EXPECTED_HASH, actual_hash)
    assert len(data) == EXPECTED_SIZE, \
        "Fixture size mismatch: expected %d, got %d" % (EXPECTED_SIZE, len(data))


def test_extractor_selection_pptx():
    """The PPTX extractor is registered with VERIFIED maturity."""
    ext = PPTXExtractor()
    assert ext.id == "pptx-extractor-v1"
    assert ext.version == "1.0.0"
    assert ext.maturity == "VERIFIED"
    assert ".pptx" in ext.supported_extensions


def test_extraction_succeeds_and_is_deterministic():
    """Two consecutive extractions produce identical results."""
    ext = PPTXExtractor()
    result_a = ext.extract(str(FIXTURE_PATH))
    result_b = ext.extract(str(FIXTURE_PATH))

    assert result_a.success is True
    assert result_b.success is True
    assert result_a.records == result_b.records
    assert result_a.diagnostics == result_b.diagnostics
    assert result_a.metadata["page_count"] == result_b.metadata["page_count"]
    assert result_a.metadata["char_count"] == result_b.metadata["char_count"]


def test_emits_only_pdf_page_records():
    """PPTX extraction must produce ONLY pdf_page records — no pptx_* typed claims."""
    result = PPTXExtractor().extract(str(FIXTURE_PATH))
    record_types = {rec["type"] for rec in result.records}
    assert record_types == {"pdf_page"}, \
        "PPTX extractor must emit only pdf_page records, found: %s" % record_types


def test_one_record_per_slide():
    """Each slide in the fixture produces exactly one pdf_page record."""
    result = PPTXExtractor().extract(str(FIXTURE_PATH))
    page_records = [r for r in result.records if r["type"] == "pdf_page"]
    # Our fixture has 2 slides
    assert len(page_records) == 2, \
        "Expected 2 page records (one per slide), got %d" % len(page_records)
    # Page numbers must be sequential starting from 1
    page_nums = sorted(r["data"]["page_no"] for r in page_records)
    assert page_nums == [1, 2], "Page numbers should be [1, 2], got %s" % page_nums


def test_expected_text_is_preserved():
    """Known text from both slides must appear in extracted content."""
    result = PPTXExtractor().extract(str(FIXTURE_PATH))
    texts = [rec["data"]["text_content"] for rec in result.records]
    combined = "\n".join(texts)

    assert "Generator Room Ventilation" in combined
    assert "Equipment Schedule" in combined
    assert "Supply Air Unit" in combined or "supply air unit" in combined.lower()
    assert "Exhaust Fan" in combined or "exhaust fan" in combined.lower()
    assert "Section 23 00 00" in combined


def test_provenance_completeness_all_records():
    """Every record has non-empty provenance with source and page keys."""
    result = PPTXExtractor().extract(str(FIXTURE_PATH))
    for rec in result.records:
        prov = rec.get("provenance")
        assert prov is not None and isinstance(prov, dict), \
            "Record missing provenance: %s" % rec
        assert "source" in prov and prov["source"], \
            "Record missing provenance.source: %s" % rec["type"]
        assert "page" in prov and prov["page"], \
            "Record missing provenance.page: %s" % rec["type"]


def test_no_pptx_typed_records_or_fabricated_semantics():
    """Must not emit any pptx_* record types or fabricated semantic data."""
    result = PPTXExtractor().extract(str(FIXTURE_PATH))
    for rec in result.records:
        assert not rec["type"].startswith("pptx_"), \
            "Disallowed typed record found: %s" % rec["type"]
        assert not rec["type"].startswith("document.scope_item"), \
            "Semantic fact must not be fabricated from PPTX extraction"
        assert not rec["type"].startswith("document.requirement"), \
            "Semantic fact must not be fabricated from PPTX extraction"


def test_page_count_and_metadata_consistent():
    """Metadata page_count agrees with the number of pdf_page records."""
    result = PPTXExtractor().extract(str(FIXTURE_PATH))
    page_records = [r for r in result.records if r["type"] == "pdf_page"]
    assert result.metadata["page_count"] == len(page_records)
    assert result.metadata["char_count"] > 0
    assert "file_name" in result.metadata


def test_existing_behavior_preserved():
    """Golden fixture extraction does not introduce unexpected diagnostics."""
    result = PPTXExtractor().extract(str(FIXTURE_PATH))
    assert result.success is True
    for diag in result.diagnostics:
        assert "mock" not in diag.lower()
        assert "fake" not in diag.lower()
