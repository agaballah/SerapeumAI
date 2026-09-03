# SerapeumAI Knowledge Expansion Roadmap v1.0

**Date:** 2026-09-02  
**Type:** Strategic Management Analysis — Value-Based Prioritization  
**Scope:** Which missing knowledge sources will create the highest improvement in engineer answer reliability  
**Constraint:** Read-only strategic analysis. No code changes. No implementation plan. No technology selection.

---

## 1. Current Knowledge Coverage Baseline

### 1.1 Reliable Knowledge (GREEN Zone)

Knowledge that currently produces trustworthy answers for engineers:

| Knowledge Type | Source | Maturity | Confidence | Typical Use |
|---|---|---|---|---|
| **PDF full-text content** | UniversalPdfExtractor | PRODUCTION | HIGH | Document search, specification lookup, text retrieval |
| **PDF structural facts** | DocumentBuilder | PRODUCTION | HIGH | Page counts, document profiles, scope item detection |
| **P6 schedule data** | P6Extractor + ScheduleBuilder | PRODUCTION | MEDIUM-HIGH | Activity lists, float values, critical path membership, WBS hierarchy |
| **FTS document search** | documents_fts, doc_blocks_fts | N/A | HIGH | Cross-document topic search, keyword retrieval |

**Coverage estimate:** ~35% of ingested project knowledge is represented as reliable text or structured schedule data.

### 1.2 Partial Knowledge (YELLOW Zone)

Knowledge that exists in the database but requires verification before engineering use:

| Knowledge Type | Source | Maturity | Limitation |
|---|---|---|---|
| **IFC element metadata** | IFCExtractor | VERIFIED | Geometry lost; requires optional ifcopenshell dependency; CANDIDATE facts only |
| **Word/PPTX text** | Word/PPTX Extractors | VERIFIED | Flattened to single records; heading hierarchy and table structure lost |
| **Excel register rows** | ExcelRegisterExtractor | EXPERIMENTAL | Keyword-based header detection is heuristic; non-standard registers misidentified |
| **DGN metadata** | DGNExtractor | EXPERIMENTAL | XREF names only; ODA converter dependency; negligible engineering content |
| **Semantic document facts** | DocumentBuilder regex | PRODUCTION (accepted risk) | Regex-derived requirements/scope items — plausible but not structurally verified |

**Coverage estimate:** ~15% additional knowledge available with caveats. Total partial knowledge ~50%.

### 1.3 Missing Knowledge (RED Zone)

Knowledge sources with zero or blocked coverage:

| Knowledge Type | Impact | Gap |
|---|---|---|
| **CAD drawings (DWG/DXF)** | 🔴 Critical — primary AECO deliverable | Zero extraction capability |
| **Site images / photographs** | 🔴 High — irreplaceable visual evidence | Zero extraction; Tesseract unavailable |
| **Field inspection records** | 🔴 High — quality assurance data | Was fabricated mock data; now blocked |
| **Document revision comparison** | 🟡 Medium — change tracking | No versioning or diff mechanism |
| **BIM geometry & coordinates** | 🟡 Medium — spatial queries | Identity preserved; form lost |
| **Risk register data** | 🟡 Medium — project risk awareness | No extraction; no risk domain |
| **Cost / BOQ data** | 🟡 Medium — quantity and budget questions | No parser; no financial domain |
| **Subcontractor assignments** | 🟢 Low-Medium — organizational context | No procurement linkage |
| **Approval workflow state** | 🟢 Low-Medium — process tracking | No workflow engine |

**Coverage estimate:** ~50-65% of total engineering knowledge is missing or blocked.

### 1.4 Current Engineer Confidence Limitations

Based on the Knowledge Coverage Map and Database Trust Map:

- Engineers can **reliably answer** 12-15 of 40 common AECO questions using current data
- Engineers must **verify manually** for another 15-20 questions (partial data available)
- Engineers **cannot answer** 10-15 questions due to missing knowledge sources
- The single biggest confidence killer: **engineers cannot ask about drawings or site photos**, which are their primary daily evidence sources

