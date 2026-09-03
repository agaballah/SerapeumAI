# SerapeumAI Evidence Quality Contract v1.0

**Date:** 2026-09-02  
**Task:** TASK-010 — Evidence Quality Contract Design Review  
**Scope:** Read-only contract definition for all evidence extractors  
**Status:** BASELINE CONTRACT — Awaiting approval before new extraction development  

---

## 1. Purpose

This contract defines the minimum quality requirements that every SerapeumAI evidence extractor must satisfy. It establishes what qualifies as valid extracted evidence, required lineage fields, failure semantics, and maturity levels.

No code is modified by this document. It is a reference standard for future extraction work.

---

## 2. Extractor Contract Interface (V02)

### 2.1 Required Properties

Every `BaseExtractor` implementation MUST expose:

| Property | Type | Requirement |
|---|---|---|
| `id` | `str` | Unique, stable identifier (e.g., `"universal-pdf-extractor-v1"`) |
| `version` | `str` | Semver string (e.g., `"1.0.0"`) |
| `supported_extensions` | `List[str]` | Lowercase extensions including dot (e.g., `[".pdf"]`) |

### 2.2 Required Method Signature

```python
def extract(self, file_path: str, context: Dict[str, Any] = None) -> ExtractionResult
```

- `file_path` must be an absolute path to the versioned file blob
- `context` is optional; may contain `doc_id`, `on_stage` callback, `llm_service`
- Return type is always `ExtractionResult`

### 2.3 ExtractionResult Schema

```python
@dataclass
class ExtractionResult:
    records: List[Dict[str, Any]]   # Raw staging records
    diagnostics: List[str]          # Human-readable status messages
    metadata: Dict[str, Any]        # Quantitative metrics (page counts, etc.)
    success: bool                   # True if extraction completed without fatal error
```

---

## 3. What Qualifies as Valid Extracted Evidence

### 3.1 Record Structure

Every record in `records` MUST conform to:

```python
{
    "type": str,           # Domain-prefixed: "pdf_page", "p6_activity", "ifc_element_metadata", etc.
    "data": Dict,          # Typed payload — domain-specific schema
    "provenance": Dict,    # REQUIRED — see §4
}
```

**Records with missing or empty `"provenance"` are INVALID.**

### 3.2 Determinism Requirement

For identical input files, extraction MUST produce deterministic records. Non-determinism sources include:
- UUID generation in record IDs or data
- Timestamps in output data
- Random ordering of records

**Allowed non-determinism:** Diagnostics messages and metadata counters (e.g., page counts).

### 3.3 Statelessness Requirement

The `extract()` method MUST be stateless relative to the file version. It may read the file but MUST NOT:
- Persist intermediate state to the database directly
- Modify global singleton state
- Depend on prior calls for correctness

All persistence is the responsibility of `ExtractJob._insert_record()`.

### 3.4 Output Completeness

A successful extraction (`success=True`) MUST produce at least one record, OR the record count must be explicitly reflected in `metadata` as zero (e.g., empty PDF with no text).

An extraction that produces zero records AND sets `success=False` is only valid when a diagnosed failure condition exists (missing dependency, corrupted file, unsupported format).

---

## 4. Required Lineage Fields

### 4.1 Provenance Schema

Every record's `provenance` dict MUST include:

| Field | Type | Description |
|---|---|---|
| `source` | `str` | The extraction method name (e.g., `"pypdf_vector"`, `"pytesseract_ocr"`, `"ezdxf_entity_listing"`) |
| `origin` | `str` | The source entity/table name (e.g., `"TASK"`, `"IfcWall"`, `"pdf_page"`) |

Additional domain-specific provenance fields are encouraged but not required:
- `page`: int — page number (for PDF)
- `entity`: str — IFC entity type
- `table`: str — XER table name
- `sheet`: str — Excel sheet name

### 4.2 Fact Input Lineage

When records are persisted by `_insert_record()`, they create implicit evidence links. For facts later built from these records, `FactInput` must include:
- `file_version_id: str`
- `location: Dict` — e.g., `{"page": 1, "bbox": [...]}` or `{"table": "TASK", "row": 5}`
- `input_kind: str` — defaults to `"evidence"`

### 4.3 Method Identification

Each record MUST include its `method_id` in metadata or provenance so downstream builders can attribute facts to specific extraction procedures.

---

## 5. Source File Requirements

### 5.1 Path Resolution

Extractors receive an absolute file path from `ExtractJob`. They MUST treat the path as read-only and verify existence before processing.

### 5.2 Extension Guard

Extractors MUST only accept files matching their declared `supported_extensions`. If called with a non-matching extension, return `ExtractionResult(success=False, diagnostics=["unsupported extension"])`.

### 5.3 Encoding Handling

