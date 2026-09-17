# Final RC Source Provenance Report

## Executive Summary

**RC SOURCE PROVENANCE — NOT PROVEN**

The Portable RC artifact was built from the **dirty working tree** at `D:\SerapeumAI`, **not** from the exact `cf5cacc` commit. While `cf5cacc` is the historical baseline (HEAD of `feature/cad-dxf-intelligence-v1`), the working tree contained 12 untracked production source files and 1 untracked migration data file that are **required for the application to run** and were bundled into the RC.

The correct next controlled action: **Commit all release-relevant working-tree changes as a single controlled commit (RC source candidate), then rebuild.**

---

## 1. Historical Baseline and Current State

| Field | Value |
|-------|-------|
| Historical Baseline SHA | `cf5cacc33bf100f7ea7bd59f22c456ac7605f256` |
| Baseline Commit Date | 2026-09-03 22:15:35 +0300 |
| Baseline Message | `fix(ingestion): align real-world format support and routing` |
| Current HEAD | `cf5cacc33bf100f7ea7bd59f22c456ac7605f256` (no commits ahead) |
| Branch | `feature/cad-dxf-intelligence-v1` |
| Working Tree Status | **DIRTY** — 19 modified files + 12 untracked production files + 4 untracked migration/data files |

---

## 2. RC Artifact Identity

