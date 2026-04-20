from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional


def _safe_json(value: Any) -> Any:
    if value in (None, ""):
        return None
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(str(value))
    except Exception:
        return value


def _fmt_ts(value: Any) -> str:
    if value in (None, ""):
        return "Not recorded"
    try:
        return datetime.fromtimestamp(float(value)).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(value)


def _trim(text: Any, limit: int = 240) -> str:
    raw = " ".join(str(text or "").split())
    if len(raw) <= limit:
        return raw
    return raw[: limit - 3].rstrip() + "..."




def _looks_like_header(line: str) -> bool:
    raw = " ".join(str(line or "").split())
    if not raw or len(raw) > 90:
        return False
    alpha = [c for c in raw if c.isalpha()]
    if not alpha:
        return False
    if raw.endswith(':'):
        return True
    upper_ratio = sum(1 for c in alpha if c.isupper()) / max(len(alpha), 1)
    return upper_ratio > 0.7 and len(raw.split()) <= 10


def _looks_like_clause_heading(line: str) -> bool:
    raw = " ".join(str(line or "").split())
    if not raw or len(raw) > 140:
        return False
    return bool(re.match(r"^(?:[A-Z]-?\d+|\d+(?:\.\d+)*|[A-Z]\.|[IVX]+\.)\s+", raw))


def _looks_like_table_line(line: str) -> bool:
    raw = str(line or "")
    if '	' in raw:
        return True
    parts = [p.strip() for p in raw.split('  ') if p.strip()]
    return len(parts) >= 3


def _format_table_line(line: str) -> str:
    raw = str(line or '').rstrip()
    if '	' in raw:
        parts = [p.strip() for p in raw.split('	') if p.strip()]
    else:
        parts = [p.strip() for p in raw.split('  ') if p.strip()]
    return ' | '.join(parts) if parts else ' '.join(raw.split())


def _reflow_deterministic_text(text: Any) -> str:
    lines = [ln.rstrip() for ln in str(text or '').splitlines()]
    out: list[str] = []
    paragraph: list[str] = []

    def flush_paragraph():
        nonlocal paragraph
        if paragraph:
            joined = ' '.join(part.strip() for part in paragraph if part.strip())
            if joined:
                out.append(joined)
            paragraph = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            flush_paragraph()
            if out and out[-1] != '':
                out.append('')
            continue
        if _looks_like_clause_heading(stripped):
            flush_paragraph()
            if out and out[-1] != '':
                out.append('')
            out.append(f"[Clause] {stripped}")
            continue
        if _looks_like_table_line(line):
            flush_paragraph()
            out.append(f"[Table] {_format_table_line(line)}")
            continue
        if _looks_like_header(stripped):
            flush_paragraph()
            if out and out[-1] != '':
                out.append('')
            out.append(f"[Header] {stripped}")
            continue
            flush_paragraph()
            out.append(f"[Table] {_format_table_line(line)}")
            continue
        paragraph.append(stripped)
    flush_paragraph()
    while out and out[-1] == '':
        out.pop()
    return "\n".join(out).strip()



def _group_blocks_by_page(blocks: List[Dict[str, Any]]) -> Dict[int, List[Dict[str, Any]]]:
    grouped: Dict[int, List[Dict[str, Any]]] = {}
    for block in blocks:
        page_idx = int(block.get('page_index') or 0)
        grouped.setdefault(page_idx, []).append(block)
    return grouped


def _format_structured_blocks(page_blocks: List[Dict[str, Any]]) -> List[str]:
    lines: List[str] = []
    for block in page_blocks:
        heading = ' '.join(str(block.get('heading_title') or '').split()).strip()
        body = _reflow_deterministic_text(block.get('text') or '')
        if heading:
            lines.append(f"[Section] {heading}")
        if body:
            lines.append(body)
        if heading or body:
            lines.append('')
    while lines and lines[-1] == '':
        lines.pop()
    return lines

