# V0.3-WP-03 — CHERRY-PICK EXECUTION REPORT

**Date**: 2026-09-19  
**Cherry-pick commit**: `58beaacc99a019e5a6c0573441ef7de48c579e22` (short: `58beaac`)  
**Source commit**: `cdf2b60e0aa77a2bb02416fa9aead7570f8cd20b` (WP-03 on `main`)  
**Target branch**: `feature/cad-dxf-intelligence-v1` (at `ac3937b`)  
**Parent**: `ac3937b23503d528749a2496cbfd7b3f42737707`  
**Status**: COMPLETE — cherry-pick committed, bugs identified and fixed, all tests passing

---

## 1. OPERATION SUMMARY

| Item | Value |
|------|-------|
| **Command** | `git cherry-pick cdf2b60e0aa77a2bb02416fa9aead7570f8cd20b` |
| **Source branch** | `main` |
| **Target branch** | `feature/cad-dxf-intelligence-v1` |
| **Conflicts** | 3 files |
| **Resolution** | Manual merge of divergent `EvidenceAnchor`, citation formatter, and UI source-navigation code |
| **Resulting commit** | `58beaac` on `feature/cad-dxf-intelligence-v1` |

**Branch topology**:
```
main:                    579fc7b → cdf2b60
feature/cad-dxf-intelligence-v1: 579fc7b → 26dcf8a → ... → ac3937b → 58beaac
```
`cdf2b60` and `ac3937b` are sibling commits descending from common ancestor `579fc7b`. The cherry-pick replays WP-03's changes on top of the v0.3 baseline.

---

## 2. CONFLICT RESOLUTION DETAILS

### 2.1 `src/domain/facts/models.py`

**Conflict type**: Structural — both sides defined `EvidenceAnchor` with different field sets and methods.

**Resolution**: Adopted WP-03's 10-field `EvidenceAnchor` as the unified model. Removed v0.3-only fields (`x`, `y`, `z`, `excerpt`, `excerpt_length`) and methods (`to_location_dict()`, `format_citation()`).

**Rationale**: No production code or tests reference `to_location_dict()` or `format_citation()` — only documentation references exist (in `docs/quality/WP03_EVIDENCE_ANCHORS_REPORT.md`, which describes the API surface rather than calling it). The 10-field model is sufficient for all actual use cases (presentation layer uses the module-level `format_evidence_citation()` function, not the instance method).

**Unified `EvidenceAnchor` fields**:
- `source_file`, `source_type`, `page_or_slide`, `bbox`, `entity_handle`, `element_id`, `activity_id`, `sheet_or_section`, `row_or_paragraph`, `cell_address`

**Unified `from_fact_input()`**: Includes WP-03's alias handling (`page` → `page_or_slide`, `sheet` → `sheet_or_section`, `row` → `row_or_paragraph`, `cell` → `cell_address`) and non-dict guard.

### 2.2 `src/application/services/fact_review_presentation.py`

**Conflict type**: Functional — divergent `_source_label()` implementations and `format_evidence_citation()` signatures (2-arg vs 1-arg).

**Resolution**: Adopted WP-03's single-arg `format_evidence_citation(location_json)` as canonical. Rewrote `_source_label()` to use `EvidenceAnchor` internally via `_anchor_from_location()` while preserving v0.3's bbox formatting (`[x0,y0-x1,y1]` format).

**Key changes**:
- `format_evidence_citation(location_json)` — single-arg canonical formatter (WP-03)
- `_source_label(source_path, location_json)` — enhanced with EvidenceAnchor + bbox (unified v0.3/WP-03)
- `_anchor_from_location(location_json)` — converts location_json to EvidenceAnchor (WP-03)
- `_format_location(location_json)` — delegates to `format_evidence_citation()` (WP-03)
- `build_fact_review_view()` — calls `format_evidence_citation(row.get("location_json"))` (WP-03 pattern)
- Replaced ellipsis character (`…`) with ASCII (`...`) in `_shorten()` (line 86)

### 2.3 `src/ui/widgets/fact_table.py`

**Conflict type**: UI/Functional — both sides modified `_open_source_file()` and button layout; v0.3 added conflict UI.

