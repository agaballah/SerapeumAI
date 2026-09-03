# SerapeumAI Evidence Authority Boundary Design v1.0

**Date:** 2026-09-02  
**Task:** TASK-012 — Evidence Authority Boundary Design  
**Scope:** Read-only investigation of the minimal architectural boundary for enforcing the Evidence Quality Contract  
**Status:** DESIGN — Awaiting approval before implementation  

---

## 1. Purpose

This document defines the minimal architectural boundary required to enforce the Evidence Quality Contract (TASK-010). It identifies where authority flows through the system, where unsafe transitions exist, and where a control point can be introduced with minimal change.

No code is modified. No implementation is proposed.

---

## 2. Current FactStatus Lifecycle

### 2.1 Status Constants

```python
class FactStatus(str, Enum):
    CANDIDATE = "CANDIDATE"       # Default. Non-governing. AI-derived or builder-produced.
    VALIDATED = "VALIDATED"       # Auto-promoted. Governing truth (trusts source extractor).
    HUMAN_CERTIFIED = "HUMAN_CERTIFIED"  # User-certified. Highest authority.
    REJECTED = "REJECTED"         # Failed validation rules or user rejection.
    SUPERSEDED = "SUPERSEDED"     # Replaced by newer version.
    DRAFT = "DRAFT"              # Pre-production, not yet submitted.
```

### 2.2 Trusted Status Set

```python
TRUSTED_FACT_STATUSES = (
    FactStatus.VALIDATED.value,
    FactStatus.HUMAN_CERTIFIED.value,
)
```

These are the **only** statuses that govern chat answers through `CoverageGate` and `FactQueryAPI.get_certified_facts()`.

### 2.3 Status Transitions

| Transition | Source | Target | Who Controls |
|---|---|---|---|
| Create (default) | Any builder | `CANDIDATE` | Implicit — all builders default to CANDIDATE |
| Auto-promote | `DocumentBuilder` (structural) | `VALIDATED` | Builder code, line 131-134 |
| Auto-promote | `SystemCompletionBuilder` | `VALIDATED` | Builder code, line 58 — **no condition** |
| Human certify | `AuthorityService.authorize_certificate()` | `HUMAN_CERTIFIED` | Role-based policy |
| Reject | `RuleRunner.commit_results()` on ERROR | `REJECTED` | Validation rules |
| Reject | `FactRepository.reject_fact()` | `REJECTED` | UI action |

### 2.4 Safe vs Unsafe Transitions

| Transition | Safe? | Condition |
|---|---|---|
| CANDIDATE → CANDIDATE (default) | ✅ Safe | No trust implied |
| VALIDATED from structural facts | ✅ Safe | Deterministic counts (page_count, has_text) |
| VALIDATED from semantic extraction | ⚠️ Conditional | Depends on PDF extractor maturity (PRODUCTION) |
| VALIDATED from `SystemCompletionBuilder` | 🔴 **Unsafe** | Source may be PLACEHOLDER extractor (FieldExtractor mock) |
| HUMAN_CERTIFIED | ✅ Safe | Requires human role authorization |
| REJECTED | ✅ Safe | Blocked by design |

---

## 3. All Paths That Create Facts

### 3.1 Builder Paths (5 builders)

| Builder | Source Extractor | Status Assignment | Test Coverage |
|---|---|---|---|
| `ScheduleBuilder` | `P6Extractor` | `CANDIDATE` (all) | ✅ 8 tests |
| `BIMBuilder` | `IFCExtractor` | `CANDIDATE` (all) | ✅ 5 tests |
| `RegisterBuilder` | `ExcelRegisterExtractor` | `CANDIDATE` (all) | ❌ 0 tests |
| `DocumentBuilder` | `UniversalPdfExtractor` | `VALIDATED` (structural) + `CANDIDATE` (semantic) | ✅ 7 tests |
| `SystemCompletionBuilder` | `FieldExtractor` | `VALIDATED` (**all**, unconditional) | 🚨 **0 tests** |

### 3.2 Query-Derivation Path

| Path | Location | Status | Trust? |
|---|---|---|---|
| `AgentOrchestrator._derive_candidate_facts_from_evidence()` | Line 822 | `CANDIDATE` | ❌ Non-governing |
| `FactAPI._validate_with_rules()` | Line 663 | Reads status, doesn't create | N/A |

