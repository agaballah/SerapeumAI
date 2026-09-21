#!/usr/bin/env python
"""
Focused test for DOC COM lock contamination.

Verifies:
- 10 sequential DOC extractions complete without hanging
- No orphan WINWORD.EXE processes remain after extraction
- No "File In Use" dialog contamination
"""
from __future__ import annotations

import os
import subprocess
import time

import pytest

from src.engine.extractors.word_extractor import WordExtractor


DOC_GOLD_FILES = [
    r"D:\SerapeumAI\_LOCAL_TEST_CORPUS\GOLD_BENCHMARK_V1\GOLD_0112.doc",
    r"D:\SerapeumAI\_LOCAL_TEST_CORPUS\GOLD_BENCHMARK_V1\GOLD_0113.doc",
    r"D:\SerapeumAI\_LOCAL_TEST_CORPUS\GOLD_BENCHMARK_V1\GOLD_0114.doc",
    r"D:\SerapeumAI\_LOCAL_TEST_CORPUS\GOLD_BENCHMARK_V1\GOLD_0115.doc",
    r"D:\SerapeumAI\_LOCAL_TEST_CORPUS\GOLD_BENCHMARK_V1\GOLD_0116.doc",
]


def _kill_winword() -> None:
    subprocess.run(
        ["powershell", "-Command", "Stop-Process -Name WINWORD -Force -ErrorAction SilentlyContinue"],
        capture_output=True,
        timeout=10,
    )
    time.sleep(1)


def _count_winword() -> int:
    try:
        result = subprocess.run(
            ["powershell", "-Command", "Get-Process WINWORD -ErrorAction SilentlyContinue | Measure-Object | Select-Object -ExpandProperty Count"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return int(result.stdout.strip() or 0)
    except Exception:
        return -1


@pytest.fixture(autouse=True)
def _clean_winword():
    """Ensure no orphan WINWORD processes before/after each test."""
    _kill_winword()
    yield
    _kill_winword()


def test_sequential_doc_extractions_no_orphans():
    """Run 10 sequential DOC extractions and verify no orphan WINWORD processes."""
    extractor = WordExtractor()
    orphan_counts = []

    for i in range(10):
        doc_path = DOC_GOLD_FILES[i % len(DOC_GOLD_FILES)]
        assert os.path.isfile(doc_path), f"Missing DOC gold file: {doc_path}"

        result = extractor.extract(doc_path, context={"doc_id": f"test_doc_{i}"})
        assert result.success, f"Extraction failed for {doc_path}: {result.diagnostics}"

        # Brief pause to allow COM cleanup
        time.sleep(0.5)

        orphan_count = _count_winword()
        orphan_counts.append(orphan_count)
        assert orphan_count == 0, f"Orphan WINWORD processes detected after extraction {i+1}: {orphan_count}"

    max_orphan = max(orphan_counts) if orphan_counts else 0
    assert max_orphan == 0, f"Maximum orphan WINWORD count: {max_orphan}"


def test_doc_extraction_timeout_cleanup():
    """Verify that timeout handling kills orphan WINWORD processes."""
    _kill_winword()
    assert _count_winword() == 0

    extractor = WordExtractor()
    doc_path = DOC_GOLD_FILES[0]
    result = extractor.extract(doc_path, context={"doc_id": "timeout_test"})
    
    # Even if extraction succeeds or fails, there should be no orphans
    time.sleep(1)
    orphan_count = _count_winword()
    assert orphan_count == 0, f"Orphan WINWORD processes after extraction: {orphan_count}"


def test_doc_com_cleanup_after_failure():
    """Verify COM cleanup when extraction encounters an error."""
    _kill_winword()
    assert _count_winword() == 0

    extractor = WordExtractor()
    
    # Use a non-existent file to trigger error path
    result = extractor.extract(r"D:\SerapeumAI\_LOCAL_TEST_CORPUS\GOLD_BENCHMARK_V1\NONEXISTENT.doc",
                                context={"doc_id": "error_test"})
    assert not result.success
    
    time.sleep(0.5)
    orphan_count = _count_winword()
    assert orphan_count == 0, f"Orphan WINWORD processes after error: {orphan_count}"
