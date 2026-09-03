# SerapeumAI Gold Fixture Implementation Plan v1.0

**Date:** 2026-09-02  
**Task:** TASK-017 — Gold Fixture Implementation Plan  
**Scope:** Design-only executable plan for establishing gold fixture infrastructure  
**Status:** PLAN ONLY — No code changes, no fixture creation, no dependency changes

**Modernization note (2026-09-03):** Per `SERAPEUMAI_PARKED_PLAN_MODERNIZATION_v1.0.md` §6, this plan gains **fixture placeholders** that are gated by future bounded packets:
- **CAD fixture placeholder** — gated by `SERAPEUMAI_CAD_DRAWING_INTELLIGENCE_PLAN_v1.0.md` packets CAD-PP-1 / CAD-PP-2 (Gate G3-G4).
- **Vision/OCR fixture placeholder** — gated by Post-Publish Upgrade Plan Upgrade 5 (Gate G6-G7).

No existing PDF/P6/IFC/Office/Excel sections are modified by this note.  

---

## 1. Current State Assessment

### 1.1 Existing Test Infrastructure

| Item | Status | Details |
|---|---|---|
| **Test runner** | `pytest` via `py -m pytest src/tests/` | 770 tests, 9.8s |
| **CI pipeline** | GitHub Actions `windows-latest`, Python 3.12.10 | Runs `python -m pytest -q src/tests` |
| **No conftest.py** | Project root | No global fixtures or hooks defined |
| **No test fixtures dir** | `src/tests/fixtures/` does not exist | All test data is inline or synthetic |
| **No requirements-lock.txt** | Not found at repo root | CI uses `requirements-lock.txt` per `.github/workflows/ci.yml` |
| **Existing fixture test** | `test_pdf_routing_fixture_pack.py` (5.9 KB) | Uses fake objects + monkeypatch, no real files |

### 1.2 Existing Test Patterns by Domain

| Domain | Test File(s) | Pattern Used | Size |
|---|---|---|---|
| **PDF** | `test_pdf_routing.py` (1.3 KB) | Fake objects + monkeypatch | Small |
| **PDF** | `test_pdf_metadata_completeness.py` (3.4 KB) | Real PDF via `pypdf.PdfWriter` | Medium |
| **PDF** | `test_pdf_routing_fixture_pack.py` (5.9 KB) | FakeReader/FakeDoc + monkeypatch | Large |
| **P6** | `test_p6_critical_path_unknown_honesty.py` (5.7 KB) | Inline XER string templates | Large |
| **P6** | `test_p6_relation_fidelity.py` (3.7 KB) | Inline XER string templates | Medium |
| **P6** | `test_p6_truth.py` (2.7 KB) | Inline XER string literal | Small |
| **IFC** | `test_ifc_dependency_contract.py` (4.2 KB) | Fake ifcopenshell modules | Medium |
| **IFC** | `test_ifc_extractor_persistence_contract.py` (3.0 KB) | DB schema + direct record inserts | Small |
| **Office/DGN** | `test_office_dgn_flattened_extraction_contract.py` (26 KB) | Fake processor classes + monkeypatch | Large |
| **Excel** | `test_excel_register_extractor_hygiene.py` (small) | Fake pandas read_excel | Tiny |
| **DGN** | `test_dgn_integration.py` (2.4 KB) | Module import checks only | Small |

### 1.3 Key Observations

1. **No real test fixture files exist** in the repository. All "fixtures" are either:
   - In-memory fake objects (monkeypatched)
   - Inline string templates (XER_BASE)
   - Synthetically generated via library APIs (PdfWriter)
2. **The CI runs from `python` command** which hits the Windows App Execution Alias — it works because the GitHub Action sets up Python explicitly via `actions/setup-python`
3. **No centralized conftest.py** exists, but that's fine — fixtures can live in individual test files
4. **PDF already has a partial golden-fixture pattern**: `test_pdf_metadata_completeness.py` generates a real PDF with `PdfWriter` and validates metadata extraction

---

## 2. Proposed Fixture Folder Structure

