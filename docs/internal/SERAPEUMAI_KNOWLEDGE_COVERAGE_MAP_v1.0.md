# SerapeumAI Knowledge Coverage Map v1.0

**Date:** 2026-09-02  
**Type:** Management Analysis — Baseline Assessment  
**Scope:** Current engineering knowledge representation and answer reliability  
**Constraint:** Read-only analysis. No code changes. No implementation proposals.

---

## 1. Engineer Question Catalogue

This section catalogs common AECO engineer questions and maps each to what knowledge is required, what SerapeumAI currently provides, and how confident an engineer can be in the answer.

### Q1: "What is the approved material or system for [component]?"

| Dimension | Detail |
|---|---|
| **Required knowledge** | Specification document text; approved submittal register status; material data sheets |
| **Required evidence sources** | PDF spec documents; Excel submittal registers; product data sheets (PDF/Word) |
| **Current SerapeumAI coverage** | ⚠️ Partial — PDF text extraction captures specification language; Excel registers capture submittal status rows. But no structured fact links "waterproofing" to a specific product. Semantic facts (`document.requirement`) are regex-derived, not structurally parsed. |
| **Confidence level** | **MEDIUM** — LLM can retrieve relevant text passages via FTS. Can cite the source document. Cannot assert approval status as governing truth without human certification. |
| **Gap** | No approval workflow tracking; no requirement-to-product traceability; regex-derived facts lack structural verification |

### Q2: "What changed between revision A and revision B?"

| Dimension | Detail |
|---|---|
| **Required knowledge** | Two file versions with content comparison; version metadata; change logs |
| **Required evidence sources** | PDF with version history; Word with tracked changes; document control system |
| **Current SerapeumAI coverage** | ❌ None — No document versioning exists. Each import creates a new `doc_id`. No diff mechanism. SHA-256 hashes exist per file_version but no comparison tooling. |
| **Confidence level** | **NONE** |
| **Gap** | No revision tracking; no content diff; no change-log integration |

### Q3: "Which documents are pending approval?"

| Dimension | Detail |
|---|---|
| **Required knowledge** | Submittal register with Status column; due dates; approval workflow state |
| **Required evidence sources** | Excel register; document control system |
| **Current SerapeumAI coverage** | ⚠️ Partial — Excel register extraction captures Status column values ("Submitted", "Under Review", "Approved", "Rejected"). Register rows persist to `register_rows`. But no VALIDATED facts are produced for register data, and no workflow state machine exists. |
| **Confidence level** | **LOW-MEDIUM** — Raw data is present. LLM can retrieve and summarize. But answers cannot be cited as authoritative because no certification path exists for register data. |
| **Gap** | No approval workflow; no due-date tracking; no overdue alerts; register facts remain CANDIDATE only |

### Q4: "What is the current critical path?"

| Dimension | Detail |
|---|---|
| **Required knowledge** | Schedule activities with float values; predecessor relations; baseline dates |
| **Required evidence sources** | P6 XER file |
| **Current SerapeumAI coverage** | ✅ Good — P6 extractor captures all activities, floats, and relations. ScheduleBuilder computes critical path membership. Facts are stored with provenance. Float normalization (hours÷8) verified by 8 tests. |
| **Confidence level** | **MEDIUM-HIGH** — Data is accurate and deterministic. But schedule facts are CANDIDATE (not VALIDATED), requiring human review before formal use. |
| **Gap** | No resource-constrained critical path; no baseline vs. current comparison; no what-if scenario support |

### Q5: "Where is this element located in the building?"

| Dimension | Detail |
|---|---|
| **Required knowledge** | BIM element GlobalId; spatial hierarchy (site→building→storey→room); coordinates |
| **Required evidence sources** | IFC model |
| **Current SerapeumAI coverage** | ⚠️ Partial — IFC extractor captures spatial containment (IfcRelContainedInSpatialStructure). Element names, types, and tags are stored. But geometry (coordinates, shapes) is lost. |
| **Confidence level** | **MEDIUM** — Can answer "which storey contains this wall?" if element is in the model. Cannot answer "what are the dimensions?" or show the element visually. |
| **Gap** | No geometry; no coordinate queries; no visual navigation; no element-measurements |

