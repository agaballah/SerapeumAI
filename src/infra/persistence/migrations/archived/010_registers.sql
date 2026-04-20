-- Migration 010: Registers Staging
-- =======================================================================
-- Tables for staging raw tabular data from Project Controls Registers.
-- (Submittal Logs, RFI Logs, Procurement Schedules, etc.)
-- =======================================================================

CREATE TABLE IF NOT EXISTS register_rows (
    row_id TEXT PRIMARY KEY,        -- Generated GUID or hash
    file_version_id TEXT NOT NULL,
    sheet_name TEXT,
    row_index INTEGER,              -- 0-based index from source
    
    raw_data_json TEXT,             -- JSON Object of the row (Header -> Value)
                                    -- e.g. { "Activity ID": "A100", "Title": "Foundations" }
    
    FOREIGN KEY(file_version_id) REFERENCES file_versions(file_version_id)
);

CREATE INDEX IF NOT EXISTS idx_regr_ver ON register_rows(file_version_id);

INSERT OR IGNORE INTO schema_version (version) VALUES (10);