Text-based extractions (XER, Office, DXF) MUST handle encoding gracefully. Failed decoding MUST NOT raise an unhandled exception — it MUST return `success=False` with a diagnostic mentioning the encoding issue.

### 5.4 File Size Caps

Extractors SHOULD implement reasonable size caps to prevent memory exhaustion. Exceeding a cap MUST return `success=False` with diagnostic, NOT silently truncate.

---

## 6. Confidence Handling

### 6.1 Confidence is NOT on Records

Confidence scores are properties of **facts**, not extraction records. Extractors do NOT emit confidence values.

### 6.2 Builder-Assigned Confidence

Downstream builders (ScheduleBuilder, BIMBuilder, DocumentBuilder) assign confidence when constructing Facts:
- Structural/deterministic facts default to `confidence=1.0`
- AI-derived or inferred facts use builder-defined confidence

### 6.3 Metadata Confidence Hints

Extractors MAY include confidence-related hints in `metadata` for diagnostic purposes, but these MUST NOT influence fact construction directly.

Example:
```python
metadata = {
    "page_count": 12,
    "ocr_quality_estimate": "good",  # diagnostic only
}
```

---

## 7. Missing Dependency Behavior

### 7.1 Rule: Honest Failure

When an optional dependency is missing, the extractor MUST:
1. Set `success=False`
2. Include the dependency name in `diagnostics`
3. Return empty `records=[]`
4. NOT fall back to an alternative method (unless the alternative is part of the core contract and tested)

### 7.2 Forbidden Patterns

The following are **PROHIBITED** when dependencies are missing:
- Silently returning empty results with `success=True`
- Falling back to regex/text parsing without explicit diagnostic
- Claiming the extraction was partial or approximate
- Raising unhandled `ImportError` (must be caught and wrapped)

### 7.3 Current Compliant Examples

| Extractor | Missing Dep | Behavior | Status |
|---|---|---|---|
| `IFCExtractor` | `ifcopenshell` | `success=False`, diagnostic names dep, no fallback | ✅ Compliant |
| `ExcelRegisterExtractor` | `pandas` | Falls through to exception (not caught) | ⚠️ Needs fix |
| `CADProcessor` | `ezdxf` | Falls through to exception (not caught) | ⚠️ Needs fix |

---

## 8. Failure Behavior

### 8.1 Failure Classification

| Category | `success` | `diagnostics` | Records | Use Case |
|---|---|---|---|---|
| **Clean empty** | `True` | `[]` | `[]` | Empty PDF, zero-row XER |
| **Partial failure** | `False` | `[error_msg]` | `[]` or partial | Corrupted file, parse error mid-stream |
| **Hard failure** | `False` | `[dep_missing_msg]` | `[]` | Missing optional dependency |
| **Runtime error** | Raises | N/A | N/A | Programming bug, should never occur |

### 8.2 Exception Policy

Extractors MUST catch all expected exceptions and convert them to `ExtractionResult(success=False, diagnostics=[...])`. Only unexpected programming errors (e.g., `KeyError` on internal dict access) should propagate.

### 8.3 No Silent Drops

When a record cannot be persisted (e.g., missing required field like `ElementId` for IFC elements), the extractor or `_insert_record()` MUST log a warning and SKIP the record — it MUST NOT silently include garbage data.

---

## 9. Mock/Test Data Separation Rules

### 9.1 Production Code Prohibition

Production extractor code MUST NOT contain:
- Hardcoded mock data returned instead of real extraction
- `uuid.uuid4()` for generating realistic-looking IDs in output records
- Filename-based branching that generates fabricated records (e.g., `if "IR" in file_path: return mock_data`)

### 9.2 Test Isolation

Tests MAY inject mocks via `monkeypatch` or fixture classes. These patterns are permitted in test files ONLY.

Permitted test patterns:
```python
# Test fixture class
class FakeWordProcessor:
    def process(self, ...):
        return {"text": "...", "pages": [...]}

# Monkeypatch
monkeypatch.setattr(word_processor, "WordProcessor", lambda: FakeWordProcessor())
```

### 9.3 Current Violations

| File | Violation | Severity |
|---|---|---|
| `src/engine/extractors/field_extractor.py:54-78` | Returns hardcoded mock IR records based on filename markers | 🔴 **CRITICAL** |
| `src/engine/extractors/field_extractor.py:36` | `TODO: Integrate Actual VLM Call` | 🟡 **WARNING** |
| `src/engine/extractors/pdf_extractor.py:118` | Hardcoded `"confidence": 0.8` for doc classification | 🟢 **INFO** |
| `src/engine/extractors/pdf_extractor.py:286` | `_get_keywords()` returns `[]` always | 🟢 **INFO** |
| `src/document_processing/classifier.py:5` | `classify()` always returns `"unknown"` | 🟡 **WARNING** |
| `src/domain/intelligence/evidence_builder.py:7` | Returns `{"documents": [], "status": "No Evidence Found"}` | 🟡 **WARNING** |

