-- Migration 003: Global File Registry for Standards
-- =================================================

CREATE TABLE IF NOT EXISTS file_registry (
    file_id TEXT PRIMARY KEY,
    project_id TEXT, -- For global files, this might be 'GLOBAL'
    first_seen_path TEXT NOT NULL,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS file_versions (
    file_version_id TEXT PRIMARY KEY,
    file_id TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    file_ext TEXT NOT NULL,
    imported_at INTEGER NOT NULL,
    source_path TEXT NOT NULL,
    last_modified_at INTEGER,
    FOREIGN KEY(file_id) REFERENCES file_registry(file_id)
);

CREATE TABLE IF NOT EXISTS documents (
    doc_id TEXT PRIMARY KEY,
    project_id TEXT,
    file_name TEXT NOT NULL,
    rel_path TEXT NOT NULL,
    abs_path TEXT NOT NULL,
    file_ext TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    file_mtime INTEGER NOT NULL,
    created INTEGER NOT NULL,
    updated INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS extraction_runs (
    run_id TEXT PRIMARY KEY,
    file_version_id TEXT NOT NULL,
    extractor_name TEXT NOT NULL,
    extractor_version TEXT NOT NULL,
    status TEXT NOT NULL, -- PENDING, RUNNING, SUCCESS, FAILED
    started_at INTEGER NOT NULL,
    ended_at INTEGER,
    diagnostics_json TEXT,
    FOREIGN KEY(file_version_id) REFERENCES file_versions(file_version_id)
);
