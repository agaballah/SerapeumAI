# SerapeumAI

**A Windows-first, local-first AECO document review workspace.**

SerapeumAI ingests project documents, extracts structured evidence with transparent provenance, supports fact review and certification, surfaces conflicts, and provides evidence-grounded AI assistance when a local runtime is available. Everything runs on your machine.

---

## What SerapeumAI Does

SerapeumAI helps engineering and construction reviewers:

- **Ingest** project files into a local project workspace
- **Extract** structured information from each document type using domain-specific parsers
- **Inspect evidence** through separated lanes (deterministic extraction, AI output, metadata)
- **Review and certify facts** before relying on them — every fact shows its source, location, and review state
- **Identify conflicts** where different documents state different values for the same subject
- **Ask project questions** through Expert Chat, with answers that show visible evidence lanes and refuse when evidence is insufficient

The application is **review assistance with evidence and provenance**, not a design tool, compliance engine, or autonomous workflow system.

---

## Current Capabilities

| Capability | Status |
|-----------|--------|
| Document ingestion from 14+ formats | Production |
| Structured fact extraction (PDF, IFC, P6, DXF) | Production |
| Evidence provenance on every record | Production |
| Fact review and certification lifecycle | Production |
| Conflict detection and resolution | Production |
| Expert Chat with evidence-labeled answers | Production |
| File Inspector with 5 lanes | Production |
| Honest runtime/dependency reporting | Production |
| Per-project SQLite isolation | Production |
| Portable Windows EXE (no install required) | Production |

---

## Supported File Formats

SerapeumAI supports the following file types for extraction. Files are processed via the Import Documents button or by placing them in the project folder and clicking **Sync Project**:

| Format | Extension(s) | What It Produces |
|--------|-------------|-----------------|
| AutoCAD DXF drawings | `.dxf` | Drawing entities, layers, blocks |
| Primavera P6 / XER schedules | `.xer` | Activities, WBS, critical path |
| PDF documents | `.pdf` | Page text (native or OCR), metadata |
| IFC BIM models | `.ifc` | Project, spatial structure, element inventory |
| Microsoft Word | `.doc`, `.docx` | Document text with pages |
| Microsoft PowerPoint | `.pptx` | Slide-level text extraction |
| Excel workbooks | `.xls`, `.xlsx`, `.xlsm` | Spreadsheet register rows |
| Plain text | `.txt`, `.md`, `.log` | Raw text |
| Structured data | `.json`, `.xml`, `.yaml`, `.yml` | Parsed structured records |
| Spreadsheets | `.csv`, `.tsv` | Table rows |
| Images | `.png`, `.jpg`, `.jpeg`, `.bmp`, `.tif`, `.tiff`, `.webp` | Image metadata |

**Formats not currently supported or intentionally excluded:**

- `.dwg`, `.rvt`, `.dgn` — proprietary CAD/BIM formats; not in the trusted pipeline
- `.ppt` (legacy PowerPoint) — not supported; use `.pptx`
- Stage 2 BIM files, field extractions — reserved for future phases

---

## What Happens When a Document Is Imported

1. The file is registered in a local SQLite database (`.serapeum/` folder in your project directory).
2. A background extraction job runs using the appropriate format-specific extractor.
3. Extracted records are persisted to a `pdf_pages` table (one entry per page of content).
4. For PDF, IFC, P6, and DXF formats, a fact-builder automatically produces structured, reviewable facts.
5. For other formats (PPTX, Word, text, images, spreadsheets), raw evidence is persisted and available for chat, but no reviewable facts are automatically created.
6. All extracted records carry immutable provenance: source file, page or location, extractor method, and composition (native text vs. OCR).

---

## Evidence / Provenance / Fact Review

SerapeumAI maintains a strict separation between evidence types:

```
Raw Deterministic Extraction  (no AI)
AI Output Only                (marked as non-governing)
Full Metadata                 (file properties, JSON metadata)
```

The **File Inspector** presents each document through these lanes so you can always verify what is machine-extracted versus AI-generated.

The **Facts** page shows all extracted facts in a reviewable table:

- Each fact shows: what it says, the source document, evidence location (page, element ID, activity), and review state
- **Review states**: Candidate (machine-produced), Validated (system-checked), Human Certified (reviewer approved), Rejected
- You can **Certify** or **Reject** each fact after verifying it against the source
- Only **Validated** and **Human Certified** facts are used to answer Expert Chat questions

The **Truth Map** shows relationships between facts and source evidence across document domains.

