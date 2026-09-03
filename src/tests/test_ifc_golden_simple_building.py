# -*- coding: utf-8 -*-
"""
test_ifc_golden_simple_building.py

Gold fixture regression test for the IFC domain (Wave A pilot).

Two paths are covered:
  1. With ifcopenshell available: runs extraction on the real .ifc fixture.
  2. Without ifcopenshell: verifies the extractor fails honestly (skipif path).

The fixture is a minimal valid IFC2x3 text file containing:
  - 1 IfcProject
  - 1 IfcSite
  - 1 IfcBuilding
  - 1 IfcBuildingStorey
  - 2 IfcWall elements with property sets
  - 1 IfcRelContainedInSpatialStructure
  - 2 IfcRelDefinesByProperties
"""

import hashlib
import sys
from pathlib import Path

import pytest

from src.engine.extractors.ifc_extractor import IFCExtractor


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "ifc" / "golden_v1"
FIXTURE_PATH = FIXTURE_DIR / "ifc_simple_building.ifc"
EXPECTED_HASH = None  # populated at import time below
EXPECTED_SIZE = 1213
EXPECTED_HASH = "b898368703adf6bfe9fb51fdb6c23d6ca03d5bee47de66e892b16e70d57a2e15"


def _has_ifcopenshell():
    """Check whether ifcopenshell is available without importing it unconditionally."""
    try:
        import ifcopenshell  # noqa: F401
        return True
    except ImportError:
        return False


ifc_available = pytest.mark.skipif(
    not _has_ifcopenshell(),
    reason="ifcopenshell not installed — skipping real-fixture tests",
)


def test_golden_fixture_hash_matches_manifest():
    """The fixture file has not been corrupted or modified."""
    assert FIXTURE_PATH.exists(), f"Missing golden fixture: {FIXTURE_PATH}"
    data = FIXTURE_PATH.read_bytes()
    actual_hash = hashlib.sha256(data).hexdigest()
    assert actual_hash == EXPECTED_HASH, \
        "Fixture hash mismatch: expected %s, got %s" % (EXPECTED_HASH, actual_hash)
    assert len(data) == EXPECTED_SIZE, \
        "Fixture size mismatch: expected %d, got %d" % (EXPECTED_SIZE, len(data))


def test_extractor_selection_simple_building():
    """IFC extractor is registered with VERIFIED maturity."""
    ext = IFCExtractor()
    assert ext.id == "ifc-extractor-v1"
    assert ext.version == "1.0.0"
    assert ext.maturity == "VERIFIED"
    assert ".ifc" in ext.supported_extensions


def test_missing_ifcopenshell_fails_honestly_on_golden_fixture(tmp_path):
    """When ifcopenshell is absent, even a valid .ifc file produces honest failure."""
    # Copy the golden fixture to a temp location so we can reference it
    dest = tmp_path / "model.ifc"
    dest.write_bytes(FIXTURE_PATH.read_bytes())

    result = IFCExtractor().extract(str(dest))

    # Honesty contract: success=False, no records, diagnostic mentions dep
    assert result.success is False
    assert result.records == []
    diag_text = "\n".join(result.diagnostics).lower()
    assert "ifcopenshell" in diag_text
    assert "missing" in diag_text or "unavailable" in diag_text
    # Must NOT fall back to regex/text parsing — the message says "no fallback ... is enabled",
    # which is the opposite of using a fallback. Assert the explicit denial pattern exists.
    assert "no fallback" in diag_text or "disabled" in diag_text, \
        "Missing: explicit 'no fallback' statement in diagnostics: %s" % diag_text
    # Ensure no regex-based extraction claim
    assert "regex/text" not in diag_text
    assert "good enough" not in diag_text


@ifc_available
def test_golden_fixture_extraction_succeeds_with_ifcopenshell():
    """With ifcopenshell present, the golden fixture extracts successfully."""
    result = IFCExtractor().extract(str(FIXTURE_PATH))
    assert result.success is True
    assert len(result.records) > 0


