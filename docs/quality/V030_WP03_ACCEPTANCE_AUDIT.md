# V0.3-WP-03 EVIDENCE ANCHORS INTEGRATION — ACCEPTANCE AUDIT

**Date**: 2026-09-19  
**Auditor**: Kilo (automated acceptance audit)  
**Baseline**: v0.2.0 (`c7f299f`) / v0.3 baseline (`ac3937b`)  
**Status**: AUDIT COMPLETE  

---

## 1. SCOPE OF AUDIT

This audit verifies the claims in:
- `docs/quality/V030_PRODUCT_WORK_PACKAGE_SELECTION.md`
- `docs/quality/V030_WP03_EVIDENCE_ANCHORS_IMPLEMENTATION_REPORT.md`

Against the actual repository state after WP-03 implementation.

---

## 2. FILES CHANGED — VERIFIED

| File | Change | Verified |
|------|--------|----------|
| `src/domain/facts/models.py` | Added `EvidenceAnchor` dataclass + `from_fact_input()` | ✅ Confirmed |
| `src/engine/builders/document_builder.py` | Added `source_file`, `source_type="pdf"`, `page_or_slide` to location dicts; `_iter_semantic_lines()` yields `(line, page_or_slide)` | ✅ Confirmed |
| `src/engine/builders/bim_builder.py` | Added `source_type="ifc"`, `entity_handle`, `element_id` | ✅ Confirmed |
| `src/engine/builders/schedule_builder.py` | Added `source_type="xer"`, `activity_id` | ✅ Confirmed |
| `src/engine/builders/register_builder.py` | Added `source_type="xlsx"`, `sheet_or_section`, `row_or_paragraph` | ✅ Confirmed |
| `src/engine/builders/completion_builder.py` | Added `source_type="field"` | ✅ Confirmed |
| `src/application/services/fact_review_presentation.py` | Extended `_source_label()` and `_format_location()` | ✅ Confirmed |
| `src/ui/widgets/fact_table.py` | Added `_open_source_file()` + "Open Source File" button | ✅ Confirmed |
| `src/tests/test_evidence_anchors_integration.py` | 32 new tests | ✅ Confirmed |

**Total modified production files**: 8  
**Total new test files**: 1  

---

## 3. ACCEPTANCE CRITERIA — DETAILED VERIFICATION

### 3.1 EvidenceAnchor dataclass exists and is functional

**Selection doc claim**: `EvidenceAnchor` dataclass exists at `src/domain/facts/models.py:48` with 16 typed fields and `from_fact_input()` classmethod.

**Verified**: ✅ PROVEN  
- `EvidenceAnchor` dataclass is present at `models.py:73-110` with 10 optional typed fields.
- `from_fact_input()` classmethod is present and functional.
- Manual verification: `EvidenceAnchor.from_fact_input(FactInput(file_version_id='x', location={'page': 2, 'bbox': [10,20,30,40]}))` correctly returns `page_or_slide=2`, `bbox=[10,20,30,40]`.

**Note**: The selection doc states "16 typed fields" but the actual class has 10 fields. This is a documentation inaccuracy in the selection doc, not a code defect.

---

### 3.2 EvidenceAnchor populated from real builder output

**Selection doc claim**: `from_fact_input()` called in builder code; `git grep "from_fact_input" -- src/engine/builders/` shows 4 builders.

**Verified**: ⚠️ PARTIAL  

**What is PROVEN**:
- All 5 builders now populate `FactInput.location` dicts with EvidenceAnchor-compatible fields (`source_type`, `page_or_slide`, `activity_id`, `element_id`, `entity_handle`, `sheet_or_section`, `row_or_paragraph`).
- The values come from real database records:
  - `DocumentBuilder`: `doc.get("file_name")` from `documents` table; `page.get("page_no")` from `pdf_pages` table; `block.get("page_index")` from `doc_blocks` table.
  - `BIMBuilder`: `p["global_id"]`, `s["element_id"]` from `ifc_projects`/`ifc_spatial_structure` tables.
  - `ScheduleBuilder`: `r_dict["activity_id"]` from `p6_activities` table.
  - `RegisterBuilder`: `r["sheet_name"]`, `r["row_index"]` from `register_rows` table.
  - `SystemCompletionBuilder`: `r["request_id"]` from `field_requests` table.