---

## 2. Engineer Value Analysis

Each missing knowledge area is evaluated by: (a) how many engineer questions it affects, (b) how frequently those questions arise in AECO practice, (c) how important the decisions are, (d) the current confidence gap, and (e) expected improvement in answer quality.

### A. CAD Drawing Intelligence (DWG/DXF)

| Attribute | Assessment |
|---|---|
| **Engineer questions affected** | "What are the dimensions?" "Show me the detailed connection" "Where does this pipe route?" "What is the rebar spacing?" "Does this match the architectural drawing?" "What is the element size at this location?" |
| **Frequency of use in AECO** | **VERY HIGH** — Every AECO professional references drawings daily. Drawings are the primary communication medium between disciplines. |
| **Decision importance** | **CRITICAL** — Construction decisions, clash detection, quantity takeoff, compliance verification all depend on drawing content. Wrong drawing interpretation can cause rework costing tens of thousands. |
| **Current confidence gap** | **COMPLETE — 0%** | Engineers have zero ability to query drawing content. Any drawing-related question returns no information. |
| **Expected improvement in answer quality** | **TRANSFORMATIVE** — Adding drawing intelligence would convert SerapeumAI from a document search tool into a genuine engineering assistant. Drawing queries are the #1 request from AECO users. |

**Value rating: 🔴 CRITICAL — Highest impact knowledge gap**

### B. Visual Evidence (Images / Scanned Drawings)

| Attribute | Assessment |
|---|---|
| **Engineer questions affected** | "What does the site look like right now?" "Is the waterproofing installed correctly?" "Show me the as-built condition" "Compare this photo with the spec requirement" "What damage is visible?" |
| **Frequency of use in AECO** | **HIGH** — Site photos are taken daily on construction projects. Scanned drawings are common historical references. Visual evidence is irreplaceable for quality verification. |
| **Decision importance** | **HIGH** — Quality acceptance, progress verification, dispute resolution, safety inspection all rely on visual evidence. |
| **Current confidence gap** | **COMPLETE — 0%** | No image extraction exists. Site photos are completely invisible to the system. |
| **Expected improvement in answer quality** | **VERY HIGH** — Visual evidence bridges the gap between digital models and physical reality. Without it, the system cannot support quality assurance or progress tracking questions. |

**Value rating: 🔴 HIGH — Second highest impact knowledge gap**

### C. Field Inspection Information (IR / NCR)

| Attribute | Assessment |
|---|---|
| **Engineer questions affected** | "Are there any open NCRs for concrete work?" "What IRs are pending for the generator room?" "Has this inspection been completed?" "What was the finding on the last site visit?" |
| **Frequency of use in AECO** | **MEDIUM-HIGH** — Field inspections occur regularly. IRs and NCRs are formal quality records that drive corrective actions. |
| **Decision importance** | **HIGH** — Unresolved NCRs can block construction progress. Inspection status affects scheduling and procurement. Quality hold points depend on field record completion. |
| **Current confidence gap** | **COMPLETE — 0%** (was fabricated, now blocked) | Previously produced FAKE inspection records. Now blocked by governance gate. Zero real field data capability. |
| **Expected improvement in answer quality** | **HIGH** — Real field inspection data would enable quality assurance queries. However, this requires a reliable VLM or structured form extraction — not trivial. |

**Value rating: 🟡 HIGH — High impact but complex to implement correctly**

### D. BIM Semantic Understanding

