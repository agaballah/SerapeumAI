# SerapeumAI Information Quality & Database Trust Map v1.0

**Date:** 2026-09-02  
**Type:** Management Analysis — Read-Only Assessment  
**Scope:** Current information quality in the database and trustworthiness of LLM-generated engineer answers  
**Constraint:** No code changes. No implementation proposals. Current reality only.

---

## 1. Information Quality Framework

This framework evaluates every piece of information that flows through SerapeumAI across five dimensions:

| Dimension | Definition | Measurement |
|---|---|---|
| **Completeness** | Did extraction capture all required information from the source? | Record count vs. expected records; missing fields; silent drops |
| **Accuracy** | Does extracted data match the source content? | Hash-stable output; known-string verification; deterministic results |
| **Structure Preservation** | Are tables, hierarchy, relationships, and context preserved? | Typed record types; provenance links; parent-child relationships intact |
| **Traceability** | Can the engineer return to the original evidence? | `fact_inputs` lineage; file_version_id; location_json; source_path |
| **Reliability** | Can this information safely influence engineering decisions? | Fact status (VALIDATED/HUMAN_CERTIFIED); source maturity; governance gate |

These dimensions are evaluated per domain below. A domain that scores low on any dimension cannot be considered trustworthy for engineering decisions.

---

## 2. Supported File Type Quality Matrix

### 2.1 PDF

| Attribute | Assessment |
|---|---|
| **File type** | `.pdf` |
| **Extractor** | `UniversalPdfExtractor` (V02) |
| **Maturity** | PRODUCTION |
| **Information stored** | Page text (`py_text`), page composition metadata (empty/vector/scanned/combined), document classification, semantic blocks with heading hierarchy, FTS index |
| **Information preserved** | Full text content per page; page-level structure; block-level heading hierarchy; file metadata (title, producer) |
| **Information lost** | Table structure (flattened to text); image content (OCR attempted but Tesseract unavailable); vector geometry; font styling; column layout |
| **Completeness** | **HIGH** — All text extracted per page; 14 tests verify routing, metadata, composition sniffing |
| **Accuracy** | **HIGH** — Deterministic; hash-stable; same input → identical output |
| **Structure preservation** | **MEDIUM** — Blocks preserve heading hierarchy (level, title, number); tables lose structure; images lose geometry |
| **Traceability** | **HIGH** — Each page linked to `file_version_id`; blocks linked to `doc_id` + `page_index`; FTS index available |
| **Reliability** | **HIGH** — PRODUCTION maturity; VALIDATED facts produced for structural items (page_count, has_text, profile); semantic facts VALIDATED via regex (accepted risk) |
| **LLM usage confidence** | **HIGH** — Chat queries about document content, page counts, scope items receive grounded answers from VALIDATED facts or retrieved text |
| **Risk note** | Semantic fact extraction uses regex heuristics — questions about "what is the requirement?" may produce plausible but unverified answers from `document.requirement` facts |

### 2.2 P6/XER

| Attribute | Assessment |
|---|---|
| **File type** | `.xer` |
| **Extractor** | `P6Extractor` (V02) |
| **Maturity** | PRODUCTION |
| **Information stored** | Project metadata, WBS hierarchy, activities (code, name, dates, status, float), relations (pred/succ, type, lag), all with FK-linked persistence |
| **Information preserved** | All TASK fields (8 columns); all TASKPRED relations; float values converted hours→days (÷8); critical path membership computed |
| **Information lost** | Resource assignments; cost data; calendar definitions; non-TASK tables (RESOURCE, ACTRESASSIGN, etc.); multi-project files |
| **Completeness** | **HIGH** — 8 tests verify float normalization, critical path, parallel relation preservation, unknown-float honesty |
| **Accuracy** | **HIGH** — Deterministic XER parse; negative float → critical; zero float → critical; bad float → None (no false criticality) |
| **Structure preservation** | **HIGH** — Full FK chain: p6_projects ← p6_wbs ← p6_activities ← p6_relations; predecessor/successor links preserved |
| **Traceability** | **HIGH** — Every activity/relation linked to `file_version_id`; fact_inputs links to source file |
| **Reliability** | **HIGH** — PRODUCTION maturity; ScheduleBuilder produces CANDIDATE facts (never VALIDATED for schedule data — requires human review) |
| **LLM usage confidence** | **MEDIUM-HIGH** — Chat can answer "what is the critical path?" but answers are CANDIDATE (non-governing). Engineer must verify against project manager. |
| **Risk note** | Float conversion uses ÷8 (P6 convention), not ÷24. Non-P6 users may misinterpret. Critical path is heuristic-based, not computed by a scheduler engine. |

