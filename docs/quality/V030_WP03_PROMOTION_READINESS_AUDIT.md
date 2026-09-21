# V0.3-WP-03 EVIDENCE ANCHORS INTEGRATION — PROMOTION READINESS AUDIT

**Date**: 2026-09-19  
**Auditor**: Kilo (read-only promotion audit)  
**Baseline**: v0.2.0 (`c7f299f`) / v0.3 baseline (`ac3937b`)  
**WP-03 changeset**: HEAD `579fc7b` working tree (uncommitted)  
**Status**: AUDIT COMPLETE  

---

## 1. EXECUTIVE SUMMARY

This audit performs the final pre-promotion verification of the WP-03 Evidence Anchors Integration changeset. It verifies:

1. The commit candidate set contains ONLY intended WP-03 files
2. No unrelated tracked files are included
3. 34 WP-03 tests + 15 protected-capability tests pass
4. 3 pre-existing full-suite failures are unchanged (not caused by WP-03)
5. EvidenceAnchor integration is genuinely present in the production path
6. PDF bbox is classified as a limitation (not a defect)
7. No dependency, migration, packaging, v0.2.0, or release changes occurred

**Binary verdict**: **PROMOTION READY**

---

## 2. COMMIT CANDIDATE SET VERIFICATION

### 2.1 Changeset against HEAD (the true WP-03 base)

Command: `git diff --name-only HEAD`

```
src/application/services/fact_review_presentation.py
src/domain/facts/models.py
src/engine/builders/bim_builder.py
src/engine/builders/completion_builder.py
src/engine/builders/document_builder.py
src/engine/builders/register_builder.py
src/engine/builders/schedule_builder.py
src/ui/widgets/fact_table.py
```

**Result**: Exactly 8 modified production files — all WP-03 deliverables.

### 2.2 Untracked files in working tree

Command: `git status --short`

```
 M src/application/services/fact_review_presentation.py
 M src/domain/facts/models.py
 M src/engine/builders/bim_builder.py
 M src/engine/builders/completion_builder.py
 M src/engine/builders/document_builder.py
 M src/engine/builders/register_builder.py
 M src/engine/builders/schedule_builder.py
 M src/ui/widgets/fact_table.py
?? src/tests/test_evidence_anchors_integration.py
?? docs/quality/V030_WP03_*.md (4 files)
?? docs/quality/V030_WP03_CLOSEOUT_REPORT.md
?? many other untracked files (NOT part of WP-03)
```

**Result**: The WP-03 commit candidates are:
- 8 modified production files (above)
- 1 new test file: `src/tests/test_evidence_anchors_integration.py`
- 4 existing WP-03 documentation files + 1 closeout report (in `docs/quality/`)

All other untracked files (`.kilo/`, `GOLD_*.dxf`, `benchmark/`, `corpus/`, `get_diff.py`, etc.) are **NOT** part of WP-03 and must NOT be committed.

### 2.3 Verification: no dependency/packaging/migration/config changes

Command: `git diff --stat HEAD -- "*.toml" "*.cfg" "*.txt" "*.lock" "*.json" "*.spec" "src/infra/persistence/migrations/"`

**Result**: No output — zero changes to dependency, packaging, migration, or configuration files.

**Confirmed**:
- `requirements.txt` — unchanged
- `pyproject.toml` — unchanged
- `SerapeumAI_Portable.spec` — unchanged
- `src/infra/persistence/migrations/020_pdf_bbox.sql` — does NOT exist
- No new migration files

### 2.4 Verification: no v0.2.0 / release changes

Command: `git tag` and `git log --oneline v0.2.0..HEAD --format="%h %s"`

**Result**: No tags modified. No release-related files changed. The v0.2.0 baseline (`c7f299f`) is untouched.

### 2.5 Commit diff stat (against HEAD)

```
8 files changed, 190 insertions(+), 52 deletions(-)
```

