# -*- coding: utf-8 -*-
"""
Focus regression tests for colleague-readiness gate — Iteration 01.

Validates fixes for four UX blockers:
  B1 — Import wizard browse button label is generic ("Browse Documents...")
  B2 — Non-Excel file display label is neutral ("Ready for ingestion:")
  B3 — Sync Project scan covers all trusted extractor extensions
  B4 — Chat page shows processing indicator during query execution
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pytest


SRC_ROOT = Path(__file__).resolve().parent.parent.parent / "src"
WIZARD_PATH = SRC_ROOT / "ui" / "widgets" / "smart_import_wizard.py"
MAIN_WIN_PATH = SRC_ROOT / "ui" / "main_window.py"
CHAT_PATH = SRC_ROOT / "ui" / "pages" / "chat_page.py"
INGEST_PATH = SRC_ROOT / "application" / "jobs" / "ingest_file_job.py"


# ── B1: Import wizard browse button ──────────────────────────────────────


class TestB1_BrowseLabel:
    """The import wizard must not say 'Excel' in the browse button."""

    def test_browse_button_does_not_mention_excel(self):
        src = WIZARD_PATH.read_text(encoding="utf-8")
        btn_match = re.search(
            r'self\.btn_browse\s*=\s*ctk\.CTkButton\(.*?text\s*=\s*"([^"]+)"',
            src,
            re.DOTALL,
        )
        assert btn_match, "Could not find self.btn_browse constructor in smart_import_wizard.py"
        label = btn_match.group(1)
        assert "Excel" not in label, (
            f"Browse button label must not reference 'Excel': got '{label}'. "
            "Use a generic label such as 'Browse Documents...'."
        )

    def test_browse_button_label_is_present(self):
        src = WIZARD_PATH.read_text(encoding="utf-8")
        btn_match = re.search(r'self\.btn_browse\s*=\s*ctk\.CTkButton\(', src)
        assert btn_match, "self.btn_browse must exist in SmartImportWizard.__init__"
        after = src[btn_match.end():]
        text_match = re.search(r'text\s*=\s*"([^"]+)"', after)
        assert text_match, "browse button must have a text= label parameter"
        assert len(text_match.group(1)) > 0, "browse button text must not be empty"


# ── B2: Non-Excel display label ──────────────────────────────────────────


class TestB2_DisplayLabel:
    """Non-Excel files must show a neutral label, not 'Engineering Standard'."""

    def test_no_engineering_standard_in_non_excel_display(self):
        src = WIZARD_PATH.read_text(encoding="utf-8")
        lines = src.splitlines()
        in_browse_file = False
        for i, line in enumerate(lines):
            if "def browse_file" in line:
                in_browse_file = True
            if in_browse_file and "Engineering Standard" in line:
                pytest.fail(
                    f"Line {i+1}: non-Excel display must not say 'Engineering Standard'. "
                    f"Found: {line.strip()!r}"
                )

    def test_ready_for_ingestion_label_exists(self):
        src = WIZARD_PATH.read_text(encoding="utf-8")
        assert "Ready for ingestion" in src, (
            "smart_import_wizard.py must contain 'Ready for ingestion' "
            "for the non-Excel file display message."
        )


# ── B3: Sync Project extension coverage ──────────────────────────────────


def _get_extractor_map_extensions():
    src = INGEST_PATH.read_text(encoding="utf-8")
    m = re.search(r"extractor_map\s*=\s*\{([^}]+)\}", src, re.DOTALL)
    assert m, "extractor_map not found in ingest_file_job.py"
    map_text = m.group(1)
    return [f".{ext}" for ext in re.findall(r'"\.(\w+)"\s*:', map_text)]


def _get_sync_scan_extensions():
    src = MAIN_WIN_PATH.read_text(encoding="utf-8")
    m = re.search(r'ext\s+in\s*\[([^\]]+)\]', src)
    assert m, "Sync scan list not found in main_window.py"
    list_text = m.group(1)
    extensions = re.findall(r'"(\.\w+)"', list_text)
    return sorted(set(e.lower() for e in extensions))


class TestB3_SyncScanCoverage:
    """Sync Project scan must include every trusted extractor extension."""

    def test_all_trusted_extensions_are_scanned(self):
        missing = []
        for dot_ext in _get_extractor_map_extensions():
            if dot_ext not in _get_sync_scan_extensions():
                missing.append(dot_ext)
        assert not missing, (
            f"The following trusted extractor extensions are missing from the "
            f"Sync Project scan list: {missing}. "
            f"Sync Project must discover every supported format the user drops "
            f"into a project folder."
        )

    def test_staging_extensions_are_not_scanned(self):
        scan = set(_get_sync_scan_extensions())
        staging_dots = {".dgn", ".xlsm"}
        # .xlsm is a trusted extractor (maps to "excel"), so it MUST be scanned
        # .dgn is staging-only and must NOT be scanned
        overlap = scan & staging_dots
        # Allow .xlsm since it's a trusted extension (maps to excel extractor)
        assert overlap <= {".xlsm"}, (
            f"Sync Project scan must not include staging-only extensions: {overlap}"
        )

    def test_sync_scan_is_nonempty(self):
        scan = _get_sync_scan_extensions()
        assert len(scan) > 10, (
            f"Sync scan has only {len(scan)} extensions — "
            f"expected at least 12 (the prior baseline)."
        )

    def test_sync_scan_matches_extractor_map_minus_staging(self):
        scan = set(_get_sync_scan_extensions())
        trusted = set(_get_extractor_map_extensions())
        # Staging extractors (.dgn) should NOT appear in either sync or trusted
        # But .xlsm IS in extractor_map (maps to "excel") so it should be in scan
        missing_from_scan = trusted - scan
        # All missing must be staging-only
        staging_set = {".dgn"}
        for ext in missing_from_scan:
            assert ext in staging_set, (
                f"Trusted extension {ext} is missing from the Sync Project scan. "
                f"Only staging-only extensions (e.g. {staging_set}) may be excluded."
            )


# ── B4: Chat processing indicator ────────────────────────────────────────


class TestB4_ChatProcessingIndicator:
    """Chat page must expose a processing label during query execution."""

    def test_processing_label_widget_exists(self):
        src = CHAT_PATH.read_text(encoding="utf-8")
        assert "lbl_processing" in src, (
            "chat_page.py must define a lbl_processing widget for the "
            "processing indicator."
        )

    def test_set_processing_method_exists(self):
        src = CHAT_PATH.read_text(encoding="utf-8")
        assert "_set_processing" in src, (
            "chat_page.py must define a _set_processing method on ChatPage."
        )

    def test_processing_shown_on_send(self):
        src = CHAT_PATH.read_text(encoding="utf-8")
        send_section = re.search(
            r"def send_message\(.*?\n(?=\n    def |\nclass |\Z)",
            src,
            re.DOTALL,
        )
        assert send_section, "Could not find send_message method body"
        body = send_section.group(0)
        assert "_set_processing(True)" in body or "_set_processing( active=True" in body.replace(" ", ""), (
            "send_message must call _set_processing(True) after deleting "
            "the entry and clearing attachments."
        )

    def test_processing_hidden_on_deliver(self):
        src = CHAT_PATH.read_text(encoding="utf-8")
        deliver_match = re.search(r"def _deliver\(\):\s*\n(?:        .*\n)*", src)
        assert deliver_match, "Could not find _deliver inner function"
        deliver_body = deliver_match.group(0)
        assert "_set_processing(False)" in deliver_body, (
            "_deliver must call _set_processing(False) before adding the Serapeum response."
        )

    def test_processing_hidden_on_error(self):
        src = CHAT_PATH.read_text(encoding="utf-8")
        error_match = re.search(r"def _deliver_chat_error\(.*?\n(?:        .*\n)*", src)
        assert error_match, "Could not find _deliver_chat_error method"
        err_body = error_match.group(0)
        assert "_set_processing(False)" in err_body, (
            "_deliver_chat_error must call _set_processing(False)."
        )

    def test_processing_hidden_on_no_orchestrator(self):
        src = CHAT_PATH.read_text(encoding="utf-8")
        else_branch = re.search(
            r"else:\s*\n\s+self\._set_processing\(False\)\s*\n\s+self\.add_message",
            src,
        )
        assert else_branch, (
            "When no orchestrator is available, send_message must call "
            "_set_processing(False) before adding the system message."
        )

    def test_processing_hidden_on_reset(self):
        src = CHAT_PATH.read_text(encoding="utf-8")
        reset_body = re.search(
            r"def reset_view\(.*?\n(?:        .*\n)*?(?=\n    def |\nclass |\Z)",
            src,
            re.DOTALL,
        )
        assert reset_body, "Could not find reset_view method body"
        assert "_set_processing(False)" in reset_body.group(0), (
            "reset_view must call _set_processing(False) when clearing the chat."
        )
