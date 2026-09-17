#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
run_gold_benchmark.py — WP-06 + WP-07A: Gold corpus extraction benchmark.

Runs each extractor on representative files from the frozen GOLD_BENCHMARK_V1
corpus and collects ACTUAL metrics:
  - extraction success (bool)
  - record count (int)
  - timing (ms, wall clock)
  - provenance coverage (fraction of records with a 'provenance' key)
  - provenance quality (format-aware: meaningful fields present)
  - record types (distribution of record['type'])
  - entity/record ID extraction (for stability checks)
  - diagnostics (list of diagnostic strings)
  - file size (KB), sha256

Outputs: docs/quality/GOLD_REGRESSION_RESULTS.json (machine-readable)

Usage:
    python tools/run_gold_benchmark.py              # Run benchmark
    python tools/run_gold_benchmark.py --compare    # Compare against baseline

This script does NOT modify the gold corpus or any extractor.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CORPUS = ROOT / "_LOCAL_TEST_CORPUS" / "GOLD_BENCHMARK_V1"
OUT_DIR = ROOT / "docs" / "quality"
OUT_PATH = OUT_DIR / "GOLD_REGRESSION_RESULTS.json"
BASELINE_PATH = OUT_DIR / "GOLD_REGRESSION_RESULTS_PRE_WP07A.json"

from src.engine.extractors.base import ExtractionResult


# ── Format-aware provenance quality requirements ──────────────────────────
# Each format family defines what meaningful provenance fields must be present.
# A record scores 1.0 if its provenance contains ALL required fields.
# DXF uses data.source_file as its provenance equivalent (no top-level key).

PROVENANCE_REQUIREMENTS: dict[str, dict] = {
    ".pdf": {
        "key": "provenance",
        "fields": ["page", "method"],
        "per_type": {
            "pdf_page": ["page", "method"],
            "doc_classification": ["source"],
            "doc_blocks": ["method"],
        },
    },
    ".docx":     {"key": "provenance", "fields": ["page", "source"]},
    ".doc":      {"key": "provenance", "fields": ["page", "source"]},
    ".pptx":     {"key": "provenance", "fields": ["page", "source"]},
    ".ppt":      {"key": "provenance", "fields": ["page", "source"]},
    ".xlsx":     {"key": "provenance", "fields": ["sheet", "row"]},
    ".xlsm":     {"key": "provenance", "fields": ["sheet", "row"]},
    ".xls":      {"key": "provenance", "fields": ["sheet", "row"]},
    ".ifc":      {"key": "provenance", "fields": ["entity"]},
    ".xer":      {"key": "provenance", "fields": ["table"]},
    ".dxf":      {"key": "data", "fields": ["source_file"]},
    ".csv":      {"key": "provenance", "fields": ["source"]},
    ".tsv":      {"key": "provenance", "fields": ["source"]},
    ".txt":      {"key": "provenance", "fields": ["source"]},
    ".md":       {"key": "provenance", "fields": ["source"]},
    ".log":      {"key": "provenance", "fields": ["source"]},
    ".json":     {"key": "provenance", "fields": ["source"]},
    ".xml":      {"key": "provenance", "fields": ["source"]},
    ".yaml":     {"key": "provenance", "fields": ["source"]},
    ".yml":      {"key": "provenance", "fields": ["source"]},
}

# Entity/record ID field per format (for stability checks)
ENTITY_ID_FIELD: dict[str, dict] = {
    ".dxf":   {"key": "data", "field": "handle"},
    ".ifc":   {"key": "data", "field": "ElementId"},
    ".xer":   {"key": "data", "field": "task_id"},
    ".xlsx":  {"key": "data", "field": "row_index"},
    ".xlsm":  {"key": "data", "field": "row_index"},
    ".xls":   {"key": "data", "field": "row_index"},
}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _file_size_kb(path: Path) -> float:
    return round(path.stat().st_size / 1024.0, 1)


def _provenance_rate(records: list) -> float:
    """Binary key-presence rate (original metric)."""
    if not records:
        return 0.0
    has_key = sum(1 for r in records if isinstance(r, dict) and "provenance" in r)
    return round(has_key / len(records), 4)


