from pathlib import Path

from src.application.services.file_inspector_presentation import build_file_inspector_payload


class _Rows:
    def __init__(self, rows):
        self._rows = rows

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return self._rows


class _FakeDb:
    def __init__(self, source_path: str):
        self.source_path = source_path

    def execute(self, sql, params=()):
        sql = " ".join(str(sql).split())
        if "FROM file_versions" in sql and "file_id=?" in sql:
            return _Rows([{"file_version_id": "fv1", "file_id": "file1", "source_path": self.source_path, "file_ext": ".pdf", "sha256": "abc", "imported_at": 1000}])
        if "FROM documents WHERE abs_path=?" in sql or "FROM documents WHERE file_name=? LIMIT 1" in sql:
            return _Rows([{"doc_id": "doc1", "project_id": "ProjectA", "doc_type": "scope_document", "doc_title": "Scope Package", "meta_json": '{"software": "Adobe Acrobat", "creator": "Authoring Tool"}', "abs_path": self.source_path, "file_name": Path(self.source_path).name}])
        if "FROM extraction_runs" in sql:
            return _Rows([{"status": "SUCCESS", "extractor_id": "pdf-extractor", "started_at": 1000}])
        if "FROM doc_blocks" in sql:
            return _Rows([{"page_index": 0, "id": 1, "heading_title": "Scope", "text": "Mechanical, electrical, and life-safety works are included."}])
        return _Rows([])

    def list_pages(self, doc_id):
        return [
            {"page_index": 0, "py_text": "The contractor shall provide modular construction works.", "ocr_text": "", "page_summary_short": "AI summary says modular construction is in scope.", "page_summary_detailed": "Detailed AI review.", "vision_general": "", "vision_detailed": "", "vision_ocr_text": ""},
            {"page_index": 1, "py_text": "", "ocr_text": "Install associated MEP systems.", "page_summary_short": "", "page_summary_detailed": "", "vision_general": "AI vision interpretation.", "vision_detailed": "", "vision_ocr_text": "AI OCR interpretation."},
        ]


def test_file_inspector_payload_separates_deterministic_and_ai_lanes(tmp_path):
    pdf = tmp_path / "scope.pdf"
    pdf.write_text("placeholder", encoding="utf-8")
    payload = build_file_inspector_payload(_FakeDb(str(pdf)), file_id="file1", file_path=str(pdf))
    assert "Consolidated Review" not in payload["consolidated_review"]  # content, not tab label
    assert "Readable review highlights" in payload["consolidated_review"]
    assert "Deterministic / parser extraction only" in payload["raw_deterministic_extraction"]
    assert "AI-generated / non-governing output only" in payload["ai_output_only"]
    assert "AI summary says modular construction is in scope." not in payload["raw_deterministic_extraction"]
    assert "Detailed AI review." in payload["ai_output_only"]


def test_file_inspector_metadata_contains_user_relevant_fields(tmp_path):
    pdf = tmp_path / "scope.pdf"
    pdf.write_text("placeholder", encoding="utf-8")
    payload = build_file_inspector_payload(_FakeDb(str(pdf)), file_id="file1", file_path=str(pdf))
    text = payload["full_metadata"]
    assert '"producer"' in text
    assert '"creator"' in text
    assert '"software"' in text
    assert '"file_version_id"' in text
