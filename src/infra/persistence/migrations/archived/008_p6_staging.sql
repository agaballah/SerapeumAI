-- Migration 008: P6 Staging Tables
-- =======================================================================
-- Tables for staging raw Primavera P6 data before Fact Building.
-- Mirrors the structure of XER export tables.
-- =======================================================================

CREATE TABLE IF NOT EXISTS p6_projects (
    p6_project_id TEXT PRIMARY KEY,
    file_version_id TEXT NOT NULL,
    short_name TEXT,                -- proj_short_name
    name TEXT,                      -- proj_short_name (or title)
    data_date TIMESTAMP,            -- last_task_cal_date
    raw_json TEXT,                  -- Full row dump
    
    FOREIGN KEY(file_version_id) REFERENCES file_versions(file_version_id)
);

CREATE TABLE IF NOT EXISTS p6_wbs (
    wbs_id TEXT PRIMARY KEY,        -- wbs_id
    file_version_id TEXT NOT NULL,
    p6_project_id TEXT NOT NULL,
    parent_wbs_id TEXT,
    code TEXT,                      -- wbs_short_name
    name TEXT,                      -- wbs_name
    
    FOREIGN KEY(p6_project_id) REFERENCES p6_projects(p6_project_id),
    FOREIGN KEY(file_version_id) REFERENCES file_versions(file_version_id)
);

CREATE TABLE IF NOT EXISTS p6_activities (
    activity_id TEXT PRIMARY KEY,   -- task_id
    file_version_id TEXT NOT NULL,
    p6_project_id TEXT NOT NULL,
    wbs_id TEXT NOT NULL,
    
    code TEXT,                      -- task_code
    name TEXT,                      -- task_name
    
    start_date TIMESTAMP,           -- target_start_date (Early Start)
    finish_date TIMESTAMP,          -- target_end_date (Early Finish)
    
    status_code TEXT,               -- status_code (TK_Active, TK_Done...)
    total_float REAL,
    
    raw_json TEXT,
    
    FOREIGN KEY(p6_project_id) REFERENCES p6_projects(p6_project_id),
    FOREIGN KEY(file_version_id) REFERENCES file_versions(file_version_id)
);

CREATE TABLE IF NOT EXISTS p6_relations (
    relation_id TEXT PRIMARY KEY,   -- Synthetic (pred_task_id + task_id) or row hash
    file_version_id TEXT NOT NULL,
    p6_project_id TEXT NOT NULL,
    
    pred_activity_id TEXT NOT NULL, -- pred_task_id
    succ_activity_id TEXT NOT NULL, -- task_id
    
    rel_type TEXT,                  -- pred_type (FS, SS, FF, SF)
    lag REAL,
    
    FOREIGN KEY(p6_project_id) REFERENCES p6_projects(p6_project_id),
    FOREIGN KEY(file_version_id) REFERENCES file_versions(file_version_id)
);

CREATE INDEX IF NOT EXISTS idx_p6_act_proj ON p6_activities(p6_project_id);
CREATE INDEX IF NOT EXISTS idx_p6_rel_pred ON p6_relations(pred_activity_id);
CREATE INDEX IF NOT EXISTS idx_p6_rel_succ ON p6_relations(succ_activity_id);

INSERT OR IGNORE INTO schema_version (version) VALUES (8);
