-- Migration 023: Fact Conflict Detection Support
-- Purpose: Enable cross-source conflict detection and tracking
-- Impact: Additive only — new table + nullable column on facts

CREATE TABLE IF NOT EXISTS fact_conflicts (
    conflict_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    fact_type TEXT NOT NULL,
    source_count INTEGER NOT NULL DEFAULT 2,
    values_json TEXT NOT NULL,
    conflict_type TEXT NOT NULL DEFAULT 'VALUE',
    resolution TEXT NOT NULL DEFAULT 'UNRESOLVED',
    resolved_by TEXT,
    resolved_at INTEGER,
    created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_conflicts_project ON fact_conflicts(project_id);
CREATE INDEX IF NOT EXISTS idx_conflicts_subject ON fact_conflicts(project_id, subject_id, fact_type);
CREATE INDEX IF NOT EXISTS idx_conflicts_resolution ON fact_conflicts(resolution);

-- Add conflict_flag column to facts table (nullable, default 0)
ALTER TABLE facts ADD COLUMN conflict_flag INTEGER DEFAULT 0;

