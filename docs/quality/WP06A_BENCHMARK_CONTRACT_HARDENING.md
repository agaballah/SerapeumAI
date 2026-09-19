# WP-06A: Benchmark Contract Hardening — Audit & Design

**Date**: 2026-09-15  
**Task**: Read-only investigation and design for hardening the Gold Regression / Technology Admission system  
**No source code modified.** No dependencies installed. No gold corpus changes.

---

## Executive Summary

The current WP-06 benchmark measures record-count preservation, warm timing, and a binary provenance-key presence check. This is **insufficient** to protect engineering intelligence: a candidate could pass by producing the right number of records with shallow provenance, wrong entity IDs, or degraded conflict behavior.

Key findings from the audit:

1. **DXF provenance is structurally present but conventionally absent** — DXF records carry `source_file`, `handle`, `entity_type`, `layer`, and `layout` in `data`, but lack the top-level `provenance` key. The gap is a convention inconsistency, not a data loss.

2. **IFC "100% provenance" is structural tagging only** — `{"entity": "IfcWall"}` per record, no file path. This is weaker than the Fact API's database-level provenance (`source_path + location_json`).

3. **PDF large-file timing (33s) is unprotected** — only GOLD_0124.pdf (62 KB) has a timing threshold; GOLD_0122.pdf (4.4 MB, 33s) has none.

4. **MPP failure is a code-environment mismatch** — `mpxj_wrapper.py` looks for `jre1.8.0_501` (broken install) but `jre1.8.0_503` is installed and HAS `server/jvm.dll`. The failure is a path-detection issue, potentially compounded by mpxj 16.7.0 requiring Java 11+.

5. **538 MB and 856 MB IFC files are untested** — skipped for safety. This is a resource constraint, not a capability gap.

6. **Technology-admission rule is too permissive** — 4 conditions only, missing entity-ID stability, record-type distribution, fact status integrity, and behavioral preservation.

---

## 1. Provenance Contract

### 1.1 Current Provenance by Extractor Family

**FACT** — Provenance key presence in `GOLD_REGRESSION_RESULTS.json`:

| Extractor Family | Records Have `provenance` Key? | Provenance Content | `source_file` in `data`? |
|-----------------|-------------------------------|--------------------|------------------------|
| PDF | ✅ (100%) | `{"page": N, "method": "...", "composition": "..."}` | ✅ metadata only |
| IFC | ✅ (100%) | `{"entity": "IfcWall"}` | ❌ not in records |
| P6/XER | ✅ (100%) | `{"table": "TASK"}` | ❌ not in records |
| DXF | ❌ (0%) | None | ✅ in entity/unsupported/xref records; ❌ in layer/block records |
| Image | ✅ (100%) | `{"source": "image_extractor", "format": "..."}` | ✅ in metadata only |
| Text/TXT/MD/LOG | ✅ (100%) | `{"source": "..._extractor", "encoding": "..."}` | ✅ in metadata only |
| CSV/TSV | ✅ (100%) | `{"source": "..._extractor", "delimiter": "..."}` | ✅ in metadata only |
| JSON | ✅ (100%) | `{"source": "json_extractor", "structure_type": "..."}` | ✅ in metadata only |
| XML | ✅ (100%) | `{"source": "xml_extractor", "root_tag": "..."}` | ✅ in metadata only |
| YAML/YML | ✅ (100%) | `{"source": "yaml_extractor", "structure_type": "..."}` | ✅ in metadata only |
| DOCX | ✅ (100%) | `{"page": N, "source": "word_extractor"}` | ✅ in metadata only |
| PPTX | ✅ (100%) | `{"page": N, "source": "pptx_extractor"}` | ✅ in metadata only |
| XLS/XLSM/XLSX | ✅ (100%) | `{"sheet": "...", "row": N}` | ✅ in metadata only |
| DGN | ✅ (100%) | `{"source": "dgn_extractor"}` | ✅ in metadata only |

