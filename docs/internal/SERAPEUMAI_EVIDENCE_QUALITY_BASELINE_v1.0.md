# SerapeumAI Evidence Quality Baseline v1.0

**Date:** 2026-09-02  
**Task:** TASK-009 — Wave A Evidence Quality Baseline  
**Scope:** Read-only investigation of current evidence/extraction reality  
**Status:** BASELINE — No implementation, no fixes  

---

## 1. Executive Summary

The extraction layer consists of **9 registered extractors** (V02 `BaseExtractor` contract) plus **10 document processors** (V01 `document_processing` layer). Both layers feed into the same `_insert_record()` persistence pipeline via `ExtractJob`. 

**Total extraction-related tests: 43 across 11 test files.** Of 744 total tests, this represents ~5.8% of the suite.

**Overall quality assessment: PARTIALLY FUNCTIONAL** — strong domains (PDF, P6, IFC) coexist with significant gaps (Images, DXF/DWG, Field/VLM, Classifier).

---

## 2. Supported File Types & Current Capability

### 2.1 Registered Extractors (V02 Engine Layer)

| Extractor | ID | Extensions | Tests | Status |
|---|---|---|---|---|
| `UniversalPdfExtractor` | `universal-pdf-extractor-v1` | `.pdf` | 14 | ✅ **Strong** |
| `P6Extractor` | `p6-extractor-standard` | `.xer` | 8 | ✅ **Strong** |
| `IFCExtractor` | `ifc-extractor-v1` | `.ifc` | 5 | ⚠️ **Partial** (depends on optional `ifcopenshell`) |
| `ExcelRegisterExtractor` | `excel-register-extractor-v1` | `.xlsx`, `.xls` | 1 | ❌ **Weak** (hygiene-only test) |
| `WordExtractor` | `word-extractor-v1` | `.doc`, `.docx` | 1 (contract) | ⚠️ **Flattened only** |
| `PPTXExtractor` | `pptx-extractor-v1` | `.pptx` | 1 (contract) | ⚠️ **Flattened only** |
| `DGNExtractor` | `dgn-extractor-v1` | `.dgn` | 3 (integration) | ⚠️ **Metadata only** |
| `FieldExtractor` | `field-extractor-v1` | `.pdf`, `.jpg`, `.png` | 0 | 🚨 **Mocked/stub** |
| *(No extractor)* | — | `.dxf`, `.dwg` | 0 | 🚨 **Missing** |
| *(No extractor)* | — | `.tiff`, `.bmp`, `.gif` | 0 | 🚨 **Missing** |

### 2.2 Document Processors (V01 Layer)

| Processor | Tests | Status |
|---|---|---|
| `PdfProcessor` | (covered by V02 PDF tests) | ✅ Strong |
| `WordProcessor` | (covered by contract test) | ⚠️ Flattened |
| `PptProcessor` | (covered by contract test) | ⚠️ Flattened |
| `DgnProcessor` | 3 integration tests | ⚠️ Metadata only |
| `ExcelProcessor` | 1 hygiene test | ❌ Weak |
| `ImageProcessor` | **0** | 🚨 **Untested** |
| `CADProcessor` | **0** | 🚨 **Untested** (uses `ezdxf`) |
| `DocumentClassifier` | **0** | 🚨 **Stub** — always returns `"unknown"` |

---

## 3. Evidence Source Map

### 3.1 Record Types Produced

| Source | Record Types | Target Tables | Deterministic? |
|---|---|---|---|
| PDF extractor | `pdf_page`, `doc_classification`, `doc_blocks` | `pdf_pages`, `doc_classifications`, `doc_blocks`, `pages` | ✅ Yes |
| P6 extractor | `p6_project`, `p6_wbs`, `p6_activity`, `p6_relation` | `p6_projects`, `p6_wbs`, `p6_activities`, `p6_relations` | ✅ Yes |
| IFC extractor | `ifc_project`, `ifc_spatial`, `ifc_element_metadata`, `ifc_connection` | `ifc_projects`, `ifc_spatial_structure`, `ifc_elements`, `links` | ✅ Yes (when ifcopenshell present) |
| Excel register | `register_row` | `register_rows` | ✅ Yes |
| Word/PPTX/DGN | `pdf_page` (flattened) | `pages` | ✅ Yes (text-only, structural) |
| Field extractor | `field_request` | `field_requests` | ❌ **MOCK DATA** (`vlm_mock`) |
| Image processor | `page` record with `ocr_text`, `image_path` | `pages` | ✅ Yes (Tesseract OCR) |
| CAD processor | `cad_entity` records | — (not persisted to typed table) | ⚠️ Partial (ezdxf entity listing) |