def _provenance_quality_rate(records: list, ext: str) -> float:
    """Format-aware provenance quality.

    For DXF: checks data.source_file (no top-level provenance key by design).
    For all others: checks provenance key has all required fields.
    When per_type requirements are defined, uses the record's type to select
    the appropriate field set (e.g., PDF doc_classification needs source,
    not page+method).
    """
    if not records:
        return 0.0
    req = PROVENANCE_REQUIREMENTS.get(ext)
    if not req:
        return 1.0 if _provenance_rate(records) > 0 else 0.0
    key = req["key"]
    default_fields = req["fields"]
    per_type = req.get("per_type", {})
    qualified = 0
    for r in records:
        if not isinstance(r, dict):
            continue
        # Select field set: per-type override if available, else default
        rtype = r.get("type", "")
        fields = per_type.get(rtype, default_fields)
        if key == "data":
            data = r.get("data", {})
            if not isinstance(data, dict):
                continue
            if all(f in data and data[f] for f in fields):
                qualified += 1
        elif key == "provenance":
            prov = r.get("provenance")
            if not isinstance(prov, dict):
                continue
            if all(f in prov and prov[f] is not None for f in fields):
                qualified += 1
    return round(qualified / len(records), 4)


def _type_distribution(records: list) -> dict:
    types = Counter()
    for r in records:
        t = r.get("type", "unknown") if isinstance(r, dict) else "unknown"
        types[t] += 1
    return dict(types.most_common())


def _entity_ids(records: list, ext: str) -> list:
    """Extract entity/record identifiers for stability checking."""
    spec = ENTITY_ID_FIELD.get(ext)
    if not spec:
        return []
    ids = []
    key = spec["key"]
    field = spec["field"]
    for r in records:
        if not isinstance(r, dict):
            continue
        container = r.get(key, {})
        if not isinstance(container, dict):
            continue
        val = container.get(field)
        if val:
            ids.append(val)
    return ids


def _safe_import(modpath: str, classname: str = ""):
    """Import an extractor class from 'module:Class' string."""
    module_path, class_name = modpath.split(":")
    try:
        module = __import__(module_path, fromlist=[class_name])
        return getattr(module, class_name), None
    except ImportError as e:
        return None, str(e)
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


EXTRACTOR_DISPATCH: dict[str, str] = {
    ".pdf":  "src.engine.extractors.pdf_extractor:UniversalPdfExtractor",
    ".docx": "src.engine.extractors.word_extractor:WordExtractor",
    ".doc":  "src.engine.extractors.word_extractor:WordExtractor",
    ".pptx": "src.engine.extractors.pptx_extractor:PPTXExtractor",
    ".ppt":  "src.engine.extractors.pptx_extractor:PPTXExtractor",
    ".xlsx": "src.engine.extractors.excel_extractor:ExcelExtractor",
    ".xlsm": "src.engine.extractors.excel_extractor:ExcelExtractor",
    ".xls":  "src.engine.extractors.excel_extractor:ExcelExtractor",
    ".csv":  "src.engine.extractors.csv_extractor:CsvExtractor",
    ".tsv":  "src.engine.extractors.csv_extractor:CsvExtractor",
    ".txt":  "src.engine.extractors.text_extractor:TextExtractor",
    ".md":   "src.engine.extractors.text_extractor:TextExtractor",
    ".log":  "src.engine.extractors.text_extractor:TextExtractor",
    ".json": "src.engine.extractors.json_extractor:JsonExtractor",
    ".xml":  "src.engine.extractors.xml_extractor:XmlExtractor",
    ".yaml": "src.engine.extractors.yaml_extractor:YamlExtractor",
    ".yml":  "src.engine.extractors.yaml_extractor:YamlExtractor",
    ".ifc":  "src.engine.extractors.ifc_extractor:IFCExtractor",
    ".dxf":  "src.engine.extractors.dxf_extractor:DXFExtractor",
    ".xer":  "src.engine.extractors.p6_extractor:P6Extractor",
    ".mpp":  "src.engine.extractors.mpxj_wrapper:MPXJWrapper",
    ".dgn":  "src.engine.extractors.dgn_extractor:DGNExtractor",
}

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}
IMAGE_EXTRACTOR = "src.engine.extractors.image_extractor:ImageExtractor"

NO_EXTRACTOR = {
    ".dwg":  "No open-source DWG extractor exists (proprietary Autodesk format)",
    ".rvt":  "No open-source RVT extractor exists (proprietary Revit format)",
}

