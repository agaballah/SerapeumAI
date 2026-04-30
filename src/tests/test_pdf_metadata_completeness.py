# -*- coding: utf-8 -*-
from pathlib import Path

from pypdf import PdfReader, PdfWriter

from src.engine.extractors.pdf_extractor import UniversalPdfExtractor


def _write_metadata_pdf(path: Path) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.add_metadata(
        {
            "/Title": "Engineering Metadata Test",
            "/Author": "Serapeum Test Author",
            "/Subject": "PDF metadata contract",
            "/Creator": "Serapeum Test Creator",
            "/Producer": "Serapeum Test Producer",
            "/CreationDate": "D:20260102030405+03'00'",
            "/ModDate": "D:20260103040506+03'00'",
        }
    )
    with path.open("wb") as fh:
        writer.write(fh)


def test_pdf_extractor_metadata_includes_normalized_document_info(tmp_path):
    pdf_path = tmp_path / "metadata-contract.pdf"
    _write_metadata_pdf(pdf_path)

    result = UniversalPdfExtractor().extract(str(pdf_path))

    assert result.success is True
    metadata = result.metadata

    assert metadata["pdf_title"] == "Engineering Metadata Test"
    assert metadata["pdf_author"] == "Serapeum Test Author"
    assert metadata["pdf_subject"] == "PDF metadata contract"
    assert metadata["pdf_creator"] == "Serapeum Test Creator"
    assert metadata["pdf_producer"] == "Serapeum Test Producer"
    assert metadata["pdf_creation_date"] == "D:20260102030405+03'00'"
    assert metadata["pdf_modified_date"] == "D:20260103040506+03'00'"
    assert metadata["pdf_page_count"] == 1


def test_pdf_extractor_preserves_raw_metadata_safely(tmp_path):
    pdf_path = tmp_path / "raw-metadata.pdf"
    _write_metadata_pdf(pdf_path)

    metadata = UniversalPdfExtractor().extract(str(pdf_path)).metadata
    raw = metadata["pdf_raw_metadata"]

    assert set(raw) >= {"pypdf", "pymupdf"}
    assert raw["pypdf"]["/Title"] == "Engineering Metadata Test"
    assert raw["pypdf"]["/Creator"] == "Serapeum Test Creator"
    assert isinstance(raw["pymupdf"], dict)


def test_pdf_extractor_summarizes_page_composition_counts(tmp_path):
    pdf_path = tmp_path / "blank-page.pdf"
    _write_metadata_pdf(pdf_path)

    result = UniversalPdfExtractor().extract(str(pdf_path))
    counts = result.metadata["page_composition_counts"]

    assert result.success is True
    assert counts["empty"] == 1
    assert counts["vector"] == 0
    assert counts["scanned"] == 0
    assert counts["combined"] == 0
    assert sum(counts.values()) == result.metadata["pdf_page_count"]


def test_pdf_extractor_keeps_existing_record_shapes(tmp_path):
    pdf_path = tmp_path / "record-shapes.pdf"
    _write_metadata_pdf(pdf_path)

    result = UniversalPdfExtractor().extract(str(pdf_path))
    record_types = [record["type"] for record in result.records]

    assert "pdf_page" in record_types
    assert "doc_classification" in record_types

    page_record = next(record for record in result.records if record["type"] == "pdf_page")
    assert set(page_record["data"]) >= {"page_no", "text_content", "metadata"}
    assert set(page_record["provenance"]) >= {"page", "method", "composition"}


def test_pdf_metadata_patch_does_not_enable_vlm_routing():
    source = Path("src/engine/extractors/pdf_extractor.py").read_text(encoding="utf-8-sig")

    assert "_extract_vlm(" in source
    assert "self._extract_vlm(" not in source
