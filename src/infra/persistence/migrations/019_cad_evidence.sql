-- Migration: CAD Evidence Tables (Iteration 3)
-- =================================================================================
-- Adds deterministic CAD evidence persistence tables that store DXF-derived
-- drawing metadata, layer inventory, entity geometry, block definitions, text
-- annotations, and dimension measurements.
--
-- All tables are scoped to file_version_id so project isolation is enforced
-- by the foreign-key relationship (file_versions.project_id).
--
-- Entities use INSERT OR REPLACE keyed on (file_version_id, handle) to
-- provide idempotent re-ingestion without duplicate facts.
-- =================================================================================

CREATE TABLE IF NOT EXISTS cad_drawings (
    drawing_id TEXT PRIMARY KEY,
    file_version_id TEXT NOT NULL,
    drawing_version TEXT,
    created_at TEXT,
    modified_at TEXT,
    units INTEGER,                        -- $MEASUREMENT: 0=drawing units, 1=metric
    modelspace_entity_count INTEGER,
    total_entity_types INTEGER,
    entity_type_counts_json TEXT,         -- JSON object mapping type->count
    layout_count INTEGER,
    layout_names_json TEXT,               -- JSON array of layout names
    layer_count INTEGER,
    extents_min_x REAL,
    extents_min_y REAL,
    extents_max_x REAL,
    extents_max_y REAL,
    cap_reached INTEGER DEFAULT 0,        -- boolean
    raw_json TEXT,                        -- full extraction metadata snapshot
    FOREIGN KEY(file_version_id) REFERENCES file_versions(file_version_id)
);

CREATE TABLE IF NOT EXISTS cad_layers (
    layer_id TEXT PRIMARY KEY,
    file_version_id TEXT NOT NULL,
    layer_name TEXT NOT NULL,
    color INTEGER,
    linetype TEXT,
    frozen INTEGER DEFAULT 0,
    locked INTEGER DEFAULT 0,
    on_flag INTEGER DEFAULT 1,
    entity_count INTEGER DEFAULT 0,     -- populated after entity insertion
    raw_json TEXT,
    UNIQUE(file_version_id, layer_name),
    FOREIGN KEY(file_version_id) REFERENCES file_versions(file_version_id)
);

CREATE TABLE IF NOT EXISTS cad_entities (
    entity_id TEXT PRIMARY KEY,
    file_version_id TEXT NOT NULL,
    handle TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    layer TEXT NOT NULL,
    layout TEXT DEFAULT 'modelspace',
    source_file TEXT,
    raw_json TEXT NOT NULL,
    UNIQUE(file_version_id, handle),
    FOREIGN KEY(file_version_id) REFERENCES file_versions(file_version_id)
);

CREATE TABLE IF NOT EXISTS cad_blocks (
    block_id TEXT PRIMARY KEY,
    file_version_id TEXT NOT NULL,
    block_name TEXT NOT NULL,
    entity_count INTEGER DEFAULT 0,
    insert_references INTEGER DEFAULT 0,
    is_xref INTEGER DEFAULT 0,
    raw_json TEXT,
    UNIQUE(file_version_id, block_name),
    FOREIGN KEY(file_version_id) REFERENCES file_versions(file_version_id)
);

CREATE TABLE IF NOT EXISTS cad_text_annotations (
    annotation_id TEXT PRIMARY KEY,
    file_version_id TEXT NOT NULL,
    handle TEXT NOT NULL,
    entity_type TEXT NOT NULL,          -- 'TEXT' or 'MTEXT'
    layer TEXT NOT NULL,
    text_content TEXT,
    x REAL,
    y REAL,
    z REAL,
    rotation_deg REAL,
    height REAL,
    width REAL,
    text_length INTEGER,
    source_file TEXT,
    raw_json TEXT,
    UNIQUE(file_version_id, handle),
    FOREIGN KEY(file_version_id) REFERENCES file_versions(file_version_id)
);

CREATE TABLE IF NOT EXISTS cad_dimensions (
    dimension_id TEXT PRIMARY KEY,
    file_version_id TEXT NOT NULL,
    handle TEXT NOT NULL,
    layer TEXT NOT NULL,
    dimension_type TEXT NOT NULL,       -- e.g. 'LINEAR', 'ALIGNED', 'RADIUS'
    dimtype_code INTEGER,
    measurement REAL,
    defpoint_x REAL,
    defpoint_y REAL,
    defpoint_z REAL,
    defpoint2_x REAL,
    defpoint2_y REAL,
    defpoint2_z REAL,
    text_override TEXT,
    dimstyle TEXT,
    source_file TEXT,
    raw_json TEXT,
    UNIQUE(file_version_id, handle),
    FOREIGN KEY(file_version_id) REFERENCES file_versions(file_version_id)
);

-- Indexes for deterministic lookup queries
CREATE INDEX IF NOT EXISTS idx_cad_ent_fdh ON cad_entities(file_version_id, handle);
CREATE INDEX IF NOT EXISTS idx_cad_ent_ftl ON cad_entities(file_version_id, entity_type, layer);
CREATE INDEX IF NOT EXISTS idx_cad_lyr_fvn ON cad_layers(file_version_id, layer_name);
CREATE INDEX IF NOT EXISTS idx_cad_txt_fh ON cad_text_annotations(file_version_id, handle);
CREATE INDEX IF NOT EXISTS idx_cad_dim_fh ON cad_dimensions(file_version_id, handle);
CREATE INDEX IF NOT EXISTS idx_cad_blk_fvb ON cad_blocks(file_version_id, block_name);
CREATE INDEX IF NOT EXISTS idx_cad_dwg_fv ON cad_drawings(file_version_id);

-- Version Tracking
INSERT OR IGNORE INTO schema_version (version) VALUES (19);