# Expected record types per format (for type-preservation checks)
EXPECTED_TYPES: dict[str, set] = {
    ".dxf": {"dxf_drawing", "dxf_layer", "dxf_block", "dxf_viewport", "dxf_text", "dxf_insert"},
    ".ifc": {"ifc_project", "ifc_spatial", "ifc_element_metadata", "ifc_connection", "ifc_entity_count"},
    ".xer": {"p6_project", "p6_wbs", "p6_activity", "p6_relation"},
    ".pdf": {"pdf_page", "doc_classification", "doc_blocks"},
    ".xlsx": {"register_row"},
    ".xls": {"register_row"},
    ".xlsm": {"register_row"},
}


def run_one(extractor_cls, file_path: Path, ext: str = "") -> dict:
    """Run an extractor on a single file; return metric dict with hardened metrics."""
    entry = {
        "file": file_path.name,
        "file_path": str(file_path.relative_to(CORPUS)),
        "file_size_kb": _file_size_kb(file_path),
        "sha256": _sha256(file_path),
        "extension": ext or file_path.suffix.lower(),
    }
    try:
        extractor = extractor_cls()
        # Run twice for entity ID stability check
        result1 = extractor.extract(str(file_path))
        result2 = extractor.extract(str(file_path))
        t0 = time.perf_counter()
        result = extractor.extract(str(file_path))
        t1 = time.perf_counter()

        entry["timing_ms"] = round((t1 - t0) * 1000, 1)
        entry["success"] = bool(result.success)
        entry["record_count"] = len(result.records) if result.records else 0
        entry["provenance_rate"] = _provenance_rate(result.records) if result.records else 0.0
        entry["provenance_quality_rate"] = _provenance_quality_rate(result.records, ext or file_path.suffix.lower()) if result.records else 0.0
        entry["type_distribution"] = _type_distribution(result.records) if result.records else {}
        entry["diagnostics"] = result.diagnostics if result.diagnostics else []
        entry["metadata_keys"] = list(result.metadata.keys()) if result.metadata else []

        # Entity ID stability (only for formats with ID field)
        ext_key = ext or file_path.suffix.lower()
        if ext_key in ENTITY_ID_FIELD and result.records:
            ids1 = set(_entity_ids(result1.records, ext_key))
            ids2 = set(_entity_ids(result2.records, ext_key))
            if ids1:
                entry["entity_id_stability"] = round(len(ids1 & ids2) / max(len(ids1), 1), 4)
                entry["entity_id_count"] = len(ids1)
            else:
                entry["entity_id_stability"] = 1.0
                entry["entity_id_count"] = 0
        else:
            entry["entity_id_stability"] = 1.0
            entry["entity_id_count"] = 0

        # Type preservation flag
        if ext_key in EXPECTED_TYPES and result.records:
            actual_types = set(entry["type_distribution"].keys())
            entry["types_preserved"] = EXPECTED_TYPES[ext_key].issubset(actual_types)
        else:
            entry["types_preserved"] = True

    except ImportError as e:
        entry["success"] = False
        entry["record_count"] = 0
        entry["timing_ms"] = 0
        entry["provenance_rate"] = 0.0
        entry["provenance_quality_rate"] = 0.0
        entry["type_distribution"] = {}
        entry["diagnostics"] = [f"ImportError: {e}"]
        entry["metadata_keys"] = []
        entry["entity_id_stability"] = 1.0
        entry["entity_id_count"] = 0
        entry["types_preserved"] = True
    except Exception as e:
        entry["success"] = False
        entry["record_count"] = 0
        entry["timing_ms"] = 0
        entry["provenance_rate"] = 0.0
        entry["provenance_quality_rate"] = 0.0
        entry["type_distribution"] = {}
        entry["diagnostics"] = [f"{type(e).__name__}: {e}"]
        entry["metadata_keys"] = []
        entry["entity_id_stability"] = 1.0
        entry["entity_id_count"] = 0
        entry["types_preserved"] = True
    return entry


