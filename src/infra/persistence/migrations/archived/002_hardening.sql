-- Migration 002: Production Hardening & Audit
CREATE TABLE IF NOT EXISTS failure_payloads (
    failure_id TEXT PRIMARY KEY,
    payload_blob BLOB NOT NULL,
    size_bytes INTEGER NOT NULL,
    compressed_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS vlm_audit_trail (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    task_type TEXT,
    system_prompt TEXT,
    user_prompt TEXT,
    response_raw TEXT,
    duration_ms INTEGER,
    model TEXT,
    status TEXT,
    error_msg TEXT
);

CREATE TABLE IF NOT EXISTS kv (
    key TEXT PRIMARY KEY,
    value_json TEXT,
    updated_at INTEGER
);

INSERT OR IGNORE INTO schema_version (version) VALUES (2);
