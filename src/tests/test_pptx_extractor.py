# -*- coding: utf-8 -*-
"""
Focused PPTX extraction tests.

Validates the ExtractionResult contract for PPTXExtractor,
including Docling-backed extraction and graceful fallback.
"""
from __future__ import annotations

import os
import sys
from unittest.mock import patch

import pytest

from src.engine.extractors.pptx_extractor import PPTXExtractor
from src.engine.extractors.base import ExtractionResult


GOLD_PPTX_DIR = os.path.join("_LOCAL_TEST_CORPUS", "GOLD_BENCHMARK_V1")
GOLD_FILES = ["GOLD_0127.pptx", "GOLD_0128.pptx", "GOLD_0129.pptx"]


def _fixture_path(name: str) -> str:
    return os.path.join(GOLD_PPTX_DIR, name)


def _has_fixtures() -> bool:
    return all(os.path.isfile(_fixture_path(f)) for f in GOLD_FILES)


@pytest.fixture()
def extractor() -> PPTXExtractor:
    return PPTXExtractor()


class TestPPTXExtractorContract:
    """Verify the ExtractionResult contract is preserved."""

    @pytest.mark.skipif(not _has_fixtures(), reason="PPTX gold corpus not available")
    def test_extract_returns_extraction_result(self, extractor: PPTXExtractor):
        result = extractor.extract(_fixture_path("GOLD_0127.pptx"), context={"doc_id": "test"})
        assert isinstance(result, ExtractionResult)

    @pytest.mark.skipif(not _has_fixtures(), reason="PPTX gold corpus not available")
    def test_extract_succeeds_on_valid_pptx(self, extractor: PPTXExtractor):
        result = extractor.extract(_fixture_path("GOLD_0127.pptx"), context={"doc_id": "test"})
        assert result.success is True

    @pytest.mark.skipif(not _has_fixtures(), reason="PPTX gold corpus not available")
    def test_records_are_pdf_page_type(self, extractor: PPTXExtractor):
        result = extractor.extract(_fixture_path("GOLD_0127.pptx"), context={"doc_id": "test"})
        assert result.records
        for record in result.records:
            assert record["type"] == "pdf_page"

    @pytest.mark.skipif(not _has_fixtures(), reason="PPTX gold corpus not available")
    def test_records_have_required_fields(self, extractor: PPTXExtractor):
        result = extractor.extract(_fixture_path("GOLD_0127.pptx"), context={"doc_id": "test"})
        required = {"page_no", "text_content", "metadata"}
        for record in result.records:
            assert required.issubset(record["data"].keys())

    @pytest.mark.skipif(not _has_fixtures(), reason="PPTX gold corpus not available")
    def test_records_have_provenance(self, extractor: PPTXExtractor):
        result = extractor.extract(_fixture_path("GOLD_0127.pptx"), context={"doc_id": "test"})
        for record in result.records:
            prov = record["provenance"]
            assert "page" in prov
            assert "source" in prov
            assert prov["source"] == "pptx_extractor"

    @pytest.mark.skipif(not _has_fixtures(), reason="PPTX gold corpus not available")
    def test_metadata_shape(self, extractor: PPTXExtractor):
        result = extractor.extract(_fixture_path("GOLD_0127.pptx"), context={"doc_id": "test"})
        meta = result.metadata
        assert "page_count" in meta
        assert "char_count" in meta
        assert "doc_id" in meta
        assert "source_path" in meta
        assert "file_name" in meta
        assert "file_size" in meta
        assert meta["doc_id"] == "test"

    @pytest.mark.skipif(not _has_fixtures(), reason="PPTX gold corpus not available")
    def test_page_no_is_one_indexed(self, extractor: PPTXExtractor):
        result = extractor.extract(_fixture_path("GOLD_0127.pptx"), context={"doc_id": "test"})
        page_nos = [r["data"]["page_no"] for r in result.records]
        assert page_nos[0] == 1
        assert page_nos == sorted(page_nos)

    @pytest.mark.skipif(not _has_fixtures(), reason="PPTX gold corpus not available")
    def test_one_record_per_slide(self, extractor: PPTXExtractor):
        result = extractor.extract(_fixture_path("GOLD_0127.pptx"), context={"doc_id": "test"})
        assert len(result.records) == result.metadata["page_count"]


class TestPPTXMultiSlide:
    """Verify multi-slide handling across representative fixtures."""

    @pytest.mark.skipif(not _has_fixtures(), reason="PPTX gold corpus not available")
    @pytest.mark.parametrize("filename", GOLD_FILES)
    def test_each_fixture_produces_records(self, extractor: PPTXExtractor, filename: str):
        result = extractor.extract(_fixture_path(filename), context={"doc_id": "test"})
        assert result.success is True
        assert len(result.records) > 0
        assert result.metadata["page_count"] == len(result.records)

    @pytest.mark.skipif(not _has_fixtures(), reason="PPTX gold corpus not available")
    def test_different_fixtures_different_page_counts(self, extractor: PPTXExtractor):
        counts = {}
        for f in GOLD_FILES:
            r = extractor.extract(_fixture_path(f), context={"doc_id": "test"})
            counts[f] = r.metadata["page_count"]
        assert len(set(counts.values())) > 1


class TestPPTXFailurePaths:
    """Verify graceful failure behavior."""

    def test_missing_file_returns_failure(self, extractor: PPTXExtractor):
        result = extractor.extract("nonexistent_file.pptx", context={"doc_id": "test"})
        assert result.success is False
        assert result.diagnostics
        assert result.metadata["page_count"] == 0
        assert result.metadata["char_count"] == 0

    def test_failure_preserves_metadata_shape(self, extractor: PPTXExtractor):
        result = extractor.extract("nonexistent_file.pptx", context={"doc_id": "test"})
        assert result.metadata["doc_id"] == "test"
        assert "source_path" in result.metadata
        assert "file_name" in result.metadata
        assert "file_size" in result.metadata


class TestPPTXDoclingFallback:
    """Verify fallback to PPTProcessor when Docling is unavailable."""

    def test_fallback_when_docling_unavailable(self, extractor: PPTXExtractor):
        with patch.dict(sys.modules, {"docling": None, "docling.document_converter": None}):
            if os.path.isfile(_fixture_path("GOLD_0127.pptx")):
                result = extractor.extract(_fixture_path("GOLD_0127.pptx"), context={"doc_id": "test"})
                assert result.success is True
                assert len(result.records) > 0
                assert "PPTXExtractor processed" in result.diagnostics[0]