**What is NOT PROVEN**:
- `EvidenceAnchor.from_fact_input()` is **never called in the production code path**. The builders populate raw `location` dicts directly; `EvidenceAnchor` is only instantiated in tests.
- `git grep "EvidenceAnchor" -- src/engine/builders/` returns **zero matches**. The selection doc's acceptance criterion "EvidenceAnchor imported in all 4 processors" is NOT met.
- The implementation report acknowledges this ("not required; builders populate location dicts directly"), which is a reasonable interpretation, but the selection doc's literal acceptance criterion is not satisfied.

**Verdict**: The infrastructure is wired such that `EvidenceAnchor.from_fact_input()` CAN reconstruct anchors from real builder output, but the class itself is not used in the hot path.

---

### 3.3 Legacy FactInput.location backward compatibility

**Selection doc claim**: `FactInput.location` dicts remain valid; `EvidenceAnchor.from_fact_input()` reads from them.

**Verified**: ✅ PROVEN  
- 3 dedicated tests pass:
  - `test_legacy_location_dict_with_table_and_row_id`
  - `test_legacy_location_dict_with_page_and_bbox`
  - `test_fact_input_location_not_mutated`
- All builders preserve existing keys (`table`, `row_id`, `doc_id`, `snippet`) alongside new keys.
- No changes to `FactInput` dataclass definition.

---

### 3.4 PDF page/bbox preservation through complete path

**Selection doc claim**: "Populate `bbox_text` column during PDF extraction"; "PDF page/bbox information is preserved where available."

**Verified**: ⚠️ PARTIAL  

**What is PROVEN**:
- **Page numbers ARE preserved** for semantic document facts. `DocumentBuilder._iter_semantic_lines()` now yields `(line, page_or_slide)` tuples, where `page_or_slide` comes from:
  - `block.get("page_index") + 1` for `doc_blocks` (0-indexed to 1-indexed conversion)
  - `page.get("page_no")` for `pdf_pages`
- The page number is stored in `FactInput.location["page_or_slide"]`.
- The presentation layer (`_format_location()`) displays `page: N`.
- The UI (`_open_source_file()`) reads `page_or_slide` and includes it in the status label message.

**What is NOT PROVEN**:
- **`bbox` is NOT populated anywhere in the extraction → builder → presentation path**.
  - `pdf_processor.py` was NOT modified. It does not populate `bbox_text` or any per-element bbox.
  - No builder sets `location["bbox"]`.
  - `Migration 020` (`020_pdf_bbox.sql`) is referenced in the selection doc but does not exist in the repository. The `pdf_pages` table schema in `001_baseline_v14.sql` does NOT have a `bbox_text` column.
  - The `_format_location()` function handles `bbox` correctly when present, but nothing in the WP-03 implementation actually populates it.

**Verdict**: Page numbers are preserved. Bbox is NOT preserved. The claim that "PDF page/bbox information is preserved" is only partially true.

---

### 3.5 IFC/XER/XLSX anchors use real identifiers from extracted records

**Selection doc claim**: Builders should use real identifiers (`global_id`, `activity_id`, `row_index`, etc.) rather than fabricated values.

**Verified**: ✅ PROVEN  
- `BIMBuilder`: `entity_handle` and `element_id` are set to `p["global_id"]` (from `ifc_projects` table query) and `s["element_id"]` (from `ifc_spatial_structure` table query). These are real IFC GlobalIds.
- `ScheduleBuilder`: `activity_id` is set to `act_id` which is `r_dict["activity_id"]` from `p6_activities` table query. This is the real P6 activity ID.
- `RegisterBuilder`: `sheet_or_section` is set to `r["sheet_name"]` and `row_or_paragraph` is set to `r["row_index"]` from `register_rows` table query. These are real sheet names and 0-based row indices from the extracted register data.

---

### 3.6 SystemCompletionBuilder "field" source type semantics

**Selection doc claim**: Not explicitly stated in selection doc, but implementation report says `source_type="field"` is added.

**Verified**: ✅ PROVEN (with note)  
- `SystemCompletionBuilder` processes `field_requests` table, which contains field inspection requests and NCRs.
- `source_type="field"` is semantically appropriate for this data source.
- The builder has minimal location context (only `request_id`), which is honestly represented.
- No misleading provenance is created.

---

### 3.7 `_open_source_file()` uses legitimate source paths safely

**Selection doc claim**: "Open Source File" button should use EvidenceAnchor data for navigation.

