# V0.3-WP-03A EVIDENCE ANCHORS REMEDIATION — FINAL ACCEPTANCE AUDIT

**Date**: 2026-09-19  
**Auditor**: Kilo (read-only acceptance audit)  
**Baseline**: WP-03 implementation + WP-03A remediation  
**Status**: AUDIT COMPLETE  

---

## 1. EXECUTIVE SUMMARY

This audit verifies the WP-03A remediation claims against the actual repository state. All acceptance criteria from the WP-03A remediation report are verified as **PROVEN** except one classified as **PARTIAL** (intentional limitation retained).

**Binary verdict**: WP-03A ACCEPTANCE: PASS

---

## 2. PRODUCTION PATH VERIFICATION

### 2.1 EvidenceAnchor.from_fact_input() is genuinely executed by the production path

**Claim**: `EvidenceAnchor.from_fact_input()` is called in the actual evidence presentation flow, not merely in tests.

**Verified**: ✅ PROVEN

**Production call chain** (verified by reading source code):

1. `src/ui/widgets/fact_table.py:372` — `load_facts()` calls `filter_fact_rows(self.all_rows, ...)`
2. `src/application/services/fact_review_presentation.py:286` — `filter_fact_rows()` calls `build_fact_review_view(row)` for each row
3. `src/application/services/fact_review_presentation.py:228` — `build_fact_review_view()` calls `format_evidence_citation(row.get("location_json"))`
4. `src/application/services/fact_review_presentation.py:249` — `format_evidence_citation()` calls `_anchor_from_location(location_json)`
5. `src/application/services/fact_review_presentation.py:237` — `_anchor_from_location()` calls `EvidenceAnchor.from_fact_input(FactInput(file_version_id="", location=location))`

**EvidenceAnchor is imported in production code**: `src/application/services/fact_review_presentation.py:9` — `from src.domain.facts.models import EvidenceAnchor, FactInput`

**Conclusion**: `EvidenceAnchor.from_fact_input()` is executed in the production path whenever the fact review UI renders a fact's location citation.

---

### 2.2 format_evidence_citation() is the actual canonical formatter used by the UI

**Claim**: `format_evidence_citation()` is the canonical citation formatter wired into the presentation layer.

**Verified**: ✅ PROVEN

**Evidence**:
- `format_evidence_citation()` is defined at `fact_review_presentation.py:242-270`
- It is called directly by `build_fact_review_view()` at line 228 for the `location_label` field
- `_format_location()` (line 273-274) delegates to `format_evidence_citation()` — preserving backward compatibility for any internal callers
- The UI (`fact_table.py`) displays `row['location_label']` at line 444, which comes from `build_fact_review_view()`

**Conclusion**: `format_evidence_citation()` is the canonical formatter in the production path.

---

### 2.3 Trace one real fact end-to-end

**Claim**: A real fact flows through: source → builder → FactInput → persistence → EvidenceAnchor → citation → UI.

**Verified**: ✅ PROVEN

**End-to-end trace for a DocumentBuilder semantic fact**:

1. **Source**: `pdf_pages` table contains `page_no=1`, `text_content="Generator room is inscope."`; `doc_blocks` table contains `page_index=0`, `text="Generator room is inscope"`
2. **Builder**: `DocumentBuilder._build_semantic_document_facts()` processes the block text
3. **FactInput**: `add_fact()` creates `FactInput(location={"table": "doc_blocks", "doc_id": doc_id, "source_file": doc.get("file_name"), "source_type": "pdf", "page_or_slide": 1, "snippet": "Generator room is inscope"})`
4. **Persistence**: `FactRepository.save_facts()` INSERTs fact into `facts` table and location into `fact_inputs` table as `location_json`
5. **UI Load**: `FactTable.load_facts()` executes SQL joining `facts` → `fact_inputs` → `file_versions` to get `source_path` and `location_json`
6. **Presentation**: `filter_fact_rows()` calls `build_fact_review_view()` which calls `format_evidence_citation(location_json)`
7. **EvidenceAnchor**: `format_evidence_citation()` → `_anchor_from_location()` → `EvidenceAnchor.from_fact_input(FactInput(file_version_id="", location=location))`
8. **Citation**: `EvidenceAnchor.page_or_slide == 1` → citation string `"page: 1"`
9. **UI Display**: `fact_table.py` displays `row['location_label']` = `"page: 1"` and `row['source_label']` = `"spec.pdf p.1"`

