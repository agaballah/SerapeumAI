# SerapeumAI Evidence Pipeline Governance Gap Report v1.0

**Date:** 2026-09-02  
**Task:** TASK-011 — Evidence Pipeline Governance Gap Analysis  
**Scope:** Read-only investigation of governance gaps in the evidence pipeline  
**Status:** GAP REPORT — Identifies where enforcement is missing; does not propose fixes  

---

## 1. Purpose

This report maps the current evidence pipeline from file ingestion through fact creation, identifies where the Evidence Quality Contract (TASK-010) is NOT enforced, and flags paths where placeholder/mock data can enter as trusted evidence.

No code is modified. No implementation proposals are included.

---

## 2. Current Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         INGESTION TRIGGER                              │
│                    IngestFileJob → ExtractJob                          │
└────────────────────────────┬──────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     EXTRACTOR SELECTION                                 │
│                                                                         │
│   ExtractJob.EXTRACTORS[extractor_name]  ← hardcoded class registry     │
│                                                                         │
│   Keys: "p6", "ifc", "excel_register", "pdf", "field",                 │
│          "word", "pptx", "dgn"                                          │
│                                                                         │
│   NO maturity gate.                                                     │
│   NO validation of extractor before instantiation.                      │
│   NO check that supported_extensions matches actual file type.          │
└────────────────────────────┬──────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     EXTRACTION RUN                                      │
│                                                                         │
│   result = extractor.extract(source_path, context=ctx)                  │
│                                                                         │
│   Result → ExtractionResult:                                            │
│     - records: List[Dict]                                               │
│     - diagnostics: List[str]                                            │
│     - metadata: Dict                                                    │
│     - success: bool                                                     │
│                                                                         │
│   NO validation of result schema.                                       │
│   NO check that provenance fields exist on each record.                 │
│   NO maturity-level check on extractor class.                           │
└────────────────────────────┬──────────────────────────────────────────┘
                             │
                    success=True?
                       ╱        ╲
                     YES          NO
                      │            │
                      ▼            ▼
┌───────────────────────────────────────┐  ┌─────────────────────────────┐
│               PERSISTENCE              │  │     FAILURE HANDLING        │
│                                       │  │                             │
│  for rec in result.records:           │  │  raise Exception(...)       │
│      self._insert_record(db, rec)     │  │  → extraction_runs FAILED   │
│                                       │  │  → job aborts                │
│  _insert_record() uses if/elif chain: │  │                             │
│    - p6_* → p6_* tables               │  │  NO soft-fail path exists   │
│    - ifc_* → ifc_* tables             │  │  for partial extractions.   │
│    - register_row → register_rows     │  │  Any failure = hard abort.  │
│    - field_request → field_requests   │  │                             │
│    - pdf_page → pdf_pages + pages     │  │                             │
│    - doc_classification → ...         │  │                             │
│    - doc_blocks → doc_blocks          │  │                             │
│    - UNKNOWN TYPE → SILENT DROP       │  │                             │
│                                       │  │                             │
│  ⚠️ Unknown types silently skipped    │  │                             │
│     with NO log, NO warning,          │  │                             │
│     NO error.                          │  │                             │
└────────────────────────────┬──────────┘  └─────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     DOWNSTREAM JOB TRIGGER                              │
│                                                                         │
│   builder_map = {                                                        │
│       "p6": "schedule",                                                  │
│       "ifc": "bim",                                                      │
│       "excel_register": "register",                                      │
│       "field": "completion"           ← PLACEHOLDER extractor maps to   │
│   }                                                                     │     VALIDATED fact builder               │
│                                                                         │
│   PDF triggers its own separate BuildFactsJob + AnalyzeDocJob           │
│                                                                         │
│   NO maturity gate before triggering builder.                            │
│   NO check that the extractor produced valid evidence.                   │
└────────────────────────────┬──────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     FACT BUILDING                                        │
│                                                                         │
│   BuildFactsJob → builder.build(project_id, snapshot_id)                │
│                                                                         │
│   ScheduleBuilder    → Fact(CANDIDATE) for all                         │
│   BIMBuilder         → Fact(CANDIDATE) for all                         │
│   RegisterBuilder    → Fact(CANDIDATE) for all                         │
│   DocumentBuilder    → Fact(VALIDATED) for structural facts            │
│                        Fact(CANDIDATE) for semantic facts              │
│   SystemCompletionBuilder → Fact(VALIDATED) for ALL ← GOVERNANCE GAP  │
│                                                                         │
│   Validation rules (RuleRunner):                                        │
│     - CORE_001: null value → ERROR → REJECTED                          │
│     - SCHED_001: negative duration → ERROR                             │
│     - SCHED_002: negative float → WARNING                              │
│                                                                         │
│   NO validation rules for: field.inspection, quality.ncr,              │
│   document.scope_item, bim.element, etc.                                │
└────────────────────────────┬──────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     FACT PERSISTENCE                                     │
│                                                                         │
│   FactRepository.save_facts(facts)                                      │
│     - INSERT OR REPLACE into facts table                                │
│     - DELETE + INSERT into fact_inputs (lineage)                        │
│                                                                         │
│   FactRepository.save_links(links)                                      │
│     - INSERT OR REPLACE into links table                                │
│                                                                         │
│   NO maturity check on fact source.                                     │
│   NO proof that facts came from verified evidence.                      │
└────────────────────────────┬──────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     QUERY / CHAT                                         │
│                                                                         │
│   FactQueryAPI → CoverageGate → chat synthesis                          │
│                                                                         │
│   Trusted sources: VALIDATED, HUMAN_CERTIFIED                           │
│   Non-governing: CANDIDATE                                              │
│                                                                         │
│   AuthorityService checks role-based certification permissions.         │
│                                                                         │
│   NO check that the original evidence was from a VERIFIED extractor.    │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Where Maturity Enforcement is Missing

