# WP-07A: Gold Regression Hardening — Changes and Verification

**Date:** 2026-09-16
**Branch:** `feature/cad-dxf-intelligence-v1`
**HEAD:** `cf5cacc`
**Scope:** Harden the Gold Regression system so PASS means an advertised engineering capability has not materially degraded.

---

## FACTS

- Pre-change baseline: `docs/quality/GOLD_REGRESSION_RESULTS_PRE_WP07A.json` (2026-09-15, generated with old tool)
- Post-change results: `docs/quality/GOLD_REGRESSION_RESULTS.json` (2026-09-15, generated with hardened tool)
- The pre-change baseline was generated with the old benchmark tool (binary `provenance_rate` only, no entity-ID or type-preservation metrics).
- The post-change results were generated with the hardened benchmark tool (format-aware provenance quality, entity-ID stability, record-type preservation, 7-condition admission gate).

## MEASURED RESULTS

### Before → After (key formats)

| Format | Records | Prov (key) | Prov Quality | Entity-ID Stability | Avg Timing | Status |
|--------|---------|------------|--------------|---------------------|------------|--------|
| .dxf   | 7820 → 7820 | 0.0 → 0.0 | N/A → **1.0** | N/A → **1.0** | 6150.7 → 6636.6ms | PASS → PASS |
| .pdf   | 40 → 40 | 1.0 → 1.0 | N/A → **0.6236** | N/A → **1.0** | 19477.1 → 20621.6ms | PASS → PASS |
| .ifc   | 32342 → 32342 | 1.0 → 1.0 | N/A → **1.0** | N/A → **1.0** | 3285.0 → 3262.3ms | PASS → PASS |
| .xer   | 11979 → 11979 | 1.0 → 1.0 | N/A → **1.0** | N/A → **1.0** | 41.1 → 48.5ms | PASS → PASS |
| .image | 14 → 14 | 1.0 → 1.0 | N/A → **1.0** | N/A → **1.0** | 1.1 → 0.4ms | PASS → PASS |
| .mpp   | 0 → 0 | 0.0 → 0.0 | N/A → 0.0 | N/A → 1.0 | 0 → 0ms | FAIL → FAIL |

### Interpretation

- **DXF provenance quality jumped from N/A (unmeasured) to 1.0** — the `source_file` field on `dxf_layer` and `dxf_block` records now satisfies the format-aware provenance quality check. All 8 DXF record types carry `data.source_file`.
- **All record counts are unchanged** (7820 DXF, 40 PDF, 32342 IFC, 11979 XER, 14 image) — no extraction regressions.
- **Entity-ID stability is 1.0 for all active formats** — deterministic extraction confirmed (DXF handles, XER task IDs, XLSX row indices, IFC GlobalIds).
- **Timing is within 2× baseline for all formats** (PDF: 19477→20622ms = 1.06×, DXF: 6151→6637ms = 1.08×). No performance regression.
- **PDF provenance quality is 0.6236** — `pdf_page` records have full `page`+`method` provenance (100%); `doc_classification` and `doc_blocks` records have partial provenance. This is the correct measurement.
- **MPP FAIL is pre-existing** — Java runtime unavailable on this machine; both baseline and candidate report the same failure. The gate classifies this as a pre-existing failure, not a regression.

### Admission Gate

All 7 conditions evaluated for each format:

1. Extraction success preserved
2. Record count ≥ 90% of baseline (<90% = FAIL; 90–99% = informational note)
3. Record types preserved
4. Entity ID stability ≥ 99%
5. Provenance quality ≥ baseline (format-aware; when baseline predates the metric, check absolute floor and flag the missing baseline explicitly)
6. Timing ≤ 2× baseline
7. No new failures introduced (pre-existing failures with same failure count are noted, not failed)

**Overall: ALL CONDITIONS PASS** for all 24 active formats. `.mpp` is a pre-existing failure (Java runtime unavailable), noted not failed. `.dwg` and `.rvt` are UNAVAILABLE (no open-source extractor).

## CHANGES

### WP-07A new code (untracked, not in HEAD)

| File | What |
|------|------|
| `tools/run_gold_benchmark.py` | New: hardened benchmark tool with format-aware provenance quality, entity-ID stability, record-type preservation, 7-condition admission gate, and `--compare` mode |
| `src/tests/test_gold_regression_hardening.py` | New: 25 hardening tests (see table below) |
| `docs/quality/GOLD_REGRESSION_RESULTS_PRE_WP07A.json` | New: pre-change baseline (frozen) |
| `docs/quality/GOLD_REGRESSION_RESULTS.json` | New: post-change results (regenerated) |
| `docs/quality/WP07A_CHANGES_AND_VERIFICATION.md` | This report |

### `src/engine/extractors/dxf_extractor.py` — `source_file` additions (WP-07A)

The committed HEAD version already had `source_file` on:
- `dxf_unsupported` records
- `dxf_drawing` records
- Entity records (LINE, CIRCLE, etc.)
- `ExtractionResult.metadata`

WP-07A adds `source_file` to three record types that lacked it:
- `dxf_layer` records (line 300 in working tree)
- `dxf_block` records (line 628 in working tree)
- Orphan entity records from direct ENTITIES section parsing (lines 685, 708)

