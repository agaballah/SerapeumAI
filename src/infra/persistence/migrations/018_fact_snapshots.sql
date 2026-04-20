-- Migration: Fact Snapshots & SSOT Registry (Phase 2.3)
-- =================================================================================
-- Adds immutable snapshotting for certified facts.
-- =================================================================================

CREATE TABLE IF NOT EXISTS fact_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    label TEXT,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_snapshot_registry (
    snapshot_id TEXT NOT NULL,
    fact_id TEXT NOT NULL,
    PRIMARY KEY (snapshot_id, fact_id)
);

CREATE INDEX IF NOT EXISTS idx_snap_reg_sid ON fact_snapshot_registry(snapshot_id);
CREATE INDEX IF NOT EXISTS idx_snap_reg_fid ON fact_snapshot_registry(fact_id);

-- Version Tracking
INSERT OR IGNORE INTO schema_version (version) VALUES (18);