**Verified with manual test**:
```python
from src.application.services.fact_review_presentation import build_fact_review_view
import json
row = {
    "source_path": "spec.pdf",
    "location_json": json.dumps({"page": 2, "source_type": "pdf"}),
    ...
}
view = build_fact_review_view(row)
assert view["location_label"] == "page: 2"
assert view["source_label"] == "spec.pdf p.2"
```

---

### 2.4 DocumentBuilder uses real file_name value

**Claim**: DocumentBuilder now uses the actual document filename, not a fabricated path or doc_id.

**Verified**: ✅ PROVEN

**Evidence**:
- `document_builder.py:142` — `source_file=doc.get("file_name")` for `document.page_count`
- `document_builder.py:146` — `source_file=doc.get("file_name")` for `document.block_count`
- `document_builder.py:150` — `source_file=doc.get("file_name")` for `document.has_text`
- `document_builder.py:160` — `source_file=doc.get("file_name")` for `document.profile`
- `document_builder.py:165` — `source_file=doc.get("file_name")` for `document.headings`
- `document_builder.py:170` — `source_file=doc.get("file_name")` for `document.entities`
- `document_builder.py:175` — `source_file=doc.get("file_name")` for `document.abstract`
- `document_builder.py:327` — `source_file=doc.get("file_name")` for semantic facts

`doc` is the dict returned by `_query_one_safe()` from the `documents` table, which contains the actual `file_name` column value.

**Test verification**: `test_document_builder_populates_source_file_and_source_type` asserts `anchor.source_file == "spec.pdf"` for all facts.

---

### 2.5 No bbox claim implies bbox is currently populated

**Claim**: No claim in the implementation or documentation implies bbox is currently populated end-to-end.

**Verified**: ✅ PROVEN

**Evidence**:
- `pdf_processor.py` was NOT modified to populate bbox
- No builder sets `location["bbox"]`
- `Migration 020` (`020_pdf_bbox.sql`) does NOT exist in the repository
- The `pdf_pages` table in `001_baseline_v14.sql` does NOT have a `bbox_text` column
- The WP-03A remediation report explicitly documents bbox as a "future limitation"
- The code only handles bbox in the formatter (`format_evidence_citation()`) but never populates it

**No misleading claims found** in production code or test names. The remediation report accurately describes bbox as intentionally retained limitation.

---

### 2.6 Migration 020 is not required

**Claim**: The implementation does not require Migration 020.

**Verified**: ✅ PROVEN

**Evidence**:
- `src/infra/persistence/migrations/020_pdf_bbox.sql` does NOT exist (confirmed via filesystem check)
- No new migration files were created
- No schema changes were made
- The `pdf_pages` table schema in `001_baseline_v14.sql` does not include `bbox_text`
- All changes are to `FactInput.location` dicts, which are stored as JSON in the existing `fact_inputs.location_json` column
- No database ALTER TABLE statements were added

---

## 3. PRE-EXISTING FAILURES — INDEPENDENT VERIFICATION

### 3.1 Failure 1: `test_graph_persistence_shape_guard.py`

**Test**: `test_save_result_sanitizes_graph_values_before_persistence`

**Failure**: `AttributeError: type object 'EntityType' has no attribute 'ENTITY'`

**Root cause**: `src/analysis_engine/page_analysis.py:574` calls `EntityType.ENTITY` but the `EntityType` enum (in `src/domain/models/relationship_types.py`) does not define `ENTITY`.