def _basename(path: str | None) -> str:
    path = str(path or "").replace("/", os.sep).replace("\\", os.sep)
    return os.path.basename(path) or "Unknown file"


def _optional_pdf_metadata(file_path: str | None) -> Dict[str, Any]:
    if not file_path or not os.path.exists(file_path) or not str(file_path).lower().endswith(".pdf"):
        return {}
    for mod in ("pypdf", "PyPDF2"):
        try:
            lib = __import__(mod)
            reader_cls = getattr(lib, "PdfReader", None)
            if not reader_cls:
                continue
            reader = reader_cls(file_path)
            meta = getattr(reader, "metadata", None) or {}
            out = {}
            for src_key, dst_key in {
                "/Producer": "producer",
                "/Creator": "creator",
                "/Author": "author",
                "/Subject": "subject",
                "/Title": "title",
                "/ModDate": "modified",
            }.items():
                if meta.get(src_key):
                    out[dst_key] = str(meta.get(src_key))
            return out
        except Exception:
            continue
    return {}


def _first_nonempty(*values: Any) -> str:
    for value in values:
        if value not in (None, "", [], {}):
            return str(value)
    return ""


class _RowWrap:
    def __init__(self, row: Any):
        self.row = dict(row) if row is not None else {}

    def get(self, key: str, default: Any = None) -> Any:
        return self.row.get(key, default)



def build_file_inspector_payload(db: Any, *, file_id: Optional[str] = None, file_path: Optional[str] = None) -> Dict[str, str]:
    file_version = _resolve_file_version(db, file_id=file_id, file_path=file_path)
    document = _resolve_document(db, file_version=file_version, file_path=file_path)
    pages = db.list_pages(document.get("doc_id")) if document.get("doc_id") else []
    runs = _query_rows(db, "SELECT * FROM extraction_runs WHERE file_version_id=? ORDER BY started_at DESC", (file_version.get("file_version_id"),)) if file_version.get("file_version_id") else []
    blocks = _query_rows(db, "SELECT * FROM doc_blocks WHERE doc_id=? ORDER BY page_index, id", (document.get("doc_id"),)) if document.get("doc_id") else []

    source_path = _first_nonempty(file_version.get("source_path"), document.get("abs_path"), file_path)
    title = _basename(source_path)

    return {
        "title": title,
        "consolidated_review": _build_consolidated_review(document, file_version, pages, blocks, runs, source_path),
        "full_metadata": _build_full_metadata(document, file_version, pages, source_path),
        "raw_deterministic_extraction": _build_raw_deterministic(document, file_version, pages, blocks),
        "ai_output_only": _build_ai_output(document, pages),
    }


def _query_one(db: Any, sql: str, params: tuple[Any, ...]) -> Dict[str, Any]:
    try:
        row = db.execute(sql, params).fetchone()
        return dict(row) if row else {}
    except Exception:
        return {}


def _query_rows(db: Any, sql: str, params: tuple[Any, ...]) -> List[Dict[str, Any]]:
    try:
        return [dict(r) for r in db.execute(sql, params).fetchall()]
    except Exception:
        return []


def _resolve_file_version(db: Any, *, file_id: Optional[str], file_path: Optional[str]) -> Dict[str, Any]:
    if file_id:
        row = _query_one(db, "SELECT * FROM file_versions WHERE file_id=? ORDER BY imported_at DESC LIMIT 1", (file_id,))
        if row:
            return row
    if file_path:
        row = _query_one(db, "SELECT * FROM file_versions WHERE source_path=? ORDER BY imported_at DESC LIMIT 1", (file_path,))
        if row:
            return row
        base = _basename(file_path)
        row = _query_one(db, "SELECT * FROM file_versions WHERE source_path LIKE ? ORDER BY imported_at DESC LIMIT 1", (f"%{base}",))
        if row:
            return row
    return {}