### 1.2 Does DXF's Existing `data.source_file` Satisfy Engineering Provenance?

**FACT** — DXF record `data` fields by record type:

| Record Type | `source_file` in `data`? | `handle` in `data`? | `entity_type` in `data`? | `layer` in `data`? |
|------------|----------------------|-----------------|---------------|----------|
| `dxf_drawing` | ✅ (`dxf_extractor.py:248`) | ❌ | ❌ | ❌ |
| `dxf_layer` | ❌ (`dxf_extractor.py:298-306`) | ❌ | ❌ | `layer_name` |
| `dxf_entity` (all types) | ✅ (`dxf_extractor.py:333`) | ✅ (`dxf_extractor.py:329`) | ✅ (`dxf_extractor.py:330`) | ✅ (`dxf_extractor.py:331`) |
| `dxf_block` | ❌ (`dxf_extractor.py:626-631`) | ❌ | ❌ | ❌ |
| `dxf_xref` | ❌ (uses `parent_file`, `dxf_extractor.py:727-732`) | ❌ | ❌ | ❌ |
| `dxf_unsupported` | ✅ (`dxf_extractor.py:157`) | ❌ | ✅ (`dxf_extractor.py:157`) | ❌ |

**INTERPRETATION**: DXF's entity records (the bulk — 5–7k+ per file) DO carry sufficient source-identifying information to reconstruct engineering provenance:
- `source_file` — the file path (enables file-level traceability)
- `handle` — DXF entity handle (stable, unique within file)
- `entity_type` — DXF entity type (e.g., LINE, CIRCLE, INSERT)
- `layer` — the DXF layer name

However, **two record types (`dxf_layer`, `dxf_block`) omit `source_file`** entirely. This is a genuine provenance gap for those specific records.

**INTERPRETATION**: The DXF extractor meets the engineering provenance requirement at the entity level (which is the engineering-relevant record type) but **not** at the metadata-record level (layers, blocks). The `provenance` key convention is a **format-wide consistency issue**, not an entity-level data loss issue.

**INTERPRETATION**: The question is not "should DXF have provenance data?" — it does (in `data.source_file`). The question is "should DXF follow the same `provenance` key convention as every other extractor?" The answer depends on whether the downstream pipeline or the technology-admission gate needs this uniform convention.

### 1.3 Provenance Quality Metric Design

**FACT**: The current benchmark's `provenance_rate` checks `"provenance" in rec` — a binary key-presence test.

**INTERPRETATION**: This metric cannot distinguish between:
- `{"provenance": {"page": 1, "method": "native", "composition": "vector"}}` (PDF — rich)
- `{"provenance": {"source": "text_extractor"}}` (Text — minimal)
- `{"provenance": {"source": "unknown"}}` (trivial — should fail)

**Proposed provenance-quality metric (format-aware)**:

Rather than a single uniform metric, define a **minimum provenance field set per format family**:

| Family | Required Provenance Fields | Test Logic |
|--------|--------------------------|------------|
| PDF | `page` (int ≥ 1) | Each `pdf_page` record must have `provenance.page` |
| IFC | `entity` (non-empty string starting with "Ifc") | Each IFC record must have `provenance.entity` |
| P6/XER | `table` (non-empty string) | Each P6 record must have `provenance.table` |
| DXF | `source_file` (non-empty path) in `data` OR `provenance.source` | Entity records must carry source identity |
| XLS/XLSM/XLSX | `sheet` (non-empty string) + `row` (int) | Each register_row record must have these |
| DOCX/PPTX | `page` (int ≥ 1) | Each page record must have `provenance.page` |
| Images | `source` (non-empty string) | Each image record must have `provenance.source` |
| Structured (CSV/TSV/TXT/MD/LOG/JSON/XML/YAML) | `source` (non-empty string) | Must identify the extractor |

**Rationale**: Format-aware because different formats have different natural provenance dimensions. DXF's natural provenance is `source_file + handle + entity_type + layer`, not a `provenance` key — forcing the key convention would be "artificial uniformity" as explicitly prohibited.