### 3.2 Extraction Entry Points

```
ExtractJob.run()
├── Resolves file_version_id → source_path from DB
├── Looks up extractor from EXTRACTORS registry
│   ├── p6, ifc, excel_register, pdf, field, word, pptx, dgn
├── Calls extractor.extract(file_path, context)
├── Persists records via _insert_record(db, rec, doc_id)
└── Triggers downstream jobs:
    ├── BuildFactsJob (p6→schedule, ifc→bim, excel→register, field→completion)
    ├── BuildFactsJob (pdf→document, priority=60)
    └── AnalyzeDocJob (pdf only)
```

---

## 4. Known Gaps

### 4.1 Missing Coverage (No Tests)

| Area | Gap | Risk |
|---|---|---|
| **DXF/DWG** | No V02 extractor; CADProcessor exists but untested | DXF files cannot enter evidence pipeline via standard path |
| **DWG** | No support at all | AutoCAD files produce no evidence |
| **Field/VLM** | `FieldExtractor` returns mock data, has `TODO` for real VLM | Any "IR" or "NCR" extraction is fabricated, not grounded |
| **Images** | `ImageProcessor` exists but zero tests | OCR on images is unverified; no quality checks |
| **Classifier** | `DocumentClassifier.classify()` always returns `"unknown"` | Document type classification is non-functional |
| **PPTX** | Only 1 contract test (no behavior tests) | Slide content extraction correctness unknown |
| **Word** | Only 1 contract test (no behavior tests) | Table/text extraction correctness unknown |
| **Register** | Only 1 hygiene test (debug path check) | Header detection, row mapping, quality unknown |

### 4.2 Placeholder/Stub Implementations

| File | Issue | Evidence |
|---|---|---|
| `src/engine/extractors/field_extractor.py:36-78` | Mock VLM output based on filename markers | `# MOCK VLM OUTPUT based on filename/content markers` |
| `src/document_processing/classifier.py:5` | Always returns `"unknown"` | `def classify(self, filename): return "unknown"` |
| `src/engine/extractors/pdf_extractor.py:286` | Empty keyword extraction | `def _get_keywords(self, text: str) -> List[str]: return []` |
| `src/engine/extractors/pdf_extractor.py:118` | Hardcoded confidence for doc classification | `"confidence": 0.8, # Heuristic` |

### 4.3 Weak Validation

| Domain | Gap | Impact |
|---|---|---|
| **PDF composition sniffing** | Thresholds hardcoded: text >300 = vector, text <100 + images >0 = scanned | Pages with 100-300 chars + few images fall into ambiguous "combined" or default "vector" buckets |
| **PDF semantic blocks** | Blocks <50 chars skipped; page assignment uses first 100 chars heuristic match | Short but meaningful blocks dropped; block-to-page mapping unreliable |
| **P6 float parsing** | `try/except` silently converts bad float to `None` → loses error signal | Bad XER data silently becomes no-float rather than flagged |
| **Excel header detection** | Keyword scoring with arbitrary weights; avg-length penalty | False headers likely on files without AECO keywords |
| **IFC extraction** | No test with real .ifc file; fake-entity tests only | Real-world IFC edge cases unverified |

### 4.4 Unsupported Claims vs Reality

| Claim (from code/docs) | Reality |
|---|---|
| "Supports PDF, DXF/DWG, IFC, XER/P6, Office, Images" | DXF and DWG have **no extractor**; only CADProcessor which lists entities without typing them |
| "FieldExtractor uses VLM" | Returns **mock data** based on filename string matching (`"IR" in file_path`) |
| "Document classification" | Returns `GENERAL_DOC` for everything; `DocumentClassifier` always returns `"unknown"` |
| "CAD/BIM Processing: Exists" (Current Reality Report §3.3) | BIM (IFC) exists but requires optional dep; CAD (DXF/DWG) is absent from V02 extractors |

---

## 5. Risk Assessment

