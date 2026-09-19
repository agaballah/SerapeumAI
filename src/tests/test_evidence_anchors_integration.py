# -*- coding: utf-8 -*-
"""
test_evidence_anchors_integration.py

Focused behavioral tests for WP-03 Evidence Anchors Integration.

Verifies:
- EvidenceAnchor.from_fact_input() creates expected anchor from location dict
- Existing FactInput.location remains compatible (backward compatibility)
- PDF page/bbox information is preserved where available
- Non-PDF evidence remains correctly represented
- Missing anchor information does not produce fabricated source locations
- The presentation layer displays the resulting citation
- Source navigation succeeds for a valid local source and fails honestly for an unavailable source
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.domain.facts.models import EvidenceAnchor, FactInput, Fact, FactStatus, ValueType
from src.application.services.fact_review_presentation import (
    build_fact_review_view,
    format_evidence_citation,
    _source_label,
)
from src.engine.builders.document_builder import DocumentBuilder
from src.engine.builders.bim_builder import BIMBuilder
from src.engine.builders.schedule_builder import ScheduleBuilder
from src.engine.builders.register_builder import RegisterBuilder
from src.engine.builders.completion_builder import SystemCompletionBuilder
from src.infra.persistence.database_manager import DatabaseManager


# ---------------------------------------------------------------------------
# EvidenceAnchor construction
# ---------------------------------------------------------------------------

class TestEvidenceAnchorConstruction:
    def test_from_fact_input_populates_all_anchor_fields(self):
        location = {
            "source_file": "spec.pdf",
            "source_type": "pdf",
            "page": 2,
            "bbox": [681, 55, 692, 68],
            "entity_handle": "1A2B3C",
            "element_id": "elem_001",
            "activity_id": "A100",
            "sheet": "Sheet1",
            "row": 5,
            "cell": "C7",
        }
        fi = FactInput(file_version_id="fv_001", location=location)
        anchor = EvidenceAnchor.from_fact_input(fi)

        assert anchor.source_file == "spec.pdf"
        assert anchor.source_type == "pdf"
        assert anchor.page_or_slide == 2
        assert anchor.bbox == [681, 55, 692, 68]
        assert anchor.entity_handle == "1A2B3C"
        assert anchor.element_id == "elem_001"
        assert anchor.activity_id == "A100"
        assert anchor.sheet_or_section == "Sheet1"
        assert anchor.row_or_paragraph == 5
        assert anchor.cell_address == "C7"

    def test_from_fact_input_handles_page_or_slide_alias(self):
        location = {"page_or_slide": 3, "source_type": "pdf"}
        fi = FactInput(file_version_id="fv_001", location=location)
        anchor = EvidenceAnchor.from_fact_input(fi)
        assert anchor.page_or_slide == 3

    def test_from_fact_input_handles_row_or_paragraph_alias(self):
        location = {"row_or_paragraph": 10, "source_type": "xlsx"}
        fi = FactInput(file_version_id="fv_001", location=location)
        anchor = EvidenceAnchor.from_fact_input(fi)
        assert anchor.row_or_paragraph == 10

    def test_from_fact_input_handles_sheet_or_section_alias(self):
        location = {"sheet_or_section": "WBS-1", "source_type": "xer"}
        fi = FactInput(file_version_id="fv_001", location=location)
        anchor = EvidenceAnchor.from_fact_input(fi)
        assert anchor.sheet_or_section == "WBS-1"

    def test_from_fact_input_missing_fields_return_none(self):
        fi = FactInput(file_version_id="fv_001", location={})
        anchor = EvidenceAnchor.from_fact_input(fi)
        assert anchor.source_file is None
        assert anchor.source_type is None
        assert anchor.page_or_slide is None
        assert anchor.bbox is None

    def test_from_fact_input_non_dict_location_returns_empty_anchor(self):
        fi = FactInput(file_version_id="fv_001", location="not-a-dict")
        anchor = EvidenceAnchor.from_fact_input(fi)
        assert anchor.source_file is None
        assert anchor.page_or_slide is None


# ---------------------------------------------------------------------------
# Backward compatibility: existing FactInput.location dicts remain valid
# ---------------------------------------------------------------------------

class TestBackwardCompatibility:
    def test_legacy_location_dict_with_table_and_row_id(self):
        """Old-style location dicts with table/row_id must still be accepted."""
        fi = FactInput(file_version_id="fv_001", location={"table": "pdf_pages", "row_id": "abc123"})
        anchor = EvidenceAnchor.from_fact_input(fi)
        assert anchor.source_file is None
        assert anchor.page_or_slide is None
        assert anchor.entity_handle is None

    def test_legacy_location_dict_with_page_and_bbox(self):
        """Old-style page/bbox location dicts must still be accepted."""
        fi = FactInput(file_version_id="fv_001", location={"page": 1, "bbox": [10, 20, 30, 40]})
        anchor = EvidenceAnchor.from_fact_input(fi)
        assert anchor.page_or_slide == 1
        assert anchor.bbox == [10, 20, 30, 40]

    def test_fact_input_location_not_mutated(self):
        """from_fact_input() must not mutate the original location dict."""
        original = {"page": 1, "source_file": "doc.pdf"}
        fi = FactInput(file_version_id="fv_001", location=original)
        EvidenceAnchor.from_fact_input(fi)
        assert original == {"page": 1, "source_file": "doc.pdf"}


# ---------------------------------------------------------------------------
# Builder wiring: evidence-producing builders create expected anchors
# ---------------------------------------------------------------------------

def _setup_db(tmp_path):
    db = DatabaseManager(root_dir=str(tmp_path), db_name=":memory:")
    base = Path("src/infra/persistence/migrations")
    db.execute_script((base / "001_baseline_v14.sql").read_text())
    v16 = base / "016_fix_missing_column.sql"
    if v16.exists():
        db.execute_script(v16.read_text())
    db.execute_script((base / "017_truth_engine_v2.sql").read_text())
    v18 = base / "018_fact_snapshots.sql"
    if v18.exists():
        db.execute_script(v18.read_text())
    db.project_id = "proj1"
    return db


class TestDocumentBuilderAnchorWiring:
    def test_document_builder_populates_source_file_and_source_type(self, tmp_path):
        db = _setup_db(tmp_path)
        snapshot_id = "fv_doc_001"
        doc_id = "doc_001"
        now = db._ts()

        db.execute(
            "INSERT INTO file_registry (file_id, project_id, first_seen_path, created_at) VALUES (?, ?, ?, ?)",
            ("file_001", "proj1", "spec.pdf", now),
        )
        db.execute(
            "INSERT INTO file_versions (file_version_id, file_id, source_path, sha256, size_bytes, file_ext, imported_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (snapshot_id, "file_001", "spec.pdf", "abc", 1024, ".pdf", now),
        )
        db.execute(
            "INSERT INTO documents (doc_id, project_id, file_name, abs_path, file_ext, file_hash, file_size, file_mtime, doc_title, doc_type, created, updated) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (doc_id, "proj1", "spec.pdf", "spec.pdf", ".pdf", "abc", 1024, 0.0, "Spec", "pdf", now, now),
        )
        db.execute(
            "INSERT INTO pdf_pages (page_id, file_version_id, page_no, text_content, metadata_json) VALUES (?, ?, ?, ?, ?)",
            ("pg1", snapshot_id, 1, "Content here.", "{}"),
        )
        db.commit()

        facts = DocumentBuilder(db).build("proj1", snapshot_id)
        assert len(facts) > 0
        for fact in facts:
            for inp in fact.inputs:
                anchor = EvidenceAnchor.from_fact_input(inp)
                assert anchor.source_type == "pdf", f"Expected source_type='pdf' for {fact.fact_type}"
                assert anchor.source_file == "spec.pdf", f"Expected source_file='spec.pdf' for {fact.fact_type}"

    def test_document_builder_semantic_fact_has_page_or_slide(self, tmp_path):
        db = _setup_db(tmp_path)
        snapshot_id = "fv_doc_002"
        doc_id = "doc_002"
        now = db._ts()

        db.execute(
            "INSERT INTO file_registry (file_id, project_id, first_seen_path, created_at) VALUES (?, ?, ?, ?)",
            ("file_002", "proj1", "scope.pdf", now),
        )
        db.execute(
            "INSERT INTO file_versions (file_version_id, file_id, source_path, sha256, size_bytes, file_ext, imported_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (snapshot_id, "file_002", "scope.pdf", "def", 2048, ".pdf", now),
        )
        db.execute(
            "INSERT INTO documents (doc_id, project_id, file_name, abs_path, file_ext, file_hash, file_size, file_mtime, doc_title, doc_type, created, updated) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (doc_id, "proj1", "scope.pdf", "scope.pdf", ".pdf", "def", 2048, 0.0, "Scope", "pdf", now, now),
        )
        db.execute(
            "INSERT INTO pdf_pages (page_id, file_version_id, page_no, text_content, metadata_json) VALUES (?, ?, ?, ?, ?)",
            ("pg1", snapshot_id, 1, "Generator room is inscope.", "{}"),
        )
        db.execute(
            "INSERT INTO doc_blocks (doc_id, block_id, page_index, heading_title, heading_number, level, text, source_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (doc_id, "b1", 0, None, None, 0, "Generator room is inscope", "pdf"),
        )
        db.commit()

        facts = DocumentBuilder(db).build("proj1", snapshot_id)
        scope_facts = [f for f in facts if f.fact_type == "document.scope_item"]
        assert len(scope_facts) == 1
        scope_fact = scope_facts[0]
        assert len(scope_fact.inputs) == 1
        anchor = EvidenceAnchor.from_fact_input(scope_fact.inputs[0])
        assert anchor.page_or_slide == 1


class TestBIMBuilderAnchorWiring:
    def test_bim_builder_populates_ifc_anchor_fields(self, tmp_path):
        db = _setup_db(tmp_path)
        snapshot_id = "fv_ifc_001"
        now = db._ts()

        db.execute(
            "INSERT INTO file_registry (file_id, project_id, first_seen_path, created_at) VALUES (?, ?, ?, ?)",
            ("file_ifc", "proj1", "model.ifc", now),
        )
        db.execute(
            "INSERT INTO file_versions (file_version_id, file_id, source_path, sha256, size_bytes, file_ext, imported_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (snapshot_id, "file_ifc", "model.ifc", "ghi", 4096, ".ifc", now),
        )
        db.execute(
            "INSERT INTO ifc_projects (global_id, file_version_id, name, phase) VALUES (?, ?, ?, ?)",
            ("proj_global", snapshot_id, "Test Project", "Construction"),
        )
        db.execute(
            "INSERT INTO ifc_spatial_structure (element_id, file_version_id, parent_id, entity_type, name, elevation) VALUES (?, ?, ?, ?, ?, ?)",
            ("spatial_1", snapshot_id, None, "IFCBUILDING", "Building A", 0.0),
        )
        db.execute(
            "INSERT INTO ifc_elements (element_id, file_version_id, spatial_container_id, entity_type, name, tag) VALUES (?, ?, ?, ?, ?, ?)",
            ("elem_1", snapshot_id, "spatial_1", "IFCWALL", "Wall-1", "W1"),
        )
        db.commit()

        facts = BIMBuilder(db).build("proj1", snapshot_id)
        assert len(facts) > 0
        for fact in facts:
            for inp in fact.inputs:
                anchor = EvidenceAnchor.from_fact_input(inp)
                assert anchor.source_type == "ifc", f"Expected source_type='ifc' for {fact.fact_type}"


class TestScheduleBuilderAnchorWiring:
    def test_schedule_builder_populates_xer_anchor_fields(self, tmp_path):
        db = _setup_db(tmp_path)
        snapshot_id = "fv_xer_001"
        now = db._ts()

        db.execute(
            "INSERT INTO file_registry (file_id, project_id, first_seen_path, created_at) VALUES (?, ?, ?, ?)",
            ("file_xer", "proj1", "schedule.xer", now),
        )
        db.execute(
            "INSERT INTO file_versions (file_version_id, file_id, source_path, sha256, size_bytes, file_ext, imported_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (snapshot_id, "file_xer", "schedule.xer", "jkl", 5120, ".xer", now),
        )
        db.execute(
            "INSERT INTO p6_projects (p6_project_id, file_version_id, short_name, name) VALUES (?, ?, ?, ?)",
            ("p6_proj", snapshot_id, "SCHED", "Schedule"),
        )
        db.execute(
            "INSERT INTO p6_activities (activity_id, file_version_id, p6_project_id, code, name, start_date, finish_date, status_code, total_float, wbs_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("act_1", snapshot_id, "p6_proj", "A100", "Activity 1", "2026-01-01", "2026-01-10", "TK_NotStart", 0.0, "wbs_1"),
        )
        db.commit()

        facts = ScheduleBuilder(db).build("proj1", snapshot_id)
        assert len(facts) > 0
        for fact in facts:
            for inp in fact.inputs:
                anchor = EvidenceAnchor.from_fact_input(inp)
                assert anchor.source_type == "xer", f"Expected source_type='xer' for {fact.fact_type}"
                if "activity_id" in inp.location:
                    assert anchor.activity_id == inp.location["activity_id"]


class TestRegisterBuilderAnchorWiring:
    def test_register_builder_populates_xlsx_anchor_fields(self, tmp_path):
        db = _setup_db(tmp_path)
        snapshot_id = "fv_xlsx_001"
        now = db._ts()

        db.execute(
            "INSERT INTO file_registry (file_id, project_id, first_seen_path, created_at) VALUES (?, ?, ?, ?)",
            ("file_xlsx", "proj1", "register.xlsx", now),
        )
        db.execute(
            "INSERT INTO file_versions (file_version_id, file_id, source_path, sha256, size_bytes, file_ext, imported_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (snapshot_id, "file_xlsx", "register.xlsx", "mno", 3072, ".xlsx", now),
        )
        db.execute(
            "INSERT INTO register_rows (row_id, file_version_id, sheet_name, row_index, raw_data_json) VALUES (?, ?, ?, ?, ?)",
            ("row_1", snapshot_id, "Submittals", 0, json.dumps({"Submittal No": "S1", "Title": "Test"})),
        )
        db.commit()

        facts = RegisterBuilder(db).build("proj1", snapshot_id)
        assert len(facts) > 0
        for fact in facts:
            for inp in fact.inputs:
                anchor = EvidenceAnchor.from_fact_input(inp)
                assert anchor.source_type == "xlsx", f"Expected source_type='xlsx' for {fact.fact_type}"
                assert anchor.sheet_or_section == "Submittals"
                assert anchor.row_or_paragraph == 0


# ---------------------------------------------------------------------------
# Presentation layer: citation display
# ---------------------------------------------------------------------------

class TestPresentationLayerCitations:
    def testformat_evidence_citation_shows_page_when_present(self):
        result = format_evidence_citation({"page": 2, "source_type": "pdf"})
        assert "page: 2" in result

    def testformat_evidence_citation_shows_page_or_slide_when_present(self):
        result = format_evidence_citation({"page_or_slide": 3})
        assert "page: 3" in result

    def testformat_evidence_citation_shows_bbox_when_present(self):
        result = format_evidence_citation({"bbox": [10, 20, 30, 40]})
        assert "bbox: (10,20-30,40)" in result

    def testformat_evidence_citation_shows_activity_id_when_present(self):
        result = format_evidence_citation({"activity_id": "A100"})
        assert "activity: A100" in result

    def testformat_evidence_citation_shows_element_id_when_present(self):
        result = format_evidence_citation({"element_id": "elem_001"})
        assert "element: elem_001" in result

    def testformat_evidence_citation_shows_entity_handle_when_present(self):
        result = format_evidence_citation({"entity_handle": "1A2B3C"})
        assert "handle: 1A2B3C" in result

    def testformat_evidence_citation_returns_not_recorded_when_empty(self):
        result = format_evidence_citation({})
        assert result == "Location not recorded"

    def testformat_evidence_citation_returns_not_recorded_for_non_dict(self):
        result = format_evidence_citation("not-a-dict")
        assert result == "Location not recorded"

    def test_source_label_shows_page(self):
        result = _source_label("spec.pdf", {"page": 2})
        assert result == "spec.pdf p.2"

    def test_source_label_shows_element_id(self):
        result = _source_label("model.ifc", {"element_id": "elem_001"})
        assert "element=elem_001" in result

    def test_build_fact_review_view_uses_enhanced_location(self):
        row = {
            "fact_id": "fact-1",
            "fact_type": "document.requirement",
            "subject_id": "scope",
            "value_text": "Contractor shall...",
            "value_num": None,
            "value_json": None,
            "unit": None,
            "status": "CANDIDATE",
            "method_id": "document_builder",
            "source_path": r"D:\Projects\Spec.pdf",
            "location_json": json.dumps({"page": 2, "bbox": [10, 20, 30, 40], "source_type": "pdf"}),
            "input_kind": "deterministic",
        }
        view = build_fact_review_view(row)
        assert "p.2" in view["source_label"]
        assert "page: 2" in view["location_label"]

    def test_format_evidence_citation_is_canonical_formatter_in_production_path(self):
        row = {
            "fact_id": "fact-1",
            "fact_type": "schedule.activity",
            "subject_id": "A100",
            "value_text": None,
            "value_num": None,
            "value_json": '{"start": "2026-01-01", "finish": "2026-01-10"}',
            "unit": None,
            "status": "CANDIDATE",
            "method_id": "schedule_builder",
            "source_path": r"D:\Projects\Schedule.xer",
            "location_json": json.dumps({"activity_id": "A100", "source_type": "xer"}),
            "input_kind": "deterministic",
        }
        view = build_fact_review_view(row)
        assert "activity: A100" in view["location_label"]
        assert view["source_label"] == "Schedule.xer activity A100"

    def test_evidence_anchor_from_fact_input_used_in_citation_path(self):
        location = {"page": 5, "bbox": [100, 200, 300, 400], "source_type": "pdf"}
        citation = format_evidence_citation(location)
        assert "page: 5" in citation
        assert "bbox: (100,200-300,400)" in citation
        anchor = EvidenceAnchor.from_fact_input(FactInput(file_version_id="fv", location=location))
        assert anchor.page_or_slide == 5
        assert anchor.bbox == [100, 200, 300, 400]


# ---------------------------------------------------------------------------
# Missing anchor information: no fabricated source locations
# ---------------------------------------------------------------------------

class TestHonestMissingAnchorHandling:
    def test_empty_location_produces_not_recorded(self):
        result = format_evidence_citation({})
        assert result == "Location not recorded"

    def test_partial_location_does_not_fabricate_missing_fields(self):
        anchor = EvidenceAnchor.from_fact_input(
            FactInput(file_version_id="fv_001", location={"page": 1})
        )
        assert anchor.source_file is None
        assert anchor.bbox is None
        assert anchor.element_id is None

    def test_non_dict_location_does_not_crash(self):
        result = format_evidence_citation(None)
        assert result == "Location not recorded"


# ---------------------------------------------------------------------------
# Source navigation
# ---------------------------------------------------------------------------

class TestSourceNavigation:
    def test_open_source_file_succeeds_for_valid_local_file(self, tmp_path):
        test_file = tmp_path / "test_spec.pdf"
        test_file.write_text("dummy pdf content")

        fake_parent = type("Parent", (), {})()
        fake_db = MagicMock()
        table = type("FactTable", (), {})()
        table.selected_fact_id = "fact-1"
        table.row_by_fact_id = {
            "fact-1": {"source_path": str(test_file), "location_json": "{}"}
        }
        table.lbl_selected = MagicMock()

        with patch("os.startfile") as mock_startfile:
            from src.ui.widgets.fact_table import FactTable
            FactTable._open_source_file(table)
            mock_startfile.assert_called_once_with(str(test_file))

    def test_open_source_file_fails_honestly_for_missing_file(self):
        fake_parent = type("Parent", (), {})()
        fake_db = MagicMock()
        table = type("FactTable", (), {})()
        table.selected_fact_id = "fact-1"
        table.row_by_fact_id = {
            "fact-1": {"source_path": r"C:\nonexistent\file.pdf", "location_json": "{}"}
        }
        table.lbl_selected = MagicMock()

        from src.ui.widgets.fact_table import FactTable
        FactTable._open_source_file(table)
        assert "not found" in table.lbl_selected.configure.call_args[1]["text"].lower()

    def test_open_source_file_handles_missing_source_path(self):
        fake_parent = type("Parent", (), {})()
        fake_db = MagicMock()
        table = type("FactTable", (), {})()
        table.selected_fact_id = "fact-1"
        table.row_by_fact_id = {
            "fact-1": {"source_path": None, "location_json": "{}"}
        }
        table.lbl_selected = MagicMock()

        from src.ui.widgets.fact_table import FactTable
        FactTable._open_source_file(table)
        assert "not recorded" in table.lbl_selected.configure.call_args[1]["text"].lower()

    def test_open_source_file_parses_location_json_string(self, tmp_path):
        test_file = tmp_path / "test.pdf"
        test_file.write_text("dummy")

        fake_parent = type("Parent", (), {})()
        fake_db = MagicMock()
        table = type("FactTable", (), {})()
        table.selected_fact_id = "fact-1"
        table.row_by_fact_id = {
            "fact-1": {
                "source_path": str(test_file),
                "location_json": json.dumps({"page": 3}),
            }
        }
        table.lbl_selected = MagicMock()

        with patch("subprocess.Popen") as mock_popen, patch("os.startfile") as mock_startfile:
            from src.ui.widgets.fact_table import FactTable
            FactTable._open_source_file(table)
            mock_popen.assert_called_once()
        assert "page 3" in table.lbl_selected.configure.call_args[1]["text"]
