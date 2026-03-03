-- Migration: Performance Tuning for Production Scale
-- Targeted at chat history, RAG blocks, and graph entity lookups.

-- Ensure prerequisite tables for graph entities exist
CREATE TABLE IF NOT EXISTS entity_nodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    value TEXT NOT NULL,
    doc_id TEXT,
    extra_json TEXT,
    confidence REAL DEFAULT 0.0,
    created_ts INTEGER,
    UNIQUE(project_id, entity_type, value, doc_id)
);

CREATE TABLE IF NOT EXISTS entity_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    from_entity_id INTEGER NOT NULL,
    to_entity_id INTEGER NOT NULL,
    rel_type TEXT NOT NULL,
    source_doc_id TEXT,
    confidence REAL DEFAULT 1.0,
    created_ts INTEGER,
    UNIQUE(project_id, from_entity_id, to_entity_id, rel_type),
    FOREIGN KEY(from_entity_id) REFERENCES entity_nodes(id),
    FOREIGN KEY(to_entity_id) REFERENCES entity_nodes(id)
);

-- Chat history indexing for fast project-specific loading
CREATE INDEX IF NOT EXISTS idx_chat_project_ts ON chat_history(project_id, timestamp);

-- RAG block indexing for efficient context retrieval
CREATE INDEX IF NOT EXISTS idx_doc_blocks_doc ON doc_blocks(doc_id);
CREATE INDEX IF NOT EXISTS idx_doc_blocks_block ON doc_blocks(block_id);

-- Graph entity indexing for fast relationship traversal
CREATE INDEX IF NOT EXISTS idx_entity_nodes_lookup ON entity_nodes(project_id, entity_type, value);
CREATE INDEX IF NOT EXISTS idx_entity_links_source ON entity_links(from_entity_id);
CREATE INDEX IF NOT EXISTS idx_entity_links_target ON entity_links(to_entity_id);

-- Generic link indexing
CREATE INDEX IF NOT EXISTS idx_links_project_kind ON links(project_id, from_kind, from_id);
CREATE INDEX IF NOT EXISTS idx_links_target ON links(to_kind, to_id);

-- [FTS SYNCHRONIZATION TRIGGERS]
-- Keep documents_fts in sync with documents
CREATE TRIGGER IF NOT EXISTS trg_documents_ai AFTER INSERT ON documents
BEGIN
    INSERT INTO documents_fts (doc_id, content_text) VALUES (new.doc_id, new.content_text);
END;

CREATE TRIGGER IF NOT EXISTS trg_documents_au AFTER UPDATE OF content_text ON documents
BEGIN
    UPDATE documents_fts SET content_text = new.content_text WHERE doc_id = old.doc_id;
END;

CREATE TRIGGER IF NOT EXISTS trg_documents_ad AFTER DELETE ON documents
BEGIN
    DELETE FROM documents_fts WHERE doc_id = old.doc_id;
END;

-- Keep doc_blocks_fts in sync with doc_blocks
CREATE TRIGGER IF NOT EXISTS trg_doc_blocks_ai AFTER INSERT ON doc_blocks
BEGIN
    INSERT INTO doc_blocks_fts (doc_id, block_id, heading_title, heading_number, text)
    VALUES (new.doc_id, new.block_id, new.heading_title, new.heading_number, new.text);
END;

CREATE TRIGGER IF NOT EXISTS trg_doc_blocks_ad AFTER DELETE ON doc_blocks
BEGIN
    DELETE FROM doc_blocks_fts WHERE doc_id = old.doc_id AND block_id = old.block_id;
END;

-- Version update
INSERT OR IGNORE INTO schema_version (version) VALUES (14);