def compare_baseline(baseline: dict, current: dict) -> dict:
    """Compare current results against baseline using the hardened admission gate.

    Returns a dict of format -> {passed: bool, issues: list[str], notes: list[str], details: dict}
    """
    results = {}
    baseline_summary = baseline.get("summary", {})
    current_summary = current.get("summary", {})

    for ext in sorted(set(baseline_summary.keys()) | set(current_summary.keys())):
        b = baseline_summary.get(ext, {})
        c = current_summary.get(ext, {})
        issues = []
        notes = []

        if b.get("status") == "UNAVAILABLE" and c.get("status") == "UNAVAILABLE":
            results[ext] = {"passed": True, "issues": [], "notes": [], "details": {"status": "UNAVAILABLE (skipped)"}}
            continue

        # Pre-existing failures: if baseline also failed the same files, do not
        # flag as a regression. Only NEW failures (condition 7) are gate failures.
        b_fail = b.get("failed", 0)
        c_fail = c.get("failed", 0)
        if c.get("status") == "FAIL" and b_fail == c_fail and b_fail > 0:
            notes.append(f"Pre-existing failure ({c_fail}/{c.get('files_tested', 0)} files) — same in baseline")

        # Condition 1: Extraction success
        if b.get("successful", 0) > 0 and c.get("successful", 0) < b.get("successful", 0):
            issues.append(f"Extraction success regressed: {b.get('successful')} → {c.get('successful')}")

        # Condition 2: Record count floor (≥90% of baseline)
        # <90% = gate failure; 90–99% = informational note (not a failure); 100% = pass
        b_total = b.get("total_records", 0)
        c_total = c.get("total_records", 0)
        if b_total > 0:
            ratio = c_total / b_total
            if ratio < 0.9:
                issues.append(f"Record count below 90%: {c_total} vs {b_total} ({ratio:.1%})")
            elif ratio < 1.0:
                notes.append(f"Record count degraded (within tolerance): {c_total} vs {b_total} ({ratio:.1%})")

        # Condition 3: Record type preservation
        b_types = _get_type_set(baseline, ext)
        c_types = _get_type_set(current, ext)
        if b_types and c_types:
            missing = b_types - c_types
            if missing:
                issues.append(f"Record types lost: {missing}")

        # Condition 4: Entity ID stability
        b_stab = b.get("avg_entity_id_stability", 1.0)
        c_stab = c.get("avg_entity_id_stability", 1.0)
        if c_stab < 0.99:
            issues.append(f"Entity ID stability degraded: {c_stab}")

        # Condition 5: Provenance quality (format-aware)
        # Never silently skip. When the baseline predates the metric, check an
        # absolute floor and flag the missing baseline explicitly.
        b_q = b.get("avg_provenance_quality_rate")
        c_q = c.get("avg_provenance_quality_rate")
        if b_q is not None and c_q is not None:
            if c.get("successful", 0) > 0 and c_q < b_q:
                issues.append(f"Provenance quality regressed: {c_q} < {b_q}")
        elif c_q is not None and b_q is None:
            # Baseline predates this metric (pre-WP07A): do NOT fabricate a
            # baseline value. Verify an absolute floor instead: any format
            # with successful extractions must have quality > 0.
            if c.get("successful", 0) > 0 and c_q == 0.0:
                issues.append(f"Provenance quality is 0.0 for successful extraction (baseline lacks metric)")
            notes.append(f"Provenance quality ({c_q}) cannot be regression-checked: baseline predates this metric. Re-baseline recommended.")

        # Condition 6: Performance (≤2× baseline)
        b_time = b.get("avg_timing_ms", 0)
        c_time = c.get("avg_timing_ms", 0)
        if b_time > 0 and c_time > b_time * 2:
            issues.append(f"Performance degraded >2×: {c_time}ms vs {b_time}ms")

        # Condition 7: Reliability (failure rate)
        b_total_files = b.get("files_tested", 0)
        if b_total_files > 0 and b_fail == 0 and c_fail > 0:
            issues.append(f"New failures introduced: {c_fail} failed files")

        results[ext] = {
            "passed": len(issues) == 0,
            "issues": issues,
            "notes": notes,
            "details": {
                "baseline_records": b_total,
                "candidate_records": c_total,
                "baseline_time_ms": b_time,
                "candidate_time_ms": c_time,
                "baseline_provenance": b_q,
                "candidate_provenance": c_q,
                "baseline_entity_stability": b_stab,
                "candidate_entity_stability": c_stab,
            },
        }

    return results


def _get_type_set(data: dict, ext: str) -> set:
    """Extract the set of record types from per_format data."""
    types = set()
    for r in data.get("per_format", {}).get(ext, []):
        types.update(r.get("type_distribution", {}).keys())
    return types


