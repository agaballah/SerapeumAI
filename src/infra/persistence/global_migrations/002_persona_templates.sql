-- Migration 002: Persona Templates for Context-Aware Routing
-- =========================================================

CREATE TABLE IF NOT EXISTS persona_templates (
    template_id TEXT PRIMARY KEY,
    role TEXT NOT NULL,
    discipline TEXT NOT NULL,
    intent TEXT NOT NULL,
    system_instructions TEXT NOT NULL,
    created_at INTEGER NOT NULL
);

-- Sample Templates: CONTRACTOR - MECH - RISK
INSERT INTO persona_templates (template_id, role, discipline, intent, system_instructions, created_at)
VALUES (
    'tmpl_cnt_mech_risk', 'Contractor', 'Mech', 'RISK',
    'Persona: Mechanical Contractor. Focus: Equipment delivery lead times, site clearances, MEP coordination clashes, and commissioning prerequisites.',
    strftime('%s','now')
);

-- Sample Templates: OWNER - PM - RISK
INSERT INTO persona_templates (template_id, role, discipline, intent, system_instructions, created_at)
VALUES (
    'tmpl_own_pm_risk', 'Owner', 'Project Manager', 'RISK',
    'Persona: Owner PM. Focus: Budget contingencies, critical path milestones (Finish Date), and high-level handover/O&M risks.',
    strftime('%s','now')
);

-- Default templates if specialized ones missing
INSERT INTO persona_templates (template_id, role, discipline, intent, system_instructions, created_at)
VALUES (
    'tmpl_default_risk', '*', '*', 'RISK',
    'Persona: General Project Intel. Focus: Schedule delays, cost overruns, and coordination gaps.',
    strftime('%s','now')
);