### Q6: "What quantity of [material] is required?"

| Dimension | Detail |
|---|---|
| **Required knowledge** | Bill of quantities; takeoff schedules; material specifications with quantities |
| **Required evidence sources** | Excel BOQ spreadsheets; PDF specification quantities; BIM element properties |
| **Current SerapeumAI coverage** | ⚠️ Limited — Excel registers capture tabular data as strings. IFC elements may contain quantity property sets (NetVolume, etc.). But no structured BOQ parsing exists. No quantity cross-reference between sources. |
| **Confidence level** | **LOW-MEDIUM** — Raw numbers may be extracted from Excel or IFC properties. No validation that quantities are consistent across documents. No audit trail for quantity takeoff methodology. |
| **Gap** | No BOQ parser; no quantity validation; no cross-document quantity reconciliation |

### Q7: "Is the installation compliant with the specification?"

| Dimension | Detail |
|---|---|
| **Required knowledge** | Specification requirements; inspection reports; non-conformance records; compliance checklists |
| **Required evidence sources** | PDF specs; field inspection reports (IR); NCRs; compliance checklists |
| **Current SerapeumAI coverage** | ❌ Partially blocked — Field/inspection data was previously fabricated (mock IR/NCR records). Now blocked by governance gate. PDF spec text is extractable. But no compliance checking engine exists. |
| **Confidence level** | **LOW** — Can retrieve specification text. Cannot perform automated compliance checking. Field inspection data is unavailable. |
| **Gap** | No compliance engine; no IR/NCR data; no specification-vs-installation comparison |

### Q8: "What are the project risks?"

| Dimension | Detail |
|---|---|
| **Required knowledge** | Risk registers; meeting minutes; delay analysis; change orders; weather data |
| **Required evidence sources** | Excel risk registers; Word meeting notes; P6 schedule delays; correspondence |
| **Current SerapeumAI coverage** | ❌ None — No risk register extraction. No meeting minute processing. No delay analysis engine. AI-generated risk summaries exist in `analysis` table but are probabilistic, not evidence-grounded. |
| **Confidence level** | **VERY LOW** — Any risk answer would be AI-synthesized from retrieved text, not derived from structured risk data. |
| **Gap** | No risk register; no meeting note extraction; no delay analysis; no risk quantification |

### Q9: "What is the project timeline and key milestones?"

| Dimension | Detail |
|---|---|
| **Required knowledge** | Schedule activities; milestone dates; baseline vs. current; progress percentages |
| **Required evidence sources** | P6 XER file |
| **Current SerapeumAI coverage** | ✅ Good — P6 extraction captures activity dates and WBS hierarchy. Milestone detection (zero-duration activities) works. Critical path computation is available. |
| **Confidence level** | **MEDIUM-HIGH** — Timeline data is accurate. Milestones are identified. Progress tracking requires manual status interpretation. |
| **Gap** | No progress percentage parsing; no milestone certification; no baseline comparison |

### Q10: "Which subcontractor is responsible for [work package]?"

| Dimension | Detail |
|---|---|
| **Required knowledge** | WBS codes; activity assignments; subcontractor registers; procurement records |
| **Required evidence sources** | P6 schedule (activity codes); Excel subcontractor register; Word scope documents |
| **Current SerapeumAI coverage** | ⚠️ Limited — P6 provides activity codes and names. Excel registers may contain subcontractor data if formatted as a standard register. But no cross-reference between schedule activities and subcontractor assignments exists. |
| **Confidence level** | **LOW-MEDIUM** — Can retrieve activity descriptions from P6. Can search register rows for subcontractor names. Cannot definitively link a work package to a specific subcontractor without manual correlation. |
| **Gap** | No subcontractor-register linkage; no WBS-to-subcontractor mapping; no procurement traceability |

### Q11: "Show me all fire-rated elements in the model"

