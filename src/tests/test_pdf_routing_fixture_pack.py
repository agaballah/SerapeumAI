# -*- coding: utf-8 -*-
import json
from types import SimpleNamespace

import pytest

import src.engine.extractors.pdf_extractor as pdf_module
from src.engine.extractors.pdf_extractor import UniversalPdfExtractor


class FakePypdfPage:
    def __init__(self, text="", image_count=0):
        self._text = text
        self.images = [object() for _ in range(image_count)]

    def extract_text(self):
        return self._text


class FakeReader:
    def __init__(self, pages):
        self.pages = pages
        self.metadata = {
            "/Title": "Routing Fixture PDF",
            "/Producer": "Routing Test Producer",
        }


class FakeFitzDoc:
    def __init__(self, page_count):
        self.pages = [SimpleNamespace(page_index=i) for i in range(page_count)]
        self.metadata = {
            "title": "Routing Fixture PDF",
            "producer": "Routing Test Producer",
        }

    def __getitem__(self, index):
        return self.pages[index]


def _install_fake_pdf(monkeypatch):
    native_vector_text = "VECTOR_NATIVE_TEXT " * 30  # >300 chars, no images => vector
    native_combined_text = "COMBINED_NATIVE_TEXT " * 8  # 100-300 chars + image => combined

    fake_pages = [
        FakePypdfPage("", 0),                    # empty
        FakePypdfPage(native_vector_text, 0),    # vector
        FakePypdfPage("", 1),                    # scanned
        FakePypdfPage(native_combined_text, 1),  # combined
    ]

    fake_reader = FakeReader(fake_pages)
    fake_doc = FakeFitzDoc(page_count=len(fake_pages))

    monkeypatch.setattr(pdf_module, "PdfReader", lambda file_path: fake_reader)
    monkeypatch.setattr(pdf_module.fitz, "open", lambda file_path: fake_doc)

    ocr_calls = []

    def fake_ocr(self, fitz_page):
        ocr_calls.append(fitz_page.page_index)
        return f"OCR_TEXT_PAGE_{fitz_page.page_index + 1}"

    def fail_vlm(self, fitz_page, context=None):
        raise AssertionError("VLM routing must remain disabled for current PDF extractor routing.")

    monkeypatch.setattr(UniversalPdfExtractor, "_extract_ocr", fake_ocr)
    monkeypatch.setattr(UniversalPdfExtractor, "_extract_vlm", fail_vlm)

    return {
        "fake_reader": fake_reader,
        "fake_doc": fake_doc,
        "ocr_calls": ocr_calls,
        "native_vector_text": native_vector_text.strip(),
        "native_combined_text": native_combined_text.strip(),
    }


def _page_records(result):
    return [record for record in result.records if record["type"] == "pdf_page"]


def _page_metadata(page_record):
    return json.loads(page_record["data"]["metadata"])


def test_pdf_routing_covers_empty_vector_scanned_and_combined_pages(monkeypatch):
    fixture = _install_fake_pdf(monkeypatch)

    result = UniversalPdfExtractor().extract("routing-fixture.pdf")

    assert result.success is True
    pages = _page_records(result)
    assert len(pages) == 4

    per_page = {
        page["data"]["page_no"]: {
            "text": page["data"]["text_content"],
            "metadata": _page_metadata(page),
            "provenance": page["provenance"],
        }
        for page in pages
    }

    assert per_page[1]["metadata"]["composition"] == "empty"
    assert per_page[1]["metadata"]["method"] == "skipped_empty"
    assert per_page[1]["text"] == ""

    assert per_page[2]["metadata"]["composition"] == "vector"
    assert per_page[2]["metadata"]["method"] == "pypdf_vector"
    assert per_page[2]["text"] == fixture["native_vector_text"]

    assert per_page[3]["metadata"]["composition"] == "scanned"
    assert per_page[3]["metadata"]["method"] == "pytesseract_ocr"
    assert per_page[3]["text"] == "OCR_TEXT_PAGE_3"

    assert per_page[4]["metadata"]["composition"] == "combined"
    assert per_page[4]["metadata"]["method"] == "hybrid_mixed"
    assert fixture["native_combined_text"] in per_page[4]["text"]
    assert "OCR_TEXT_PAGE_4" in per_page[4]["text"]
    assert "--OCR--" in per_page[4]["text"]


def test_pdf_routing_ocr_boundaries_and_vlm_non_use_are_locked(monkeypatch):
    fixture = _install_fake_pdf(monkeypatch)

    result = UniversalPdfExtractor().extract("routing-fixture.pdf")

    assert result.success is True
    # OCR should run only for scanned and combined pages: zero-based page indexes 2 and 3.
    assert fixture["ocr_calls"] == [2, 3]


def test_pdf_routing_page_metadata_and_document_counts_agree(monkeypatch):
    _install_fake_pdf(monkeypatch)

    result = UniversalPdfExtractor().extract("routing-fixture.pdf")

    assert result.success is True
    pages = _page_records(result)
    compositions = [_page_metadata(page)["composition"] for page in pages]

    assert compositions == ["empty", "vector", "scanned", "combined"]
    assert result.metadata["page_composition_counts"] == {
        "empty": 1,
        "vector": 1,
        "scanned": 1,
        "combined": 1,
    }
    assert sum(result.metadata["page_composition_counts"].values()) == result.metadata["pdf_page_count"] == 4

    for page in pages:
        metadata = _page_metadata(page)
        assert page["provenance"]["composition"] == metadata["composition"]
        assert page["provenance"]["method"] == metadata["method"]
        assert metadata["is_visual"] is (metadata["composition"] in ("scanned", "combined"))


def test_pdf_routing_preserves_pdf_metadata_contract(monkeypatch):
    _install_fake_pdf(monkeypatch)

    result = UniversalPdfExtractor().extract("routing-fixture.pdf")

    assert result.success is True
    assert result.metadata["pdf_title"] == "Routing Fixture PDF"
    assert result.metadata["pdf_producer"] == "Routing Test Producer"
    assert result.metadata["pdf_page_count"] == 4
    assert "pdf_raw_metadata" in result.metadata