```
src/tests/
├── __init__.py
├── conftest.py                                          # [FUTURE] shared fixtures
│
├── fixtures/                                            # NEW: golden fixture storage
│   ├── __init__.py
│   ├── MANIFEST.md                                      # NEW: fixture registry with SHA-256 hashes
│   │
│   ├── pdf/
│   │   ├── golden_v1/
│   │   │   ├── pdf_vector_simple.pdf                    # 1 page, vector text only
│   │   │   ├── pdf_scanned_single.pdf                   # 1 page, scanned image
│   │   │   └── pdf_combined_multi.pdf                   # 4 pages, mixed content
│   │   └── expected_outputs/
│   │       └── pdf_vector_simple.json                   # Canonical output contract
│   │
│   ├── p6/
│   │   ├── golden_v1/
│   │   │   └── p6_standard.xer                          # 5-activity project, full logic
│   │   └── inline_templates.py                          # [NEW] XER_BASE moved from tests
│   │
│   ├── ifc/
│   │   ├── golden_v1/
│   │   │   └── ifc_simple_building.ifc                  # Minimal valid IFC model
│   │   └── fake_models.py                               # [NEW] FakeModel reused from tests
│   │
│   ├── excel/
│   │   ├── golden_v1/
│   │   │   └── excel_standard_register.xlsx              # 3-col register, 10 rows
│   │   └── helpers.py                                   # [NEW] openpyxl generation helpers
│   │
│   └── office/
│       ├── word_golden.docx                              # Placeholder for future
│       └── pptx_golden.pptx                              # Placeholder for future
│
└── (existing test files remain unchanged)
```

### 2.1 Rationale

- **`fixtures/` lives under `src/tests/`** to keep test-relative paths simple (`Path(__file__).resolve().parent / "fixtures"`)
- **Version subdirectories (`golden_v1/`)** allow fixture evolution without breaking old tests
- **`MANIFEST.md`** provides a single source of truth for fixture inventory, hashes, and maturity status
- **`inline_templates.py` and `helpers.py`** consolidate shared test utilities that currently duplicate across test files
- **No `conftest.py` yet** — shared fixtures can be added later when multiple tests need them

---

## 3. Naming Convention

### 3.1 Fixture File Names

```
{domain}_{scenario}_v{version}.{extension}
```

| Component | Allowed Values | Example |
|---|---|---|
| `domain` | `pdf`, `p6`, `ifc`, `excel`, `word`, `pptx`, `dgn`, `image` | `pdf_vector_simple` |
| `scenario` | Descriptive behavior being tested | `vector_simple`, `scanned_single`, `combined_multi`, `standard`, `empty` |
| `version` | Semantic version starting at `v1` | `v1` |
| `extension` | Matches the file format | `.pdf`, `.xer`, `.ifc`, `.xlsx` |

### 3.2 Test File Names

```
test_{domain}_{behavior}_with_{fixture_name}.py
```

Or keep existing names and add fixture parameters:

```python
# Current pattern (keep):
test_pdf_routing_fixture_pack.py
test_p6_critical_path_unknown_honesty.py

# New pattern (add):
test_pdf_golden_vector_simple.py        # Tests golden fixture against PDF extractor
test_p6_golden_standard.py              # Tests golden XER against P6 extractor
test_ifc_golden_simple_building.py      # Tests golden IFC against IFC extractor
```

### 3.3 Expected Output File Names

```
{fixture_name}_expected.json
```

Example: `pdf_vector_simple_expected.json`

---

## 4. Priority Order for Golden Fixture Deployment

### Phase 1: PDF (Already Partially Covered)

**Current state:** 14 tests, PRODUCTION maturity, synthetic fixtures via PdfWriter

**Gap:** No golden fixture with a real `.pdf` file on disk

**Implementation steps:**

1. Create `src/tests/fixtures/pdf/golden_v1/pdf_vector_simple.pdf`
   - Generated with `pypdf.PdfWriter` + minimal text content
   - 1 page, pure vector, no images
   - Contains known text strings for assertion

2. Create `src/tests/fixtures/pdf/golden_v1/pdf_combined_multi.pdf`
   - 4 pages: empty, vector, scanned (fake), combined
   - Reuses existing `test_pdf_routing_fixture_pack.py` pattern but with real file on disk

