# SerapeumAI User Manual
**Version**: 1.0.0
**Last Updated**: December 2025

---

## 📚 Table of Contents
1. [Introduction](#1-introduction)
2. [Installation & Setup](#2-installation--setup)
3. [Getting Started](#3-getting-started)
4. [Core Features](#4-core-features)
   - [Document Ingestion](#document-ingestion)
   - [AI Chat](#ai-chat)
   - [Compliance Analysis](#compliance-analysis)
5. [Advanced Features](#5-advanced-features)
   - [Vision Processing](#vision-processing)
   - [Cross-Document Linking](#cross-document-linking)
6. [Troubleshooting](#6-troubleshooting)

---

## 1. Introduction
**SerapeumAI** is an advanced AI-powered assistant designed for the Architecture, Engineering, and Construction (AEC) industry. It helps you analyze technical documents, verify compliance with building codes, and extract insights from complex drawings and specifications.

### Key Capabilities
- **Multi-Format Support**: Process PDFs, Images, DXF (CAD), and Office documents.
- **Local AI**: Runs entirely on your machine using LM Studio (no data leaves your device).
- **Vision Intelligence**: Understands technical drawings and layouts using Vision Language Models (VLM).
- **Compliance Engine**: Automatically checks documents against SBC, IBC, and NFPA standards.

---

## 2. Installation & Setup

### Prerequisites
- **OS**: Windows 10 or 11 (64-bit)
- **GPU**: NVIDIA GeForce RTX 3060 or better (Recommended for Vision)
- **RAM**: 16 GB minimum (32 GB recommended)
- **Disk Space**: 10 GB free space

### Step 1: Install LM Studio
SerapeumAI relies on **LM Studio** to run the AI models locally.
1. Download LM Studio from [lmstudio.ai](https://lmstudio.ai).
2. Install and launch the application.
3. Search for and download a compatible model (e.g., `Mistral-7B-Instruct` or `Qwen2-VL`).
4. Start the **Local Server** in LM Studio (Port 1234).

### Step 2: Install SerapeumAI
1. Run the `SerapeumAI_Setup.exe` installer.
2. Follow the on-screen instructions.
3. Launch SerapeumAI from the desktop shortcut.

---

## 3. Getting Started

### Creating a Project
1. Click **"New Project"** on the welcome screen.
2. Enter a **Project Name** (e.g., "Riyadh Metro Station").
3. Select a **Root Folder** where your documents are stored.
4. Click **"Create"**.

### Ingesting Documents
1. Once the project is loaded, the system will automatically scan the folder.
2. Click **"Run Pipeline"** to start processing.
3. The system will:
   - Extract text from PDFs and Office files.
   - Convert CAD drawings to readable formats.
   - Index everything for fast search.

---

## 4. Core Features

### Document Ingestion
SerapeumAI automatically organizes your files.
- **Supported Formats**: `.pdf`, `.docx`, `.xlsx`, `.pptx`, `.dxf`, `.jpg`, `.png`
- **Status Indicators**:
  - 🟢 **Indexed**: Ready for search/chat.
  - 🟡 **Processing**: Currently being analyzed.
  - 🔴 **Error**: Failed to process (check logs).

### AI Chat
Chat with your documents using the **Chat Panel** on the right.
- **Ask Questions**: "What are the fire safety requirements for the lobby?"
- **Cite Sources**: The AI will provide citations (e.g., `[Spec-Section-05.pdf, Page 12]`).
- **Context Aware**: The AI knows about all documents in your project.

### Compliance Analysis
Verify your designs against standards.
1. Go to the **"Compliance"** tab.
2. Select a standard (e.g., **SBC 2018**).
3. Click **"Analyze"**.
4. Review the report highlighting compliant and non-compliant sections.

---

## 5. Advanced Features

### Vision Processing
For scanned PDFs and drawings, SerapeumAI uses **Vision AI**.
- **Auto-Trigger**: Automatically detects images and drawings.
- **Captioning**: Generates descriptions for diagrams (e.g., "Floor plan showing emergency exits").
- **OCR**: Extracts text from non-selectable PDFs.

### Cross-Document Linking
The system identifies relationships between documents.
- **Example**: A drawing referencing a specification section.
- **Graph View**: Visualize connections in the **"Graph"** tab.

---

## 6. Troubleshooting

### Common Issues

**Q: The AI is not responding.**
- **A**: Ensure LM Studio is running and the Local Server is started on port 1234.

**Q: PDF text is empty.**
- **A**: The document might be a scanned image. Ensure Vision Processing is enabled.

**Q: "Vision Worker" is paused.**
- **A**: The system pauses background vision tasks when you are chatting to prioritize speed. It will resume automatically.

### Support
For additional support, please contact:
- **Email**: support@serapeum.ai
- **Docs**: [docs.serapeum.ai](https://docs.serapeum.ai)
