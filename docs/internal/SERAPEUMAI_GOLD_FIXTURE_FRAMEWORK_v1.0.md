# SerapeumAI Gold Fixture Framework v1.0

**Date:** 2026-09-02  
**Task:** TASK-016 — Design Gold Fixture and Evidence Quality Framework  
**Scope:** Read-only quality control design for future extractor improvements  
**Status:** FRAMEWORK DESIGN — No implementation, no code changes  

---

## 1. Purpose

This framework defines the fixture ecosystem that will underpin all future evidence-quality work. A **gold fixture** is a canonical input artifact (real file or deterministic synthetic replacement) paired with an **expected output contract** that future tests will assert against. When an extractor is upgraded, gold fixture tests prove the upgrade did not regress existing behavior.

This document does NOT modify extractors, add domains, or change authority rules. It defines the testing foundation only.

---

## 2. Fixture Categories

Four categories of test fixtures serve different purposes:

### 2.1 Category A: Golden Fixtures (Real Files)

Small, curated real-world files that represent the **canonical case** for each domain. These are checked into the repository and used as the ground truth for regression tests.

| Attribute | Requirement |
|---|---|
| **Origin** | Real AECO document (PDF spec, XER schedule, IFC model, Excel register) |
| **Size** | Minimal but representative (≤ 5 MB per file) |
| **Stability** | Immutable — never regenerated, never modified |
| **Storage** | `src/tests/fixtures/<domain>/` directory |
| **Hash** | SHA-256 recorded in fixture manifest |
| **License** | Must be open-source, permissive, or fabricated |

**Purpose:** Prove the extractor works on real data. Used for integration-level tests.

### 2.2 Category B: Synthetic Fixtures (Generated Files)

Deterministically generated files that create specific edge cases impossible or impractical with real files. Generated at test time via helper functions.

| Attribute | Requirement |
|---|---|
| **Origin** | Python helper function using `tmp_path` |
| **Determinism** | Same code → same bytes → same hash |
| **Purpose** | Edge cases, boundary conditions, known-failure modes |
| **Lifecycle** | Generated per-test, cleaned up automatically by `tmp_path` |

**Examples:**
- Empty PDF with zero pages
- XER with malformed float values
- IFC with orphaned elements (no GlobalId)
- Excel with no header row
- PDF with mixed vector/scanned/combined pages

### 2.3 Category C: Fake/Mock Fixtures (In-Memory Substitutes)

Python objects that replace external dependencies (pypdf, fitz, ifcopenshell, pandas) to isolate the extractor from system state. Used for unit-level routing tests.

| Attribute | Requirement |
|---|---|
| **Origin** | Python classes defined in the test file |
| **Isolation** | Zero filesystem I/O, zero network, zero optional deps |
| **Purpose** | Test extraction logic without requiring real files |
| **Pattern** | Monkeypatch-based injection |

**Existing examples:**
- `FakePypdfPage` / `FakeReader` / `FakeFitzDoc` in `test_pdf_routing_fixture_pack.py`
- `FakeModel` / `FakeEntity` in `test_ifc_dependency_contract.py`
- `FakeWordProcessor` / `FakePPTProcessor` in `test_office_dgn_flattened_extraction_contract.py`

### 2.4 Category D: Inline Data Fixtures (String-Based)

Self-contained data embedded directly in test source code. Used when generating a real file would add unnecessary complexity.

| Attribute | Requirement |
|---|---|
| **Origin** | String literal in test code |
| **Format** | Valid file format content (XER, SQL, JSON) |
| **Purpose** | Fast, portable, version-controlled test inputs |

**Existing examples:**
- `XER_BASE` template in `test_p6_critical_path_unknown_honesty.py`
- Test SQL INSERT statements in `test_truth_state_enforcement.py`

---

## 3. Required File Examples Per Domain

### 3.1 PDF (Category A + B)

**Golden fixtures required:**

