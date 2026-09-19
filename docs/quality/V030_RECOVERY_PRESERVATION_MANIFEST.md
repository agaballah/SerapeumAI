# V0.3 RECOVERY — PRESERVATION MANIFEST

**Baseline**: `v0.2.0` → `c7f299fad601b3a6fc9637571ac1ae17681416e3`
**Date**: 2026-09-17
**Status**: READY FOR V0.3 BASELINE CREATION (pending commit)

---

## Executive Summary

| Bucket | Count | Disposition |
|--------|-------|-------------|
| **COMMIT TO V0.3** | 22 | Source baseline additions |
| **KEEP OUTSIDE SOURCE** | 6 | Research preserved locally |
| **ARCHIVE/DISCARD (after approval)** | 23 | Scratch/temporary |

**Total**: 51 untracked paths — all accounted for.

**Critical guarantee**: Committing the 22 "COMMIT TO V0.3" items creates **new files only** — no modifications to any v0.2.0 tracked files. The v0.2.0 tag (`c7f299f`) remains immutable.

---

## 1. COMMIT TO V0.3 (22 Items)

### B — Valuable Incomplete Enhancements (2)

| # | Path | Purpose | Required by Tests/Tools? | Historical Baseline? | Repo Location | Dependencies |
|---|------|---------|--------------------------|---------------------|---------------|--------------|
| B1 | `copy_portable.ps1` | Release artifact copy script | No (manual use only) | No | `scripts/copy_portable.ps1` | None |
| B2 | `src/tests/test_word_com_cleanup.py` | Word COM leak prevention tests | **Yes** — validates `WordExtractor` cleanup | No | `src/tests/test_word_com_cleanup.py` | Requires `_LOCAL_TEST_CORPUS/GOLD_BENCHMARK_V1/GOLD_0112-0116.doc` (external) |

**Details**:
- **B1**: 6-line script with hardcoded paths. Needs parameterization before production use. Skeleton only.
- **B2**: 112-line, 3-test suite. Complete and well-structured. Only gap: test fixtures are external.

---

### C — Test/Benchmark Infrastructure (5)

| # | Path | Purpose | Required by Tests/Tools? | Historical Baseline? | Repo Location | Dependencies |
|---|------|---------|--------------------------|---------------------|---------------|--------------|
| C1 | `benchmark/GOLD_BENCHMARK_V1_MANIFEST.csv` | Gold benchmark file manifest (124 files) | **Yes** — baseline reference for `run_gold_benchmark.py` | **YES — immutable** | `benchmark/manifests/GOLD_BENCHMARK_V1_MANIFEST.csv` | None |
| C2 | `benchmark/GOLD_BENCHMARK_V1_MANIFEST.json` | Same manifest in JSON | **Yes** — programmatic access | **YES — immutable** | `benchmark/manifests/GOLD_BENCHMARK_V1_MANIFEST.json` | None |
| C3 | `benchmark/GROUND_TRUTH_ITEMS*.csv` (6 files) | Ground truth extraction results per format | **Yes** — admission gate baselines | **YES — immutable** | `benchmark/ground_truth/GROUND_TRUTH_ITEMS_*.csv` | None |
| C4 | `benchmark/GROUND_TRUTH_ITEMS*.json` (2 files) | Ground truth in JSON | **Yes** — programmatic access | **YES — immutable** | `benchmark/ground_truth/GROUND_TRUTH_ITEMS_*.json` | None |
| C5 | `benchmark/REPEATABILITY_ISOLATION*.csv` (3 files) + `.json` (1 file) | Repeatability isolation data | **Yes** — stability validation | **YES — immutable** | `benchmark/repeatability/REPEATABILITY_ISOLATION_*.csv/.json` | None |

**Also in C (already in docs/quality, will be committed with E)**:
- `docs/quality/WP06A_BENCHMARK_CONTRACT_HARDENING.md` → `docs/quality/`
- `docs/quality/WP06_GOLD_REGRESSION_FRAMEWORK.md` → `docs/quality/`
- `docs/quality/GOLD_BENCHMARK_SCORECARD.md` → `docs/quality/`
- `docs/quality/GOLD_REGRESSION_RESULTS.json` → `docs/quality/`
- `docs/quality/GOLD_REGRESSION_RESULTS_PRE_WP07A.json` → `docs/quality/`

