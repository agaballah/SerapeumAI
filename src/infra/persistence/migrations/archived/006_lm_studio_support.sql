-- Migration 006: LM Studio 0.4.0 Support
-- =======================================================================
-- Adds tables and columns for LM Studio v1 API integration:
-- - Stateful session tracking (chat, vision, analysis  
-- - Model usage telemetry
-- - Multi-model benchmarking
-- - User model preferences

-- LM Studio session tracking
CREATE TABLE IF NOT EXISTS lm_studio_sessions (
    session_id TEXT PRIMARY KEY,
    session_type TEXT NOT NULL,  -- 'chat', 'vision', 'analysis'
    response_id TEXT,  -- Current LM Studio response_id
    project_id TEXT,
    created_at INTEGER NOT NULL,
    last_updated INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_lm_studio_sessions_project ON lm_studio_sessions(project_id);
CREATE INDEX IF NOT EXISTS idx_lm_studio_sessions_type ON lm_studio_sessions(session_type);

-- Model usage telemetry
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

CREATE INDEX IF NOT EXISTS idx_model_usage_model ON model_usage(model_name);
CREATE INDEX IF NOT EXISTS idx_model_usage_task ON model_usage(task_type);
CREATE INDEX IF NOT EXISTS idx_model_usage_created ON model_usage(created_at);

-- Model benchmarks
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

-- Model preferences (user's choice per task)
CREATE TABLE IF NOT EXISTS model_preferences (
    task TEXT PRIMARY KEY,
    preferred_model TEXT NOT NULL,
    last_updated INTEGER NOT NULL
);

-- =======================================================================
-- NOTE: Column additions below will fail if columns already exist.
-- This is expected on re-runs and can be safely ignored. 
-- The migration system ensures this only runs once per database.
-- =======================================================================

INSERT OR IGNORE INTO schema_version (version) VALUES (6);