---

## 10. Extractor Maturity Levels

### 10.1 Definition

Each extractor MUST be assigned one of four maturity levels:

| Level | Criteria | Contract Requirements | Testing Required |
|---|---|---|---|
| **PRODUCTION** | Extractor produces deterministic, complete evidence for its domain. All failure modes handled. All required fields populated. | Full compliance with this contract. No TODOs in critical paths. | ≥5 tests covering routing, edge cases, persistence, and dependency failure |
| **VERIFIED** | Extractor works for known-good inputs. Some edge cases or validation gaps remain. | Compliant with core contract (§3–§8). Minor deviations documented. | ≥3 tests + contract tests proving no prohibited patterns |
| **EXPERIMENTAL** | Extractor is implemented but has known limitations or unverified behavior. | Must clearly mark limitations in code comments and `diagnostics`. Cannot be referenced as trusted evidence source. | ≥1 contract test proving it fails honestly on invalid input |
| **PLACEHOLDER** | Stub or incomplete implementation. Returns fabricated or empty data. | Must NOT be registered in `ExtractJob.EXTRACTORS`. Must have TODO comment explaining required work. | N/A (should not be registered) |

### 10.2 Current Maturity Assessment

| Extractor | Maturity | Rationale |
|---|---|---|
| `UniversalPdfExtractor` | **PRODUCTION** | 14 tests, full routing, metadata, semantic blocks. Minor: hardcoded confidence in classification |
| `P6Extractor` | **PRODUCTION** | 8 tests, deterministic XER parse, critical path logic verified |
| `IFCExtractor` | **VERIFIED** | 5 tests, honest dependency failure, but no real .ifc fixture testing |
| `ExcelRegisterExtractor` | **EXPERIMENTAL** | 1 hygiene test only. Header detection heuristic unvalidated |
| `WordExtractor` | **VERIFIED** | Contract test proves flattened output. No behavior tests for complex docs |
| `PPTXExtractor` | **VERIFIED** | Contract test proves flattened output. No behavior tests for complex presentations |
| `DGNExtractor` | **EXPERIMENTAL** | 3 integration tests. XREF extraction depends on optional ODA converter |
| `FieldExtractor` | **PLACEHOLDER** | Returns mock data. Not registered in EXTRACTORS? (Actually it IS registered) |
| *(No extractor)* | **PLACEHOLDER** | `.dxf` / `.dwg` — no V02 extractor exists. CADProcessor is untested V01 code |
| *(No extractor)* | **PLACEHOLDER** | Images — no V02 extractor. ImageProcessor is untested V01 code |

### 10.3 Registration Requirement

Only **PRODUCTION** and **VERIFIED** extractors MAY be registered in `ExtractJob.EXTRACTORS`. 

**Current violation:** `FieldExtractor` (PLACEHOLDER) is registered in `ExtractJob.EXTRACTORS` at line 15 of `extract_job.py`. This must be removed or upgraded before field evidence can be trusted.

---

## 11. Existing Contract Violations

### 11.1 Critical Violations

| # | Violation | Location | Impact |
|---|---|---|---|
| C1 | Mock data returned as real evidence | `field_extractor.py:54-78` | Fabricated IR/NCR records enter DB and can produce fabricated facts |
| C2 | Placeholder extractor registered in production pipeline | `extract_job.py:15` (`"field": FieldExtractor`) | Any file triggering field extractor produces fake data |
| C3 | IFC no fallback declared but code allows potential confusion | `ifc_extractor.py:117-122` | Actually compliant — honest failure. No action needed. |

### 11.2 Warning Violations

| # | Violation | Location | Impact |
|---|---|---|---|
| W1 | Classifier stub always returns `"unknown"` | `classifier.py:5` | Document type classification is non-functional |
| W2 | EvidencePackBuilder stub returns empty | `evidence_builder.py:7` | Legacy evidence pack feature is non-functional |
| W3 | PDF classification confidence hardcoded to 0.8 | `pdf_extractor.py:118` | Misleading confidence metric (informational only, no factual impact) |
| W4 | `_get_keywords()` always returns `[]` | `pdf_extractor.py:286` | Classification keywords empty but not used functionally |
| W5 | P6 float errors silently converted to None | `p6_extractor.py:89-92` | Bad float data silently loses criticality information |

### 11.3 Informational Observations

| # | Observation | Location | Impact |
|---|---|---|---|
| I1 | No tests for ImageProcessor | Missing | OCR on images unverified |
| I2 | No tests for CADProcessor | Missing | DXF entity listing unverified |
| I3 | No tests for PPTX behavior | Missing | Slide content extraction unverified |
| I4 | No tests for Word behavior | Missing | Table/text extraction unverified |
| I5 | No tests for DGN processor | Partial (3 integration tests) | DGN→DXF conversion path partially covered |
| I6 | CadProcessor uses ezdxf but no V02 extractor wraps it | `cad_processor.py` | DXF files have no standardized extraction entry point |

