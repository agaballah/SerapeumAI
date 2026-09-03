# -*- coding: utf-8 -*-
"""
test_excel_golden_submittal_register.py

Gold fixture regression test for the Excel Register domain (Wave A pilot).
Proves that the EXPERIMENTAL ExcelRegisterExtractor produces deterministic,
provenance-complete output from a real .xlsx file with AECO register data.
"""

import hashlib
from pathlib import Path

from src.engine.extractors.register_extractor import ExcelRegisterExtractor


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "excel" / "golden_v1"
FIXTURE_PATH = FIXTURE_DIR / "submittal_register.xlsx"
EXPECTED_HASH = "fef9169c2431b368c2c0ff35b1629fe1fa165f8cb1eb6ff43a6f691c64c0a17b"
EXPECTED_SIZE = 5274


def test_golden_fixture_hash_matches_manifest():
    """The fixture file has not been corrupted or modified."""
    assert FIXTURE_PATH.exists(), f"Missing golden fixture: {FIXTURE_PATH}"
    data = FIXTURE_PATH.read_bytes()
    actual_hash = hashlib.sha256(data).hexdigest()
    assert actual_hash == EXPECTED_HASH, \
        "Fixture hash mismatch: expected %s, got %s" % (EXPECTED_HASH, actual_hash)
    assert len(data) == EXPECTED_SIZE, \
        "Fixture size mismatch: expected %d, got %d" % (EXPECTED_SIZE, len(data))


def test_extractor_selection_excel_register():
    """The Excel Register extractor is registered with EXPERIMENTAL maturity."""
    ext = ExcelRegisterExtractor()
    assert ext.id == "excel-register-extractor-v1"
    assert ext.version == "1.0.0"
    assert ext.maturity == "EXPERIMENTAL"
    assert ".xlsx" in ext.supported_extensions
    assert ".xls" in ext.supported_extensions


def test_extraction_succeeds_and_is_deterministic():
    """Two consecutive extractions produce identical results."""
    ext = ExcelRegisterExtractor()
    result_a = ext.extract(str(FIXTURE_PATH))
    result_b = ext.extract(str(FIXTURE_PATH))

    assert result_a.success is True
    assert result_b.success is True
    assert result_a.records == result_b.records
    assert result_a.diagnostics == result_b.diagnostics


def test_all_records_are_register_row_type():
    """All extracted records must be type 'register_row' — no typed claims for other types."""
    result = ExcelRegisterExtractor().extract(str(FIXTURE_PATH))
    record_types = {rec["type"] for rec in result.records}
    assert record_types == {"register_row"}, \
        "Expected only register_row records, found: %s" % record_types


def test_expected_row_count():
    """The fixture has 5 data rows; all should be extracted."""
    result = ExcelRegisterExtractor().extract(str(FIXTURE_PATH))
    register_rows = [r for r in result.records if r["type"] == "register_row"]
    assert len(register_rows) == 5, \
        "Expected 5 register rows, got %d" % len(register_rows)


def test_known_data_is_present():
    """Specific AECO register entries must appear in the output."""
    result = ExcelRegisterExtractor().extract(str(FIXTURE_PATH))
    rows = {r["data"]["content"].get("No"): r["data"]["content"]
            for r in result.records if r["type"] == "register_row"}

    assert "SR-001" in rows
    assert rows["SR-001"]["Document Title"] == "HVAC Ductwork Shop Drawing"
    assert rows["SR-001"]["Status"] == "Submitted"
    assert rows["SR-001"]["Discipline"] == "Mechanical"
    assert rows["SR-001"]["Area"] == "Generator Room"

    assert "SR-003" in rows
    assert rows["SR-003"]["Status"] == "Approved"
    assert rows["SR-003"].get("Approved Date") == "2026-02-28"

    assert "SR-005" in rows
    assert rows["SR-005"]["Status"] == "Rejected"


def test_provenance_completeness_all_records():
    """Every record has non-empty provenance with sheet and row keys."""
    result = ExcelRegisterExtractor().extract(str(FIXTURE_PATH))
    for rec in result.records:
        prov = rec.get("provenance")
        assert prov is not None and isinstance(prov, dict), \
            "Record missing provenance: %s" % rec
        assert "sheet" in prov and prov["sheet"], \
            "Record missing provenance.sheet: %s" % rec["type"]
        assert "row" in prov and prov["row"], \
            "Record missing provenance.row: %s" % rec["type"]


def test_no_fabricated_semantic_facts():
    """Excel extraction must not produce document scope/requirement facts."""
    result = ExcelRegisterExtractor().extract(str(FIXTURE_PATH))
    for rec in result.records:
        t = rec["type"]
        assert not t.startswith("document."), \
            "Fabricated semantic fact from Excel: %s" % t
        assert not t.startswith("schedule."), \
            "Fabricated schedule fact from Excel: %s" % t


def test_header_detection_scores_correctly():
    """Header row detection should identify row 0 as header (keyword-rich row)."""
    result = ExcelRegisterExtractor().extract(str(FIXTURE_PATH))
    diag_text = "\n".join(result.diagnostics)
    assert "detected header row 0" in diag_text, \
        "Header detection failed — expected row 0 in diagnostics: %s" % diag_text


def test_sheet_name_preserved_in_provenance():
    """The sheet name must appear in every record's provenance."""
    result = ExcelRegisterExtractor().extract(str(FIXTURE_PATH))
    for rec in result.records:
        assert rec["provenance"]["sheet"] == "Submittal Register", \
            "Sheet name mismatch: %s" % rec["provenance"].get("sheet")


def test_existing_behavior_preserved():
    """Golden fixture extraction does not introduce unexpected diagnostics."""
    result = ExcelRegisterExtractor().extract(str(FIXTURE_PATH))
    assert result.success is True
    for diag in result.diagnostics:
        assert "mock" not in diag.lower()
        assert "fake" not in diag.lower()
