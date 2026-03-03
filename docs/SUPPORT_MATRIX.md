# Technical Support Matrix

This document defines the technical capabilities of the Serapeum AI extraction engine across different file formats and document types.

## 🏗️ Core Engineering Formats

| Format | Category | Engine/Provider | Extracted Metadata | Strategy |
| :--- | :--- | :--- | :--- | :--- |
| **.pdf** | Drawings / Docs | pypdf / Tesseract / VLM | Text, Layout, Captions, Revisions | Native + OCR + Vision |
| **.dxf** | CAD | ezdxf | Layers, Entity Counts, Recursive XREFs | Object Graph Parsing |
| **.dgn** | CAD | ODA Converter | Converted to DXF for parsing | Automated Fallback |
| **.ifc** | BIM | ifcopenshell (Fallback Regex) | Projects, Sites, Buildings, Storeys | Spatial Hierarchy Extraction |
| **.xer** | Schedules | Custom Parser | Projects, WBS, Activities, Relationships | Structural XER Decoding |

## 📊 Project Controls & Registers

| Format | Category | Engine/Provider | Extracted Metadata | Strategy |
| :--- | :--- | :--- | :--- | :--- |
| **.xlsx / .xls** | Registers / Logs | Pandas | Sheet names, Header detection, Key-Value rows | Intelligent Tabular Sniffing |
| **.docx / .doc** | Specifications | python-docx | Headings, Paragraphs, Document Metadata | Semantic Text Extraction |
| **.pptx** | Presentations | python-pptx | Slide text, Titles, Shapes | Slide-by-slide extraction |

## 📱 Field Data & Compliance

| Format | Category | Engine/Provider | Extracted Metadata | Strategy |
| :--- | :--- | :--- | :--- | :--- |
| **PDF / Image** | IR / NCR / RFI | VLM (Vision Language Model) | Form IDs, Locations, Statuses, Dates | Specialized VLM Prompting |
| **Image** | Site Photos | VLM / Tesseract | Scene description, OCR Text, Metadata | Multi-modal Analysis |

---

## 🔍 Data Coverage Details

### 1. CAD Relationship Mapping (v0.2)
- **XREF Support**: Recursive scanning of external references.
- **Link Type**: `CAD_XREF` recorded in the system `links` table.

### 2. Schedule Truth Atoms
- **Activities**: ID, Name, Code, Start, Finish, Duration, Critical Path.
- **Lineage**: Mapped back to the source XER table (e.g., `TASK`, `TASKPRED`).

### 3. BIM Spatial Records
- **Entities**: IfcProject, IfcBuilding, IfcBuildingStorey.
- **Attributes**: GlobalId, Name, Type.

### 4. Smart Register Parsing
- **Header Sniffing**: Automatically matches common construction keywords (Status, Rev, Date) to infer column meanings.
- **Sheet Discovery**: Processes all tabs in a workbook by default.