**Resolution**: Preserved ALL v0.3 conflict UI methods and state. Unified `_open_source_file()` to support both DB-backed lookup (v0.3) and `row_by_fact_id` fallback (WP-03), with `os.path.isfile()` existence check and page-aware PDF opening.

**Key changes**:
- Added `import os`, `import platform`, `import subprocess`, `import json as _json` at module level
- `_build_content_area()` — parent changed from `self` to `self.frame_content` (see Bug #1 below)
- Button state: `btn_open_source` disabled when no source_path (WP-03 enhancement to v0.3)
- `_open_source_file()` — unified DB query + `row_by_fact_id` fallback, `os.path.isfile()` check, page-aware PDF opening via `subprocess.Popen`
- Error message: `"Resolution failed: {e}"` (was `"Conflict resolution failed: {e}"`)
- Removed redundant `import json as _json` inside method bodies

### 2.4 Builder files (non-conflict changes from WP-03)

The cherry-pick also applied non-conflicting changes to 5 builder files:

| File | Change |
|------|--------|
| `document_builder.py` | Added `source_file`, `source_type`, `snippet`, `page_or_slide` to location dicts; `_build_semantic_document_facts()` now receives `doc` param; `_iter_semantic_lines()` yields `(line, page_or_slide)` tuples |
| `bim_builder.py` | Added `source_type="ifc"`, `entity_handle`, `element_id` to IFC location dicts |
| `schedule_builder.py` | Added `source_type="xer"`, `activity_id` to P6/XER location dicts |
| `register_builder.py` | Added `source_type="xlsx"`, `sheet_or_section`, `row_or_paragraph` to Excel location dicts |
| `completion_builder.py` | Added `source_type="field"` to completion location dicts |

---

## 3. POST-CHERRY-PICK BUG FIXES

After the cherry-pick committed at `58beaac`, two bugs were identified and fixed in the working tree:

### 3.1 Bug #1: `_build_content_area()` parent reference (`fact_table.py:103`)

**Severity**: High — would cause `AttributeError` on FactTable instantiation

**Problem**: The cherry-pick conflict resolution changed the parent widget reference from `self` to `self.frame_content`:
```python
# BROKEN (before fix):
self.frame_content = ctk.CTkFrame(self.frame_content, fg_color=Theme.BG_DARKER)
```
Since `self.frame_content` has not yet been assigned at this point, this raises `AttributeError: 'FactTable' object has no attribute 'frame_content'`.

**Fix**: Restored the correct parent reference:
```python
# FIXED:
self.frame_content = ctk.CTkFrame(self, fg_color=Theme.BG_DARKER)
```

**Root cause**: During conflict resolution, the line was inadvertently modified. The v0.3 baseline (`ac3937b`) and all prior versions used `ctk.CTkFrame(self, ...)`.

### 3.2 Bug #2: `Link.to_dict()` second definition (`models.py:207-216`)

**Severity**: Medium — `Link.to_dict()` would raise `AttributeError` at runtime

**Problem**: The cherry-pick conflict resolution changed the second `Link.to_dict()` to reference `Fact`-specific fields that don't exist on `Link`:
```python
# BROKEN (before fix):
def to_dict(self):
    return {
        "link_id": self.link_id,
        "project_id": self.project_id,
        "fact_type": self.fact_type,       # AttributeError: Link has no 'fact_type'
        "subject_kind": self.subject_kind, # AttributeError: Link has no 'subject_kind'
        "subject_id": self.subject_id,     # AttributeError: Link has no 'subject_id'
        "value": self.value,               # AttributeError: Link has no 'value'
        "status": self.status.value,
        "confidence_tier": self.confidence_tier
    }
```

**Fix**: Restored the correct `Link`-specific fields:
```python
# FIXED:
def to_dict(self):
    return {
        "link_id": self.link_id,
        "project_id": self.project_id,
        "link_type": self.link_type,
        "from_kind": self.from_kind,
        "from_id": self.from_id,
        "to_kind": self.to_kind,
        "to_id": self.to_id,
        "status": self.status.value,
        "confidence_tier": self.confidence_tier
    }
```

**Root cause**: Line-number shift from the `EvidenceAnchor` class contraction caused git's 3-way merge to misalign the conflict context, inadvertently applying the first `Link.to_dict()` body (which had pre-existing Fact-field references) to the second `Link` class definition. The v0.3 baseline (`ac3937b`) had correct Link-specific fields in the second `to_dict()`.

**Note**: Both `LinkStatus` and `Link` classes are duplicated in this file (pre-existing in v0.2.0, v0.3 baseline, and WP-03). Python uses the last definition. The first definition's `to_dict()` with Fact fields is dead code (overridden). This duplication is a pre-existing code quality issue, not introduced by the cherry-pick.

---

## 4. TEST RESULTS

### 4.1 WP-03 evidence anchor tests
```
34 passed in 0.63s
```
All 34 tests in `test_evidence_anchors_integration.py` pass, covering:
- EvidenceAnchor construction from FactInput (6 tests)
- Backward compatibility with legacy location dicts (3 tests)
- Builder anchor wiring (4 tests)
- Presentation layer citations (12 tests)
- Honest missing anchor handling (3 tests)
- Source file navigation (4 tests)

### 4.2 Protected capability tests
```
4 passed in 2.32s
```
All 4 tests in `test_fact_review_presentation.py` pass, verifying backward compatibility for the presentation layer.

### 4.3 Conflict resolution behavior tests
```
10 passed in 2.32s
```
All 10 tests in `test_conflict_resolution_behavior.py` pass, verifying v0.3 conflict UI behavior is preserved.

### 4.4 Builder-specific tests
```
1 passed in 0.12s
```
`test_document_builder_semantic_facts.py` passes, verifying the document builder's page-aware evidence anchoring.

### 4.5 Combined test run
```
82 passed, 49 warnings in 3.37s
```
All 82 tests across the 7 relevant test files pass after bug fixes.

---

## 5. VERIFICATION CHECKLIST

| Check | Status |
|-------|--------|
| Cherry-pick commit `58beaac` created | PASS |
| No conflict markers remain | PASS |
| All 3 conflict files compile | PASS |
| `EvidenceAnchor.from_fact_input()` works with all alias types | PASS |
| `format_evidence_citation()` single-arg signature correct | PASS |
| `_source_label()` preserves bbox formatting | PASS |
| Conflict UI methods preserved in `fact_table.py` | PASS |
| `_open_source_file()` supports DB + row_by_fact_id fallback | PASS |
| `os.path.isfile()` check prevents silent failures | PASS |
| Page-aware PDF opening on Windows | PASS |
| Bug #1 fixed: `_build_content_area()` parent is `self` | PASS |
| Bug #2 fixed: `Link.to_dict()` references Link fields | PASS |
| All 82 related tests pass | PASS |
| v0.2.0 tags unchanged | PASS |
| No new tags created | PASS |
| No push performed | PASS |
| Untracked research material untouched | PASS |

---

## 6. WORKING TREE STATUS

The two bug fixes above are applied in the working tree but **not yet committed**:

```
src/domain/facts/models.py       | 9 ++++-----
src/ui/widgets/fact_table.py     | 2 +-
2 files changed, 3 insertions(+), 8 deletions(-)
```

**Recommended next step**: `git add` the two fixed files and create a follow-up commit `fix: correct post-cherry-pick regressions in fact_table and models` on `feature/cad-dxf-intelligence-v1`.

---

## 7. SUMMARY

The WP-03 commit (`cdf2b60`) was successfully cherry-picked onto the v0.3 baseline (`ac3937b`) at `58beaac`. Three files required manual conflict resolution. The unified implementation adopted WP-03's cleaner APIs (10-field `EvidenceAnchor`, single-arg `format_evidence_citation()`) while preserving all v0.3 conflict UI and DB-backed behaviors.

Two regressions were identified in the committed cherry-pick and fixed in the working tree:
1. `fact_table.py:103` — parent widget reference bug (AttributeError on UI init)
2. `models.py:207-216` — `Link.to_dict()` referenced nonexistent Fact fields (AttributeError at runtime)

All 82 related tests pass after fixes. No v0.2.0 tags were modified. No push was performed.

*Report generated: 2026-09-19*</br>
*Commit: 58beaacc99a019e5a6c0573441ef7de48c579e22*</br>
*Fixes applied to working tree, not yet committed.*