### 3.1 Registry Level — No Gate

**Location:** `src/application/jobs/extract_job.py:36-45`

```python
EXTRACTORS: Dict[str, Type[BaseExtractor]] = {
    "p6": P6Extractor,
    "ifc": IFCExtractor,
    "excel_register": ExcelRegisterExtractor,
    "pdf": UniversalPdfExtractor,
    "field": FieldExtractor,      # ← PLACEHOLDER maturity, still registered
    "word": WordExtractor,
    "pptx": PPTXExtractor,
    "dgn": DGNExtractor,
}
```

**Gap:** Any extractor class can be placed in this dictionary regardless of maturity. There is no enforcement that only PRODUCTION or VERIFIED extractors are registered.

**Test that reinforces the gap:**
- `test_extractor_registry_reachability.py:16` explicitly asserts `"field"` is in the registry

### 3.2 Builder Map Level — No Gate

**Location:** `src/application/jobs/extract_job.py:167-172`

```python
builder_map = {
    "p6": "schedule",
    "ifc": "bim",
    "excel_register": "register",
    "field": "completion"       # ← PLACEHOLDER extractor triggers VALIDATED facts
}
```

**Gap:** No check that the extractor mapped here has passed maturity requirements. A placeholder extractor can trigger a builder that produces trusted facts.

### 3.3 Result Validation — No Gate

**Location:** `src/application/jobs/extract_job.py:145-155`

After `result = extractor.extract(...)`, the code immediately:
1. Checks `result.success` — but this is just a boolean
2. Iterates `result.records` and passes each to `_insert_record`

**Gaps:**
- No schema validation on individual records (missing `type`, `data`, or `provenance`)
- No maturity-level check on the extractor class
- No verification that record types match expected output for this extractor
- No check that `diagnostics` doesn't contain warnings about fabrication

### 3.4 Record Persistence — Silent Drop

**Location:** `src/application/jobs/extract_job.py:223-381` (`_insert_record`)

The method uses an `if/elif` chain with no final `else` clause. If a record type doesn't match any known branch, it falls through silently.

**Gaps:**
- Unknown record types produce NO log, NO warning, NO error
- No validation that required provenance fields exist
- No validation that `data` contains required fields for the record type
- If an extractor returns an unexpected `type` string, the data is lost with no audit trail

---

## 4. Where Placeholder Outputs Can Enter

### 4.1 Critical Path: Field → Completion → VALIDATED Facts

| Step | File | Behavior | Risk |
|---|---|---|---|
| 1 | `field_extractor.py:54-78` | Returns mock IR/NCR records based on filename markers | 🔴 Fabricated data enters pipeline |
| 2 | `extract_job.py:145` | `result.success` is `True` (mock returns success) | 🟡 No failure signal |
| 3 | `extract_job.py:336-342` | Inserts mock records into `field_requests` table | 🔴 Fake data persisted to DB |
| 4 | `extract_job.py:171-182` | Triggers `BuildFactsJob(builder_type="completion")` | 🔴 Fake data triggers fact building |
| 5 | `completion_builder.py:58` | Sets `status=FactStatus.VALIDATED` | 🔴🔴 **Fabricated data becomes TRUSTED** |
| 6 | `repository.py:49-93` | Persists VALIDATED facts to DB | 🔴🔴 Unquestionable truth in query results |

**Impact:** If a file path contains "IR" or "Inspection", the system produces VALIDATED facts about inspection requests that never existed. These facts would govern chat answers through the CoverageGate.

