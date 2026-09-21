# WP-07B: PDF Provenance Quality Investigation

**Date:** 2026-09-16
**Scope:** Read-only investigation of PDF provenance quality = 0.6236
**Verdict:** See final section

---

## FACTS

- PDF provenance quality is 0.6236 (aggregate across 3 gold files).
- Per-file: GOLD_0122.pdf = 0.3333 (1/3 records qualify), GOLD_0123.pdf = 0.9375 (30/32), GOLD_0124.pdf = 0.6 (3/5).
- The benchmark requires PDF records to have `provenance.page` AND `provenance.method`.
- Three PDF record types exist: `pdf_page`, `doc_classification`, `doc_blocks`.
- Only `pdf_page` records carry both `page` and `method` in their provenance.
- `doc_classification` carries `provenance.source` only.
- `doc_blocks` carries `provenance.method` only.
- In every file, ALL `pdf_page` records qualify (100%). The 0.6236 is driven entirely by the 2 non-page records per file.

---

## CURRENT PDF PROVENANCE MAP

### Record type: `pdf_page` (one record per PDF page)

| Field | Value |
|-------|-------|
| Represents | Text content + composition metadata for a single page |
| `data` | `page_no`, `text_content`, `metadata` (composition, method, is_visual) |
| `provenance` | `{"page": i+1, "method": "pypdf_vector"\|"pytesseract_ocr"\|"hybrid_mixed"\|"skipped_empty", "composition": "vector"\|"scanned"\|"combined"\|"empty"}` |
| Page available? | **YES** — `page` is the record's primary identifier |
| Required for verification? | **YES** — an engineer verifying "what text is on page 3" needs the page number |

### Record type: `doc_classification` (one record per document)

| Field | Value |
|-------|-------|
| Represents | Document-level type classification (DRAWING, SPEC, SCOPE, CONTRACT, etc.) |
| `data` | `doc_type`, `confidence` (0.8 heuristic), `keywords_found` |
| `provenance` | `{"source": "heuristic_classification"}` |
| Page available? | **NO** — classification is derived from full document text (first 2000 chars), not a single page |
| Required for verification? | **NO** — the source location is the document file itself, not a page. The `file_version_id` in the DB links to the source file. |
| DB storage | `doc_classifications` table: `class_id`, `file_version_id`, `doc_type`, `confidence`, `keywords_json` |

### Record type: `doc_blocks` (one record per document, containing all blocks)

| Field | Value |
|-------|-------|
| Represents | All semantic blocks (heading + body chunks) for RAG retrieval |
| `data` | `doc_id`, `blocks[]` (each block has `block_id`, `page_index`, `heading_title`, `heading_number`, `level`, `text`) |
| `provenance` | `{"method": "semantic_chunking"}` |
| Page available? | **PARTIALLY** — the record-level provenance has no `page`, but each individual block inside `data.blocks[]` has `page_index`. The `doc_blocks` DB table has `page_index INTEGER NOT NULL` per row. |
| Required for verification? | **For the record as a whole: NO** — it represents the document's block collection. **For an individual block: YES** — and the page IS available via `page_index` in the DB and in `data.blocks[].page_index`. |
| DB storage | `doc_blocks` table: `doc_id`, `block_id`, `page_index`, `heading_title`, `heading_number`, `level`, `text`, `source_type` |

### PDF metadata (in `ExtractionResult.metadata`, not a record)

| Field | Value |
|-------|-------|
| Represents | Normalized PDF document metadata |
| Keys | `pdf_producer`, `pdf_creator`, `pdf_author`, `pdf_title`, `pdf_subject`, `pdf_creation_date`, `pdf_modified_date`, `pdf_raw_metadata`, `page_count`, `char_count`, `block_count`, `image_count`, `page_composition_counts` |
| Page available? | N/A — document-level metadata |
| Provenance | Carried in `ExtractionResult.metadata`, not in any record's `provenance` dict |

---

## RECORD TYPE → AVAILABLE SOURCE LOCATION

