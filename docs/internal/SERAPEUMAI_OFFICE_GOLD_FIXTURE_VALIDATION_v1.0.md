# SerapeumAI Office Gold Fixture Validation v1.0

**Date:** 2026-09-02  
**Task:** TASK-021 — Office (Word/PPTX) Gold Fixture Pilot Implementation  
**Scope:** Word and PPTX domains only, additive changes  
**Status:** PASSED — 830 passed, 7 skipped, 0 failed  

---

## 1. Test Results

```
830 passed, 7 skipped, 56 warnings in 10.76s
(811 baseline + 19 new Office tests)
```

All previous tests continue to pass. Zero regressions.

---

## 2. Fixtures Created

| File | Path | Size | SHA-256 |
|---|---|---|---|
| `minimal.docx` | `src/tests/fixtures/office/golden_v1/` | 36,946 B | `322aaeae...53da58` |
| `minimal.pptx` | `src/tests/fixtures/office/golden_v1/` | 29,307 B | `831e55f7...32a32a8` |

### Fixture Descriptions

**`minimal.docx`** — Single-page Word document with structured content
- 1 heading: "Generator Room Ventilation Requirements"
- 3 body paragraphs including AECO-specific text ("Section 23 00 00", HVAC scope)
- 1 table: 3 columns (Item, Description, Status), 2 data rows
- Total extracted text: 333 characters across 1 page record

**`minimal.pptx`** — 2-slide presentation with title and content
- Slide 1: Title "Generator Room Ventilation" + body text about Section 23 00 00
- Slide 2: Title "Equipment Schedule" + body text with line items (Supply Air Unit, Exhaust Fan)
- Total extracted text: 188 characters across 2 page records (one per slide)

Both fixtures were generated programmatically using `python-docx` and `python-pptx` APIs — standard library construction, no manual XML editing.

---

## 3. Tests Added (19 new)

### `test_word_golden_minimal.py` (9 tests)

| Test | What It Proves |
|---|---|
| `test_golden_fixture_hash_matches_manifest` | Fixture immutability (SHA-256 invariant) |
| `test_extractor_selection_word` | Maturity=VERIFIED, id/version correct |
| `test_extraction_succeeds_and_is_deterministic` | Byte-for-byte reproducible across two runs |
| `test_emits_only_pdf_page_records` | ONLY `pdf_page` type — no `word_*` typed claims |
| `test_expected_text_is_preserved` | Known strings found in extracted content |
| `test_provenance_completeness_all_records` | Every record has source + page in provenance |
| `test_no_word_typed_records_or_fabricated_semantics` | No scope_item/requirement fabrication from Word |
| `test_page_count_and_metadata_consistent` | page_count == record count, char_count > 0 |
| `test_existing_behavior_preserved` | No mock/fake diagnostics |

### `test_pptx_golden_minimal.py` (10 tests)

| Test | What It Proves |
|---|---|
| `test_golden_fixture_hash_matches_manifest` | Fixture immutability |
| `test_extractor_selection_pptx` | Maturity=VERIFIED, capabilities correct |
| `test_extraction_succeeds_and_is_deterministic` | Deterministic across runs |
| `test_emits_only_pdf_page_records` | ONLY `pdf_page` — no `pptx_*` typed claims |
| `test_one_record_per_slide` | 2 slides → 2 page records, sequential page numbers |
| `test_expected_text_is_preserved` | Known strings on both slides |
| `test_provenance_completeness_all_records` | source + page provenance on all records |
| `test_no_pptx_typed_records_or_fabricated_semantics` | No semantic fact fabrication from PPTX |
| `test_page_count_and_metadata_consistent` | page_count matches record count |
| `test_existing_behavior_preserved` | No mock/fake in diagnostics |

---

## 4. Scenarios Proven

| Scenario | Status | Evidence |
|---|---|---|
| **Extractor maturity = VERIFIED** | ✅ PROVED | Both extractors assert `maturity == "VERIFIED"` |
| **Deterministic output** | ✅ PROVED | Two runs → identical records, diagnostics, metadata counts |
| **Only flattened pdf_page output** | ✅ PROVED | Record type set is exactly `{"pdf_page"}` for both domains |
| **No word_* typed records** | ✅ PROVED | Explicit assertion forbids any record starting with `word_` |
| **No pptx_* typed records** | ✅ PROVED | Explicit assertion forbids any record starting with `pptx_` |
| **No fabricated semantic facts** | ✅ PROVED | Asserts no `document.scope_item` or `document.requirement` from extraction |
| **Expected text preserved** | ✅ PROVED | Known AECO strings appear in extracted content |
| **Provenance completeness** | ✅ PROVED | All records have `provenance.source` and `provenance.page` |
| **Fixture hash stability** | ✅ PROVED | SHA-256 matches manifest for both fixtures |
| **Page-per-slide mapping (PPTX)** | ✅ PROVED | 2 slides → 2 records, page numbers [1, 2] |
| **Existing behavior preserved** | ✅ PROVED | All 811 baseline tests pass |

---

## 5. Existing Office Tests (All Still Passing)

| Test File | Tests | Status |
|---|---|---|
| `test_office_dgn_flattened_extraction_contract.py` | 6 | ✅ PASS |
| `test_dgn_integration.py` | 3 | ✅ PASS |
| **Total existing Office-related** | **9** | **✅ ALL PASS** |

---

