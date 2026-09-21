# -*- coding: utf-8 -*-
"""
test_gold_regression.py — Permanent Gold Corpus Regression Framework.

This test file is the release gate for SerapeumAI. It runs the current
extractors against the frozen GOLD_BENCHMARK_V1 corpus and verifies:
  - Extraction success (records produced)
  - Record counts meet minimums
  - Provenance is present
  - No regressions in protected capabilities

Each format has specific acceptance criteria. Failures block release.

Run: pytest src/tests/test_gold_regression.py -v
"""
from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from src.engine.extractors.base import ExtractionResult
from src.infra.persistence.database_manager import DatabaseManager
from src.application.api.fact_api import FactQueryAPI

# ──────────────────────────────────────────────────────────────
# CORPUS PATH
# ──────────────────────────────────────────────────────────────

CORPUS_DIR = Path(__file__).resolve().parents[2] / "_LOCAL_TEST_CORPUS" / "GOLD_BENCHMARK_V1"


def _corpus() -> Path:
    if not CORPUS_DIR.is_dir():
        pytest.skip(f"Gold corpus not found: {CORPUS_DIR}")
    return CORPUS_DIR


def _files(ext: str, corpus: Path) -> List[Path]:
    return sorted(corpus.glob(f"*{ext}"))


def _run(ext: str, index: int = 0, corpus: Optional[Path] = None) -> Optional[ExtractionResult]:
    """Run the appropriate extractor on the Nth file of given extension."""
    corpus = corpus or _corpus()
    files = _files(ext, corpus)
    if not files:
        return None
    path = files[min(index, len(files) - 1)]
    ext_str = ext.lower()

    dispatch = {
        ".pdf": "src.engine.extractors.pdf_extractor:UniversalPdfExtractor",
        ".docx": "src.engine.extractors.word_extractor:WordExtractor",
        ".doc": "src.engine.extractors.word_extractor:WordExtractor",
        ".pptx": "src.engine.extractors.pptx_extractor:PPTXExtractor",
        ".ppt": "src.engine.extractors.pptx_extractor:PPTXExtractor",
        ".xlsx": "src.engine.extractors.excel_extractor:ExcelExtractor",
        ".xlsm": "src.engine.extractors.excel_extractor:ExcelExtractor",
        ".xls": "src.engine.extractors.excel_extractor:ExcelExtractor",
        ".csv": "src.engine.extractors.csv_extractor:CsvExtractor",
        ".tsv": "src.engine.extractors.csv_extractor:CsvExtractor",
        ".txt": "src.engine.extractors.text_extractor:TextExtractor",
        ".md": "src.engine.extractors.text_extractor:TextExtractor",
        ".log": "src.engine.extractors.text_extractor:TextExtractor",
        ".json": "src.engine.extractors.json_extractor:JsonExtractor",
        ".xml": "src.engine.extractors.xml_extractor:XmlExtractor",
        ".yaml": "src.engine.extractors.yaml_extractor:YamlExtractor",
        ".yml": "src.engine.extractors.yaml_extractor:YamlExtractor",
        ".ifc": "src.engine.extractors.ifc_extractor:IFCExtractor",
        ".dxf": "src.engine.extractors.dxf_extractor:DXFExtractor",
        ".xer": "src.engine.extractors.p6_extractor:P6Extractor",
        ".mpp": "src.engine.extractors.mpxj_wrapper:MPXJWrapper",
        ".png": "src.engine.extractors.image_extractor:ImageExtractor",
        ".jpg": "src.engine.extractors.image_extractor:ImageExtractor",
        ".jpeg": "src.engine.extractors.image_extractor:ImageExtractor",
        ".bmp": "src.engine.extractors.image_extractor:ImageExtractor",
        ".tif": "src.engine.extractors.image_extractor:ImageExtractor",
        ".tiff": "src.engine.extractors.image_extractor:ImageExtractor",
        ".webp": "src.engine.extractors.image_extractor:ImageExtractor",
        ".dgn": "src.engine.extractors.dgn_extractor:DGNExtractor",
    }

    if ext_str not in dispatch:
        return None

    module_path, class_name = dispatch[ext_str].split(":")
    try:
        module = __import__(module_path, fromlist=[class_name])
        extractor = getattr(module, class_name)()
        return extractor.extract(str(path))
    except ImportError as e:
        return ExtractionResult(success=False, records=[], diagnostics=[f"ImportError: {e}"])
    except Exception as e:
        return ExtractionResult(success=False, records=[], diagnostics=[f"{type(e).__name__}: {e}"])