| Fixture | Description | Expected Records |
|---|---|---|
| `pdf_vector_simple.pdf` | Single-page vector text PDF (no images) | 1 × `pdf_page` (vector), 1 × `doc_classification`, blocks |
| `pdf_scanned_single.pdf` | Single-page scanned image PDF | 1 × `pdf_page` (scanned/OCR), 1 × `doc_classification`, blocks |
| `pdf_combined_multi.pdf` | Multi-page mixed content (vector + images) | N × `pdf_page` (mixed composition), 1 × `doc_classification`, blocks |
| `pdf_empty.pdf` | Blank PDF, zero pages | 0 records, `success=True` |
| `pdf_corrupted.pdf` | Truncated/corrupted PDF bytes | `success=False`, diagnostic about parse error |

**Synthetic fixtures required:**

| Fixture | Purpose | Generation |
|---|---|---|
| `pdf_one_char_per_page.pdf` | Tests composition threshold boundaries | pypdf + PdfWriter |
| `pdf_exact_300_chars.pdf` | Tests vector vs combined boundary (text_len == 300) | pypdf + PdfWriter |
| `pdf_exact_100_chars_with_image.pdf` | Tests scanned vs combined boundary | pypdf + PdfWriter |

**Expected output contract:**

```python
# For any valid PDF extraction result:
assert result.success is True
assert isinstance(result.metadata["page_count"], int)
assert result.metadata["page_count"] == sum(
    result.metadata["page_composition_counts"].values()
)
for record in result.records:
    assert "type" in record
    assert "data" in record
    assert "provenance" in record
    assert "source" in record["provenance"]
    assert "origin" in record["provenance"]
```

### 3.2 P6/XER (Category A + D)

**Golden fixtures required:**

| Fixture | Description | Expected Records |
|---|---|---|
| `p6_standard.xer` | Clean project with 5 activities, full predecessor logic | p6_project, p6_wbs, p6_activity ×5, p6_relation ×N |
| `p6_milestone_only.xer` | Project where all activities have zero duration | All activities → milestones, no critical path |
| `p6_partial_float.xer` | Some activities missing total_float_hr_cnt | Float=None for those, no false critical-path membership |

**Inline data fixtures required (Category D):**

| Fixture | Purpose | Format |
|---|---|---|
| `xer_parallel_relations` | Two TASKPRED rows between same activity pair with different pred_type | String template |
| `xer_negative_float` | Activity with negative total_float → must be critical | String template |
| `xer_missing_float` | Activity with empty total_float_hr_cnt | String template |
| `xer_empty_task` | XER with TASK header but zero rows | String template |

**Expected output contract:**

```python
# For any valid P6 extraction:
assert result.success is True
activity_records = [r for r in result.records if r["type"].startswith("p6_")]
for rec in activity_records:
    assert rec["provenance"]["table"] == "TASK"
    assert rec["data"].get("task_id") is not None

relation_records = [r for r in result.records if r["type"] == "p6_relation"]
# Parallel relations must NOT collapse — each TASKPRED row produces one record
assert len(relation_records) == count_of_TASKPRED_rows
```

### 3.3 IFC (Category C + B)

**Golden fixtures required:**

| Fixture | Description | Expected Records |
|---|---|---|
| `ifc_simple_building.ifc` | IfcProject + IfcSite + IfcBuilding + IfcBuildingStorey + 1 element | ifc_project, ifc_spatial ×N, ifc_element_metadata, ifc_connection |

**Mock fixtures required (Category C):**

| Fixture | Purpose | Mock Level |
|---|---|---|
| `ifc_orphaned_element` | Element without GlobalId | FakeEntity missing GlobalId |
| `ifc_connection_incomplete` | Connection with only one endpoint | FakeConnection with one null endpoint |
| `ifc_no_product` | Model with only spatial structure, no products | FakeModel with empty product list |

**Expected output contract:**

