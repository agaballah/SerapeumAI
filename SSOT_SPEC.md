# SerapeumAI Consolidated Specification (SSOT)

**Product Intent • Documentation Rules • User Journey • Engineering Build Bible**

Version: v1.2 | Date: 19 Feb 2026

---

## Purpose

This document consolidates the current, authoritative product and engineering intent for SerapeumAI into a single source of truth (SSOT). It aligns:
1. The non-negotiable product contract (facts-only answering)
2. Documentation red lines and run-path rules
3. The end-to-end user workflow
4. The offline engineering architecture and data model required to enforce provenance, reproducibility, and certification gates.

---

## 1. Product Contract (Non-Negotiables)

### Core Promise
- The assistant answers **ONLY** from Certified Facts (`VALIDATED` and, where required, `HUMAN_CERTIFIED`).
- Every answer is **reproducible**: same file versions + extractor/builder versions must rebuild the same fact set.
- Every answer is **provable**: facts must include lineage back to evidence (page/bbox, cell, GUID, activity ID, etc.).
- If required facts/links are **missing**, the assistant **MUST refuse** and return (a) the coverage gap and (b) a job plan to close it.
- If **conflicting** certified facts exist, the assistant **MUST disclose** the conflict; no silent choice.

### Key Definitions

| Term | Definition |
|------|-----------|
| **Evidence** | Atomic extracted item tied to a specific file version and location |
| **Canonical Entity** | Normalized real-world project object across sources |
| **Crosswalk Link** | Explicit link between entities (`CANDIDATE` or `VALIDATED`) |
| **Fact** | Computed/validated statement allowed in answers, bound to an as-of snapshot and backed by lineage |

---

## 2. Scope, Out-of-Scope, and Red Lines

### In Scope
- Desktop-first workflow (Windows baseline)
- Local-first processing as default; privacy-first language must be accurate
- Evidence-based output with citations back to project documents
- Workflow: Projects → Documents → Processing → Chat/Compliance → Export

### Out of Scope
- No design authoring (no CAD/BIM editing)
- No cloud collaboration features required for core use
- No automatic submission/approval actions on behalf of the user
- **No autonomous agent behavior without a clear user trigger**

### Documentation Red Lines
- Docs must match **shipped behavior**, not ambition
- User docs are **not** engineering docs (avoid internal module names, file paths, stack diagrams, code blocks)
- One clear run path: `python run.py`
- No claims of guaranteed compliance certification; position outputs as review assistance with evidence

---

## 3. Canonical Documentation Set

### User-Facing Docs

| Doc | Audience | Allowed | Not Allowed |
|-----|----------|---------|-------------|
| `README.md` | All | What it does; minimal setup; single run path | Architecture; internal paths |
| User Manual | Practitioners | Screen-by-screen workflow | Implementation modules; code |
| System Requirements | IT/Admin | OS, Python, models, hardware, offline posture | Ambiguous privacy claims |
| Troubleshooting | All | Common errors and recovery steps | Speculative fixes |
| `CONTRIBUTING.md` | Devs | Dev setup, lint/tests, contribution guide | User doc content |

---

## 4. End-to-End Workflow

> The workflow is a deterministic pipeline that turns raw artifacts into certified, queryable truth. Chat is the front-end narrator; the truth lives in the database.

### Pipeline

```
Ingest → Extract → Normalize/Link → Build Facts → Validate/Certify → Snapshot → Chat
```