3. Add `test_pdf_golden_vector_simple.py`
   - Loads real `.pdf` from fixtures directory
   - Runs `UniversalPdfExtractor.extract()`
   - Asserts record count, provenance completeness, determinism
   - Compares output hash against `expected_outputs/pdf_vector_simple.json`

4. Add determinism test
   - Run extractor twice on same file
   - Assert byte-identical results

**Estimated effort:** 2 new test files, 2 golden fixtures (~10 KB total)

### Phase 2: P6/XER (Inline Templates → Golden Fixtures)

**Current state:** 8 tests, PRODUCTION maturity, all use inline XER string templates

**Gap:** No real `.xer` file on disk; all input is string templates written per-test

**Implementation steps:**

1. Extract `XER_BASE` template from `test_p6_critical_path_unknown_honesty.py` into `src/tests/fixtures/p6/inline_templates.py`
   - Reusable across all P6 tests
   - Contains: standard project, parallel relations, negative float, missing float, empty task variants

2. Create `src/tests/fixtures/p6/golden_v1/p6_standard.xer`
   - 5 activities, full predecessor logic, mixed float values
   - Written once, used by all P6 golden fixture tests

3. Create `src/tests/fixtures/p6/golden_v1/p6_malformed_float.xer`
   - Same structure but with corrupted float values
   - Tests honest failure handling

4. Add `test_p6_golden_standard.py`
   - Loads real `.xer` from fixtures
   - Runs `P6Extractor.extract()` + `ScheduleBuilder.build()`
   - Asserts activity count, critical path membership, relation fidelity
   - Verifies all records have valid provenance

5. Add `test_p6_golden_determinism.py`
   - Run extractor twice on same file
   - Assert identical record lists and diagnostics

**Estimated effort:** 1 module refactor + 2 new test files + 2 golden fixtures

### Phase 3: IFC (Mock Objects → Golden Fixture)

**Current state:** 5 tests, VERIFIED maturity, all use `FakeModel` monkeypatch

**Gap:** No real `.ifc` file on disk; extraction tested only via mocked `ifcopenshell`

**Implementation steps:**

1. Create `src/tests/fixtures/ifc/fake_models.py`
   - Extract `FakeModel`, `FakeEntity`, `FakeConnection` from `test_ifc_dependency_contract.py`
   - Shared module for all IFC tests

2. Create `src/tests/fixtures/ifc/golden_v1/ifc_simple_building.ifc`
   - Minimal valid IFC2x3 file with: IfcProject, IfcSite, IfcBuilding, IfcBuildingStorey, 1 IfcWall
   - Can be generated with `ifcopenshell` if available, or hand-crafted IFC text

3. Add `test_ifc_golden_simple_building.py`
   - Loads real `.ifc` from fixtures
   - Runs `IFCExtractor.extract()` (may skip if ifcopenshell unavailable)
   - Asserts record types, provenance completeness, entity hierarchy
   - Tests both success and missing-dependency paths

**Estimated effort:** 1 refactor + 1 new test file + 1 golden fixture

### Phase 4: Office (Word/PPTX/DGN)

**Current state:** 6 contract tests, VERIFIED maturity, all use fake processors

**Gap:** No real `.docx`, `.pptx`, or `.dgn` files; no content extraction tests

**Implementation steps:**

1. Create `src/tests/fixtures/office/word_golden.docx`
   - 1 paragraph + 1 table via `python-docx`
   - Minimal content with known strings

2. Create `src/tests/fixtures/office/pptx_golden.pptx`
   - 1 title slide + 1 body slide via `python-pptx`
   - Minimal content with known strings

3. Add `test_word_golden_flattened.py`
   - Loads real `.docx`
   - Runs `WordExtractor.extract()`
   - Asserts flattened `pdf_page` output, provenance, no typed persistence claims

4. Add `test_pptx_golden_flattened.py`
   - Same pattern for PPTX

**Note:** DGN requires ODA converter (not installed). Skip golden fixture until ODA is available.

**Estimated effort:** 2 golden fixtures + 2 new test files

### Phase 5: Remaining Domains (Excel Register Enhancement)