### 2.3 IFC/BIM

| Attribute | Assessment |
|---|---|
| **File type** | `.ifc` |
| **Extractor** | `IFCExtractor` (V02) |
| **Maturity** | VERIFIED |
| **Information stored** | Project metadata, spatial structure hierarchy (site→building→storey), element metadata (type, name, tag, properties), connections (IfcRelConnectsElements) |
| **Information preserved** | Entity GlobalIds, types, names; property sets (fire rating, volume, etc.); spatial containment relationships |
| **Information lost** | Geometry (coordinates, shapes); IFC relationships beyond connectivity (IfcRelAssigns, IfcRelDefinesByProperties beyond basics); material specifications; construction sequences |
| **Completeness** | **MEDIUM** — 5 tests verify dependency honesty and contract types; no real .ifc fixture testing yet |
| **Accuracy** | **MEDIUM** — Depends on ifcopenshell parsing; fake-entity tests pass but real-model behavior unverified |
| **Structure preservation** | **MEDIUM** — Spatial hierarchy preserved; element properties preserved; connections preserved as generic links table |
| **Traceability** | **HIGH** — All records linked to `file_version_id`; element GlobalId preserved in `element_id` |
| **Reliability** | **MEDIUM** — VERIFIED maturity; BIMBuilder produces CANDIDATE facts only (not VALIDATED). Requires human certification for engineering use. |
| **LLM usage confidence** | **MEDIUM** — Chat can answer "what elements exist?" but element-level questions require CANDIDATE facts. No VALIDATED BIM facts currently produced. |
| **Risk note** | Missing optional dependency (`ifcopenshell`) causes honest failure — no fabricated BIM data. However, without the dependency, zero BIM information enters the database. |

### 2.4 Word (DOCX)

| Attribute | Assessment |
|---|---|
| **File type** | `.docx`, `.doc` |
| **Extractor** | `WordExtractor` (V02) |
| **Maturity** | VERIFIED |
| **Information stored** | Flattened text into `pages` table as `pdf_page` records; character count; file metadata |
| **Information preserved** | All paragraph text; table content (flattened with `[Table]` marker); inline image OCR attempts (requires Tesseract) |
| **Information lost** | Heading hierarchy (H1/H2 levels lost); font styling; image content (no OCR without Tesseract); table cell structure; footnotes; headers/footers |
| **Completeness** | **MEDIUM** — Text content captured; structure lost. 9 golden fixture tests verify behavior. |
| **Accuracy** | **HIGH** — python-docx reads paragraphs directly; deterministic output |
| **Structure preservation** | **LOW** — Entire document becomes one `pdf_page` record; no heading levels, no table structure, no spatial context |
| **Traceability** | **MEDIUM** — Linked to `file_version_id` via the pages table; but no row/column/paragraph-level granularity |
| **Reliability** | **MEDIUM** — VERIFIED maturity; produces only CANDIDATE output (flattened text goes through DocumentBuilder which creates VALIDATED structural facts only) |
| **LLM usage confidence** | **MEDIUM** — Chat can answer "what does the document say?" via text retrieval, but cannot distinguish headings, tables, or sections |
| **Risk note** | No typed Word records exist — information is indistinguishable from PDF text in the database. Engineers cannot query "show me all tables from this Word doc." |

### 2.5 PPTX

| Attribute | Assessment |
|---|---|
| **File type** | `.pptx` |
| **Extractor** | `PPTXExtractor` (V02) |
| **Maturity** | VERIFIED |
| **Information stored** | One `pdf_page` record per slide; slide text (title + body); speaker notes |
| **Information preserved** | Slide titles; body text; table content (flattened); speaker notes |
| **Information lost** | Slide layout; image content (no OCR without Tesseract); shape positions; animations; chart data; master slide content |
| **Completeness** | **MEDIUM** — One record per slide; all text captured per slide |
| **Accuracy** | **HIGH** — python-pptx reads shapes directly; deterministic |
| **Structure preservation** | **LOW** — Title/body distinction marked with `[Title]`/`[Body]` tags but not semantically structured |
| **Traceability** | **MEDIUM** — Page numbers preserved; linked to `file_version_id` |
| **Reliability** | **MEDIUM** — VERIFIED; only flattened output, no typed persistence |
| **LLM usage confidence** | **MEDIUM** — Chat can answer slide-content questions but not structural questions ("how many slides discuss HVAC?") |
| **Risk note** | Like Word, PPTX content is stored as flat text — no way to distinguish slide boundaries in queries except by page number. |

