-- Migration 007: V02 Spine (The Truth Engine)
-- =======================================================================
-- Establishes the core schema for Serapeum V02:
-- 1. Registry Layer (File Identity & Versioning)
-- 2. Staging Layer (Base for Extractors)
-- 3. Fact Layer (Ground Truth Atoms)
-- 4. Crosswalk Layer (Links)
-- 5. Validation Layer (Rules & Certifications)
-- =======================================================================

-- -----------------------------------------------------------------------
-- 1. REGISTRY LAYER
-- -----------------------------------------------------------------------

-- Immutable file identity (hash-based)
CREATE TABLE IF NOT EXISTS file_registry (
    file_id TEXT PRIMARY KEY,       -- UUID or hash of initial content
    project_id TEXT NOT NULL,
    first_seen_path TEXT,           -- Hint for display
    created_at INTEGER NOT NULL
);

-- Versioned content (The source of all Truth)
CREATE TABLE IF NOT EXISTS file_versions (
    file_version_id TEXT PRIMARY KEY, -- SHA256 hash or UUID
    file_id TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    file_ext TEXT,
    imported_at INTEGER NOT NULL,
    source_path TEXT,                 -- Path at time of ingestion
    
    FOREIGN KEY(file_id) REFERENCES file_registry(file_id)
);

CREATE INDEX IF NOT EXISTS idx_file_versions_hash ON file_versions(sha256);
CREATE INDEX IF NOT EXISTS idx_file_versions_file ON file_versions(file_id);

-- -----------------------------------------------------------------------
-- 2. STAGING LAYER (Extraction Audit)
-- -----------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS extraction_runs (
    run_id TEXT PRIMARY KEY,
    file_version_id TEXT NOT NULL,
    extractor_id TEXT NOT NULL,
    extractor_version TEXT NOT NULL,
    started_at INTEGER NOT NULL,
    ended_at INTEGER,
    status TEXT NOT NULL,           -- 'PENDING', 'SUCCESS', 'FAILED'
    diagnostics_json TEXT,          -- Warnings/Errors
    
    FOREIGN KEY(file_version_id) REFERENCES file_versions(file_version_id)
);

-- -----------------------------------------------------------------------
-- 3. FACT LAYER (The Atom of Truth)
-- -----------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS facts (
    fact_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    
    -- Taxonomy
    fact_type TEXT NOT NULL,        -- e.g., 'schedule.activity_start_date'
    subject_kind TEXT NOT NULL,     -- e.g., 'activity', 'document', 'bim_element'
    subject_id TEXT NOT NULL,       -- Primary Key of the subject entity
    
    -- Context
    scope_json TEXT,                -- Optional: {zone: 'Z1', system: 'HVAC'}
    as_of_json TEXT NOT NULL,       -- Snapshot definition: {snapshot_id: '...', type: 'P6'}
    
    -- Value (One must be non-null)
    value_type TEXT NOT NULL,       -- 'NUM', 'TEXT', 'DATE', 'BOOL', 'JSON'
    value_num REAL,
    value_text TEXT,
    value_bool INTEGER,
    value_json TEXT,
    unit TEXT,
    
    -- Control
    status TEXT NOT NULL DEFAULT 'CANDIDATE', -- 'CANDIDATE', 'VALIDATED', 'REJECTED'
    confidence REAL DEFAULT 1.0,
    
    -- Lineage
    method_id TEXT NOT NULL,        -- Builder ID
    builder_version TEXT,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_facts_subject ON facts(subject_id, subject_kind);
CREATE INDEX IF NOT EXISTS idx_facts_type ON facts(fact_type);
CREATE INDEX IF NOT EXISTS idx_facts_status ON facts(status);

-- Provenance (Many-to-Many: Fact -> Evidence)
CREATE TABLE IF NOT EXISTS fact_inputs (
    fact_id TEXT NOT NULL,
    file_version_id TEXT NOT NULL,
    location_json TEXT,             -- {page: 1, bbox: [x,y,w,h]} or {cell: 'A1'}
    input_kind TEXT,                -- 'evidence', 'inference_basis'
    
    PRIMARY KEY(fact_id, file_version_id),
    FOREIGN KEY(fact_id) REFERENCES facts(fact_id),
    FOREIGN KEY(file_version_id) REFERENCES file_versions(file_version_id)
);

-- -----------------------------------------------------------------------
-- 4. CROSSWALK LAYER (Links)
-- -----------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS links (
    link_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    
    link_type TEXT NOT NULL,        -- 'ACTIVITY_TO_ELEMENT', 'RFI_TO_DOC'
    
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

CREATE INDEX IF NOT EXISTS idx_links_from ON links(from_kind, from_id);
CREATE INDEX IF NOT EXISTS idx_links_to ON links(to_kind, to_id);

-- -----------------------------------------------------------------------
-- 5. VALIDATION LAYER
-- -----------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS rules (
    rule_id TEXT PRIMARY KEY,
    rule_group TEXT NOT NULL,
    severity TEXT NOT NULL,         -- 'ERROR', 'WARNING'
    description TEXT,
    logic_hash TEXT                 -- Version tracking
);

CREATE TABLE IF NOT EXISTS validation_runs (
    run_id TEXT PRIMARY KEY,
    target_id TEXT NOT NULL,        -- fact_id or link_id
    rule_id TEXT NOT NULL,
    pass_fail INTEGER NOT NULL,     -- 1=Pass, 0=Fail
    details_json TEXT,
    run_at INTEGER NOT NULL,
    
    FOREIGN KEY(target_id) REFERENCES facts(fact_id)
    -- specific FK hard to enforce if target can be link or fact, usually handled in app logic or separate tables
);

CREATE TABLE IF NOT EXISTS certifications (
    cert_id TEXT PRIMARY KEY,
    target_id TEXT NOT NULL,
    cert_type TEXT NOT NULL,        -- 'HUMAN_APPROVAL', 'AUTO_RULE'
    certified_by TEXT,              -- User ID or Rule Engine ID
    certified_at INTEGER NOT NULL,
    note TEXT
);

-- Version update
INSERT OR IGNORE INTO schema_version (version) VALUES (7);