**Current state:** 1 hygiene test, EXPERIMENTAL maturity

**Gap:** No behavioral tests for header detection or row mapping

**Implementation steps:**

1. Create `src/tests/fixtures/excel/helpers.py`
   - `create_register_sheet(workbook, headers, rows)` using openpyxl

2. Create `src/tests/fixtures/excel/golden_v1/excel_standard_register.xlsx`
   - 3 columns: Doc No, Status, Revision
   - 10 data rows with known values

3. Add `test_excel_golden_register.py`
   - Loads real `.xlsx`
   - Runs `ExcelRegisterExtractor.extract()`
   - Asserts row count, sheet_name, row_index, content keys

4. Add `test_excel_synthetic_no_header.py`
   - Generates Excel with no keyword-matching headers
   - Asserts graceful fallback (header=0, no false positives)

**Estimated effort:** 1 module + 1 golden fixture + 2 new test files

---

## 5. Required Metadata Per Fixture

Each golden fixture must have a corresponding entry in `MANIFEST.md`:

```markdown
## pdf_vector_simple (v1)

| Field | Value |
|---|---|
| **Source type** | Synthetic PDF (pypdf.PdfWriter) |
| **Expected extractor** | UniversalPdfExtractor (`pdf`) |
| **Maturity level** | PRODUCTION |
| **File size** | ~2 KB |
| **SHA-256** | `<hash>` |
| **Expected record count** | 3 (1 pdf_page + 1 doc_classification + 1 doc_blocks) |
| **Expected provenance fields** | `source`, `origin`, `composition`, `method`, `page` |
| **Regression test** | `test_pdf_golden_vector_simple.py` |
| **Notes** | Pure vector, 1 page, contains "Generator room is inscope" text |
```

### 5.1 Metadata Fields

| Field | Required | Description |
|---|---|---|
| `source_type` | Yes | How the fixture was created (synthetic, hand-crafted, exported) |
| `expected_extractor` | Yes | Which V02 extractor processes this fixture |
| `maturity_level` | Yes | Matcher extractor maturity: PRODUCTION, VERIFIED, EXPERIMENTAL, PLACEHOLDER |
| `file_size_bytes` | Yes | For regression detection |
| `sha256` | Yes | Content hash for change detection |
| `expected_record_types` | Yes | Set of record `type` values expected |
| `expected_record_count_min` | Yes | Minimum record count (allows expansion) |
| `expected_provenance_fields` | Yes | Required keys in each record's `provenance` dict |
| `regression_test` | Yes | Test file that asserts this fixture |
| `notes` | No | Additional context |

---

## 6. CI Integration Approach

### 6.1 Current CI Flow

```
push to main → checkout → setup-python 3.12.10 → pip install -r requirements-lock.txt
→ compileall → pytest -q src/tests
```

### 6.2 Fixture Integration Changes

**No changes required to CI configuration.** The existing `pytest -q src/tests` command will discover and run new fixture tests automatically because:

1. `src/tests/fixtures/` is under `src/tests/` — pytest collects from there
2. No `conftest.py` needed — fixtures are loaded via `Path(__file__)` relative paths
3. No new dependencies — all fixture generation uses existing packages (`pypdf`, `openpyxl`, etc.)

### 6.3 Optional CI Enhancements (Future)

| Enhancement | Purpose | Effort |
|---|---|---|
| **Fixture hash verification** | Add step to check `MANIFEST.md` hashes match actual files | Low |
| **Fixture count assertion** | Assert minimum number of golden fixtures per domain | Low |
| **Determinism check** | Run each golden fixture test twice, compare outputs | Medium |

These are **not required** for initial deployment.

---

## 7. Migration Plan: Current Tests → Fixture-Based Tests

### 7.1 Strategy: Additive, Not Rewriting

**Do NOT rewrite existing tests.** The current test suite (770 tests) must continue passing. New fixture-based tests coexist alongside existing ones.

### 7.2 Migration Phases