### 3.3 Direct Persistence Paths

| Path | Location | Status | Trust? |
|---|---|---|---|
| `FactRepository.save_facts()` | repository.py:49 | Writes whatever status is passed | Depends on caller |
| `FactRepository.update_fact_status()` | repository.py:13 | Can transition any status | Controlled by AuthorityService |

### 3.4 Summary: Who Can Create VALIDATED Facts

| Source | Can produce VALIDATED? | Risk |
|---|---|---|
| `ScheduleBuilder` | **No** — always CANDIDATE | ✅ Safe |
| `BIMBuilder` | **No** — always CANDIDATE | ✅ Safe |
| `RegisterBuilder` | **No** — always CANDIDATE | ✅ Safe |
| `DocumentBuilder` | **Yes** — for structural facts | ⚠️ Conditional (depends on PDF maturity) |
| `SystemCompletionBuilder` | **Yes** — unconditionally | 🔴 **Unsafe** |
| `AuthorityService.authorize_certificate()` | **Yes** — via human cert | ✅ Safe |

---

## 4. All Builders That Assign Fact Status

### 4.1 Status Assignment Matrix

| Builder | Fact Types | Status | Confidence | Condition |
|---|---|---|---|---|
| `ScheduleBuilder` | schedule.activity, schedule.dates, schedule.logic, etc. | CANDIDATE | 1.0 | Always |
| `BIMBuilder` | bim.project, bim.zone, bim.element_inventory_*, etc. | CANDIDATE | 1.0 | Always |
| `RegisterBuilder` | register.document, register.submittal, etc. | CANDIDATE | 1.0 | Always |
| `DocumentBuilder` | document.page_count, document.has_text, etc. | **VALIDATED** | — | If fact_type in `_STRUCTURAL_FACT_TYPES` |
| `DocumentBuilder` | document.scope_item, document.requirement, etc. | **VALIDATED** | 0.95 | Hardcoded in `_build_semantic_document_facts()` |
| `SystemCompletionBuilder` | field.inspection, quality.ncr | **VALIDATED** | — | Always, no condition |

### 4.2 Critical Finding: Two VALIDATED Pathways

**Path A — DocumentBuilder structural facts (lines 130-134):**
```python
status=(
    FactStatus.VALIDATED
    if fact_type in _STRUCTURAL_FACT_TYPES
    else FactStatus.CANDIDATE
)
```
This is **conditional**: only facts in `_STRUCTURAL_FACT_TYPES` get VALIDATED. These are deterministic counts (page_count, block_count, has_text) derived from row counts and file metadata.

**Path B — DocumentBuilder semantic facts (lines 309-319):**
```python
status=FactStatus.VALIDATED,
confidence=0.95,
```
This is **unconditional** for any fact produced by `_build_semantic_document_facts()`. These include scope_item, requirement, area_approx, etc. — derived via regex matching on extracted text.

**Path C — SystemCompletionBuilder (line 58):**
```python
status=FactStatus.VALIDATED, # Signed document = Validated Fact
```
This is **unconditional** for ALL field inspection/NCR facts. Source is `FieldExtractor` which returns mock data.

### 4.3 Pattern: "VALIDATED Without Source Verification"

Both Path B and Path C assign VALIDATED without checking:
1. Whether the source extractor meets maturity requirements
2. Whether the evidence is real or fabricated
3. Whether the extraction succeeded honestly (vs. mock/placeholder)

---

## 5. Existing Evidence Provenance

### 5.1 Fact Model Provenance Fields

```python
@dataclass
class Fact:
    method_id: str = "unknown"          # Builder ID (e.g., "document_builder_v1")
    inputs: List[FactInput] = ...       # Evidence lineage
    as_of: Dict[str, Any] = ...         # Snapshot context

@dataclass
class FactInput:
    file_version_id: str                # Links to file_versions table
    location: Dict[str, Any]            # {page: 1, bbox: [...], table: "TASK", ...}
    input_kind: str = "evidence"        # "evidence" or "rag_evidence"
```

### 5.2 What Provenance Currently Captures