| Dimension | Detail |
|---|---|
| **Required knowledge** | IFC element properties; FireRating property set; element types |
| **Required evidence sources** | IFC model |
| **Current SerapeumAI coverage** | ⚠️ Partial — IFC extractor captures property sets including FireRating. But no filtered query tool exists. The LLM cannot execute SQL-like filters on `ifc_elements.raw_properties_json`. |
| **Confidence level** | **VERY LOW** — Data exists in the database but is not accessible through the chat interface. |
| **Gap** | No property-filtered BIM query; no element-type filtering; no visualization |

### Q12: "What documents reference [specific topic]?"

| Dimension | Detail |
|---|---|
| **Required knowledge** | Document full-text content; document metadata; cross-references |
| **Required evidence sources** | PDFs, Word docs, PPTX files |
| **Current SerapeumAI coverage** | ✅ Good — FTS indexes exist on `documents.content_text` and `doc_blocks.text`. The LLM can search across all ingested documents. |
| **Confidence level** | **HIGH** — Text search is reliable. Results are grounded in extracted content with provenance. |
| **Gap** | No semantic search (keyword-only via FTS); no cross-document relationship mapping |

---

## 2. Knowledge Source Coverage Matrix

### 2.1 PDF Specifications / Reports

| Attribute | Assessment |
|---|---|
| **Available today?** | ✅ Yes — Primary supported format |
| **Information captured** | Full page text; heading hierarchy (blocks); document classification; page composition type; FTS index |
| **Information lost** | Table structure; image content; font styling; multi-column layout; vector graphics |
| **Engineer usefulness** | **HIGH** — Most AECO specifications are PDF. Text retrieval is reliable. FTS enables topic search. |
| **Confidence level** | **HIGH** — PRODUCTION maturity; deterministic extraction; governed by governance gate |

### 2.2 P6/XER Schedules

| Attribute | Assessment |
|---|---|
| **Available today?** | ✅ Yes — Fully supported |
| **Information captured** | Project metadata; WBS hierarchy; all activities with dates/status/float; all predecessors; critical path membership |
| **Information lost** | Resources; costs; calendars; non-TASK tables; multi-project context; baselines (unless separate file) |
| **Engineer usefulness** | **HIGH** — Critical path and schedule queries are well-supported. Deterministic float calculation. |
| **Confidence level** | **MEDIUM-HIGH** — PRODUCTION maturity; facts are CANDIDATE (requires human sign-off for formal use) |

### 2.3 IFC BIM Data

| Attribute | Assessment |
|---|---|
| **Available today?** | ⚠️ Conditionally — Requires `ifcopenshell` (optional dependency, not installed in current environment) |
| **Information captured** | Project metadata; spatial hierarchy (site→building→storey); element types/names/tags; property sets; connectivity relationships |
| **Information lost** | All geometry; coordinates; shapes; materials beyond basic properties; construction sequences; Clash detection data |
| **Engineer usefulness** | **MEDIUM** — Element identity and properties are useful. Spatial queries work. Geometry-dependent questions fail. |
| **Confidence level** | **MEDIUM** — VERIFIED maturity; CANDIDATE facts only; dependency absence causes honest zero-output |

### 2.4 DOCX Information Documents

| Attribute | Assessment |
|---|---|
| **Available today?** | ✅ Yes — Supported |
| **Information captured** | All paragraph text; table content (flattened); character count; file metadata |
| **Information lost** | Heading hierarchy levels; font styling; images; footnotes; headers/footers; table cell structure |
| **Engineer usefulness** | **MEDIUM** — Text content is retrievable. Structural questions (show headings, tables) cannot be answered. |
| **Confidence level** | **MEDIUM** — VERIFIED maturity; flattened output; no typed claims |

### 2.5 PPTX Presentations

| Attribute | Assessment |
|---|---|
| **Available today?** | ✅ Yes — Supported |
| **Information captured** | Slide titles; body text; speaker notes; table content (flattened) |
| **Information lost** | Slide layouts; positioning; chart data; animations; master slide content; image content |
| **Engineer usefulness** | **LOW-MEDIUM** — Text content retrievable slide-by-slide. Structural/layout questions impossible. |
| **Confidence level** | **MEDIUM** — VERIFIED maturity; flattened one-record-per-slide output |

### 2.6 XLSX Registers