---

## 12. Acceptance Criteria for New Extractors

Any new extractor MUST satisfy all of the following before registration in `ExtractJob.EXTRACTORS`:

### 12.1 Mandatory Tests (Minimum 5)

1. **Extension guard** — Rejects unsupported file type
2. **Empty file handling** — Returns `success=False` with diagnostic for empty/corrupted file
3. **Deterministic output** — Same input produces identical records
4. **Provenance completeness** — Every record includes valid `provenance` dict
5. **Missing dependency honesty** — Fails with named diagnostic when optional dep absent

### 12.2 Contract Compliance Checklist

- [ ] Implements `BaseExtractor` abstract interface
- [ ] `id`, `version`, `supported_extensions` all present and correct
- [ ] All records include `provenance.source` and `provenance.origin`
- [ ] No mock/fabricated data in production code path
- [ ] Optional dependency absence → `success=False` + named diagnostic
- [ ] No unhandled exceptions propagate to caller
- [ ] Results are deterministic for identical inputs
- [ ] `supported_extensions` matches actual supported formats

### 12.3 Maturity Gate

New extractors start at **EXPERIMENTAL** maturity. They advance to **VERIFIED** only after:
- ≥3 behavior tests with real or realistic fixtures
- Contract tests confirming no prohibited patterns
- Successful integration through `ExtractJob._insert_record()` into correct DB tables

They advance to **PRODUCTION** only after:
- ≥5 tests covering all failure modes
- Code review confirming no TODOs in critical paths
- Explicit maturity declaration in docstring

---

## 13. Prohibited Patterns

The following patterns are FORBIDDEN in all extractor code:

| Pattern | Example | Why |
|---|---|---|
| Mock data in production | `if "IR" in file_path: return mock_record` | Produces fabricated evidence |
| UUID-generated IDs in output | `"request_id": f"IR-{uuid.uuid4().hex[:4]}"` | Non-deterministic, unverifiable |
| Hardcoded confidence in records | `"confidence": 0.95` in record data | Misleads downstream; confidence belongs in Fact, not record |
| Silent dependency fallback | `try: import heavy_dep except: use_regex_fallback` | Hidden quality degradation |
| Absolute debug paths | `open("D:\\debug.txt", "w")` | Leaks local filesystem paths |
| Uncaught ImportError | Missing `try/except` around optional import | Crashes extraction job unexpectedly |
| Regex/text fallback for structured formats | Parsing IFC with regex when ifcopenshell unavailable | Undocumented quality loss |

---

## 14. Domain-Specific Contract Addenda

### 14.1 PDF Extractor Addendum

- Page composition routing (empty/vector/scanned/combined) is CONTRACTED — thresholds are implementation detail but must be testable
- VLM extraction path MUST remain disabled in the main routing flow (locked by test)
- Semantic block extraction is APPROACHABLE but blocks <50 chars being dropped is an accepted limitation

### 14.2 P6/XER Extractor Addendum

- Float calculation (hours → days, criticality threshold) is CONTRACTED — verified by 8 tests
- Parallel TASKPRED relations MUST be preserved (not collapsed) — verified
- Missing/malformed float MUST NOT produce false critical-path membership — verified
- Zero-duration activities treated as milestones is IMPLEMENTATION CHOICE

### 14.3 IFC Extractor Addendum

- `ifcopenshell` absence → honest failure with diagnostic — CONTRACTED
- NO regex/text fallback permitted — CONTRACTED (verified by source scan test)
- Element metadata without `ElementId` → skip with warning — CONTRACTED
- Connection records without both endpoint IDs → skip with warning — CONTRACTED

### 14.4 Office/DGN Extractor Addendum

- MUST produce only flattened `pdf_page` records — no typed persistence claims
- MUST NOT claim "typed Word/Excel/PPTX/DGN persistence" in any output
- Diagnostics and metadata must reflect flattened nature

### 14.5 Excel Register Extractor Addendum

- Header row detection is HEURISTIC — must not be claimed as deterministic
- Register rows must include `sheet_name` and `row_index` in data for traceability
- No cell-level or range-level persistence — register row only

### 14.6 Field/VLM Extractor Addendum

- Currently PLACEHOLDER — MUST NOT be registered until real VLM integration
- When implemented, VLM confidence must come from model output, not hardcoded
- All mock data patterns must be removed from production code path

---

*Document authority: BaseExtractor interface (§2), Fact models (§3 of facts/models.py), RuleRunner validation (§1), existing test contracts. This document is read-only analysis.*