**Verified**: ✅ PROVEN  
- `_open_source_file()` reads `source_path` from the selected fact row.
- `source_path` comes from the `fact_inputs` → `file_versions` join in `load_facts()` SQL query.
- Before opening, the method checks `os.path.exists(source_path)` and fails honestly if the file is missing.
- The method handles missing `source_path` with the message "Source path not recorded for this fact."
- Path is passed to `os.startfile()` / `subprocess.Popen()` as a string/list element, not via shell injection.
- No unsafe path handling (no `shell=True`, no user-controlled command execution).

---

### 3.8 PDF page navigation behavior

**Selection doc claim**: "File opens at the exact page/bbox/handle/entity_id where the fact was extracted."

**Verified**: ⚠️ PARTIAL  

**What is PROVEN**:
- The code reads `page_or_slide` from `location_json`.
- The status label displays `Opened source: <filename> (page N)` when a page number is present.
- The code attempts `subprocess.Popen(["cmd", "/c", "start", "", str(source_path)])` for Windows PDFs.

**What is NOT PROVEN / LIMITATION**:
- `cmd /c start "" file.pdf` does **NOT** navigate to a specific page. The Windows `start` command simply opens the file with the default associated application. It does not pass page parameters to PDF viewers.
- The implementation report honestly documents this limitation: "True page-level navigation depends on the PDF viewer's command-line support... The method logs the intended page number and attempts `cmd /c start` for Windows PDFs, but falls back to `os.startfile()` if the viewer-specific invocation fails."
- **No actual page navigation occurs.** The user still must manually navigate to the page. The "(page N)" message in the status label is informational only.

**Verdict**: The file is opened, and the intended page is displayed in the UI message, but the PDF viewer is NOT instructed to navigate to that page.

---

### 3.9 No existing fact/provenance/lifecycle behavior changed

**Selection doc claim**: "Do not redesign the fact model", "Do not replace the existing provenance system", "Do not change FactStatus/lifecycle semantics."

**Verified**: ✅ PROVEN  
- `FactInput` dataclass is unchanged (same fields, same defaults).
- `Fact` dataclass is unchanged.
- `FactStatus` enum is unchanged.
- `fact_inputs` table schema is unchanged.
- No modifications to `build_facts_job.py`.
- No modifications to conflict detection pipeline.
- All changes are additive to `FactInput.location` dicts.

---

### 3.10 No new database migrations

**Selection doc claim**: "Do not create a new database migration unless Migration 020 is demonstrably insufficient."

**Verified**: ✅ PROVEN  
- No new migration files created.
- No schema changes in existing migration files.
- The `pdf_pages` table in `001_baseline_v14.sql` does NOT have a `bbox_text` column (the selection doc references `020_pdf_bbox.sql` which does not exist in the repository).

**Note**: `Migration 020` (`020_pdf_bbox.sql`) is referenced in the selection doc as already committed, but it does not exist in the repository. This is a documentation inaccuracy.

---

### 3.11 No new dependencies

**Verified**: ✅ PROVEN  
- No changes to `requirements.txt`, `pyproject.toml`, or any dependency configuration.
- All imports are from existing modules.

---

### 3.12 Existing tests pass

**Selection doc claim**: `py -m pytest src/tests/test_build_facts_evidence_closure.py src/tests/test_conflict_resolution_behavior.py -v` — All pass.

**Verified**: ⚠️ PARTIAL  

**What is PROVEN**:
- `test_fact_review_presentation.py` (4 tests): ✅ All pass
- `test_fact_review_ui_release_source.py` (2 tests): ✅ All pass
- `test_truth_state_enforcement.py` (8 tests): ✅ All pass
- `test_evidence_anchors_integration.py` (32 tests): ✅ All pass
- `test_document_builder_semantic_facts.py` (1 test): ✅ Pass

**What is NOT PROVEN**:
- `test_build_facts_evidence_closure.py` cannot be run because it imports `FactQueryAPI` → `RuleRunner` → `DatabaseManager` → `src.domain.models.page_record.PageRecord`, which does not exist in the repository. This is a **pre-existing import error**, not caused by WP-03.
- `test_conflict_resolution_behavior.py` does not exist in the repository.
- The selection doc's verification commands reference files that do not exist in the current codebase.

---

### 3.13 v0.2.0 immutability

**Selection doc claim**: `git diff v0.2.0 --name-only` shows zero modifications to v0.2.0 tracked files.