| Attribute | Assessment |
|---|---|
| **Available today?** | ✅ Yes — Supported |
| **Information captured** | Cell values as strings; sheet names; row positions; header detection (keyword heuristic) |
| **Information lost** | Cell formatting; formulas; data validation; pivot tables; charts; multi-sheet relationships |
| **Engineer usefulness** | **MEDIUM** — Standard registers work well. Non-standard layouts may misidentify headers. No certification path. |
| **Confidence level** | **LOW-MEDIUM** — EXPERIMENTAL maturity; keyword header detection is heuristic; no validation rules for register data |

### 2.7 Drawings (DWG/DXF)

| Attribute | Assessment |
|---|---|
| **Available today?** | ❌ No — No V02 extractor exists |
| **Information captured** | Nothing |
| **Information lost** | All engineering information — geometry, annotations, dimensions, layers, blocks |
| **Engineer usefulness** | **NONE** — These are primary AECO deliverables and are completely invisible to the system |
| **Confidence level** | **NONE** |

### 2.8 Images / Scans

| Attribute | Assessment |
|---|---|
| **Available today?** | ❌ No functional extraction |
| **Information captured** | Nothing (ImageProcessor exists but untested; Tesseract unavailable) |
| **Information lost** | All visual information — site photos, scanned drawings, diagrams, charts |
| **Engineer usefulness** | **NONE** — Site photos and scanned drawings are critical evidence and are completely inaccessible |
| **Confidence level** | **NONE** |

### 2.9 Field Records (IR/NCR)

| Attribute | Assessment |
|---|---|
| **Available today?** | ⚠️ Blocked — Extractor is PLACEHOLDER, now in STAGING registry |
| **Information captured** | Nothing reliable (previously returned mock data based on filename markers) |
| **Information lost** | N/A — No real extraction occurs |
| **Engineer usefulness** | **NONE** — Even if registered, data would be fabricated. Governance gate prevents PLACEHOLDER output from reaching VALIDATED. |
| **Confidence level** | **NONE** |

### 2.10 Correspondence / Document Control

| Attribute | Assessment |
|---|---|
| **Available today?** | ⚠️ Partial — Email correspondences and transmittals are not processed |
| **Information captured** | Only if exported as PDF and ingested as document |
| **Information lost** | Email metadata (from, to, date, subject); thread relationships; attachment structure |
| **Engineer usefulness** | **LOW** — If correspondence is saved as PDF, text is searchable. Email-specific metadata is lost. |
| **Confidence level** | **MEDIUM** (for PDF-exported correspondence); **NONE** (for native email data) |

---

## 3. Database Knowledge Reality

### 3.1 What Knowledge Currently Exists

#### Layer 1: Document Content (Text-Only Knowledge)

| Knowledge Type | Storage | Quantity Estimate | Trust |
|---|---|---|---|
| Full-page PDF text | `pages.py_text`, `documents.content_text` | High (all ingested PDFs) | HIGH — deterministic extraction |
| Semantic text blocks | `doc_blocks.text` | Medium (structured by heading hierarchy) | HIGH — with provenance |
| FTS-searchable text | `documents_fts`, `doc_blocks_fts` | High (covers all above) | HIGH — indexed for search |
| Word/PPTX flat text | `pages.py_text` | Medium | MEDIUM — structure lost |

**Assessment:** Text knowledge from PDFs is robust. Office document text is captured but unstructured.

#### Layer 2: Structured Schedule Knowledge

| Knowledge Type | Storage | Quantity Estimate | Trust |
|---|---|---|---|
| Project metadata | `p6_projects` | Low (one per XER) | HIGH — FK-linked |
| WBS hierarchy | `p6_wbs` | Low-Medium | HIGH — parent-child FK |
| Activity details | `p6_activities` | Medium (5-500 per project) | HIGH — deterministic parse |
| Predecessor relations | `p6_relations` | Medium | HIGH — parallel relations preserved |
| Float/critical path facts | `facts` (CANDIDATE) | Medium | MEDIUM — heuristic computation |

**Assessment:** Schedule knowledge is the most complete structured domain. Critical path logic is documented and tested.

#### Layer 3: BIM Element Knowledge

