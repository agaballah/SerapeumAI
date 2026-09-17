# Final Release Commit Manifest

**Verdict: RELEASE COMMIT MANIFEST — READY FOR MANAGEMENT APPROVAL**

## Summary

| Category | Files | Status |
|----------|-------|--------|
| A — REQUIRED RELEASE PRODUCT CODE | 27 files | ✅ Required for RC |
| B — REQUIRED RELEASE PACKAGING | 1 file | ✅ Required for RC |
| C — REQUIRED RELEASE TEST/VALIDATION | 6 files | ✅ Required for RC |
| D — RELEASE DOCUMENTATION | 9 files | ✅ Required for release |
| E — BENCHMARK/GOLD CORPUS | 0 files | ❌ Not for release commit |
| F — LOCAL DEVELOPMENT / EXPERIMENTAL | 22 paths | ❌ Leave uncommitted |
| G — UNRELATED / PRE-EXISTING | 1 file | ❌ Leave uncommitted |

**Total proposed for release commit: 43 files across A/B/C/D**

---

## Historical Baseline and Proposed Release State

| Field | Value |
|-------|-------|
| HISTORICAL BASELINE | `cf5cacc33bf100f7ea7bd59f22c456ac7605f256` |
| PROPOSED RELEASE DELTA | 43 files (see manifest below) |
| PROPOSED RELEASE SOURCE | `cf5cacc` + controlled release delta |
| UNCOMMITTED LOCAL MATERIAL | 22 paths in categories F + G |

---

## A — REQUIRED RELEASE PRODUCT CODE (27 files)

These changes are **required** because they were present in the validated Portable RC or are required to reproduce its behavior. All were confirmed via:
- PyInstaller xref (proves module was bundled)
- dist package inspection (proves migration/data file was included)
- Source code analysis (proves import dependency)

### A.1 Untracked Production Source Files (12 files) — **MUST COMMIT**

| Path | Required for RC? | Evidence |
|------|------------------|----------|
| `src/domain/intelligence/conflict_detector.py` | ✅ YES | Imported by `build_facts_job.py:84`; xref confirms inclusion; RC validation tested conflict resolution |
| `src/infra/dependency_status.py` | ✅ YES | Imported by `dashboard_page.py:20`; xref confirms inclusion; RC validation tested dependency health panel |
| `src/engine/extractors/csv_extractor.py` | ✅ YES | Imported by `extract_job.py:24`; xref confirms inclusion; WP-07B test `test_structured_formats_produce_extraction_runs` validates |
| `src/engine/extractors/excel_extractor.py` | ✅ YES | Imported by `extract_job.py:26`; xref confirms inclusion; WP-07B test validates |
| `src/engine/extractors/image_extractor.py` | ✅ YES | Imported by `extract_job.py:25`; xref confirms inclusion; WP-07B test `test_jpg_routed_to_image_extractor` validates |
| `src/engine/extractors/json_extractor.py` | ✅ YES | Imported by `extract_job.py:21`; xref confirms inclusion; WP-07B test validates |
| `src/engine/extractors/mpxj_wrapper.py` | ✅ YES | Imported by `extract_job.py:19`; xref confirms inclusion; enables MPP support |
| `src/engine/extractors/text_extractor.py` | ✅ YES | Imported by `extract_job.py:20`; xref confirms inclusion; WP-07B test validates |
| `src/engine/extractors/xml_extractor.py` | ✅ YES | Imported by `extract_job.py:22`; xref confirms inclusion; WP-07B test validates |
| `src/engine/extractors/yaml_extractor.py` | ✅ YES | Imported by `extract_job.py:23`; xref confirms inclusion; WP-07B test validates |
| `src/infra/persistence/migrations/020_pdf_bbox.sql` | ✅ YES | Bundled in dist package `_internal/src/infra/persistence/migrations/`; required for `pdf_pages.bbox` column used by P1 PDF block attribution |
| `src/infra/persistence/migrations/023_conflicts.sql` | ✅ YES | Bundled in dist package; required for `fact_conflicts` table used by conflict resolution UI |

### A.2 Modified Tracked Product Files (15 files) — **MUST COMMIT**