```python
# For any valid IFC extraction:
for rec in result.records:
    assert "provenance" in rec
    assert "entity" in rec["provenance"]
    # No regex/text fallback should ever appear in diagnostics
    diag_text = " ".join(result.diagnostics).lower()
    assert "regex" not in diag_text
    assert "fallback" not in diag_text
```

### 3.4 Excel Register (Category B)

**Golden fixtures required:**

| Fixture | Description | Expected Records |
|---|---|---|
| `excel_standard_register.xlsx` | 3-column register (No, Description, Status) with 10 rows | 10 × register_row |

**Synthetic fixtures required:**

| Fixture | Purpose | Generation |
|---|---|---|
| `excel_no_header.xlsx` | File with data in row 1 but no keyword-matching headers | openpyxl |
| `excel_empty.xlsx` | Workbook with one empty sheet | openpyxl |
| `excel_mixed_types.xlsx` | Column with mixed string/numeric/empty values | openpyxl |

**Expected output contract:**

```python
# For any valid Excel register extraction:
register_records = [r for r in result.records if r["type"] == "register_row"]
for rec in register_records:
    assert "sheet_name" in rec["data"]
    assert "row_index" in rec["data"]
    assert "content" in rec["data"]
    assert "provenance" in rec
    assert "sheet" in rec["provenance"]
```

### 3.5 Word / PPTX / DGN (Category C + B)

These produce flattened `pdf_page` records. The gold fixture requirement is lower priority — contract tests (no typed persistence claims) are sufficient for now.

| Extractor | Current Coverage | Gap |
|---|---|---|
| Word | 1 contract test (fake processor) | No real .docx test; no content quality check |
| PPTX | 1 contract test (fake processor) | No real .pptx test; no slide content check |
| DGN | 3 integration tests (fake processor) | No real .dgn test; ODA dependency untested |

**Future golden fixtures (when ready):**

| Fixture | Description |
|---|---|
| `word_simple.docx` | Single paragraph + one table |
| `pptx_simple.pptx` | One title slide + one body slide |
| `dgn_simple.dgn` | MicroStation file with one XREF reference |

### 3.6 Field/VLM (Category C Only — PLACEHOLDER)

No golden or synthetic fixtures. The extractor is PLACEHOLDER maturity and must not be registered. Test fixtures only exist to verify it stays in STAGING.

### 3.7 DXF / DWG / Images (No Fixtures — No Extractor)

These domains have no V02 extractor. CADProcessor and ImageProcessor exist in the V01 layer but are untested. Future extraction work for these domains MUST define fixtures BEFORE implementation.

---

## 4. Expected Extraction Outputs

### 4.1 Record-Type Catalog

Every extractor must produce records from the following allowed types:

| Record Type | Extractor | Table | Provenance Required |
|---|---|---|---|
| `pdf_page` | UniversalPdfExtractor | `pdf_pages`, `pages` | `source`, `origin`, `composition`, `method`, `page` |
| `doc_classification` | UniversalPdfExtractor | `doc_classifications` | `source`, `origin`, `keywords_found` |
| `doc_blocks` | UniversalPdfExtractor | `doc_blocks` | `method` |
| `p6_project` | P6Extractor | `p6_projects` | `table` |
| `p6_wbs` | P6Extractor | `p6_wbs` | `table` |
| `p6_activity` | P6Extractor | `p6_activities` | `table`, `has_logic` |
| `p6_relation` | P6Extractor | `p6_relations` | `table` |
| `ifc_project` | IFCExtractor | `ifc_projects` | `entity` |
| `ifc_spatial` | IFCExtractor | `ifc_spatial_structure` | `entity` |
| `ifc_element_metadata` | IFCExtractor | `ifc_elements` | `entity`, `pset` |
| `ifc_connection` | IFCExtractor | `links` | `entity` |
| `register_row` | ExcelRegisterExtractor | `register_rows` | `sheet`, `row` |
| `field_request` | FieldExtractor | `field_requests` | `source` ← PLACEHOLDER, must not reach pipeline |
| `pdf_page` (flattened) | Word/PPTX/DGN Extractors | `pages` | `source`, `origin` |