| Knowledge Type | Storage | Quantity Estimate | Trust |
|---|---|---|---|
| Project metadata | `ifc_projects` | Low | HIGH (when ifcopenshell available) |
| Spatial hierarchy | `ifc_spatial_structure` | Low-Medium | HIGH — containment relationships |
| Element metadata | `ifc_elements` | Medium-High | MEDIUM — depends on dependency |
| Property sets | `ifc_elements.raw_properties_json` | Medium | MEDIUM — unstructured JSON |
| Connections | `links` (ifc.connection) | Low-Medium | MEDIUM — limited relation types |

**Assessment:** BIM element identity knowledge exists but geometry and detailed properties are lost. Dependency-dependent (ifcopenshell not installed).

#### Layer 4: Register / Tabular Knowledge

| Knowledge Type | Storage | Quantity Estimate | Trust |
|---|---|---|---|
| Excel rows | `register_rows.raw_data_json` | Low-Medium | MEDIUM — header detection heuristic |
| Sheet context | `register_rows.sheet_name` | Low | MEDIUM |
| Row position | `register_rows.row_index` | Low | MEDIUM |

**Assessment:** Tabular data is captured as JSON blobs. No schema enforcement. Header detection is the weakest point.

#### Layer 5: Fact Knowledge (Governing Truth)

| Knowledge Type | Storage | Quantity Estimate | Trust |
|---|---|---|---|
| VALIDATED facts | `facts` (status=VALIDATED) | Low (structural PDF facts only) | HIGH — gate-enforced |
| CANDIDATE facts | `facts` (status=CANDIDATE) | Medium | MEDIUM — unverified |
| HUMAN_CERTIFIED facts | `facts` (status=HUMAN_CERTIFIED) | Unknown (depends on usage) | HIGH — human-authored |
| Fact lineage | `fact_inputs` | Medium | HIGH — FK to file_versions |
| Snapshot bindings | `fact_snapshot_registry` | Low | MEDIUM — incomplete evidence binding |

**Assessment:** Governing truth is narrowly defined — currently limited to PDF structural facts (page_count, has_text, profile) and regex-derived semantic facts. Schedule, BIM, and register data produce only CANDIDATE facts.

#### Layer 6: Missing Knowledge Layers

| Knowledge Type | Expected Storage | Current Status |
|---|---|---|
| CAD drawing intelligence | `dxf_entities`, `dwg_layers` | ❌ Does not exist |
| Image/photograph content | `image_ocr_text`, `image_metadata` | ❌ Does not exist |
| Field inspection records | `field_requests` | ⚠️ Exists but blocked (PLACEHOLDER) |
| Risk register data | `risk_items`, `risk_categories` | ❌ Does not exist |
| Subcontractor assignments | `subcontractor_register` | ❌ Does not exist |
| Document revision history | `document_revisions` | ❌ Does not exist |
| Approval workflow state | `approval_workflows` | ❌ Does not exist |

---

## 4. Answer Reliability Assessment

### GREEN — Reliable Answers Possible

Questions the system can answer with confidence based on current evidence:

| Question | Why GREEN | Evidence Source |
|---|---|---|
| "How many pages does this PDF have?" | Deterministic count; VALIDATED fact | `document.page_count` |
| "Does this document have text content?" | Binary check; VALIDATED fact | `document.has_text` |
| "What is the document type classification?" | Metadata-based; VALIDATED fact | `document.profile` |
| "List all activities in the schedule" | Complete XER parse; FK-linked | `p6_activities` |
| "What is the float value for activity A-001?" | Deterministic extraction | `p6_activities.total_float` |
| "Which activities are on the critical path?" | Heuristic but verified logic | `schedule.critical_path_membership` |
| "Search for 'generator room' across all documents" | FTS-indexed text search | `documents_fts`, `doc_blocks_fts` |
| "What text is on page 3 of Mechanical-Scope.pdf?" | Page-level text retention | `pdf_pages.text_content` |
| "What is the WBS breakdown structure?" | Complete hierarchy preserved | `p6_wbs` |
| "What IFC elements exist in this model?" | When ifcopenshell available | `ifc_elements` |

