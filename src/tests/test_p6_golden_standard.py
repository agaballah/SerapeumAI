# -*- coding: utf-8 -*-
"""
test_p6_golden_standard.py

Gold fixture regression test for the P6/XER domain (Wave A pilot).
Proves that the PRODUCTION P6Extractor produces deterministic, complete
evidence from a real .xer file on disk — 5 activities, 4 relations, mixed float values.
"""

import hashlib
from pathlib import Path

from src.engine.extractors.p6_extractor import P6Extractor


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "p6" / "golden_v1"
FIXTURE_PATH = FIXTURE_DIR / "p6_standard.xer"
EXPECTED_HASH = "22d831648978f614522415f04b3943bbb44c0a807c5785e7abf12caca5ea9b93"
EXPECTED_SIZE = 767


def test_golden_fixture_hash_matches_manifest():
    """The fixture file has not been corrupted or modified."""
    assert FIXTURE_PATH.exists(), f"Missing golden fixture: {FIXTURE_PATH}"
    data = FIXTURE_PATH.read_bytes()
    actual_hash = hashlib.sha256(data).hexdigest()
    assert actual_hash == EXPECTED_HASH, \
        "Fixture hash mismatch: expected %s, got %s" % (EXPECTED_HASH, actual_hash)
    assert len(data) == EXPECTED_SIZE, \
        "Fixture size mismatch: expected %d, got %d" % (EXPECTED_SIZE, len(data))


def test_extractor_selection_standard():
    """The P6 extractor is registered and callable on the golden fixture."""
    ext = P6Extractor()
    assert ext.id == "p6-extractor-standard"
    assert ext.version == "1.0.0"
    assert ext.maturity == "PRODUCTION"
    assert ".xer" in ext.supported_extensions


def test_extraction_succeeds_and_is_deterministic():
    """Two consecutive extractions produce identical results."""
    ext = P6Extractor()
    result_a = ext.extract(str(FIXTURE_PATH))
    result_b = ext.extract(str(FIXTURE_PATH))

    assert result_a.success is True
    assert result_b.success is True
    assert result_a.records == result_b.records
    assert result_a.diagnostics == result_b.diagnostics
    assert result_a.metadata == result_b.metadata


def test_record_count_and_types():
    """The golden fixture produces exactly the expected record types and counts."""
    result = P6Extractor().extract(str(FIXTURE_PATH))
    type_counts = {}
    for rec in result.records:
        t = rec["type"]
        type_counts[t] = type_counts.get(t, 0) + 1

    assert type_counts.get("p6_project") == 1
    assert type_counts.get("p6_wbs") == 1
    assert type_counts.get("p6_activity") == 5
    assert type_counts.get("p6_relation") == 4
    assert len(result.records) == 11


def test_provenance_completeness_all_records():
    """Every record has a non-empty provenance dict with a table key."""
    result = P6Extractor().extract(str(FIXTURE_PATH))
    for rec in result.records:
        prov = rec.get("provenance")
        assert prov is not None and isinstance(prov, dict), \
            "Record missing provenance: %s" % rec
        assert len(prov) > 0, "Record has empty provenance: %s" % rec["type"]
        assert "table" in prov and prov["table"], \
            "Record missing provenance.table: %s" % rec["type"]


def test_activities_have_required_fields():
    """All p6_activity records carry task_id, task_code, total_float, is_critical."""
    result = P6Extractor().extract(str(FIXTURE_PATH))
    activities = [r for r in result.records if r["type"] == "p6_activity"]
    assert len(activities) == 5

    required_keys = {"task_id", "task_code", "total_float", "is_critical"}
    for act in activities:
        data = act.get("data", {})
        for key in required_keys:
            assert key in data, \
                "Activity missing key '%s': %s" % (key, data)


def test_float_normalization_and_criticality():
    """Hours are converted to days (÷8); negative float → critical; zero float → critical."""
    result = P6Extractor().extract(str(FIXTURE_PATH))
    activities = {r["data"]["task_code"]: r["data"]
                  for r in result.records if r["type"] == "p6_activity"}

    # A-001: total_float_hr_cnt=-8 → -8/8 = -1.0 days → critical
    a1 = activities["A-001"]
    assert a1["total_float"] == -1.0
    assert a1["total_float_hours"] == -8.0
    assert a1["is_critical"] is True

    # A-002: total_float_hr_cnt=0 → 0 days → critical
    a2 = activities["A-002"]
    assert a2["total_float"] == 0.0
    assert a2["is_critical"] is True

    # A-003: total_float_hr_cnt=16 → 16/8 = 2.0 days → not critical
    a3 = activities["A-003"]
    assert a3["total_float"] == 2.0
    assert a3["is_critical"] is False

    # A-004: total_float_hr_cnt=40 → 40/8 = 5.0 days → not critical
    a4 = activities["A-004"]
    assert a4["total_float"] == 5.0
    assert a4["is_critical"] is False

    # A-005: total_float_hr_cnt=80 → 80/8 = 10.0 days → not critical
    a5 = activities["A-005"]
    assert a5["total_float"] == 10.0
    assert a5["is_critical"] is False


def test_relations_preserve_type_and_lag():
    """TASKPRED relations preserve pred_type and lag values via raw row dict."""
    result = P6Extractor().extract(str(FIXTURE_PATH))
    relations = [r for r in result.records if r["type"] == "p6_relation"]
    assert len(relations) == 4

    for rel in relations:
        data = rel.get("data", {})
        assert "pred_task_id" in data, "Relation missing pred_task_id"
        assert "task_id" in data, "Relation missing task_id (successor)"
        assert "pred_type" in data, "Relation missing pred_type"
        assert "lag" in data, "Relation missing lag"


def test_existing_behavior_preserved():
    """Golden fixture extraction does not introduce unexpected behavior."""
    result = P6Extractor().extract(str(FIXTURE_PATH))
    assert result.success is True
    assert len(result.records) == 11
    # Verify no fabricated/mock data in diagnostics
    for diag in result.diagnostics:
        assert "mock" not in diag.lower()
        assert "fake" not in diag.lower()
