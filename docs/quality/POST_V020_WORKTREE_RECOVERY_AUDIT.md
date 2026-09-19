# POST-v0.2.0 WORKTREE RECOVERY AUDIT (RECONCILED)

**Baseline**: `v0.2.0` → `c7f299fad601b3a6fc9637571ac1ae17681416e3`
**Audit Date**: 2026-09-17
**Status**: POST-v0.2.0 RECOVERY — CLASSIFICATION VALIDATION COMPLETE

---

## Exact Git Status

```bash
$ git -C D:\SerapeumAI status --short
?? .kilo/
?? GOLD_0150.dxf
?? GOLD_0151.dxf
?? GOLD_0152.dxf
?? GOLD_0167.dxf
?? GOLD_0168.dxf
?? benchmark/
?? copy_portable.ps1
?? corpus/
?? docs/quality/FINAL_PUBLISH_READINESS_REPORT.md
?? docs/quality/FINAL_RC2_CLEAN_REPRODUCTION_REPORT.md
?? docs/quality/FINAL_RC_CLEAN_REPRODUCTION_REPORT.md
?? docs/quality/FINAL_RELEASE_EXECUTION_REPORT.md
?? docs/quality/GOLD_BENCHMARK_SCORECARD.md
?? docs/quality/GOLD_REGRESSION_RESULTS.json
?? docs/quality/GOLD_REGRESSION_RESULTS_PRE_WP07A.json
?? docs/quality/P1_PDF_BLOCK_PAGE_ATTRIBUTION.md
?? docs/quality/POST_V020_WORKTREE_RECOVERY_AUDIT.md
?? docs/quality/SERAPEUMAI_SCORECARD.md
?? docs/quality/WORKING_TREE_RECONCILIATION_REPORT.md
?? docs/quality/WP01_DEPENDENCY_RECOVERY_REPORT.md
?? docs/quality/WP02_DEPENDENCY_TRANSPARENCY_REPORT.md
?? docs/quality/WP03_EVIDENCE_ANCHORS_REPORT.md
?? docs/quality/WP04_CONFLICT_DETECTION_REPORT.md
?? docs/quality/WP05A_CONFLICT_RESOLUTION_AND_OUTPUT_VALIDATION_REPORT.md
?? docs/quality/WP05_ACCEPTANCE_AUDIT.md
?? docs/quality/WP05_AI_HONESTY_AND_CONFLICT_PRESENTATION_REPORT.md
?? docs/quality/WP06A_BENCHMARK_CONTRACT_HARDENING.md
?? docs/quality/WP06_GOLD_REGRESSION_FRAMEWORK.md
?? docs/quality/WP07B_PDF_PROVENANCE_INVESTIGATION.md
?? docs/technology/
?? experiments/
?? f3_diagnostic_0171/
?? get_diff.py
?? gold_0172.ifc
?? gold_0172_analyze.txt
?? gold_0172_diag.json
?? gold_0172_elements.json
?? gold_0172_elements_all.json
?? gold_0172_ifc_output.txt
?? gold_0172_ifc_strict.txt
?? gold_0172_inspect.json
?? probe_evidence_report.md
?? report_5c.md
?? slik_rvt_scripts_260902.zip
?? slik_rvt_scripts_extracted/
?? src/tests/test_word_com_cleanup.py
?? test_excel.py
?? test_excel2.py
?? test_write.txt
?? tmp_tests/
```

**Exact counts**: 0 modified tracked, 51 untracked paths, 0 staged.

---

## Reconciled Classification (Every Path Appears Once)