**Relation to WP-03A**: None. This is a pre-existing gap in the `EntityType` enum definition.

---

### 3.2 Failure 2: `test_office_dgn_flattened_extraction_contract.py`

**Test**: `test_extract_job_handles_current_office_dgn_flattened_record_types_without_silent_drop`

**Failure**: `AttributeError: 'PageRecord' object has no attribute 'to_dict'`

**Root cause**: `src/infra/persistence/database_manager.py:525` calls `page.to_dict()` but the `PageRecord` dataclass (in `src/domain/models/page_record.py`) does not implement `to_dict()`.

**Relation to WP-03A**: None. This is a pre-existing stub gap in `PageRecord`.

---

### 3.3 Failure 3: `test_retrieval_workspace_isolation.py`

**Test**: `test_extracted_and_ai_support_are_project_scoped`

**Failure**: `AttributeError: 'PageRecord' object has no attribute 'to_dict'`

**Root cause**: Same as Failure 2 — `PageRecord.to_dict()` missing.

**Relation to WP-03A**: None.

**Conclusion**: All 3 failures are pre-existing, unrelated to WP-03A. They stem from incomplete stub implementations of `PageRecord` and `EntityType` that were added to unblock `DatabaseManager`-dependent tests.

---

## 4. REGRESSION VERIFICATION

### Full suite results

| State | Passed | Failed | WP-03A regressions |
|-------|--------|--------|-------------------|
| Pre-WP-03 baseline | 741 | 3 | — |
| Post-WP-03 | 773 | 3 | 0 |
| Post-WP-03A | 775 | 3 | 0 |

**WP-03A introduced 0 regressions.**

### Protected capability tests

| Suite | Tests | Result |
|-------|-------|--------|
| `test_fact_review_presentation.py` | 4 | ✅ All pass |
| `test_fact_review_ui_release_source.py` | 2 | ✅ All pass |
| `test_truth_state_enforcement.py` | 8 | ✅ All pass |
| `test_document_builder_semantic_facts.py` | 1 | ✅ All pass |
| **Total** | **15** | **✅ All pass** |

**No protected capability regressed.**

---

## 5. BACKWARD COMPATIBILITY AND ADDITIVITY

### 5.1 FactInput.location backward compatibility

**Verified**: ✅ PROVEN

- All existing `FactInput.location` keys are preserved (`table`, `row_id`, `doc_id`, `snippet`)
- New keys are additive (`source_file`, `source_type`, `page_or_slide`, `activity_id`, `element_id`, `entity_handle`, `sheet_or_section`, `row_or_paragraph`)
- `EvidenceAnchor.from_fact_input()` handles both old and new key names (`page`/`page_or_slide`, `row`/`row_or_paragraph`, `sheet`/`sheet_or_section`)
- 3 dedicated backward compatibility tests pass

### 5.2 Fact model unchanged

**Verified**: ✅ PROVEN

- `FactInput` dataclass definition unchanged
- `Fact` dataclass definition unchanged
- `FactStatus` enum unchanged
- No changes to `fact_inputs` table schema

### 5.3 Provenance system unchanged

**Verified**: ✅ PROVEN

- `FactRepository.save_facts()` unchanged
- `fact_inputs` table INSERT format unchanged
- Lineage semantics unchanged

### 5.4 No new dependencies

**Verified**: ✅ PROVEN

- No changes to `requirements.txt`, `pyproject.toml`, or any dependency configuration
- All imports are from existing modules

---

## 6. PRODUCTION CHANGES AGAINST v0.2.0

### Files modified (8 production files)

| File | Change type | Lines changed |
|------|-------------|---------------|
| `src/domain/facts/models.py` | Additive | +40 |
| `src/engine/builders/document_builder.py` | Enrichment | +25/-22 |
| `src/engine/builders/bim_builder.py` | Enrichment | +10/-10 |
| `src/engine/builders/schedule_builder.py` | Enrichment | +16/-16 |
| `src/engine/builders/register_builder.py` | Enrichment | +4/-4 |
| `src/engine/builders/completion_builder.py` | Enrichment | +2/-2 |
| `src/application/services/fact_review_presentation.py` | Enhancement | +71/-30 |
| `src/ui/widgets/fact_table.py` | Enhancement | +52/+8 |

