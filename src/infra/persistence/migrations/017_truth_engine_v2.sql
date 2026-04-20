-- Migration: Truth Engine v2 Spine
-- =================================================================================
-- This migration introduces Fact Domains, Link Confidence Tiers, and Authority 
-- Policies to support the "Certified Engineering Truth Engine" model.
-- =================================================================================

-- 1. Fact Domain & Authority Role Support in Facts
-- Adding columns to facts table. Since SQLite doesn't support ADD COLUMN multiple 
-- columns in one statement reliably, we'll do them sequentially or via a shadow table if needed.
-- But standard ADD COLUMN is fine for basic additions.

ALTER TABLE facts ADD COLUMN domain TEXT;
ALTER TABLE facts ADD COLUMN authority_role TEXT;

-- 2. Link Tiers
-- We'll add confidence_tier to both the generic links and the graph entity_links.
ALTER TABLE links ADD COLUMN confidence_tier TEXT DEFAULT 'CANDIDATE';
ALTER TABLE entity_links ADD COLUMN confidence_tier TEXT DEFAULT 'CANDIDATE';

-- 3. Authority Policies Table
-- Maps domains to roles authorized to certify them.
CREATE TABLE IF NOT EXISTS authority_policies (
    policy_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    role_id TEXT NOT NULL,
    can_certify BOOLEAN DEFAULT 0,
    can_validate BOOLEAN DEFAULT 1,
    UNIQUE(project_id, domain, role_id)
);

-- 4. Initial Authority Policies (Baseline)
INSERT OR IGNORE INTO authority_policies (policy_id, project_id, domain, role_id, can_certify)
VALUES 
    ('p_baseline_schedule', 'GLOBAL', 'SCHEDULE', 'PLANNER', 1),
    ('p_baseline_bim', 'GLOBAL', 'BIM', 'BIM_LEAD', 1),
    ('p_baseline_proc', 'GLOBAL', 'PROCUREMENT', 'PROCUREMENT_MANAGER', 1),
    ('p_baseline_qa', 'GLOBAL', 'FIELD', 'QA_ENGINEER', 1);

-- 5. Indexes for Domain & Performance
CREATE INDEX IF NOT EXISTS idx_facts_domain ON facts(domain, status);
CREATE INDEX IF NOT EXISTS idx_links_tier ON links(confidence_tier, status);
CREATE INDEX IF NOT EXISTS idx_entity_links_tier ON entity_links(confidence_tier);

-- 6. Schema Version Tracking
INSERT OR IGNORE INTO schema_version (version) VALUES (17);