**Nature**: Net additive (+138 lines). All changes enrich `FactInput.location` dicts, add `EvidenceAnchor` dataclass, wire `format_evidence_citation()` into the presentation path, and add UI navigation.

---

## 3. TEST VERIFICATION

### 3.1 WP-03 focused tests

Command: `python -m pytest src/tests/test_evidence_anchors_integration.py -v`

```
34 passed in 0.63s
```

| Test class | Tests | Result |
|-----------|-------|--------|
| `TestEvidenceAnchorConstruction` | 6 | ✅ All pass |
| `TestBackwardCompatibility` | 3 | ✅ All pass |
| `TestDocumentBuilderAnchorWiring` | 2 | ✅ All pass |
| `TestBIMBuilderAnchorWiring` | 1 | ✅ Pass |
| `TestScheduleBuilderAnchorWiring` | 1 | ✅ Pass |
| `TestRegisterBuilderAnchorWiring` | 1 | ✅ Pass |
| `TestPresentationLayerCitations` | 12 | ✅ All pass |
| `TestHonestMissingAnchorHandling` | 3 | ✅ All pass |
| `TestSourceNavigation` | 4 | ✅ All pass |

### 3.2 Protected capability tests

Command: `python -m pytest src/tests/test_fact_review_presentation.py src/tests/test_fact_review_ui_release_source.py src/tests/test_truth_state_enforcement.py src/tests/test_document_builder_semantic_facts.py -v`

```
15 passed in 0.51s
```

| Test suite | Tests | Result |
|-----------|-------|--------|
| `test_fact_review_presentation.py` | 4 | ✅ All pass |
| `test_fact_review_ui_release_source.py` | 2 | ✅ All pass |
| `test_truth_state_enforcement.py` | 8 | ✅ All pass |
| `test_document_builder_semantic_facts.py` | 1 | ✅ All pass |

### 3.3 Full regression suite

Command: `python -m pytest src/tests/ -q`

```
775 passed, 3 failed, 44 warnings in 6.48s
```

### 3.4 Pre-existing failures (NOT caused by WP-03)

| # | Test | Error | Root cause | Related to WP-03? |
|---|------|-------|------------|---------------------|
| 1 | `test_graph_persistence_shape_guard.py::test_save_result_sanitizes_graph_values_before_persistence` | `AttributeError: 'EntityType' has no attribute 'ENTITY'` | `src/domain/models/relationship_types.py` missing `ENTITY` value | **No** — pre-existing stub gap |
| 2 | `test_office_dgn_flattened_extraction_contract.py::test_extract_job_handles_current_office_dgn_flattened_record_types_without_silent_drop` | `AttributeError: 'PageRecord' object has no attribute 'to_dict'` | `src/domain/models/page_record.py` missing `to_dict()` method | **No** — pre-existing stub gap |
| 3 | `test_retrieval_workspace_isolation.py::test_extracted_and_ai_support_are_project_scoped` | `AttributeError: 'PageRecord' object has no attribute 'to_dict'` | Same as #2 | **No** — pre-existing stub gap |

**All 3 failures stem from `PageRecord.to_dict()` and `EntityType.ENTITY` gaps in stub modules** (`src/domain/models/page_record.py`, `src/domain/models/relationship_types.py`) that were added as gitignored stubs to unblock DatabaseManager-dependent tests. These are unrelated to WP-03.

**Regression proof**: 741 baseline passes → 775 post-WP-03 passes (34 WP-03 + 0 regressions). The same 3 failures exist before and after.

---

## 4. EVIDENCEANCHOR PRODUCTION INTEGRATION VERIFICATION

### 4.1 EvidenceAnchor is genuinely executed in the production path

**Production call chain** (verified by source code inspection):

1. `fact_table.py:372` → `filter_fact_rows(self.all_rows, ...)`
2. `fact_review_presentation.py:286` → `filter_fact_rows()` calls `build_fact_review_view(row)` per row
3. `fact_review_presentation.py:228` → `build_fact_review_view()` calls `format_evidence_citation(row.get("location_json"))`
4. `fact_review_presentation.py:249` → `format_evidence_citation()` calls `_anchor_from_location(location_json)`
5. `fact_review_presentation.py:237` → `_anchor_from_location()` calls `EvidenceAnchor.from_fact_input(FactInput(file_version_id="", location=location))`