### 2.6 Excel Register (XLSX)

| Attribute | Assessment |
|---|---|
| **File type** | `.xlsx`, `.xls` |
| **Extractor** | `ExcelRegisterExtractor` (V02) |
| **Maturity** | EXPERIMENTAL |
| **Information stored** | `register_rows` table with `raw_data_json` containing key-value pairs per row; sheet name and row index in provenance |
| **Information preserved** | Cell values (all strings); header detection via keyword scoring; sheet name; row position |
| **Information lost** | Cell formatting; formulas (evaluated but not tracked as source); conditional formatting; data validation rules; pivot tables; charts |
| **Completeness** | **MEDIUM** — Keyword-based header detection works on standard registers; fails on non-standard layouts |
| **Accuracy** | **MEDIUM** — Values are accurate strings; header misidentification produces wrong column keys |
| **Structure preservation** | **LOW** — No column relationships preserved beyond key-value pairs; no row grouping; no multi-sheet aggregation |
| **Traceability** | **MEDIUM** — `sheet_name` and `row_index` in provenance; `file_version_id` link |
| **Reliability** | **LOW** — EXPERIMENTAL maturity; register builder produces CANDIDATE facts but no validation rules exist for register data |
| **LLM usage confidence** | **LOW-MEDIUM** — Chat can retrieve register rows but cannot validate them against engineering standards; no certification path exists |
| **Risk note** | Header detection heuristic may misidentify non-standard columns. No test coverage for header misidentification edge cases. |

### 2.7 DGN (MicroStation)

| Attribute | Assessment |
|---|---|
| **File type** | `.dgn` |
| **Extractor** | `DGNExtractor` (V02) |
| **Maturity** | EXPERIMENTAL |
| **Information stored** | Metadata (file name, size, creation date); XREF link list; converted DXF entity listing (via ODA) |
| **Information preserved** | File-level metadata; XREF references; entity type counts |
| **Information lost** | Geometry; layer information; drawing intelligence; annotation text; dimension data |
| **Completeness** | **LOW** — Only metadata extracted; no drawing content |
| **Accuracy** | **N/A** — Metadata is accurate when ODA converter present; silent failure when absent |
| **Structure preservation** | **LOW** — No spatial or hierarchical structure preserved |
| **Traceability** | **LOW** — Limited linkage to `file_version_id` |
| **Reliability** | **LOW** — EXPERIMENTAL; depends on optional ODA converter (not installed, not distributable) |
| **LLM usage confidence** | **VERY LOW** — Essentially no extractable engineering information from DGN files |
| **Risk note** | DGN files enter the pipeline but produce negligible evidence. Users may believe their CAD drawings are being processed when they are not. |

### 2.8 DXF/DWG (AutoCAD)

| Attribute | Assessment |
|---|---|
| **File type** | `.dxf`, `.dwg` |
| **Extractor** | **NONE** (V01 `CADProcessor` exists but untested; no V02 extractor) |
| **Maturity** | N/A — Not registered in EXTRACTORS or STAGING_EXTRACTORS |
| **Information stored** | Nothing — these files cannot enter the evidence pipeline |
| **Information preserved** | N/A |
| **Information lost** | All engineering information — entire file is inaccessible |
| **Completeness** | **ZERO** — No extraction capability exists |
| **Accuracy** | **N/A** |
| **Structure preservation** | **N/A** |
| **Traceability** | **N/A** |
| **Reliability** | **N/A** |
| **LLM usage confidence** | **NONE** — Zero information from these sources reaches the LLM |
| **Risk note** | This is the most significant information gap. AutoCAD drawings are the primary deliverable in AECO. The system claims to support DXF/DWG but provides zero extraction capability. |

### 2.9 Images

| Attribute | Assessment |
|---|---|
| **File type** | `.tiff`, `.bmp`, `.gif`, `.jpg`, `.png` |
| **Extractor** | **NONE** (V01 `ImageProcessor` exists but untested; no V02 extractor) |
| **Maturity** | N/A — No registered extractor |
| **Information stored** | Nothing — images cannot enter the evidence pipeline via standard path |
| **Information preserved** | N/A |
| **Information lost** | All visual engineering information — photos, scanned drawings, site images |
| **Completeness** | **ZERO** — No extraction capability exists |
| **Accuracy** | **N/A** |
| **Structure preservation** | **N/A** |
| **Traceability** | **N/A** |
| **Reliability** | **N/A** |
| **LLM usage confidence** | **NONE** |
| **Risk note** | Site photos and scanned drawings are critical AECO evidence. Their absence means the system cannot answer any question about physical site conditions. |