### 4.2 Determinism Contract

For any given golden fixture file, the extraction output must be **byte-for-byte identical** across runs:

```python
# Golden fixture determinism check
result_a = extractor.extract(fixture_path)
result_b = extractor.extract(fixture_path)
assert result_a.records == result_b.records
assert result_a.diagnostics == result_b.diagnostics
assert result_a.metadata == result_b.metadata
```

**Exempt fields (non-deterministic, allowed):** None. All output must be deterministic. Diagnostics that include timestamps or UUIDs are a contract violation.

### 4.3 Provenance Completeness Contract

Every record MUST pass this schema validation:

```python
def validate_provenance(record: Dict) -> bool:
    prov = record.get("provenance")
    if not prov or not isinstance(prov, dict):
        return False
    if "source" not in prov or not prov["source"]:
        return False
    if "origin" not in prov or not prov["origin"]:
        return False
    return True
```

---

## 5. Regression Rules

### 5.1 Golden Fixture Regression Rule

When any extractor is upgraded (maturity change, bug fix, feature addition), ALL golden fixture tests for that domain MUST pass. A regression is defined as:

| Condition | Classification | Action |
|---|---|---|
| Record count changes for same input | 🔴 **FAILURE** | Block merge |
| Record type changes | 🔴 **FAILURE** | Block merge |
| Provenance fields missing | 🔴 **FAILURE** | Block merge |
| Determinism broken (same input → different output) | 🔴 **FAILURE** | Block merge |
| New diagnostic warnings added | 🟡 **WARNING** | Document and justify |
| New record types added (with approval) | 🟢 **INFO** | Update fixture catalog |

### 5.2 Fixture Versioning Rule

Each golden fixture has a version number in its metadata:

```
src/tests/fixtures/pdf/golden_v1/pdf_vector_simple.pdf  → version 1
src/tests/fixtures/p6/golden_v1/xer_standard.xer        → version 1
```

When a fixture is updated (content change), the version must increment and a migration note must explain why. Old fixture versions are preserved for backward-compatibility tests.

### 5.3 New Domain Entry Rule

Before any new V02 extractor is implemented, the following must exist:

1. **At least 1 golden fixture** (real file) or **3 synthetic fixtures** (edge cases)
2. **Expected output contract** defined in this document
3. **Provenance completeness test** asserting all records have valid provenance
4. **Determinism test** asserting byte-for-byte reproducibility
5. **Maturity assignment** (defaults to EXPERIMENTAL until ≥3 behavior tests exist)

### 5.4 Maturity Advancement Rule

An extractor advances through maturity levels based on fixture test coverage:

| Current → Target | Requirement |
|---|---|
| PLACEHOLDER → EXPERIMENTAL | No mock data in production code; documented limitations |
| EXPERIMENTAL → VERIFIED | ≥3 behavior tests with synthetic fixtures; all provenance validated |
| VERIFIED → PRODUCTION | ≥5 behavior tests including golden fixture; all failure modes covered |

---

## 6. Acceptance Criteria for Future Extractor Upgrades

### 6.1 Pre-Upgrade Checklist

Before any code change to an extractor, verify:

- [ ] Current golden fixture tests are green
- [ ] Maturity level is documented on the class
- [ ] No TODO/FIXME markers in critical paths
- [ ] Optional dependency handling is honest (success=False + named diagnostic)
- [ ] No mock/fabricated data in production code

### 6.2 Post-Upgrade Checklist

After any code change to an extractor, verify:

- [ ] All current golden fixture tests pass
- [ ] All synthetic fixture tests pass
- [ ] All fake/mock isolation tests pass
- [ ] Determinism verified (two consecutive runs produce identical output)
- [ ] Provenance completeness verified on all output records
- [ ] No new prohibited patterns introduced (mock data, silent fallbacks, debug paths)
- [ ] Method ID unchanged (or intentionally changed with documentation)
- [ ] DB persistence contract unchanged (records still insert into correct tables)

### 6.3 Maturity Upgrade Criteria

To promote an extractor's maturity rating:

| Promotion | Requirements |
|---|---|
| EXPERIMENTAL → VERIFIED | 3+ behavioral tests with synthetic fixtures; no mock data; honest dependency handling |
| VERIFIED → PRODUCTION | 5+ tests covering routing, edge cases, persistence, dependency failure; code review clean |

### 6.4 Regression Testing Matrix

Every domain must maintain this minimum test matrix:

| Test Type | Minimum Count | Example |
|---|---|---|
| Golden fixture test | ≥1 | Real file → expected records |
| Synthetic edge case test | ≥2 | Empty file, corrupted file, boundary values |
| Determinism test | ≥1 | Same input → same output |
| Provenance completeness test | ≥1 | All records have source + origin |
| Dependency failure test | ≥1 | Missing dep → success=False + diagnostic |
| Persistence contract test | ≥1 | Records insert into correct DB tables |

---

## 7. Fixture Directory Structure

```
src/tests/fixtures/
├── __init__.py
├── README.md                         # Fixture manifest with SHA-256 hashes
│
├── pdf/
│   ├── golden_v1/
│   │   ├── pdf_vector_simple.pdf     # 1 page, vector text only
│   │   ├── pdf_scanned_single.pdf    # 1 page, scanned image
│   │   └── pdf_combined_multi.pdf    # 4 pages, mixed content
│   ├── synthetic/                    # Generated at test time
│   │   └── (no files — generated via helpers)
│   └── expected_outputs/
│       ├── pdf_vector_simple.json    # Canonical output contract
│       ├── pdf_scanned_single.json
│       └── pdf_combined_multi.json
│
├── p6/
│   ├── golden_v1/
│   │   └── p6_standard.xer           # 5-activity project with full logic
│   └── inline/                       # String templates (Category D)
│       └── xer_templates.py          # XER_BASE, xer_parallel_relations, etc.
│
├── ifc/
│   ├── golden_v1/
│   │   └── ifc_simple_building.ifc    # Minimal IFC with spatial hierarchy
│   └── fake/                         # FakeEntity/FakeModel classes
│       └── ifc_fixtures.py
│
├── excel/
│   ├── golden_v1/
│   │   └── excel_standard_register.xlsx
│   └── synthetic/                    # Generated via openpyxl helpers
│
├── word/
│   └── (contract tests only — no golden fixtures yet)
│
├── pptx/
│   └── (contract tests only — no golden fixtures yet)
│
└── dgn/
    └── (integration tests only — no golden fixtures yet)
```

---

## 8. Current State vs. Target State

### 8.1 What Exists Today

| Domain | Golden Fixtures | Synthetic Fixtures | Fake/Mock Fixtures | Inline Data | Total Tests |
|---|---|---|---|---|---|
| PDF | ✅ 4 fixture tests | ✅ Threshold boundaries | ✅ FakeReader/FakeDoc | — | 14 |
| P6 | ❌ None | ❌ None | — | ✅ XER_BASE templates | 8 |
| IFC | ❌ None | ❌ None | ✅ FakeModel/FakeEntity | — | 5 |
| Excel | ❌ None | ❌ None | ✅ Fake read_excel | — | 1 |
| Word | ❌ None | ❌ None | ✅ FakeWordProcessor | — | 1 |
| PPTX | ❌ None | ❌ None | ✅ FakePPTProcessor | — | 1 |
| DGN | ❌ None | ❌ None | ✅ Fake process() | — | 3 |
| Field | ❌ None | ❌ None | N/A (PLACEHOLDER) | — | 0 |
| DXF/DWG | ❌ None | ❌ None | ❌ None | — | 0 |
| Images | ❌ None | ❌ None | ❌ None | — | 0 |

