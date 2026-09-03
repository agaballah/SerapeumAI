# SerapeumAI Test Fixture Manifest v1.0

**Maintained by:** Evidence Quality Foundation (TASK-016 / TASK-017)
**Created:** 2026-09-02
**Status:** Active — pilot phase (PDF domain)

---

## Purpose

This manifest records all golden fixture files used for evidence-quality regression testing. Each entry includes the file path, SHA-256 hash, size, expected extractor, maturity level, and the test file that consumes it.

**Golden fixtures are immutable.** Any change to a fixture requires:
1. Updating this manifest with the new hash
2. Bumping the version subdirectory (e.g., `golden_v1` → `golden_v2`)
3. Adding a migration note explaining the change
4. Ensuring all consuming tests pass against the new fixture

---

## PDF Domain (`fixtures/pdf/golden_v1/`)

| Fixture | Size | SHA-256 | Extractor | Maturity | Regression Test | Notes |
|---|---|---|---|---|---|---|
| `pdf_vector_simple.pdf` | 1253 B | `bafcbf977d225a3962a7d351fa2cbad332fc4384bf145e193bae8dd4b86f01f5` | `UniversalPdfExtractor` (`pdf`) | PRODUCTION | `test_pdf_golden_vector_simple.py` | 1 page, pure vector text, contains known strings for assertion |
| `pdf_combined_multi.pdf` | 2521 B | `a8f5bcc22464484657483d68d1027e8149ce4af5145799544ea1744839bcc639` | `UniversalPdfExtractor` (`pdf`) | PRODUCTION | `test_pdf_golden_combined_multi.py` | 4 pages, all vector, tests multi-page record count + provenance |

### Expected Output Contracts

#### `pdf_vector_simple.pdf`
- `result.success` == `True`
- Record count == 3 (`pdf_page`, `doc_classification`, `doc_blocks`)
- Page 1 composition == `"vector"`, method == `"pypdf_vector"`
- All records have `provenance.source` and `provenance.origin` populated
- Deterministic: two runs produce identical `records`, `diagnostics`, and `metadata`

#### `pdf_combined_multi.pdf`
- `result.success` == `True`
- Record count >= 6 (4 × `pdf_page` + `doc_classification` + `doc_blocks`)
- All pages composition == `"vector"`, method == `"pypdf_vector"`
- `metadata.page_composition_counts.vector` == 4
- `metadata.pdf_page_count` == 4
- All records have valid provenance

---

---

## P6/XER Domain (`fixtures/p6/golden_v1/`)

| Fixture | Size | SHA-256 | Extractor | Maturity | Regression Test | Notes |
|---|---|---|---|---|---|---|
| `p6_standard.xer` | 767 B | `22d831648978f614522415f04b3943bbb44c0a807c5785e7abf12caca5ea9b93` | `P6Extractor` (`p6`) | PRODUCTION | `test_p6_golden_standard.py` | 5 activities, 4 relations, mixed float values |
| `p6_malformed_float.xer` | 620 B | `adb7efc79eb601b3dd973703a4cdcb755731c4bfa3ec984e383ca66d70a2d5f7` | `P6Extractor` (`p6`) | PRODUCTION | `test_p6_golden_malformed_float.py` | Missing/non-numeric floats → honest None values |

### Expected Output Contracts

#### `p6_standard.xer`
- `result.success` == `True`
- Record count == 11 (1 × p6_project + 1 × p6_wbs + 5 × p6_activity + 4 × p6_relation)
- All `p6_activity` records have valid `task_id`, `task_code`, and `provenance.table == "TASK"`
- All `p6_relation` records have valid `pred_task_id`, `succ_activity_id`, and `provenance.table == "TASKPRED"`
- A-001 has negative float (-8 hrs = -1 day) → `is_critical=True`
- A-002 has zero float → `is_critical=True`
- Float normalization: hours→days applied correctly

#### `p6_malformed_float.xer`
- `result.success` == `True`
- 3 activity records produced (no crash on bad data)
- All three activities have `total_float=None`, `is_critical=False`
- No false critical-path membership emitted for missing/malformed floats
- Provenance complete on all records

---

---

## IFC Domain (`fixtures/ifc/golden_v1/`)

| Fixture | Size | SHA-256 | Extractor | Maturity | Regression Test | Notes |
|---|---|---|---|---|---|---|
| `ifc_simple_building.ifc` | 1213 B | `b898368703adf6bfe9fb51fdb6c23d6ca03d5bee47de66e892b16e70d57a2e15` | `IFCExtractor` (`ifc`) | VERIFIED | `test_ifc_golden_simple_building.py` | Minimal IFC2x3: project+site+bldg+storey+2 walls+props |
| — | — | — | — | — | `test_ifc_golden_dependency_honesty.py` | Fake model share + dependency honesty probe |