---

## Expert Chat and Local AI Runtime

Expert Chat answers questions about your project using evidence that has been extracted and reviewed.

**How answers work:**
- The answer begins with a **source basis banner** indicating whether the information comes from certified facts, extracted evidence, linked support, or AI-generated synthesis
- Click **Show Evidence** to see the supporting items in four color-coded lanes
- Answers that touch conflicting certified facts include a **conflict disclosure** section
- If the required information is not available, the app **refuses to answer** and explains what evidence would be needed

**Local runtime requirement:**
- Expert Chat and AI-assisted PDF analysis require a local LLM runtime (LM Studio-compatible)
- The application reports runtime state honestly in the sidebar: **READY** or **MODEL_NOT_LOADED / not ready**
- No external API keys or cloud accounts are required
- If the runtime is unavailable, extraction and fact review still work fully

---

## Dependencies and Optional Capabilities

SerapeumAI bundles its core runtime. The table below lists what is required versus optional.

| Capability | Dependency | Required? | What You See If Missing |
|-----------|-----------|----------|------------------------|
| Document ingestion (all formats) | Bundled application | **Yes** | Application will not start |
| Scanned PDF text extraction | Tesseract OCR + Poppler | **Optional** | PDFs extract digital text only; scanned PDFs show "Extraction blocked: Tesseract unavailable" in File Inspector; install from the links below to enable |
| IFC BIM extraction | `ifcopenshell` (pip) | **Optional** | `.ifc` files show red "Blocked — ifcopenshell" in Documents; File Inspector shows "Extraction blocked: required dependency 'ifcopenshell' is missing" with install command |
| MPP schedule extraction | Java + `mpxj`/`jpype1` (pip) | **Optional** | `.mpp` files show red "Blocked — mpxj" status; Dashboard dependency panel shows install command |
| Legacy XLS extraction | `xlrd` (pip) | **Optional** | `.xls` files show red "Blocked — xlrd"; `.xlsx`/`.xlsm` work normally via built-in openpyxl |
| Expert Chat / AI analysis | LM Studio-compatible local runtime | **Optional** | Chat answers show "Expert Brain not initialized" until runtime is available; fact review and evidence extraction work independently |

**Install commands shown in the application:**
- Tesseract: `Install Tesseract OCR from https://github.com/UB-Mannheim/tesseract/wiki`
- Poppler: `Install poppler from https://poppler.freedesktop.org/`
- ifcopenshell: `pip install ifcopenshell`
- mpxj: `pip install mpxj jpype1`
- xlrd: `pip install xlrd`

---

## Download and Installation

### Step 1: Download