### 2.10 Field/VLM (IR/NCR)

| Attribute | Assessment |
|---|---|
| **File type** | `.pdf`, `.jpg`, `.png` |
| **Extractor** | `FieldExtractor` (V02) |
| **Maturity** | PLACEHOLDER |
| **Information stored** | `field_requests` table — but ONLY if mock data reaches it (now blocked by registry gate) |
| **Information preserved** | N/A — No real extraction occurs |
| **Information lost** | N/A |
| **Completeness** | **ZERO** — Extractor returns mock data based on filename markers (`"IR" in file_path`) |
| **Accuracy** | **ZERO** — Data is fabricated, not extracted |
| **Structure preservation** | **N/A** |
| **Traceability** | **N/A** — Provenance would claim real source but data is fake |
| **Reliability** | **CRITICAL** — Was producing VALIDATED facts from mock data before TASK-013. Now blocked by registry gate (PLACEHOLDER in STAGING_EXTRACTORS) and governance gate (demotes to CANDIDATE). |
| **LLM usage confidence** | **NONE** — Even CANDIDATE field facts would be fabricated |
| **Risk note** | This is the highest-risk domain. The extractor was actively producing TRUSTED facts from fabricated data before the authority gate was implemented. The gate prevents this now, but the underlying capability does not exist. |

---

## 3. Database Information Reality

### 3.1 What Actually Lives in the Database

The SQLite database contains the following information categories, ordered by trustworthiness:

#### Layer 1: Source Identity (High Trust)
| Table | Content | Trust Level |
|---|---|---|
| `projects` | Project name, root path, timestamps | HIGH — User-created, static |
| `file_registry` | File IDs, project associations, first-seen paths | HIGH — Auto-populated on ingest |
| `file_versions` | SHA-256 hashes, sizes, extensions, source paths | HIGH — Cryptographic identity |
| `documents` | File names, paths, hashes, total content text | MEDIUM — Text is extracted, may be incomplete |

#### Layer 2: Raw Evidence (Medium Trust)
| Table | Content | Trust Level |
|---|---|---|
| `pages` | Per-page text (PDF), OCR text, vision text, quality flags | MEDIUM — Text accurate, structure lost |
| `pdf_pages` | Extracted PDF page text + composition metadata | MEDIUM — Extraction is deterministic |
| `doc_blocks` | Semantic text blocks with heading hierarchy | MEDIUM — Block boundaries are heuristic |
| `doc_classifications` | Document type guesses with confidence | LOW — Classifier always returns "unknown" |
| `p6_projects`, `p6_wbs`, `p6_activities`, `p6_relations` | Schedule data with full FK relationships | HIGH — Deterministic XER parse |
| `ifc_projects`, `ifc_spatial_structure`, `ifc_elements`, `links` | BIM spatial hierarchy and element metadata | MEDIUM — Depends on ifcopenshell availability |
| `register_rows` | Excel register rows as JSON | MEDIUM — Header detection is heuristic |
| `field_requests` | Field inspection requests | **UNTRUSTED** — Mock data source, now blocked |
| `cad_entities` | DXF entity listings (from V01 processor) | LOW — Untested, no V02 wrapper |

#### Layer 3: Derived Facts (Variable Trust)
| Table | Content | Trust Level |
|---|---|---|
| `facts` | Structured assertions with status, confidence, method_id | VARIABLE — Depends on source |
| `fact_inputs` | Lineage linking facts to source file versions | HIGH — Explicit FK relationships |
| `fact_snapshots` | Point-in-time fact snapshots | HIGH — Immutable once created |
| `fact_snapshot_registry` | Snapshot-to-fact mappings | HIGH |
| `links` | Cross-domain relationships between entities | MEDIUM — Derived from extraction |

#### Layer 4: AI-Generated Content (Low Trust)
| Table | Content | Trust Level |
|---|---|---|
| `analysis` | AI analysis payloads | LOW — Probabilistic, non-deterministic |
| `compliance` | AI compliance checks | LOW |
| `analysis_results` | Structured AI analysis output | LOW |
| `vision_queue` | Pages queued for VLM processing | N/A — Processing status |
| `vlm_audit_trail` | VLM call logs | MEDIUM — Audit trail, not evidence |