### 4.2 Secondary Path: Classifier Stub → DocumentBuilder

| Step | File | Behavior | Risk |
|---|---|---|---|
| 1 | `classifier.py:5` | `classify()` always returns `"unknown"` | 🟡 Non-functional |
| 2 | `pdf_extractor.py:111` | Calls classifier (or uses heuristic) | 🟡 No classification impact |
| 3 | `document_builder.py:130-134` | Structural facts get VALIDATED regardless | 🟢 No direct risk (structural facts are count-based) |

**Impact:** Low. Document classification is non-functional but doesn't affect trusted fact generation.

### 4.3 Tertiary Path: EvidencePackBuilder Stub

| Step | File | Behavior | Risk |
|---|---|---|---|
| 1 | `evidence_builder.py:7` | Returns `{"documents": [], "status": "No Evidence Found"}` | 🟡 Legacy dead code |
| 2 | No active callers identified | — | 🟢 No current risk |

---

## 5. Where Validation Should Occur

### 5.1 ExtractionResult Pre-Persistence Validation

**Location:** Between `extractor.extract()` call (line 145) and `_insert_record` loop (line 154)

**Missing checks:**
- Record count is consistent with `metadata` (e.g., page_count matches record count)
- Every record has a valid `type` matching one of the known types for this extractor
- Every record has `provenance.source` and `provenance.origin` populated
- `success=False` results are handled gracefully (not raised as exceptions that abort the job)
- No record contains fabricated/mocked data indicators in provenance

### 5.2 Extractor Maturity Gate Before Registration

**Location:** `ExtractJob.EXTRACTORS` definition (line 36)

**Missing checks:**
- Registry should only accept extractors with maturity ≥ VERIFIED
- PLACEHOLDER extractors should be isolated in a separate staging registry
- A maturity attribute on the extractor class should be checked at registration time

### 5.3 Builder Selection Gate

**Location:** `builder_map` lookup (line 167-173)

**Missing checks:**
- Only VERIFIED+ extractors should trigger automated fact building
- PLACEHOLDER extractors should either skip builder trigger or trigger a builder that produces CANDIDATE-only facts
- The `field→completion` mapping should not exist until `FieldExtractor` reaches at least VERIFIED maturity

### 5.4 Fact Status Governance

**Location:** Individual builders (`completion_builder.py:58`, `document_builder.py:130-134`)

**Missing checks:**
- `SystemCompletionBuilder` promotes all facts to `VALIDATED` unconditionally — no maturity check on source extractor
- `DocumentBuilder` promotes structural facts to `VALIDATED` — acceptable for deterministic counts, but needs explicit policy
- No builder checks the maturity of its source extractor before assigning fact status

### 5.5 Unknown Record Type Handling

**Location:** `_insert_record` (line 223-381)

**Missing checks:**
- Final `else` clause with `logger.warning("Unknown record type '%s' from extractor '%s'", rtype, self.extractor_name)`
- Count of skipped/dropped records tracked in extraction run diagnostics
- Option to fail the job on unknown record types (strict mode) vs. warn (permissive mode)

---

## 6. Existing Tests Protecting These Flows

### 6.1 Extraction Layer Tests (36 tests covering 11 files)

| Test File | What It Protects | Coverage |
|---|---|---|
| `test_extractor_registry_reachability.py` | Registry contains expected keys | ⚠️ **Reinforces gap** — asserts `"field"` is present |
| `test_ifc_extractor_persistence_contract.py` | IFC records persist to correct tables | ✅ Good |
| `test_ifc_dependency_contract.py` | Honest failure when `ifcopenshell` missing | ✅ Good |
| `test_p6_truth.py` | Float normalization, critical path | ✅ Good |
| `test_p6_relation_fidelity.py` | Parallel relations preserved | ✅ Good |
| `test_p6_critical_path_unknown_honesty.py` | Unknown float handling | ✅ Good |
| `test_pdf_routing.py` | Page composition sniffing | ✅ Good |
| `test_pdf_metadata_completeness.py` | PDF metadata extraction | ✅ Good |
| `test_pdf_routing_fixture_pack.py` | Full routing + OCR boundaries | ✅ Good |
| `test_excel_register_extractor_hygiene.py` | No debug file write | ⚠️ Only hygiene, no behavior |
| `test_office_dgn_flattened_extraction_contract.py` | Office/DGN produce flattened output only | ✅ Good |

### 6.2 Builder Layer Tests (7 tests)

| Test File | What It Protects | Coverage |
|---|---|---|
| `test_build_facts_evidence_closure.py` | Document facts from extracted evidence | ✅ Good |
| `test_document_builder_semantic_facts.py` | Semantic fact emission | ⚠️ Limited |
| `test_early_build_visibility.py` | Job queue priority | ✅ Good |

