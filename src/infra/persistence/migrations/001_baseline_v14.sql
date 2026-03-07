-- Migration: Consolidated Baseline v14
-- =================================================================================
-- This migration consolidates the final state of all migrations 001-014 into 
-- a single baseline for faster fresh installations.
--
-- IMPORTANT: This file replaces migrations 001-014 for NEW installations only.
-- Existing databases that have already applied migrations 1-14 will skip this.
--
-- Schema Version: 14
-- Last Updated: 2026-02-12
-- Replaces: 001-014 (archived)
-- =================================================================================

PRAGMA journal_mode=WAL;

-- =================================================================================
-- SCHEMA VERSION TRACKING
-- =================================================================================

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- =================================================================================
-- CORE PROJECT & DOCUMENT LAYER (from 001_core_schema.sql)
-- =================================================================================

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
    vision_indexed INTEGER DEFAULT 0,  -- Added in 013
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

-- Full-Text Search (FTS5)
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

-- =================================================================================
-- HARDENING & AUDIT LAYER (from 002_hardening.sql)
-- =================================================================================

CREATE TABLE IF NOT EXISTS failure_payloads (
    failure_id TEXT PRIMARY KEY,
    payload_blob BLOB NOT NULL,
    size_bytes INTEGER NOT NULL,
    compressed_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS vlm_audit_trail (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    task_type TEXT,
    system_prompt TEXT,
    user_prompt TEXT,
    response_raw TEXT,
    duration_ms INTEGER,
    model TEXT,
    status TEXT,
    error_msg TEXT
);

CREATE TABLE IF NOT EXISTS kv (
    key TEXT PRIMARY KEY,
    value_json TEXT,
    updated_at INTEGER
);

-- =================================================================================
-- LM STUDIO SUPPORT (from 006_lm_studio_support.sql)
-- =================================================================================

CREATE TABLE IF NOT EXISTS lm_studio_sessions (
    session_id TEXT PRIMARY KEY,
    session_type TEXT NOT NULL,  -- 'chat', 'vision', 'analysis'
    response_id TEXT,  -- Current LM Studio response_id
    project_id TEXT,
    created_at INTEGER NOT NULL,
    last_updated INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS model_usage (
    usage_id TEXT PRIMARY KEY,
    model_name TEXT NOT NULL,
    task_type TEXT NOT NULL,  -- 'vision', 'analysis', 'chat', 'benchmark'
    tokens_in INTEGER,
    tokens_out INTEGER,
    duration_ms INTEGER,
    tokens_per_sec REAL,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS model_benchmarks (
    benchmark_id TEXT PRIMARY KEY,
    task TEXT NOT NULL,  -- 'vision_drawing', 'entity_extraction', 'qa', 'summarization'
    model TEXT NOT NULL,
    duration_sec REAL,
    tokens_per_sec REAL,
    quality_score REAL,  -- 0.0 to 1.0
    output_sample TEXT,  -- First 500 chars of output
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS model_preferences (
    task TEXT PRIMARY KEY,
    preferred_model TEXT NOT NULL,
    last_updated INTEGER NOT NULL
);

-- =================================================================================
-- V02 SPINE - TRUTH ENGINE (from 007_v02_spine.sql)
-- =================================================================================

-- Registry Layer (File Identity & Versioning)
CREATE TABLE IF NOT EXISTS file_registry (
    file_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    first_seen_path TEXT,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS file_versions (
    file_version_id TEXT PRIMARY KEY,
    file_id TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    file_ext TEXT,
    imported_at INTEGER NOT NULL,
    source_path TEXT,
    FOREIGN KEY(file_id) REFERENCES file_registry(file_id)
);

-- Staging Layer (Extraction Audit)
CREATE TABLE IF NOT EXISTS extraction_runs (
    run_id TEXT PRIMARY KEY,
    file_version_id TEXT NOT NULL,
    extractor_id TEXT NOT NULL,
    extractor_version TEXT NOT NULL,
    started_at INTEGER NOT NULL,
    ended_at INTEGER,
    status TEXT NOT NULL,  -- 'PENDING', 'SUCCESS', 'FAILED'
    diagnostics_json TEXT,
    FOREIGN KEY(file_version_id) REFERENCES file_versions(file_version_id)
);

-- Fact Layer (The Atom of Truth)
CREATE TABLE IF NOT EXISTS facts (
    fact_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    fact_type TEXT NOT NULL,
    subject_kind TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    scope_json TEXT,
    as_of_json TEXT NOT NULL,
    value_type TEXT NOT NULL,
    value_num REAL,
    value_text TEXT,
    value_bool INTEGER,
    value_json TEXT,
    unit TEXT,
    status TEXT NOT NULL DEFAULT 'CANDIDATE',
    confidence REAL DEFAULT 1.0,
    method_id TEXT NOT NULL,
    builder_version TEXT,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_inputs (
    fact_id TEXT NOT NULL,
    file_version_id TEXT NOT NULL,
    location_json TEXT,
    input_kind TEXT,
    PRIMARY KEY(fact_id, file_version_id),
    FOREIGN KEY(fact_id) REFERENCES facts(fact_id),
    FOREIGN KEY(file_version_id) REFERENCES file_versions(file_version_id)
);

-- Crosswalk Layer (Links)
CREATE TABLE IF NOT EXISTS links (
    link_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    link_type TEXT NOT NULL,
    from_kind TEXT NOT NULL,
    from_id TEXT NOT NULL,
    to_kind TEXT NOT NULL,
    to_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'CANDIDATE',
    confidence REAL DEFAULT 1.0,
    method_id TEXT,
    created_at INTEGER NOT NULL,
    validated_at INTEGER
);

-- Validation Layer
CREATE TABLE IF NOT EXISTS rules (
    rule_id TEXT PRIMARY KEY,
    rule_group TEXT NOT NULL,
    severity TEXT NOT NULL,
    description TEXT,
    logic_hash TEXT
);

CREATE TABLE IF NOT EXISTS validation_runs (
    run_id TEXT PRIMARY KEY,
    target_id TEXT NOT NULL,
    rule_id TEXT NOT NULL,
    pass_fail INTEGER NOT NULL,
    details_json TEXT,
    run_at INTEGER NOT NULL,
    FOREIGN KEY(target_id) REFERENCES facts(fact_id)
);

CREATE TABLE IF NOT EXISTS certifications (
    cert_id TEXT PRIMARY KEY,
    target_id TEXT NOT NULL,
    cert_type TEXT NOT NULL,
    certified_by TEXT,
    certified_at INTEGER NOT NULL,
    note TEXT
);

-- =================================================================================
-- P6 STAGING (from 008_p6_staging.sql)
-- =================================================================================

CREATE TABLE IF NOT EXISTS p6_projects (
    p6_project_id TEXT PRIMARY KEY,
    file_version_id TEXT NOT NULL,
    short_name TEXT,
    name TEXT,
    data_date TIMESTAMP,
    raw_json TEXT,
    FOREIGN KEY(file_version_id) REFERENCES file_versions(file_version_id)
);

CREATE TABLE IF NOT EXISTS p6_wbs (
    wbs_id TEXT PRIMARY KEY,
    file_version_id TEXT NOT NULL,
    p6_project_id TEXT NOT NULL,
    parent_wbs_id TEXT,
    code TEXT,
    name TEXT,
    FOREIGN KEY(p6_project_id) REFERENCES p6_projects(p6_project_id),
    FOREIGN KEY(file_version_id) REFERENCES file_versions(file_version_id)
);

CREATE TABLE IF NOT EXISTS p6_activities (
    activity_id TEXT PRIMARY KEY,
    file_version_id TEXT NOT NULL,
    p6_project_id TEXT NOT NULL,
    wbs_id TEXT NOT NULL,
    code TEXT,
    name TEXT,
    start_date TIMESTAMP,
    finish_date TIMESTAMP,
    status_code TEXT,
    total_float REAL,
    raw_json TEXT,
    FOREIGN KEY(p6_project_id) REFERENCES p6_projects(p6_project_id),
    FOREIGN KEY(file_version_id) REFERENCES file_versions(file_version_id)
);

CREATE TABLE IF NOT EXISTS p6_relations (
    relation_id TEXT PRIMARY KEY,
    file_version_id TEXT NOT NULL,
    p6_project_id TEXT NOT NULL,
    pred_activity_id TEXT NOT NULL,
    succ_activity_id TEXT NOT NULL,
    rel_type TEXT,
    lag REAL,
    FOREIGN KEY(p6_project_id) REFERENCES p6_projects(p6_project_id),
    FOREIGN KEY(file_version_id) REFERENCES file_versions(file_version_id)
);

-- =================================================================================
-- IFC STAGING (from 009_ifc_staging.sql)
-- =================================================================================

CREATE TABLE IF NOT EXISTS ifc_projects (
    global_id TEXT PRIMARY KEY,
    file_version_id TEXT NOT NULL,
    name TEXT,
    long_name TEXT,
    phase TEXT,
    FOREIGN KEY(file_version_id) REFERENCES file_versions(file_version_id)
);

CREATE TABLE IF NOT EXISTS ifc_spatial_structure (
    element_id TEXT PRIMARY KEY,
    file_version_id TEXT NOT NULL,
    ifc_project_id TEXT,
    parent_id TEXT,
    entity_type TEXT,
    name TEXT,
    elevation REAL,
    raw_properties_json TEXT,
    FOREIGN KEY(file_version_id) REFERENCES file_versions(file_version_id)
);

CREATE TABLE IF NOT EXISTS ifc_elements (
    element_id TEXT PRIMARY KEY,
    file_version_id TEXT NOT NULL,
    spatial_container_id TEXT,
    entity_type TEXT,
    name TEXT,
    tag TEXT,
    raw_properties_json TEXT,
    FOREIGN KEY(file_version_id) REFERENCES file_versions(file_version_id)
);

-- =================================================================================
-- REGISTERS STAGING (from 010_registers.sql)
-- =================================================================================

CREATE TABLE IF NOT EXISTS register_rows (
    row_id TEXT PRIMARY KEY,
    file_version_id TEXT NOT NULL,
    sheet_name TEXT,
    row_index INTEGER,
    raw_data_json TEXT,
    FOREIGN KEY(file_version_id) REFERENCES file_versions(file_version_id)
);

-- =================================================================================
-- FIELD STAGING (from 011_field_staging.sql)
-- =================================================================================

CREATE TABLE IF NOT EXISTS field_requests (
    request_id TEXT PRIMARY KEY,
    file_version_id TEXT NOT NULL,
    req_type TEXT,
    discp_code TEXT,
    location_text TEXT,
    status TEXT,
    inspection_date TEXT,
    raw_vlm_json TEXT,
    FOREIGN KEY(file_version_id) REFERENCES file_versions(file_version_id)
);

-- =================================================================================
-- PDF STAGING (from 012_pdf_staging.sql)
-- =================================================================================

CREATE TABLE IF NOT EXISTS pdf_pages (
    page_id TEXT PRIMARY KEY,
    file_version_id TEXT NOT NULL,
    page_no INTEGER,
    text_content TEXT,
    metadata_json TEXT,
    FOREIGN KEY(file_version_id) REFERENCES file_versions(file_version_id)
);

CREATE TABLE IF NOT EXISTS doc_classifications (
    class_id TEXT PRIMARY KEY,
    file_version_id TEXT NOT NULL,
    doc_type TEXT,
    confidence REAL,
    keywords_json TEXT,
    FOREIGN KEY(file_version_id) REFERENCES file_versions(file_version_id)
);

-- =================================================================================
-- VISION QUEUE (from 013_scaling_indexes.sql)
-- =================================================================================

CREATE TABLE IF NOT EXISTS vision_queue (
    queue_id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id TEXT NOT NULL,
    page_index INTEGER NOT NULL,
    priority INTEGER DEFAULT 0,
    status TEXT DEFAULT 'queued',
    retry_count INTEGER DEFAULT 0,
    created_at INTEGER,
    UNIQUE(doc_id, page_index)
);

-- =================================================================================
-- GRAPH ENTITIES (from 014_performance_tuning.sql)
-- =================================================================================

CREATE TABLE IF NOT EXISTS entity_nodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    value TEXT NOT NULL,
    doc_id TEXT,
    extra_json TEXT,
    confidence REAL DEFAULT 0.0,
    created_ts INTEGER,
    UNIQUE(project_id, entity_type, value, doc_id)
);

CREATE TABLE IF NOT EXISTS entity_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    from_entity_id INTEGER NOT NULL,
    to_entity_id INTEGER NOT NULL,
    rel_type TEXT NOT NULL,
    source_doc_id TEXT,
    confidence REAL DEFAULT 1.0,
    created_ts INTEGER,
    UNIQUE(project_id, from_entity_id, to_entity_id, rel_type),
    FOREIGN KEY(from_entity_id) REFERENCES entity_nodes(id),
    FOREIGN KEY(to_entity_id) REFERENCES entity_nodes(id)
);

-- =================================================================================
-- INDEXES (consolidated from 013 & 014)
-- =================================================================================

-- Core document indexes
CREATE INDEX IF NOT EXISTS idx_docs_project ON documents(project_id);
CREATE INDEX IF NOT EXISTS idx_pages_doc ON pages(doc_id, page_index);
CREATE INDEX IF NOT EXISTS idx_pages_vision_indexed ON pages(vision_indexed) WHERE vision_indexed = 0;

-- Fact layer indexes
CREATE INDEX IF NOT EXISTS idx_facts_subject ON facts(subject_id, subject_kind);
CREATE INDEX IF NOT EXISTS idx_facts_type ON facts(fact_type);
CREATE INDEX IF NOT EXISTS idx_facts_status ON facts(status, created_at);

-- File versioning indexes
CREATE INDEX IF NOT EXISTS idx_file_versions_hash ON file_versions(sha256);
CREATE INDEX IF NOT EXISTS idx_file_versions_file ON file_versions(file_id);

-- Link indexes
CREATE INDEX IF NOT EXISTS idx_links_from ON links(from_kind, from_id);
CREATE INDEX IF NOT EXISTS idx_links_to ON links(to_kind, to_id);
CREATE INDEX IF NOT EXISTS idx_links_project_kind ON links(project_id, from_kind, from_id);
CREATE INDEX IF NOT EXISTS idx_links_target ON links(to_kind, to_id);

-- LM Studio indexes
CREATE INDEX IF NOT EXISTS idx_lm_studio_sessions_project ON lm_studio_sessions(project_id);
CREATE INDEX IF NOT EXISTS idx_lm_studio_sessions_type ON lm_studio_sessions(session_type);
CREATE INDEX IF NOT EXISTS idx_model_usage_model ON model_usage(model_name);
CREATE INDEX IF NOT EXISTS idx_model_usage_task ON model_usage(task_type);
CREATE INDEX IF NOT EXISTS idx_model_usage_created ON model_usage(created_at);
CREATE INDEX IF NOT EXISTS idx_model_benchmarks_task ON model_benchmarks(task);
CREATE INDEX IF NOT EXISTS idx_model_benchmarks_model ON model_benchmarks(model);

-- P6 indexes
CREATE INDEX IF NOT EXISTS idx_p6_act_proj ON p6_activities(p6_project_id);
CREATE INDEX IF NOT EXISTS idx_p6_rel_pred ON p6_relations(pred_activity_id);
CREATE INDEX IF NOT EXISTS idx_p6_rel_succ ON p6_relations(succ_activity_id);

-- IFC indexes
CREATE INDEX IF NOT EXISTS idx_ifc_spatial_parent ON ifc_spatial_structure(parent_id);
CREATE INDEX IF NOT EXISTS idx_ifc_elem_container ON ifc_elements(spatial_container_id);

-- Staging indexes
CREATE INDEX IF NOT EXISTS idx_regr_ver ON register_rows(file_version_id);
CREATE INDEX IF NOT EXISTS idx_field_ver ON field_requests(file_version_id);
CREATE INDEX IF NOT EXISTS idx_pdf_pg_ver ON pdf_pages(file_version_id);

-- Vision queue index
CREATE INDEX IF NOT EXISTS idx_vision_queue_status ON vision_queue(status, priority DESC, created_at ASC);

-- Chat history index
CREATE INDEX IF NOT EXISTS idx_chat_project_ts ON chat_history(project_id, timestamp);

-- RAG block indexes
CREATE INDEX IF NOT EXISTS idx_doc_blocks_doc ON doc_blocks(doc_id);
CREATE INDEX IF NOT EXISTS idx_doc_blocks_block ON doc_blocks(block_id);

-- Graph entity indexes
CREATE INDEX IF NOT EXISTS idx_entity_nodes_lookup ON entity_nodes(project_id, entity_type, value);
CREATE INDEX IF NOT EXISTS idx_entity_links_source ON entity_links(from_entity_id);
CREATE INDEX IF NOT EXISTS idx_entity_links_target ON entity_links(to_entity_id);

-- =================================================================================
-- FTS SYNCHRONIZATION TRIGGERS (from 014_performance_tuning.sql)
-- =================================================================================

-- Keep documents_fts in sync with documents
CREATE TRIGGER IF NOT EXISTS trg_documents_ai AFTER INSERT ON documents
BEGIN
    INSERT INTO documents_fts (doc_id, content_text) VALUES (new.doc_id, new.content_text);
END;

CREATE TRIGGER IF NOT EXISTS trg_documents_au AFTER UPDATE OF content_text ON documents
BEGIN
    UPDATE documents_fts SET content_text = new.content_text WHERE doc_id = old.doc_id;
END;

CREATE TRIGGER IF NOT EXISTS trg_documents_ad AFTER DELETE ON documents
BEGIN
    DELETE FROM documents_fts WHERE doc_id = old.doc_id;
END;

-- Keep doc_blocks_fts in sync with doc_blocks
CREATE TRIGGER IF NOT EXISTS trg_doc_blocks_ai AFTER INSERT ON doc_blocks
BEGIN
    INSERT INTO doc_blocks_fts (doc_id, block_id, heading_title, heading_number, text)
    VALUES (new.doc_id, new.block_id, new.heading_title, new.heading_number, new.text);
END;

CREATE TRIGGER IF NOT EXISTS trg_doc_blocks_ad AFTER DELETE ON doc_blocks
BEGIN
    DELETE FROM doc_blocks_fts WHERE doc_id = old.doc_id AND block_id = old.block_id;
END;

-- =================================================================================
-- VERSION TRACKING
-- =================================================================================
-- Mark all consolidated versions as applied so existing DBs skip this migration
INSERT OR IGNORE INTO schema_version (version) VALUES 
    (1), (2), (6), (7), (8), (9), (10), (11), (12), (13), (14), (15);
