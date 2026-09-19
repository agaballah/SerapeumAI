# V0.3-WP-03 EVIDENCE ANCHORS INTEGRATION — CLOSEOUT REPORT

**Date**: 2026-09-19  
**Work Package**: WP-03 Evidence Anchors Integration (with WP-03A remediation)  
**Baseline**: v0.2.0 (`c7f299f`) / v0.3 baseline (`ac3937b`)  
**Status**: Complete — promotion ready  

---

## 1. DELIVERABLES SUMMARY

### 1.1 Production code changes (8 files modified)

| File | Lines changed | Description |
|------|---------------|-------------|
| `src/domain/facts/models.py` | +40 | Added `EvidenceAnchor` dataclass + `from_fact_input()` classmethod |
| `src/application/services/fact_review_presentation.py` | +71/-30 | Added `format_evidence_citation()`, `_anchor_from_location()`; wired `EvidenceAnchor` into production path |
| `src/engine/builders/document_builder.py` | +47/-20 | Added `source_file`, `source_type="pdf"`, `page_or_slide` to all `FactInput.location` dicts |
| `src/engine/builders/bim_builder.py` | +10/-10 | Added `source_type="ifc"`, `entity_handle`, `element_id` |
| `src/engine/builders/schedule_builder.py` | +16/-16 | Added `source_type="xer"`, `activity_id` |
| `src/engine/builders/register_builder.py` | +4/-4 | Added `source_type="xlsx"`, `sheet_or_section`, `row_or_paragraph` |
| `src/engine/builders/completion_builder.py` | +2/-2 | Added `source_type="field"` |
| `src/ui/widgets/fact_table.py` | +52/+8 | Added `_open_source_file()` method and "Open Source File" button |

**Total**: 190 insertions, 52 deletions (net +138 lines)

### 1.2 Test changes (1 file)

| File | Tests | Description |
|------|-------|-------------|
| `src/tests/test_evidence_anchors_integration.py` | 34 | New focused behavioral tests covering all WP-03 acceptance criteria |

### 1.3 Documentation changes (4 files)

| File | Purpose |
|------|---------|
| `docs/quality/V030_WP03_EVIDENCE_ANCHORS_IMPLEMENTATION_REPORT.md` | Initial implementation report (pre-audit) |
| `docs/quality/V030_WP03_ACCEPTANCE_AUDIT.md` | First acceptance audit (identified 2 FAILED criteria) |
| `docs/quality/V030_WP03A_REMEDIATION_REPORT.md` | Remediation report (WP-03A: fixed both FAILED criteria) |
| `docs/quality/V030_WP03A_FINAL_ACCEPTANCE_AUDIT.md` | Final acceptance audit (all criteria PROVEN/PARTIAL) |

> **Note**: The original implementation report stated "2 documentation files" in one section and listed 4. This closeout report corrects that inconsistency: there are 4 documentation files total.

---

## 2. COMMIT CANDIDATE SET VERIFICATION

### Files in commit candidate set (against HEAD `579fc7b`)

```
src/application/services/fact_review_presentation.py
src/domain/facts/models.py
src/engine/builders/bim_builder.py
src/engine/builders/completion_builder.py
src/engine/builders/document_builder.py
src/engine/builders/register_builder.py
src/engine/builders/schedule_builder.py
src/ui/widgets/fact_table.py
src/tests/test_evidence_anchors_integration.py (new)
docs/quality/V030_WP03_EVIDENCE_ANCHORS_IMPLEMENTATION_REPORT.md (untracked)
docs/quality/V030_WP03_ACCEPTANCE_AUDIT.md (untracked)
docs/quality/V030_WP03A_REMEDIATION_REPORT.md (untracked)
docs/quality/V030_WP03A_FINAL_ACCEPTANCE_AUDIT.md (untracked)
```

### Excluded from commit candidate set

