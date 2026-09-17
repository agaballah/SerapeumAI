-- Migration 020: PDF Text Bounding Box Support
-- Purpose: Enable evidence anchors for PDF text navigation
-- Impact: Additive only — no existing columns modified

ALTER TABLE pdf_pages ADD COLUMN bbox_text TEXT;
CREATE INDEX IF NOT EXISTS idx_pdf_pg_bbox ON pdf_pages(file_version_id, page_no);