**Import verified**: `fact_review_presentation.py:9`
```python
from src.domain.facts.models import EvidenceAnchor, FactInput
```

**Conclusion**: `EvidenceAnchor.from_fact_input()` is executed in the production UI rendering path whenever the fact review widget displays a fact. This is NOT test-only usage.

### 4.2 EvidenceAnchor is defined with all required fields

Verified at `models.py:73-110`:
```python
@dataclass
class EvidenceAnchor:
    source_file: Optional[str] = None
    source_type: Optional[str] = None
    page_or_slide: Optional[int] = None
    bbox: Optional[List[float]] = None
    entity_handle: Optional[str] = None
    element_id: Optional[str] = None
    activity_id: Optional[str] = None
    sheet_or_section: Optional[str] = None
    row_or_paragraph: Optional[int] = None
    cell_address: Optional[str] = None
```

### 4.3 Builders populate EvidenceAnchor-compatible fields from real DB records

| Builder | source_type | Fields populated from real DB column |
|---------|-------------|--------------------------------------|
| `DocumentBuilder` | `"pdf"` | `source_file` ← `doc["file_name"]`; `page_or_slide` ← `block["page_index"]` or `page["page_no"]` |
| `BIMBuilder` | `"ifc"` | `entity_handle` ← `p["global_id"]`; `element_id` ← `s["element_id"]` |
| `ScheduleBuilder` | `"xer"` | `activity_id` ← `r_dict["activity_id"]` |
| `RegisterBuilder` | `"xlsx"` | `sheet_or_section` ← `r["sheet_name"]`; `row_or_paragraph` ← `r["row_index"]` |
| `SystemCompletionBuilder` | `"field"` | `source_type` only (minimal location context available) |

All values come from actual database rows queried at runtime, not fabricated values.

### 4.4 format_evidence_citation() is the canonical formatter

Verified at `fact_review_presentation.py:242-270`:
- `format_evidence_citation(location_json)` is the public canonical formatter
- Converts persisted `location_json` → `EvidenceAnchor` → human-readable citation string
- Called by `build_fact_review_view()` at line 228 for the `location_label` field
- `_format_location()` (line 273) delegates to `format_evidence_citation()` for backward compatibility
- UI displays `row['location_label']` at `fact_table.py:444`

---

## 5. PDF BBOX CLASSIFICATION

### 5.1 Page numbers: PRESERVED (PROVEN)

- `DocumentBuilder._iter_semantic_lines()` yields `(line, page_or_slide)` tuples where `page_or_slide` comes from `block["page_index"] + 1` or `page["page_no"]`
- Location dicts include `page_or_slide` for semantic facts
- `format_evidence_citation()` formats `page_or_slide` as `"page: N"`
- UI displays page number in citation and status message
- Test: `test_document_builder_semantic_fact_has_page_or_slide` verifies `anchor.page_or_slide == 1`

### 5.2 Bbox: KNOWN LIMITATION (PARTIAL)

- `EvidenceAnchor.bbox` field exists in the dataclass
- `format_evidence_citation()` handles bbox formatting correctly when present: `"bbox: (x1,y1-x2,y2)"`
- **No code in the extraction → builder → presentation path populates bbox**:
  - `pdf_processor.py` was NOT modified
  - `Migration 020` (`020_pdf_bbox.sql`) does NOT exist in the repository
  - `pdf_pages` table schema in `001_baseline_v14.sql` does NOT have a `bbox_text` column
  - No builder sets `location["bbox"]`
- **Classification**: Known limitation, not a defect. Bbox requires extraction infrastructure changes (pypdf with per-word bbox support or an OCR/layout analysis stage) that are outside WP-03's bounded scope.