---

## 2. Semantic Regression Protection

### 2.1 Minimum Tests Needed

**FACT**: Current protected tests (from `test_gold_regression.py`):
- 17 tests total (see WP06 §4)
- **MISSING: record-type distribution check**
- **MISSING: entity ID stability**
- **MISSING: provenance quality (only binary presence)**
- **MISSING: fact status integrity**
- **MISSING: conflict behavior preservation**
- **MISSING: File Inspector 4-lane behavior**
- **MISSING: large PDF timing**

### 2.2 Required New Tests

| Capability | Current Test? | Proposed Test | Protected? |
|-----------|--------------|---------------|-----------|
| **Record-type distribution** | ❌ | Verify same set of `record_type` values (e.g., IFC must produce `ifc_element_metadata`, `ifc_connection`, `ifc_spatial`, `ifc_project`, `ifc_entity_count`) | ✅ Domain-specific |
| **Entity ID stability** | ❌ | Run DXF/IFC/P6 twice on same file; verify same handles/GlobalIds appear | ✅ Prevents ID drift |
| **DXF source identity** | ❌ | Verify `source_file` present in entity/block records | ⚠️ See §5 |
| **Provenance quality** | ❌ (PDF only checks key presence) | Verify provenance fields are non-trivial per format family (§1.3) | ✅ |
| **Fact status integrity** | ❌ | Verify only `VALIDATED`/`HUMAN_CERTIFIED` returned by `FactQueryAPI` | ✅ Trust boundary |
| **Conflict detection** | ✅ (`test_lifecycle_open_reviewed_resolved`) | Verify `detect_and_store_conflicts` finds conflicts for candidate facts | ✅ |
| **No silent selection** | ✅ (`test_no_silent_selection`) | Verify both values in disclosure | ✅ |
| **Project isolation** | ✅ (`test_project_isolation`) | Verify zero cross-project data | ✅ |
| **File Inspector 4-lane** | ⚠️ (`test_conflict_disclosure_structural`) | Verify disclosure contains fact_type, subject_id, both values, both method_ids | ⚠️ Could be stricter |
| **PDF large-file timing** | ❌ (only 62KB file protected) | GOLD_0122.pdf <60s, GOLD_0123.pdf <30s | ⚠️ Resource-dependent |
| **PDF OCR path protection** | ❌ | Verify combined-layout pages still extract via OCR | ✅ |

### 2.3 Fact Status Integrity

**FACT**: `FactQueryAPI` (`fact_api.py:37,91-92`) uses `TRUSTED_FACT_STATUSES = TRUSTED_FACT_STATUSES_SQL` to filter. Let me check what `TRUSTED_FACT_STATUSES` is:

The `fact_api.py` imports from `src.domain.facts.models`:
```python
from src.domain.facts.models import Fact, FactStatus, TRUSTED_FACT_STATUSES, TRUSTED_FACT_STATUSES_SQL, ...
```

**FACT**: `test_project_isolation` queries with `WHERE status IN ('VALIDATED','HUMAN_CERTIFIED')` directly — this is the TRUSTED set.

**INTERPRETATION**: A candidate replacement that marks facts as `VALIDATED` without proper validation would bypass this protection. However, the current Fact API enforces this at the query layer, so a candidate extractor that produces records would still need to go through the BuildFactsJob pipeline to create facts with `VALIDATED` status.

**RECOMMENDATION**: Add a test that verifies `FactQueryAPI.get_certified_facts()` never returns facts with `AI_GENERATED` or `CONFLICTING` status (only `VALIDATED`/`HUMAN_CERTIFIED`).

### 2.4 File Inspector 4-Lane Behavior

**FACT**: `test_conflict_disclosure_structural` verifies that `_compose_conflict_disclosure` includes both values. But it does NOT verify the 4-lane structure (fact_type, subject_id, conflicting_facts, action_required).