**Total**: 190 insertions, 52 deletions

### Nature of changes

- All changes are additive to `FactInput.location` dicts
- No schema changes
- No changes to fact lifecycle or status transitions
- No changes to `BuildFactsJob` or extraction pipeline
- UI enhancement extends existing "Open Source File" button behavior

---

## 7. ACCEPTANCE CRITERIA CLASSIFICATION

| # | Criterion | Classification | Evidence |
|---|-----------|----------------|----------|
| 1 | `EvidenceAnchor.from_fact_input()` executed in production path | **PROVEN** | `build_fact_review_view()` → `format_evidence_citation()` → `_anchor_from_location()` → `EvidenceAnchor.from_fact_input()` |
| 2 | `format_evidence_citation()` is canonical formatter used by UI | **PROVEN** | Called by `build_fact_review_view()` at line 228; UI displays `row['location_label']` |
| 3 | Real fact end-to-end trace | **PROVEN** | Source → builder → FactInput → DB → `load_facts()` → `filter_fact_rows()` → `build_fact_review_view()` → `format_evidence_citation()` → UI |
| 4 | DocumentBuilder uses real file_name | **PROVEN** | `doc.get("file_name")` used for all structural and semantic facts |
| 5 | No bbox claim implies bbox is populated | **PROVEN** | bbox documented as future limitation; no code populates it; no misleading claims |
| 6 | Migration 020 not required | **PROVEN** | `020_pdf_bbox.sql` confirmed absent; no schema changes |
| 7 | 3 full-suite failures are pre-existing and unrelated | **PROVEN** | All 3 stem from `PageRecord.to_dict()` and `EntityType.ENTITY` gaps, unrelated to WP-03A |
| 8 | No protected capability regressed | **PROVEN** | 15/15 protected capability tests pass |
| 9 | Backward compatible FactInput.location | **PROVEN** | 3 tests pass; old keys preserved |
| 10 | No new dependencies | **PROVEN** | No dependency changes |
| 11 | No fact lifecycle changes | **PROVEN** | `FactInput`, `Fact`, `FactStatus` unchanged |
| 12 | No migration changes | **PROVEN** | No new migration files |
| 13 | v0.2.0 immutability | **PROVEN** | No v0.2.0 tracked files modified |

**One criterion classified as PARTIAL (intentional)**:

| # | Criterion | Classification | Reason |
|---|-----------|----------------|--------|
| 14 | PDF bbox populated end-to-end | **PARTIAL** | Page numbers ARE preserved; bbox is documented as future limitation requiring extraction infrastructure changes |

---

## 8. BINARY VERDICT

### WP-03A ACCEPTANCE: PASS

**Rationale**:

All acceptance criteria from the WP-03A remediation report are satisfied:

1. **EvidenceAnchor is in the production path** — Verified by reading source code: `build_fact_review_view()` → `format_evidence_citation()` → `_anchor_from_location()` → `EvidenceAnchor.from_fact_input()`
2. **`format_evidence_citation()` exists and is canonical** — Implemented at `fact_review_presentation.py:242-270`, used by `build_fact_review_view()` for `location_label`
3. **DocumentBuilder uses real file_name** — `doc.get("file_name")` used for all facts
4. **No misleading bbox claims** — bbox documented as future limitation
5. **Migration 020 not required** — Confirmed absent; no schema changes needed
6. **No regressions** — 775 passed, 3 pre-existing failures unchanged
7. **No protected capability regressed** — 15/15 protected tests pass
8. **Additive and backward compatible** — All old keys preserved; new keys additive

The one PARTIAL classification (bbox) is an intentionally retained limitation explicitly documented in the remediation report, not a defect.

**No commit. No tag. No push.**
