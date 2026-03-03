# Serapeum AI — AECO Project Intelligence Platform

## Purpose

Serapeum AI is an **engineering-first project intelligence system** designed to **eliminate manual cross‑reading, cross‑checking, and cross‑matching** of construction project documents.

The system ingests **all project artifacts** — specifications, drawings, shop drawings, contracts, minutes of meetings (MOMs), schedules, CAD files, BIM models, and images — and builds a **unified, queryable project memory**.

Engineers interact with the project directly:

> *“Should the apartment entrance door be fire‑rated?”*

The system answers **with evidence**, resolving conflicts across:

* Design drawings
* Shop drawings
* Specifications
* Codes & standards
* Contracts and MOMs

Example response:

> *The apartment entrance door **must be fire‑rated for 2 hours**. The architectural design drawings do not explicitly state the rating. However, approved shop drawing **SD‑00421 (dated 00/00/0000)** specifies a 2‑hour fire rating, which aligns with **Clause X.X of the Project Contract** and **MOM – Week 14**. Therefore, the shop drawing governs.*

This is the **intended end‑state**. The current implementation already lays the full technical foundation.

---

## What the Application Is Today

Serapeum AI is currently a **local, offline‑first, deterministic ingestion and analysis system** with the following confirmed capabilities:

### 1. Project‑Scoped Document Ingestion

* Each project is ingested **from its own directory**
* All supported files are scanned while **explicitly excluding internal folders** (`.serapeum`, `.git`, `venv`, etc.)
* Ingestion is **idempotent** using SHA‑256 file hashing
* Documents are re‑ingested automatically if processors change (version‑aware)

Supported formats include:

* **Text & Office**: PDF, DOCX, XLSX, PPTX, TXT, CSV, XML, JSON
* **Images**: PNG, JPG, TIFF, BMP, WebP
* **CAD / BIM**: DWG, DXF, DGN, RVT, IFC
* **Schedules**: XER, MPP

---

### 2. Dual‑Database Architecture (Task 1 — Updated)

Serapeum AI intentionally uses **two physically separate SQLite databases**:

#### A. Project Database (Per Project)

**Location:**

```
<project_root>/.serapeum/project.db
```

**Contains only project‑specific data:**

* Documents (design, shop drawings, MOMs, contracts, schedules)
* Page‑level text, OCR output, and vision output
* Extracted BIM elements and schedule activities
* Analysis results, conflicts, and cross‑references

This database is **fully self‑contained and portable with the project**.

---

#### B. Global Codes & Standards Database

**Location:**

```
<application_root>/data/standards.db
```

**Contains shared, reusable knowledge:**

* Codes (NFPA, SBC, IBC, IEC, ASHRAE, ISO, etc.)
* Standards documents
* Classification metadata

**Routing Logic (Already Implemented):**

* Documents detected as standards (by filename + content patterns) are ingested into the **global database**
* A reference remains in the project database for traceability

This ensures:

* No duplication of codes across projects
* Consistent interpretation of standards

---

### 3. Deterministic File Processing (Per Format)

#### PDFs

Pipeline:

1. Extract native text (PyPDF)
2. Measure total extracted characters
3. If text is **below threshold**, render pages to images
4. Run **Tesseract OCR** (language‑aware)
5. Store:

   * Native text
   * OCR text (if used)
   * Page images for vision

**Nothing is discarded.** All channels are preserved.

---

#### Images

* Stored as normalized PNG copies
* OCR executed immediately (Tesseract)
* Image retained for later vision analysis

---

#### Office Documents

* Converted to structured text
* Section and block extraction where applicable

---

#### CAD (DWG / DXF / DGN)

**Current State:**

* Files are ingested and registered
* Geometry parsing groundwork exists

**Intended Processing:**

* Extract layers, blocks, annotations, and symbols
* Link textual labels to spatial entities
* Enable cross‑reference with drawings and schedules

---

#### BIM (IFC / RVT)

**Current State:**

* Structured data ingestion supported
* BIM elements stored in normalized tables

**Intended Processing:**

* Queryable building elements (doors, walls, fire ratings)
* Attribute‑level reasoning (e.g., fire rating, material)
* Cross‑validation against drawings and specs

---

### 4. Vision Pipeline (Page‑Oriented by Design)

The vision system is **explicitly page‑based**. This is intentional.

#### Current Vision Logic

For each page:

1. **Python Text Extraction**

   * Native PDF text or prior OCR

2. **OCR (If Needed)**

   * Triggered when text is insufficient

3. **Vision Language Model (VLM)**

   * Executed when:

     * Text is short
     * Raster graphics exist
     * Vector drawings exist

The VLM produces:

* **General summary** (what the page shows)
* **Detailed description** (systems, rooms, notes, issues)

Vision quality is scored automatically. Pages may be flagged for retry or human review.

---

### 5. Unified Analysis & Fusion

All signals are fused:

* Native text
* OCR text
* Vision summaries
* Vision detailed descriptions
* Layout and spatial hints

The analysis engine:

* Detects conflicts
* Cross‑links related documents
* Preserves source attribution (page, document, revision)

This is the foundation for **engineering‑grade answers**.

---

## What the Application Is Not (Yet)

* ❌ Not a general chatbot
* ❌ Not a speculative AI assistant
* ❌ Not a cloud SaaS (by design)
* ❌ Not replacing engineering judgment

---

## What the Application Is Intended to Become

Serapeum AI is intended to function as a **digital senior reviewer**:

* Reads *everything*
* Remembers *everything*
* Cross‑checks *everything*
* Explains *why* a conclusion is correct

The engineer does **not search documents** — the engineer **questions the project**.

---

## How to Run the Application (Task 2)

### Requirements

* Python 3.11
* Local OCR (Tesseract)
* Optional GPU for vision (recommended)

### Run

```powershell
python run.py
```

`run.py` is the **single authoritative entry point**. It:

* Initializes configuration
* Loads databases
* Launches UI
* Controls ingestion, vision, and analysis pipelines

---

## Final Notes

Everything described above is **grounded in the existing codebase**:

* `DocumentService`
* `GenericProcessor`
* Vision worker & adaptive extraction
* DatabaseManager schema

Future work builds *on this*, not around it.