| Field | Captures | Gap |
|---|---|---|
| `method_id` | Builder identity | Does NOT capture extractor identity |
| `inputs[].file_version_id` | Source file version | Does NOT capture which extractor processed it |
| `inputs[].location` | Evidence location | Does NOT capture extraction method details |
| `as_of` | Snapshot context | Does NOT capture maturity/provenance class |
| `confidence` | Builder confidence | NOT derived from extractor maturity |

### 5.3 What Provenance Does NOT Capture

- **Extractor identity**: Which V02 extractor produced the source records
- **Extractor maturity**: Whether the extractor is PRODUCTION/VERIFIED/EXPERIMENTAL/PLACEHOLDER
- **Extraction success**: Whether `result.success` was True (mock data also sets True)
- **Dependency honesty**: Whether an optional dependency was actually present
- **Provenance class**: EVIDENCE vs AI_GENERATED vs SUPPLEMENTARY_RETRIEVAL (enum exists but unused on facts)

### 5.4 FactTable Schema (Relevant Columns)

```sql
facts (
    fact_id TEXT PRIMARY KEY,
    method_id TEXT NOT NULL,       -- Builder ID only
    status TEXT NOT NULL DEFAULT 'CANDIDATE',
    confidence REAL DEFAULT 1.0,
    as_of_json TEXT NOT NULL,      -- {file_version_id: "..."}
    domain TEXT,                   -- Exists but NOT populated by builders
    builder_version TEXT           -- Exists but NOT populated
)

fact_inputs (
    fact_id TEXT,
    file_version_id TEXT,          -- Links to file_versions
    location_json TEXT,
    input_kind TEXT                -- "evidence" or "rag_evidence"
)
```

---

## 6. Can Extractor Metadata Be Introduced Without Redesign?

### 6.1 Existing Infrastructure That Supports It

| Existing Element | How It Helps |
|---|---|
| `BaseExtractor.id` property | Already contains extractor identity |
| `BaseExtractor.version` property | Already contains semver |
| `ExtractionResult.metadata` dict | Already carries quantitative metrics |
| `ExtractionResult.diagnostics` list | Already carries status messages |
| `Fact.method_id` column | Could store `"extractor_id@builder_id"` composite |
| `Fact.inputs[].input_kind` | Could carry `"extraction_method"` value |
| `FactInput.location` dict | Could carry `{"extractor": "universal-pdf-extractor-v1", "version": "1.0.0"}` |
| `facts.builder_version` column | Could store extractor version |
| `facts.domain` column | Could store domain from extractor mapping |

### 6.2 Minimal Extension Points

**Option A: Extend `ExtractionResult` metadata**
Add an `extractor_id` and `maturity_level` to the `metadata` dict during extraction. This requires zero schema changes.

**Option B: Extend `FactInput.location`**
Add extractor provenance to each `FactInput.location` dict. Requires zero schema changes, only builder-side updates.

**Option C: Add columns to `facts` table**
Add `extractor_id TEXT` and `extractor_maturity TEXT` columns. Requires a migration but provides explicit queryability.

**Option D: Use existing `method_id` creatively**
Encode extractor info in `method_id` (e.g., `"universal-pdf-extractor-v1→document_builder_v1"`). Zero changes, but fragile.

### 6.3 Recommended Approach: Extend `FactInput.location`

This is the minimal change because:
1. `location_json` already stores arbitrary key-value pairs per fact input
2. No schema migration required
3. Extraction-level provenance naturally belongs at the input (evidence) level, not the fact level
4. Queryable via JSON extraction: `SELECT json_extract(location_json, '$.extractor_id') FROM fact_inputs`

---

## 7. Proposed Control Point Location

### 7.1 Primary Control Point: `FactRepository.save_facts()`

**Location:** `src/domain/facts/repository.py:49`

**Why here:** This is the single write path for all facts. Every builder, every source, all data flows through this method. A governance check here catches ALL paths uniformly.

**What it would check:**
1. For each fact, inspect `inputs[0].location` for extractor provenance
2. Look up extractor maturity (from a registry or config)
3. If fact status is `VALIDATED` and source extractor is below VERIFIED maturity → demote to `CANDIDATE`
4. Log a warning for any demoted facts

### 7.2 Secondary Control Point: Builder-Level Guards

**Location:** Each builder's `build()` method before status assignment