### 5.3 No misleading claims

No documentation or test names in the WP-03 changeset claim bbox is currently populated. The remediation report (`V030_WP03A_REMEDIATION_REPORT.md`) explicitly documents bbox as a "future limitation."

---

## 6. CONSTRAINT COMPLIANCE

| Constraint | Status | Evidence |
|------------|--------|----------|
| No new dependencies | ✅ PASS | `git diff HEAD -- "pyproject.toml" "requirements*.txt" "Pipfile" "*.lock"` returns no output |
| No fact lifecycle changes | ✅ PASS | `FactInput` dataclass unchanged; `FactStatus` enum unchanged |
| No provenance system replacement | ✅ PASS | `fact_inputs` table schema unchanged; `FactRepository.save_facts()` unchanged |
| No protected extractor redesign | ✅ PASS | No extraction logic modified |
| No new database migration | ✅ PASS | No migration files in changeset; `020_pdf_bbox.sql` does not exist |
| No v0.2.0 modification | ✅ PASS | `git diff v0.2.0 --name-only` shows no v0.2.0 tracked files modified |
| No packaging changes | ✅ PASS | No `*.spec`, `setup.py`, `setup.cfg` in changeset |
| No release/tag changes | ✅ PASS | No tags or releases modified |
| Backward compatible FactInput.location | ✅ PASS | All existing keys preserved; new keys additive; 3 backward compat tests pass |

---

## 7. DOCUMENTATION CONSISTENCY

### 7.1 Documentation file count

The original implementation report contained an inconsistency stating "2 documentation files" while listing 4. This is corrected:

There are **4 WP-03 documentation files** in `docs/quality/`:
1. `V030_WP03_EVIDENCE_ANCHORS_IMPLEMENTATION_REPORT.md` — implementation report
2. `V030_WP03_ACCEPTANCE_AUDIT.md` — first acceptance audit (identified FAILED criteria)
3. `V030_WP03A_REMEDIATION_REPORT.md` — remediation report
4. `V030_WP03A_FINAL_ACCEPTANCE_AUDIT.md` — final acceptance audit

Plus this closeout report:
5. `V030_WP03_CLOSEOUT_REPORT.md` (this file)

### 7.2 Test count

| Document | Claim | Actual |
|----------|-------|--------|
| Implementation report (Section 3) | 32 new tests | 34 tests (2 added during WP-03A) |
| Remediation report (Section 3) | 34 tests | 34 tests ✅ |
| Final acceptance audit (Section 2) | 34 tests | 34 tests ✅ |

### 7.3 Pre-existing failure count

| Document | Claim | Actual |
|----------|-------|--------|
| Implementation report (Section 3) | 2 failures | 3 failures |
| Remediation report (Section 4) | 3 failures | 3 failures ✅ |
| Final acceptance audit (Section 4) | 3 failures | 3 failures ✅ |

All inconsistencies have been corrected in the closeout report.

---

## 8. FINAL VERDICT

### PROMOTION READY

**Rationale**:

1. **Commit candidate set is clean and scoped**: Only 8 WP-03 production files + 1 new test file. No dependency, packaging, migration, v0.2.0, or release changes are in the changeset.

2. **All WP-03 tests pass**: 34/34 in `test_evidence_anchors_integration.py`.

3. **All protected capability tests pass**: 15/15.

4. **No regressions**: 775 passed (741 baseline + 34 WP-03), 3 pre-existing failures unchanged and unrelated to WP-03.

5. **EvidenceAnchor is in the production path**: Verified by source code inspection — `build_fact_review_view()` → `format_evidence_citation()` → `_anchor_from_location()` → `EvidenceAnchor.from_fact_input()`. Import confirmed at `fact_review_presentation.py:9`.

6. **PDF bbox correctly classified as a known limitation**: Page numbers are preserved end-to-end; bbox is documented as future infrastructure work, not a defect.

7. **All documentation inconsistencies have been corrected** in this audit and the closeout report.

**No commit. No tag. No push.**
