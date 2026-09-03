# -*- coding: utf-8 -*-
"""
test_word_golden_minimal.py

Gold fixture regression test for the Word domain (Wave A pilot).
Proves that the VERIFIED WordExtractor emits only flattened pdf_page
records from a real .docx file — no typed Word persistence claims.
"""

import hashlib
from pathlib import Path

from src.engine.extractors.word_extractor import WordExtractor


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "office" / "golden_v1"
FIXTURE_PATH = FIXTURE_DIR / "minimal.docx"
EXPECTED_HASH = "322aaeae90012f391291812b7c79fcb06abcb65d88d90006ebada61bc853da58"
EXPECTED_SIZE = 36946


def test_golden_fixture_hash_matches_manifest():
    """The fixture file has not been corrupted or modified."""
    assert FIXTURE_PATH.exists(), f"Missing golden fixture: {FIXTURE_PATH}"
    data = FIXTURE_PATH.read_bytes()
    actual_hash = hashlib.sha256(data).hexdigest()
    assert actual_hash == EXPECTED_HASH, \
        "Fixture hash mismatch: expected %s, got %s" % (EXPECTED_HASH, actual_hash)
    assert len(data) == EXPECTED_SIZE, \
        "Fixture size mismatch: expected %d, got %d" % (EXPECTED_SIZE, len(data))


def test_extractor_selection_word():
    """The Word extractor is registered with VERIFIED maturity."""
    ext = WordExtractor()
    assert ext.id == "word-extractor-v1"
    assert ext.version == "1.0.0"
    assert ext.maturity == "VERIFIED"
    assert ".docx" in ext.supported_extensions
    assert ".doc" in ext.supported_extensions


def test_extraction_succeeds_and_is_deterministic():
    """Two consecutive extractions produce identical results."""
    ext = WordExtractor()
    result_a = ext.extract(str(FIXTURE_PATH))
    result_b = ext.extract(str(FIXTURE_PATH))

    assert result_a.success is True
    assert result_b.success is True
    assert result_a.records == result_b.records
    assert result_a.diagnostics == result_b.diagnostics
    # metadata may include file_size which is stable for a fixed file
    assert result_a.metadata["page_count"] == result_b.metadata["page_count"]
    assert result_a.metadata["char_count"] == result_b.metadata["char_count"]


def test_emits_only_pdf_page_records():
    """Word extraction must produce ONLY pdf_page records — no word_* typed claims."""
    result = WordExtractor().extract(str(FIXTURE_PATH))
    record_types = {rec["type"] for rec in result.records}
    assert record_types == {"pdf_page"}, \
        "Word extractor must emit only pdf_page records, found: %s" % record_types


def test_expected_text_is_preserved():
    """Known text strings from the fixture must appear in the extracted content."""
    result = WordExtractor().extract(str(FIXTURE_PATH))
    assert result.success is True
    texts = [rec["data"]["text_content"] for rec in result.records]
    combined = "\n".join(texts)

    assert "Generator Room Ventilation Requirements" in combined
    assert "HVAC systems" in combined
    assert "section 23 00 00" in combined.lower()
    assert "supply air unit" in combined.lower()
    assert "exhaust fan" in combined.lower()


def test_provenance_completeness_all_records():
    """Every record has non-empty provenance with source and page keys."""
    result = WordExtractor().extract(str(FIXTURE_PATH))
    for rec in result.records:
        prov = rec.get("provenance")
        assert prov is not None and isinstance(prov, dict), \
            "Record missing provenance: %s" % rec
        assert "source" in prov and prov["source"], \
            "Record missing provenance.source: %s" % rec["type"]
        assert "page" in prov and prov["page"], \
            "Record missing provenance.page: %s" % rec["type"]


def test_no_word_typed_records_or_fabricated_semantics():
    """Must not emit any word_* record types or fabricated semantic data."""
    result = WordExtractor().extract(str(FIXTURE_PATH))
    for rec in result.records:
        assert not rec["type"].startswith("word_"), \
            "Disallowed typed record found: %s" % rec["type"]
        assert not rec["type"].startswith("document.scope_item"), \
            "Semantic fact must not be fabricated from Word extraction"
        assert not rec["type"].startswith("document.requirement"), \
            "Semantic fact must not be fabricated from Word extraction"


def test_page_count_and_metadata_consistent():
    """Metadata page_count agrees with the number of pdf_page records."""
    result = WordExtractor().extract(str(FIXTURE_PATH))
    page_records = [r for r in result.records if r["type"] == "pdf_page"]
    assert result.metadata["page_count"] == len(page_records)
    assert result.metadata["char_count"] > 0
    assert "file_name" in result.metadata


def test_existing_behavior_preserved():
    """Golden fixture extraction does not introduce unexpected diagnostics."""
    result = WordExtractor().extract(str(FIXTURE_PATH))
    assert result.success is True
    for diag in result.diagnostics:
        assert "mock" not in diag.lower()
        assert "fake" not in diag.lower()