| # | Path | Category | Disposition |
|---|------|----------|-------------|
| 1 | `.kilo/` | **F** | ARCHIVE |
| 2 | `GOLD_0150.dxf` | **F** | ARCHIVE |
| 3 | `GOLD_0151.dxf` | **F** | ARCHIVE |
| 4 | `GOLD_0152.dxf` | **F** | ARCHIVE |
| 5 | `GOLD_0167.dxf` | **F** | ARCHIVE |
| 6 | `GOLD_0168.dxf` | **F** | ARCHIVE |
| 7 | `benchmark/` | **C** | **COMMIT TO V0.3** (as infrastructure) |
| 8 | `copy_portable.ps1` | **B** | **COMMIT TO V0.3** |
| 9 | `corpus/` | **F** | ARCHIVE |
| 10 | `docs/quality/FINAL_PUBLISH_READINESS_REPORT.md` | **E** | **COMMIT TO V0.3** (release history) |
| 11 | `docs/quality/FINAL_RC2_CLEAN_REPRODUCTION_REPORT.md` | **E** | **COMMIT TO V0.3** |
| 12 | `docs/quality/FINAL_RC_CLEAN_REPRODUCTION_REPORT.md` | **E** | **COMMIT TO V0.3** |
| 13 | `docs/quality/FINAL_RELEASE_EXECUTION_REPORT.md` | **E** | **COMMIT TO V0.3** |
| 14 | `docs/quality/GOLD_BENCHMARK_SCORECARD.md` | **C** | **COMMIT TO V0.3** |
| 15 | `docs/quality/GOLD_REGRESSION_RESULTS.json` | **C** | **COMMIT TO V0.3** |
| 16 | `docs/quality/GOLD_REGRESSION_RESULTS_PRE_WP07A.json` | **C** | **COMMIT TO V0.3** |
| 17 | `docs/quality/P1_PDF_BLOCK_PAGE_ATTRIBUTION.md` | **E** | **COMMIT TO V0.3** |
| 18 | `docs/quality/POST_V020_WORKTREE_RECOVERY_AUDIT.md` | **E** | **COMMIT TO V0.3** |
| 19 | `docs/quality/SERAPEUMAI_SCORECARD.md` | **E** | **COMMIT TO V0.3** |
| 20 | `docs/quality/WORKING_TREE_RECONCILIATION_REPORT.md` | **E** | **COMMIT TO V0.3** |
| 21 | `docs/quality/WP01_DEPENDENCY_RECOVERY_REPORT.md` | **E** | **COMMIT TO V0.3** |
| 22 | `docs/quality/WP02_DEPENDENCY_TRANSPARENCY_REPORT.md` | **E** | **COMMIT TO V0.3** |
| 23 | `docs/quality/WP03_EVIDENCE_ANCHORS_REPORT.md` | **E** | **COMMIT TO V0.3** |
| 24 | `docs/quality/WP04_CONFLICT_DETECTION_REPORT.md` | **E** | **COMMIT TO V0.3** |
| 25 | `docs/quality/WP05A_CONFLICT_RESOLUTION_AND_OUTPUT_VALIDATION_REPORT.md` | **E** | **COMMIT TO V0.3** |
| 26 | `docs/quality/WP05_ACCEPTANCE_AUDIT.md` | **E** | **COMMIT TO V0.3** |
| 27 | `docs/quality/WP05_AI_HONESTY_AND_CONFLICT_PRESENTATION_REPORT.md` | **E** | **COMMIT TO V0.3** |
| 28 | `docs/quality/WP06A_BENCHMARK_CONTRACT_HARDENING.md` | **C** | **COMMIT TO V0.3** |
| 29 | `docs/quality/WP06_GOLD_REGRESSION_FRAMEWORK.md` | **C** | **COMMIT TO V0.3** |
| 30 | `docs/quality/WP07B_PDF_PROVENANCE_INVESTIGATION.md` | **E** | **COMMIT TO V0.3** |
| 31 | `docs/technology/` | **D** | **KEEP OUTSIDE SOURCE BUT PRESERVE** |
| 32 | `experiments/` | **D** | **KEEP OUTSIDE SOURCE BUT PRESERVE** |
| 33 | `f3_diagnostic_0171/` | **F** | ARCHIVE |
| 34 | `get_diff.py` | **F** | ARCHIVE |
| 35 | `gold_0172.ifc` | **D** | **KEEP OUTSIDE SOURCE BUT PRESERVE** |
| 36 | `gold_0172_analyze.txt` | **F** | ARCHIVE |
| 37 | `gold_0172_diag.json` | **F** | ARCHIVE |
| 38 | `gold_0172_elements.json` | **F** | ARCHIVE |
| 39 | `gold_0172_elements_all.json` | **F** | ARCHIVE |
| 40 | `gold_0172_ifc_output.txt` | **F** | ARCHIVE |
| 41 | `gold_0172_ifc_strict.txt` | **F** | ARCHIVE |
| 42 | `gold_0172_inspect.json` | **F** | ARCHIVE |
| 43 | `probe_evidence_report.md` | **F** | ARCHIVE |
| 44 | `report_5c.md` | **F** | ARCHIVE |
| 46 | `slik_rvt_scripts_260902.zip` | **D** | **KEEP OUTSIDE SOURCE BUT PRESERVE** |
| 47 | `slik_rvt_scripts_extracted/` | **D** | **KEEP OUTSIDE SOURCE BUT PRESERVE** |
| 48 | `src/tests/test_word_com_cleanup.py` | **B** | **COMMIT TO V0.3** |
| 49 | `test_excel.py` | **F** | ARCHIVE |
| 50 | `test_excel2.py` | **F** | ARCHIVE |
| 51 | `test_write.txt` | **F** | ARCHIVE |
| 52 | `tmp_tests/` | **F** | ARCHIVE |

