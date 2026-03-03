# Upgrade & Realignment Plan: Serapeum v02 (Engineering Truth Engine)

## Context
The application is transitioning from a document-chat assistant (v01) to a structured fact-based Truth Engine (v02). This plan outlines the steps to align documentation, UI behavior, and AI narrative with this new reality.

## Phase 1: Documentation Governance (COMPLETED)
- [x] **Create Documentation Index**: Centralized hub at `docs/INDEX.md`.
- [x] **Clean README**: Focused on "Single Run Path" (`python run.py`).
- [x] **Sync User Manual**: Rewrote `docs/USER_MANUAL.md` to reflect Facts/Schedule tabs and Snapshot logic.
- [x] **Archive Obsolete Specs**: Moved contradictory historical docs to `docs/archive/`.

## Phase 2: UI & UX Synchronization (IN PROGRESS)
- [ ] **Fact Browser Detail View**: Implement a side panel in the `FactsPage` to show fact lineage (file/page/cell).
- [ ] **Snapshot Persistence**: Ensure the `MainApp` snapshot selection persists across tab switches.
- [ ] **Job Feedback**: Add a visual "Job Log" to the Dashboard to explain what builders are currently running.

## Phase 3: AI Narrative Refinement (PLANNING)
- [ ] **Update LLM System Prompt**:
    - Instruct the model to query the `Fact Layer` before attempting RAG search.
    - Implement the **Refusal Policy**: If facts are missing, the LLM should output a "Coverage Gap" report rather than guessing.
- [ ] **Consistency Check**: Prompt the AI to flag conflicts between current and past snapshots.

## Phase 4: Production Hardening
- [ ] **Local Model Bundling**: Clarify `models/DOWNLOAD_INSTRUCTIONS.md` to support offline-only deployments.
- [ ] **Storage Management**: Implement a cleanup utility for `.serapeum/cache` to prevent disk bloat.

---
*Status: Architecture shifted to v02 Truth Engine core. Documentation aligned. Next step: Deep fact-gating in Expert Chat.*
