# Entity Schema for MCCC Project

## Overview

This document defines the entity types and structure for the MCCC (Mission Critical Construction Consulting) project entity graph. The entity graph connects documents, physical spaces, standards, and compliance elements across the project.

## Core Entity Types

### Spatial Hierarchy

- **project**: Top-level project entity
  - Example: "MCCC Riyadh Headquarters"
  - Attributes: project_code, location, client

- **site**: Physical site or campus
  - Example: "King Abdullah Financial District Site"
  - Attributes: address, area_sqm

- **building**: Building within a site
  - Example: "HQ Tower A", "Data Center Building"
  - Attributes: floors, height_m, occupancy_type

- **floor**: Floor level within a building
  - Example: "Level 3", "Basement B2"
  - Attributes: floor_number, area_sqm, use_type

- **space**: Room or defined space
  - Example: "Control Room 301", "Data Hall 1"
  - Attributes: room_number, area_sqm, occupancy_load

### Documentation

- **drawing**: CAD drawing or design document
  - Example: "A-101 Floor Plan", "E-201 Power Distribution"
  - Attributes: drawing_number, discipline, revision, date

- **sheet**: Individual sheet within a drawing set
  - Example: "Sheet 5 of 12"
  - Attributes: sheet_number, total_sheets

- **detail**: Detail callout or enlarged view
  - Example: "Detail 3/A-101"
  - Attributes: detail_mark, parent_sheet

### Contractual

- **contract**: Contract document or agreement
  - Example: "Main Construction Contract", "MEP Subcontract"
  - Attributes: contract_number, value, parties

- **spec_section**: Specification section
  - Example: "Division 26 - Electrical"
  - Attributes: section_number, title

- **schedule**: Construction or delivery schedule
  - Example: "Master Project Schedule", "MEP Submittal Schedule"
  - Attributes: schedule_type, start_date, end_date

- **attachment**: Supporting attachment or exhibit
  - Example: "Equipment List", "Vendor Specifications"
  - Attributes: attachment_number, file_type

### Standards & Compliance

- **standard**: Official standard or code document
  - Example: "Saudi Building Code (SBC)", "NFPA 70"
  - Attributes: standard_code, version, jurisdiction

- **standard_clause**: Specific clause or section within a standard
  - Example: "SBC 10.3.2", "IBC Section 1007"
  - Attributes: clause_number, title, category

- **standard_reference**: Reference to a standard found in project documents
  - Example: "As per TMSS-01", "Compliant with TESP-11921"
  - Attributes: ref_text, standard_code, clause_hint

- **code**: Building or safety code reference
  - Example: "IBC egress requirements", "SBC fire protection"
  - Attributes: code_type, section

## Relationship Types

### Spatial Relationships

- **part_of**: Child is part of parent
  - Example: space → floor, floor → building, building → site

- **located_in**: Entity is physically located in another
  - Example: equipment → space

### Reference Relationships

- **references**: Document references another document or standard
  - Example: drawing → specification, contract → standard

- **derived_from**: Entity is derived from another
  - Example: detail → sheet

- **supersedes**: Newer entity replaces older one
  - Example: drawing_rev_B → drawing_rev_A

### Compliance Relationships

- **complies_with**: Entity meets standard requirements
  - Example: design → standard_clause

- **conflicts_with**: Entities have conflicting information
  - Example: drawing_A → drawing_B (dimension mismatch)

- **requires**: Entity requires another for compliance
  - Example: space → fire_rating

## Entity JSON Structure

```json
{
  "type": "building",
  "value": "HQ Tower A",
  "id_hint": "Bldg-A",
  "doc_id": "doc-123",
  "confidence": 0.9,
  "extra": {
    "floors": 12,
    "height_m": 48,
    "occupancy_type": "Business"
  }
}
```

## Standard Reference Extraction

### TMSS (Telecom Modular Support System)
- Pattern: `TMSS-\d+`
- Example: "TMSS-01", "TMSS-15"

### TESP (Telecom Equipment Support Program)
- Pattern: `TESP-\d{5}`
- Example: "TESP-11921", "TESP-12001"

### TESB (Telecom Equipment Support Bulletin)
- Pattern: `TESB-\d+`
- Example: "TESB-100"

### Saudi Building Code (SBC)
- Pattern: `SBC\s+\d+\.\d+` or `SBC\s+Section\s+\d+`
- Example: "SBC 10.3.2", "SBC Section 1007"

### International Building Code (IBC)
- Pattern: `IBC\s+\d{4}` or `IBC\s+Section\s+\d+`
- Example: "IBC 2021", "IBC Section 1007"

### NFPA (National Fire Protection Association)
- Pattern: `NFPA\s+\d+`
- Example: "NFPA 70", "NFPA 13"

## Usage in Analysis Engine

The analysis engine extracts entities and relationships from documents, storing them in:
- `entity_nodes` table: Individual entity instances
- `entity_links` table: Relationships between entities
- `doc_references` table: Document-to-document references

Cross-document linking merges duplicate entities and identifies conflicts.