## 6. Files Changed

### New Files (6)

| File | Lines | Purpose |
|---|---|---|
| `src/tests/fixtures/office/__init__.py` | 0 | Package marker |
| `src/tests/fixtures/office/golden_v1/minimal.docx` | 36,946 B | Golden Word fixture |
| `src/tests/fixtures/office/golden_v1/minimal.pptx` | 29,307 B | Golden PPTX fixture |
| `src/tests/test_word_golden_minimal.py` | ~120 | 9 golden fixture tests |
| `src/tests/test_pptx_golden_minimal.py` | ~130 | 10 golden fixture tests |

### Modified Files (1)

| File | Change |
|---|---|
| `src/tests/fixtures/MANIFEST.md` | Added Office domain section + migration history v1.3 |

### Modified Existing Tests

**None.** All existing tests remain untouched.

### Schema Changes

**None.** Zero migration files touched.

---

## 7. Limitations Discovered

### 7.1 Current Capability Confirmed

| Aspect | Finding |
|---|---|
| **Output format** | Word and PPTX both emit ONLY `pdf_page` records — confirmed flattened-only design |
| **No typed persistence** | Neither extractor creates `word_*` or `pptx_*` DB records — contract verified |
| **Text extraction quality** | Full paragraph text is captured; table content is flattened with `[Table]` marker |
| **PPTX slide granularity** | One `pdf_page` per slide — confirmed by 2-slide fixture producing 2 records |
| **Provenance** | `source="word_extractor"` / `source="pptx_extractor"` correctly set |

### 7.2 Quality Gaps Observed

| Gap | Severity | Impact |
|---|---|---|
| **Tables are flattened with `[Table]` marker** | 🟡 Medium | Table structure (cell boundaries, headers) is lost; only row-by-row text remains |
| **No slide layout preservation** | 🟢 Low | Slide titles and body text are concatenated; spatial relationship between elements is lost |
| **No image OCR for embedded images** | 🟡 Medium | Both processors attempt Tesseract OCR on images but silently skip if unavailable |
| **Single page record per document** | 🟢 Low | Word documents don't get multi-page segmentation like PDFs — entire content is one record |
| **No heading hierarchy preservation** | 🟢 Low | Heading levels (H1, H2, etc.) are not captured; only plain text is emitted |

### 7.3 Scope Limitation

This pilot validates that Word and PPTX extractors **do not fabricate evidence** — they produce honest flattened text output. It does NOT test:
- Complex documents with many tables, shapes, or embedded objects
- .doc legacy format support (explicitly unsupported)
- .ppt legacy format support (explicitly unsupported)
- Image OCR quality (requires Tesseract)

These are out of scope for the gold fixture pilot. The current fixtures exercise the happy path only.

---

## 8. Comparison Across All Piloted Domains

| Domain | Fixtures | Tests | Maturity | Output Type | Key Risk |
|---|---|---|---|---|---|
| **PDF** | 2 | 16 | PRODUCTION | Rich typed (pdf_page, doc_classification, doc_blocks) | Regex-based semantic extraction |
| **P6/XER** | 2 | 16 | PRODUCTION | Rich typed (p6_project, p6_activity, p6_relation) | Float normalization (hours÷8=days) |
| **IFC** | 1 | 16 | VERIFIED | Rich typed (ifc_project, ifc_element_metadata, ifc_connection) | Optional dependency (ifcopenshell) |
| **Word** | 1 | 9 | VERIFIED | Flattened only (pdf_page) | Text structure loss (tables, headings) |
| **PPTX** | 1 | 10 | VERIFIED | Flattened only (pdf_page) | Slide layout loss, no spatial context |

### Cross-Domain Observations

1. **Rich vs. flattened**: PDF, P6, and IFC produce domain-typed records that feed into structured builders. Word and PPTX produce only flattened `pdf_page` records — they bypass builder-specific logic entirely.

2. **Maturity alignment**: All piloted domains are at least VERIFIED. No EXPERIMENTAL or PLACEHOLDER domains have been piloted yet.

3. **Test coverage ratio**: Rich-typed domains have more tests because they need to verify record-type fidelity. Flattened domains need fewer tests because the contract is simpler (only pdf_page records, no typed claims).

4. **Fabrication risk**: Word and PPTX extractors have the lowest fabrication risk — they only emit what's in the file as plain text. The risk profile is dominated by extraction quality (what gets lost), not fabrication (what gets invented).

---

## 9. Summary

| Metric | Value |
|---|---|
| New golden fixtures | 2 (minimal.docx, minimal.pptx) |
| New tests | 19 (9 Word + 10 PPTX) |
| Total test suite | 830 (+19 new passing) |
| Skipped | 7 (IFC dep-dependent) |
| Failures | 0 |
| Modified existing tests | 0 |
| Schema changes | 0 |
| Production code changes | 0 |

**Both Word and PPTX golden fixtures are fully operational and regression-safe.** The key finding is confirmation of the flattened-only contract: these extractors produce ONLY `pdf_page` records with no typed persistence claims, and no fabricated semantic facts.

The Excel Register phase (Phase 5) is the next candidate. It shares the same simplicity pattern as Word/PPTX — deterministic tabular extraction with header detection heuristics.

---

*Wave A pilot: PDF ✅, P6 ✅, IFC ✅, Word ✅, PPTX ✅. Framework proven across 5 domains.*
