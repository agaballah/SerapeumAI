-- Migration 011: Field Staging
-- =======================================================================
-- Tables for staging digitized field data (IRs, NCRs, Checklists).
-- =======================================================================

CREATE TABLE IF NOT EXISTS field_requests (
    request_id TEXT PRIMARY KEY,    -- Extracted ID (e.g. IR-2023-001) or Hash
    file_version_id TEXT NOT NULL,
    
    req_type TEXT,                  -- 'IR' (Inspection), 'NCR', 'CHECKLIST'
    discp_code TEXT,                -- 'CIVIL', 'MEP'
    location_text TEXT,             -- Raw location string "Room 101"
    
    status TEXT,                    -- 'APPROVED', 'REJECTED', 'OPEN'
    inspection_date TEXT,           -- ISO8601
    
    raw_vlm_json TEXT,              -- Full VLM output
    
    FOREIGN KEY(file_version_id) REFERENCES file_versions(file_version_id)
);

CREATE INDEX IF NOT EXISTS idx_field_ver ON field_requests(file_version_id);

INSERT OR IGNORE INTO schema_version (version) VALUES (11);
