# SerapeumAI: Project Legacy Ledger
**The Definitive History and Evolution of the AECO Engineering Intelligence Platform**

---

## 📜 Development Timeline & Phase Summaries

### Phase 1: Absolute Repository Scour (Nov 2025 - Jan 2026)
- **Objective**: 100% audit of the prototype codebase (150+ files).
- **Outcome**: Identification of high-value logic "islands" (Hidden Personas in `src/vision`, Hybrid RAG in `src/services`) and production bottlenecks (Global GPU lock, 37-column tuple fragility).
- **Baseline**: 0 chars extracted from 100% of analyzed PDFs; 0 standards in DB.

### Phase 2: Structural Realignment & Promotion
- **Migration to Domain-Driven Design (DDD)**: Established the professional directory structure.
    - `src/infra/`: Persistence, Adapters (LLM/Vector), Telemetry.
    - `src/domain/`: Engineering Models, Intelligence (Confidence/Prompts), Personas.
    - `src/application/`: Pipeline Orchestration, Document/RAG Services.
- **Outcome**: Successfully promoted Advanced Engines to Core, resolving import divergence.

### Phase 3: Performance & Foundation (Jan 2026)
- **Milestones**:
    - Established CI/CD (GitHub Actions for test/lint/build).
    - Captured Performance Baselines (Vision: 12.6s/page; Search: <50ms FTS).
    - Implemented Parallel Vision Processing (ThreadPoolExecutor).
    - Enabled LLM Streaming UI (Perceived latency reduction from 30s to <1s).

### Phase 4: Persistence & State Sovereignty (Production Hardening)
- **Milestones**:
    - **Versioned SQL Migrations**: Transitioned to automated schema discovery via `migrations/` directory.
    - **Structured DAO**: Replaced positional 37-column tuples with type-safe `PageRecord` objects.
    - **Knowledge Graph Enums**: Standardized `EntityType` and `RelationshipType` for machine-readable connections.
    - **Durable Storage**: Implemented compressed `BLOB` storage for failure recovery context.

### Phase 5: Verification & Production Certification
- **Outcome**: 80%+ coverage target for Core components. Validated Physical Quantity Parser (unit-aware engineering tolerances) and Bayesian Confidence Learning (Beta distribution updates).

---

## 🏗️ Architectural Decisions (ADRs)

### ADR-001: Local-First Data Sovereignty
- **Selection**: SQLite3 for metadata; local `llama-cpp-python` for inference.
- **Rationale**: AECO requirements involve sensitive proprietary blueprints; cloud-zero operation is a mandatory competitive advantage.

### ADR-002: Unit-Aware Engineering Logic
- **Selection**: `pint` Unit Registry integration.
- **Rationale**: Engineering requirement checking (e.g., 5mm vs 0.005m) requires mathematical precision that LLMs cannot provide alone.

### ADR-003: Bayesian Confidence Updates
- **Decision**: Departed from linear confidence updates (+0.05/-0.05) in favor of a Bayesian Beta distribution.
- **Rationale**: Provides statistically sound reliability scoring that accounts for sample size and model-specific history.

---

## 📁 Key Legacy Documentation (Archived)
The following documents have been synthesized into this ledger and archived into `docs/archive/`:
- `PHASE1_ARCHITECTURE.md` (Original Prototype Blueprint)
- `PHASE3_FINAL_REPORT.txt` (Initial Performance Results)
- `TECHNICAL_OVERVIEW.md` (November 2025 Baseline)
- `PHASE4_ROADMAP.md` (Strategic Transition Plan)

---

## 🚀 The Future: Enterprise Readiness
The repository is now "Alembic-ready" and "DDD-compliant". New features (e.g., Revit API integration, Arabic language support) can be added as simple domain modules without impacting the hardened persistence and ingestion layers.