# ──────────────────────────────────────────────────────────────
# FORMAT-SPECIFIC BENCHMARKS
# ──────────────────────────────────────────────────────────────

class TestGoldRegressionPDF:
    def test_pdf_extracts_records(self):
        result = _run(".pdf", 2)  # GOLD_0124.pdf
        assert result is not None, "PDF file not found"
        assert result.success is True, f"PDF failed: {result.diagnostics}"
        assert len(result.records) > 0, "PDF produced zero records"

    def test_pdf_provenance_present(self):
        result = _run(".pdf", 2)
        if result and result.success:
            for rec in result.records[:5]:
                assert "provenance" in rec, f"Record missing provenance: {rec.get('type')}"


class TestGoldRegressionDOCX:
    def test_docx_extracts_records(self):
        result = _run(".docx", 0)
        assert result is not None
        assert result.success is True, f"DOCX failed: {result.diagnostics}"
        assert len(result.records) > 0


class TestGoldRegressionPPTX:
    def test_pptx_extracts_records(self):
        result = _run(".pptx", 0)
        assert result is not None
        assert result.success is True, f"PPTX failed: {result.diagnostics}"
        assert len(result.records) > 0


class TestGoldRegressionXLSX:
    def test_xlsx_extracts_records(self):
        result = _run(".xlsx", 0)  # GOLD_0142.xlsx (small)
        assert result is not None
        assert result.success is True, f"XLSX failed: {result.diagnostics}"
        assert len(result.records) > 0


class TestGoldRegressionDXF:
    """PROTECTED CAPABILITY."""

    def test_dxf_extracts_records(self):
        result = _run(".dxf", 0)  # GOLD_0153.dxf
        assert result is not None
        assert result.success is True, f"DXF failed: {result.diagnostics}"
        assert len(result.records) > 0, "DXF produced zero records"

    def test_dxf_entity_count_minimum(self):
        """PROTECTED: >100 entities from GOLD_0153.dxf."""
        result = _run(".dxf", 0)
        if result and result.success:
            assert len(result.records) > 100, (
                f"DXF below protected minimum: {len(result.records)} records"
            )


class TestGoldRegressionP6:
    """PROTECTED CAPABILITY."""

    def test_p6_extracts_records(self):
        result = _run(".xer", 0)  # GOLD_0118_JSON.xer
        assert result is not None
        assert result.success is True, f"P6 failed: {result.diagnostics}"
        assert len(result.records) > 0

    def test_p6_activity_count_minimum(self):
        """PROTECTED: >50 activities from GOLD_0118_JSON.xer."""
        result = _run(".xer", 0)
        if result and result.success:
            assert len(result.records) > 50, (
                f"P6 below protected minimum: {len(result.records)} records"
            )


class TestGoldRegressionIFC:
    """PROTECTED CAPABILITY (dependency-gated)."""

    def test_ifc_extracts_records(self):
        result = _run(".ifc", 2)  # GOLD_0158.ifc (smallest at 33MB)
        assert result is not None
        if "ImportError" in str(result.diagnostics):
            pytest.skip("ifcopenshell not installed")
        assert result.success is True, f"IFC failed: {result.diagnostics}"
        assert len(result.records) > 0


class TestGoldRegressionImages:
    def test_image_extracts_metadata(self):
        result = _run(".png", 0)
        assert result is not None
        assert result.success is True, f"Image failed: {result.diagnostics}"
        assert len(result.records) > 0


class TestGoldRegressionStructured:
    def test_csv(self):
        result = _run(".csv", 0)
        assert result and result.success, f"CSV failed: {result.diagnostics if result else 'N/A'}"

    def test_json(self):
        result = _run(".json", 0)
        assert result and result.success

    def test_xml(self):
        result = _run(".xml", 0)
        assert result and result.success

    def test_yaml(self):
        result = _run(".yaml", 0)
        assert result and result.success

    def test_txt(self):
        result = _run(".txt", 0)
        assert result and result.success