def _resolve_document(db: Any, *, file_version: Dict[str, Any], file_path: Optional[str]) -> Dict[str, Any]:
    source_path = _first_nonempty(file_version.get("source_path"), file_path)
    if source_path:
        row = _query_one(db, "SELECT * FROM documents WHERE abs_path=? OR file_name=? OR rel_path=? LIMIT 1", (source_path, source_path, source_path))
        if row:
            return row
        row = _query_one(db, "SELECT * FROM documents WHERE file_name=? LIMIT 1", (_basename(source_path),))
        if row:
            return row
    return {}


def _build_consolidated_review(document: Dict[str, Any], file_version: Dict[str, Any], pages: List[Dict[str, Any]], blocks: List[Dict[str, Any]], runs: List[Dict[str, Any]], source_path: str) -> str:
    py_pages = [p for p in pages if str(p.get("py_text") or "").strip()]
    ocr_pages = [p for p in pages if str(p.get("ocr_text") or "").strip()]
    ai_pages = [p for p in pages if str(p.get("page_summary_short") or p.get("page_summary_detailed") or p.get("vision_general") or p.get("vision_detailed") or "").strip()]
    snippets: List[str] = []
    for page in py_pages[:2] + ocr_pages[:2]:
        page_no = int(page.get("page_index") or 0) + 1
        text = _first_nonempty(page.get("py_text"), page.get("ocr_text"))
        if text:
            snippets.append(f"- Extraction p.{page_no}: {_trim(text, 180)}")
    for page in ai_pages[:2]:
        page_no = int(page.get("page_index") or 0) + 1
        ai_text = _first_nonempty(page.get("page_summary_short"), page.get("page_summary_detailed"), page.get("vision_general"), page.get("vision_detailed"))
        if ai_text:
            snippets.append(f"- AI review p.{page_no}: {_trim(ai_text, 180)}")

    lines = [
        f"File: {_basename(source_path)}",
        f"Document type: {_first_nonempty(document.get('doc_type'), 'general document')}",
        f"Imported: {_fmt_ts(file_version.get('imported_at'))}",
        f"Pages detected: {len(pages)}",
        f"Deterministic extraction coverage: {len(py_pages)} page(s) with direct text, {len(ocr_pages)} page(s) with OCR text",
        f"AI interpretation coverage: {len(ai_pages)} page(s)",
    ]
    if runs:
        latest = runs[0]
        lines.append(f"Latest extraction run: {latest.get('status', 'UNKNOWN')} using {latest.get('extractor_id') or latest.get('extractor_name') or 'extractor'}")
    if blocks:
        lines.append(f"Structured deterministic blocks: {len(blocks)}")
    lines.append("")
    lines.append("Readable review highlights")
    lines.extend(snippets or ["- No readable review highlights recorded yet."])
    return "\n".join(lines)


def _build_full_metadata(document: Dict[str, Any], file_version: Dict[str, Any], pages: List[Dict[str, Any]], source_path: str) -> str:
    doc_meta = _safe_json(document.get("meta_json")) or {}
    pdf_meta = _optional_pdf_metadata(source_path)
    file_stats = {}
    if source_path and os.path.exists(source_path):
        try:
            st = os.stat(source_path)
            file_stats = {
                "size_bytes": st.st_size,
                "modified": _fmt_ts(st.st_mtime),
                "created": _fmt_ts(getattr(st, "st_ctime", None)),
            }
        except Exception:
            file_stats = {}

    combined = {
        "file": {
            "name": _basename(source_path),
            "path": source_path or "Not recorded",
            "extension": file_version.get("file_ext") or document.get("file_ext") or "Not recorded",
            "sha256": file_version.get("sha256") or document.get("file_hash") or "Not recorded",
            **file_stats,
        },
        "document": {
            "doc_id": document.get("doc_id") or "Not recorded",
            "project_id": document.get("project_id") or "Not recorded",
            "doc_type": document.get("doc_type") or "Not recorded",
            "doc_title": document.get("doc_title") or "Not recorded",
        },
        "container_metadata": {
            "producer": pdf_meta.get("producer") or doc_meta.get("producer") or "Not recorded",
            "creator": pdf_meta.get("creator") or doc_meta.get("creator") or "Not recorded",
            "author": pdf_meta.get("author") or doc_meta.get("author") or "Not recorded",
            "software": doc_meta.get("software") or doc_meta.get("software_version") or "Not recorded",
            "title": pdf_meta.get("title") or doc_meta.get("title") or document.get("doc_title") or "Not recorded",
            "subject": pdf_meta.get("subject") or doc_meta.get("subject") or "Not recorded",
        },
        "ingestion": {
            "file_version_id": file_version.get("file_version_id") or "Not recorded",
            "file_id": file_version.get("file_id") or "Not recorded",
            "imported_at": _fmt_ts(file_version.get("imported_at")),
            "pages_detected": len(pages),
        },
        "raw_document_meta_json": doc_meta,
    }
    return json.dumps(combined, indent=2, ensure_ascii=False)