| Path | Required for RC? | Evidence |
|------|------------------|----------|
| `src/application/jobs/build_facts_job.py` | ✅ YES | Added conflict_detector import (line 84); RC validation requires conflict detection |
| `src/application/jobs/extract_job.py` | ✅ YES | Added 8 new extractor imports; expanded EXTRACTORS registry; WP-07B tests require new routing |
| `src/application/jobs/ingest_file_job.py` | ✅ YES | Updated extractor_map to route new formats; WP-07B tests require new routing |
| `src/application/orchestrators/agent_orchestrator.py` | ✅ YES | xref confirms inclusion; part of validated application |
| `src/application/services/document_service.py` | ✅ YES | Modified SUPPORTED_EXT; xref confirms inclusion |
| `src/application/services/fact_review_presentation.py` | ✅ YES | xref confirms inclusion; part of validated application |
| `src/document_processing/pdf_processor.py` | ✅ YES | Modified; xref confirms inclusion; P1 PDF block attribution |
| `src/document_processing/ppt_processor.py` | ✅ YES | Modified; xref confirms inclusion |
| `src/document_processing/word_processor.py` | ✅ YES | Modified; xref confirms inclusion |
| `src/domain/facts/models.py` | ✅ YES | Modified; xref confirms inclusion; fact status lifecycle |
| `src/engine/extractors/dxf_extractor.py` | ✅ YES | Added `source_file` to dxf_layer/dxf_block; orphan entity parsing; WP-07A validation |
| `src/engine/extractors/ifc_extractor.py` | ✅ YES | Added entity type counts; xref confirms inclusion |
| `src/infra/persistence/database_manager.py` | ✅ YES | Added conflict resolution methods (`resolve_conflict`, `mark_conflict_reviewed`, `get_project_conflicts`); xref confirms inclusion; WP-05A conflict resolution |
| `src/ui/pages/dashboard_page.py` | ✅ YES | Added dependency health panel; imports `dependency_status`; xref confirms inclusion |
| `src/ui/widgets/fact_table.py` | ✅ YES | Added conflict UI panel, source file opening; xref confirms inclusion; WP-05A conflict resolution |

---

## B — REQUIRED RELEASE PACKAGING (1 file)

| Path | Required for RC? | Evidence |
|------|------------------|----------|
| `SerapeumAI_Portable.spec` | ✅ YES | Modified at 9:17 AM (before 9:31 AM build); added hiddenimports for `fact_table`, `fact_lineage_popup`, `smart_import_wizard`, `vram_monitor`; build fails without these |

---

## C — REQUIRED RELEASE TEST/VALIDATION (6 files)

These tests permanently protect the released capability and should be committed with the release.

| Path | Required for RC? | Evidence |
|------|------------------|----------|
| `src/tests/test_gold_regression.py` | ✅ YES | WP-06/WP-07 Gold Regression benchmark; 28 tests protect core extraction capabilities |
| `src/tests/test_gold_regression_hardening.py` | ✅ YES | WP-07A hardening; 24 tests protect provenance quality, type preservation, entity-ID stability, admission gate |
| `src/tests/test_conflict_resolution_behavior.py` | ✅ YES | WP-05A conflict resolution; tests UI workflow (Mark Reviewed, Accept A/B) |
| `src/tests/test_pdf_block_page_attribution.py` | ✅ YES | P1 PDF block page_index accuracy; validates `_find_page_for_text` fix |
| `src/tests/test_iter5b_support_contract_repair.py` | ✅ YES | Modified at cf5cacc; updated to expect new extractor routing (XLS/XLSX/IMG/structured formats) |
| `src/tests/test_ifc_dependency_contract.py` | ✅ YES | Modified at cf5cacc; updated to expect success with ifcopenshell installed |

---

## D — RELEASE DOCUMENTATION (9 files)

These documents record the validation evidence and should accompany the release.

| Path | Required for RC? | Evidence |
|------|------------------|----------|
| `docs/quality/FINAL_RC_SOURCE_PROVENANCE_REPORT.md` | ✅ YES | This provenance audit; required for release traceability |
| `docs/quality/FINAL_CAPABILITY_CLOSURE_AUDIT.md` | ✅ YES | WP-08 audit: 932 tests passed, 35 capabilities PROVEN, 1 PARTIALLY PROVEN, 3 UNPROVEN |
| `docs/quality/PORTABLE_RELEASE_CANDIDATE_REPORT.md` | ✅ YES | RC validation results: clean-machine test, security scan, EXE hash |
| `docs/quality/RELEASE_VALIDATION_REPORT.md` | ✅ YES | Cross-worktree validation evidence |
| `docs/quality/WP00_BASELINE_FREEZE_REPORT.md` | ✅ YES | WP-00 baseline freeze |
| `docs/quality/WP07A_CHANGES_AND_VERIFICATION.md` | ✅ YES | WP-07A DXF source_file fix and remediation |
| `docs/quality/WP07B_BENCHMARK_CORRECTION_REPORT.md` | ✅ YES | WP-07B provenance benchmark correction |
| `docs/quality/WP07A_REMEDIATION_REPORT.md` | ✅ YES | WP-07A test remediation details |
| `docs/quality/WP08_POST_WP07B_GAP_AUDIT.md` | ✅ YES | WP-08 post-WP07B gap audit |

---

## E — BENCHMARK/GOLD CORPUS (0 files for release commit)

