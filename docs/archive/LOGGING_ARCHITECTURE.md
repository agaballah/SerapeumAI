# Logging Architecture

## Overview
SerapeumAI uses a two-tier logging system to separate application-level events from project-specific processing.

## Log Locations

### 1. Application Logs
**Location**: `D:\SerapeumAI\logs\`

**Purpose**: System-level events
- Application startup/shutdown
- Configuration changes
- System errors
- Model loading
- Database connections

**Files**:
- `app.jsonl` - JSON-formatted application logs
- Other system logs

**Format**: JSON (structured logging)

---

### 2. Project Logs
**Location**: `<project_directory>\.serapeum\logs\`

**Example**: `D:\AAC\Misc\MCCC_Riyadh HQ\.serapeum\logs\`

**Purpose**: Project-specific processing
- Document ingestion
- File processing (PDF, Excel, Word, CAD, etc.)
- Extraction results
- Geometry analysis
- VLM prompts

**Files**:
- `processing.log` - All document processing (unified)
- Individual processor logs if needed

**Format**: Human-readable with timestamps

---

## Implementation

### Project Logger
**File**: `src/document_processing/cad_logger.py` (renamed to `project_logger.py`)

**Usage**:
```python
from src.document_processing.cad_logger import set_project_directory, log_processing

# Set project directory when loading project
set_project_directory("D:\\AAC\\Misc\\MCCC_Riyadh HQ")

# Log processing events
log_processing("[pdf.step1] Extracting text from document.pdf")
log_processing("[excel.complete] Processed 3 sheets from BOQ.xlsx")
log_processing("[cad.geometry] Extracted 450 entities from drawing.dgn")
```

**Output**:
- **Console**: `[pdf.step1] Extracting text from document.pdf`
- **File**: `2026-01-11 10:20:15 - [pdf.step1] Extracting text from document.pdf`

---

## Integration Points

### Document Processors
All processors should use project logger:
- `pdf_processor.py` ✅ (already has detailed logging)
- `excel_processor.py` ✅ (enhanced with step logging)
- `cad_converter_manager.py` ✅ (uses print, needs migration)
- `dxf_processor.py` ✅ (uses print, needs migration)
- `word_processor.py` (uses `_log()`, needs migration)
- `ppt_processor.py` (uses `_log()`, needs migration)

### Migration Plan
1. Import project logger in each processor
2. Replace `print()` with `log_processing()`
3. Replace `_log()` with `log_processing()`
4. Set project directory when project loads

---

## Benefits

### Separation of Concerns
- **Application logs**: Debugging system issues
- **Project logs**: Tracking document processing

### Easy Troubleshooting
- Check application logs for system errors
- Check project logs for processing issues
- Each project has its own log history

### Clean Organization
- Logs stay with project data
- No mixing of different projects
- Easy to archive/share with project

---

## Next Steps

1. ✅ Rename `cad_logger.py` to `project_logger.py`
2. ✅ Update to handle all document types
3. ⏳ Integrate into all processors
4. ⏳ Set project directory on project load
5. ⏳ Test with real processing
