-- Migration 009: IFC Staging Tables
-- =======================================================================
-- Tables for staging raw IFC data.
-- Focuses on the "Spatial Hierarchy" and "Elements".
-- =======================================================================

CREATE TABLE IF NOT EXISTS ifc_projects (
    global_id TEXT PRIMARY KEY,     -- IfcGloballyUniqueId
    file_version_id TEXT NOT NULL,
    name TEXT,                      -- Name
    long_name TEXT,                 -- LongName
    phase TEXT,                     -- Phase
    
    FOREIGN KEY(file_version_id) REFERENCES file_versions(file_version_id)
);

CREATE TABLE IF NOT EXISTS ifc_spatial_structure (
    element_id TEXT PRIMARY KEY,    -- GlobalId
    file_version_id TEXT NOT NULL,
    ifc_project_id TEXT,
    
    parent_id TEXT,                 -- GlobalId of container (Site -> Project)
    entity_type TEXT,               -- IfcSite, IfcBuilding, IfcBuildingStorey, IfcSpace
    name TEXT,
    elevation REAL,
    
    raw_properties_json TEXT,       -- Dump of property sets
    
    FOREIGN KEY(file_version_id) REFERENCES file_versions(file_version_id)
);

CREATE TABLE IF NOT EXISTS ifc_elements (
    element_id TEXT PRIMARY KEY,    -- GlobalId
    file_version_id TEXT NOT NULL,
    spatial_container_id TEXT,      -- GlobalId of IfcBuildingStorey usually
    
    entity_type TEXT,               -- IfcWall, IfcDoor, etc.
    name TEXT,
    tag TEXT,                       -- Tag/Mark
    
    raw_properties_json TEXT,       -- Dump of property sets
    
    FOREIGN KEY(file_version_id) REFERENCES file_versions(file_version_id)
);

CREATE INDEX IF NOT EXISTS idx_ifc_spatial_parent ON ifc_spatial_structure(parent_id);
CREATE INDEX IF NOT EXISTS idx_ifc_elem_container ON ifc_elements(spatial_container_id);

INSERT OR IGNORE INTO schema_version (version) VALUES (9);
