# Serapeum AECO Assistant — Technical Overview

> **Last Updated**: November 2025  
> **Version**: 1.0  
> **Status**: Active Development

## Executive Summary

Serapeum AECO Assistant is a **local-first, AI-powered desktop application** designed for Architecture, Engineering, Construction, and Operations (AECO) professionals. It provides intelligent document ingestion, compliance analysis, drawing interpretation, and role-aware conversational AI—all while maintaining complete data sovereignty and offline operation.

### Core Capabilities

1. **Intelligent Document Ingestion** — Multi-format support (PDF, Office, CAD, BIM, Images)
2. **AI Vision & OCR** — Automated text extraction and drawing interpretation
3. **Automated Compliance** — Standards-based validation against global codes
4. **Context-Aware Chat (RAG)** — Role-specific AI assistant grounded in project data
5. **Verified Calculations** — Tool-based numerical accuracy (calculator, n8n webhooks)
6. **Data Sovereignty** — Fully offline, SQLite-based, local-first architecture

---

## 🏗️ Architecture Overview

### Technology Stack

| Layer | Technology |
|-------|------------|
| **UI Framework** | Tkinter with ttkbootstrap styling |
| **Database** | SQLite3 (project-specific + global standards) |
| **LLM Backend** | llama-cpp-python (embedded inference, no external server) |
| **Default Model** | Qwen2-VL-7B-Instruct (vision + text, 4.6GB GGUF) |
| **Document Processing** | `pdf2image`, `pypdf`, `python-docx`, `openpyxl`, `python-pptx` |
| **CAD/BIM** | `ezdxf` (DXF), `ifcopenshell` (IFC) |
| **OCR** | Tesseract, PaddleOCR (optional) |
| **Testing** | pytest, ruff (linter), vulture (dead code analysis) |

### Database Architecture

#### 1. Global Standards Database
- **Location**: `.serapeum/standards.sqlite3`
- **Scope**: Shared across all projects
- **Contents**: International and regional codes (IBC, SBC, ADA, LEED, FIDIC, ISO 19650)
- **Tables**: `standards`, `clauses`, `mappings`, `xref`, `clauses_fts` (FTS5)

#### 2. Project-Specific Database
- **Location**: `.serapeum/serapeum.sqlite3` (per project)
- **Tables**:
  - `projects` — Project metadata
  - `documents` — File registry with `content_text` for RAG
  - `pages` — Page-level data with OCR text
  - `analysis` — AI-extracted entities, relationships, requirements
  - `compliance` — Standards violations and clause matches
  - `chat_history` — Conversation logs
  - `key_value` — User settings and LLM configuration
  - `documents_fts` — FTS5 virtual table for full-text search

---

## 📁 Supported File Formats

### ✅ Currently Supported

| Category | Extensions | Processor |
|----------|-----------|-----------|
| **PDF** | `.pdf` | `PDFProcessor` (image extraction) + Vision OCR |
| **Office** | `.docx`, `.doc`, `.xlsx`, `.xls`, `.csv`, `.pptx`, `.ppt` | Word/Excel/PPT processors |
| **Images** | `.jpg`, `.jpeg`, `.png`, `.tif`, `.tiff` | `ImageProcessor` + OCR |
| **CAD** | `.dxf` | `DXFProcessor` (ezdxf) |
| **BIM** | `.ifc` | `IFCProcessor` (ifcopenshell) |
| **Text** | `.txt`, `.md`, `.json` | Direct text extraction |

### ⚠️ Partial Support

| Format | Status | Notes |
|--------|--------|-------|
| **DWG** | Requires ODA File Converter | Convert to DXF first (see [DWG_SUPPORT.md](docs/DWG_SUPPORT.md)) |
| **Revit (.rvt)** | Manual IFC export | See [REVIT_SUPPORT.md](docs/REVIT_SUPPORT.md) |

### 🔜 Planned Expansion
- `.dgn` (MicroStation)
- `.zip`, `.rar` (batch ingestion)
- `.obj`, `.stl`, `.3ds` (3D models)
- `.eml`, `.msg` (email correspondence)
- `.rtf`, `.odt`, `.pages` (legacy formats)

---

## 🔄 Document Processing Pipeline