### YELLOW — Partial Answers, Requires Caution

Questions where partial data exists but answers need verification:

| Question | Why YELLOW | Required Caution |
|---|---|---|
| "What is the current critical path?" | Data is accurate but CANDIDATE, not VALIDATED | Verify with project scheduler |
| "Which documents mention waterproofing?" | Text search works; no structured requirement fact | Cite source page; verify specification |
| "What is the approved waterproofing system?" | Spec text retrievable; no approval fact | Check submittal register manually |
| "What elements have FireRating 2HR?" | Properties in JSON but no filtered query | Manual JSON scan required |
| "Show me all submittals under review" | Register rows exist but no workflow state | Verify header detection was correct |
| "What is the material specification?" | Regex-derived `document.requirement` fact | Verify against original PDF clause |
| "How many walls are in the model?" | Element count from IFC properties | Depends on ifcopenshell availability |
| "What text is in this Word document?" | Flattened text available | Structure lost; no heading context |
| "Summarize this presentation" | Slide text available | No visual/layout context |

### RED — Insufficient Knowledge

Questions the system cannot reliably answer:

| Question | Why RED | Missing Knowledge |
|---|---|---|
| "What changed between rev A and rev B?" | No version comparison | No revision tracking |
| "Is this installation compliant?" | No compliance engine | No spec-vs-installation check |
| "What are the project risks?" | No risk register | No risk data |
| "What is the quantity of concrete required?" | No BOQ parser | No quantity extraction |
| "Show me the fire-rated walls on plan" | No geometry; no filtered query | No BIM visualization |
| "Which subcontractor does the HVAC work?" | No subcontractor mapping | No procurement linkage |
| "What do the site photos show?" | No image extraction | No vision capability |
| "What does this drawing depict?" | No CAD extraction | DWG/DXF unsupported |
| "Is there a conflict between discipline models?" | No clash detection | No multi-model comparison |
| "When will the project be completed?" | Schedule dates exist; no forecasting | No progress % parsing |
| "Show me all IRs for generator room" | Field data is mock/blocked | No real field extraction |
| "What is the cost variance?" | No cost data | No budget integration |

---

## 5. Missing Knowledge Impact

### Ranking by: Frequency × Decision Importance × Information Gap

| Rank | Missing Knowledge Source | Frequency of Use | Decision Impact | Missing Info % | Overall Impact |
|---|---|---|---|---|---|
| **1** | **CAD Drawings (DWG/DXF)** | VERY HIGH — Every AECO project produces drawings | CRITICAL — Design intent, dimensions, specifications | ~100% of drawing intelligence lost | 🔴 **CRITICAL** |
| **2** | **Site Images / Photographs** | HIGH — Daily site documentation | HIGH — Physical condition, progress verification, quality | ~100% of visual evidence lost | 🔴 **HIGH** |
| **3** | **Field Inspection Records (IR/NCR)** | MEDIUM-HIGH — Daily field operations | HIGH — Quality assurance, compliance verification | ~100% of field data lost (was fabricated) | 🔴 **HIGH** |
| **4** | **Document Revision Comparison** | MEDIUM — Regular revision cycles | MEDIUM — Change impact assessment, compliance tracking | ~100% of delta knowledge lost | 🟡 **HIGH** |
| **5** | **BIM Geometry & Coordinates** | MEDIUM — Design verification | MEDIUM — Spatial queries, clash detection, measurements | ~70% of BIM intelligence lost (identity only) | 🟡 **MEDIUM** |
| **6** | **Schedule Progress Data** | MEDIUM — Weekly reporting | MEDIUM — Delay analysis, lookahead planning | ~40% lost (dates exist; progress % missing) | 🟡 **MEDIUM** |
| **7** | **Excel Non-Standard Registers** | MEDIUM — Various project registers | LOW-MEDIUM — Custom formats break header detection | ~30% lost (standard registers work) | 🟢 **LOW-MEDIUM** |
| **8** | **Office Document Structure** | LOW-MEDIUM | LOW — Context loss but text is captured | ~50% of structure lost (hierarchy, tables) | 🟢 **LOW** |

### Top 3 Highest-Impact Gaps