| Attribute | Assessment |
|---|---|
| **Engineer questions affected** | "Find all fire-rated walls" "How many outlets are in this room?" "What is the volume of this space?" "Show me all ductwork on level 3" "Which elements connect to this column?" |
| **Frequency of use in AECO** | **MEDIUM** — BIM queries are common during design review and coordination. Quantity takeoff and clash detection rely on BIM data. |
| **Decision importance** | **MEDIUM-HIGH** — BIM queries support design decisions, quantity validation, and coordination. Errors in BIM interpretation can cause construction conflicts. |
| **Current confidence gap** | **PARTIAL — ~70% gap** | Element identity and properties exist. Geometry, coordinates, and spatial relationships are lost. No filtered query capability. |
| **Expected improvement in answer quality** | **MEDIUM-HIGH** — Adding geometry and property-filtered queries would unlock BIM as a primary evidence source. The foundation (element identity) is already in place. |

**Value rating: 🟡 MEDIUM-HIGH — Foundation exists; enhancement would be high-value**

### E. Document Control / Workflow Intelligence

| Attribute | Assessment |
|---|---|
| **Engineer questions affected** | "Which documents are pending approval?" "What changed in the last revision?" "Is this drawing still valid?" "Who approved this specification?" "What is the submittal status?" |
| **Frequency of use in AECO** | **MEDIUM** — Document control questions arise regularly in coordination meetings and submittal reviews. Revision tracking is essential for compliance. |
| **Decision importance** | **MEDIUM** — Using an outdated drawing or unapproved spec can cause rework. Approval status affects construction sequencing. |
| **Current confidence gap** | **PARTIAL — Data partially exists** | Submittal register rows exist in Excel. But no workflow state, no revision history, no approval chain. |
| **Expected improvement in answer quality** | **MEDIUM** — Adding revision comparison and workflow state would transform document queries from static retrieval to dynamic status awareness. |

**Value rating: 🟢 MEDIUM — Useful but lower urgency than CAD/visual gaps**

### F. Structured Table and Schedule Preservation

| Attribute | Assessment |
|---|---|
| **Engineer questions affected** | "Show me the table from page 5" "What are the column headers in this register?" "Compare these two schedules" "Extract the BOQ from this spreadsheet" |
| **Frequency of use in AECO** | **MEDIUM** — Tables appear in specs, registers, BOQs, and schedules. Engineers frequently need to reference tabular data. |
| **Decision importance** | **LOW-MEDIUM** — Table structure loss degrades answer quality but rarely causes wrong decisions. Values are usually still retrievable as flat text. |
| **Current confidence gap** | **PARTIAL — ~50% gap** | Cell values are captured. Structure (rows, columns, merged cells, formulas) is lost. Header detection is heuristic. |
| **Expected improvement in answer quality** | **LOW-MEDIUM** — Table structure preservation would improve accuracy of register and BOQ queries. But the value is incremental rather than transformative. |

**Value rating: 🟢 LOW-MEDIUM — Incremental improvement, not a gap-filler**

---

## 3. Knowledge Expansion Priority Matrix

Ranked by: (improvement to engineer answers × frequency of engineer use × importance of affected decisions). Implementation difficulty is explicitly EXCLUDED from ranking.

| Rank | Knowledge Area | Answer Improvement | Frequency | Decision Impact | Overall Priority | Current State |
|---|---|---|---|---|---|---|
| **1** | **CAD Drawing Intelligence** | Transformative | Very High | Critical | 🔴 **P1 — Must Have** | 0% coverage |
| **2** | **Visual Evidence (Images/Scans)** | Very High | High | High | 🔴 **P1 — Must Have** | 0% coverage |
| **3** | **BIM Semantic Enhancement** | High | Medium | Medium-High | 🟡 **P2 — Should Have** | 30% coverage (identity only) |
| **4** | **Field Inspection Information** | High | Medium-High | High | 🟡 **P2 — Should Have** | 0% coverage (blocked) |
| **5** | **Document Control / Workflow** | Medium | Medium | Medium | 🟢 **P3 — Nice to Have** | 40% coverage (data only) |
| **6** | **Structured Table Preservation** | Low-Medium | Medium | Low-Medium | 🟢 **P3 — Nice to Have** | 50% coverage (values only) |