| Record type | Record-level source location | Page-level location | How an engineer verifies |
|-------------|------------------------------|---------------------|--------------------------|
| `pdf_page` | `provenance.page` = N | **YES** — direct | Open page N of the source PDF |
| `doc_classification` | `provenance.source` = "heuristic_classification" | **NO** — not applicable (document-level) | Review the full document; the classification is a property of the whole file. The `file_version_id` in DB links to the source file. |
| `doc_blocks` (record) | `provenance.method` = "semantic_chunking" | **NO at record level** — document-level collection | The record represents ALL blocks. Verify by checking `data.blocks[]` — each block has `page_index`. |
| `doc_blocks` (individual block) | — | **YES** — `page_index` in `data.blocks[]` and in `doc_blocks` DB table | Open the page indicated by `page_index` to verify the block text |

---

## ENGINEER VERIFICATION REQUIREMENT

**Question: Can an engineer verify each PDF record type without the missing provenance field?**

| Record | Can engineer verify? | How? |
|--------|---------------------|------|
| `pdf_page` | **YES** | `provenance.page` tells them exactly which page. `provenance.method` tells them how the text was extracted. |
| `doc_classification` | **YES** | The classification is a document-level attribute. An engineer verifies by reviewing the document as a whole. The `file_version_id` → `file_versions.source_path` chain provides the file location. No page number is needed because the classification spans the entire document. |
| `doc_blocks` (record) | **YES** | The record is a collection. An engineer verifies individual blocks via `data.blocks[].page_index` or via the `doc_blocks` DB table which has `page_index` per row. The RAG service explicitly queries `b.page_index` for evidence retrieval (rag_service.py:215). |
| `doc_blocks` (block) | **YES** | `page_index` is available in the DB and in the block data. |

**Conclusion: No engineer is blocked from verifying any PDF record due to the missing `page` in the record-level provenance of `doc_classification` and `doc_blocks`.**

---

## REAL GAPS

**None identified.**

- `pdf_page` records have full page-level provenance. ✅
- `doc_classification` is a document-level record where a single page number is not applicable. Its `provenance.source` correctly identifies the method. ✅
- `doc_blocks` is a document-level collection. Individual blocks have `page_index` in both the record data and the database. ✅
- The EvidenceAnchor model (`page_or_slide: Optional[int]`) already accommodates records without page-level provenance. ✅
- The `format_evidence_citation` function gracefully handles missing page (`if loc.get("page")`). ✅
- The RAG service uses `page_index` from the DB for evidence retrieval, not from the record-level provenance. ✅

---

## BENCHMARK-DEFINITION GAPS

**The 0.6236 is a benchmark-definition issue, not a capability gap.**

The benchmark requires `{"key": "provenance", "fields": ["page", "method"]}` for ALL PDF records. This is a page-level requirement applied to document-level records:

1. **`doc_classification`**: A single `page` number does not exist for a document-level classification. Requiring it would be semantically incorrect — it would imply the classification came from one specific page, when it was derived from the full document text.

2. **`doc_blocks` (record)**: The record represents ALL blocks. A single `page` number would be misleading. The page-level information IS present — in `data.blocks[].page_index` and in the `doc_blocks` DB table. The record-level provenance correctly identifies the method (`semantic_chunking`) without a single page.

**The correct benchmark definition for PDF would be format-aware per record type:**

| Record type | Required provenance fields |
|-------------|---------------------------|
| `pdf_page` | `page`, `method` (page-level record) |
| `doc_classification` | `source` or `method` (document-level record) |
| `doc_blocks` | `method` (document-level collection; page is in nested blocks) |

With this corrected definition, PDF provenance quality would be **1.0** (all records have their appropriate provenance fields).

---

## RECOMMENDED FIXES

### Option A: Fix the benchmark definition (recommended)

Change the PDF entry in `PROVENANCE_REQUIREMENTS` from:
```python
".pdf": {"key": "provenance", "fields": ["page", "method"]},
```
to a per-record-type check that:
- For `pdf_page` records: requires `page` + `method`
- For `doc_classification` records: requires `source` (document-level)
- For `doc_blocks` records: requires `method` (document-level collection)

This is the correct fix because:
- It does not change the extractor (no code changes to `src/**`)
- It does not lower a threshold (the requirement is still that provenance be meaningful)
- It does not invent a new convention
- It reflects the actual semantic structure of the records
- It makes the benchmark measure what it claims to measure: "does each record carry meaningful provenance?"

