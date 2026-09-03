# SerapeumAI PDF Gold Fixture Validation v1.0

**Date:** 2026-09-02  
**Task:** TASK-018 — PDF Gold Fixture Pilot Implementation  
**Scope:** PDF domain only, additive changes  
**Status:** PASSED — 786/786 tests passing, 0 failed  

---

## 1. Test Results

```
786 passed, 0 failed, 56 warnings in 10.10s
(770 baseline + 16 new PDF golden fixture tests)
```

All previous tests continue to pass. Zero regressions.

---

## 2. Fixtures Created

| File | Path | Size | SHA-256 |
|---|---|---|---|
| `pdf_vector_simple.pdf` | `src/tests/fixtures/pdf/golden_v1/` | 1,253 B | `bafcbf97...6f01f5` |
| `pdf_combined_multi.pdf` | `src/tests/fixtures/pdf/golden_v1/` | 2,521 B | `a8f5bc...bcc639` |

### Fixture Descriptions

**`pdf_vector_simple.pdf`** — 1-page pure vector PDF
- Generated with PyMuPDF: 3 text lines ("Generator room is inscope", "Area is 377 sqm Approx.", "Scope includes underground diesel tank")
- Expected output: 3 records (pdf_page, doc_classification, doc_blocks)
- Composition: `vector`, method: `pypdf_vector`

**`pdf_combined_multi.pdf`** — 4-page multi-page vector PDF
- Generated with PyMuPDF + pypdf merge: 4 pages, each with ~15+ words of text
- Expected output: ≥6 records (4 × pdf_page, 1 × doc_classification, 1 × doc_blocks)
- All pages: composition `vector`, method `pypdf_vector`

---

## 3. Tests Added (16 new)

### `test_pdf_golden_vector_simple.py` (8 tests)

| Test | What It Proves |
|---|---|
| `test_golden_fixture_hash_matches_manifest` | Fixture file is immutable (SHA-256 invariant) |
| `test_extractor_selection_vector_simple` | Extractor maturity is PRODUCTION, id/version correct |
| `test_extraction_succeeds_and_is_deterministic` | Byte-for-byte reproducible across two runs |
| `test_record_count_and_types` | Exactly 3 records: pdf_page, doc_classification, doc_blocks |
| `test_provenance_completeness` | Every record has non-empty provenance with method/source key |
| `test_page_record_has_expected_structure` | Page 1 = vector, pypdf_vector method, correct metadata |
| `test_metadata_consistency` | page_count == record count, composition sums agree |
| `test_existing_pdf_tests_still_pass` | Smoke test: known metadata keys present, success=True |

### `test_pdf_golden_combined_multi.py` (8 tests)

| Test | What It Proves |
|---|---|
| `test_golden_fixture_hash_matches_manifest` | Multi-page fixture immutability |
| `test_extractor_selection_combined_multi` | Extractor callable on real file |
| `test_extraction_succeeds_and_is_deterministic` | Determinism across 4-page file |
| `test_record_count_multi_page` | 4 pdf_page records + classification + blocks |
| `test_all_pages_routed_as_vector` | All pages = vector composition, pypdf_vector method |
| `test_provenance_completeness_all_records` | All 6+ records have valid provenance |
| `test_metadata_page_count_agrees` | page_count=4, all counts match, no empty/scanned/combined |
| `test_existing_behavior_preserved` | No unexpected metadata fields introduced |

---

## 4. Scenarios Proven

| Scenario | Status | Evidence |
|---|---|---|
| **Extractor selection** | ✅ PROVED | Both tests assert `maturity == "PRODUCTION"`, `id == "universal-pdf-extractor-v1"` |
| **Deterministic extraction** | ✅ PROVED | Two consecutive `extract()` calls on same file → identical records/diagnostics/metadata |
| **Provenance completeness** | ✅ PROVED | Every record has non-empty provenance dict with method or source key |
| **Record count fidelity** | ✅ PROVED | 1-page = 3 records; 4-page = 6+ records; all types present |
| **Composition routing** | ✅ PROVED | All pages correctly routed as `vector` / `pypdf_vector` |
| **Metadata consistency** | ✅ PROVED | `page_composition_counts` sum equals `pdf_page_count`; all keys present |
| **Fixture immutability** | ✅ PROVED | SHA-256 hash check on every test run |
| **Existing behavior preserved** | ✅ PROVED | All 770 baseline tests pass; no regressions |
| **No schema changes** | ✅ CONFIRMED | Zero migration files modified |
| **No dependency changes** | ✅ CONFIRMED | Only existing packages used (`pypdf`, `fitz`) |

---

## 5. Existing PDF Tests (All Still Passing)