class TestGoldRegressionXLS:
    def test_xls(self):
        result = _run(".xls", 0)
        assert result is not None
        if "ImportError" in str(result.diagnostics):
            pytest.skip("xlrd not installed")
        assert result.success


class TestGoldRegressionMPP:
    def test_mpp(self):
        result = _run(".mpp", 0)
        assert result is not None
        if "ImportError" in str(result.diagnostics):
            pytest.skip("mpxj not installed")
        diag = str(result.diagnostics).lower()
        # JVM/Java unavailable is a known environment limitation, not a regression
        if any(k in diag for k in ("jvm", "jre", "java runtime not found", "java_home", "jdk")):
            pytest.skip("JVM/Java not available - MPP extraction blocked (environment limitation)")
        assert result.success


class TestGoldRegressionUnavailable:
    """Formats without extractors must report gracefully."""

    def test_dwg_reports_unavailable(self):
        corpus = _corpus()
        files = _files(".dwg", corpus)
        assert files, "No DWG files in corpus"
        # DWG has no extractor — verify it's not in the dispatch
        result = _run(".dwg", 0)
        assert result is None or result.success is False


# ──────────────────────────────────────────────────────────────
# PERFORMANCE BASELINE (informational)
# ──────────────────────────────────────────────────────────────

class TestGoldRegressionPerformance:
    def test_pdf_medium_timing(self):
        """GOLD_0124.pdf (62KB) < 5s."""
        corpus = _corpus()
        target = [f for f in _files(".pdf", corpus) if f.name == "GOLD_0124.pdf"]
        if not target:
            pytest.skip("GOLD_0124.pdf not found")
        from src.engine.extractors.pdf_extractor import UniversalPdfExtractor
        start = time.perf_counter()
        result = UniversalPdfExtractor().extract(str(target[0]))
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 5000, f"PDF too slow: {elapsed_ms:.0f}ms"

    def test_dxf_timing(self):
        """GOLD_0153.dxf (12.5MB) < 30s."""
        corpus = _corpus()
        target = [f for f in _files(".dxf", corpus) if f.name == "GOLD_0153.dxf"]
        if not target:
            pytest.skip("GOLD_0153.dxf not found")
        from src.engine.extractors.dxf_extractor import DXFExtractor
        start = time.perf_counter()
        result = DXFExtractor().extract(str(target[0]))
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 30000, f"DXF too slow: {elapsed_ms:.0f}ms"

    def test_p6_large_timing(self):
        """GOLD_0120_JSON.xer (5MB) < 5s."""
        corpus = _corpus()
        target = [f for f in _files(".xer", corpus) if f.name == "GOLD_0120_JSON.xer"]
        if not target:
            pytest.skip("GOLD_0120_JSON.xer not found")
        from src.engine.extractors.p6_extractor import P6Extractor
        start = time.perf_counter()
        result = P6Extractor().extract(str(target[0]))
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 5000, f"P6 too slow: {elapsed_ms:.0f}ms"


# ──────────────────────────────────────────────────────────────
# TRUST BEHAVIOR (DETERMINISTIC, NO LLM)
# ──────────────────────────────────────────────────────────────