#### Layer 5: Query Context ( ephemeral )
| Table | Content | Trust Level |
|---|---|---|
| `chat_history` | Conversation messages | N/A — Not evidence |
| `entity_nodes`, `entity_links` | Graph-layer entity representation | LOW — AI-derived topology |
| `data_conflicts` | Conflicts between native and VLM extraction | MEDIUM — Flags disagreements |
| `failed_extractions` | Extraction error logs | MEDIUM — Diagnostic only |

### 3.2 Lineage Completeness

| Path | Complete? | Gap |
|---|---|---|
| File → file_version → extraction_run → records → facts → fact_inputs → file_version | ✅ Yes | — |
| File → documents → pages → doc_blocks | ✅ Yes | — |
| Fact → fact_snapshot → project snapshot | ⚠️ Partial | Snapshots don't bind to evidence tables |
| Evidence page → fact input location | ⚠️ Partial | `location_json` exists but page-level precision varies |
| IFC element → global_id → links table | ✅ Yes | — |
| P6 activity → code → p6_activities table | ✅ Yes | — |

### 3.3 Orphaned Data Risk

The Current Reality Report identifies one critical structural risk:
- **`file_versions` has no FK to `documents`** — linked via `source_path` string matching
- **Evidence tables (`pages`, `doc_blocks`, `analysis`) are not linked to `fact_snapshots`**
- If a file is re-imported with a different path, lineage breaks

---

## 4. Engineer Question Test

### Q1: "What is the approved waterproofing system?"

| Dimension | Assessment |
|---|---|
| **Required source information** | Spec document (PDF) containing waterproofing specification; approved submittal (Excel register); material data sheets |
| **Whether current extraction captures it** | ⚠️ Partially — PDF text extraction captures spec language; Excel register may capture submittal approval status |
| **Whether database can support the answer** | ⚠️ The answer depends on document content retrieval. The LLM can retrieve PDF text via FTS or evidence retrieval. But no VALIDATED fact exists for "waterproofing system = X" unless manually certified. |
| **Confidence level** | **MEDIUM** — LLM can cite the document text, but cannot assert it as engineered truth without human certification |
| **Missing information** | No structured fact linking "waterproofing" to a specific product/spec. No approval workflow tracking. |

### Q2: "What is the current critical path?"

| Dimension | Assessment |
|---|---|
| **Required source information** | P6 XER file with current schedule data, float values, predecessor relations |
| **Whether current extraction captures it** | ✅ Yes — P6 extractor captures all activities, floats, and relations; ScheduleBuilder computes critical path |
| **Whether database can support the answer** | ⚠️ Yes, but with caveats — Critical path facts are CANDIDATE, not VALIDATED. The computation is deterministic but heuristic (hours÷8, negative float = critical). |
| **Confidence level** | **MEDIUM-HIGH** — The data is accurate and complete; the critical path logic is documented; but it lacks human sign-off |
| **Missing information** | No resource-constrained critical path; no what-if scenario comparison; no baseline vs. current comparison |

### Q3: "Which documents are pending approval?"

| Dimension | Assessment |
|---|---|
| **Required source information** | Submittal register (Excel) with status column; or document management system |
| **Whether current extraction captures it** | ⚠️ Partially — Excel register extraction works for standard registers; status column is preserved as string value |
| **Whether database can support the answer** | ⚠️ Register rows are stored as `register_rows` with JSON content, but no VALIDATED facts are produced for register data. The LLM would need to query the raw register table or rely on CANDIDATE facts. |
| **Confidence level** | **LOW-MEDIUM** — Data is present but not governed. An engineer cannot trust a chat answer about approval status without verifying against the source spreadsheet. |
| **Missing information** | No approval workflow state machine; no due-date tracking; no notification of overdue items; register builder produces only CANDIDATE facts |

### Q4: "What is the required material specification?"

| Dimension | Assessment |
|---|---|
| **Required source information** | Specification document (PDF) with material requirements; approved submittals |
| **Whether current extraction captures it** | ⚠️ Partially — PDF text extraction captures specification language; but semantic fact extraction (scope_item, requirement) uses regex heuristics, not structured parsing |
| **Whether database can support the answer** | ⚠️ The LLM can retrieve relevant text passages via FTS or evidence retrieval. DocumentBuilder produces VALIDATED `document.requirement` facts via regex — these are trusted by the governance gate but are regex-derived, not deterministic. |
| **Confidence level** | **MEDIUM** — Text is accurate; the requirement extraction is heuristic. An engineer should verify regex-derived requirements against the original PDF. |
| **Missing information** | No structured requirement parsing; no traceability from requirement to specific clause; no requirement version tracking |