| Phase | Domain | Action | Risk |
|---|---|---|---|
| **1** | PDF | Add `test_pdf_golden_vector_simple.py` alongside existing 14 PDF tests | 🟢 None — additive only |
| **2** | P6 | Extract XER_BASE to `fixtures/p6/inline_templates.py`, add `test_p6_golden_standard.py` | 🟢 Low — refactor shared template |
| **3** | IFC | Extract fake models to `fixtures/ifc/fake_models.py`, add `test_ifc_golden_simple_building.py` | 🟢 Low — refactor shared mocks |
| **4** | Office | Add `test_word_golden_flattened.py` and `test_pptx_golden_flattened.py` | 🟢 None — additive only |
| **5** | Excel | Add `test_excel_golden_register.py` alongside existing hygiene test | 🟢 None — additive only |

### 7.3 Test Coexistence Rules

1. **Old tests keep their current pattern** (fake objects, inline templates, monkeypatch)
2. **New fixture tests add a parallel golden-fixture assertion**
3. **If a new fixture test fails, it does not block merging the existing test suite**
4. **Golden fixture tests should be marked with `@pytest.mark.golden_fixture`** to enable selective skipping

### 7.4 Example: PDF Golden Fixture Test

```python
# test_pdf_golden_vector_simple.py  (NEW — additive)
import hashlib
from pathlib import Path

import pytest
from pypdf import PdfWriter

from src.engine.extractors.pdf_extractor import UniversalPdfExtractor


FIXTURE_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "pdf" / "golden_v1"


def _make_vector_pdf(path: Path) -> None:
    """Generate a deterministic 1-page vector PDF."""
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    # Add known text that the extractor will route as 'vector'
    writer.add_page_text(0, "Generator room is inscope.\nArea is 377 sqm Approx.")
    with path.open("wb") as f:
        writer.write(f)


@pytest.fixture(scope="session")
def pdf_vector_simple(tmp_path_factory):
    path = tmp_path_factory.mktemp("fixtures") / "pdf_vector_simple.pdf"
    if not path.exists():
        _make_vector_pdf(path)
    return path


def test_golden_pdf_vector_simple_deterministic(pdf_vector_simple):
    extractor = UniversalPdfExtractor()
    result_a = extractor.extract(str(pdf_vector_simple))
    result_b = extractor.extract(str(pdf_vector_simple))
    assert result_a.records == result_b.records
    assert result_a.diagnostics == result_b.diagnostics


def test_golden_pdf_vector_simple_provenance_complete(pdf_vector_simple):
    result = UniversalPdfExtractor().extract(str(pdf_vector_simple))
    assert result.success is True
    for rec in result.records:
        prov = rec.get("provenance", {})
        assert "source" in prov and prov["source"]
        assert "origin" in prov and prov["origin"]


def test_golden_pdf_vector_simple_expected_record_types(pdf_vector_simple):
    result = UniversalPdfExtractor().extract(str(pdf_vector_simple))
    record_types = {r["type"] for r in result.records}
    assert "pdf_page" in record_types
    assert "doc_classification" in record_types
```

This test is **fully additive** — it does not modify or replace any existing test.

---

## 8. Estimated Test Count Growth

| Phase | New Tests | Total Expected |
|---|---|---|
| Current baseline | — | 770 |
| Phase 1 (PDF) | +3 | 773 |
| Phase 2 (P6) | +3 | 776 |
| Phase 3 (IFC) | +2 | 778 |
| Phase 4 (Office) | +2 | 780 |
| Phase 5 (Excel) | +2 | 782 |
| **Target** | **+12** | **~782** |

All growth is additive. Zero existing tests are modified or removed.

---

## 9. Summary

| Item | Detail |
|---|---|
| **New directories** | 1: `src/tests/fixtures/` with domain subdirs |
| **New files (non-test)** | `fixtures/__init__.py`, `fixtures/MANIFEST.md`, 5 helper modules |
| **New golden fixtures** | ~7 real/synthetic files (~30 KB total) |
| **New test files** | ~12 test files (additive) |
| **Modified existing tests** | 0 |
| **Schema changes** | 0 |
| **Dependency changes** | 0 |
| **CI changes** | 0 |

**Total implementation cost:** ~20 new files, ~30 KB of fixture data, ~12 new tests. All additive. No existing code touched.

---

*This document is an analysis/design artifact. No code was modified. No fixtures were created.*