**Total: 51 paths** (the audit report itself is path #18)

---

## Category Summary (Reconciled)

| Category | Count | Paths |
|----------|-------|-------|
| **B — Valuable incomplete enhancement** | 2 | `copy_portable.ps1`, `src/tests/test_word_com_cleanup.py` |
| **C — Test/benchmark infrastructure** | 5 | `benchmark/`, `GOLD_BENCHMARK_SCORECARD.md`, `GOLD_REGRESSION_RESULTS.json`, `GOLD_REGRESSION_RESULTS_PRE_WP07A.json`, `WP06A_BENCHMARK_CONTRACT_HARDENING.md`, `WP06_GOLD_REGRESSION_FRAMEWORK.md` |
| **D — Research/experimental** | 6 | `docs/technology/`, `experiments/`, `gold_0172.ifc`, `slik_rvt_scripts_260902.zip`, `slik_rvt_scripts_extracted/` |
| **E — Documentation/governance** | 15 | All 15 quality reports + this audit + reconciliation |
| **F — Temporary/scratch** | 23 | `.kilo/`, 5 GOLD DXF files, `corpus/`, `f3_diagnostic_0171/`, 8 gold_0172 outputs, `get_diff.py`, `probe_evidence_report.md`, `report_5c.md`, `test_excel.py`, `test_excel2.py`, `test_write.txt`, `tmp_tests/` |

**Total: 2+5+6+15+23 = 51** ✅

---

## Critical Investigation: Benchmark/Corpus/GOLD Files vs. 932-Test Baseline

### What the Tests Actually Require

**Test reference analysis** (144 test lines referencing corpus/GOLD/benchmark):

```python
# test_gold_regression.py:35
CORPUS_DIR = Path(__file__).resolve().parents[2] / "_LOCAL_TEST_CORPUS" / "GOLD_BENCHMARK_V1"

# test_gold_regression_hardening.py:25
CORPUS_DIR = Path(__file__).resolve().parents[2] / "_LOCAL_TEST_CORPUS" / "GOLD_BENCHMARK_V1"
```

**Tests that require the corpus** (all skip if missing):
- `test_gold_regression.py`: 29 tests (22 skip when corpus missing)
- `test_gold_regression_hardening.py`: 24 tests (15 skip when corpus missing)
- `test_word_com_cleanup.py`: 3 tests (require specific DOC files from corpus)
- `test_pdf_block_page_attribution.py`: 4 tests (3 skip when corpus missing)
- `test_iter5b_support_contract_repair.py`: 24 tests (all pass without corpus — uses mocks)

**What `_LOCAL_TEST_CORPUS/GOLD_BENCHMARK_V1` contains**: 124 files (PDF, DXF, XLSX, XER, IFC, DOC, CSV, JSON, XML, YAML, images, logs, etc.)

### What the Untracked Paths Provide

| Untracked Path | Role | Required for Tests? |
|----------------|------|---------------------|
| `corpus/` | Small public fixtures (40 files, mostly MD/YAML/PPT/TSV) | **NO** — tests don't reference this |
| `GOLD_0150.dxf`–`GOLD_0168.dxf` (5 files) | Root-level DXF copies | **NO** — tests use `_LOCAL_TEST_CORPUS/` path |
| `benchmark/` | 42,532 files: acquisition scripts, research reports, CSV data, manifests | **NO** — not referenced by test suite |
| `GOLD_BENCHMARK_SCORECARD.md` etc. (6 docs) | Historical benchmark results | **NO** — documentation only |

### The Real Dependency

**The 932-test baseline requires `_LOCAL_TEST_CORPUS/GOLD_BENCHMARK_V1` (124 files, ~2.5 GB total)** which is:
- **External to the repository** (not in any untracked path here)
- **Already excluded** by `.gitignore` (`_LOCAL_TEST_CORPUS/`)
- **Required for gold regression tests** (29 + 24 tests skip without it)

**Conclusion**: None of the 51 untracked paths here are required for the gold regression tests. The test corpus lives at `_LOCAL_TEST_CORPUS/` which is a separate local directory.

### What Is Required for v0.3 Regression Testing

| Requirement | Status | Source |
|-------------|--------|--------|
| Gold regression corpus (`_LOCAL_TEST_CORPUS/GOLD_BENCHMARK_V1`) | **External** | Must be provisioned separately |
| Benchmark scripts (`tools/run_gold_benchmark.py`) | **In v0.2.0** | Already committed |
| Test suite (`test_gold_regression*.py`, etc.) | **In v0.2.0** | Already committed |
| Benchmark manifests (`GOLD_BENCHMARK_V1_MANIFEST.csv`) | **In `benchmark/`** | Should be committed |
| Historical results (`GOLD_*.json`, `SCORECARD.md`) | **In untracked docs** | Should be committed for history |

---

## Reassessed Items

### `FINAL_CAPABILITY_CLOSURE_AUDIT.md` — NOT IN UNTRACKED LIST
This file **does not exist** in the current working tree (it was part of RC1 tag but not recreated). The previous audit incorrectly listed it as G-category. **Removed from classification.**

### `copy_portable.ps1` — Content Analysis
```powershell
$src = 'D:\SerapeumAI\dist\SerapeumAI_Portable'
$dst = 'C:\Temp\SerapeumAI_Portable_Test'
if (Test-Path $dst) { Remove-Item $dst -Recurse -Force }
Copy-Item $src $dst -Recurse
Write-Host "Copied to: $dst"
Get-ChildItem $dst | Select-Object Name, Length
```
**Assessment**: Hardcoded paths, no error handling, no logging, no version awareness. **Incomplete but functional skeleton.** Should be committed to v0.3 as `scripts/copy_portable.ps1` with parameterization.

### `test_word_com_cleanup.py` — Content Analysis
- 112 lines, 3 focused tests for Word COM resource cleanup
- References `_LOCAL_TEST_CORPUS/GOLD_BENCHMARK_V1/GOLD_0112.doc`–`GOLD_0116.doc`
- Uses `WordExtractor` from `src.engine.extractors.word_extractor`
- Implements proper fixture cleanup (`_clean_winword`)
- **Complete, well-structured test** — only missing CI integration and corpus provisioning

---

## Final Disposition for Each Category

| Category | Paths | Disposition |
|----------|-------|-------------|
| **B** (2) | `copy_portable.ps1`, `test_word_com_cleanup.py` | **COMMIT TO V0.3** |
| **C** (5) | `benchmark/`, 4 gold result docs, 2 WP06 docs | **COMMIT TO V0.3** (as `benchmark/`, `docs/quality/`) |
| **D** (6) | `docs/technology/`, `experiments/`, `gold_0172.ifc`, 2 Revit archives | **KEEP OUTSIDE SOURCE BUT PRESERVE** |
| **E** (15) | All quality reports + this audit + reconciliation | **COMMIT TO V0.3** (as `docs/quality/`) |
| **F** (23) | Scratch, diagnostics, temp files, root GOLD DXF copies, `corpus/` | **ARCHIVE** (DISCARD ONLY AFTER OWNER APPROVAL) |

---

## Answer: What Is Genuinely Required for v0.3 Regression Baseline?

### **REQUIRED (Must Have for Reproducible Testing)**

| Item | Location | Why |
|------|----------|-----|
| Gold regression test suite | `src/tests/test_gold_regression*.py` (in v0.2.0) | Core regression logic |
| Benchmark comparison tool | `tools/run_gold_benchmark.py` (in v0.2.0) | Admission gate logic |
| Test manifests/historical baselines | `benchmark/GOLD_BENCHMARK_V1_MANIFEST.csv`, `GOLD_*.json` (untracked) | Baseline data for comparison |
| Word COM cleanup test | `src/tests/test_word_com_cleanup.py` (untracked) | Prevents regression in Word extraction |

### **NOT REQUIRED (Historical/Research/Local Only)**

| Item | Why Not Required |
|------|------------------|
| `_LOCAL_TEST_CORPUS/GOLD_BENCHMARK_V1` (124 files) | External test fixtures — must be provisioned per environment; not part of source |
| `corpus/` (40 public fixtures) | Unused by test suite |
| Root `GOLD_*.dxf` (5 files) | Duplicate copies; tests use `_LOCAL_TEST_CORPUS/` |
| `benchmark/` scripts (`acquire_*.py`, `create_*.py`) | One-time acquisition tools, not runtime |
| `benchmark/` research reports (20+ MD/CSV) | Research evidence, not test infrastructure |
| `experiments/`, `docs/technology/`, Revit/IFC research | R&D exploration, not production |
| All F-category scratch/diagnostics | Zero engineering value |

---

## Management Decision Points

1. **Commit test infrastructure to v0.3**: `benchmark/` (manifests + key reports), `tools/` already in repo, `test_word_com_cleanup.py`
2. **Provision `_LOCAL_TEST_CORPUS/` separately**: Not a repo concern — document in v0.3 setup
3. **Archive F-category**: 23 paths safe to discard after owner approval
4. **Preserve D-category externally**: Research artifacts kept but not in source control

**POST-v0.2.0 RECOVERY — CLASSIFICATION VALIDATION COMPLETE**