### 6.3 Missing Test Coverage

| Area | Tests | Risk |
|---|---|---|
| **Field/Completion pipeline** | **0** | 🔴 No test prevents mock data → VALIDATED facts |
| **SystemCompletionBuilder** | **0** | 🔴 No test for fact status assignment |
| **Unknown record type handling** | **0** | 🟡 Silently dropped records untested |
| **ExtractionResult schema validation** | **0** | 🟡 No test enforces provenance requirements |
| **Maturity-based registry gates** | **0** | 🔴 No test enforces registry maturity rules |
| **Builder selection gates** | **0** | 🟡 No test prevents placeholder extractors from triggering builders |
| **Excel register behavior** | **0** | 🟡 Only hygiene test exists |
| **Word/PPTX content extraction** | **0** | 🟡 Only contract tests exist |

---

## 7. Required Future Change Boundaries

The following boundary zones were identified where governance enforcement must be added. These are NOT implementation proposals — they define where change is required.

### Zone A: Extractor Registration Boundary

**Boundary:** The `EXTRACTORS` dictionary in `ExtractJob`

**Current state:** Open registry — any class can be added

**Required enforcement point:** Before or at registry population time, each extractor must declare its maturity level, and the registry must refuse PLACEHOLDER-level extractors

**Related contract section:** §10 (Maturity Levels), §10.3 (Registration Requirement)

### Zone B: ExtractionResult Validation Boundary

**Boundary:** Between `extractor.extract()` return and `_insert_record` loop

**Current state:** No validation — raw records flow directly to persistence

**Required enforcement point:** A validation step must inspect each record for schema compliance (required fields, provenance completeness, type validity) before persistence

**Related contract section:** §3 (What Qualifies as Valid Extracted Evidence), §4 (Required Lineage Fields)

### Zone C: Builder Trigger Boundary

**Boundary:** The `builder_map` and its usage in `ExtractJob.run()` lines 167-182

**Current state:** All registered extractors (including PLACEHOLDER) trigger downstream builders

**Required enforcement point:** Only extractors at VERIFIED or higher maturity should trigger automated fact building. PLACEHOLDER extractors should either not trigger builders or trigger builders that produce CANDIDATE-only facts

**Related contract section:** §10.3 (Registration Requirement), §12 (Acceptance Criteria)

### Zone D: Fact Status Assignment Boundary

**Boundary:** Inside each builder's `build()` method where `status=` is assigned

**Current state:** `SystemCompletionBuilder` assigns `VALIDATED` unconditionally; `DocumentBuilder` assigns `VALIDATED` for structural facts

**Required enforcement point:** Fact status assignment must consider the maturity of the source extractor. VALIDATED status should only be assigned when the evidence source meets minimum maturity requirements

**Related contract section:** §6 (Confidence Handling), §10.1 (Maturity Definitions)

### Zone E: Unknown Record Handling Boundary

**Boundary:** The end of `_insert_record()` after the last `elif` clause

**Current state:** Unknown record types silently disappear

**Required enforcement point:** A final handler must log a warning for unknown record types and optionally count them in extraction run diagnostics for auditability

**Related contract section:** §8.4 (No Silent Drops)

---

## 8. Summary of Gaps by Severity

| Severity | Gap | Location | Impact |
|---|---|---|---|
| 🔴 **CRITICAL** | Mock data → VALIDATED facts | `field_extractor` → `completion_builder` | Fabricated evidence governs chat answers |
| 🔴 **CRITICAL** | No maturity gate on registry | `ExtractJob.EXTRACTORS` | PLACEHOLDER extractors operate in production |
| 🔴 **CRITICAL** | No test coverage for field pipeline | Missing tests | No regression protection for critical path |
| 🟡 **HIGH** | Unknown record types silently dropped | `_insert_record` else branch | Data loss without audit trail |
| 🟡 **HIGH** | No ExtractionResult validation | Between extract and persist | Schema violations go undetected |
| 🟡 **HIGH** | No builder trigger maturity check | `builder_map` usage | PLACEHOLDER extractors auto-trigger builders |
| 🟢 **MEDIUM** | Excel register behavior untested | Missing tests | Header detection quality unknown |
| 🟢 **MEDIUM** | Word/PPTX content untested | Missing tests | Extraction quality unknown beyond contract |
| 🟢 **LOW** | Classifier stub always returns "unknown" | `classifier.py` | Low — doesn't affect trusted facts |
| 🟢 **LOW** | EvidencePackBuilder stub | `evidence_builder.py` | Dead code, no active callers |

---

*This report is read-only analysis. No code was modified. No implementation decisions were made.*
