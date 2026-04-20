-- Migration 001: Initial Global Schema (Standards + Benchmarking + Preferences)
-- =======================================================================

-- 1. Engineering Standards
CREATE TABLE IF NOT EXISTS standards (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    region TEXT NOT NULL,
    meta TEXT
);

CREATE TABLE IF NOT EXISTS clauses (
    id INTEGER PRIMARY KEY,
    standard_id INTEGER NOT NULL,
    path TEXT NOT NULL,
    text TEXT NOT NULL,
    meta TEXT,
    FOREIGN KEY(standard_id) REFERENCES standards(id)
);

CREATE TABLE IF NOT EXISTS mappings (
    clause_id INTEGER NOT NULL,
    concept TEXT NOT NULL,
    meta TEXT,
    PRIMARY KEY (clause_id, concept),
    FOREIGN KEY(clause_id) REFERENCES clauses(id)
);

CREATE TABLE IF NOT EXISTS xrefs (
    a INTEGER NOT NULL,
    b INTEGER NOT NULL,
    kind TEXT NOT NULL,
    meta TEXT,
    PRIMARY KEY (a, b, kind),
    FOREIGN KEY(a) REFERENCES clauses(id),
    FOREIGN KEY(b) REFERENCES clauses(id)
);

CREATE INDEX IF NOT EXISTS idx_standards_region ON standards(region);
CREATE INDEX IF NOT EXISTS idx_clauses_standard_path ON clauses(standard_id, path);
CREATE INDEX IF NOT EXISTS idx_mappings_concept ON mappings(concept);
CREATE INDEX IF NOT EXISTS idx_mappings_clause ON mappings(clause_id);
CREATE INDEX IF NOT EXISTS idx_xrefs_a ON xrefs(a);
CREATE INDEX IF NOT EXISTS idx_xrefs_b ON xrefs(b);

-- 2. LM Studio Benchmarking & Preferences
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

CREATE INDEX IF NOT EXISTS idx_model_benchmarks_task ON model_benchmarks(task);
CREATE INDEX IF NOT EXISTS idx_model_benchmarks_model ON model_benchmarks(model);

CREATE TABLE IF NOT EXISTS model_preferences (
    task TEXT PRIMARY KEY,
    preferred_model TEXT NOT NULL,
    last_updated INTEGER NOT NULL
);

-- 3. Telemetry (Global)
CREATE TABLE IF NOT EXISTS model_usage (
    usage_id TEXT PRIMARY KEY,
    model_name TEXT NOT NULL,
    task_type TEXT NOT NULL,
    tokens_in INTEGER,
    tokens_out INTEGER,
    duration_ms INTEGER,
    tokens_per_sec REAL,
    created_at INTEGER NOT NULL
);

-- Version tracking (Global)
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

INSERT OR IGNORE INTO schema_version (version) VALUES (1);