@ifc_available
def test_golden_fixture_deterministic_extraction():
    """Two extractions of the same golden fixture produce identical results."""
    r1 = IFCExtractor().extract(str(FIXTURE_PATH))
    r2 = IFCExtractor().extract(str(FIXTURE_PATH))
    assert r1.records == r2.records
    assert r1.diagnostics == r2.diagnostics
    assert r1.metadata == r2.metadata


@ifc_available
def test_golden_fixture_produces_contract_record_types():
    """Only the four known contract record types are emitted."""
    result = IFCExtractor().extract(str(FIXTURE_PATH))
    record_types = {rec["type"] for rec in result.records}
    # Each type must be one of the known contract types
    allowed = {"ifc_project", "ifc_spatial", "ifc_element_metadata", "ifc_connection"}
    assert record_types.issubset(allowed), \
        "Unexpected record types: %s" % (record_types - allowed,)
    # At minimum we should get project and spatial records from this fixture
    assert "ifc_project" in record_types


@ifc_available
def test_golden_fixture_provenance_completeness():
    """Every record carries provenance with an entity identifier."""
    result = IFCExtractor().extract(str(FIXTURE_PATH))
    for rec in result.records:
        prov = rec.get("provenance")
        assert prov is not None and isinstance(prov, dict), \
            "Record missing provenance: %s" % rec
        assert len(prov) > 0, "Record has empty provenance: %s" % rec["type"]
        # All IFC records must identify their entity type
        assert "entity" in prov and prov["entity"], \
            "Record missing provenance.entity: %s" % rec["type"]


@ifc_available
def test_golden_fixture_no_regex_fallback_in_output():
    """No record should carry a regex-derived source indication."""
    result = IFCExtractor().extract(str(FIXTURE_PATH))
    for rec in result.records:
        src = rec.get("provenance", {}).get("source", "")
        assert "regex" not in src.lower(), \
            "Regex-derived record found: %s" % rec
    diag_text = "\n".join(result.diagnostics).lower()
    assert "regex" not in diag_text, \
        "Diagnostic mentions regex fallback"
    assert "fallback" not in diag_text, \
        "Diagnostic mentions fallback"


def test_golden_fixture_entity_count_matches_fixture_structure():
    """
    The IFC fixture contains:
      - 1 IfcProject → 1 ifc_project record
      - 1 IfcSite + 1 IfcBuilding + 1 IfcBuildingStorey → 3 ifc_spatial records
      - 2 IfcWall → at least 2 ifc_element_metadata records
      - 0 connections → 0 ifc_connection records (unless Pset triggers one)
    """
    # This test only runs when ifcopenshell is available.
    # When unavailable, the fixture is still valid and the skip is honest.
    if not _has_ifcopenshell():
        pytest.skip("ifcopenshell not installed")

    result = IFCExtractor().extract(str(FIXTURE_PATH))
    project_records = [r for r in result.records if r["type"] == "ifc_project"]
    spatial_records = [r for r in result.records if r["type"] == "ifc_spatial"]
    element_records = [r for r in result.records if r["type"] == "ifc_element_metadata"]

    assert len(project_records) >= 1, "Expected at least 1 ifc_project record"
    assert len(spatial_records) >= 3, "Expected at least 3 ifc_spatial records (site+building+storey)"
    assert len(element_records) >= 2, "Expected at least 2 ifc_element_metadata records (2 walls)"


def test_golden_fixture_no_mock_data_in_diagnostics():
    """Diagnostics must not contain fabrication indicators."""
    if not _has_ifcopenshell():
        pytest.skip("ifcopenshell not installed")

    result = IFCExtractor().extract(str(FIXTURE_PATH))
    for diag in result.diagnostics:
        assert "mock" not in diag.lower(), "Mock data found in diagnostics: %s" % diag
        assert "fake" not in diag.lower(), "Fake data found in diagnostics: %s" % diag
        assert "vlm" not in diag.lower(), "VLM reference found in diagnostics: %s" % diag
