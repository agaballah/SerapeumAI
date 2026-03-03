# SerapeumAI — User Manual (What You See)

This manual describes the **visible UI**: screens, panels, and the normal flow from “new project” to “chat” and “review”.

It avoids code, internal architecture, and implementation details on purpose.

---

## 1) Core concepts

### Project
A project is a named workspace that points to a **root folder** on your disk. SerapeumAI scans that folder, ingests supported files, and builds an index so you can search and chat.

Typical project folders contain:
- Specifications (PDF)
- Submittals (PDF)
- Meeting minutes (DOCX/PDF)
- Schedules (XLSX)
- Drawings or exported drawings (PDF/Images; DXF where supported)

### Documents
Documents are the files inside your project folder. Each document is shown with a **processing status** (for example: Ready / Processing / Error).

### Pipeline (processing)
When you process a project, SerapeumAI runs a set of background steps such as:
- Extracting text (native PDFs and text-based files)
- Vision/OCR for scanned documents or drawings
- Indexing for fast search and retrieval
- Building cross-document links (references, repeated entities)
- Preparing data for compliance review and chat

You don’t need to know the internal mechanics—just that processing needs to run before results are reliable.

### Chat
Chat is a document-grounded conversation UI. Responses can include **citations** showing which documents and pages supported the answer.

### Compliance review
Compliance review is a structured workflow where you:
1) Pick a standard (or standard set)
2) Run analysis
3) Review findings with evidence and citations

SerapeumAI can accelerate review, but it does not replace professional judgment.

### Graph view
Graph view visualizes relationships between documents, references, and extracted entities to help you discover “what connects to what”.

---

## 2) First launch flow

### Welcome screen
On launch you typically see:
- **New Project**
- **Open Project** (or recent projects list)

If this is your first run, you may also be prompted to:
- Choose a local AI model (or confirm a default model)
- Confirm a default storage location for app data (projects, cache, reports)

> Tip: If the app asks you to choose a model, pick a smaller model first. You can switch later.

---

## 3) Creating a project

### New Project screen
You will typically enter:
- **Project name**
- **Root folder** (the folder that contains your files)

After creating the project:
- The project opens in the main workspace
- The app shows your document list (initially unprocessed until you run processing)

### Best practice for project folders
- Keep everything for one project inside one folder tree.
- Use descriptive filenames (the citation system depends on filenames being readable).
- Avoid deeply nested folders if possible.

---

## 4) Main workspace layout

SerapeumAI is organized around a few primary areas:

### B) Work area
The center area changes depending on the selected tab:
- **Dashboard**: High-level overview of files and processing progress.
- **Facts**: The "Ground Truth" browser. View validated engineering data extracted from your files.
- **Schedule**: Visual and tabular view of P6 schedule activities and critical paths.
- **Documents**: Folder-based browser for raw files and their individual processing statuses.
- **Expert Chat**: The document-grounded AI interface with citations and engineering context.

### C) Snapshot (As-Of) Selection
Located at the bottom of the sidebar, this selector allows you to view the project state at a specific point in time (e.g., a specific data date or issue package). Switching the snapshot refreshes the data in the Facts, Schedule, and Chat panels to maintain consistency.

---

## 5) Dashboard & Ingestion

The Dashboard is your entry point for a project. It shows:
- **File Counts**: Breakdown of PDFs, Drawings, Schedules, and Models.
- **Processing Status**: A summary of how many files are "Ready" vs "Processing" vs "Error".
- **⚡ Sync Project**: A button to trigger a full scan and ingestion of your project folder.

---

## 6) Facts (Engineering Truth Browser)

The **Facts** tab is the core of Serapeum v02. Unlike raw text search, the Facts panel shows structured data that has been "certified" by the engine's builders.

- **Fact Types**: Filter by schedule milestones, BIM properties, document revisions, or procurement statuses.
- **Lineage**: Select a fact to see exactly which file, page, or cell it came from.
- **Status**: Facts are marked as **Validated** (passed automated rules) or **Candidate** (needs review).

---

## 7) Schedule

The **Schedule** tab displays data extracted from Primavera P6 (XER/XML) or Excel schedules.
- **Critical Path**: View the driving sequence of activities.
- **Forecast vs Baseline**: Compare current dates against your project baseline.
- **Cross-Links**: See which drawings or BIM elements are linked to a specific activity.

---

## 8) Expert Chat

### Writing good queries
Better prompts are:
- Specific (which discipline, which area, which requirement)
- Ask for evidence (“cite the section/page”)
- Define constraints (“based only on project documents”)

Examples (write in your own words):
- “Summarize fire egress requirements for the lobby and cite sources.”
- “List any conflicts between drawing A and spec section B with citations.”
- “What does the standard say about stair width? Provide the quoted requirement and reference.”

### Citations
When citations are enabled, answers include references such as:
- Document name
- Page number (where available)

Use citations to:
- Verify answers
- Jump to the source text
- Build review notes

### Common chat behaviors
- If processing is incomplete, chat may respond with partial information.
- If you switch models mid-project, answers may differ in tone/quality.

---

---

## 9) Settings & Privacy

Access settings via the gear icon or the **Settings** button (availability depends on your build).

### Model
- Select which local AI model is used for extraction and chat.
- Performance controls allow you to enable GPU acceleration if your hardware supports it.

### Privacy
- **Local-first**: All processing happens on your machine.
- **Index Data**: Project indexes are stored in a `.serapeum` folder within your project directory.

---

## 9) Settings

Settings vary by build, but commonly include:

### Model
- Select which local AI model is used
- Optional performance controls (e.g., GPU acceleration)

### Performance
- Background work priority (chat vs processing)
- Limits for very large projects (to keep the UI responsive)

### Privacy
- Local-only processing controls
- Export preferences (where reports are saved)

---

## 10) Exporting Results

Serapeum supports exporting data for use in external reports:
- **Fact Export**: Export the validated truth table for a specific snapshot.
- **Expert Chat Transcript**: Save your conversation and citations as Markdown.
- **Schedule Reports**: Export critical path analysis or variance reports.

---

## 11) Practical workflow (recommended)

1) **Open Project**: Select your engineering folder.
2) **⚡ Sync Project**: Trigger the ingestion and extraction pipeline.
3) **Review Facts**: Check the Facts tab to see what properties and milestones were extracted.
4) **Query Expert Chat**: Ask domain-specific questions about procurement, schedule risks, or design compliance.
5) **Switch Snapshots**: Compare current data against previous updates.

---

## 12) Limitations (Honest Expectations)

SerapeumAI is a **Review Assistant**, not a Certification Tool.
- **Refusal Policy**: If the system cannot find a "Certified Fact" to support an answer, it may refuse to answer rather than guess.
- **Quality Matters**: Low-resolution scans or complex hand-drafted drawings may require manual fact verification.
- **Deterministic Core**: Calculations are deterministic; the AI is the narrator of those facts.