### 8.2 Target State (Wave A Completion)

| Domain | Golden Fixtures | Behavior Tests | Maturity | Gate Status |
|---|---|---|---|---|
| PDF | 3 golden + 3 synthetic | 14 | PRODUCTION | ✅ Trusted |
| P6 | 1 golden + 4 synthetic | 8 | PRODUCTION | ✅ Trusted |
| IFC | 1 golden + 3 synthetic | 5 | VERIFIED | ✅ Trusted |
| Excel | 1 golden + 3 synthetic | ≥5 | EXPERIMENTAL → VERIFIED | Staging |
| Word | 1 golden + 2 synthetic | ≥4 | VERIFIED → PRODUCTION | ✅ Trusted |
| PPTX | 1 golden + 2 synthetic | ≥4 | VERIFIED → PRODUCTION | ✅ Trusted |
| DGN | 1 golden + 2 synthetic | ≥5 | EXPERIMENTAL | Staging |
| Field | N/A | 0 (PLACEHOLDER) | PLACEHOLDER | 🚫 Blocked |
| DXF | TBD (future) | 0 | PLACEHOLDER | 🚫 Not registered |
| DWG | TBD (future) | 0 | PLACEHOLDER | 🚫 Not registered |
| Images | TBD (future) | 0 | PLACEHOLDER | 🚫 Not registered |

---

## 9. Quality Gates for Wave A Progression

Before Wave A is considered complete, the following gates must be satisfied:

### 9.1 Mandatory Gates

| Gate | Criterion | Current | Target |
|---|---|---|---|
| **M1: Core domain golden fixtures** | ≥1 golden fixture per PRODUCTION/VERIFIED domain | PDF ✅, P6 ❌, IFC ❌ | PDF ✅, P6 ✅, IFC ✅ |
| **M2: Synthetic edge case coverage** | ≥2 synthetic fixtures per domain | PDF ✅, P6 ❌, IFC ❌ | All domains ✅ |
| **M3: Determinism verification** | Byte-for-byte identical output on re-run | Unverified | Verified for all |
| **M4: Provenance completeness** | Every record has source + origin | Partially tested | 100% tested |
| **M5: Dependency honesty** | Missing dep → success=False + named diagnostic | IFC ✅, others ⚠️ | All ✅ |

### 9.2 Optional Gates (Future Waves)

| Gate | Criterion | Status |
|---|---|---|
| O1: Image processing tests | ImageProcessor + gold fixture | ❌ Not started |
| O2: DXF extractor | V02 extractor with gold fixture | ❌ Not started |
| O3: DWG support | Via ODA or explicit rejection | ❌ Not started |
| O4: Field/VLM real implementation | Replace mock with actual VLM call | ❌ Placeholder |
| O5: Classifier implementation | Replace stub with working classifier | ❌ Stub |

---

## 10. Summary

The Gold Fixture Framework establishes a **testable, versioned, regression-proof foundation** for all future evidence-quality work:

1. **Four fixture categories** serve different testing needs (golden, synthetic, fake, inline)
2. **Domain-specific expected outputs** are defined per record type
3. **Regression rules** prevent silent quality degradation during upgrades
4. **Maturity advancement** is gated on fixture test coverage
5. **Directory structure** provides a clear organizational model

**No code changes are made by this document.** It is a design specification for future implementation work.

---

*Document authority: SERAPEUMAI_EVIDENCE_QUALITY_BASELINE_v1.0, SERAPEUMAI_EVIDENCE_QUALITY_CONTRACT_v1.0, SERAPEUMAI_EVIDENCE_TRUST_REGRESSION_BASELINE_v1.0, SERAPEUMAI_EVIDENCE_TRUST_INTEGRATION_VALIDATION_v1.0. This is a read-only design artifact.*