The large `git diff` (291 insertions, 32 deletions) for this file includes other uncommitted branch work from `feature/cad-dxf-intelligence-v1` that is **not** part of WP-07A. Only the `source_file` additions listed above are WP-07A.

### `src/tests/test_gold_regression.py` — MPP skip condition fix

Updated the MPP test skip condition to match the current Java-unavailable diagnostic message ("Java runtime not found" / "JAVA_HOME" / "JDK"), which no longer contains the old "JVM"/"jre" strings. This changes the test from FAIL to SKIP, which is the correct classification for an environment limitation.

### Benchmark tool: `tools/run_gold_benchmark.py`

- **Format-aware provenance quality** (`_provenance_quality_rate`): checks meaningful fields per format family (DXF: `data.source_file`, PDF: `provenance.page`+`method`, etc.)
- **Record-type preservation** (`_type_distribution` + `EXPECTED_TYPES`): verifies expected type sets are present
- **Entity-ID stability** (`_entity_ids` + dual-run): runs extraction twice, compares ID sets for DXF, IFC, XER, XLSX/XLSM/XLS
- **7-condition admission gate** (`compare_baseline` + `--compare` flag): compares candidate against baseline
- **Gate condition 2**: <90% = FAIL; 90–99% = informational note (not a gate failure); 100% = pass
- **Gate condition 5**: when baseline lacks `avg_provenance_quality_rate` (pre-WP07A), checks absolute floor (quality > 0 for successful extractions) and flags the missing baseline explicitly as a note. Never silently skips.
- **Pre-existing failure handling**: when both baseline and candidate have the same failure count, the gate notes it as pre-existing rather than flagging it as a regression
- **Refactoring**: summary-building extracted into `_build_output()` so `--compare` mode works correctly

### Test module: `src/tests/test_gold_regression_hardening.py` (25 tests)

| Test class | Tests | What they verify |
|------------|-------|-----------------|
| `TestDXFSourceFileCompleteness` | 3 | All DXF record types carry `data.source_file`; specifically `dxf_layer` and `dxf_block` |
| `TestRecordTypePreservation` | 3 | Expected type sets present for DXF, XER, PDF |
| `TestEntityIDStability` | 4 | DXF handles, XER task IDs, IFC GlobalIds, XLSX row indices stable across two extraction runs (≥99% overlap) |
| `TestProvenanceQuality` | 3 | Format-aware provenance quality: DXF `data.source_file` ≥90%, PDF `pdf_page` records ≥90%, XER `provenance.table` ≥90% |
| `TestPDFTiming` | 2 | Large PDF (4.4MB) under 45s (measured); medium PDF (62KB) under 5s (measured) |
| `TestAdmissionGate` | 9 | Unit tests for `compare_baseline`: pass, extraction-success regression, record-count regression, new failures, UNAVAILABLE skip, performance regression, entity-ID instability, record-type loss, provenance quality regression |

## TEST RESULTS

### Hardening tests (new)

```
24 passed in ~205s
```

All 24 tests pass. No failures.

### Existing gold regression tests

```
28 passed, 1 skipped (MPP/Java unavailable), 0 failed
```

The MPP test now correctly skips (was failing before the skip-condition fix). All other 28 tests pass.

## REGRESSIONS

**None detected.** All 7 admission gate conditions pass for every active format.

- Record counts: identical (7820 DXF, 40 PDF, 32342 IFC, 11979 XER, 14 image)
- Extraction success: identical (3/3 for DXF, PDF, IFC, XER; 14/14 for image)
- Entity-ID stability: 1.0 across all formats
- Timing: within 2× baseline for all formats (worst: PPT at 1.36×, PDF at 1.06×, DXF at 1.08×)
- Record types: all preserved

## REMAINING GAPS

1. **PDF provenance quality is 0.6236, not 1.0** — `doc_classification` records have `provenance.source` but not `page`+`method`; `doc_blocks` records have `provenance.method` but not `page`. Future work: add `page` to these record types.
2. **MPP extraction blocked** — Java runtime not found. Pre-existing environment issue. The gate correctly classifies this as a pre-existing failure, not a regression.
3. **DWG and RVT** — No open-source extractors exist. Correctly reported as UNAVAILABLE.
4. **Pre-WP07A baseline lacks `avg_provenance_quality_rate` and `avg_entity_id_stability`** — These fields were not measured by the old tool. The gate now flags this explicitly (not silently skipped) and checks an absolute floor. Future baselines generated with the hardened tool will include these fields, enabling full regression checking.

## CONTROLLED ARTIFACTS

| File | Status |
|------|--------|
| `docs/quality/GOLD_REGRESSION_RESULTS_PRE_WP07A.json` | Pre-change baseline (frozen) |
| `docs/quality/GOLD_REGRESSION_RESULTS.json` | Post-change results (regenerated) |
| `tools/run_gold_benchmark.py` | New: hardened benchmark tool |
| `src/tests/test_gold_regression_hardening.py` | New: 24 hardening tests |
| `src/engine/extractors/dxf_extractor.py` | `source_file` added to `dxf_layer`, `dxf_block`, and 2 orphan-entity records (WP-07A); other diff lines are pre-existing branch work |
| `src/tests/test_gold_regression.py` | MPP skip condition updated to match current diagnostic |