| Category | Files | Reason |
|----------|-------|--------|
| Dependencies | `requirements.txt`, `pyproject.toml`, `*.lock` | Not modified by WP-03 |
| Packaging | `*.spec`, `setup.py`, `setup.cfg` | Not modified by WP-03 |
| Database migrations | `src/infra/persistence/migrations/*.sql` | No new migrations; `020_pdf_bbox.sql` confirmed absent |
| v0.2.0 tags/releases | git tags | Not modified |
| Unrelated untracked files | `.kilo/`, `GOLD_*.dxf`, `benchmark/`, `corpus/`, etc. | Not part of WP-03 |

**Verification method**: `git diff --stat HEAD` (filtered to configured patterns) returns only the 8 production files. `git diff HEAD --name-only` returns exactly the 8 production files. No dependency, packaging, migration, or release files appear in the changeset.

---

## 3. TEST RESULTS

### 3.1 WP-03 focused tests

```
34 passed in 0.63s
```

All 34 tests in `src/tests/test_evidence_anchors_integration.py` pass.

### 3.2 Protected capability tests

```
15 passed in 0.51s
```

| Test suite | Tests | Status |
|------------|-------|--------|
| `test_fact_review_presentation.py` | 4 | ✅ All pass |
| `test_fact_review_ui_release_source.py` | 2 | ✅ All pass |
| `test_truth_state_enforcement.py` | 8 | ✅ All pass |
| `test_document_builder_semantic_facts.py` | 1 | ✅ All pass |

### 3.3 Full regression suite

```
775 passed, 3 failed, 44 warnings in 6.48s
```

| State | Passed | Failed |
|-------|--------|--------|
| Pre-WP-03 baseline | 741 | 3 |
| Post-WP-03 | 773 | 3 |
| Post-WP-03A | 775 | 3 |

**WP-03/WP-03A introduced 0 regressions.**

### 3.4 Pre-existing failures (unrelated to WP-03)

| Test | Failure | Root cause |
|------|---------|------------|
| `test_graph_persistence_shape_guard.py::test_save_result_sanitizes_graph_values_before_persistence` | `AttributeError: type object 'EntityType' has no attribute 'ENTITY'` | Pre-existing gap in `EntityType` enum (`src/domain/models/relationship_types.py`) |
| `test_office_dgn_flattened_extraction_contract.py::test_extract_job_handles_current_office_dgn_flattened_record_types_without_silent_drop` | `AttributeError: 'PageRecord' object has no attribute 'to_dict'` | Pre-existing stub gap in `PageRecord` dataclass (`src/domain/models/page_record.py`) |
| `test_retrieval_workspace_isolation.py::test_extracted_and_ai_support_are_project_scoped` | `AttributeError: 'PageRecord' object has no attribute 'to_dict'` | Same as above |

These failures were present before WP-03 was implemented and are unrelated to the EvidenceAnchor integration.

---

## 4. EVIDENCEANCHOR PRODUCTION INTEGRATION VERIFICATION

### Production call chain (verified by source code inspection)

1. `src/ui/widgets/fact_table.py:372` — `load_facts()` calls `filter_fact_rows(self.all_rows, ...)`
2. `src/application/services/fact_review_presentation.py:286` — `filter_fact_rows()` calls `build_fact_review_view(row)` for each row
3. `src/application/services/fact_review_presentation.py:228` — `build_fact_review_view()` calls `format_evidence_citation(row.get("location_json"))`
4. `src/application/services/fact_review_presentation.py:249` — `format_evidence_citation()` calls `_anchor_from_location(location_json)`
5. `src/application/services/fact_review_presentation.py:237` — `_anchor_from_location()` calls `EvidenceAnchor.from_fact_input(FactInput(...))`

**EvidenceAnchor is imported** at `src/application/services/fact_review_presentation.py:9`:
```python
from src.domain.facts.models import EvidenceAnchor, FactInput
```

**Conclusion**: `EvidenceAnchor.from_fact_input()` is executed in the production UI rendering path whenever the fact review widget displays a fact.

---

## 5. PDF BBOX CLASSIFICATION

PDF bbox is classified as a **known limitation** (PARTIAL), not a defect:

- **Page numbers**: Are preserved end-to-end through the complete path (extraction → builder → persistence → presentation → UI)
- **Bbox**: Is NOT populated anywhere in the extraction → builder → presentation path
  - `pdf_processor.py` was not modified (pypdf does not provide per-word/per-character bbox without additional dependencies)
  - `Migration 020` (`020_pdf_bbox.sql`) does NOT exist in the repository
  - No builder sets `location["bbox"]`
  - `EvidenceAnchor.bbox` field exists and `format_evidence_citation()` handles it correctly when present, but nothing populates it

This is an intentional limitation retained per WP-03 constraints (no new dependencies, no extraction pipeline modifications).

---

## 6. DOCUMENTATION INCONSISTENCIES CORRECTED

### 6.1 Test count

| Document | Claim | Actual |
|----------|-------|--------|
| Implementation report (Section 3.2) | "32 new tests" | 34 tests (2 added during WP-03A remediation) |
| Acceptance audit (Section 5.1-5.5) | "2 pre-existing failures" | 3 pre-existing failures |

### 6.2 Test names

| Implementation report name | Actual test name |
|---------------------------|-----------------|
| `test_format_location_shows_page_when_present` | `testformat_evidence_citation_shows_page_when_present` |
| `test_format_location_shows_bbox_when_present` | `testformat_evidence_citation_shows_bbox_when_present` |
| `test_format_location_returns_not_recorded_when_empty` | `testformat_evidence_citation_returns_not_recorded_when_empty` |

Multiple test names in the implementation report's Section 3 are missing the `test_` prefix or have incorrect names. The actual test file uses `format_evidence_citation` in names, not `format_location`.

### 6.3 Documentation file count

| Claim | Correct value |
|-------|--------------|
| "2 documentation files" (in original closeout) | 4 documentation files |

The 4 documentation files are:
1. `V030_WP03_EVIDENCE_ANCHORS_IMPLEMENTATION_REPORT.md`
2. `V030_WP03_ACCEPTANCE_AUDIT.md`
3. `V030_WP03A_REMEDIATION_REPORT.md`
4. `V030_WP03A_FINAL_ACCEPTANCE_AUDIT.md`

---

## 7. CONTRACT COMPLIANCE

| Constraint | Status | Evidence |
|------------|--------|----------|
| No new dependencies | ✅ | No changes to `requirements.txt`, `pyproject.toml` |
| No fact lifecycle changes | ✅ | `FactInput`, `Fact`, `FactStatus` unchanged |
| No protected extractor redesign | ✅ | No changes to extraction logic |
| No migration changes | ✅ | No new migration files; `020_pdf_bbox.sql` confirmed absent |
| No v0.2.0 modification | ✅ | No tags/releases modified |
| No packaging changes | ✅ | No packaging files modified |
| Backward compatible FactInput.location | ✅ | All old keys preserved; new keys additive |
| Existing tests pass | ✅ | 15/15 protected capability tests pass |

---

## 8. FINAL VERDICT

### PROMOTION READY

**Rationale**:

1. **Commit candidate set is clean**: Only 8 production files + 1 test file + 4 documentation files. No dependency, packaging, migration, v0.2.0, or release changes.

2. **All WP-03 tests pass**: 34/34 in `test_evidence_anchors_integration.py`.

3. **All protected capability tests pass**: 15/15.

4. **No regressions**: 775 passed, 3 pre-existing failures unchanged (all from `PageRecord`/`EntityType` stub gaps, unrelated to WP-03).

5. **EvidenceAnchor is in the production path**: `build_fact_review_view()` → `format_evidence_citation()` → `_anchor_from_location()` → `EvidenceAnchor.from_fact_input()`.

6. **PDF bbox is documented as a known limitation**: Not a defect; the data model and formatter handle bbox correctly when populated by future extraction infrastructure.

7. **All documentation inconsistencies have been corrected** in this closeout report and the final acceptance audit.

**No commit. No tag. No push.**
