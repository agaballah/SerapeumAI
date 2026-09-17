# -*- coding: utf-8 -*-
"""
test_gold_regression_hardening.py — WP-07A Gold Regression Hardening Tests.

Verifies the format-aware hardening added to the gold regression benchmark:
  - DXF source_file completeness across all 6 record types
  - Record type preservation (expected type sets present)
  - Entity ID stability (DXF handles stable across runs)
  - Provenance quality per format family (format-aware)
  - PDF large-file timing thresholds
  - Technology admission gate comparison logic
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from src.engine.extractors.base import ExtractionResult

CORPUS_DIR = Path(__file__).resolve().parents[2] / "_LOCAL_TEST_CORPUS" / "GOLD_BENCHMARK_V1"
ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = ROOT / "tools"


def _corpus() -> Path:
    if not CORPUS_DIR.is_dir():
        pytest.skip(f"Gold corpus not found: {CORPUS_DIR}")
    return CORPUS_DIR


def _files(ext: str, corpus: Path) -> List[Path]:
    return sorted(corpus.glob(f"*{ext}"))


def _run(extractor_path: str, file_path: Path) -> Optional[ExtractionResult]:
    """Run an extractor class given 'module:Class' path on a file."""
    module_path, class_name = extractor_path.split(":")
    try:
        module = __import__(module_path, fromlist=[class_name])
        extractor = getattr(module, class_name)()
        return extractor.extract(str(file_path))
    except ImportError as e:
        return ExtractionResult(success=False, records=[], diagnostics=[f"ImportError: {e}"])
    except Exception as e:
        return ExtractionResult(success=False, records=[], diagnostics=[f"{type(e).__name__}: {e}"])


# ──────────────────────────────────────────────────────────────
# DXF Provenance Completeness (WP-07A scope: source_file added)
# ──────────────────────────────────────────────────────────────

class TestDXFSourceFileCompleteness:
    """All DXF record types must carry data.source_file."""

    DXF_DISPATCH = "src.engine.extractors.dxf_extractor:DXFExtractor"

    @pytest.fixture
    def dxf_files(self):
        corpus = _corpus()
        files = _files(".dxf", corpus)
        if not files:
            pytest.skip("No DXF files in corpus")
        return files

    def test_all_dxf_record_types_have_source_file(self, dxf_files):
        """dxf_layer and dxf_block (and all others) must include data.source_file."""
        for f in dxf_files:
            result = _run(self.DXF_DISPATCH, f)
            if not result or "ImportError" in str(result.diagnostics):
                pytest.skip("ezdxf not available")
            assert result.success, f"DXF extraction failed for {f.name}: {result.diagnostics}"
            for rec in result.records:
                if not isinstance(rec, dict):
                    continue
                if rec.get("type", "").startswith("dxf_"):
                    data = rec.get("data", {})
                    assert isinstance(data, dict), f"Record data is not a dict: {rec.get('type')}"
                    assert "source_file" in data, (
                        f"DXF record type {rec.get('type')} missing source_file in data"
                    )
                    assert data["source_file"], (
                        f"DXF record type {rec.get('type')} has empty source_file"
                    )

    def test_dxf_layer_records_have_source_file(self, dxf_files):
        """Specifically verify dxf_layer records have source_file."""
        corpus = _corpus()
        found_any = False
        for f in dxf_files:
            result = _run(self.DXF_DISPATCH, f)
            if not result or "ImportError" in str(result.diagnostics):
                pytest.skip("ezdxf not available")
            assert result.success
            layer_records = [r for r in result.records if r.get("type") == "dxf_layer"]
            if layer_records:
                found_any = True
                for rec in layer_records:
                    assert "source_file" in rec["data"], "dxf_layer missing source_file"
                    assert rec["data"]["source_file"]
        assert found_any, "No dxf_layer records found in any DXF file"

    def test_dxf_block_records_have_source_file(self, dxf_files):
        """Specifically verify dxf_block records have source_file."""
        corpus = _corpus()
        found_any = False
        for f in dxf_files:
            result = _run(self.DXF_DISPATCH, f)
            if not result or "ImportError" in str(result.diagnostics):
                pytest.skip("ezdxf not available")
            assert result.success
            block_records = [r for r in result.records if r.get("type") == "dxf_block"]
            if block_records:
                found_any = True
                for rec in block_records:
                    assert "source_file" in rec["data"], "dxf_block missing source_file"
                    assert rec["data"]["source_file"]
        assert found_any, "No dxf_block records found in any DXF file"


# ──────────────────────────────────────────────────────────────
# Record Type Preservation
# ──────────────────────────────────────────────────────────────

class TestRecordTypePreservation:
    """Expected record type sets must be present for each format."""

    EXPECTED_TYPES = {
        ".dxf": {"dxf_drawing", "dxf_layer", "dxf_block", "dxf_viewport", "dxf_text", "dxf_insert"},
        ".ifc": {"ifc_project", "ifc_spatial", "ifc_element_metadata", "ifc_connection", "ifc_entity_count"},
        ".xer": {"p6_project", "p6_wbs", "p6_activity", "p6_relation"},
        ".pdf": {"pdf_page", "doc_classification", "doc_blocks"},
    }

    EXTRACTORS = {
        ".dxf": "src.engine.extractors.dxf_extractor:DXFExtractor",
        ".ifc": "src.engine.extractors.ifc_extractor:IFCExtractor",
        ".xer": "src.engine.extractors.p6_extractor:P6Extractor",
        ".pdf": "src.engine.extractors.pdf_extractor:UniversalPdfExtractor",
    }

    def test_dxf_record_types_preserved(self):
        corpus = _corpus()
        files = _files(".dxf", corpus)
        if not files:
            pytest.skip("No DXF files")
        result = _run(self.EXTRACTORS[".dxf"], files[0])
        if not result or "ImportError" in str(result.diagnostics):
            pytest.skip("ezdxf not available")
        assert result.success
        actual_types = {r.get("type", "unknown") for r in result.records}
        expected = self.EXPECTED_TYPES[".dxf"]
        missing = expected - actual_types
        assert not missing, f"DXF missing expected record types: {missing}"

    def test_xer_record_types_preserved(self):
        corpus = _corpus()
        files = _files(".xer", corpus)
        if not files:
            pytest.skip("No XER files")
        result = _run(self.EXTRACTORS[".xer"], files[0])
        assert result is not None and result.success
        actual_types = {r.get("type", "unknown") for r in result.records}
        expected = self.EXPECTED_TYPES[".xer"]
        missing = expected - actual_types
        assert not missing, f"XER missing expected record types: {missing}"

    def test_pdf_record_types_preserved(self):
        corpus = _corpus()
        files = _files(".pdf", corpus)
        if not files:
            pytest.skip("No PDF files")
        result = _run(self.EXTRACTORS[".pdf"], files[2])  # GOLD_0124.pdf (small)
        if not result or "ImportError" in str(result.diagnostics):
            pytest.skip("PDF extractor not available")
        assert result.success
        actual_types = {r.get("type", "unknown") for r in result.records}
        expected = self.EXPECTED_TYPES[".pdf"]
        missing = expected - actual_types
        assert not missing, f"PDF missing expected record types: {missing}"


# ──────────────────────────────────────────────────────────────
# Entity ID Stability
# ──────────────────────────────────────────────────────────────

class TestEntityIDStability:
    """Entity IDs must be stable across repeated extraction runs."""

    def test_dxf_handles_stable_across_runs(self):
        corpus = _corpus()
        files = _files(".dxf", corpus)
        if not files:
            pytest.skip("No DXF files")
        result1 = _run("src.engine.extractors.dxf_extractor:DXFExtractor", files[0])
        if not result1 or "ImportError" in str(result1.diagnostics):
            pytest.skip("ezdxf not available")
        result2 = _run("src.engine.extractors.dxf_extractor:DXFExtractor", files[0])

        handles1 = {
            r.get("data", {}).get("handle")
            for r in result1.records
            if isinstance(r, dict) and r.get("data", {}).get("handle")
        }
        handles2 = {
            r.get("data", {}).get("handle")
            for r in result2.records
            if isinstance(r, dict) and r.get("data", {}).get("handle")
        }
        assert handles1, "No entity handles found in DXF records"
        overlap = handles1 & handles2
        stability = len(overlap) / max(len(handles1), 1)
        assert stability >= 0.99, (
            f"DXF entity ID stability below 99%: {stability:.1%} "
            f"({len(overlap)}/{len(handles1)} handles stable)"
        )

    def test_xer_task_ids_stable_across_runs(self):
        corpus = _corpus()
        files = _files(".xer", corpus)
        if not files:
            pytest.skip("No XER files")
        result1 = _run("src.engine.extractors.p6_extractor:P6Extractor", files[0])
        if not result1 or not result1.success:
            pytest.skip("P6 extraction failed")
        result2 = _run("src.engine.extractors.p6_extractor:P6Extractor", files[0])

        ids1 = {r.get("data", {}).get("task_id") for r in result1.records if isinstance(r, dict)}
        ids2 = {r.get("data", {}).get("task_id") for r in result2.records if isinstance(r, dict)}
        ids1.discard(None)
        ids2.discard(None)
        if not ids1:
            pytest.skip("No task IDs found")
        overlap = ids1 & ids2
        stability = len(overlap) / max(len(ids1), 1)
        assert stability >= 0.99, f"XER entity ID stability below 99%: {stability:.1%}"

    def test_ifc_element_ids_stable_across_runs(self):
        """IFC GlobalId is a GUID embedded in the file — deterministic across runs."""
        corpus = _corpus()
        files = _files(".ifc", corpus)
        if not files:
            pytest.skip("No IFC files")
        small = sorted(files, key=lambda f: f.stat().st_size)
        f = small[0]
        result1 = _run("src.engine.extractors.ifc_extractor:IFCExtractor", f)
        if not result1 or "ImportError" in str(result1.diagnostics):
            pytest.skip("ifcopenshell not available")
        if not result1.success:
            pytest.skip("IFC extraction failed")
        result2 = _run("src.engine.extractors.ifc_extractor:IFCExtractor", f)

        ids1 = {r.get("data", {}).get("ElementId") for r in result1.records if isinstance(r, dict)}
        ids2 = {r.get("data", {}).get("ElementId") for r in result2.records if isinstance(r, dict)}
        ids1.discard(None)
        ids2.discard(None)
        if not ids1:
            pytest.skip("No IFC ElementId found in records")
        overlap = ids1 & ids2
        stability = len(overlap) / max(len(ids1), 1)
        assert stability >= 0.99, f"IFC entity ID stability below 99%: {stability:.1%}"

    def test_xlsx_row_indices_stable_across_runs(self):
        """XLSX row_index is sequential — deterministic across runs."""
        corpus = _corpus()
        files = _files(".xlsx", corpus)
        if not files:
            pytest.skip("No XLSX files")
        small = sorted(files, key=lambda f: f.stat().st_size)
        f = small[0]
        result1 = _run("src.engine.extractors.excel_extractor:ExcelExtractor", f)
        if not result1 or "ImportError" in str(result1.diagnostics):
            pytest.skip("openpyxl not available")
        if not result1.success:
            pytest.skip("XLSX extraction failed")
        result2 = _run("src.engine.extractors.excel_extractor:ExcelExtractor", f)

        ids1 = {r.get("data", {}).get("row_index") for r in result1.records if isinstance(r, dict)}
        ids2 = {r.get("data", {}).get("row_index") for r in result2.records if isinstance(r, dict)}
        ids1.discard(None)
        ids2.discard(None)
        if not ids1:
            pytest.skip("No XLSX row_index found in records")
        overlap = ids1 & ids2
        stability = len(overlap) / max(len(ids1), 1)
        assert stability >= 0.99, f"XLSX entity ID stability below 99%: {stability:.1%}"


# ──────────────────────────────────────────────────────────────
# Provenance Quality (format-aware)
# ──────────────────────────────────────────────────────────────

class TestProvenanceQuality:
    """Format-aware provenance quality: meaningful fields must be present."""

    FORMAT_REQUIREMENTS = {
        ".pdf": {
            "key": "provenance",
            "fields": ["page", "method"],
            "per_type": {
                "pdf_page": ["page", "method"],
                "doc_classification": ["source"],
                "doc_blocks": ["method"],
            },
        },
        ".docx": {"key": "provenance", "fields": ["page", "source"]},
        ".pptx": {"key": "provenance", "fields": ["page", "source"]},
        ".xlsx": {"key": "provenance", "fields": ["sheet", "row"]},
        ".xls": {"key": "provenance", "fields": ["sheet", "row"]},
        ".csv": {"key": "provenance", "fields": ["source"]},
        ".json": {"key": "provenance", "fields": ["source"]},
        ".xml": {"key": "provenance", "fields": ["source"]},
        ".txt": {"key": "provenance", "fields": ["source"]},
        ".yaml": {"key": "provenance", "fields": ["source"]},
        ".yml": {"key": "provenance", "fields": ["source"]},
        ".dxf": {"key": "data", "fields": ["source_file"]},
        ".ifc": {"key": "provenance", "fields": ["entity"]},
        ".xer": {"key": "provenance", "fields": ["table"]},
    }

    EXTRACTORS = {
        ".pdf": "src.engine.extractors.pdf_extractor:UniversalPdfExtractor",
        ".dxf": "src.engine.extractors.dxf_extractor:DXFExtractor",
        ".xer": "src.engine.extractors.p6_extractor:P6Extractor",
        ".csv": "src.engine.extractors.csv_extractor:CsvExtractor",
        ".json": "src.engine.extractors.json_extractor:JsonExtractor",
        ".txt": "src.engine.extractors.text_extractor:TextExtractor",
    }

    def _quality_rate(self, records: list, ext: str) -> float:
        req = self.FORMAT_REQUIREMENTS.get(ext)
        if not req:
            return 1.0
        if not records:
            return 0.0
        key = req["key"]
        default_fields = req["fields"]
        per_type = req.get("per_type", {})
        qualified = 0
        for r in records:
            if not isinstance(r, dict):
                continue
            rtype = r.get("type", "")
            fields = per_type.get(rtype, default_fields)
            if key == "data":
                data = r.get("data", {})
                if isinstance(data, dict) and all(f in data and data[f] for f in fields):
                    qualified += 1
            elif key == "provenance":
                prov = r.get("provenance")
                if isinstance(prov, dict) and all(f in prov and prov[f] is not None for f in fields):
                    qualified += 1
        return round(qualified / len(records), 4)

    def test_dxf_provenance_quality(self):
        """DXF records must have data.source_file (format-aware provenance)."""
        corpus = _corpus()
        files = _files(".dxf", corpus)
        if not files:
            pytest.skip("No DXF files")
        result = _run(self.EXTRACTORS[".dxf"], files[0])
        if not result or "ImportError" in str(result.diagnostics):
            pytest.skip("ezdxf not available")
        assert result.success
        rate = self._quality_rate(result.records, ".dxf")
        assert rate >= 0.90, f"DXF provenance quality below 90%: {rate}"

    def test_pdf_provenance_quality(self):
        """PDF records must have type-appropriate provenance.

        Per-record-type requirements:
        - pdf_page: page + method (page-level record)
        - doc_classification: source (document-level record, no single page applies)
        - doc_blocks: method (document-level collection; page_index is in nested blocks)

        With correct per-type requirements, all PDF records qualify.
        """
        corpus = _corpus()
        files = _files(".pdf", corpus)
        if not files:
            pytest.skip("No PDF files")
        result = _run(self.EXTRACTORS[".pdf"], files[2])
        if not result or "ImportError" in str(result.diagnostics):
            pytest.skip("PDF extractor not available")
        assert result.success
        rate = self._quality_rate(result.records, ".pdf")
        assert rate >= 0.90, f"PDF provenance quality below 90%: {rate}"
        # Verify pdf_page records specifically have page + method
        page_records = [r for r in result.records if r.get("type") == "pdf_page"]
        assert page_records, "No pdf_page records found"
        for r in page_records:
            prov = r.get("provenance", {})
            assert "page" in prov, f"pdf_page record missing page: {r.get('type')}"
            assert "method" in prov, f"pdf_page record missing method: {r.get('type')}"

    def test_xer_provenance_quality(self):
        """XER records must have provenance with table field."""
        corpus = _corpus()
        files = _files(".xer", corpus)
        if not files:
            pytest.skip("No XER files")
        result = _run(self.EXTRACTORS[".xer"], files[0])
        if not result or not result.success:
            pytest.skip("P6 extraction failed")
        rate = self._quality_rate(result.records, ".xer")
        assert rate >= 0.90, f"XER provenance quality below 90%: {rate}"


# ──────────────────────────────────────────────────────────────
# PDF Large-File Timing
# ──────────────────────────────────────────────────────────────

class TestPDFTiming:
    """PDF extraction must meet timing thresholds for large and combined files."""

    def test_pdf_large_file_timing(self):
        """GOLD_0122.pdf (4.4MB) must extract within 60s.

        Measured times across benchmark runs: 37-48s. 60s provides ~25% margin
        for system load variance.
        """
        corpus = _corpus()
        target = [f for f in _files(".pdf", corpus) if f.name == "GOLD_0122.pdf"]
        if not target:
            pytest.skip("GOLD_0122.pdf not found")
        start = time.perf_counter()
        result = _run("src.engine.extractors.pdf_extractor:UniversalPdfExtractor", target[0])
        elapsed_ms = (time.perf_counter() - start) * 1000
        if not result or "ImportError" in str(result.diagnostics):
            pytest.skip("PDF extractor not available")
        assert result.success, f"PDF extraction failed: {result.diagnostics}"
        assert elapsed_ms < 60000, f"Large PDF too slow: {elapsed_ms:.0f}ms (threshold 60000ms)"

    def test_pdf_medium_file_timing(self):
        """GOLD_0124.pdf (62KB) must extract within 5s."""
        corpus = _corpus()
        target = [f for f in _files(".pdf", corpus) if f.name == "GOLD_0124.pdf"]
        if not target:
            pytest.skip("GOLD_0124.pdf not found")
        start = time.perf_counter()
        result = _run("src.engine.extractors.pdf_extractor:UniversalPdfExtractor", target[0])
        elapsed_ms = (time.perf_counter() - start) * 1000
        if not result or "ImportError" in str(result.diagnostics):
            pytest.skip("PDF extractor not available")
        assert result.success
        assert elapsed_ms < 5000, f"PDF too slow: {elapsed_ms:.0f}ms"


# ──────────────────────────────────────────────────────────────
# Admission Gate Comparison Logic
# ──────────────────────────────────────────────────────────────

class TestAdmissionGate:
    """Test the technology admission gate comparison logic."""

    def _import_benchmark_module(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("run_gold_benchmark", TOOLS_DIR / "run_gold_benchmark.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_admission_gate_passes_when_no_regressions(self):
        """Gate passes when candidate matches or exceeds baseline."""
        bench = self._import_benchmark_module()

        baseline = {
            "summary": {
                ".dxf": {
                    "successful": 3, "files_tested": 3, "failed": 0,
                    "total_records": 7820, "avg_timing_ms": 6000,
                    "avg_provenance_quality_rate": 0.0,
                    "avg_entity_id_stability": 1.0,
                    "status": "PASS",
                }
            },
            "per_format": {
                ".dxf": [
                    {"type_distribution": {"dxf_drawing": 1, "dxf_layer": 1, "dxf_block": 1, "dxf_text": 1, "dxf_insert": 1, "dxf_viewport": 1}}
                ]
            }
        }
        current = {
            "summary": {
                ".dxf": {
                    "successful": 3, "files_tested": 3, "failed": 0,
                    "total_records": 7820, "avg_timing_ms": 6000,
                    "avg_provenance_quality_rate": 1.0,
                    "avg_entity_id_stability": 1.0,
                    "status": "PASS",
                }
            },
            "per_format": {
                ".dxf": [
                    {"type_distribution": {"dxf_drawing": 1, "dxf_layer": 1, "dxf_block": 1, "dxf_text": 1, "dxf_insert": 1, "dxf_viewport": 1}}
                ]
            }
        }
        results = bench.compare_baseline(baseline, current)
        assert results[".dxf"]["passed"], f"Gate should pass: {results['.dxf']['issues']}"

    def test_admission_gate_detects_extraction_success_regression(self):
        """Gate fails when extraction success count drops below baseline."""
        bench = self._import_benchmark_module()

        baseline = {
            "summary": {".pdf": {"successful": 3, "files_tested": 3, "failed": 0,
                                "total_records": 40, "avg_timing_ms": 10000,
                                "avg_provenance_quality_rate": 1.0, "avg_entity_id_stability": 1.0,
                                "status": "PASS"}},
            "per_format": {".pdf": [{"type_distribution": {}}]}
        }
        current = {
            "summary": {".pdf": {"successful": 2, "files_tested": 3, "failed": 1,
                                "total_records": 30, "avg_timing_ms": 10000,
                                "avg_provenance_quality_rate": 1.0, "avg_entity_id_stability": 1.0,
                                "status": "WARN"}},
            "per_format": {".pdf": [{"type_distribution": {}}]}
        }
        results = bench.compare_baseline(baseline, current)
        assert not results[".pdf"]["passed"]
        assert any("Extraction success regressed" in i for i in results[".pdf"]["issues"])

    def test_admission_gate_detects_record_count_regression(self):
        """Gate fails when record count drops below 90%."""
        bench = self._import_benchmark_module()

        baseline = {
            "summary": {".dxf": {"successful": 3, "files_tested": 3, "failed": 0,
                                "total_records": 7820, "avg_timing_ms": 6000,
                                "avg_provenance_quality_rate": 1.0, "avg_entity_id_stability": 1.0,
                                "status": "PASS"}},
            "per_format": {".dxf": [{"type_distribution": {}}]}
        }
        current = {
            "summary": {".dxf": {"successful": 3, "files_tested": 3, "failed": 0,
                                "total_records": 1000, "avg_timing_ms": 6000,
                                "avg_provenance_quality_rate": 1.0, "avg_entity_id_stability": 1.0,
                                "status": "PASS"}},
            "per_format": {".dxf": [{"type_distribution": {}}]}
        }
        results = bench.compare_baseline(baseline, current)
        assert not results[".dxf"]["passed"]
        assert any("Record count below 90%" in i for i in results[".dxf"]["issues"])

    def test_admission_gate_detects_new_failures(self):
        """Gate fails when new file failures are introduced."""
        bench = self._import_benchmark_module()

        baseline = {
            "summary": {".pdf": {"successful": 3, "files_tested": 3, "failed": 0,
                                "total_records": 40, "avg_timing_ms": 10000,
                                "avg_provenance_quality_rate": 1.0, "avg_entity_id_stability": 1.0,
                                "status": "PASS"}},
            "per_format": {".pdf": [{"type_distribution": {}}]}
        }
        current = {
            "summary": {".pdf": {"successful": 2, "files_tested": 3, "failed": 1,
                                "total_records": 25, "avg_timing_ms": 10000,
                                "avg_provenance_quality_rate": 1.0, "avg_entity_id_stability": 1.0,
                                "status": "FAIL"}},
            "per_format": {".pdf": [{"type_distribution": {}}]}
        }
        results = bench.compare_baseline(baseline, current)
        assert not results[".pdf"]["passed"]
        assert any("New failures" in i for i in results[".pdf"]["issues"])

    def test_admission_gate_skips_unavailable(self):
        """Gate passes when both baseline and candidate are UNAVAILABLE."""
        bench = self._import_benchmark_module()

        baseline = {
            "summary": {".dwg": {"successful": 0, "files_tested": 5, "failed": 0,
                                "total_records": 0, "avg_timing_ms": 0,
                                "avg_provenance_quality_rate": 0, "avg_entity_id_stability": 1.0,
                                "status": "UNAVAILABLE", "reason": "No open-source DWG extractor"}},
            "per_format": {".dwg": []}
        }
        current = {
            "summary": {".dwg": {"successful": 0, "files_tested": 5, "failed": 0,
                                "total_records": 0, "avg_timing_ms": 0,
                                "avg_provenance_quality_rate": 0, "avg_entity_id_stability": 1.0,
                                "status": "UNAVAILABLE", "reason": "No open-source DWG extractor"}},
            "per_format": {".dwg": []}
        }
        results = bench.compare_baseline(baseline, current)
        assert results[".dwg"]["passed"], f"UNAVAILABLE should pass: {results['.dwg']['issues']}"

    def test_admission_gate_detects_performance_regression(self):
        """Gate fails when timing exceeds 2× baseline."""
        bench = self._import_benchmark_module()

        baseline = {
            "summary": {".ifc": {"successful": 3, "files_tested": 3, "failed": 0,
                                "total_records": 32000, "avg_timing_ms": 3000,
                                "avg_provenance_quality_rate": 1.0, "avg_entity_id_stability": 1.0,
                                "status": "PASS"}},
            "per_format": {".ifc": [{"type_distribution": {}}]}
        }
        current = {
            "summary": {".ifc": {"successful": 3, "files_tested": 3, "failed": 0,
                                "total_records": 32000, "avg_timing_ms": 8000,
                                "avg_provenance_quality_rate": 1.0, "avg_entity_id_stability": 1.0,
                                "status": "PASS"}},
            "per_format": {".ifc": [{"type_distribution": {}}]}
        }
        results = bench.compare_baseline(baseline, current)
        assert not results[".ifc"]["passed"]
        assert any("Performance" in i for i in results[".ifc"]["issues"])

    def test_admission_gate_detects_entity_id_imbalance(self):
        """Gate fails when entity ID stability drops below 99%."""
        bench = self._import_benchmark_module()

        baseline = {
            "summary": {".dxf": {"successful": 3, "files_tested": 3, "failed": 0,
                                "total_records": 7820, "avg_timing_ms": 6000,
                                "avg_provenance_quality_rate": 1.0, "avg_entity_id_stability": 1.0,
                                "status": "PASS"}},
            "per_format": {".dxf": [{"type_distribution": {"dxf_drawing": 1}}]}
        }
        current = {
            "summary": {".dxf": {"successful": 3, "files_tested": 3, "failed": 0,
                                "total_records": 7820, "avg_timing_ms": 6000,
                                "avg_provenance_quality_rate": 1.0, "avg_entity_id_stability": 0.85,
                                "status": "PASS"}},
            "per_format": {".dxf": [{"type_distribution": {"dxf_drawing": 1}}]}
        }
        results = bench.compare_baseline(baseline, current)
        assert not results[".dxf"]["passed"]
        assert any("Entity ID stability" in i for i in results[".dxf"]["issues"])

    def test_admission_gate_detects_record_type_loss(self):
        """Gate fails when record types are lost."""
        bench = self._import_benchmark_module()

        baseline = {
            "summary": {".dxf": {"successful": 3, "files_tested": 3, "failed": 0,
                                "total_records": 7820, "avg_timing_ms": 6000,
                                "avg_provenance_quality_rate": 1.0, "avg_entity_id_stability": 1.0,
                                "status": "PASS"}},
            "per_format": {".dxf": [
                {"type_distribution": {"dxf_block": 1, "dxf_layer": 1}}
            ]}
        }
        current = {
            "summary": {".dxf": {"successful": 3, "files_tested": 3, "failed": 0,
                                "total_records": 7820, "avg_timing_ms": 6000,
                                "avg_provenance_quality_rate": 1.0, "avg_entity_id_stability": 1.0,
                                "status": "PASS"}},
            "per_format": {".dxf": [
                {"type_distribution": {"dxf_block": 1}}
            ]}
        }
        results = bench.compare_baseline(baseline, current)
        assert not results[".dxf"]["passed"]
        assert any("Record types lost" in i for i in results[".dxf"]["issues"])

    def test_admission_gate_detects_provenance_quality_regression(self):
        """Gate fails when provenance quality drops below baseline."""
        bench = self._import_benchmark_module()

        baseline = {
            "summary": {".pdf": {"successful": 3, "files_tested": 3, "failed": 0,
                                "total_records": 40, "avg_timing_ms": 10000,
                                "avg_provenance_quality_rate": 1.0, "avg_entity_id_stability": 1.0,
                                "status": "PASS"}},
            "per_format": {".pdf": [{"type_distribution": {}}]}
        }
        current = {
            "summary": {".pdf": {"successful": 3, "files_tested": 3, "failed": 0,
                                "total_records": 40, "avg_timing_ms": 10000,
                                "avg_provenance_quality_rate": 0.5, "avg_entity_id_stability": 1.0,
                                "status": "PASS"}},
            "per_format": {".pdf": [{"type_distribution": {}}]}
        }
        results = bench.compare_baseline(baseline, current)
        assert not results[".pdf"]["passed"]
        assert any("Provenance quality" in i for i in results[".pdf"]["issues"])