### Shared Module

| File | Purpose |
|---|---|
| `fake_models.py` | Reusable `FakeEntity`, `FakeConnection`, `FakeModel`, `make_fake_ifcopenshell()` for unit tests |

### Expected Output Contracts

#### `ifc_simple_building.ifc`
- When `ifcopenshell` available: `success=True`, records emitted for project/spatial/elements/connections
- When `ifcopenshell` absent: `success=False`, empty records, diagnostic names dep, no regex/fallback
- All records carry `provenance.entity` identifying the IFC entity type
- No regex-derived or mock data in any output path

---

---

## Office Domain (`fixtures/office/golden_v1/`)

| Fixture | Size | SHA-256 | Extractor | Maturity | Regression Test | Notes |
|---|---|---|---|---|---|---|
| `minimal.docx` | 36,946 B | `322aaeae...53da58` | `WordExtractor` (`word`) | VERIFIED | `test_word_golden_minimal.py` | 1 heading + 3 paragraphs + 1 table; flattened pdf_page output |
| `minimal.pptx` | 29,307 B | `831e55f7...32a32a8` | `PPTXExtractor` (`pptx`) | VERIFIED | `test_pptx_golden_minimal.py` | 2 slides (title+body); one pdf_page per slide |

### Expected Output Contracts

#### `minimal.docx`
- `result.success` == `True`
- Record count == 1 (single `pdf_page` record — all text flattened)
- All records are `type="pdf_page"` only — no `word_*` typed claims
- Known text strings preserved: "Generator Room Ventilation", "HVAC", "section 23 00 00"
- Provenance carries `source="word_extractor"` and `page` number
- No fabricated semantic facts (scope_item, requirement, etc.)

#### `minimal.pptx`
- `result.success` == `True`
- Record count == 2 (one `pdf_page` per slide)
- All records are `type="pdf_page"` only — no `pptx_*` typed claims
- Known text strings preserved on both slides
- Page numbers sequential [1, 2]
- No fabricated semantic facts

---

---

## Excel Domain (`fixtures/excel/golden_v1/`)

| Fixture | Size | SHA-256 | Extractor | Maturity | Regression Test | Notes |
|---|---|---|---|---|---|---|
| `submittal_register.xlsx` | 5,274 B | `fef9169c...c0a17b` | `ExcelRegisterExtractor` (`excel_register`) | EXPERIMENTAL | `test_excel_golden_submittal_register.py` | 8-col AECO register, 5 data rows, keyword header detection |

### Expected Output Contracts

#### `submittal_register.xlsx`
- `result.success` == `True`
- All records are `type="register_row"` — no typed persistence claims beyond register domain
- Record count == 5 (one per data row)
- Known entries present: SR-001 through SR-005 with correct Document Title, Status, Discipline, Area
- Every record carries `provenance.sheet` and `provenance.row`
- Header detection identifies row 0 via keyword scoring ("No", "Document Title", "Status", etc.)
- No fabricated semantic facts (no `document.*` or `schedule.*` records)

---

## Future Domains (Planned)

| Domain | Status | Planned Fixtures | Target Phase |
|---|---|---|---|
| **P6/XER** | ✅ Complete | `p6_standard.xer`, `p6_malformed_float.xer` | Phase 2 — pilot complete |
| **IFC** | ✅ Complete | `ifc_simple_building.ifc` | Phase 3 — pilot complete |
| **Excel** | ✅ Complete | `submittal_register.xlsx` | Phase 5 — pilot complete |
| **Word** | ✅ Complete | `minimal.docx` | Phase 4 — pilot complete |
| **PPTX** | ✅ Complete | `minimal.pptx` | Phase 4 — pilot complete |
| **DGN** | Blocked | Requires ODA converter | Skipped |
| **Image** | Not started | Needs Tesseract available | Skipped |
| **DXF/DWG** | Not started | No V02 extractor exists | Not applicable |

---

## Migration History

| Version | Date | Changes | Reason |
|---|---|---|---|
| v1.0 | 2026-09-02 | Initial pilot: 2 PDF golden fixtures | Wave A evidence quality foundation |
| v1.1 | 2026-09-02 | P6/XER pilot: 2 golden fixtures + inline_templates module | Phase 2 expanded |
| v1.2 | 2026-09-02 | IFC pilot: 1 golden fixture + fake_models shared module | Phase 3 expanded |
| v1.3 | 2026-09-02 | Office pilot: 2 golden fixtures (Word + PPTX), flattened output verified | Phase 4 expanded |
| v1.4 | 2026-09-02 | Excel pilot: 1 golden fixture, keyword header detection verified | Phase 5 expanded |