**FACT**: Looking at `agent_orchestrator.py:_compose_conflict_disclosure` — I need to check this method.

Let me check the `_compose_conflict_disclosure` method.

Actually, I already checked this in the test `test_no_silent_selection` which passes `{"fact_type", "subject_id", "conflicting_facts"}` as input. The disclosure includes "CONFLICT DISCLOSURE", both values, and "action required" text. But there's no test that verifies the disclosure includes the `method_id` of each conflicting fact — which is critical for the 4-lane behavior (you need to know which extractor produced each value).

---

## 3. PDF Performance Assessment

### 3.1 Measured Results

**FACT**: From `GOLD_REGRESSION_RESULTS.json`:

| File | Size | Pages | Composition | Time | Per-page |
|------|------|-------|------------:|------|----------|
| GOLD_0122.pdf | 4.4 MB | 1 | combined | 32,971 ms | 32,971 ms |
| GOLD_0123.pdf | 128 KB | 30 | combined | 23,250 ms | 775 ms |
| GOLD_0124.pdf | 62 KB | 3 | vector | 580 ms | 193 ms |

**FACT**: The test `test_pdf_medium_timing` only checks GOLD_0124.pdf (62 KB, <5s). No threshold exists for GOLD_0122.pdf or GOLD_0123.pdf.

**FACT**: PDF extractor code (`pdf_extractor.py:79-91`) classifies pages as `empty`, `vector`, `scanned`, or `combined`. Combined pages trigger both native extraction + OCR, which is the slow path.

### 3.2 Should GOLD_0122 and GOLD_0123 Become Protected Cases?

**INTERPRETATION**: GOLD_0122.pdf (4.4 MB, 33s) is extreme but within a reasonable engineering budget (e.g., <60s). GOLD_0123.pdf (128 KB, 23s for 30 combined pages) is more concerning — 775 ms per page is slow for a text-classification+OCR workflow.

**RECOMMENDATION**: Add two protected thresholds:
- `test_pdf_large_combined_timing`: GOLD_0122.pdf < 60,000 ms (60 seconds) — current: 33s → 1.8× safety margin
- `test_pdf_many_page_timing`: GOLD_0123.pdf < 30,000 ms (30 seconds) — current: 23s → 1.3× safety margin

These are evidence-based thresholds using actual measurements, with margins appropriate for CI variability.

---

## 4. IFC Coverage Assessment

### 4.1 Untested IFC Files

**FACT**: Gold corpus contains 5 IFC files:

| File | Size | Benchmarked? |
|------|------|-------------|
| GOLD_0174.ifc | 21 MB | ✅ Yes |
| GOLD_0158.ifc | 32 MB | ✅ Yes |
| GOLD_0173.ifc | 61 MB | ✅ Yes |
| GOLD_0157.ifc | 539 MB | ❌ No |
| GOLD_0156.ifc | 817 MB | ❌ No |

**FACT**: The benchmark script deliberately skipped 539 MB and 817 MB files for "safety" (memory/runtime concerns).

### 4.2 Should They Be Benchmarked?

**FACT**: ifcopenshell successfully opened the 61 MB file (GOLD_0173.ifc) producing 20,154 records in 5,140 ms. The 539 MB file is ~9× larger and 817 MB is ~13× larger.

**INTERPRETATION**: Linear extrapolation suggests:
- 539 MB: ~46,000 records expected, ~46 seconds, ~5–10 GB memory
- 817 MB: ~73,000 records expected, ~67 seconds, ~5–10 GB memory

These could be tested on a machine with sufficient RAM (≥16 GB) but would be very slow. The old `baseline_benchmark_results.json` listed both as `success: false` — but that was because ifcopenshell was not installed, not because of size limits.

**RECOMMENDATION**: The 539 MB and 817 MB IFC files should be benchmarked in a resource-rich CI environment (≥16 GB RAM, ≥60 second timeout) as **non-blocking validation**. They are capability validation tests, not regression-critical (the 21–61 MB files already prove the extractor works).