### Q5: "What IFC element information exists?"

| Dimension | Assessment |
|---|---|
| **Required source information** | IFC model with element geometry, properties, spatial relationships |
| **Whether current extraction captures it** | ⚠️ Partially — ifcopenshell extraction captures element types, names, GlobalIds, property sets, and spatial containment. Geometry is NOT captured. |
| **Whether database can support the answer** | ⚠️ Element metadata is stored in `ifc_elements` with FK to `file_version_id`. But BIMBuilder produces only CANDIDATE facts. No VALIDATED BIM facts exist. |
| **Confidence level** | **MEDIUM-LOW** — Element identity and properties are accurate when ifcopenshell is available. But without the dependency (not installed in this environment), zero BIM data enters the database. |
| **Missing information** | No geometry; no construction sequencing; no quantity takeoff; no clash detection; no element relationships beyond connectivity |

### Q6: "Show me all fire-rated walls in the model"

| Dimension | Assessment |
|---|---|
| **Required source information** | IFC model with IfcWall elements having FireRating property |
| **Whether current extraction captures it** | ⚠️ Partially — IFC extractor captures property sets including FireRating. But no filtered query mechanism exists in the LLM tooling. |
| **Whether database can support the answer** | ❌ No — While `ifc_elements.raw_properties_json` contains FireRating data, there is no tool or fact type that enables filtered element queries by property value. The LLM cannot execute SQL-like filters on IFC data. |
| **Confidence level** | **VERY LOW** — The data exists in the database but is not accessible through the chat interface. |
| **Missing information** | No element-property query tool; no filtered BIM search; no visualization |

---

## 5. Information Loss Analysis

### 5.1 By Extraction Phase

| Source | Information Lost | Severity | Impact |
|---|---|---|---|
| **PDF → Text** | Table structure, column layouts, image geometry, font hierarchy, multi-column text order | 🟡 Medium | Tables become unstructured text; engineers cannot query "what does table 3 on page 5 say?" |
| **PDF → Blocks** | Short blocks (<50 chars) dropped; block-to-page mapping uses heuristic (first 100 chars match) | 🟡 Medium | Some information silently discarded; block boundaries are approximate |
| **P6/XER → Activities** | Resources, costs, calendars, non-TASK tables, multi-project context | 🟢 Low-Medium | Full schedule data not captured; resource allocation invisible |
| **IFC → Elements** | Geometry, coordinates, shapes, materials (beyond property sets), construction phasing | 🔴 High | Element identity preserved; element form and function lost |
| **Word → Pages** | Heading hierarchy, font styling, images, footnotes, headers/footers, table structure | 🔴 High | Document becomes flat text; structure invisible to query |
| **PPTX → Slides** | Layout, positioning, chart data, animations, master slide content, image content | 🔴 High | Presentation structure lost; only text remains |
| **Excel → Rows** | Cell formatting, formulas, data validation, pivot tables, charts, multi-sheet relationships | 🟡 Medium | Values preserved; context and calculation logic lost |
| **DGN → Metadata** | All drawing content; only XREF names and file metadata | 🔴 Critical | Zero engineering information from CAD drawings |
| **Images → None** | All visual information; OCR requires Tesseract (unavailable) | 🔴 Critical | Site photos, scanned drawings produce no evidence |
| **Field/VLM → Mock** | No real extraction; previously produced fabricated data | 🔴 Critical | Zero reliable field inspection data |
| **DXF/DWG → Nothing** | No extractor exists | 🔴 Critical | Primary AECO deliverable format is completely unsupported |

### 5.2 By Database Layer

| Layer | Information Lost | Root Cause |
|---|---|---|
| **Evidence → Facts** | Raw evidence detail collapsed into boolean/string facts | Builder abstraction loses nuance |
| **Facts → Chat** | Engineering judgment, context, caveats stripped | Fact model is binary (true/false/value) |
| **Snapshots → Evidence** | No binding between snapshot and source evidence | Schema gap identified in Current Reality Report |
| **LLM Context → Answer** | Quantitative precision lost in natural language | Synthesis is probabilistic |

---

## 6. LLM Trust Boundary

### 6.1 SAFE — Directly Supports Answers

Information at this level can be used by the LLM to generate answers with high confidence:

| Source | Reason |
|---|---|
| **PDF page text** (`pages.py_text`) | Deterministic extraction; FTS-indexed; byte-for-byte reproducible |
| **PDF block text** (`doc_blocks.text`) | Structured with heading hierarchy; provenance includes page index |
| **P6 activity data** (`p6_activities.*`) | Deterministic XER parse; FK-linked; float normalization verified |
| **P6 relation data** (`p6_relations.*`) | Predecessor/successor chains preserved; parallel relations not collapsed |
| **IFC element metadata** (`ifc_elements.*`) | When ifcopenshell available; GlobalId-traceable; property sets captured |
| **File identity** (`file_versions.sha256`) | Cryptographic certainty; immutable reference |

**Engineer can trust**: "Based on the PDF text for Mechanical-Scope.pdf page 3, the specification states..."

### 6.2 LIMITED — Requires Caution

Information at this level can support answers but requires the engineer to verify against source:

| Source | Risk | Mitigation |
|---|---|---|
| **Document semantic facts** (`document.requirement`, `document.scope_item`) | Regex-derived from PDF text; not structurally parsed | LLM citations should reference the source page; engineer confirms against PDF |
| **Schedule critical path** (`schedule.critical_path_membership`) | Heuristic computation (negative float = critical); not a scheduler engine | Engineer reviews float values; compares against Primavera P6 directly |
| **BIM element lists** (`bim.element_inventory_*`) | Missing geometry; only metadata captured | Engineer verifies element existence in Revit/Navisworks |
| **Register rows** (`register_rows.raw_data_json`) | Header detection is heuristic; non-standard registers misidentified | Engineer opens the Excel file to verify column mapping |
| **Word/PPTX text** (`pages` flattened) | Structure lost; no heading/table distinction | Engineer references original document for context |
| **FactQueryAPI retrived facts** | CANDIDATE facts are non-governing; VALIDATED facts may be regex-derived | Engineer checks fact status; VALIDATED facts are trusted; CANDIDATE facts are supporting only |

**Engineer can trust**: "The schedule shows A-001 is on the critical path with -1.0 days float, but verify against the P6 baseline."

### 6.3 UNSAFE — Must Not Be Used as Authoritative

Information at this level must not be cited as fact in engineering decisions:

| Source | Risk | Status |
|---|---|---|
| **Field/inspection data** (`field_requests`) | Previously mock data; now blocked by governance gate | PLACEHOLDER — zero reliable data |
| **Analysis results** (`analysis.payload_json`) | AI-generated probabilistic content | Not evidence; supplementary only |
| **Compliance checks** (`compliance.payload_json`) | AI-generated probabilistic content | Not evidence; supplementary only |
| **Entity graph** (`entity_nodes`, `entity_links`) | AI-derived topology; heuristic clustering | Not evidence; exploration aid only |
| **DGN/CAD data** | No extraction exists | Zero information available |
| **Image data** | No extraction exists | Zero information available |
| **DXF/DWG data** | No extractor exists | Zero information available |
| **Chat history** (`chat_history`) | Ephemeral; not persisted evidence | Not a data source |

**Engineer must NOT trust**: Any answer that cites field inspection results, AI analysis summaries, or CAD drawing content as authoritative evidence.

---

## 7. Management Conclusion

### 7.1 What Percentage of Project Knowledge Is Currently Represented?

**Estimated: 35-45% of accessible document knowledge; 5-10% of drawing/model knowledge.**

Breakdown:
- **PDF documents**: ~60% of knowledge represented (text captured, structure partially lost)
- **P6 schedules**: ~80% of schedule data represented (activities, floats, relations all captured)
- **IFC models**: ~20% of BIM data represented (identity and properties captured; geometry lost; dependency absent)
- **Office files (Word/PPTX)**: ~30% of content represented (text captured; structure lost)
- **Excel registers**: ~50% of tabular data represented (values captured; header detection heuristic)
- **CAD drawings (DGN/DXF/DWG)**: ~0% represented (no extraction)
- **Site images/photos**: ~0% represented (no extraction)
- **Field inspections**: ~0% represented (mock data, now blocked)

**Overall estimate: ~35%** of project knowledge that enters the system via supported formats is represented in the database. Of the total project knowledge (including unsupported formats like DWG and images), approximately **5-10%** is represented.

### 7.2 Which Domains Are Trustworthy Today?

**Trusted for engineering decisions (with citation):**

| Domain | Trust Level | Condition |
|---|---|---|
| **PDF text content** | HIGH | Cite source file and page; structural claims need human review |
| **P6 schedule data** | HIGH | Float values and critical path are accurate; human sign-off required for formal decisions |
| **IFC element metadata** | MEDIUM | Only when ifcopenshell is installed; geometry absent |

