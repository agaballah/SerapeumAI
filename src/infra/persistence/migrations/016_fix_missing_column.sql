-- Migration 016: Compatibility Marker (No-Op)
-- =======================================================================
-- This migration exists for version tracking only.
-- 
-- The baseline v14 (fixed) already includes the last_modified_at column.
-- This migration ensures existing databases that applied the broken baseline
-- can mark version 16 as complete without errors.
-- 
-- Fresh databases will skip this entirely (baseline handles everything).
-- =======================================================================

-- Fix for existing databases missing the ingestion optimization column
ALTER TABLE file_versions ADD COLUMN last_modified_at REAL;
CREATE INDEX IF NOT EXISTS idx_file_versions_metadata ON file_versions(source_path, size_bytes, last_modified_at);

-- Just mark version as applied
INSERT OR IGNORE INTO schema_version (version) VALUES (16);