| Stage | Job (backend) | DB Outputs | User-Visible Surface |
|-------|--------------|-----------|---------------------|
| Ingest | `INGEST_FILE_VERSION(file_path)` | `file`, `file_version` | Documents + Ingestion dashboard |
| Extract | `EXTRACT(file_version_id, extractor_id)` | `extraction_run` + staging rows | Job progress; extraction report |
| Normalize/Link | `NORMALIZE / LINK` | canonical entities + link | Registers; early graphs |
| Build Facts | `BUILD_FACTS(project_id, builder_id, snapshot_id)` | `fact` + lineage | Coverage dashboard; fact explorer |
| Validate/Certify | `VALIDATE_FACTS + HUMAN_QUEUE` | validation_run; conflicts | Validation queue; conflict panels |
| Snapshot | `UPDATE_SNAPSHOT(project_id)` | snapshot sets | Snapshot selector in Chat |
| Chat | `coverage_check + fact_query` | read-only queries | Answer + Sources + Activity log |

---

## 5. Offline Architecture Overview

### Components
- **Windows Desktop UI**: workspace, ingestion dashboard, coverage dashboard, validation queue, fact explorer, chat with sources
- **Local Backend Service**: file registry/versioning, job queue/DAG, extractor runner, fact builder runner, validation engine, fact query API, LLM orchestrator
- **Storage**: SQLite (default) or local Postgres; optional DuckDB for analytics; optional vector index for discovery only (**not ground truth**)

### LLM Role (Strict)
> The LLM is a **query planner + narrator**. It must never answer from raw files, embeddings, or unstaged text. It may only retrieve information via a **whitelisted fact query interface** over Certified Facts and VALIDATED links.

---

## 6. Canonical Data Model

```
Evidence → Entities → Links → Facts
```

| Layer | Contents |
|-------|---------|
| Raw registry | Immutable file truth (`file` + `file_version`) |
| Extraction staging | Typed evidence tables (PDF blocks, XLSX cells, P6 activities, IFC entities) |
| Canonical entity | Normalized project objects (documents, schedule activities, BIM elements, equipment) |
| Crosswalk | Links with status gates (`CANDIDATE` / `VALIDATED` / `REJECTED`) |
| Fact | Typed computed statements with method/version, as-of snapshot, full lineage |

### Minimum Fact Record (Required Fields)
- `fact_type`, `subject_id`, `scope`, `snapshot_id`/`as_of`, `typed_value`, `units`
- `method_id` + `method_version`
- `status` (`CANDIDATE` / `VALIDATED` / `HUMAN_CERTIFIED`)
- Lineage pointers to evidence IDs and link IDs

---

## 7. Strict Chat Protocol

### Mandatory Sequence
1. Parse question → identify template and parameters
2. `coverage_check(template, snapshot, params)`
3. If **incomplete**: refuse + list missing fact/link types + propose required imports/jobs
4. If **complete**: retrieve facts/links via whitelisted API only
5. If **conflicts** exist: disclose both; if policy requires, refuse to choose
6. Respond: Answer + Evidence/Sources pointers; keep assumptions empty unless explicitly needed

---

## 8. Repo Structure + Implementation Pointers

> **Internal only. Do not copy into user-facing docs.**

| Path | Role |
|------|------|
| `run.py` | Boots desktop UI + initializes core app when project is opened |
| `src/core` | AppCore, config, DB manager, schema init, plugin registry |
| `src/document_processing` | Processors for PDF/DOCX/XLSX/images and utilities |
| `src/analysis_engine` | Entity/relationship/compliance analyzers and cross-document aggregation |
| `src/ui` | Dashboard, documents, facts, schedule, chat pages (Tkinter) |
| `models/` | Fast/deep local vision-capable model profiles (GGUF + projector) |

---

## 9. Open Questions / Resolution Queue

- [ ] Installation story must be singular — avoid mixing EXE installer, LM Studio manual steps, and 'automatic model download'
- [ ] Define certification policy per `fact_type` (what requires `HUMAN_CERTIFIED` vs automated `VALIDATED`)
- [ ] Decide default storage (SQLite vs Postgres) and when to expose advanced option in UI
- [ ] Define export formats for fact packs and compliance reports (PDF/CSV/JSON) and which are user-facing in MVP
- [ ] Clarify the boundary between compliance review assistance and any certification language across all docs