**Why here:** Defense-in-depth. Even if the repository check is bypassed, builders should enforce their own maturity requirements.

**What each builder would check:**
- `ScheduleBuilder`: P6Extractor maturity must be ≥ VERIFIED for any non-CANDIDATE status
- `BIMBuilder`: IFCExtractor maturity must be ≥ VERIFIED
- `RegisterBuilder`: ExcelRegisterExtractor maturity must be ≥ VERIFIED
- `DocumentBuilder`: UniversalPdfExtractor maturity must be ≥ VERIFIED for VALIDATED assignment
- `SystemCompletionBuilder`: FieldExtractor maturity must be ≥ VERIFIED before assigning VALIDATED (currently blocks all VALIDATED output)

### 7.3 Tertiary Control Point: ExtractJob Registry Gate

**Location:** `ExtractJob.EXTRACTORS` dictionary population

**Why here:** Prevent PLACEHOLDER extractors from being discoverable at the pipeline entry point.

**What it would check:** Extractors registered here must have a `maturity` class attribute ≥ VERIFIED. PLACEHOLDER extractors go to a separate `STAGING_EXTRACTORS` dictionary.

---

## 8. Unsafe Transitions Map

### 8.1 Current Unsafe Paths to VALIDATED

```
┌─────────────────────────────────────────────────────────────────┐
│ UNDEFINED TRUTH PATH #1                                         │
│                                                                 │
│ FieldExtractor (PLACEHOLDER)                                    │
│   → returns mock IR/NCR records with success=True               │
│   → _insert_record persists to field_requests                   │
│   → SystemCompletionBuilder reads field_requests                 │
│   → Creates Fact(status=VALIDATED)                              │
│   → CoverageGate treats as trusted                              │
│   → Chat answer governed by fabricated evidence                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ CONDITIONAL TRUTH PATH #2                                       │
│                                                                 │
│ UniversalPdfExtractor (PRODUCTION)                              │
│   → extracts real PDF content                                   │
│   → DocumentBuilder semantic section uses regex                 │
│   → Creates Fact(status=VALIDATED, confidence=0.95)             │
│   → These are HIGH-RISK structural facts                        │
│   → Regex-based scope/requirement detection                      │
│   → Not truly deterministic (edge cases in text matching)       │
└─────────────────────────────────────────────────────────────────┘
```

### 8.2 Safe Paths to VALIDATED

```
┌─────────────────────────────────────────────────────────────────┐
│ TRUTH PATH #3 (SAFE)                                            │
│                                                                 │
│ UniversalPdfExtractor (PRODUCTION)                              │
│   → page_count, has_text, profile facts                         │
│   → Deterministic row counts, metadata reads                    │
│   → VALIDATED is appropriate                                    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ TRUTH PATH #4 (SAFE)                                            │
│                                                                 │
│ Any builder → CANDIDATE (default)                               │
│   → Never reaches CoverageGate                                  │
│   → Available as supporting evidence only                        │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ TRUTH PATH #5 (SAFE)                                            │
│                                                                 │
│ AuthorityService.authorize_certificate()                        │
│   → Human role authorization required                           │
│   → HUMAN_CERTIFIED status                                      │
└─────────────────────────────────────────────────────────────────┘
```

### 8.3 Missing VALIDATED Paths (Gaps)

| Builder | Should Produce VALIDATED? | Current | Gap |
|---|---|---|---|
| ScheduleBuilder | No — schedule data needs human review | CANDIDATE | ✅ Correct |
| BIMBuilder | No — BIM data needs human review | CANDIDATE | ✅ Correct |
| RegisterBuilder | No — register data needs human review | CANDIDATE | ✅ Correct |
| DocumentBuilder (structural) | Yes — deterministic counts | VALIDATED | ✅ Correct |
| DocumentBuilder (semantic) | Debatable — regex-based | VALIDATED | ⚠️ Needs policy decision |
| SystemCompletionBuilder | Only if FieldExtractor is VERIFIED | VALIDATED (unsafe) | 🔴 Must be fixed |

---

## 9. Minimal Change Boundary

### 9.1 Change Zones