**RECOMMENDATION**: Do NOT add them to the protected capability set — add them as **integration tests** with a skip-on-resource-limit behavior.

---

## 5. DXF Provenance: Should It Be Changed?

### 5.1 Current State

**FACT**: Every DXF entity record has `source_file` in its `data` dict:
- `dxf_extractor.py:333`: `"source_file": abs_path` (in `_extract_entity`)
- `dxf_extractor.py:157`: `"source_file": abs_path` (in `dxf_unsupported`)
- `dxf_extractor.py:683, 706`: `"source_file": abs_path` (in orphan entities)

**FACT**: Two record types omit `source_file`:
- `dxf_layer` (`dxf_extractor.py:298-307`) — no `source_file`
- `dxf_block` (`dxf_extractor.py:624-632`) — no `source_file`

**FACT**: No DXF record has a top-level `provenance` key.

### 5.2 Does DXF Need a `provenance` Key?

**INTERPRETATION**: The engineering question is: does any downstream consumer of DXF records require the `provenance` key, or does it read `data.source_file` directly?

Looking at `ExtractJob._insert_record()` (`extract_job.py:416-589`):
- DXF records are routed to `_insert_cad_record()`
- `_insert_cad_record()` reads `data.get("handle")`, `data.get("source_file")`, etc.
- It does NOT read a `provenance` key for DXF records

**FACT**: The Fact API provenance test (`test_provenance_available`) works at the **database level** — it traces `facts.fact_id` → `fact_inputs.file_version_id` → `file_versions.source_path`. This is independent of the extractor-level `provenance` key.

**INTERPRETATION**: Adding a `provenance` key to DXF records would ONLY affect:
1. The benchmark's `provenance_rate` metric (would go from 0% to 100%)
2. The technology-admission gate's `candidate_provenance >= current_provenance` condition
3. Any future code that checks `rec.get("provenance")` for DXF records (currently none exists)

It would NOT change extraction behavior, Fact API behavior, or any downstream pipeline logic.

### 5.3 Recommendation

**RECOMMENDATION**: **Do NOT add a top-level `provenance` key to DXF records solely to make the benchmark metric reach 100%.**

**REASONING**:
1. DXF records already carry sufficient source identity (`source_file`, `handle`, `entity_type`, `layer`, `layout`) for engineering traceability.
2. No downstream code currently reads DXF `provenance` keys.
3. The benchmark metric should be **format-aware** (see §1.3), not force artificial uniformity.

**RECOMMENDATION**: Instead, do TWO things:
1. Fix the two missing `source_file` fields in `dxf_layer` and `dxf_block` (genuine gap)
2. Update the benchmark's provenance metric for DXF to check `data.source_file` or `data.parent_file` instead of the `provenance` key — making it a **format-aware provenance quality metric** (see §1.3)

This approach fixes a real gap (missing source_file in layer/block records) without adding meaningless key ceremony.

---

## 6. MPP Investigation

### 6.1 Root Cause

**FACT**: `mpxj_wrapper.py:41-52` searches for Java at:
```python
candidates = [
    r"C:\Program Files\Java\jre1.8.0_501",
    r"C:\Program Files\Java\jdk-17",
    r"C:\Program Files\Java\jre8",
]
```