**Trusted for reference only (cannot govern decisions):**

| Domain | Trust Level | Condition |
|---|---|---|
| **Excel register data** | MEDIUM | Verify header detection; no certification path exists |
| **Word/PPTX text** | MEDIUM | Structure lost; treat as flat text reference |
| **Semantic document facts** | MEDIUM | Regex-derived; cite source page; verify against PDF |

**Not trusted:**

| Domain | Trust Level | Reason |
|---|---|---|
| **Field/inspection data** | NONE | Mock data; PLACEHOLDER extractor |
| **DGN drawings** | NONE | No extractor |
| **DXF/DWG drawings** | NONE | No extractor |
| **Images/photos** | NONE | No extractor; no Tesseract |
| **AI analysis** | NONE | Probabilistic, not evidential |

### 7.3 Which Domains Limit Engineer Confidence?

| Rank | Domain | Impact on Confidence | Root Cause |
|---|---|---|---|
| **1** | **DXF/DWG** | CRITICAL | Primary AECO deliverable is invisible |
| **2** | **Field/VLM** | CRITICAL | Was producing fabricated VALIDATED facts; now blocked but zero real capability |
| **3** | **Images** | HIGH | Site photos are irreplaceable evidence; completely absent |
| **4** | **IFC geometry** | MEDIUM | Element identity present; form and function absent |
| **5** | **Office structure** | MEDIUM | Text captured; hierarchy and tables lost |
| **6** | **Excel header detection** | LOW-MEDIUM | Works on standard registers; fails on custom layouts |
| **7** | **PDF table structure** | LOW-MEDIUM | Text extracted; column relationships lost |

### 7.4 Highest-Impact Information Quality Gaps

| Gap | Impact | Severity | Current State |
|---|---|---|---|
| **No CAD extraction (DXF/DWG)** | Engineers cannot query drawing content | 🔴 Critical | No V02 extractor; CADProcessor untested |
| **No image extraction** | Site photos and scanned drawings invisible | 🔴 Critical | ImageProcessor exists but untested; Tesseract unavailable |
| **Field data was fabricated** | Was producing TRUSTED facts from mock data | 🔴 Critical | Now blocked by governance gate; real VLM not implemented |
| **IFC geometry absent** | Cannot answer spatial/engineering questions about models | 🟡 High | Properties captured; coordinates and shapes lost |
| **No snapshot-evidence binding** | Cannot prove which evidence supported a certified fact | 🟡 High | Schema gap: evidence tables not linked to fact_snapshots |
| **file_versions disconnected from documents** | Lineage can break on path changes | 🟡 High | String-matching link instead of FK |
| **No approval workflow tracking** | Cannot answer "what is pending approval?" authoritatively | 🟡 High | Register data exists but no workflow state machine |
| **Office structure loss** | Cannot distinguish headings, tables, slides | 🟢 Medium | Flattened text only; accepted design trade-off |

### 7.5 Summary Statement

**Can engineers trust the database information used by the local LLM?**

**Yes, with documented conditions:**

1. **For PDF and P6 data**: Trust is HIGH. Extraction is deterministic, provenance is complete, and governance gates prevent unverified data from reaching VALIDATED status.

2. **For IFC, Excel, Word, PPTX**: Trust is MEDIUM. Data is accurate but incomplete — structure and geometry are lost. Engineers should verify important findings against source files.

3. **For CAD, images, and field inspections**: Trust is NONE. These domains either have no extraction or previously had fabricated data. The system cannot currently support engineering decisions based on these evidence types.

4. **For AI-generated content (analysis, compliance, entity graphs)**: Trust is NONE for evidence purposes. These are supplementary aids, not authoritative sources.

**The system's trustworthiness is proportional to the maturity of its extractors:**
- PRODUCTION extractors (PDF, P6) → trustworthy
- VERIFIED extractors (IFC, Word, PPTX) → conditionally trustworthy
- EXPERIMENTAL extractors (Excel Register, DGN) → reference only
- PLACEHOLDER extractors (Field/VLM) → do not use

**The governance gate implemented in TASK-013 ensures that only PRODUCTION and VERIFIED extractors can produce VALIDATED facts. This is the correct boundary. All other evidence should be treated as supporting context, not governing truth.**

---

*This document reflects the current repository state as of 2026-09-02. It is a quality assessment artifact, not an implementation plan. No code was modified.*
