# -*- coding: utf-8 -*-
"""
Focused regression tests for A15 — honest dependency failure warnings.

Validates that the application does not silently present dependency-blocked
files as successfully ingested, and that both the Documents page and File
Inspector surface clear per-file dependency warnings.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


SRC_ROOT = Path(__file__).resolve().parent.parent.parent / "src"
sys.path.insert(0, str(SRC_ROOT))


class TestDependencyCheckerExtensionMap:
    """DependencyHealthChecker.get_dependency_info_for_extension must cover known critical deps."""

    def test_ifc_extension_maps_to_ifcopenshell_when_missing(self):
        from src.infra.dependency_status import DependencyHealthChecker
        with patch.object(DependencyHealthChecker, 'check_all') as mock_check:
            mock_dep = MagicMock()
            mock_dep.name = "ifcopenshell"
            mock_dep.status = "missing"
            mock_dep.required_for = [".ifc"]
            mock_dep.install_command = "pip install ifcopenshell"
            mock_dep.severity = "critical"
            mock_mpxj = MagicMock()
            mock_mpxj.name = "mpxj"
            mock_mpxj.status = "installed"
            mock_mpxj.required_for = [".mpp"]
            mock_mpxj.install_command = "pip install mpxj jpype1"
            mock_mpxj.severity = "critical"
            mock_xlrd = MagicMock()
            mock_xlrd.name = "xlrd"
            mock_xlrd.status = "installed"
            mock_xlrd.required_for = [".xls"]
            mock_xlrd.install_command = "pip install xlrd"
            mock_xlrd.severity = "critical"
            mock_check.return_value = [mock_dep, mock_mpxj, mock_xlrd]
            info = DependencyHealthChecker.get_dependency_info_for_extension(".ifc")
            assert info is not None
            assert info["dependency"] == "ifcopenshell"
            assert info["severity"] == "critical"

    def test_installed_dependency_returns_none(self):
        from src.infra.dependency_status import DependencyHealthChecker
        with patch.object(DependencyHealthChecker, 'check_all') as mock_check:
            mock_check.return_value = [
                MagicMock(name="ifcopenshell", status="installed", required_for=[".ifc"],
                          install_command="", severity="critical", version="0.8.5"),
            ]
            info = DependencyHealthChecker.get_dependency_info_for_extension(".ifc")
            assert info is None

    def test_unrelated_extension_returns_none(self):
        from src.infra.dependency_status import DependencyHealthChecker
        with patch.object(DependencyHealthChecker, 'check_all') as mock_check:
            mock_check.return_value = []
            info = DependencyHealthChecker.get_dependency_info_for_extension(".pdf")
            assert info is None

    def test_empty_extension_returns_none(self):
        from src.infra.dependency_status import DependencyHealthChecker
        info = DependencyHealthChecker.get_dependency_info_for_extension("")
        assert info is None

    def test_case_insensitive_extension_match(self):
        from src.infra.dependency_status import DependencyHealthChecker
        with patch.object(DependencyHealthChecker, 'check_all') as mock_check:
            mock_dep = MagicMock()
            mock_dep.name = "ifcopenshell"
            mock_dep.status = "missing"
            mock_dep.required_for = [".ifc"]
            mock_dep.install_command = "pip install ifcopenshell"
            mock_dep.severity = "critical"
            mock_check.return_value = [mock_dep]
            # Uppercase extension should still match
            info = DependencyHealthChecker.get_dependency_info_for_extension(".IFC")
            assert info is not None
            assert info["dependency"] == "ifcopenshell"


class TestDocumentsPageStatusLabels:
    """Documents page must show blocked status for files whose dependency is missing."""

    def test_blocked_file_shows_dependency_label(self):
        from src.ui.pages.documents_page import DocumentsPage

        # Verify the status logic is present in _build_document_rows
        import inspect
        src = inspect.getsource(DocumentsPage._build_document_rows)
        assert "get_dependency_info_for_extension" in src, (
            "_build_document_rows must call DependencyHealthChecker "
            "to classify file status."
        )
        assert "Blocked" in src or "blocked" in src, (
            "_build_document_rows must display a blocked-status label "
            "for files with missing dependencies."
        )
        assert "Ingested" in src, (
            "_build_document_rows must retain the 'Ingested' label for "
            "files without missing dependencies."
        )

    def test_sql_query_includes_file_ext(self):
        """The file list query must fetch file_ext so status can be classified."""
        import inspect
        from src.ui.pages.documents_page import DocumentsPage
        src = inspect.getsource(DocumentsPage._query_files)
        assert "file_ext" in src, (
            "_query_files must SELECT file_ext from file_versions "
            "so the status label can be computed per file."
        )


class TestFileInspectorDependencyWarning:
    """File Inspector consolidated review must surface dependency warnings."""

    def test_consolidated_review_contains_dependency_warning(self):
        from src.application.services.file_inspector_presentation import _build_consolidated_review

        with patch("src.application.services.file_inspector_presentation.DependencyHealthChecker") as MockDHC:
            MockDHC.get_dependency_info_for_extension.return_value = {
                "dependency": "ifcopenshell",
                "install_command": "pip install ifcopenshell",
                "severity": "critical",
            }

            result = _build_consolidated_review(
                document={},
                file_version={"file_ext": ".ifc", "imported_at": 0},
                pages=[],
                blocks=[],
                runs=[],
                source_path="/project/test.ifc",
            )

            assert "ifcopenshell" in result, (
                "Consolidated review must mention the specific missing dependency."
            )
            assert "blocked" in result.lower() or "Blocked" in result, (
                "Consolidated review must clearly state extraction is blocked."
            )

    def test_consolidated_review_no_warning_when_dep_present(self):
        from src.application.services.file_inspector_presentation import _build_consolidated_review

        with patch("src.application.services.file_inspector_presentation.DependencyHealthChecker") as MockDHC:
            MockDHC.get_dependency_info_for_extension.return_value = None

            result = _build_consolidated_review(
                document={},
                file_version={"file_ext": ".pdf", "imported_at": 0},
                pages=[],
                blocks=[],
                runs=[],
                source_path="/project/test.pdf",
            )

            assert "blocked" not in result.lower(), (
                "Consolidated review must not show a blocked warning when dependency is present."
            )

    def test_consolidated_review_shows_extraction_failure_status(self):
        """When extraction failed (not dependency-blocked), show FAILED status."""
        from src.application.services.file_inspector_presentation import _build_consolidated_review

        with patch("src.application.services.file_inspector_presentation.DependencyHealthChecker") as MockDHC:
            MockDHC.get_dependency_info_for_extension.return_value = None

            runs = [{"status": "FAILED", "extractor_id": "pdf_extractor"}]
            result = _build_consolidated_review(
                document={},
                file_version={"file_ext": ".pdf", "imported_at": 0},
                pages=[],
                blocks=[],
                runs=runs,
                source_path="/project/broken.pdf",
            )

            assert "FAILED" in result, (
                "Consolidated review must show FAILED status for failed extractions."
            )

    def test_consolidated_review_shows_pending_when_no_runs(self):
        """When no extraction has run yet, show pending status."""
        from src.application.services.file_inspector_presentation import _build_consolidated_review

        with patch("src.application.services.file_inspector_presentation.DependencyHealthChecker") as MockDHC:
            MockDHC.get_dependency_info_for_extension.return_value = None

            result = _build_consolidated_review(
                document={},
                file_version={"file_ext": ".txt", "imported_at": 0},
                pages=[],
                blocks=[],
                runs=[],
                source_path="/project/pending.txt",
            )

            assert "pending" in result.lower(), (
                "Consolidated review must indicate pending extraction when no runs exist."
            )
