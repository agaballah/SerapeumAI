# SerapeumAI | Sample Project Guide

This directory contains a minimal sample project to help you get started with SerapeumAI's ingestion and query capabilities.

## 📁 Structure
- `specs/`: Sample HVAC and Architectural specifications (PDF).
- `schedules/`: A small Primavera P6 (.xer) file with ~50 activities.
- `models/`: A skeletal IFC model representing a 2-story building.
- `registers/`: An Excel-based RFI log.

## 🚀 How to use
1. Launch SerapeumAI: `python run.py`.
2. Click **"Load Project"** in the sidebar.
3. Select this directory (`examples/sample_project`).
4. Wait for the **Sync Engine** to process the files.
5. Navigate to the **Facts** or **Chat** pages to explore the extracted intelligence.

## 💡 Example Queries
- "What are the HVAC commissioning requirements?"
- "Which schedule activities are on the critical path?"
- "How many walls are in the IFC model?"
- "Summarize the open RFIs from the Excel log."