**Verified**: ✅ PROVEN  
- No v0.2.0 tags or releases were modified.
- All changes are on top of the current `main` branch.
- The working directory has 8 modified files, all of which are new changes not present in v0.2.0.

---

## 4. FULL REGRESSION RESULTS

### Baseline (without WP-03 changes)

```
3 failed, 741 passed, 44 warnings
```

Pre-existing failures:
1. `test_graph_persistence_shape_guard.py::test_save_result_sanitizes_graph_values_before_persistence`
2. `test_office_dgn_flattened_extraction_contract.py::test_extract_job_handles_current_office_dgn_flattened_record_types_without_silent_drop`
3. `test_retrieval_workspace_isolation.py::test_extracted_and_ai_support_are_project_scoped`

### With WP-03 changes

```
3 failed, 773 passed, 44 warnings
```

**WP-03 introduced 0 regressions.** All 741 baseline passing tests continue to pass, plus 32 new WP-03 tests pass.

---

## 5. INACCURACIES IN IMPLEMENTATION REPORT

### 5.1 `format_evidence_citation()` does not exist

**Report claim**: "`format_evidence_citation()` in `fact_review_presentation.py` supports EvidenceAnchor-compatible location dicts."

**Fact**: `format_evidence_citation()` does NOT exist anywhere in the codebase (`git grep` returns zero matches). The report appears to have confused `_format_location()` with a non-existent `format_evidence_citation()`.

**Correction**: The report should state that `_format_location()` and `_source_label()` were extended to support EvidenceAnchor-compatible fields.

### 5.2 Pre-existing failure count

**Report claim**: "2 pre-existing failures unrelated to WP-03."

**Fact**: There are **3** pre-existing failures (see Section 4). The report undercounts by 1.

### 5.3 `EvidenceAnchor` usage in production code

**Report claim**: "6 dedicated tests + used in presentation layer" for `from_fact_input()`.

**Fact**: `EvidenceAnchor.from_fact_input()` is **only called in tests**. It is NOT used in the production code path (`fact_review_presentation.py` reads `location_json` directly as a dict; `fact_table.py` reads `location_json` directly). The report overstates production usage.

### 5.4 `source_file` for DocumentBuilder semantic facts

**Report claim**: "`source_file` (doc file_name)" for DocumentBuilder.

**Fact**: For structural facts, `source_file` is set to `doc.get("file_name")`. For semantic facts, `source_file` is set to `doc_id` (not `file_name`). See `document_builder.py` line ~326: `loc = {"table": "doc_blocks", "doc_id": doc_id, "source_file": doc_id, ...}`.

### 5.5 `Migration 020` existence

**Report claim**: "Migration 020 (`020_pdf_bbox.sql`) adds `bbox_text TEXT` column to `pdf_pages` table."

**Fact**: `020_pdf_bbox.sql` does NOT exist in the repository. The `pdf_pages` table in `001_baseline_v14.sql` does NOT have a `bbox_text` column. The report references a migration that is not present.

---

## 6. ADDITIONAL FINDINGS

### 6.1 `bbox` field is not populated end-to-end

The `EvidenceAnchor.bbox` field exists and `_format_location()` handles it correctly, but no code in the WP-03 implementation populates it. The `pdf_processor.py` was not modified. The `bbox_text` column does not exist. This means:

- The "bbox" part of the user workflow ("GOLD_0124.pdf p.2 bbox=(681,55-692,68)") is NOT implemented.
- Only page numbers are preserved for document facts.

### 6.2 `EvidenceAnchor` not used in production hot path

The `EvidenceAnchor` dataclass and `from_fact_input()` method are available for consumers, but neither `fact_review_presentation.py` nor `fact_table.py` imports or uses them. The builders populate raw dicts; the presentation layer reads raw dicts. `EvidenceAnchor` is an unused intermediate abstraction in the production path.

### 6.3 PDF page navigation does not actually navigate

The `_open_source_file()` method uses `cmd /c start "" file.pdf` on Windows. This opens the PDF with the default viewer but does NOT navigate to the specified page. The "(page N)" message shown to the user is informational only.

---

## 7. ACCEPTANCE CRITERIA — FINAL CLASSIFICATION

