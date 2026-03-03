# Analysis & Vision Health Report
## Generated: 2025-12-07

---

## QUESTION 1: Which Data Source Does Chat Use?

### Answer: **HIERARCHICAL - Multiple Sources**

The chat system uses data in this priority order:

1. **PRIMARY: doc_blocks (Block-level Text)**
   - Location: `doc_blocks` table → `doc_blocks_fts` (FTS5 index)
   - Source: Pure text from `py_text` extractors (pypdf, python-docx, etc.)
   - Used by: `RAGService._retrieve_block_level_context()`
   - Contains: Structured chunks with headings + body text
   - **This is the MAIN source for chat RAG**

2. **FALLBACK: documents.content_text (Document-level Text)**
   - Location: `documents` table → `documents_fts` (FTS5 index)
   - Source: Also pure text from py extractors
   - Used by: `RAGService._retrieve_document_level_context()`
   - Used when: Block-level search returns no results

3. **SUPPLEMENTAL: pages.page_summary_short (AI Summaries)**
   - Location: `pages` table (page_summary_short, page_summary_detailed)
   - Source: JSON from **Analysis Model** (Mistral-7B)
   - Used by: `AnalysisEngine._analyze_document()` for document rollup
   - **NOT directly used by chat, but feeds into document-level analysis**

### Data Flow Diagram:

```
User Query
    ↓
ChatPanel → RAGService.retrieve_hybrid_context()
    ↓
├─ Query Router: Classify intent
│  ├─ Semantic → search_doc_blocks(query)  ← USES py_text (pure text)
│  ├─ BIM → query_bim_elements()           ← USES structured data
│  └─ Schedule → query_schedule_activities() ← USES structured data
    ↓
Context (text chunks) → LLM (Llama-3)
    ↓
Response to User
```

### Key Insight:
**Chat uses PURE TEXT from Python extractors, NOT the JSON analysis summaries.**

The analysis summaries are used for:
- Document-level rollups
- Cross-document linking
- Compliance checking

But the **chat RAG retrieves raw text** to give the LLM maximum context.

---

## QUESTION 2: Health Indicators for Analysis

### Current Status (from your logs):

#### ✅ **Healthy Pages (Saved Successfully)**
- Pages that returned valid JSON AND saved to database
- Example: Pages 0, 1 (from Excel files)
- Indicators:
  - ✅ emoji in logs
  - Summary printed
  - Type identified
  - Entities extracted
  - NO error messages

#### ❌ **Unhealthy - Parse Errors** (4 occurrences)
Pages: 52, 53, 56, 57

**Error**: `sequence item 0: expected str instance, dict found`

**Root Cause**: LLM returns:
```json
{
  "entities": [
    {"entity_type": "Contractor", "role": "..."},  ← DICT (wrong!)
    {"entity_type": "SEC", "role": "..."}
  ]
}
```

But schema asks for:
```json
{
  "entities": ["Contractor", "SEC", "Document"]  ← STRINGS (correct)
}
```

**FIX APPLIED**: `page_analysis.py` now normalizes entities (`_save_result()`)

#### ⚠️ **Unhealthy - Save Errors** (0 occurrences so far)
Would occur if database write fails after successful LLM call.

#### ⚠️ **Unhealthy - LLM Errors** (0 major failures)
Would occur if model crashes, OOM, or timeout.

#### ⏸️ **"No Response" Pages** (Pages 49, 50, 51, 54, 55, etc.)

**Error**: Logs show "⚠️ No response" even though LLM returned data.

**Root Cause**: `llm_service.chat_json()` returned `{}` (empty dict) on parse failure, which evaluates to `False` in Python.

**FIX APPLIED**: Changed to return `None` on parse failure.

---

## QUESTION 3: Vision Health Indicators

### Recommendation: Add Vision Health Tracker

Similar to analysis health, we need to track:

```python
# Vision Health States
VISION_HEALTHY = "✅ OCR extracted successfully"
VISION_UNHEALTHY_OCR = "❌ OCR failed (Tesseract/Paddle error)"
VISION_UNHEALTHY_VLM = "❌ VLM failed (Qwen2 error)"
VISION_UNHEALTHY_SAVE = "❌ Failed to save vision data"
VISION_SKIPPED = "⏭️ Skipped (high-quality py_text already exists)"
VISION_PENDING = "⏸️ Queued but not processed"
```

### Key Metrics to Track:

1. **Per-Page Metrics:**
   - `py_text_len` (chars extracted by Python)
   - `vision_ocr_len` (chars extracted by OCR)
   - `vision_general` (exists/null)
   - `vision_detailed` (exists/null)
   - `quality` (queued/low/high)

2. **Aggregate Metrics:**
   - Total pages queued for vision
   - Pages with successful OCR
   - Pages with successful VLM captions
   - Pages skipped (good py_text)
   - Average OCR quality score

3. **Performance Metrics:**
   - Average OCR time per page
   - Average VLM time per page
   - Model swap count (Qwen2 ↔ Mistral)

---

## Implementation: Vision Health Tracker

**File**: `d:\SerapeumAI\src\vision\vision_health_tracker.py`

*(See next artifact for implementation)*

---

## Summary of Fixes Applied

### ✅ 1. Fixed Entity Schema Mismatch
- **File**: `page_analysis.py::_save_result()`
- **Change**: Normalize entities to strings before JSON dump
- **Impact**: Eliminates "sequence item 0" error

### ✅ 2. Fixed "No Response" False Positives
- **File**: `llm_service.py::chat_json()`
- **Change**: Return `None` instead of `{}` on parse failure
- **Impact**: Distinguishes parse failures from empty valid JSON

### ✅ 3. Added Analysis Health Tracking
- **File**: `analysis_engine/health_tracker.py` (NEW)
- **Integration**: `page_analysis.py`
- **Features**:
  - Categorizes failures (parse/save/llm)
  - Identifies retry candidates
  - Prints summary after each document
  - Saves JSON reports

### 🔄 4. Recommended: Add Vision Health Tracker
- **Status**: Not yet implemented (awaiting confirmation)
- **Priority**: Medium (improves visibility into OCR pipeline)

---

## Next Steps

1. **Rerun analysis pipeline** to see new health indicators in action
2. **Review health report** at end of each document:
   ```
   📊 PAGE ANALYSIS HEALTH SUMMARY
   ================================================================================
   ✅ Healthy:          45 /  58
   ❌ Parse Errors:      4
   ❌ Save Errors:       0
   ❌ LLM Errors:        9
   ⏸️  Pending:          0
   ⏭️  Skipped:          0
   
   🎯 Health Rate: 77.6%
   ```

3. **Retry unhealthy pages** using:
   ```python
   from src.analysis_engine.health_tracker import get_health_tracker
   tracker = get_health_tracker()
   retry_pages = tracker.get_retry_candidates(max_attempts=3)
   # Process retry_pages...
   ```

4. **Implement Vision Health Tracker** if needed