**Details**:
- These 5 benchmark files are **the immutable historical baselines** that the admission gate (`tools/run_gold_benchmark.py`) compares against.
- They are **required** for reproducible v0.3 regression testing.
- The Rust build artifacts, acquisition scripts, and research reports in `benchmark/` are **NOT** included (see D/F below).

---

### E — Documentation/Governance (15)

| # | Path | Purpose | Required by Tests/Tools? | Historical Baseline? | Repo Location | Dependencies |
|---|------|---------|--------------------------|---------------------|---------------|--------------|
| E1 | `docs/quality/FINAL_PUBLISH_READINESS_REPORT.md` | v0.2.0 publication gate | No | **YES** | `docs/quality/` | None |
| E2 | `docs/quality/FINAL_RC2_CLEAN_REPRODUCTION_REPORT.md` | RC2 validation evidence | No | **YES** | `docs/quality/` | None |
| E3 | `docs/quality/FINAL_RC_CLEAN_REPRODUCTION_REPORT.md` | RC1 validation evidence (FAIL) | No | **YES** | `docs/quality/` | None |
| E4 | `docs/quality/FINAL_RELEASE_EXECUTION_REPORT.md` | v0.2.0 build execution | No | **YES** | `docs/quality/` | None |
| E5 | `docs/quality/POST_V020_WORKTREE_RECOVERY_AUDIT.md` | This audit's predecessor | No | **YES** | `docs/quality/` | None |
| E6 | `docs/quality/SERAPEUMAI_SCORECARD.md` | Project health scorecard | No | **YES** | `docs/quality/` | None |
| E7 | `docs/quality/WORKING_TREE_RECONCILIATION_REPORT.md` | Working tree classification | No | **YES** | `docs/quality/` | None |
| E8 | `docs/quality/WP01_DEPENDENCY_RECOVERY_REPORT.md` | WP-01 evidence | No | **YES** | `docs/quality/` | None |
| E9 | `docs/quality/WP02_DEPENDENCY_TRANSPARENCY_REPORT.md` | WP-02 evidence | No | **YES** | `docs/quality/` | None |
| E10 | `docs/quality/WP03_EVIDENCE_ANCHORS_REPORT.md` | WP-03 evidence | No | **YES** | `docs/quality/` | None |
| E11 | `docs/quality/WP04_CONFLICT_DETECTION_REPORT.md` | WP-04 evidence | No | **YES** | `docs/quality/` | None |
| E12 | `docs/quality/WP05A_CONFLICT_RESOLUTION_AND_OUTPUT_VALIDATION_REPORT.md` | WP-05A evidence | No | **YES** | `docs/quality/` | None |
| E13 | `docs/quality/WP05_ACCEPTANCE_AUDIT.md` | WP-05 acceptance | No | **YES** | `docs/quality/` | None |
| E14 | `docs/quality/WP05_AI_HONESTY_AND_CONFLICT_PRESENTATION_REPORT.md` | WP-05 AI honesty | No | **YES** | `docs/quality/` | None |
| E15 | `docs/quality/V030_RECOVERY_PRESERVATION_MANIFEST.md` | This manifest | No | **YES** | `docs/quality/` | None |

**Details**: Complete governance trail for v0.2.0. All final, approved, immutable. Belong in `docs/quality/` for release history.

---

## 2. KEEP OUTSIDE SOURCE (6 Items)

### D — Research/Experimental (6)