### Priority Definitions

| Priority | Meaning | Decision Rule |
|---|---|---|
| **P1 — Must Have** | Without this, SerapeumAI cannot serve core AECO engineering workflows. The system is fundamentally incomplete for its target users. | Must be addressed before the system can be considered production-ready for engineering teams. |
| **P2 — Should Have** | Significant value addition. Addresses real engineer needs. Improves answer reliability substantially. | Should be addressed in the next development cycle after P1 gaps are closed. |
| **P3 — Nice to Have** | Incremental quality improvement. Useful but not decisive for engineering adoption. | Can be deferred. Address only if resources permit after P1 and P2 are complete. |

---

## 4. Target Knowledge Model

### 4.1 Current State

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Source File  │────▶│  Text/Record  │────▶│  Database    │────▶│  LLM Query   │
│  (PDF/XER/…)  │     │  (flattened)  │     │  (evidence)  │     │  (answer)    │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                                                    │
                     ┌──────────────────────────────┘
                     ▼
            ┌─────────────────┐
            │  Trusted Facts  │  ← Only VALIDATED/HUMAN_CERTIFIED
            │  (narrow scope) │     govern chat answers
            └─────────────────┘
```

**Limitations of current model:**
- Extraction is format-focused, not knowledge-focused
- Structure is lost during flattening
- No cross-source correlation
- No spatial or visual reasoning
- Governance gate is narrow (only PDF structural facts are VALIDATED)

### 4.2 Desired Future State

```
┌──────────────┐     ┌──────────────────────┐     ┌──────────────┐     ┌──────────────┐
│  Source File  │────▶│  Structured Knowledge │────▶│  Evidence     │────▶│  LLM Query   │
│  (all types)  │     │  (preserved context)  │     │  Graph        │     │  (grounded)  │
└──────────────┘     └──────────────────────┘     └──────────────┘     └──────────────┘
                                        │                              │
                    ┌───────────────────┼──────────────────┐           │
                    ▼                   ▼                  ▼           ▼
            ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
            │  Text Facts  │  │  Spatial     │  │  Visual      │  │  Process     │
            │  (spec, doc) │  │  Facts       │  │  Facts       │  │  Facts       │
            │              │  │  (BIM, drawing│  │  (photo,     │  │  (workflow,  │
            │              │  │   geometry)  │  │   scan)      │  │   revision)  │
            └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘
                    │                   │                  │               │
                    └───────────────────┴──────────────────┴───────────────┘
                                            │
                                            ▼
                                   ┌─────────────────┐
                                   │  Trusted Facts  │
                                   │  (multi-domain) │
                                   │  cross-referenced│
                                   └─────────────────┘