class TestGoldRegressionTrust:
    @pytest.fixture
    def trust_db(self):
        db_path = os.path.join(tempfile.gettempdir(), f"wp06_trust_{os.getpid()}.db")
        if os.path.exists(db_path):
            os.unlink(db_path)
        db = DatabaseManager(db_path)
        yield db
        db.close_all_instances()
        if os.path.exists(db_path):
            os.unlink(db_path)

    def test_refusal_when_no_facts(self, trust_db):
        from src.application.services.coverage_gate import CoverageGate
        gate = CoverageGate(trust_db)
        result = gate.check("What is the fire rating?", project_id="empty-project")
        assert result["is_complete"] is False

    def test_conflict_disclosure_structural(self, trust_db):
        from src.application.orchestrators.agent_orchestrator import AgentOrchestrator
        from unittest.mock import MagicMock
        db_path = os.path.join(tempfile.gettempdir(), f"wp06_orch_{os.getpid()}.db")
        if os.path.exists(db_path):
            os.unlink(db_path)
        db = DatabaseManager(db_path)
        orch = AgentOrchestrator(db=db, llm=MagicMock())
        db.close_all_instances()
        if os.path.exists(db_path):
            os.unlink(db_path)

        conflicts = [{
            "fact_type": "bim.element", "subject_id": "W1",
            "conflicting_facts": [
                {"fact_id": "a", "value": "120min", "status": "VALIDATED", "method_id": "ifc"},
                {"fact_id": "b", "value": "60min", "status": "VALIDATED", "method_id": "pdf"},
            ],
        }]
        disclosure = orch._compose_conflict_disclosure(conflicts)
        assert "CONFLICT DISCLOSURE" in disclosure
        assert "120min" in disclosure
        assert "60min" in disclosure

    def test_no_conflict_no_disclosure(self):
        from src.application.orchestrators.agent_orchestrator import AgentOrchestrator
        from unittest.mock import MagicMock
        db_path = os.path.join(tempfile.gettempdir(), f"wp06_orch2_{os.getpid()}.db")
        if os.path.exists(db_path):
            os.unlink(db_path)
        db = DatabaseManager(db_path)
        orch = AgentOrchestrator(db=db, llm=MagicMock())
        db.close_all_instances()
        if os.path.exists(db_path):
            os.unlink(db_path)
        assert orch._compose_conflict_disclosure([]) == ""

    def test_provenance_available(self, trust_db):
        trust_db.upsert_project(project_id="p1", name="T", root="/tmp")
        trust_db._exec(
            "INSERT OR REPLACE INTO file_registry (file_id, project_id, first_seen_path, created_at) "
            "VALUES ('f1','p1','t.pdf',1000)")
        trust_db._exec(
            "INSERT OR REPLACE INTO file_versions "
            "(file_version_id,file_id,sha256,size_bytes,file_ext,imported_at,source_path) "
            "VALUES ('fv1','f1','abc',100,'.pdf',1000,'/tmp/t.pdf')")
        trust_db._exec(
            "INSERT OR REPLACE INTO facts "
            "(fact_id,project_id,fact_type,subject_kind,subject_id,as_of_json,"
            "value_type,value_json,status,confidence,method_id,created_at,updated_at) "
            "VALUES ('fct1','p1','bim.element','element','W1','{}','json','v42',"
            "'VALIDATED',1.0,'test',1000,1000)")
        trust_db._exec(
            "INSERT OR REPLACE INTO fact_inputs (fact_id,file_version_id,location_json,input_kind) "
            "VALUES ('fct1','fv1','{\"page\":2}','evidence')")
        trust_db.commit()

        row = trust_db.execute(
            "SELECT fv.source_path, fi.location_json FROM fact_inputs fi "
            "LEFT JOIN file_versions fv ON fv.file_version_id=fi.file_version_id "
            "WHERE fi.fact_id='fct1' LIMIT 1"
        ).fetchone()
        assert row is not None
        assert row[0] == "/tmp/t.pdf"
        assert json.loads(row[1])["page"] == 2

    def test_project_isolation(self, trust_db):
        trust_db.upsert_project(project_id="pa", name="A", root="/tmp")
        trust_db.upsert_project(project_id="pb", name="B", root="/tmp")
        trust_db._exec(
            "INSERT OR REPLACE INTO facts (fact_id,project_id,fact_type,subject_kind,subject_id,"
            "as_of_json,value_type,value_json,status,confidence,method_id,created_at,updated_at) "
            "VALUES ('fa','pa','schedule.activity','activity','x','{}','json','v1',"
            "'VALIDATED',1.0,'m',1,1)")
        trust_db._exec(
            "INSERT OR REPLACE INTO facts (fact_id,project_id,fact_type,subject_kind,subject_id,"
            "as_of_json,value_type,value_json,status,confidence,method_id,created_at,updated_at) "
            "VALUES ('fb','pb','schedule.activity','activity','x','{}','json','v2',"
            "'VALIDATED',1.0,'m',1,1)")
        trust_db.commit()

        # Query directly to verify isolation (bypasses intent inference)
        rows_a = trust_db.execute(
            "SELECT fact_id FROM facts WHERE project_id='pa' AND status IN ('VALIDATED','HUMAN_CERTIFIED')"
        ).fetchall()
        rows_b = trust_db.execute(
            "SELECT fact_id FROM facts WHERE project_id='pb' AND status IN ('VALIDATED','HUMAN_CERTIFIED')"
        ).fetchall()
        ids_a = {r[0] for r in rows_a}
        ids_b = {r[0] for r in rows_b}
        assert "fa" in ids_a, "Project A fact missing"
        assert "fb" not in ids_a, "Project B fact leaked into A"
        assert "fb" in ids_b, "Project B fact missing"
        assert "fa" not in ids_b, "Project A fact leaked into B"