| # | Acceptance Criterion | Classification | Evidence |
|---|---------------------|----------------|----------|
| 1 | EvidenceAnchor dataclass exists and is functional | **PROVEN** | Present in `models.py:73-110`; 6 tests verify construction |
| 2 | `from_fact_input()` callable and working | **PROVEN** | 6 tests + manual verification pass |
| 3 | EvidenceAnchor populated from real builder output | **PARTIAL** | Builders populate compatible dicts from real DB records; `EvidenceAnchor` never called in production |
| 4 | Legacy `FactInput.location` backward compatible | **PROVEN** | 3 tests pass; all old keys preserved |
| 5 | PDF page/bbox preserved through complete path | **PARTIAL** | Page numbers preserved for semantic document facts; bbox NOT populated anywhere |
| 6 | IFC/XER/XLSX anchors use real identifiers | **PROVEN** | `global_id`, `activity_id`, `sheet_name`/`row_index` come from actual DB queries |
| 7 | SystemCompletionBuilder source_type semantically correct | **PROVEN** | `source_type="field"` accurately reflects `field_requests` origin |
| 8 | `_open_source_file()` uses legitimate source paths safely | **PROVEN** | Uses `file_versions.source_path`; `os.path.exists()` check; no shell injection |
| 9 | PDF page navigation opens requested page | **PARTIAL** | File opens; page number displayed in UI; actual page navigation NOT achieved |
| 10 | No fact/provenance/lifecycle behavior changed | **PROVEN** | Only additive changes to `location` dicts |
| 11 | No new database migrations | **PROVEN** | No new migration files |
| 12 | No new dependencies | **PROVEN** | No dependency changes |
| 13 | Existing tests pass | **PARTIAL** | Tests that CAN run all pass; some referenced tests don't exist or have pre-existing import errors |
| 14 | v0.2.0 immutability | **PROVEN** | No v0.2.0 tracked files modified |
| 15 | `EvidenceAnchor` imported in builders | **NOT PROVEN** | `git grep "EvidenceAnchor" -- src/engine/builders/` returns 0 matches |
| 16 | `format_evidence_citation()` exists and is used | **FAILED** | `format_evidence_citation()` does NOT exist in the codebase |

---

## 8. CORRECTIONS TO IMPLEMENTATION REPORT

1. **Section 2.1**: States "16 typed fields" — actual count is 10.
2. **Section 2.3**: References `format_evidence_citation()` — this function does not exist. Should reference `_format_location()` and `_source_label()`.
3. **Section 2.4**: Claims "page-aware PDF opening" — `cmd /c start` does not navigate to a specific page. Should clarify this is a known limitation.
4. **Section 3**: Claims "6 dedicated tests + used in presentation layer" for `from_fact_input()` — it is only used in tests, not in production.
5. **Section 5**: States "2 pre-existing failures" — actual count is 3.
6. **Section 8**: "EvidenceAnchor imported in all 5 builders" — `EvidenceAnchor` is not imported in any builder.
7. **Section 8**: "`from_fact_input()` called in builder code" — not called in any builder.
8. **Section 8**: "`bbox_text` populated during PDF extraction" — `bbox_text` column does not exist; not populated.
9. **Section 6, item 2**: Claims `source_file` uses `doc file_name` for DocumentBuilder — for semantic facts it uses `doc_id`, not `file_name`.

---

## 9. BINARY VERDICT

### FAIL / REMEDIATION REQUIRED

**Reason**: Two acceptance criteria are classified as **FAILED**:

1. **`format_evidence_citation()` does not exist** — The selection doc and implementation report both claim this function exists and is wired into the presentation flow. It does not exist anywhere in the codebase. This is a fundamental gap between the documented intent and the actual implementation.

2. **`EvidenceAnchor` not used in the production code path** — The selection doc's acceptance criterion "EvidenceAnchor imported in all 4 processors" is not met. `EvidenceAnchor` is defined but never imported or called in any production code path. The builders populate raw dicts; the presentation layer reads raw dicts. `EvidenceAnchor` is an unused abstraction in the hot path.

**Required remediation** (do not implement during audit):
- Either implement `format_evidence_citation()` as described in the selection doc, or update the selection doc and implementation report to accurately reflect that `_format_location()` serves this role.
- Either import and use `EvidenceAnchor.from_fact_input()` in the presentation layer (`fact_review_presentation.py`) and/or UI (`fact_table.py`), or update the acceptance criteria to reflect that builders populate compatible dicts directly without using the `EvidenceAnchor` class.
- Update the implementation report to correct all inaccuracies documented in Section 8.

---

*Audit completed: 2026-09-19*  
*No remediation changes were made during this audit.*