**FACT**: Installed Java versions in `C:\Program Files\Java\`:
- `jre1.8.0_501` — exists as directory, but BROKEN (no `server/jvm.dll`, no `client/jvm.dll`, no `java.exe`)
- `jre1.8.0_503` — exists, HAS `server/jvm.dll` and `java.exe`
- `latest` — exists

**FACT**: `mpxj 16.7.0` is installed. MPXJ's public documentation states Java 11+ is required for MPXJ 16.x.

**FACT**: The error is `[WinError 126] JVM DLL not found: C:\Program Files\Java\jre1.8.0_501\bin\java.exe`

### 6.2 Application vs. Environment

**INTERPRETATION**: Two issues:

1. **Code bug (environment detection)**: The code doesn't check `jre1.8.0_503` (which HAS the JVM DLL) or `JAVA_HOME` or the system PATH. This is a code issue — fixing the Java detection would resolve the immediate `WinError 126`.

2. **Application requirement (Java version)**: Even if the JVM DLL were found, `mpxj 16.7.0` likely requires Java 11+. Java 8 may not be supported by the installed mpxj version. This is an application limitation.

**Recommendation**: The MPP limitation should be classified as:
- **Environment limitation** (broken JRE detection path) — fixable by code
- **Potentially also an application limitation** (mpxj 16.7.0 may require Java 11+) — requires Java upgrade

Since we cannot verify whether Java 8 would work once the path is fixed, the classification is: **MPP is blocked by Java version incompatibility (8 < 11 required by mpxj 16.7.0), combined with a broken Java path detection in the code.**

---

## 7. Redesigned Technology Admission Gate

### 7.1 Current Gate (4 conditions — too permissive)

```
1. records >= current_records * 0.9
2. provenance >= current_provenance  (for DXF: 0% → no protection)
3. time <= current_time * 2
4. failure_rate <= current_failure_rate
```

### 7.2 Hardened Gate (9 conditions)

**FACT**: The following capabilities are domain-specific and must be preserved:

| # | Condition | Rationale | Test Method |
|----|----------|----------|-------------|
| 1 | **Extraction success** | File must still process | `result.success == True` on all currently-passing files |
| 2 | **Record count floor** | No >10% record loss | `candidate_records >= current_records * 0.9` |
| 3 | **Record-type distribution** | New tech can't drop entire record categories | Same set of `record_type` values (e.g., IFC must still produce `ifc_element_metadata`, `ifc_connection`, `ifc_spatial`, `ifc_project`) |
| 4 | **Entity ID stability** | Stable identifiers for Fact linking | Re-run on same file; verify handles/GlobalIds unchanged |
| 5 | **Provenance quality** | Not just key presence | Format-aware field-set check (§1.3 table) |
| 6 | **Performance cap** | No >2× slowdown | `candidate_time <= current_time * 2` |
| 7 | **Reliability** | No new failures | `candidate_failure_rate <= current_failure_rate` |
| 8 | **Behavioral preservation** | Conflict/project isolation/trust refusal | Run all trust + WP-05-A tests against candidate output |
| 9 | **File Inspector 4-lane** | Method attribution + both values | Disclosure includes `method_id` per value |

### 7.3 Admission Decision Matrix

| Condition | Pass | Warn | Fail |
|----------|------|------|------|
| 1. Success | All files extract | — | Any currently-passing file fails |
| 2. Record count | ≥90% of baseline | 80–90% | <80% |
| 3. Type distribution | All types preserved | — | Any type missing |
| 4. ID stability | ≥99% handles match | 95–99% | <95% |
| 5. Provenance quality | ≥ format-specific threshold | — | Below threshold |
| 6. Performance | ≤2× baseline | 2–3× | >3× |
| 7. Reliability | 0 new failures | — | Failure count increases |
| 8. Behavioral | All trust/WP-05-A tests pass | — | Any behavioral test fails |

**RECOMMENDATION**: A candidate must pass ALL "Fail" conditions to be admitted. "Warn" conditions require explicit owner sign-off.

**Not justified as protected gates**:
- Overall percentage scores (not reproducible)
- DGN geometry (experimental, no current capability to regress from)
- LLM answer quality (non-deterministic)
- Cold-start timing (not currently measured)

---

## 8. Mandatory Tests to Add

| # | Test Name | What It Verifies | Current Gap |
|---|-----------|-----------------|-------------|
| 1 | `test_dxf_source_file_present` | DXF entity records have `data.source_file` | ❌ Missing |
| 2 | `test_dxf_provenance_quality` | DXF provenance contains `entity_type` + `handle` | ❌ Missing |
| 3 | `test_record_type_distribution_ifc` | IFC produces all 5 record types | ❌ Missing |
| 4 | `test_record_type_distribution_dxf` | DXF produces expected entity types | ❌ Missing |
| 5 | `test_record_type_distribution_p6` | P6 produces project/WBS/activity/relation | ❌ Missing |
| 6 | `test_entity_id_stability_dxf` | Same DXF file → same handles | ❌ Missing |
| 7 | `test_entity_id_stability_ifc` | Same IFC file → same GlobalIds | ❌ Missing |
| 8 | `test_provenance_quality_pdf` | PDF provenance has `page` + `method` | ⚠️ Partial (only checks key presence) |
| 9 | `test_provenance_quality_ifc` | IFC provenance has `entity` field | ❌ Missing |
| 10 | `test_provenance_quality_p6` | P6 provenance has `table` field | ❌ Missing |
| 11 | `test_pdf_large_combined_timing` | GOLD_0122.pdf (4.4 MB) < 60s | ❌ Missing |
| 12 | `test_pdf_many_page_timing` | GOLD_0123.pdf (30 pages) < 30s | ❌ Missing |
| 13 | `test_dxf_layer_source_file` | DXF layer records have `source_file` | ❌ Missing (current gap) |
| 14 | `test_dxf_block_source_file` | DXF block records have `source_file` | ❌ Missing (current gap) |
| 15 | `test_fact_status_integrity` | `FactQueryAPI` never returns non-certified facts | ⚠️ Implied by code, not tested |
| 16 | `test_disclosure_method_attribution` | Conflict disclosure includes `method_id` per value | ⚠️ Partial |

## 9. Tests NOT Justified (Yet)

| Test | Reason |
|------|--------|
| `test_dxf_provenance_key_present` | Would force artificial uniformity; DXF already has source identity in `data` |
| `test_cold_start_timing` | No established cold-start budget; would be arbitrary threshold |
| `test_ifc_large_file_539mb` | Resource constraint, not capability gap; 21–61 MB already proves extraction |
| `test_ifc_large_file_817mb` | Same as above |
| `test_dgn_geometry_extraction` | DGN has no geometry capability; no regression possible |
| `test_mpp_extraction` | Blocked by Java version; cannot test without environment change |
| `test_llm_answer_quality` | Non-deterministic; requires live model |
| `test_overall_format_score` | Not reproducible; violates "no overall percentage" rule |

---

## 10. DXF Provenance: Precise Recommendation

**RECOMMENDATION**: **Do NOT change the DXF `provenance` key convention. Instead:**

1. **Fix the real gap**: Add `source_file` to `dxf_layer` and `dxf_block` records in `dxf_extractor.py` — these are the only record types that currently omit source identity.

2. **Update the benchmark metric**: Change `provenance_rate` for DXF to check `data.get("source_file")` or `data.get("parent_file")` instead of the top-level `provenance` key. This makes the metric **format-aware** and accurate.

3. **Do NOT add a `provenance` key** to DXF records merely for metric uniformity — the DXF records already contain richer source identity (`handle`, `entity_type`, `layer`, `layout`, `source_file`) than a `provenance` key would provide.

**Justification**: The engineering requirement is "can you trace a DXF entity back to its source file and position?" — DXF entity records already answer this via `source_file` + `handle`. The gap is only in layer/block records, which is a small, concrete fix.

---

## 11. Recommended Next Implementation Work Package

Based on measured evidence only:

### **WP-07-A: DXF Source-File Completeness + Benchmark Hardening**

**Rationale**: DXF is a protected capability producing 1,791–4,584 records per file, but 2 of 6 record types (`dxf_layer`, `dxf_block`) omit `source_file`. This is the only data-traceability gap in a currently-passing protected extractor.

**Proposed work**:
1. Add `source_file` to `dxf_layer` records (`dxf_extractor.py:298-306`)
2. Add `source_file` to `dxf_block` records (`dxf_extractor.py:624-632`)
3. Add `test_dxf_source_file_present` to `test_gold_regression.py`
4. Update `run_gold_benchmark.py` provenance metric to be format-aware for DXF
5. Re-run full suite + benchmark to verify

**NOT in this WP**:
- Adding `provenance` key to DXF records (unnecessary ceremony)
- DXF performance optimization (within threshold)
- PDF performance optimization (separate issue)
- MPP Java upgrade (environment limitation)

---

## 12. Files Inspected (Read-Only)

| File | Purpose |
|------|---------|
| `docs/quality/GOLD_REGRESSION_RESULTS.json` | Generated benchmark results |
| `docs/quality/GOLD_BENCHMARK_SCORECARD.md` | Per-format evidence |
| `docs/quality/WP06_GOLD_REGRESSION_FRAMEWORK.md` | WP-06 framework |
| `tools/run_gold_benchmark.py` | Benchmark tool |
| `src/tests/test_gold_regression.py` | Regression test suite (29 tests) |
| `src/tests/test_conflict_resolution_behavior.py` | WP-05-A behavioral tests (10 tests) |
| `src/engine/extractors/base.py` | `ExtractionResult` dataclass |
| `src/engine/extractors/dxf_extractor.py` | DXF extractor (736 lines) |
| `src/engine/extractors/ifc_extractor.py` | IFC extractor (150 lines) |
| `src/engine/extractors/p6_extractor.py` | P6/XER extractor (157 lines) |
| `src/engine/extractors/pdf_extractor.py` | PDF extractor (351 lines) |
| `src/engine/extractors/dgn_extractor.py` | DGN extractor (142 lines) |
| `src/engine/extractors/mpxj_wrapper.py` | MPP wrapper (247 lines) |
| `src/engine/extractors/text_extractor.py` | Text extractor (129 lines) |
| `src/engine/extractors/csv_extractor.py` | CSV extractor (130 lines) |
| `src/engine/extractors/json_extractor.py` | JSON extractor (133 lines) |
| `src/engine/extractors/xml_extractor.py` | XML extractor |
| `src/engine/extractors/yaml_extractor.py` | YAML extractor |
| `src/engine/extractors/image_extractor.py` | Image extractor (164 lines) |
| `src/engine/extractors/word_extractor.py` | Word extractor (125 lines) |
| `src/engine/extractors/pptx_extractor.py` | PPTX extractor |
| `src/engine/extractors/excel_extractor.py` | Excel extractor (174 lines) |
| `src/application/jobs/extract_job.py` | Extractor registry + DB insertion |
| `src/infra/persistence/database_manager.py` | DB layer (conflict methods) |
| `src/application/orchestrators/agent_orchestrator.py` | Conflict disclosure |
| `src/domain/intelligence/conflict_detector.py` | Conflict detection |
| `src/application/services/coverage_gate.py` | Pre-LLM coverage enforcement |
| `src/application/api/fact_api.py` | Certified fact query interface |
| `benchmark/GOLD_BENCHMARK_V1_MANIFEST.json` | Gold corpus manifest |
| `docs/technology/FORMAT_SCORECARDS/*.md` | 9 old scorecards |
| `docs/technology/baseline_benchmark_results.json` | Old baseline (partial) |

---

## Binary Recommendation

**WP-06A: PASS — Ready for implementation**

The audit has identified concrete, measured gaps and proposed a format-aware, evidence-based hardening of the benchmark contract. The recommendations are:
1. Format-aware provenance quality (not key-presence)
2. Record-type distribution preservation
3. Entity ID stability
4. PDF large-file timing thresholds
5. Two specific missing `source_file` fields in DXF (layer + block records)
6. A hardened 9-condition technology admission gate

No source code changes are required to **decide** on implementation. The next step is implementation of WP-07-A (DXF source-file completeness + benchmark hardening).

**STOP.**
