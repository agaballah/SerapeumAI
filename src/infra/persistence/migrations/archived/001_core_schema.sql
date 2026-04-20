-- Migration 001: Initial AECO Intelligence Schema
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS projects (
    project_id TEXT PRIMARY KEY,
    name TEXT,
    root TEXT,
    created INTEGER,
    updated INTEGER
);

CREATE TABLE IF NOT EXISTS documents (
    doc_id TEXT PRIMARY KEY,
    project_id TEXT,
    file_name TEXT,
    rel_path TEXT,
    abs_path TEXT,
    file_ext TEXT,
    file_hash TEXT,
    file_size INTEGER,
    file_mtime REAL,
    doc_type TEXT DEFAULT 'general_document',
    doc_title TEXT,
    content_text TEXT,
    meta_json TEXT,
    created INTEGER,
    updated INTEGER
);

CREATE TABLE IF NOT EXISTS pages (
    doc_id TEXT,
    page_index INTEGER,
    width INTEGER,
    height INTEGER,
    py_text_extracted BOOLEAN DEFAULT 0,
    py_text_len INTEGER DEFAULT 0,
    py_text TEXT,
    vision_ocr_done BOOLEAN DEFAULT 0,
    vision_ocr_len INTEGER DEFAULT 0,
    vision_model TEXT,
    vision_ocr_text TEXT,
    vision_general TEXT,
    vision_detailed TEXT,
    vision_timestamp INTEGER,
    img_path TEXT,
    ocr_text TEXT,
    text_hint TEXT,
    image_path TEXT,
    image_hash TEXT,
    quality TEXT,
    caption_json TEXT,
    vision_quality_score REAL DEFAULT 0.0,
    vision_quality_flags TEXT,
    vision_needs_retry BOOLEAN DEFAULT 0,
    vision_human_review BOOLEAN DEFAULT 0,
    page_summary_short TEXT,
    page_summary_detailed TEXT,
    page_entities TEXT,
    ai_summary_generated BOOLEAN DEFAULT 0,
    ai_model_used TEXT,
    has_raster BOOLEAN DEFAULT 0,
    has_vector BOOLEAN DEFAULT 0,
    layout_json TEXT,
    unified_context TEXT,
    updated INTEGER,
    PRIMARY KEY (doc_id, page_index)
);

CREATE TABLE IF NOT EXISTS chat_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT,
    role TEXT,
    content TEXT,
    attachments_json TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS doc_blocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id TEXT NOT NULL,
    block_id TEXT NOT NULL,
    page_index INTEGER NOT NULL,
    heading_title TEXT,
    heading_number TEXT,
    level INTEGER NOT NULL DEFAULT 0,
    text TEXT NOT NULL,
    source_type TEXT NOT NULL DEFAULT 'pdf',
    created_at INTEGER,
    UNIQUE(doc_id, block_id)
);

CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
    doc_id UNINDEXED,
    content_text
);

CREATE VIRTUAL TABLE IF NOT EXISTS doc_blocks_fts USING fts5(
    doc_id UNINDEXED,
    block_id UNINDEXED,
    heading_title,
    heading_number,
    text
);

INSERT OR IGNORE INTO schema_version (version) VALUES (1);