1. **CAD Drawings** — This is the single largest gap. Engineering drawings are the primary deliverable in AECO. The system claims DXF/DWG support in documentation but has zero extraction capability. Engineers routinely ask drawing-related questions that the system cannot answer.

2. **Site Images** — Photographic evidence is irreplaceable for quality verification, progress tracking, and dispute resolution. No image extraction means the system cannot address any question about physical site conditions.

3. **Field Records** — The most dangerous gap because it was previously producing FAKE evidence. IRs and NCRs are critical for quality management. The governance gate now blocks this, but real capability doesn't exist yet.

---

## 6. Management Conclusion

### 6.1 What Can SerapeumAI Reliably Answer Today?

**Core reliable capabilities:**
- Document text search across all ingested PDFs, Word, and PPTX files
- PDF structural facts: page counts, text presence, document profile
- P6 schedule data: activities, WBS, floats, predecessors, critical path membership
- Basic IFC element inventory (when ifcopenshell is available)
- FTS-based topic search across all document text
- Fact-certified answers for STRUCTURAL document properties only

**Answer quality:** HIGH for text search and P6 schedule queries. MEDIUM for IFC and semantic document facts. LOW for anything requiring structure preservation or cross-domain correlation.

### 6.2 What Questions Remain Weak?

**Weak answer domains:**
- Any question about **drawing content** (dimensions, details, annotations) — ZERO coverage
- Any question about **site conditions** (photos, visual inspection) — ZERO coverage
- Any question about **compliance verification** (spec vs. installation) — NO engine
- Any question about **quantity takeoff** (BOQ, material quantities) — NO parser
- Any question about **cost/schedule variance** — NO financial data
- Any question about **revision changes** — NO version comparison
- Any question about **subcontractor responsibilities** — NO procurement linkage
- Any question requiring **multi-source correlation** (e.g., "does the schedule match the BIM?") — NO cross-domain reasoning

### 6.3 What Knowledge Is Missing?

**Completely absent knowledge sources:**
- CAD drawing intelligence (DWG/DXF) — **100% gap**
- Image/photograph content — **100% gap**
- Field inspection records (real) — **100% gap** (was mock, now blocked)
- Document revision deltas — **100% gap**
- Risk register data — **100% gap**
- Cost/BOQ data — **100% gap**
- Subcontractor assignments — **100% gap**

**Partially captured knowledge:**
- IFC geometry — **~70% gap** (identity preserved, form lost)
- Schedule progress — **~40% gap** (dates present, % complete missing)
- Office structure — **~50% gap** (text present, hierarchy lost)
- Excel semantics — **~30% gap** (values present, formula/validation lost)

### 6.4 Current Knowledge Coverage Limitation

**Overall assessment: SerapeumAI currently captures approximately 30-40% of AECO engineering knowledge.**

Breakdown:
- **Text-based knowledge (PDFs, specs):** ~60% coverage — strong foundation
- **Structured schedule data (P6):** ~80% coverage — best domain
- **BIM element identity (IFC):** ~20% coverage — dependency-limited
- **Office documents (Word, PPTX):** ~30% coverage — text only, structure lost
- **Tabular data (Excel):** ~50% coverage — heuristic header detection
- **Drawings (DWG/DXF):** 0% coverage — critical gap
- **Images/Photos:** 0% coverage — critical gap
- **Field records:** 0% coverage — was fabricated, now blocked
- **Risk/Cost/Procurement:** 0% coverage — not implemented

**The system is strongest as a document text search and P6 schedule viewer. It is weakest (non-existent) for the visual and graphical domains that engineers use daily.**

**The governance gate ensures that what IS trusted (VALIDATED facts) comes only from verified sources. But the volume of trusted knowledge is narrow — primarily PDF structural facts and regex-derived semantic facts.**

**Engineers should treat SerapeumAI as a supplementary research aid, not as a source of authoritative engineering truth — except for questions explicitly answered by VALIDATED or HUMAN_CERTIFIED facts.**

---

*This document reflects the current repository state as of 2026-09-02. It is a knowledge coverage baseline for management decision-making. No implementation recommendations are included.*
