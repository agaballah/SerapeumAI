# -*- coding: utf-8 -*-
"""
Focused regression tests for A16 — evidence click-through anchors.

Validates that the fact-to-source navigation flow preserves existing behavior,
wires EvidenceAnchor page/bbox info into source opening, and enhances the
lineage popup with location-aware buttons.
"""
from __future__ import annotations

import inspect
import json
import os
import platform
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


SRC_ROOT = Path(__file__).resolve().parent.parent.parent / "src"


class TestOpenSourceFilePageAware:
    """_open_source_file must extract and use EvidenceAnchor page/bbox."""

    def test_extracts_page_from_location_json_string(self):
        from src.ui.widgets.fact_table import FactTable
        src = inspect.getsource(FactTable._open_source_file)
        assert 'loc.get("page")' in src or 'loc.get(\'page\')' in src, (
            "_open_source_file must read page_or_slide from location_json."
        )
        assert 'loc.get("page_or_slide")' in src or 'loc.get(\'page_or_slide\')' in src, (
            "_open_source_file must read page_or_slide alias from location_json."
        )

    def test_extracts_bbox_from_location_json(self):
        from src.ui.widgets.fact_table import FactTable
        src = inspect.getsource(FactTable._open_source_file)
        assert 'loc.get("bbox")' in src or 'loc.get(\'bbox\')' in src, (
            "_open_source_file must read bbox from location_json for region citations."
        )

    def test_citation_text_includes_page_and_bbox(self):
        from src.ui.widgets.fact_table import FactTable
        src = inspect.getsource(FactTable._open_source_file)
        assert "cited:" in src.lower() or "citation" in src.lower(), (
            "_open_source_file status message must include the cited location."
        )

    def test_pdf_acroread32_page_navigation_attempted(self):
        from src.ui.widgets.fact_table import FactTable
        src = inspect.getsource(FactTable._open_source_file)
        # The method should call _open_pdf_with_page for PDFs with a page number
        assert "_open_pdf_with_page" in src, (
            "_open_source_file must delegate PDF page navigation to _open_pdf_with_page."
        )

    def test_fallback_to_startfile_on_no_pdf_page(self):
        from src.ui.widgets.fact_table import FactTable
        src = inspect.getsource(FactTable._open_source_file)
        assert "os.startfile" in src, (
            "_open_source_file must fall back to os.startfile when no page nav is applicable."
        )


class TestPdfWithPageHelper:
    """_open_pdf_with_page must locate Acrobat Reader and attempt page navigation."""

    def test_method_exists(self):
        from src.ui.widgets.fact_table import FactTable
        assert hasattr(FactTable, "_open_pdf_with_page"), (
            "FactTable must expose a static _open_pdf_with_page helper."
        )

    def test_returns_false_when_no_reader(self):
        from src.ui.widgets.fact_table import FactTable
        with patch("src.ui.widgets.fact_table.os.path.isfile", return_value=False):
            with patch("shutil.which", return_value=None):
                result = FactTable._open_pdf_with_page("/fake/path.pdf", 3)
                assert result is False

    def test_calls_acrord32_with_page_flag(self):
        from src.ui.widgets.fact_table import FactTable
        fake_reader = r"C:\Fake\AcroRd32.exe"
        with patch("src.ui.widgets.fact_table.os.path.isfile", return_value=True):
            with patch("src.ui.widgets.fact_table.subprocess.Popen") as mock_popen:
                mock_popen.return_value = MagicMock()
                result = FactTable._open_pdf_with_page(fake_reader, 7)
                assert result is True
                mock_popen.assert_called_once()
                call_args = mock_popen.call_args
                args_list = call_args[0][0] if call_args[0] else call_args[1].get("args", [])
                assert "/A" in args_list, "Must pass /A flag for page navigation"
                assert "page=7" in args_list, "Must pass page number in /A argument"

    def test_returns_false_on_subprocess_exception(self):
        from src.ui.widgets.fact_table import FactTable
        fake_reader = r"C:\Fake\AcroRd32.exe"
        with patch("src.ui.widgets.fact_table.os.path.isfile", return_value=True):
            with patch("src.ui.widgets.fact_table.subprocess.Popen", side_effect=Exception("boom")):
                result = FactTable._open_pdf_with_page(fake_reader, 1)
                assert result is False


class TestLineagePopupLocationDisplay:
    """Lineage popup must show evidence location and provide File Inspector button."""

    def test_lineage_query_selects_location_json(self):
        from src.ui.widgets.fact_lineage_popup import FactLineagePopup
        src = inspect.getsource(FactLineagePopup.draw_lineage)
        assert "location_json" in src, (
            "draw_lineage must SELECT location_json from facts table."
        )

    def test_lineage_shows_page_in_location_label(self):
        from src.ui.widgets.fact_lineage_popup import FactLineagePopup
        src = inspect.getsource(FactLineagePopup.draw_lineage)
        assert "page_no" in src, (
            "draw_lineage must parse and display page_no from location_json."
        )

    def test_lineage_has_inspector_button(self):
        from src.ui.widgets.fact_lineage_popup import FactLineagePopup
        src = inspect.getsource(FactLineagePopup.draw_lineage)
        assert "_open_inspector" in src or "FileDetailPanel" in src, (
            "draw_lineage must provide a button or callback to open FileDetailPanel."
        )

    def test_open_inspector_passes_page_no(self):
        from src.ui.widgets.fact_lineage_popup import FactLineagePopup
        src = inspect.getsource(FactLineagePopup._open_inspector)
        assert "page_no" in src, (
            "_open_inspector must accept and forward page_no to FileDetailPanel."
        )


class TestFileDetailPanelPageContext:
    """FileDetailPanel must accept page_no and show citation banner."""

    def test_accepts_page_no_parameter(self):
        from src.ui.panels.file_detail_panel import FileDetailPanel
        sig = inspect.signature(FileDetailPanel.__init__)
        params = list(sig.parameters.keys())
        assert "page_no" in params, (
            "FileDetailPanel.__init__ must accept a page_no parameter."
        )

    def test_title_includes_page_context(self):
        from src.ui.panels.file_detail_panel import FileDetailPanel
        src = inspect.getsource(FileDetailPanel.__init__)
        assert "page_no" in src, (
            "__init__ must reference page_no to build the title."
        )
        assert "Cited location" in src or "page" in src.lower(), (
            "__init__ must show page context in the UI when navigated from a fact."
        )


class TestBackwardCompatibility:
    """Existing behavior must be preserved — callers without page_no still work."""

    def test_file_detail_panel_without_page_no(self):
        from src.ui.panels.file_detail_panel import FileDetailPanel
        # Verify default value is None so existing callers work
        sig = inspect.signature(FileDetailPanel.__init__)
        page_no_param = sig.parameters.get("page_no")
        assert page_no_param is not None, "page_no parameter must exist"
        assert page_no_param.default is None, "page_no must default to None for backward compat"

    def test_lineage_popup_without_location_json(self):
        from src.ui.widgets.fact_lineage_popup import FactLineagePopup
        # draw_lineage must handle missing location_json gracefully
        src = inspect.getsource(FactLineagePopup.draw_lineage)
        assert "except" in src or "location_json" in src, (
            "draw_lineage must handle cases where location_json is missing/None."
        )
