# -*- coding: utf-8 -*-
from pathlib import Path

import pandas as pd

from src.application.jobs.extract_job import ExtractJob
from src.engine.extractors.dgn_extractor import DGNExtractor
from src.engine.extractors.pptx_extractor import PPTXExtractor
from src.engine.extractors.register_extractor import ExcelRegisterExtractor
from src.engine.extractors.word_extractor import WordExtractor
from src.infra.persistence.database_manager import DatabaseManager


def _write_file(path: Path, content: bytes = b"fixture") -> Path:
    path.write_bytes(content)
    return path


class FakeWordProcessor:
    def process(self, abs_path, rel_path, export_root):
        return {
            "text": "Word paragraph\n[Table]\nA | B",
            "pages": [
                {
                    "page_index": 0,
                    "py_text": "Word paragraph\n[Table]\nA | B",
                    "quality": "queued",
                }
            ],
            "meta": {"source": "fake-word-processor"},
        }


class FakePPTProcessor:
    def process(self, abs_path, rel_path, export_root):
        return {
            "text": "[Title] Slide 1\n[Body] Slide body\n[Speaker Notes] Notes",
            "pages": [
                {
                    "page_index": 0,
                    "py_text": "[Title] Slide 1\n[Body] Slide body\n[Speaker Notes] Notes",
                    "quality": "queued",
                }
            ],
            "meta": {"source": "fake-ppt-processor", "slides": 1},
        }


def _assert_no_typed_persistence_claim(result):
    combined = " ".join(
        [str(item) for item in result.diagnostics]
        + [str(result.metadata)]
        + [str(record) for record in result.records]
    ).lower()

    forbidden_claims = [
        "typed word persistence",
        "typed office persistence",
        "typed slide persistence",
        "typed cad persistence",
        "cad entity persistence",
        "geometry persistence",
        "cell/range persistence",
        "generic workbook persistence",
    ]

    for claim in forbidden_claims:
        assert claim not in combined


def test_word_extractor_current_contract_is_flattened_pdf_page_only(tmp_path, monkeypatch):
    import src.document_processing.word_processor as word_processor

    monkeypatch.setattr(word_processor, "WordProcessor", lambda: FakeWordProcessor())

    source = _write_file(tmp_path / "contract.docx")
    result = WordExtractor().extract(str(source), context={"doc_id": "doc_word"})

    assert WordExtractor().supported_extensions == [".doc", ".docx"]
    assert result.success is True
    assert {record["type"] for record in result.records} == {"pdf_page"}

    record = result.records[0]
    assert record["provenance"]["source"] == "word_extractor"
    assert record["data"]["page_no"] == 1
    assert "Word paragraph" in record["data"]["text_content"]
    assert "[Table]" in record["data"]["text_content"]
    assert record["data"]["metadata"] is None

    assert "WordExtractor processed 1 page(s)" in result.diagnostics
    _assert_no_typed_persistence_claim(result)


def test_pptx_extractor_current_contract_is_flattened_pdf_page_only(tmp_path, monkeypatch):
    import src.document_processing.ppt_processor as ppt_processor

    monkeypatch.setattr(ppt_processor, "PPTProcessor", lambda: FakePPTProcessor())

    source = _write_file(tmp_path / "deck.pptx")
    result = PPTXExtractor().extract(str(source), context={"doc_id": "doc_pptx"})

    assert PPTXExtractor().supported_extensions == [".pptx"]
    assert result.success is True
    assert {record["type"] for record in result.records} == {"pdf_page"}

    record = result.records[0]
    assert record["provenance"]["source"] == "pptx_extractor"
    assert record["data"]["page_no"] == 1
    assert "[Title] Slide 1" in record["data"]["text_content"]
    assert "[Speaker Notes] Notes" in record["data"]["text_content"]
    assert record["data"]["metadata"] is None

    assert "PPTXExtractor processed 1 slide(s)" in result.diagnostics
    _assert_no_typed_persistence_claim(result)


def test_dgn_extractor_current_contract_is_minimal_flattened_status_page_only(tmp_path, monkeypatch):
    import src.document_processing.dgn_processor as dgn_processor

    def fake_process(file_path, output_dir=None, *, extract_xrefs=True):
        return {
            "status": "no_oda",
            "file_path": file_path,
            "xrefs": ["xref-a.dgn", "xref-b.dgn"],
            "dxf_path": None,
            "text": "DGN Processing: no_oda",
            "meta": {"source": "fake-dgn-processor", "status": "no_oda"},
            "error": None,
        }

    monkeypatch.setattr(dgn_processor, "process", fake_process)

    source = _write_file(tmp_path / "drawing.dgn")
    result = DGNExtractor().extract(str(source), context={"doc_id": "doc_dgn"})

    assert DGNExtractor().supported_extensions == [".dgn"]
    assert result.success is True
    assert {record["type"] for record in result.records} == {"pdf_page"}

    record = result.records[0]
    assert record["provenance"]["source"] == "dgn_extractor"
    assert "Processing status: no_oda" in record["data"]["text_content"]
    assert "xref-a.dgn" in record["data"]["text_content"]

    assert result.metadata["dgn_status"] == "no_oda"
    assert result.metadata["xref_count"] == 2
    assert "DGNExtractor: status=no_oda, xrefs=2" in result.diagnostics
    _assert_no_typed_persistence_claim(result)