### Phase 1: Discovery & Ingestion
1. **File Discovery** — `DocumentService` scans project folder recursively
2. **Format Routing** — `GenericProcessor` dispatches to specialized processors
3. **Text Extraction** — Native extraction per format (Word, Excel, DXF, IFC, etc.)
4. **Page Conversion** — PDFs/PPTs → PNG images saved to `.pages/` directory
5. **Database Insert** — Populate `documents` and `pages` tables

**⚠️ CRITICAL ISSUE**: PDFs currently return **empty text** (`"text": ""`). Vision OCR is not auto-triggered.

### Phase 2: Vision Processing (Optional)
1. **OCR Backend** — Tesseract or PaddleOCR extracts text from images
2. **VLM Captioning** — Gemma-3-12B generates semantic descriptions
3. **Database Update** — Populate `pages.ocr_text` and `pages.vlm_caption`

**⚠️ CRITICAL ISSUE**: Vision worker is **not automatically queued** post-ingestion. UI button is disabled.

### Phase 3: AI Analysis
1. **Entity Extraction** — `AnalysisEngine` uses LLM to identify zones, materials, dimensions
2. **Relationship Mapping** — Links entities across documents (BOQ ↔ drawings)
3. **Compliance Check** — `ComplianceAnalyzer` matches content against standards database
4. **Cross-Document Linking** — `CrossDocumentAnalyzer` finds drawing-spec relationships

**⚠️ CRITICAL ISSUE**: `content_text` is empty, so **analysis returns zero entities**.

### Phase 4: User Interaction (Chat)
1. **RAG Context Retrieval** — `RAGService` uses FTS5 to search `documents_fts`
2. **Role-Aware Prompting** — `RoleManager` loads specialty-specific system prompts
3. **Tool Execution** — LLM can delegate to `CalculatorTool` or `N8NTool` for verified results
4. **Response Generation** — LLM response displayed in `ChatPanel`

---

## 💬 Role-Aware Chat System

### Role & Specialty Selection

| Role | Focus |
|------|-------|
| **Contractor** | Claims, schedules, RFIs, constructability |
| **Owner** | Cost control, change orders, compliance |
| **Technical Consultant** | Design validation, code compliance |
| **PMC** | Project coordination, milestone tracking |

| Specialty | Domain |
|-----------|--------|
| **Arch** | Architectural design, layouts, finishes |
| **Str** | Structural safety, load analysis, reinforcement |
| **Mech** | HVAC, plumbing, fire protection |
| **Elec** | Electrical systems, lighting, power distribution |
| **Other** | General project questions |

### Chat Features

1. **Retrieval Augmented Generation (RAG)**
   - Uses FTS5 to search `documents_fts` table
   - Retrieves top-K relevant document chunks
   - Injects context into LLM system prompt

2. **Tool Use System**
   - **CalculatorTool**: Safe math evaluation (prevents LLM hallucination)
   - **N8NTool**: Webhook integration for external workflows
   - LLM can request tool execution via structured JSON

3. **File Attachments**
   - Users can attach code/text files to chat
   - Content is included in LLM context

4. **LLM Configuration**
   - Settings dialog for Base URL, API Key, Model selection
   - Config saved to `.serapeum/_context/profile.json`

---

## 📊 Analysis Engine

### `AnalysisEngine`
- **Input**: `content_text` from `documents` table
- **Output**: JSON with `entities`, `relationships`, `requirements`, `issues`, `summary`
- **Modes**:
  - **LLM-powered** (default): Uses Gemma-3-12B for structured extraction
  - **Zero-LLM fallback**: Basic keyword/regex extraction

### `ComplianceAnalyzer`
- **Input**: Document entities + global standards database
- **Process**:
  1. Fetch relevant clauses from `standards.sqlite3`
  2. LLM compares document content against clauses
  3. Identify violations or compliance gaps
- **Output**: JSON with `violations` array (clause ID, severity, description)

### `CrossDocumentAnalyzer`
- **Purpose**: Link related documents (e.g., drawing A-101 ↔ spec 03 30 00)
- **Techniques**:
  - Filename heuristics
  - Metadata matching
  - Entity overlap analysis

---

## 🗂️ Directory Structure

