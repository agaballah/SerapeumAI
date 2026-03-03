-- Migration 015: Ingestion Optimization
-- =======================================================================
-- Adds metadata tracking to allow skipping redundant hash calculations.
-- =================================--------------------------------------

-- Add last_modified_at to track filesystem mtime
ALTER TABLE file_versions ADD COLUMN last_modified_at REAL;

-- Create an index to speed up the metadata check during project scan
CREATE INDEX IF NOT EXISTS idx_file_versions_metadata 
ON file_versions(source_path, size_bytes, last_modified_at);

-- Version update
INSERT OR IGNORE INTO schema_version (version) VALUES (15);