def _build_raw_deterministic(document: Dict[str, Any], file_version: Dict[str, Any], pages: List[Dict[str, Any]], blocks: List[Dict[str, Any]]) -> str:
    file_ext = str(file_version.get("file_ext") or document.get("file_ext") or "").lower()
    lines = [
        "Deterministic / parser extraction only",
        "No AI narrative is included in this tab.",
        "",
    ]
    blocks_by_page = _group_blocks_by_page(blocks)
    for page in pages:
        page_no = int(page.get("page_index") or 0) + 1
        py_text = _reflow_deterministic_text(page.get("py_text") or "")
        ocr_text = _reflow_deterministic_text(page.get("ocr_text") or "")
        page_blocks = blocks_by_page.get(int(page.get("page_index") or 0), [])
        if not py_text and not ocr_text and not page_blocks:
            continue
        lines.append(f"--- PAGE {page_no} ---")
        if page_blocks:
            lines.append("[Structured Sections]")
            lines.extend(_format_structured_blocks(page_blocks[:8]))
            if page_blocks and lines and lines[-1] != '':
                lines.append('')
        if py_text:
            lines.append("[Direct Text]")
            lines.append(py_text)
        if ocr_text:
            lines.append("[OCR / Parser Text]")
            lines.append(ocr_text)
        lines.append("")
    if len(lines) <= 3:
        if file_ext in {'.xlsx', '.xls'}:
            lines.append('No deterministic page text is recorded for this workbook. Structured deterministic spreadsheet extraction is not yet available in this build, so workbook semantics remain limited to stored deterministic metadata only.')
        else:
            lines.append("No deterministic extraction has been recorded yet.")
    return "\n".join(lines)


def _build_ai_output(document: Dict[str, Any], pages: List[Dict[str, Any]]) -> str:
    lines = [
        "AI-generated / non-governing output only",
        "This tab contains AI interpretation and synthesis. It does not represent certified truth by itself.",
        "",
    ]
    for page in pages:
        page_no = int(page.get("page_index") or 0) + 1
        short = str(page.get("page_summary_short") or "").strip()
        detailed = str(page.get("page_summary_detailed") or "").strip()
        vg = str(page.get("vision_general") or "").strip()
        vd = str(page.get("vision_detailed") or "").strip()
        vocr = str(page.get("vision_ocr_text") or "").strip()
        if not any([short, detailed, vg, vd, vocr]):
            continue
        lines.append(f"--- PAGE {page_no} ---")
        if short:
            lines.append(f"[AI Summary] {short}")
        if detailed:
            lines.append(f"[AI Detailed Summary]\n{detailed}")
        if vg:
            lines.append(f"[AI Vision Review]\n{vg}")
        if vd:
            lines.append(f"[AI Detailed Vision]\n{vd}")
        if vocr:
            lines.append(f"[AI OCR Interpretation]\n{vocr}")
        lines.append("")
    if len(lines) <= 3:
        lines.append("No AI-generated outputs have been recorded yet.")
    return "\n".join(lines)