```
D:\SerapeumAI\
├── run.py                      # Application entry point
├── run_pipeline_headless.py    # CLI ingestion script
├── requirements.txt            # Python dependencies
├── config/
│   └── config.json             # App-wide settings
├── .serapeum/                  # Local data directory
│   ├── serapeum.sqlite3        # Project-specific DB
│   ├── standards.sqlite3       # Global standards DB
│   └── recent_projects.json    # Project history
├── src/
│   ├── core/                   # LLM, pipeline, config
│   ├── db/                     # DatabaseManager
│   ├── document_processing/    # File processors
│   ├── analysis_engine/        # AI analysis modules
│   ├── compliance/             # Standards & compliance
│   ├── services/               # RAG, project services
│   ├── tools/                  # Calculator, n8n integration
│   ├── ui/                     # Tkinter UI panels
│   ├── vision/                 # OCR & VLM workers
│   ├── role_adaptation/        # Role-specific prompts
│   └── role_management/        # Role selection logic
├── scripts/
│   ├── debug/                  # Diagnostic scripts
│   ├── migrations/             # Schema updates
│   └── seeds/                  # Sample data
├── tests/                      # Pytest test suite
└── docs/                       # User guides
```

---

## 🐛 Known Issues & Gaps

### Critical Blockers

1. **Zero Text Extraction from PDFs**
   - **Issue**: `PDFProcessor` returns `"text": ""` with comment "OCR handled later"
   - **Impact**: RAG, Analysis, and Compliance are non-functional (57/57 docs show 0 chars)
   - **Fix**: Implement native PDF text extraction using `pypdf` library

2. **Vision Worker Not Auto-Triggered**
   - **Issue**: Vision processing must be manually initiated (UI button is disabled)
   - **Impact**: OCR text is never populated, even when PDFs have scanned pages
   - **Fix**: Auto-queue pages for vision processing post-ingestion

3. **Undefined Variable Errors (7 Critical)**
   - **Files**: `contractor_adapter.py`, `owner_adapter.py`, `pmc_adapter.py`, `chat_panel.py`, `main_window.py`
   - **Impact**: Application crashes on certain code paths
   - **Fix**: Define missing `q`, `ce`, `e` variables; remove unreachable code

### Medium Priority

4. **Empty Standards Database**
   - `standards.sqlite3` contains 0 standards and 0 clauses
   - Compliance checks return empty results

5. **Missing Native Revit Support**
   - `.rvt` files require manual IFC export
   - No programmatic Revit API integration

6. **Text Mirrors Not Implemented**
   - Spec mentions saving `.txt` files per page (not currently done)

### Low Priority (Code Quality)

7. **88 Auto-Fixable Lint Issues** (unused imports, f-strings, etc.)
8. **Dead Code Detected** (`llm_integration/`, `chat_panel_enhanced.py` appear unused)

---

## 🧪 Testing & Validation

### Test Suite

| Test File | Coverage | Status |
|-----------|----------|--------|
| `test_smoke.py` | Core imports, DB init, LLM init | ✅ 3/4 pass |
| `test_llm_connection.py` | LLM API connectivity | ❌ Requires LM Studio running |
| `test_all_processors.py` | File routing, extraction | ✅ All pass |
| `test_cad_processors.py` | DXF & IFC processors | ✅ All pass |
| `verify_rag.py` | FTS5 search | ✅ Pass |

### Linting Results

```bash
# High-severity errors (must fix)
py -3.11 -m ruff check src --select E9,F63,F7,F82,F821
# Result: 7 undefined variable errors

# All issues
py -3.11 -m ruff check src scripts tests
# Result: 148 errors (88 auto-fixable)

# Dead code detection
py -3.11 -m vulture src scripts
# Result: ~115 unused functions/classes (~60% confidence)
```

---

## 🔧 Configuration

### LLM Settings
- **Location**: `.serapeum/_context/profile.json` (per project)
- **Fields**:
  - `llm_model_path` (default: `models/qwen2-vl-7b-instruct-q4_k_m.gguf`)
  - `llm_use_gpu` (default: true, auto-detect)
  - `llm_n_gpu_layers` (default: 33, 0 for CPU-only)
  - `llm_context_window` (default: 4096)
  - `n8n_webhook_url` (for N8NTool)

### OCR Backend
- **Tesseract**: Set `TESSERACT_CMD` env variable
- **PaddleOCR**: Requires `paddlepaddle` and `paddleocr` packages

---

## 🚀 Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/yourorg/SerapeumAI.git
cd SerapeumAI

# Install dependencies
pip install -r requirements.txt

# Optional: CAD/BIM support
pip install ezdxf ifcopenshell

# Optional: Advanced OCR
pip install paddlepaddle paddleocr
```

### Running the Application

```bash
# Launch GUI
python run.py

