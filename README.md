# SerapeumAI | Engineering Truth Engine 🏗️🤖

SerapeumAI is a professional-grade, **locally-hosted** construction intelligence platform. It enables engineers, project managers, and VDC teams to query, analyze, and verify project documentation (PDFs, Schedules, BIM, Registers) without sensitive data ever leaving their network.

---

## 🌟 Key Features

- **Hybrid Construction RAG**: Combines semantic vector search (for drawings/diagrams) with keyword-based block search (for specifications) and structured SQL queries (for P6/IFC data).
- **Automated Fact Builders**: Extracts "Certified Facts" from P6 (.xer) and BIM (.ifc) files, providing verifiable answers for critical path, element inventory, and float.
- **Vision-Augmented Ingestion**: Automatically analyzes technical drawings (VLM) and indexes descriptions for natural language discovery.
- **Full Traceability**: Every AI-generated answer includes deep lineage links back to the exact source document, page, or database record.
- **Arabic Language Support**: Advanced OCR and text unification for regional construction documentation.
- **Zero-UI LLM**: The app auto-starts LM Studio server headlessly via the `lms` CLI — no manual steps required.

---

## 🚀 Quick Start

### 1. Requirements
- **Python**: 3.10 or 3.11 (3.11 recommended — do NOT use 3.12+)
- **LM Studio CLI** (`lms`): Auto-started by the app — see [INSTALL.md](INSTALL.md) to install it once
- **System Tools**: Tesseract OCR + Poppler (for PDF processing)
- **Hardware**: 16GB RAM minimum (32GB+ recommended for vision processing)

### 2. Installation

> **📋 First-time setup? Double-click `Setup.bat`.**
> This automatically installs Python 3.11, Node.js, and all project dependencies.

```bash
git clone https://github.com/gaballa/SerapeumAI.git
cd SerapeumAI
pip install -r requirements.txt
```

### 3. Execution

Just run — the app handles LM Studio automatically:
```bash
python run.py
```

On first launch, the app will:
1. Auto-start the LM Studio daemon (`lms daemon up`)
2. Auto-start the LM Studio server (`lms server start`)
3. Open the project folder selection dialog

---

## 🏗️ System Architecture

SerapeumAI follows a **Staging → Fact → Brain** pipeline:
1. **Extractors**: Parse various formats (P6, IFC, PDF, XLSX) into structured SQLite staging tables.
2. **Fact Builders**: Consolidate staging data into discrete "Certified Facts" with full lineage.
3. **RAG Engine**: Routes user queries to the appropriate data source (Text Blocks, Fact Table, or Vector Store).
4. **Orchestrator**: Reason about multi-document context to provide grounded engineering insights.

Detailed guide: [Architecture Overview](docs/ARCHITECTURE.md)

---

## 🤝 Contributing
We welcome contributions to extractors, fact builders, and UI enhancements! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

---

## 📄 License & Dual Licensing
SerapeumAI operates under a **Dual Licensing** model to ensure it remains free for the community while supporting commercial development:

1. **Open Source (GNU AGPLv3)**:
   The project is completely free for individual, non-commercial, and open-source use under the [GNU AGPLv3 License](LICENSE). Note that if you modify the code and provide it as a service over a network, you *must* open-source your modifications.

2. **Commercial License**:
   For companies that wish to integrate SerapeumAI into proprietary software, use it internally without the AGPL open-source requirements, or embed it in a commercial product, a separate Commercial License is required. Please contact the author for commercial licensing.

---
*Developed by construction engineers, for construction engineers.*