1. Go to the [GitHub Releases page](https://github.com/agaballah/SerapeumAI/releases).
2. Download the latest portable ZIP release (e.g., `SerapeumAI_Portable_v0.1.0-3u.zip`).
3. If the release is split into parts (e.g., `.part001`, `.part002`), download **all parts**.
4. Verify the SHA-256 checksum (see below).

### Step 2: Verify (optional but recommended)

```
SHA256SUMS_v0.1.0-3u.txt
```

On Windows, verify the downloaded file:

```powershell
Get-FileHash SerapeumAI_Portable\SerapeumAI.exe -Algorithm SHA256
```

Compare the output hash against the hash in the release's `SHA256SUMS` file.

### Step 3: Extract

1. Extract the **complete** ZIP contents to a folder of your choice.
2. **Do NOT move or delete the `_internal` folder.** The application requires it at runtime.

### Step 4: Run

1. Double-click `SerapeumAI.exe`.
2. No Python installation is required.
3. No administrator privileges are required.
4. No internet connection is required (except for LM Studio on your local machine).

### Where Data Is Stored

When you open or create a project folder, SerapeumAI creates a `.serapeum/` subfolder inside your project directory. This contains:

- The project SQLite database
- Vector embeddings (for chat)
- Extraction output cache

Your project documents outside `.serapeum/` are never modified.

---

## First Use

1. **Open** the application by double-clicking `SerapeumAI.exe`.
2. **Create/open a project**: Select a folder containing your project documents. The app creates a `.serapeum/` subfolder inside it.
3. **Import documents**: Click **Import Documents** in the Documents page, browse to select files, then click **Run Ingestion**. Or place files in the project folder and click **Sync Project** in the sidebar.
4. **Inspect extraction**: Open the **Dashboard** page to see pipeline activity and per-format throughput after a few seconds.
5. **Review facts**: Go to the **Facts** page. Review each fact against its cited source, then click **Certify** or **Reject**.
6. **Inspect evidence**: Click any file to open the **File Inspector**. Verify the evidence lanes separate deterministic extraction from AI output.
7. **Ask chat questions**: Use **Expert Chat** to ask questions. Check the **source basis banner** and click **Show Evidence** to verify each answer.
8. **Verify evidence**: For any chat answer, trace through the shown evidence lanes back to the original source document. Judge AI answers against the displayed project evidence.

---

## Controlled Colleague Testing

This software is ready for real-world engineering review testing. The recommended flow:

1. Start the application
2. Create or open a project folder
3. Import several of your normal project documents
4. Try different supported formats (PDF, DXF, XER, IFC, PPTX, DOCX, Excel)
5. Inspect extraction results in the Dashboard and File Inspector
6. Review extracted facts and test certification
7. Check provenance and evidence for facts that interest you
8. Test conflict presentation if you have documents that disagree
9. If LM Studio is available, test Expert Chat with questions you know the answer to
10. Try a question where you expect the answer is not in evidence — confirm it refuses
11. Close and reopen the project — verify your data persists

> **Tip**: Your confusion is test evidence. If something is unclear, that is a finding worth reporting — even if the software eventually works correctly.

---

## How to Report Findings

Use the template below and open an issue on GitHub, or email your findings:

```
Finding

File/type:
What I tried:
What I expected:
What happened:
Why it matters:
Screenshot:
```

**Do not include in your reports:**
- Passwords
- API keys or tokens
- Private credentials
- Confidential project documents
- Sensitive client information

---

## Known Limitations

These are intentional limitations of the current release, not bugs:

1. **Dependency-controlled capabilities**: PDF OCR, IFC extraction, MPP extraction, and XLS extraction require optional dependencies. Without them, the affected file types show clear "Blocked" warnings instead of failing silently.

2. **Limited fact-builder coverage**: Only PDF, IFC, P6, and DXF automatically produce structured, reviewable facts. Other formats preserve raw evidence for chat use but do not generate reviewable facts.

3. **Acrobat-dependent page navigation**: When opening a PDF fact's source file at a specific page, the application attempts page-aware opening using Acrobat Reader. If Acrobat Reader is not installed, the PDF opens at page 1 in the default viewer, but the cited page is always shown in the status bar.

4. **Schedule is review assistance only**: The Schedule page and schedule-aware facts support review and inspection. SerapeumAI does **not** implement a Schedule Truth Workspace, autonomous scheduling, or a critical path method (CPM) engine.

5. **No AI arithmetic**: LLM responses are informational only. All numerical calculations and deterministic checks are performed by the application's own tools, not by the LLM.

6. **Windows-first**: The application is built and tested for Windows. macOS and Linux are not currently packaged.

7. **Local-only by design**: No cloud services, no external API calls, no telemetry. All processing happens on the local machine.

---

## Privacy / Local-First Statement

SerapeumAI is designed to keep all data and processing on your machine:

- All extracted evidence, facts, and chat history are stored in a local SQLite database inside the project folder (`.serapeum/`).
- No data is sent to external servers.
- No API keys, tokens, or cloud credentials are stored by the application.
- Optional AI features (Expert Chat, PDF AI analysis) require a local LM Studio runtime — no cloud LLM is used.
- Each project has its own isolated database; facts from one project cannot appear in another project's chat.

---

## Important Non-Claims

The current release does **not** and **cannot**:

- Guarantee compliance with legal, contractual, regulatory, or certification requirements
- Replace human engineering judgment or professional review
- Provide autonomous document correction or design authoring
- Access external APIs or cloud services
- Perform OCR on scanned PDFs without Tesseract installed
- Extract structured facts from non-PDF/IFC/P6/DXF formats automatically
- Navigate proprietary CAD formats (`.dwg`, `.rvt`, `.dgn`)
- Perform autonomous schedule analysis or CPM calculations

---

## Project Status

SerapeumAI is under active development. The current release represents a v0.3 engineering baseline with colleague-testing readiness gate passed.

- **Stable release**: v0.1.0-3u (published)
- **Current development**: v0.3 engineering baseline
- **License**: Apache 2.0 — see `LICENSE` and `NOTICE`
- **Third-party notices**: `THIRD_PARTY_NOTICES.md`

---

## Contributing

SerapeumAI is not currently accepting public pull requests. If you find a bug or have a question, please open an issue on GitHub.

See `CONTRIBUTING.md` for internal contributor guidelines.