```
Zone 1: EXTRACTOR REGISTRY (extract_job.py)
  ─── Restrict EXTRACTORS dict to maturity ≥ VERIFIED
  ─── Add STAGING_EXTRACTORS dict for PLACEHOLDER extractors
  ─── Add maturity_class attribute to BaseExtractor

Zone 2: EXTRACTION RESULT (base.py)
  ─── Add maturity indicator to ExtractionResult
  ─── Or: add extractor provenance to record provenance dict

Zone 3: FACT CREATION (builders)
  ─── Option A: Builders check extractor maturity before VALIDATED assignment
  ─── Option B: FactRepository.save_facts() enforces maturity gate
  ─── Option C: Both (defense in depth)

Zone 4: FACT PERSISTENCE (repository.py)
  ─── Add maturity check in save_facts()
  ─── Demote INVALIDATED facts to CANDIDATE
  ─── Log warnings for demoted facts
```

### 9.2 Minimum Viable Boundary

The **smallest change** that enforces the contract:

1. **Add `maturity` class attribute to `BaseExtractor`** — one line per extractor
2. **Move PLACEHOLDER extractors to `STAGING_EXTRACTORS`** — one dict entry change
3. **Add maturity check in `FactRepository.save_facts()`** — ~10 lines of code
4. **Demote facts from non-verified sources** — conditional logic in save_facts

This requires:
- **Zero schema changes**
- **Zero new columns**
- **Changes to 3 files max** (base.py, extract_job.py, repository.py)
- **Backward compatible** — existing VALIDATED facts remain VALIDATED; only new facts are gated

### 9.3 Zero-Change Safety Nets Already in Place

| Existing Mechanism | Protection Level | Gap |
|---|---|---|
| `CoverageGate` checks `TRUSTED_FACT_STATUSES` | ✅ Blocks CANDIDATE facts | Doesn't distinguish VALIDATED quality |
| `AuthorityService` requires role for certification | ✅ Blocks unauthorized certs | Doesn't check source maturity |
| `RuleRunner` rejects ERROR-severity facts | ✅ Catches null values, bad dates | Doesn't catch fabrication |
| `FactMethod` uniqueness via `method_id` | ✅ Traceable to builder | Doesn't trace to extractor |
| `fact_inputs` lineage table | ✅ Links facts to file versions | Doesn't link to extractor identity |

---

## 10. Tests Required Before Implementation

### 10.1 New Tests Needed

| Test | Purpose | Location |
|---|---|---|
| `test_placeholder_extractor_cannot_trigger_builder` | Verify PLACEHOLDER extractors in STAGING dict don't trigger BuildFactsJob | `test_extractor_registry_reachability.py` (extend) |
| `test_completion_builder_produces_candidate_not_validated` | Verify SystemCompletionBuilder outputs CANDIDATE when source is unverified | `test_completion_builder_contract.py` (new) |
| `test_repository_demotes_unverified_validated_facts` | Verify FactRepository.save_facts() demotes facts from unverified sources | `test_fact_repository_governance.py` (new) |
| `test_structural_document_facts_remain_validated` | Verify DocumentBuilder structural facts still get VALIDATED (they come from PRODUCTION extractor) | `test_document_builder_semantic_facts.py` (extend) |
| `test_semanatic_document_facts_undergo_review` | Define policy for semantic VALIDATED facts (regex-based) | TBD |
| `test_extractor_maturity_attribute_exists` | Verify every registered extractor has a maturity class attribute | `test_extractor_registry_reachability.py` (extend) |
| `test_no_mock_data_in_production_pipeline` | Static analysis: no mock data patterns in production extractors | `test_field_extractor_no_mock_data.py` (new) |

### 10.2 Existing Tests That Must Continue Passing

| Test File | Count | Risk if Changed |
|---|---|---|
| `test_truth_state_enforcement.py` | 9 tests | Low — tests trusted status constants |
| `test_truth_spine_contract_guardrails.py` | 5 tests | Low — tests answer path structure |
| `test_build_facts_evidence_closure.py` | 4 tests | Medium — tests VALIDATED document facts |
| `test_p6_truth.py` | 2 tests | Low — tests CANDIDATE schedule facts |
| `test_p6_critical_path_unknown_honesty.py` | 6 tests | Low — tests CANDIDATE schedule facts |
| `test_p6_relation_fidelity.py` | 2 tests | Low — tests CANDIDATE schedule facts |
| `test_pdf_routing*.py` | 14 tests | Low — tests PDF extraction, not fact creation |
| `test_ifc_*.py` | 5 tests | Low — tests IFC extraction |
| `test_office_dgn_flattened_extraction_contract.py` | 6 tests | Low — tests flattened output contract |
| `test_extractor_registry_reachability.py` | 2 tests | **HIGH** — must be updated to reflect new registry policy |