| Risk | Level | Description |
|---|---|---|
| **Fabricated field evidence** | 🔴 **HIGH** | `FieldExtractor` produces mock IR/NCR records. If used in chat, answers would reference non-existent inspections. |
| **Undetected DXF/DWG absence** | 🟡 **MEDIUM** | Files silently fail or bypass extraction; user sees no evidence from CAD drawings. |
| **Image OCR unverified** | 🟡 **MEDIUM** | No tests; could silently produce empty or garbage text. |
| **Weak PDF routing thresholds** | 🟢 **LOW** | Correct for typical AECO PDFs; edge cases may misroute pages. |
| **Excel header detection false positives** | 🟢 **LOW** | Works for standard registers; unusual column layouts may misidentify headers. |
| **P6 float silence on errors** | 🟡 **MEDIUM** | Missing float values silently treated as "no criticality info" rather than flagged. |

---

## 6. Test Coverage Matrix

| Domain | Unit Tests | Contract Tests | Integration Tests | Total | Grade |
|---|---|---|---|---|---|
| **PDF** | 6 | 8 | — | 14 | A |
| **P6/XER** | 4 | 4 | — | 8 | A |
| **IFC** | 2 | 3 | — | 5 | B |
| **Office (W/P/D)** | — | 6 | — | 6 | C |
| **Excel Register** | — | 1 (hygiene) | — | 1 | D |
| **DGN/CAD** | — | — | 3 | 3 | D |
| **Field/VLM** | — | — | — | 0 | F |
| **Images** | — | — | — | 0 | F |
| **DXF/DWG** | — | — | — | 0 | F |

**Summary:** 43 extraction tests total. 3 of 10 supported types have **zero test coverage**. 1 extractor produces **mock data**.

---

## 7. Required Acceptance Criteria

For each domain, acceptance criteria should define:

### 7.1 Minimum Test Requirements Per Domain

| Criterion | Required |
|---|---|
| **Input contract** | Extractor accepts only declared extensions; rejects unsupported types |
| **Deterministic output** | Same input file → identical records (hash-stable) |
| **Empty/degenerate input** | Corrupted or empty file returns `success=False` with diagnostic, not crash |
| **Persistence contract** | All record types inserted into correct DB tables with required columns |
| **Provenance fields** | Every record includes `provenance` dict with source identifier |
| **Optional dependency** | Missing optional dep → `success=False` + diagnostic mentioning dep name; no silent fallback |

### 7.2 Domain-Specific Criteria

| Domain | Specific Requirement |
|---|---|
| **PDF** | Page composition routing must correctly classify empty/vector/scanned/combined for known test fixtures |
| **P6** | Float calculation must preserve negative-as-critical semantics; TASKPRED parallel relations must not collapse |
| **IFC** | Must emit only `ifcopenshell`-sourced records; no regex/text fallback under any condition |
| **Excel Register** | Header row detection must score known AECO column patterns; malformed files must not throw unhandled exceptions |
| **Word/PPTX** | Must produce flattened `pdf_page` records only; no claim of typed cell/slide/entity persistence |
| **DGN** | Must surface XREF links and conversion status; ODA absence must be diagnostic not silent |
| **Images** | OCR must return empty string (not raise) when Tesseract unavailable; image path must be preserved |
| **DXF** | Entity listing must cap payload size; layer info must be extracted; ezdxf absence must be diagnostic |
| **DWG** | Must either implement via ODA or explicitly reject with diagnostic (no silent skip) |
| **Field/VLM** | Must NOT return mock data in production; `vlm_mock` provenance must be gated behind explicit flag |

### 7.3 Prohibited Patterns (Must Not Appear)

- Mock or fabricated record data in production code paths
- Silent fallback from missing optional dependencies (must fail loudly with diagnostic)
- Regex/regex-text fallback for IFC (ifcopenshell-only per design)
- Absolute debug file paths written to disk
- Hardcoded confidence values without provenance annotation
- Document type classification without keyword-source traceability

---

## 8. Conclusion

The evidence/extraction layer has a **solid foundation in its core domains** (PDF, P6, IFC) with 27 of 43 tests providing good coverage. However, **significant gaps exist**:

1. **Three file types have zero test coverage** (Images, DXF, DWG).
2. **One extractor produces fabricated data** (Field/VLM with `vlm_mock`).
3. **One classifier is a complete stub** (`DocumentClassifier` always returns `"unknown"`).
4. **Excel Register extraction has only a hygiene test** (no behavior validation).
5. **Office file extractors lack behavior tests** (only contract/non-persistence tests).

The baseline confirms that **quality contracts and domain-specific acceptance criteria** are needed before any further implementation expands the extraction surface. This aligns with the DOC-first principle from the Planning Consolidation Register.

---

*This document is read-only analysis. No code was modified. No implementation decisions were made.*