```

**Key differences:**
1. **Extraction preserves structure** — tables remain tabular, drawings retain geometry, images retain visual content
2. **Multiple knowledge types** — text facts, spatial facts, visual facts, process facts each have their own governance
3. **Cross-source correlation** — a drawing can be linked to its spec, a photo can be linked to its location in the model
4. **Domain-aware trust** — different fact types have appropriate maturity levels based on extraction reliability

---

## 5. Management Decision Points

### 5.1 What Must Be Solved Before SerapeumAI Can Be Considered a Complete Engineering Assistant?

| Requirement | Rationale | Status |
|---|---|---|
| **CAD drawing intelligence (P1)** | Engineers cannot function without querying drawing content. This is the #1 daily workflow. | ❌ Not started — zero capability |
| **Visual evidence capture (P1)** | Site photos and scanned drawings are irreplaceable evidence. Their absence creates a trust deficit. | ❌ Not started — zero capability |
| **Governance consistency across domains** | Current gate only protects PDF/P6 paths. New domains need the same maturity gate. | ⚠️ Partial — framework exists, needs extension |

**Assessment:** Two critical gaps (CAD + visual) must be addressed before the system can credibly serve AECO engineering teams. Without these, the system is a document search tool, not an engineering assistant.

### 5.2 What Can Remain Secondary?

| Area | Rationale |
|---|---|
| **Structured table preservation (P3)** | Values are currently captured. Structure loss is inconvenient but rarely causes wrong decisions. |
| **Document control workflow (P3)** | Useful for process tracking but doesn't affect engineering correctness. Can be added later. |
| **Excel header detection improvement** | Incremental quality improvement. Standard registers work adequately today. |

### 5.3 What Requires Additional Investigation Before Decisions?

| Area | Unknown | Why It Needs Investigation |
|---|---|---|
| **BIM semantic enhancement (P2)** | How much geometry can be extracted with acceptable performance? | Geometry extraction may be computationally expensive. Need to understand trade-off between completeness and speed. |
| **Field inspection information (P2)** | What extraction method produces reliable IR/NCR data? | Was previously fabricated. Need to determine if VLM, structured forms, or hybrid approach is viable. |
| **Image OCR quality** | Can Tesseract or alternative produce usable text from site photos? | Current Tesseract availability unknown. Alternative approaches (commercial OCR, cloud vision APIs) may be needed. |
| **DWG vs DXF support** | Does DWG require proprietary SDK while DXF is open? | This affects licensing and deployment constraints significantly. |

---

## 6. Conclusion

### 6.1 Single Highest-Value Knowledge Gap

**CAD Drawing Intelligence (DWG/DXF).**

This is the single most impactful knowledge gap because:
1. Drawings are the **primary AECO deliverable** — every project produces them, every discipline references them
2. Engineer questions about drawings are the **most frequent** in daily practice
3. Decision importance is **critical** — wrong drawing interpretation causes rework and safety issues
4. Current coverage is **zero** — the system claims to support DXF but has no extractor
5. The gap is **visible and felt** — engineers will immediately notice they cannot ask about drawings

No other gap has this combination of frequency, importance, and zero coverage.

### 6.2 What Should NOT Be Developed Yet?

**Structured table preservation and document workflow intelligence (P3 priorities).**

These are incremental improvements that do not address the fundamental completeness gap. The system already captures cell values and document text. Adding structure or workflow state improves convenience but does not unlock new question domains. Resources should focus on P1 and P2 gaps first.

Additionally, **field inspection information should not be developed until the extraction method is validated**. The previous PLACEHOLDER approach produced fabricated evidence — this must not recur. Any new field data implementation must pass the Evidence Quality Contract before being registered.

### 6.3 What Should Be Investigated Next?

**Two parallel investigations:**

1. **CAD extraction feasibility study** — Determine whether open-source DXF parsing (ezdxf) can produce useful engineering knowledge (layer info, entity geometry, annotations). Assess whether DWG requires a proprietary solution. Estimate the knowledge density achievable from DXF files.

2. **Visual evidence extraction assessment** — Determine whether Tesseract (or alternative OCR) can produce usable text from site photos and scanned drawings. Evaluate the quality threshold required for engineering trust. Assess whether image metadata (EXIF, GPS) adds value.

These investigations should answer: **Can we extract actionable engineering knowledge from drawings and images at a quality level that passes the Evidence Quality Contract?** The answer determines whether P1 gaps can be closed and at what scale.

---

### Summary Statement

SerapeumAI currently provides **reliable text search and schedule viewing** but is **fundamentally incomplete as an engineering assistant** because it cannot access drawings or visual evidence — the two most important knowledge sources in AECO practice. The P1 gaps (CAD + visual) represent the highest-value expansion opportunity. P2 enhancements (BIM geometry, field inspections) provide meaningful secondary value. P3 improvements (table structure, workflow) are deferrable.

The next decision should be: **investigate whether CAD and visual extraction can meet the Evidence Quality Contract before committing to implementation.**

---

*This document is a strategic analysis artifact. It identifies knowledge gaps and prioritizes expansion opportunities based on engineer value. No implementation decisions are made. No code is modified.*