| Path | Classification | Notes |
|------|----------------|-------|
| `benchmark/` | ❌ RESEARCH TOOLING | Rust workspace (rvt-rs-bench, reviter-qualification); not required for Python runtime |
| `GOLD_0150.dxf` through `GOLD_0168.dxf` | ❌ TEST FIXTURES | Local benchmark corpus files; not needed in repo for runtime |
| `gold_0172.ifc` + related `*_diag.json` | ❌ DIAGNOSTIC OUTPUT | IFC diagnostic artifacts; local only |

**Recommendation:** These remain uncommitted. If benchmark infrastructure is needed, it should be in a separate `benchmark/` repo or CI artifact, not the product repo.

---

## F — LOCAL DEVELOPMENT / EXPERIMENTAL (22 paths)

| Path | Classification | Notes |
|------|----------------|-------|
| `.kilo/` | ❌ LOCAL DEV | Kilo agent workspace / worktrees |
| `experiments/` | ❌ LOCAL DEV | GPU environment, temp venvs |
| `f3_diagnostic_0171/` | ❌ LOCAL DEV | Diagnostic output directory |
| `gold_0172_analyze.txt`, `gold_0172_diag.json`, `gold_0172_elements.json`, `gold_0172_elements_all.json`, `gold_0172_ifc_output.txt`, `gold_0172_ifc_strict.txt`, `gold_0172_inspect.json` | ❌ LOCAL DEV | IFC diagnostic outputs |
| `slik_rvt_scripts_260902.zip`, `slik_rvt_scripts_extracted/` | ❌ LOCAL DEV | Revit scripts archive + extraction |
| `copy_portable.ps1` | ❌ LOCAL DEV | Build utility script |
| `test_excel.py`, `test_excel2.py`, `test_write.txt` | ❌ LOCAL DEV | Scratch test scripts |
| `tmp_tests/` | ❌ LOCAL DEV | Temporary test scratch |
| `corpus/` | ❌ LOCAL DEV | Local test corpus (gitignored via `_LOCAL_TEST_CORPUS/`) |
| `get_diff.py` | ❌ LOCAL DEV | Utility script |
| `probe_evidence_report.md`, `report_5c.md` | ❌ LOCAL DEV | Experiment notes |
| `tools/run_gold_benchmark.py` | ❌ LOCAL DEV | Benchmark tool (not a test; used for WP-07/WP-08 but not shipped) |

**Recommendation:** Leave all uncommitted. None required for runtime.

---

## G — UNRELATED / PRE-EXISTING (1 file)

| Path | Classification | Notes |
|------|----------------|-------|
| `.gitignore` | ❌ PRE-EXISTING | Minor change: added `_LOCAL_TEST_CORPUS/` |

**Recommendation:** Leave uncommitted. Not required for RC behavior.

---

## Proposed Release Delta Summary

| Category | Count | Description |
|----------|-------|-------------|
| A — REQUIRED RELEASE PRODUCT CODE | 27 | 12 untracked + 15 modified tracked |
| B — REQUIRED RELEASE PACKAGING | 1 | Spec file |
| C — REQUIRED RELEASE TEST/VALIDATION | 6 | Test files protecting released capabilities |
| D — RELEASE DOCUMENTATION | 9 | Quality/release audit reports |
| **TOTAL PROPOSED FOR COMMIT** | **43** | |

---

## Files to Leave Uncommitted (22 paths)

- `.kilo/`
- `experiments/`
- `f3_diagnostic_0171/`
- `gold_0172.*` (7 files)
- `slik_rvt_scripts_260902.zip`, `slik_rvt_scripts_extracted/`
- `copy_portable.ps1`
- `test_excel.py`, `test_excel2.py`, `test_write.txt`
- `tmp_tests/`
- `corpus/`
- `get_diff.py`
- `probe_evidence_report.md`, `report_5c.md`
- `tools/run_gold_benchmark.py`
- `benchmark/` (entire directory tree)
- `GOLD_0150.dxf` through `GOLD_0168.dxf` (5 files)

---

## Files Requiring Owner Review (0)

None — all A/B/C/D items have clear evidence from RC validation.

---

## Final Verification Checklist

- [x] All 12 untracked production modules are in PyInstaller xref
- [x] Both untracked migrations are in dist package
- [x] All 15 modified tracked files have mtime before build (9:31 AM)
- [x] Spec file modification (9:17 AM) precedes build
- [x] All 6 test files validate capabilities present in RC
- [x] 9 documentation files record validation evidence
- [x] No benchmark/corpus/dev files required for runtime
- [x] No .gitignore changes required for RC behavior

---

## Next Action (Requires Management Approval)

Upon approval:
1. `git add` the 43 files listed in categories A/B/C/D
2. `git commit` with message: `release: v0.2.0-rc1 — validated Portable RC source`
3. `git tag v0.2.0-rc1`
4. Rebuild from tag to confirm reproducibility
5. Proceed with release