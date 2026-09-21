# -*- coding: utf-8 -*-
"""
test_pdf_block_page_attribution.py — P1: Verify doc_blocks page_index accuracy.

Proves that _find_page_for_text correctly attributes blocks to pages:
  1. Known block text maps to the expected page
  2. Repeated header/footer text is attributed to the first page (correct)
  3. No block is misattributed to a page where its text does not appear
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import pytest

from src.engine.extractors.pdf_extractor import UniversalPdfExtractor

CORPUS_DIR = Path(__file__).resolve().parents[2] / "_LOCAL_TEST_CORPUS" / "GOLD_BENCHMARK_V1"


def _corpus() -> Path:
    if not CORPUS_DIR.is_dir():
        pytest.skip(f"Gold corpus not found: {CORPUS_DIR}")
    return CORPUS_DIR


def _extract_blocks(pdf_file: Path) -> tuple:
    """Extract blocks and page_texts from a PDF using the production extractor."""
    extractor = UniversalPdfExtractor()
    result = extractor.extract(str(pdf_file))
    if not result.success:
        pytest.skip(f"PDF extraction failed: {result.diagnostics}")

    # Rebuild page_texts from pdf_page records (same text the extractor used)
    page_texts: Dict[int, str] = {}
    for rec in result.records:
        if rec.get("type") == "pdf_page":
            page_no = rec["data"]["page_no"]
            page_texts[page_no - 1] = rec["data"]["text_content"]

    blocks_record = next((r for r in result.records if r.get("type") == "doc_blocks"), None)
    if not blocks_record:
        return [], page_texts

    blocks = blocks_record.get("data", {}).get("blocks", [])
    return blocks, page_texts


class TestPDFBlockPageAttribution:
    """Verify doc_blocks page_index is correctly attributed."""

    def test_no_block_misattributed_to_wrong_page(self):
        """Every block whose snippet is found on its claimed page is correctly placed.

        A misattribution would mean: block claims page N, but the block's first
        100 chars do NOT appear on page N's text. This would mean the heuristic
        sent the block to the wrong page.
        """
        corpus = _corpus()
        target = corpus / "GOLD_0123.pdf"
        if not target.exists():
            pytest.skip("GOLD_0123.pdf not found")

        blocks, page_texts = _extract_blocks(target)
        assert blocks, "No blocks extracted"
        assert page_texts, "No page texts"

        mismatches = []
        for b in blocks:
            snippet = b.get("text", "")[:100]
            if not snippet:
                continue
            claimed = b.get("page_index", 0)
            # Check: does the snippet appear on the claimed page?
            if claimed in page_texts and snippet in page_texts[claimed]:
                continue  # Correct attribution
            # Check: does it appear on SOME page?
            found_on = [p for p, pt in page_texts.items() if snippet in pt]
            if found_on:
                # Snippet exists but NOT on the claimed page → misattribution
                mismatches.append({
                    "block_id": b.get("block_id"),
                    "claimed": claimed,
                    "found_on": found_on,
                })
            # If not found on any page: OCR artifact, not a misattribution

        # No block should be on a page where its text does NOT appear
        assert not mismatches, (
            f"{len(mismatches)} blocks misattributed to wrong page. "
            f"First 5: {mismatches[:5]}"
        )

    def test_repeated_headers_attributed_to_first_page(self):
        """Blocks containing repeated header/footer text (e.g., 'Proprietary and
        Confidential', company address) are attributed to the first page where
        the text appears. This is correct behavior for repeated content.
        """
        corpus = _corpus()
        target = corpus / "GOLD_0123.pdf"
        if not target.exists():
            pytest.skip("GOLD_0123.pdf not found")

        blocks, page_texts = _extract_blocks(target)

        # Find blocks that are ambiguous (snippet on multiple pages)
        ambiguous = []
        for b in blocks:
            snippet = b.get("text", "")[:100]
            if not snippet:
                continue
            found_on = [p for p, pt in page_texts.items() if snippet in pt]
            if len(found_on) > 1:
                ambiguous.append({
                    "block_id": b.get("block_id"),
                    "claimed": b.get("page_index", 0),
                    "found_on": found_on,
                })

        # All ambiguous blocks should be attributed to the FIRST page found
        for a in ambiguous:
            expected = min(a["found_on"])
            assert a["claimed"] == expected, (
                f"Block {a['block_id']}: ambiguous snippet found on "
                f"{a['found_on']}, claimed p{a['claimed']}, expected p{expected}"
            )

    def test_known_page_text_maps_to_correct_page(self):
        """Create a controlled multi-page PDF where specific text is on a known
        page, and verify the block's page_index matches.
        """
        import tempfile
        from pypdf import PdfWriter

        # Build a 3-page PDF with distinct text per page
        writer = PdfWriter()
        # Page 0: distinctive text
        writer.add_blank_page(width=612, height=792)
        writer.add_blank_page(width=612, height=792)
        writer.add_blank_page(width=612, height=792)

        # We need to add text. pypdf can't easily add text to blank pages,
        # so use fitz instead.
        import fitz
        import tempfile

        doc = fitz.open()
        for i in range(3):
            page = doc.new_page(width=612, height=792)
            text = f"UNIQUE_PAGE_MARKER_{i}_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
            page.insert_text(fitz.Point(72, 100), text, fontsize=12)
        for i in range(3):
            page = doc[i]
            page.insert_text(fitz.Point(72, 30), "REPEATED_HEADER_FOR_TESTING", fontsize=10)

        tmp_fd, tmp_path_str = tempfile.mkstemp(suffix=".pdf")
        import os
        os.close(tmp_fd)
        tmp_path = Path(tmp_path_str)
        doc.save(str(tmp_path))
        doc.close()

        try:
            extractor = UniversalPdfExtractor()
            result = extractor.extract(str(tmp_path))
            assert result.success, f"Extraction failed: {result.diagnostics}"

            blocks_record = next((r for r in result.records if r.get("type") == "doc_blocks"), None)
            if not blocks_record:
                pytest.skip("No blocks extracted from test PDF")

            blocks = blocks_record["data"].get("blocks", [])
            page_texts: Dict[int, str] = {}
            for rec in result.records:
                if rec.get("type") == "pdf_page":
                    page_no = rec["data"]["page_no"]
                    page_texts[page_no - 1] = rec["data"]["text_content"]

            if not blocks or not page_texts:
                pytest.skip("No blocks or page texts")

            # Verify each block's page_index is correct
            for b in blocks:
                snippet = b.get("text", "")[:100]
                if not snippet:
                    continue
                claimed = b.get("page_index", 0)
                found_on = [p for p, pt in page_texts.items() if snippet in pt]
                if found_on:
                    assert claimed in found_on, (
                        f"Block '{snippet[:40]}...' claimed p{claimed} "
                        f"but only found on {found_on}"
                    )
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_ocr_garbled_blocks_default_to_page_zero(self):
        """Blocks with OCR-garbled text that cannot be matched to any page
        default to page 0. This is a known limitation, not a bug.
        """
        corpus = _corpus()
        target = corpus / "GOLD_0123.pdf"
        if not target.exists():
            pytest.skip("GOLD_0123.pdf not found")

        blocks, page_texts = _extract_blocks(target)
        if not blocks:
            pytest.skip("No blocks")

        # Count blocks not found on any page
        not_found = 0
        for b in blocks:
            snippet = b.get("text", "")[:100]
            if not snippet:
                continue
            if not any(snippet in pt for pt in page_texts.values()):
                not_found += 1
                # These should default to page 0
                assert b.get("page_index", 0) == 0, (
                    f"Unfindable block {b.get('block_id')} has page_index="
                    f"{b.get('page_index')}, expected 0 (default)"
                )

        # The ratio of not-found blocks should be documented
        # (OCR artifacts in GOLD_0123.pdf: ~29/221 ≈ 13%)
        ratio = not_found / len(blocks) if blocks else 0
        print(f"  Not-found blocks: {not_found}/{len(blocks)} ({ratio:.1%})")
        # No assertion on the ratio — it's a measurement, not a threshold.
        # The key assertion is that unfindable blocks default to page 0.