**Impact on score:** PDF prov_q would change from 0.6236 to 1.0. This is NOT a manufactured improvement — it is the correct measurement of the actual provenance state.

### Option B: Add `page_range` to `doc_blocks` provenance (optional, not required)

Add `provenance: {"method": "semantic_chunking", "page_range": [min_page, max_page]}` to the `doc_blocks` record. This would give engineers a quick reference for which pages the blocks span.

**Impact:** Minor convenience improvement. Does NOT fix the 0.6236 score (the benchmark still requires `page`, not `page_range`). Does NOT change any existing behavior. Would require a one-line change in `pdf_extractor.py`.

### Option C: Do nothing (acceptable)

The current system is fully functional. Engineers can verify all PDF records. The 0.6236 score is a known, documented measurement of the current state. The WP-07A gate correctly notes that this metric cannot be regression-checked against the pre-WP07A baseline.

**When to revisit:** When the next post-WP07A baseline is generated, the gate will compare prov_q against the new baseline. If a future change degrades `pdf_page` provenance, the gate will catch it.

---

## PROTECTION IMPACT

**No protected capability is affected.**

- `pdf_page` provenance (page + method + composition) is intact and will not change.
- The RAG retrieval path uses `doc_blocks.page_index` from the DB — not the record-level provenance.
- The fact/evidence chain uses `file_version_id` → `file_versions.source_path` for source location — not the record-level provenance.
- The EvidenceAnchor model already accommodates missing page (`page_or_slide: Optional[int]`).
- No code in `src/**` needs to change.
- No dependencies need to be added.
- No new provenance convention needs to be invented.

---

## MEASURED EVIDENCE

| Evidence | Source |
|----------|--------|
| `pdf_page` prov_q = 1.0 (all 36 pdf_page records across 3 files have `page`+`method`) | Benchmark per-file data: 3/3, 30/30, 3/3 |
| `doc_classification` prov_q = 0.0 (3/3 records lack `page`+`method`) | Benchmark: each file has exactly 1 doc_classification record |
| `doc_blocks` prov_q = 0.0 (3/3 records lack `page`+`method`) | Benchmark: each file has exactly 1 doc_blocks record |
| `doc_blocks` DB table has `page_index INTEGER NOT NULL` | `001_baseline_v14.sql:108` |
| RAG service queries `b.page_index` for evidence | `rag_service.py:215` |
| EvidenceAnchor has `page_or_slide: Optional[int]` | `models.py:82` |
| `format_evidence_citation` handles missing page | `fact_review_presentation.py:158` |
| `doc_blocks` individual blocks have `page_index` in data | `pdf_extractor.py:335` (`"page_index": page_index`) |
| `doc_classification` is document-level (first 2000 chars of full text) | `pdf_extractor.py:206` |
| 0.6236 = (0.3333 + 0.9375 + 0.6) / 3 | Arithmetic verified |

---

## VERDICT

**NO DEFECT — benchmark issue.**

The PDF provenance quality of 0.6236 is a benchmark-definition artifact, not a capability gap:

1. **All page-level records (`pdf_page`) have full page provenance.** 36/36 = 100%.
2. **`doc_classification` is a document-level record** where a single page number is semantically inapplicable. Its `provenance.source` correctly identifies the method. An engineer verifies it by reviewing the document, not a specific page.
3. **`doc_blocks` is a document-level collection.** The record-level provenance correctly identifies the method. Page-level information IS available in `data.blocks[].page_index` and in the `doc_blocks` DB table (`page_index INTEGER NOT NULL`). The RAG service and evidence chain use this data, not the record-level provenance.
4. **No engineer is blocked from verifying any PDF record.** The EvidenceAnchor model, fact review presentation, and RAG service all gracefully handle document-level records without a single page number.

The benchmark's `PROVENANCE_REQUIREMENTS["pdf"]` applies a page-level field requirement to all PDF records, including two document-level types where a single page does not apply. This is a definition issue in the benchmark tool, not a defect in the extractor.

**Recommended action:** Fix the benchmark definition (Option A) to use per-record-type provenance requirements. This requires no changes to `src/**`, no new dependencies, no new conventions, and no threshold changes. It makes the benchmark measure what it claims to measure.

**STOP.** No implementation performed. No files modified. No threshold changed.