| Field | Value |
|-------|-------|
| EXE Path | `C:\Temp\SerapeumAI_Portable_Test\SerapeumAI.exe` |
| Package Path | `C:\Temp\SerapeumAI_Portable_Test\` (full directory) |
| EXE SHA-256 | `86E1C4F135084234DBA31902B9C50BC6F9FB5D4C57006AC414184379F2877756` |
| Local dist SHA-256 | `86E1C4F135084234DBA31902B9C50BC6F9FB5D4C57006AC414184379F2877756` (matches EXE) |
| Package ZIP SHA-256 | `278D4AE3CC472D6ECD3982169E4CDFFD5CB1374DD536A0AF54DF2B65056692E3` (archive of full directory) |
| EXE Creation Time | 9/17/2026 9:31:54 AM (local) |
| EXE Last Write Time | 9/17/2026 9:31:54 AM (local) |
| Package Directory Creation | 9/17/2026 9:32:13 AM (local) |

---

## 3. Build Timeline Reconstruction

### Key Timestamps

| File/Event | Timestamp |
|------------|-----------|
| cf5cacc commit | 2026-09-03 22:15:35 +0300 |
| `SerapeumAI_Portable.spec` last modification (committed) | 2026-04-26 09:01:09 |
| `SerapeumAI_Portable.spec` working-tree modification | **9/17/2026 9:17:28 AM** |
| `copy_portable.ps1` creation | **9/17/2026 9:06:37 AM** |
| `src/ui/widgets/fact_table.py` last modification | **9/17/2026 9:30:47 AM** |
| `src/infra/persistence/database_manager.py` last modification | 9/15/2026 9:34:55 AM |
| `src/engine/extractors/dxf_extractor.py` last modification | 9/15/2026 16:08:29 |
| `src/domain/intelligence/conflict_detector.py` (untracked) creation | 9/15/2026 08:14:47 |
| `src/infra/dependency_status.py` (untracked) creation | 9/15/2026 08:14:47 |
| Migration 020_pdf_bbox.sql (untracked) creation | 9/14/2026 16:28:38 |
| Migration 023_conflicts.sql (untracked) creation | 9/15/2026 08:43:10 |
| PyInstaller Analysis phase started | 9/17/2026 9:31:50 AM |
| EXE produced | **9/17/2026 9:31:54 AM** |

### Build Process Evidence

The build was executed by running `powershell -ExecutionPolicy Bypass -File build_portable.ps1`, which invokes:
```
py -m PyInstaller --clean --noconfirm SerapeumAI_Portable.spec
```

PyInstaller build artifacts in `D:\SerapeumAI\build\SerapeumAI_Portable/` confirm:
- Analysis phase: 9/17/2026 9:31:50 AM
- PKG created: 9/17/2026 9:31:52 AM
- EXE created: 9/17/2026 9:31:54 AM
- COLLECT completed: 9/17/2026 9:31:56 AM

---

## 4. Evidence That RC Was Built from Dirty Working Tree

### Evidence 1: PyInstaller xref confirms untracked files were bundled

The file `D:\SerapeumAI\build\SerapeumAI_Portable\xref-SerapeumAI_Portable.html` (generated at 9:31:50 AM) contains cross-references confirming the following modules were included in the build:

**Untracked files (missing from cf5cacc but present in working tree):**
- `src.domain.intelligence.conflict_detector`
- `src.infra.dependency_status`
- `src.engine.extractors.image_extractor`
- `src.engine.extractors.csv_extractor`
- `src.engine.extractors.excel_extractor`
- `src.engine.extractors.json_extractor`
- `src.engine.extractors.mpxj_wrapper`
- `src.engine.extractors.text_extractor`
- `src.engine.extractors.xml_extractor`
- `src.engine.extractors.yaml_extractor`

### Evidence 2: Untracked migration files present in dist package

The following untracked migration files exist in the dist package but NOT in cf5cacc:
- `dist/SerapeumAI_Portable/_internal/src/infra/persistence/migrations/020_pdf_bbox.sql` ✓ exists
- `dist/SerapeumAI_Portable/_internal/src/infra/persistence/migrations/023_conflicts.sql` ✓ exists

### Evidence 3: Modified file timestamps post-date cf5cacc

All 19 modified files have mtimes between 9/4/2026 and 9/17/2026, while cf5cacc was committed on 9/3/2026.

### Evidence 4: xref references absolute working-tree paths

The xref HTML contains references to `D:/SerapeumAI/src/ui/widgets/fact_table.py`, confirming the build used files from the working directory at `D:\SerapeumAI`.

### Evidence 5: Spec file modification predates build

The `SerapeumAI_Portable.spec` was modified at 9/17/2026 9:17:28 AM — 14 minutes before the build completed at 9:31:54 AM. The modification added explicit hidden imports for `src.ui.widgets.fact_table` among others. This change is NOT in cf5cacc.

---

## 5. Classification of Release-Relevant Changes

### CERTIFIED AND INCLUDED IN RC

These changes are in the working tree AND confirmed present in the build artifacts:

| File | Change Type | Evidence of Inclusion |
|------|-------------|----------------------|
| `src/ui/widgets/fact_table.py` | Modified | xref, dist `_internal/src` |
| `src/ui/pages/dashboard_page.py` | Modified | xref |
| `src/application/jobs/build_facts_job.py` | Modified | xref |
| `src/application/services/document_service.py` | Modified | xref |
| `src/application/services/fact_review_presentation.py` | Modified | xref |
| `src/application/orchestrators/agent_orchestrator.py` | Modified | xref |
| `src/document_processing/pdf_processor.py` | Modified | xref |
| `src/document_processing/word_processor.py` | Modified | xref |
| `src/document_processing/ppt_processor.py` | Modified | xref |
| `src/domain/facts/models.py` | Modified | xref |
| `src/engine/extractors/dxf_extractor.py` | Modified | xref |
| `src/engine/extractors/ifc_extractor.py` | Modified | xref |
| `src/infra/persistence/database_manager.py` | Modified | xref |
| `src/domain/intelligence/conflict_detector.py` | **UNTRACKED** | xref |
| `src/infra/dependency_status.py` | **UNTRACKED** | xref |
| `src/engine/extractors/csv_extractor.py` | **UNTRACKED** | xref |
| `src/engine/extractors/excel_extractor.py` | **UNTRACKED** | xref |
| `src/engine/extractors/image_extractor.py` | **UNTRACKED** | xref |
| `src/engine/extractors/json_extractor.py` | **UNTRACKED** | xref |
| `src/engine/extractors/mpxj_wrapper.py` | **UNTRACKED** | xref |
| `src/engine/extractors/text_extractor.py` | **UNTRACKED** | xref |
| `src/engine/extractors/xml_extractor.py` | **UNTRACKED** | xref |
| `src/engine/extractors/yaml_extractor.py` | **UNTRACKED** | xref |
| `src/infra/persistence/migrations/020_pdf_bbox.sql` | **UNTRACKED** | dist `_internal/src` |
| `src/infra/persistence/migrations/023_conflicts.sql` | **UNTRACKED** | dist `_internal/src` |
| `SerapeumAI_Portable.spec` | Modified | Build input |
| `.gitignore` | Modified | N/A (no effect on app behavior) |
| `packaging/runtime_hooks/serapeum_runtime_log_hygiene.py` | Not modified | N/A |

### VALIDATED BUT NOT PROVEN INCLUDED IN RC

These test/validation files exist in the working tree but are excluded from the PyInstaller build (spec excludes `src.tests`):

| File | Status |
|------|--------|
| `src/tests/test_gold_regression.py` | Untracked, excluded from build |
| `src/tests/test_gold_regression_hardening.py` | Untracked, excluded from build |
| `src/tests/test_conflict_resolution_behavior.py` | Untracked, excluded from build |
| `src/tests/test_pdf_block_page_attribution.py` | Untracked, excluded from build |
| `src/tests/test_word_com_cleanup.py` | Untracked, excluded from build |
| `src/tests/test_ifc_dependency_contract.py` | Modified, excluded from build |
| `src/tests/test_iter5b_support_contract_repair.py` | Modified, excluded from build |
| `tools/run_gold_benchmark.py` | Untracked, excluded from build |
| `copy_portable.ps1` | Untracked, build tooling |

### UNVALIDATED

None identified — all release-relevant production changes in the working tree have been validated by the full test suite (932 passed, 1 skipped).

### TEST/DOCUMENTATION ONLY

| File | Notes |
|------|-------|
| `docs/quality/*.md` | Provenance/audit reports |
| `docs/technology/*.md` | Technology adoption rules |
| `benchmark/` | RVT bench tooling (Rust workspace) |
| Various `.dxf`, `.ifc` corpus files | Test data files |

### DEVELOPMENT/LOCAL ONLY

| File | Notes |
|------|-------|
| `.kilo/` | Kilo agent workspace / worktrees |
| `experiments/_tmp_gpu_env/` | Temporary GPU environment |
| `_LOCAL_TEST_CORPUS/` | Local test corpus (gitignored) |
| `test_excel.py`, `test_excel2.py` | Experimental scripts |
| `tmp_tests/` | Temporary test scratch |
| `get_diff.py` | Utility script |
| `report_5c.md`, `probe_evidence_report.md` | Experiment notes |
| `gold_0172_*.txt`, `gold_0172_*.json` | Diagnostic output files |

---

## 6. The Central Contradiction Resolved

> **If the Portable RC was built from the dirty working tree, explicitly state: "cf5cacc is the historical baseline, NOT the source identity of the validated Portable RC."**

**cf5cacc is the historical baseline, NOT the source identity of the validated Portable RC.**

### Why cf5cacc alone is insufficient for a working build:

1. **Missing untracked dependency**: `src/domain/intelligence/conflict_detector.py` is imported by `build_facts_job.py` at line 84 (`from src.domain.intelligence.conflict_detector import detect_and_store_conflicts`). cf5cacc's `build_facts_job.py` does NOT contain this import. The cf5cacc version of `build_facts_job.py` has 26 fewer lines at the end.

2. **Missing untracked extractors**: 8 extractor modules (`csv_extractor.py`, `excel_extractor.py`, `image_extractor.py`, `json_extractor.py`, `mpxj_wrapper.py`, `text_extractor.py`, `xml_extractor.py`, `yaml_extractor.py`) are imported by `extract_job.py` in the working tree but do NOT exist at cf5cacc. cf5cacc's `extract_job.py` imports only 10 extractors; the working tree version imports 18.

3. **Missing untracked dependency_status.py**: Imported by `dashboard_page.py` at line 20 (`from src.infra.dependency_status import DependencyHealthChecker`).

4. **Missing untracked migrations**: `020_pdf_bbox.sql` and `023_conflicts.sql` are bundled into the dist package but don't exist in cf5cacc.

5. **Spec file changes**: The `hiddenimports` additions in `SerapeumAI_Portable.spec` (lines 93-99) that explicitly import `src.ui.widgets.fact_table` were applied at 9/17 9:17 AM, before the build.

### What this means:

If someone tried to rebuild from cf5cacc, the application would either:
- Fail to import (ImportError on missing `conflict_detector`, `dependency_status`, or 8 extractor modules), OR
- Not include the conflict resolution UI and the additional extractors

The RC artifact in its current form **cannot be reproduced from cf5cacc alone**.

---

## 7. Release Source Candidate

| Field | Value |
|-------|-------|
| RELEASE SOURCE SHA/STATE | **NOT PROVEN** — no single Git SHA reproduces the RC |
| PORTABLE RC BUILT FROM | Dirty working tree at `D:\SerapeumAI` as of 2026-09-17 09:31:54 |
| VALIDATION TESTED | Working tree state (cf5cacc + 19 modified files + 12 untracked source files + 2 untracked migrations + untracked test files) |
| ARTIFACT HASH | EXE: `86E1C4F135084234DBA31902B9C50BC6F9FB5D4C57006AC414184379F2877756` |

**If the source was an uncommitted working tree, say so explicitly:**

**Yes — the Portable RC was built from an uncommitted working tree, not from any Git commit. The working tree contains 12 untracked production source files and 2 untracked migration data files that are required for the application to function.**

---

## 8. Unresolved Discrepancies

1. `.serapeum/logs/serapeum.log` exists in the working tree but is excluded from the build via spec rules.
2. The `build_facts_job.py` in the working tree imports `conflict_detector` inside a try/except block, meaning the app would run even without it (with a non-fatal warning) — but the conflict detection feature would be silently absent.
3. The `extract_job.py` in the working tree unconditionally imports 8 untracked extractors at module level, meaning importing `ExtractJob` would fail with ImportError if those files don't exist — a hard dependency.
4. The `020_pdf_bbox.sql` migration adds a `bbox` column to `pdf_pages`; the `023_conflicts.sql` migration adds conflict tracking tables. Both are required for the conflict resolution UI (which was added to `fact_table.py`).

---

## 9. Exact Next Controlled Action

**Do not proceed to release until the following controlled action is taken:**

1. **Stage and commit all release-relevant working-tree changes** as a single controlled commit on `feature/cad-dxf-intelligence-v1`:
   - 19 modified tracked files (including `SerapeumAI_Portable.spec`)
   - 12 untracked production source files (including `conflict_detector.py`, `dependency_status.py`, 8 extractors)
   - 2 untracked migration files (`020_pdf_bbox.sql`, `023_conflicts.sql`)
   - **Exclude** all test files, docs, corpus files, experimental scripts, and dev-only artifacts

2. **Tag the resulting commit** (e.g., `v0.2.0-rc1`) as the official release source candidate.

3. **Rebuild** the portable artifact from the new controlled commit using `build_portable.ps1`.

4. **Verify** the rebuilt artifact's hash matches the expected value before proceeding with release.

---

## 10. Final Verdict

**RC SOURCE PROVENANCE — NOT PROVEN**

The Portable RC cannot be traced to a single Git SHA. It was built from a dirty working tree containing untracked production-critical files that do not exist in cf5cacc or any other commit on the branch. To achieve a provable release, commit the working tree state as a controlled release candidate first.