# Headless pipeline (CLI)
python run_pipeline_headless.py --project_dir "path/to/project"
```

### First-Time Setup

1. **Install Serapeum** (includes automatic model download)
2. **First Launch**: App downloads Qwen2-VL-7B (4.6 GB, one-time)
3. **Create a New Project** via UI
4. **Select Project Folder** containing AECO documents
5. **Run Pipeline** to ingest and analyze files
6. **Open Chat Panel** for role-aware AI assistance

---

## 📖 Related Documentation

- [DWG Support Guide](docs/DWG_SUPPORT.md) — Converting DWG to DXF
- [Revit Support Guide](docs/REVIT_SUPPORT.md) — Manual IFC export workflow
- [CAD Quick Start](docs/QUICKSTART_CAD.md) — Testing CAD/BIM processors
- [Codebase Audit](codebase_audit.md) — Detailed file inventory
- [Application Values](application_values_report.md) — Core capabilities explained

---

## 🛠️ Development Roadmap

### Immediate Priorities (Q4 2025)
- [ ] Implement native PDF text extraction (`pypdf`)
- [ ] Auto-trigger Vision worker post-ingestion
- [ ] Fix 7 critical undefined variable errors
- [ ] Populate standards database with sample data

### Short-Term (Q1 2026)
- [ ] Implement `.rvt` support via Autodesk Forge API
- [ ] Add DWG auto-conversion using ODA File Converter
- [ ] Enhance compliance reporting (export to PDF/Excel)
- [ ] Add project templates for common AECO workflows

### Long-Term (2026)
- [ ] Cloud sync option (optional, privacy-preserving)
- [ ] Plugin system for custom processors
- [ ] Multi-language support (Arabic, Chinese, Spanish)
- [ ] Advanced visualization (3D model viewer, Gantt charts)

---

## 📝 License & Attribution

**License**: [Specify license here]  
**Author**: [Your Name/Organization]  
**Contact**: [Email/Website]

---

## Appendix A: Module Responsibility Matrix

| Module | Primary Responsibility | Key Classes/Functions |
|--------|------------------------|----------------------|
| `core/llm_service.py` | LLM API interface | `LLMService.chat()` |
| `core/pipeline.py` | Orchestration | `Pipeline.run()` |
| `db/database_manager.py` | SQLite operations | `DatabaseManager` |
| `document_processing/generic_processor.py` | File routing | `GenericProcessor.process()` |
| `document_processing/pdf_processor.py` | PDF → images | `PDFProcessor.run()` |
| `document_processing/dxf_processor.py` | DXF parsing | `DXFProcessor.run()` |
| `document_processing/ifc_processor.py` | IFC/BIM parsing | `IFCProcessor.run()` |
| `analysis_engine/analysis_engine.py` | Entity extraction | `AnalysisEngine.analyze()` |
| `analysis_engine/compliance_analyzer.py` | Standards checks | `ComplianceAnalyzer.analyze()` |
| `services/rag_service.py` | FTS5 retrieval | `RAGService.get_context()` |
| `tools/calculator_tool.py` | Math evaluation | `CalculatorTool.execute()` |
| `ui/chat_panel.py` | Chat interface | `ChatPanel._chat_thread()` |
| `ui/main_window.py` | Main GUI | `MainApp` |
| `vision/run_vision_worker.py` | OCR + VLM | `VisionWorker.run()` |

---

## Appendix B: Database Schema

### `documents` Table
```sql
CREATE TABLE documents (
    id TEXT PRIMARY KEY,
    file_name TEXT,
    file_path TEXT,
    file_type TEXT,
    file_size INTEGER,
    created_at TIMESTAMP,
    content_text TEXT,  -- For RAG search
    meta TEXT  -- JSON metadata
);
```

### `pages` Table
```sql
CREATE TABLE pages (
    id TEXT PRIMARY KEY,
    doc_id TEXT,
    page_index INTEGER,
    image_path TEXT,
    ocr_text TEXT,      -- From Tesseract/Paddle
    vlm_caption TEXT,   -- From Gemma-3-12B
    text TEXT,          -- Legacy field
    FOREIGN KEY (doc_id) REFERENCES documents(id)
);
```

### `documents_fts` Table (FTS5)
```sql
CREATE VIRTUAL TABLE documents_fts USING fts5(
    doc_id UNINDEXED,
    file_name,
    content_text,
    content='documents',
    content_rowid='rowid'
);
```

---

**End of Technical Overview**