def _build_output(all_results, by_ext) -> dict:
    """Build the full output dict from benchmark results (used by both modes)."""
    summary = {}
    for ext, results in all_results.items():
        total = len(results)
        successful = sum(1 for r in results if r["success"])
        total_records = sum(r["record_count"] for r in results if r["success"])
        successful_times = [r["timing_ms"] for r in results if r["success"] and r["timing_ms"] > 0]
        avg_time = round(sum(successful_times) / max(len(successful_times), 1), 1)
        successful_provs = [r["provenance_rate"] for r in results if r["success"]]
        avg_prov = round(sum(successful_provs) / max(len(successful_provs), 1), 4)
        successful_qprovs = [r["provenance_quality_rate"] for r in results if r["success"]]
        avg_qprov = round(sum(successful_qprovs) / max(len(successful_qprovs), 1), 4)
        avg_stab = round(sum(r["entity_id_stability"] for r in results) / max(total, 1), 4)
        types_preserved = all(r["types_preserved"] for r in results)

        summary[ext] = {
            "files_tested": total,
            "successful": successful,
            "failed": total - successful,
            "total_records": total_records,
            "avg_timing_ms": avg_time,
            "avg_provenance_rate": avg_prov,
            "avg_provenance_quality_rate": avg_qprov,
            "avg_entity_id_stability": avg_stab,
            "types_preserved": types_preserved,
            "status": "PASS" if successful == total else ("WARN" if successful > 0 else "FAIL"),
        }

    for ext, reason in by_ext.get("_skipped", {}).items():
        summary[ext] = {
            "files_tested": len(by_ext.get(ext, [])),
            "successful": 0,
            "failed": 0,
            "total_records": 0,
            "avg_timing_ms": 0,
            "avg_provenance_rate": 0,
            "avg_provenance_quality_rate": 0,
            "avg_entity_id_stability": 1.0,
            "types_preserved": True,
            "status": "UNAVAILABLE",
            "reason": reason,
        }

    return {
        "benchmark_name": "GOLD_REGRESSION_BENCHMARK_V1",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "corpus_path": str(CORPUS.resolve()),
        "corpus_total_files": len([f for f in CORPUS.iterdir() if f.is_file()]),
        "corpus_extensions": len(by_ext) - 1,
        "python_version": sys.version.split()[0],
        "summary": summary,
        "per_format": all_results,
        "technology_admission_gate": {
            "conditions": [
                "1. Extraction success preserved",
                "2. Record count ≥ 90% of baseline",
                "3. Record types preserved",
                "4. Entity ID stability ≥ 99%",
                "5. Provenance quality ≥ baseline (format-aware)",
                "6. Timing ≤ 2× baseline",
                "7. No new failures introduced",
            ],
            "baseline_file": str(BASELINE_PATH),
        },
    }


def main():
    compare_mode = "--compare" in sys.argv

    if compare_mode:
        if not BASELINE_PATH.exists():
            print(f"ERROR: Baseline file not found: {BASELINE_PATH}")
            print("Run without --compare first to generate a baseline.")
            sys.exit(1)

        with open(BASELINE_PATH) as f:
            baseline = json.load(f)
        all_results, by_ext = _run_benchmark()
        current = _build_output(all_results, by_ext)
        comparison = compare_baseline(baseline, current)

        print("\n=== TECHNOLOGY ADMISSION GATE RESULTS ===")
        all_passed = True
        for ext, result in sorted(comparison.items()):
            status = "PASS" if result["passed"] else "FAIL"
            if not result["passed"]:
                all_passed = False
            print(f"  {ext:12s}: {status}")
            for issue in result["issues"]:
                print(f"    ⚠ {issue}")
            for note in result.get("notes", []):
                print(f"    [note] {note}")
        print(f"\nOverall: {'ALL CONDITIONS PASS' if all_passed else 'REGRESSION DETECTED'}")
        return

    # Normal benchmark mode
    if not CORPUS.is_dir():
        print(f"ERROR: Gold corpus not found: {CORPUS}")
        sys.exit(1)

    all_results, by_ext = _run_benchmark()
    output = _build_output(all_results, by_ext)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nResults written to: {OUT_PATH}")
    print("\n=== SUMMARY ===")
    for ext, s in sorted(output["summary"].items()):
        if s.get("status") == "UNAVAILABLE":
            print(f"  {ext:12s}: UNAVAILABLE — {s['reason']}")
        else:
            print(f"  {ext:12s}: {s['successful']}/{s['files_tested']} files, "
                  f"{s['total_records']} records, avg {s['avg_timing_ms']}ms, "
                  f"prov_key={s['avg_provenance_rate']} prov_q={s['avg_provenance_quality_rate']} "
                  f"id_stab={s['avg_entity_id_stability']} types_ok={s['types_preserved']} [{s['status']}]")


