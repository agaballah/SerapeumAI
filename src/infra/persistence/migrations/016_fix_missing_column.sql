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

-- No schema changes needed - column exists in baseline
-- Just mark version as applied
INSERT OR IGNORE INTO schema_version (version) VALUES (16);
