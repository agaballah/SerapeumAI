# -*- coding: utf-8 -*-
"""
test_p6_golden_malformed_float.py

Gold fixture regression test for the P6/XER domain — edge-case variant.
Proves that malformed float values (missing, non-numeric, blank) produce
honest None values without crashes, false critical-path claims, or
fabricated evidence.
"""

import hashlib
from pathlib import Path

from src.engine.extractors.p6_extractor import P6Extractor


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "p6" / "golden_v1"
FIXTURE_PATH = FIXTURE_DIR / "p6_malformed_float.xer"
EXPECTED_HASH = "adb7efc79eb601b3dd973703a4cdcb755731c4bfa3ec984e383ca66d70a2d5f7"
EXPECTED_SIZE = 620


def test_golden_fixture_hash_matches_manifest():
    """The fixture file has not been corrupted or modified."""
    assert FIXTURE_PATH.exists(), f"Missing golden fixture: {FIXTURE_PATH}"
    data = FIXTURE_PATH.read_bytes()
    actual_hash = hashlib.sha256(data).hexdigest()
    assert actual_hash == EXPECTED_HASH, \
        "Fixture hash mismatch: expected %s, got %s" % (EXPECTED_HASH, actual_hash)
    assert len(data) == EXPECTED_SIZE, \
        "Fixture size mismatch: expected %d, got %d" % (EXPECTED_SIZE, len(data))


def test_extractor_selection_malformed():
    """The P6 extractor is registered and callable on the golden fixture."""
    ext = P6Extractor()
    assert ext.id == "p6-extractor-standard"
    assert ext.maturity == "PRODUCTION"
    assert ".xer" in ext.supported_extensions


def test_extraction_succeeds_despite_bad_data():
    """Malformed floats do not crash the extractor — success=True, no records lost."""
    result = P6Extractor().extract(str(FIXTURE_PATH))
    assert result.success is True
    activities = [r for r in result.records if r["type"] == "p6_activity"]
    assert len(activities) == 3, \
        "Expected 3 activity records, got %d" % len(activities)


def test_missing_floats_become_none_not_crash():
    """Missing, non-numeric, and blank float values all become None."""
    result = P6Extractor().extract(str(FIXTURE_PATH))
    activities = {r["data"]["task_code"]: r["data"]
                  for r in result.records if r["type"] == "p6_activity"}

    for code in ("A-001", "A-002", "A-003"):
        assert code in activities, "Activity %s missing from extraction" % code
        assert activities[code]["total_float"] is None, \
            "Activity %s expected None float, got %s" % (code, activities[code]["total_float"])
        assert activities[code]["is_critical"] is False, \
            "Activity %s with bad float must NOT be marked critical" % code


def test_no_false_critical_path_from_bad_floats():
    """Activities with missing/malformed floats must NOT trigger critical path membership."""
    result = P6Extractor().extract(str(FIXTURE_PATH))
    activities = [r for r in result.records if r["type"] == "p6_activity"]
    for act in activities:
        assert act["data"]["is_critical"] is False, \
            "Activity %s with bad float must not be critical" % act["data"].get("task_code")


def test_provenance_complete_on_all_records():
    """Every record has valid provenance even when data is malformed."""
    result = P6Extractor().extract(str(FIXTURE_PATH))
    for rec in result.records:
        prov = rec.get("provenance")
        assert prov is not None and isinstance(prov, dict), \
            "Record missing provenance: %s" % rec
        assert len(prov) > 0, "Record has empty provenance: %s" % rec["type"]


def test_existing_behavior_preserved():
    """Golden fixture extraction does not introduce unexpected diagnostics."""
    result = P6Extractor().extract(str(FIXTURE_PATH))
    assert result.success is True
    # No mock or fabricated data in output
    for rec in result.records:
        for key in ("data", "provenance"):
            val = str(rec.get(key, ""))
            assert "mock" not in val.lower()
            assert "fake" not in val.lower()
    # Diagnostics should be empty or informational (no error-level messages)
    for diag in result.diagnostics:
        assert "error" not in diag.lower() or "missing" in diag.lower(), \
            "Unexpected error diagnostic: %s" % diag