| Test File | Tests | Status |
|---|---|---|
| `test_pdf_routing.py` | 3 | ✅ PASS |
| `test_pdf_metadata_completeness.py` | 4 | ✅ PASS |
| `test_pdf_routing_fixture_pack.py` | 4 | ✅ PASS |
| `test_build_facts_evidence_closure.py` | 4 | ✅ PASS |
| `test_document_builder_semantic_facts.py` | 1 | ✅ PASS |
| **Total existing PDF-related** | **16** | **✅ ALL PASS** |

The new golden fixture tests are fully additive — they coexist alongside the existing fake-object and monkeypatch-based PDF tests.

---

## 6. Lessons Before Expanding to P6

### 6.1 What Worked Well

1. **Path resolution**: `Path(__file__).resolve().parent / "fixtures"` is the correct pattern. Avoid `.parent.parent.parent` — it over-traverses.
2. **Real-file fixtures**: Using actual `.pdf` files on disk (not just synthetic generation in-memory) catches path-resolution bugs that monkeypatch tests miss.
3. **Hash immutability check**: The `test_golden_fixture_hash_matches_manifest` test is a lightweight corruption detector. It caught nothing here but will catch accidental fixture modifications.
4. **Determinism test**: Running the extractor twice and comparing results is a powerful regression guard. Any non-deterministic output (UUIDs, timestamps) would be caught immediately.
5. **Combined fixture**: A multi-page fixture revealed that `metadata.page_composition_counts` aggregation works correctly across pages — something single-page tests can't verify.

### 6.2 What Needs Adjustment for P6

1. **Inline XER templates need extraction**: P6 tests currently embed XER content as string literals (`XER_BASE.format(...)`). These should be moved to `src/tests/fixtures/p6/inline_templates.py` before creating golden `.xer` files, to avoid duplication.
2. **File encoding matters**: P6 XER files use `latin-1` encoding. The golden fixture must be written with the same encoding to match production behavior.
3. **ifcopenshell availability**: IFC golden fixtures will need a skip condition when the optional dependency is absent (similar to how `test_ifc_dependency_contract.py` already handles this). P6 has no optional deps — this is a lower risk.
4. **Database schema assumptions**: P6 tests seed `file_registry` and `file_versions` rows manually. The golden fixture test should follow the same pattern rather than going through `ExtractJob.run()` (which requires a full DB setup), to keep the test focused and fast.
5. **SHA-256 of text files**: XER files are small text files. Their hashes will be stable across runs, but the test should tolerate whitespace differences if any arise from editor normalization.

### 6.3 Recommended P6 Implementation Order

1. Extract `XER_BASE` and related templates from existing P6 tests into `fixtures/p6/inline_templates.py`
2. Generate `p6_standard.xer` with 5 activities and full predecessor logic
3. Write `test_p6_golden_standard.py` (hash + determinism + record count + provenance)
4. Write `test_p6_golden_malformed_float.py` (honest failure on bad float data)
5. Verify all 786+ tests still pass

### 6.4 Anti-Patterns to Avoid

- **Do NOT** move existing tests to use golden fixtures — keep them as-is (additive principle)
- **Do NOT** change the extractor code to make tests pass — the fixture tests validate current behavior
- **Do NOT** create fixtures larger than 5 MB — keep regeneration fast in CI
- **Do NOT** generate fixtures at test time if they can be static files — static files enable hash checks

---

## 7. Files Changed

### New Files (5)

| File | Lines | Purpose |
|---|---|---|
| `src/tests/fixtures/__init__.py` | 0 | Package marker |
| `src/tests/fixtures/pdf/__init__.py` | 0 | Package marker |
| `src/tests/fixtures/MANIFEST.md` | ~70 | Fixture registry with hashes |
| `src/tests/test_pdf_golden_vector_simple.py` | 119 | 8 golden fixture tests |
| `src/tests/test_pdf_golden_combined_multi.py` | 109 | 8 golden fixture tests |

### New Fixtures (2)

| File | Size | Type |
|---|---|---|
| `src/tests/fixtures/pdf/golden_v1/pdf_vector_simple.pdf` | 1,253 B | Real PDF (PyMuPDF-generated) |
| `src/tests/fixtures/pdf/golden_v1/pdf_combined_multi.pdf` | 2,521 B | Real PDF (4-page, PyMuPDF-generated) |

### Modified Files

**None.** Zero existing source or test files were modified.

### Schema Changes

**None.** Zero migration files touched.

---

## 8. Conclusion

The PDF gold fixture pilot is **complete and validated**:

- 2 golden fixtures created (real .pdf files on disk)
- 16 new regression tests added (all passing)
- 770 existing tests continue to pass (zero regressions)
- 0 production code changes
- 0 schema changes
- 0 dependency changes

The framework is proven for the PDF domain. The path forward to P6/XER is clear: extract inline templates, create golden `.xer` files, and add hash+determinism+provenance tests following the same pattern.

---

*Wave A pilot complete. Framework ready for Phase 2 (P6).*