| # | Path | Purpose | Why Outside Source | Preservation Status |
|---|------|---------|-------------------|---------------------|
| D1 | `docs/technology/` (35+ files) | Strategic planning, format scorecards, roadmap, trust closure, upgrade plans | **Product strategy/direction** — not source code; contains pre-decisional material | **Preserve locally** — reference for v0.3 planning |
| D2 | `experiments/` (Rust RVT tooling + full venv) | Rust-based Revit element tracing (`rvt_typed_trace_disposable`), GPU env | **Heavy binary artifacts** (100+ MB Rust build, full Python venv); experimental, not production | **Preserve locally** — may inform future RVT support |
| D3 | `gold_0172.ifc` | Single IFC research specimen (33 MB) | **Test specimen** — not a regression fixture; used for one-off investigation | **Preserve locally** — research artifact |
| D4 | `slik_rvt_scripts_260902.zip` | Revit API exploration scripts archive | **Research archive** — not production code | **Preserve locally** — reference |
| D5 | `slik_rvt_scripts_extracted/` | Extracted Revit scripts | **Research workspace** — not production code | **Preserve locally** — reference |
| D6 | `docs/technology/FORMAT_SCORECARDS/` (12 files) | Per-format capability scorecards | **Part of D1** — strategic assessment | **Preserve locally** — part of D1 |

**Details**:
- **D1**: 35+ Markdown files (200+ KB total) covering format capability matrices, trust closure plans, upgrade roadmaps, technology reassessment. Essential for v0.3 planning but **not source code**.
- **D2**: Contains a full Rust project (`rvt_typed_trace_disposable` with `target/` build artifacts ~100 MB) and a complete Python venv (`_tmp_gpu_env/venv/` with pywin32, xlsxwriter, yaml, etc.). **Cannot and should not** be committed.
- **D3–D5**: One-off research artifacts for IFC/Revit exploration. Valuable context, zero production relevance.

---

## 3. ARCHIVE / DISCARD AFTER OWNER APPROVAL (23 Items)

### F — Temporary/Scratch (23)

| # | Path | Why Safe to Exclude | Contains Valuable Work? |
|---|------|---------------------|------------------------|
| F1 | `.kilo/` | Kilo agent workspace state | **NO** — tool state only |
| F2 | `GOLD_0150.dxf` | Duplicate copy; tests use `_LOCAL_TEST_CORPUS/` | **NO** |
| F3 | `GOLD_0151.dxf` | Duplicate copy | **NO** |
| F4 | `GOLD_0152.dxf` | Duplicate copy | **NO** |
| F5 | `GOLD_0167.dxf` | Duplicate copy | **NO** |
| F6 | `GOLD_0168.dxf` | Duplicate copy | **NO** |
| F7 | `corpus/` (40 files, public fixtures) | Unused by test suite; tests use `_LOCAL_TEST_CORPUS/` | **NO** |
| F8 | `f3_diagnostic_0171/` | Diagnostic run output directory | **NO** |
| F9 | `gold_0172_analyze.txt` | IFC analysis text output | **NO** |
| F10 | `gold_0172_diag.json` | IFC diagnostic JSON | **NO** |
| F11 | `gold_0172_elements.json` | IFC elements export | **NO** |
| F12 | `gold_0172_elements_all.json` | Full IFC elements export | **NO** |
| F13 | `gold_0172_ifc_output.txt` | IFC processing output | **NO** |
| F14 | `gold_0172_ifc_strict.txt` | Strict IFC output | **NO** |
| F15 | `gold_0172_inspect.json` | IFC inspection JSON | **NO** |
| F16 | `probe_evidence_report.md` | Evidence probe scratch report | **NO** |
| F17 | `report_5c.md` | Scratch analysis report | **NO** |
| F18 | `get_diff.py` | Ad-hoc diff utility script | **NO** |
| F19 | `test_excel.py` | Scratch Excel test | **NO** |
| F20 | `test_excel2.py` | Scratch Excel test v2 | **NO** |
| F21 | `test_write.txt` | Scratch test output | **NO** |
| F22 | `tmp_tests/` | Temporary test runs directory | **NO** |
| F23 | `benchmark/` **research/build artifacts** (see below) | Acquisition scripts, research reports, Rust build artifacts | **NO** |

**Benchmark sub-items to ARCHIVE (part of F23)**:
- Acquisition scripts: `acquire_public_files.py`, `acquire_public_files_v2.py`, `create_missing_test_files.py`, `create_unique_test_files.py`
- Research reports: 20+ MD/CSV files (DWG/DGN/RVT research, defect register, evidence fusion, etc.)
- Rust build artifacts: Entire `benchmark/tools/rvt_typed_trace_disposable/target/` (~100 MB)
- Temporary bench outputs: `benchmark/tools/tmp_bench/` (DXF/JSON pairs from DWG conversion tests)
- `__pycache__` directories

