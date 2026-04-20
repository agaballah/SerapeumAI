-- Migration 012: PDF Staging
-- =======================================================================
-- Tables for staging PDF content (Universal Extraction).
-- =======================================================================

CREATE TABLE IF NOT EXISTS pdf_pages (
    page_id TEXT PRIMARY KEY,       -- row_ver_page (e.g. pg_v123_1)
    file_version_id TEXT NOT NULL,
    page_no INTEGER,
    text_content TEXT,
    metadata_json TEXT,             -- Cached page metadata
    
    FOREIGN KEY(file_version_id) REFERENCES file_versions(file_version_id)
);

CREATE INDEX IF NOT EXISTS idx_pdf_pg_ver ON pdf_pages(file_version_id);

CREATE TABLE IF NOT EXISTS doc_classifications (
    class_id TEXT PRIMARY KEY,
    file_version_id TEXT NOT NULL,
    doc_type TEXT,                  -- 'SCOPE', 'SPEC', 'DRAWING'
    confidence REAL,
    keywords_json TEXT,
    
    FOREIGN KEY(file_version_id) REFERENCES file_versions(file_version_id)
);

INSERT OR IGNORE INTO schema_version (version) VALUES (12);