def _run_benchmark() -> tuple:
    """Core benchmark logic — returns (all_results, by_ext_with_skipped)."""
    all_files = sorted(CORPUS.iterdir(), key=lambda p: p.name)
    by_ext: dict[str, list[Path]] = {}
    skipped: dict[str, str] = {}
    for f in all_files:
        if not f.is_file():
            continue
        ext = f.suffix.lower()
        by_ext.setdefault(ext, []).append(f)

    print(f"Gold corpus: {len(all_files)} files, {len(by_ext)} extensions")
    print()

    all_results: dict[str, list[dict]] = {}

    for ext in sorted(by_ext.keys()):
        files = by_ext[ext]

        if ext in NO_EXTRACTOR:
            skipped[ext] = NO_EXTRACTOR[ext]
            print(f"=== {ext} — SKIPPED (no extractor) ===")
            continue

        if ext in IMAGE_EXTS:
            continue

        if ext == ".ifc":
            small = sorted(files, key=lambda f: f.stat().st_size)
            files = small[:3]

        if ext == ".xls":
            files = files[:2]

        files = files[:3]

        modpath = EXTRACTOR_DISPATCH.get(ext)
        if not modpath:
            skipped[ext] = "No registered extractor"
            continue

        cls, err = _safe_import(modpath, "")
        if err:
            print(f"=== {ext} — IMPORT ERROR: {err} ===")
            results = []
            for f in files:
                r = run_one(type("Dummy", (), {
                    "extract": lambda self, p, context=None: (_ for _ in ()).throw(ImportError(err))
                }), f, ext)
                r["extractor"] = ext.lstrip(".")
                r["extractor_error"] = err
                results.append(r)
            all_results[ext] = results
            continue

        label = ext.lstrip(".")
        print(f"=== {ext} ({len(files)} files) — {cls.__name__} ===")
        results = []
        for f in files:
            r = run_one(cls, f, ext)
            r["extractor"] = label
            r["extractor_version"] = "1.0.0"
            results.append(r)
            status = "OK" if r["success"] else "FAIL"
            print(f"  {r['file']}: {status} recs={r['record_count']} time={r['timing_ms']}ms "
                  f"prov_k={r['provenance_rate']} prov_q={r['provenance_quality_rate']} "
                  f"types_ok={r['types_preserved']} id_stab={r['entity_id_stability']}")
        all_results[ext] = results
        print()

    # Images
    image_files_by_ext: dict[str, list[Path]] = {}
    for ext in IMAGE_EXTS:
        if ext in by_ext:
            for f in sorted(by_ext[ext], key=lambda p: p.stat().st_size):
                image_files_by_ext.setdefault(ext, []).append(f)
    image_files = []
    for ext, files in sorted(image_files_by_ext.items()):
        image_files.extend(files[:2])

    if image_files:
        cls, err = _safe_import(IMAGE_EXTRACTOR, "")
        if err:
            print(f"=== Images — IMPORT ERROR: {err} ===")
            for f in image_files:
                r = {
                    "file": f.name,
                    "file_path": str(f.relative_to(CORPUS)),
                    "extension": f.suffix.lower(),
                    "extractor": "image",
                    "file_size_kb": _file_size_kb(f),
                    "sha256": _sha256(f),
                    "success": False, "record_count": 0, "timing_ms": 0,
                    "provenance_rate": 0.0, "provenance_quality_rate": 0.0,
                    "type_distribution": {}, "diagnostics": [f"ImportError: {err}"],
                    "entity_id_stability": 1.0, "entity_id_count": 0, "types_preserved": True,
                }
                all_results.setdefault(".image", []).append(r)
                print(f"  {r['file']}: FAIL (import error)")
        else:
            print(f"=== Images ({len(image_files)} files) — {cls.__name__} ===")
            results = []
            for f in image_files:
                r = run_one(cls, f, f.suffix.lower())
                r["extractor"] = "image"
                r["extractor_version"] = "1.0.0"
                results.append(r)
                status = "OK" if r["success"] else "FAIL"
                print(f"  {r['file']}: {status} recs={r['record_count']} time={r['timing_ms']}ms "
                      f"prov_q={r['provenance_quality_rate']}")
            all_results[".image"] = results
        print()

    by_ext["_skipped"] = skipped
    return all_results, by_ext


if __name__ == "__main__":
    main()