# ──────────────────────────────────────────────────────────────
# WP-05-A REGRESSION PROTECTION
# ──────────────────────────────────────────────────────────────

class TestGoldRegressionWP05A:
    def test_lifecycle_open_reviewed_resolved(self):
        db_path = os.path.join(tempfile.gettempdir(), f"wp06_lc_{os.getpid()}.db")
        if os.path.exists(db_path):
            os.unlink(db_path)
        db = DatabaseManager(db_path)
        db.upsert_project(project_id="p", name="P", root="/tmp")
        db._exec("INSERT OR REPLACE INTO facts "
            "(fact_id,project_id,fact_type,subject_kind,subject_id,as_of_json,"
            "value_type,value_json,status,confidence,method_id,created_at,updated_at) "
            "VALUES ('f1','p','t','s','x','{}','json','A','VALIDATED',1.0,'m',1,1)")
        db._exec("INSERT OR REPLACE INTO facts "
            "(fact_id,project_id,fact_type,subject_kind,subject_id,as_of_json,"
            "value_type,value_json,status,confidence,method_id,created_at,updated_at) "
            "VALUES ('f2','p','t','s','x','{}','json','B','VALIDATED',1.0,'m',1,1)")
        db.commit()

        from src.domain.intelligence.conflict_detector import detect_and_store_conflicts
        conflicts = detect_and_store_conflicts(db, "p", [
            {"fact_id": "f1", "project_id": "p", "fact_type": "t", "subject_id": "x",
             "value": "A", "status": "VALIDATED", "confidence": 1.0, "method_id": "m", "inputs": []},
            {"fact_id": "f2", "project_id": "p", "fact_type": "t", "subject_id": "x",
             "value": "B", "status": "VALIDATED", "confidence": 1.0, "method_id": "m", "inputs": []},
        ])
        assert len(conflicts) == 1
        cid = conflicts[0]["conflict_id"]

        assert db.get_conflict_by_id(cid)["resolution"] == "UNRESOLVED"
        db.mark_conflict_reviewed(cid, reviewer="test")
        assert db.get_conflict_by_id(cid)["resolution"] == "REVIEWED"
        db.resolve_conflict(cid, accepted_fact_id="f1", resolver="test")
        c = db.get_conflict_by_id(cid)
        assert c["resolution"] == "RESOLVED"

        vals = c.get("values_parsed", [])
        if isinstance(vals, str):
            vals = json.loads(vals)
        assert {v["value"] for v in vals} == {"A", "B"}

        db.close_all_instances()
        if os.path.exists(db_path):
            os.unlink(db_path)

    def test_no_silent_selection(self):
        db_path = os.path.join(tempfile.gettempdir(), f"wp06_ns_{os.getpid()}.db")
        if os.path.exists(db_path):
            os.unlink(db_path)
        db = DatabaseManager(db_path)
        from src.application.orchestrators.agent_orchestrator import AgentOrchestrator
        from unittest.mock import MagicMock
        orch = AgentOrchestrator(db=db, llm=MagicMock())
        db.close_all_instances()
        if os.path.exists(db_path):
            os.unlink(db_path)

        conflicts = [{
            "fact_type": "bim.element", "subject_id": "W1",
            "conflicting_facts": [
                {"fact_id": "a", "value": "100mm", "status": "VALIDATED", "method_id": "ifc"},
                {"fact_id": "b", "value": "200mm", "status": "VALIDATED", "method_id": "pdf"},
            ],
        }]
        d = orch._compose_conflict_disclosure(conflicts)
        assert "100mm" in d and "200mm" in d
