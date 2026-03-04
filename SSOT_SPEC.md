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
| **Canonical Entity** | Normalized real-world project object (the nodes of the Truth Graph) |
| **Crosswalk Link** | Explicit link between entities with **Confidence Tiers** |
| **Fact** | Computed statement bound to an as-of snapshot and a **Fact Domain** |
| **Truth Graph** | The project-wide knowledge graph tying all entities and links together |

---

## 2. Advanced Architectural Layers (Truth Engine v2)

### A) Link Confidence Tiers
To reduce human validation workload, links must be categorized by reliability:
- `AUTO_VALIDATED`: Deterministic mappings (e.g., matching unique IDs/codes).
- `HIGH_CONFIDENCE`: Strong NLP + metadata synergy (ready for machine use in some domains).
- `CANDIDATE`: Needs human validation via the Validation Queue.
- `REJECTED`: Explicitly invalidated links.

### B) Fact Domains
Facts are grouped into logical domains to manage state and coverage:
- `SCHEDULE`: Activity dates, float, critical path progress.
- `BIM`: Element inventory, geometry, property completeness.
- `DOC_CONTROL`: Revision states, superseded maps.
- `PROCUREMENT`: Submittal status, equipment approvals.
- `FIELD`: Installation, inspection, and test results.
- `RISK`: Cross-domain derived risks (e.g., Schedule vs. Procurement).

### C) The Truth Graph
The backbone of the system is a Project Knowledge Graph. Crosswalk links are the **edges** of this graph.
- **Traversal Reasoning**: Allows the engine to reason across systems (e.g., finding Drawings for a specific BIM Element linked to a Schedule Activity).

### D) Authority Policies
Security layer ensuring only authorized roles can certify certain truth domains:
- `SCHEDULE_FACTS`: Certified by `PLANNER`
- `BIM_FACTS`: Certified by `BIM_LEAD`
- `PROCUREMENT_FACTS`: Certified by `PROCUREMENT_MANAGER`

---

## 3. Scope, Out-of-Scope, and Red Lines
... (previous sections 2 and 3 remain logicially similar but are now v2-aware) ...

---

## 4. End-to-End Workflow

### Pipeline
```
Ingest → Extract → Normalize/Link (Tiers) → Build Facts (Domains) → Validate/Certify → Snapshot → Chat
```

| Stage | Job (backend) | DB Outputs | User-Visible Surface |
|-------|--------------|-----------|---------------------|
| Ingest | `INGEST_FILE_VERSION` | `file`, `file_version` | Ingestion dashboard |
| Extract | `EXTRACT` | evidence tables | Extraction report |
| Normalize/Link | `NORMALIZE / LINK` | `entity_nodes`, `entity_links` | Truth Map Visualization |
| Build Facts | `BUILD_FACTS` | `facts` (grouped by domain) | Coverage dashboard (per domain) |
| Validate/Certify | `VALIDATE + HUMAN_QUEUE` | `certifications` | Validation queue (CANDIDATE prioritized) |
| Snapshot | `UPDATE_SNAPSHOT` | snapshot sets | Snapshot selector |
| Chat | `router + coverage + query` | answers from truth | Answer + Sources + Truth Map |

---

## 5. Offline Architecture Overview
... (same components as v1.2) ...

### LLM Role: The Template Router
The LLM acts as a **Template Router**. 
1. Natural Language question ↓
2. **Router** selects matching Fact Templates.
3. System performs `coverage_check` on those templates.
4. Response is generated based on retrieved certified facts.

---

## 6. Canonical Data Model

### Truth Graph Schema
- `entity_nodes`: `(id, project_id, type, value, metadata)`
- `entity_links`: `(id, project_id, from_id, to_id, rel_type, confidence_tier)`

### Facts with Domains
- `facts`: `(fact_id, domain, fact_type, subject_id, status, authority_role, ...)`

---

## 7. Strict Chat Protocol (v2)

### Mandatory Sequence
1. **Route**: Parse question → identify set of Fact Templates via Template Router.
2. **Check**: `coverage_check(templates, snapshot, params)` across Fact Domains.
3. **Refuse**: If incomplete, list missing requirements.
4. **Retrieve**: Query Facts + traverse Truth Graph for evidence map.
5. **Narrate**: Answer + Evidence + Truth Map visualization pointer.

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
