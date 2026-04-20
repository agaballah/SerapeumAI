-- Migration: Scaling Indexes for Production Scale
-- Targeted at documents, pages, and facts tables to speed up dashboard and RAG lookups.

CREATE INDEX IF NOT EXISTS idx_docs_project ON documents(project_id);
CREATE INDEX IF NOT EXISTS idx_pages_doc ON pages(doc_id, page_index);
CREATE INDEX IF NOT EXISTS idx_facts_status ON facts(status, created_at);
-- job_queue index removed (handled in job_queue.py)

-- Add vision_indexed flag to pages for efficient RAG synchronization
ALTER TABLE pages ADD COLUMN vision_indexed INTEGER DEFAULT 0;
CREATE INDEX IF NOT EXISTS idx_pages_vision_indexed ON pages(vision_indexed) WHERE vision_indexed = 0;

-- Vision Queue Table for O(1) performance
CREATE TABLE IF NOT EXISTS vision_queue (
    queue_id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id TEXT NOT NULL,
    page_index INTEGER NOT NULL,
    priority INTEGER DEFAULT 0,
    status TEXT DEFAULT 'queued', -- 'queued', 'processing', 'failed'
    retry_count INTEGER DEFAULT 0,
    created_at INTEGER,
    UNIQUE(doc_id, page_index)
);
CREATE INDEX IF NOT EXISTS idx_vision_queue_status ON vision_queue(status, priority DESC, created_at ASC);
