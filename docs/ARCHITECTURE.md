# SerapeumAI Architecture Overview

SerapeumAI is designed as an offline-first "Engineering Truth Engine." It transforms unstructured project data into a structured knowledge graph that can be queried via natural language.

---

## 1. Data Processing Pipeline (The "Truth Chain")

SerapeumAI uses a four-stage ingestion process:

### Stage A: Raw Ingestion & Classification
- Documents are registered in the `documents` and `file_versions` tables.
- Files are classified (e.g., DRAWING, SPECIFICATION, SCHEDULE) to determine the next extraction steps.

### Stage B: Modular Extraction (Staging)
Individual extractors parse files into specialized staging tables:
- **P6Extractor**: `p6_activities`, `p6_relations`, `p6_wbs`.
- **IFCExtractor**: `ifc_elements`, `ifc_spatial_structure`.
- **RegisterExtractor**: `register_rows` (for RFIs, submittals).
- **UniversalPdfExtractor**: `doc_blocks` (semantic text chunks).

### Stage C: Fact Building (Certification)
Fact Builders analyze the raw staging data to generate "Certified Facts" (stored in `facts` table):
- **ScheduleFactBuilder**: Calculates critical path membership, float usage, and milestone forecasts.
- **BIMFactBuilder**: Inventory counts by level and type, hierarchy depth.
- **RegisterFactBuilder**: Validates procurement items and metadata.

### Stage D: RAG & Reasoning
The **RAGService** serves as the intelligence router:
1. **Semantic Route**: Queries the Vector Store (ChromaDB) for visual/conceptual matches.
2. **Keyword Route**: Queries SQLite FTS for exact specification matches.
3. **Structured Route**: Queries the native Fact table for engineering metrics.

The **AgentOrchestrator** combines these inputs to formulate the final grounded answer.

---

## 2. Core Components

- **infra/persistence**: Manages per-project SQLite databases.
- **engine/extractors**: Specialized parsers for AEC file formats.
- **engine/builders**: Logic for computing facts and lineage.
- **application/services**: RAG, Vision, and Vector Store orchestration.
- **ui**: CustomTkinter-based desktop interface.

---

## 3. Data Privacy & Local Execution

- **No Cloud Required**: All processing, from OCR to LLM inference, runs locally.
- **Project Isolation**: Every project has its own `.serapeum` folder containing its private database and vector index.
- **Transparency**: The fact lineage system allows users to verify every AI claim against a physical source file.
