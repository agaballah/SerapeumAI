# Proposal: Layered Clean Architecture (DDD)

To resolve the tight coupling identified in the audit, we will migrate SerapeumAI to a four-layer architecture.

## 1. CORE (Domain Layer)
*Logic that defines WHAT the system does, independent of UI or Database.*
- **Path**: `src/core/`
- **Contents**:
    - `safety/`: (Validation Enums & Rules)
    - `domain_models/`: (BIM Enums, Schedule Types)
    - `resilience/`: (Retriable Errors, Circuit Breakers)
    - `validators/`: (Prompt & Cross-Modal Logic)
    - `optimizers/`: (Prompt Engineering heuristics)

## 2. INFRASTRUCTURE (Implementation Layer)
*Technical implementations, external tools, and persistence.*
- **Path**: `src/infrastructure/`
- **Sub-dirs**:
    - `persistence/`: `DatabaseManager`, SQL Migrations.
    - `adapters/`: `LLMService`, Tesseract OCR wrappers.
    - `parsers/`: (PDF, IFC, XER, DXF individual processors).
    - `telemetry/`: `StructuredLogging`, `MetricsCollector`.
    - `system/`: `ResourceMonitor`, `ModelManager` (GPU/VRAM).

## 3. SERVICES (Orchestration Layer)
*Pipeline management and workflow logic.*
- **Path**: `src/services/`
- **Sub-dirs**:
    - `ingestion/`: `DocumentService` (File scanning -> Parsers -> DB).
    - `analysis/`: `AnalysisEngine`, `HierarchyRollup`.
    - `compliance/`: `ComplianceAnalyzer`.

## 4. UI / INTERFACE (Delivery Layer)
*Qt Widgets and API bridges.*
- **Path**: `src/ui/`
- **Contents**: Existing `main_window.py` and modular widgets.

---

## 🚀 Execution Strategy
1. **Create Folders**: Initialize the new structure.
2. **Atomic Moves**: Move files one functional group at a time (e.g., all Telemetry first).
3. **Import Shimming**: Add temporary generic imports to avoid breaking 100% of the UI immediately.
4. **Cleanup**: Remove deprecated paths.