### 10.3 Expected Test Impact

- **Must update:** `test_extractor_registry_reachability.py` — currently asserts `"field"` is in EXTRACTORS; will need to assert `"field"` is in STAGING_EXTRACTORS instead
- **Must add:** 7 new tests (see §10.1)
- **Should preserve:** All existing tests must continue passing after the boundary is added
- **Will break:** Any test that directly inserts VALIDATED facts without going through the new governance check (none currently, but future tests may need updating)

---

## 11. Boundary Enforcement Flow (Design)

```
                    ┌──────────────────────┐
                    │   ExtractJob.run()   │
                    │   (entry point)      │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  1. Registry Gate    │
                    │  (Zone 1)            │
                    │                      │
                    │  EXTRACTORS dict:    │
                    │    maturity ≥ VERIFIED│
                    │  STAGING_EXTRACTORS: │
                    │    PLACEHOLDER only  │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  2. Extraction       │
                    │  (already exists)    │
                    │                      │
                    │  result =            │
                    │    extractor.extract │
                    │                      │
                    │  provenance:         │
                    │    record.provenance │
                    │      .extractor_id   │
                    │      .maturity       │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  3. Builder Run      │
                    │  (existing)          │
                    │                      │
                    │  facts = builder.    │
                    │    build(project,    │
                    │     snapshot)        │
                    │                      │
                    │  builder assigns     │
                    │  status (some to     │
                    │  VALIDATED)          │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  4. Governance Gate  │
                    │  (Zone 3/4)          │
                    │                      │
                    │  for each fact in    │
                    │  facts:              │
                    │    if status ==      │
                    │      VALIDATED:      │
                    │      check extractor │
                    │      maturity        │
                    │      if < VERIFIED:  │
                    │        demote to     │
                    │        CANDIDATE     │
                    │        log warning   │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  5. Persist          │
                    │  (existing)          │
                    │                      │
                    │  repo.save_facts(    │
                    │    facts)            │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  6. Query/Chat       │
                    │  (existing)          │
                    │                      │
                    │  CoverageGate only   │
                    │  sees VALIDATED &    │
                    │  HUMAN_CERTIFIED     │
                    │  (governed facts)    │
                    └──────────────────────┘
```

---

## 12. Summary of Findings

### 12.1 Safe Components (No Changes Needed)
- `ScheduleBuilder`, `BIMBuilder`, `RegisterBuilder` — all produce CANDIDATE only
- `AuthorityService` — requires human role authorization
- `CoverageGate` — correctly filters to TRUSTED_FACT_STATUSES
- `FactStatus` model — mature enum with clear semantics
- `FactInput` lineage — captures file_version_id and location

### 12.2 Unsafe Components (Boundary Required)
- `SystemCompletionBuilder` — produces VALIDATED from PLACEHOLDER source
- `DocumentBuilder.semantic_extract` — produces VALIDATED via regex (needs policy decision)
- `ExtractJob.EXTRACTORS` — accepts PLACEHOLDER extractors
- No maturity tracking in fact provenance

### 12.3 Proposed Minimal Boundary
- **One new attribute:** `maturity` on `BaseExtractor`
- **One new registry:** `STAGING_EXTRACTORS` for PLACEHOLDER extractors
- **One gate:** Maturity check in `FactRepository.save_facts()`
- **Zero schema changes**
- **Estimated change surface:** ~3 files, ~15 lines of new code

### 12.4 Critical Risk Addressed
The primary risk (mock field data → VALIDATED facts → governing chat answers) is fully addressed by the boundary: moving `FieldExtractor` to STAGING and adding the maturity gate in `save_facts()` prevents any fact from reaching VALIDATED status when its source extractor is PLACEHOLDER.

---

*This document is read-only analysis. No code was modified. No implementation decisions were made beyond identifying the minimal boundary.*