def test_excel_register_current_contract_is_register_rows_not_generic_workbook_cells(monkeypatch):
    def fake_read_excel(file_path, sheet_name=None, nrows=None, header=0, dtype=str):
        if sheet_name is None:
            return {"Register": pd.DataFrame({"Doc No": ["A-001"], "Status": ["Open"]})}
        if header is None:
            return pd.DataFrame([["Doc No", "Status"], ["A-001", "Open"]])
        return pd.DataFrame([{"Doc No": "A-001", "Status": "Open"}])

    import src.engine.extractors.register_extractor as register_module

    monkeypatch.setattr(register_module.pd, "read_excel", fake_read_excel)

    result = ExcelRegisterExtractor().extract("register.xlsx")

    assert ExcelRegisterExtractor().supported_extensions == [".xlsx", ".xls"]
    assert result.success is True
    assert {record["type"] for record in result.records} == {"register_row"}

    record = result.records[0]
    assert record["data"]["sheet_name"] == "Register"
    assert record["data"]["row_index"] == 1
    assert record["data"]["content"]["Doc No"] == "A-001"
    assert record["provenance"] == {"sheet": "Register", "row": 1}

    combined = " ".join(result.diagnostics + [str(record)]).lower()
    assert "cell_range" not in combined
    assert "workbook_cell" not in combined
    assert "generic workbook" not in combined


def _build_db(tmp_path):
    db = DatabaseManager(root_dir=str(tmp_path), db_name=":memory:")
    migration = Path("src/infra/persistence/migrations/001_baseline_v14.sql")
    db.execute_script(migration.read_text(encoding="utf-8-sig"))

    now = db._ts()
    db.execute(
        "INSERT INTO file_registry (file_id, project_id, first_seen_path, created_at) VALUES (?, ?, ?, ?)",
        ("file_office", "ProjectA", str(tmp_path / "source.docx"), now),
    )
    db.execute(
        "INSERT INTO file_versions (file_version_id, file_id, sha256, size_bytes, file_ext, imported_at, source_path) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("fv_office", "file_office", "hash-office", 1, ".docx", now, str(tmp_path / "source.docx")),
    )
    db.commit()
    return db


def test_extract_job_handles_current_office_dgn_flattened_record_types_without_silent_drop(tmp_path):
    db = _build_db(tmp_path)
    job = ExtractJob("job_office", "ProjectA", "fv_office", extractor_name="word")

    job._insert_record(
        db,
        {
            "type": "pdf_page",
            "data": {
                "page_no": 1,
                "text_content": "Flattened Office/DGN page text",
                "metadata": None,
            },
            "provenance": {"page": 1, "source": "word_extractor"},
        },
        doc_id="doc_office",
    )

    page_row = db.execute(
        "SELECT page_no, text_content FROM pdf_pages WHERE file_version_id=?",
        ("fv_office",),
    ).fetchone()
    assert page_row is not None
    assert page_row["page_no"] == 1
    assert page_row["text_content"] == "Flattened Office/DGN page text"

    page_bridge = db.execute(
        "SELECT doc_id, page_index, py_text FROM pages WHERE doc_id=?",
        ("doc_office",),
    ).fetchone()
    assert page_bridge is not None
    assert page_bridge["page_index"] == 0
    assert page_bridge["py_text"] == "Flattened Office/DGN page text"


def test_extract_job_handles_current_excel_register_record_type_without_silent_drop(tmp_path):
    db = _build_db(tmp_path)
    job = ExtractJob("job_register", "ProjectA", "fv_office", extractor_name="excel_register")

    job._insert_record(
        db,
        {
            "type": "register_row",
            "data": {
                "sheet_name": "Register",
                "row_index": 5,
                "content": {"Doc No": "A-005", "Status": "Open"},
            },
            "provenance": {"sheet": "Register", "row": 5},
        },
        doc_id="doc_register",
    )

    row = db.execute(
        "SELECT sheet_name, row_index, raw_data_json FROM register_rows WHERE file_version_id=?",
        ("fv_office",),
    ).fetchone()

    assert row is not None
    assert row["sheet_name"] == "Register"
    assert row["row_index"] == 5
    assert "A-005" in row["raw_data_json"]