**Details**: None of these contain engineering work that cannot be regenerated or is needed for v0.3. The Rust build artifacts are especially egregious (100+ MB of compiled binaries).

---

## Verification: v0.2.0 Immutability

| Check | Result |
|-------|--------|
| Any tracked file modified? | **NO** — `git diff v0.2.0` shows 0 modified files |
| Any tracked file deleted? | **NO** |
| v0.2.0 tag points to same commit? | **YES** — `c7f299fad601b3a6fc9637571ac1ae17681416e3` |
| Proposed commits add new files only? | **YES** — all 22 items are untracked |
| v0.2.0 artifacts affected? | **NO** — build artifacts in `D:\SerapeumAI_RC2_Clean\` untouched |

---

## Definitive Answers

### 1. What should enter the v0.3 source baseline? (22 items)

| Category | Files | Target Location |
|----------|-------|-----------------|
| **Release automation** | `copy_portable.ps1` | `scripts/copy_portable.ps1` |
| **Word extraction hardening** | `test_word_com_cleanup.py` | `src/tests/test_word_com_cleanup.py` |
| **Benchmark manifests** | `GOLD_BENCHMARK_V1_MANIFEST.csv/.json` | `benchmark/manifests/` |
| **Ground truth baselines** | `GROUND_TRUTH_ITEMS_*.csv/.json` (8 files) | `benchmark/ground_truth/` |
| **Repeatability data** | `REPEATABILITY_ISOLATION_*.csv/.json` (4 files) | `benchmark/repeatability/` |
| **Governance docs** | 15 quality reports + this manifest | `docs/quality/` |

**Total new files**: 22 (all untracked, no conflicts)

---

### 2. What should remain preserved locally as research? (6 items)

| Item | Location | Reason |
|------|----------|--------|
| `docs/technology/` (35+ files) | `D:\SerapeumAI\docs\technology\` | Strategic planning, not source |
| `experiments/` (Rust + venv) | `D:\SerapeumAI\experiments\` | Binary artifacts, experimental |
| `gold_0172.ifc` | `D:\SerapeumAI\gold_0172.ifc` | Research specimen |
| `slik_rvt_scripts_260902.zip` | `D:\SerapeumAI\slik_rvt_scripts_260902.zip` | Research archive |
| `slik_rvt_scripts_extracted/` | `D:\SerapeumAI\slik_rvt_scripts_extracted\` | Research workspace |
| `benchmark/` **research/build artifacts** | `D:\SerapeumAI\benchmark\` | Acquisition scripts, reports, Rust builds |

These remain in the working directory, excluded by `.gitignore`, available for v0.3 planning.

---

### 3. What can eventually be archived/discarded? (23 items)

| Item | Owner Approval Required? |
|------|--------------------------|
| `.kilo/` | Yes |
| 5× `GOLD_*.dxf` (root copies) | Yes |
| `corpus/` (public fixtures) | Yes |
| `f3_diagnostic_0171/` | Yes |
| 8× `gold_0172_*` outputs | Yes |
| `probe_evidence_report.md` | Yes |
| `report_5c.md` | Yes |
| `get_diff.py` | Yes |
| `test_excel.py`, `test_excel2.py`, `test_write.txt` | Yes |
| `tmp_tests/` | Yes |
| `benchmark/` research/build artifacts (scripts, reports, Rust builds, tmp_bench) | Yes |

**Total**: 23 paths safe to discard after owner sign-off.

---

## Next Steps (Not Executed Here)

1. **Owner approval** on F-category discard list
2. **Create v0.3 baseline commit** with 22 new files (structured as above)
3. **Move D-category to separate research archive** (optional, for cleanliness)
4. **Provision `_LOCAL_TEST_CORPUS/`** separately for v0.3 test execution
5. **Begin v0.3 development** on clean baseline

---

**V0.3 RECOVERY — PRESERVATION MANIFEST COMPLETE**

No commits, no deletions, no modifications performed. All decisions documented for management review.