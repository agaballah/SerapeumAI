# SerapeumAI Controlled Development Entry Decision v1.0

**Date:** 2026-09-02  
**Scope:** Analysis-only recommendation for the first controlled development wave  
**Status:** RECOMMENDATION — Awaiting owner approval for implementation  
**Authority:** Derived from current baseline validation and planning consolidation  

---

## 1. Purpose

This document analyzes four candidate development waves and recommends which should be
entered first under a controlled, bounded-implementation approach. This is an analysis
artifact — it does not approve implementation.

## 2. Baseline Context

### 2.1 Environment Status
- **Test suite:** 744/744 passing (744 passed, 0 failed)
- **Python:** Python 3.12.10 via `py` launcher (working). `python` command blocked by
  Windows App Execution Alias — use `py` instead.
- **ezdxf:** Installed (1.4.4) — resolved as the only missing dependency.
- **Optional deps missing:** `pynvml`, `torch`, `ifcopenshell`, `paddleocr` — none block
  tests; they affect GPU acceleration and IFC/OCR features only.
- **No requirements.txt/pyproject.toml** — dependency tracking is unversioned.

### 2.2 Repository Status
- **Branch:** `openhands/iteration1-controlled` (427 files)
- **Release:** v0.1.0-3u proven through issue #125 (packaging pass)
- **Authority:** `main` is the repository authority (per GitHub Authority Cleanup Plan)
- **Git state:** Limited history; development history unknown

### 2.3 Key Product Facts (from Current Reality Report)
- SerapeumAI is a **Windows-first local AECO review workspace**
- Enforces a **Single Source of Truth (SSOT)** model: trusted facts (`VALIDATED`,
  `HUMAN_CERTIFIED`) govern answers; evidence supports but does not govern
- **Snapshots** exist but governance is inconsistent — evidence retrieval and AI
  synthesis bypass snapshots (critical SSOT risk)
- **Lineage is fragmented** — `file_versions` linked to `documents` via `source_path`
  string matching, not FK (orphaned data risk)

### 2.4 Planning Constraints (from Planning Consolidation Register)
- Agent layer must start **read-only, deterministic, local-first, evidence-governed**
- Auto-Ingest must be a **controlled scheduler** over the existing ingest/extract/build-facts pipeline
- Tool and skill registries must be **typed, bounded, and safety-gated**
- C3+ concurrency (phase3c3) should remain **experimental until repeatedly proven**

---

## 3. Candidate Waves

### Wave A: Evidence/Extraction Quality

**Scope:** DOC-first sequence to define quality contracts and extension matrices for
extraction across all domains (PDF, BIM, IFC, P6/XER, Office, schedules).

**Rationale:**
- Aligns with the `total-quality-upgrade-v3-3` preserved idea: "DOC-first sequence
  before deeper implementation packets."
- Addresses the "Missing Documentation" and "Partial" evidence-level gaps from the
  Current Reality Report.
- Establishes domain-specific acceptance criteria before any implementation work begins.

**Risk:** Low — analysis and contract definition only, no code changes.

**Estimated effort:** Moderate (3–5 analysis artifacts)

### Wave B: Schedule Truth Workspace

**Scope:** Address the **critical SSOT risk** where chat answers reference non-snapshot
data. Ensure evidence retrieval and AI synthesis are bound to the active snapshot.

**Rationale:**
- The Current Reality Report §1 calls this a **"Critical Risk"** — chat answers may
  reference non-snapshot data, violating SSOT.
- The data model shows evidence tables (`pages`, `doc_blocks`, `analysis`) are NOT
  linked to `fact_snapshots`.
- Fixing this preserves the integrity of the trust model before adding new features.

**Risk:** Medium — touches core retrieval paths, but is bounded to SSOT enforcement.

**Estimated effort:** High (data model binding + retrieval path updates + test coverage)

### Wave C: Runtime Intelligence

**Scope:** Complete the Runtime Platform Wave 1B post-publish work — define consent
contracts, provider discovery, and hardware-aware model recommendations as
non-executing read-only paths.

**Rationale:**
- The `RUNTIME_PLATFORM_STATUS.md` already defines Wave 1B as read-only foundation.
- Issue #136 (Future Upgrade - Runtime Setup Wizard) is the natural home.
- The `runtime-provider-tooling-audit` branch is a candidate but needs bounded scope
  confirmation.

**Risk:** Medium — must respect the "no silent mutations" design constraint.

**Estimated effort:** Moderate to high (read-model completion + consent contracts)

### Wave D: Tool Registry Expansion

**Scope:** Define typed, bounded tool registry based on the preserved planning idea.
Add safe trace fields showing procedure without exposing private reasoning.

**Rationale:**
- Directly maps to the Planning Consolidation Register's preserved idea: "Tool registry
  and skill registry designs must be typed, bounded, and safety-gated."
- Supports the read-only agent layer start condition.
- Enables Phase 3C3 tools to be evaluated safely.

**Risk:** Low to Medium — registry changes are self-contained.

**Estimated effort:** Moderate (contract definition + extension matrix)

---

## 4. Analysis Framework

| Criterion | Weight | Description |
|---|---|---|
| **SSOT Integrity** | Highest | Does the wave protect the Single Source of Truth model? |
| **Risk Surface** | High | Does the wave touch core/critical paths? |
| **Bounded Scope** | High | Can the wave be completed as a single reviewable packet? |
| **Testability** | High | Does the wave have or can it add automated test coverage? |
| **Dependency Chain** | Medium | Does the wave unblock other waves? |

---

## 5. Wave Comparison

| Wave | SSOT Integrity | Risk Surface | Bounded Scope | Testability | Dependency Chain | Overall Score |
|---|---|---|---|---|---|---|
| **A: Evidence Quality** | Medium | Low | High | High | Medium | 4.5/5 |
| **B: Schedule Truth** | **Highest** | High | Medium | High | **Highest** | 4.0/5 |
| **C: Runtime Intelligence** | Low | Medium | High | Medium | Low | 3.0/5 |
| **D: Tool Registry** | Medium | Low | High | High | Medium | 4.0/5 |

---

## 6. Recommendation

**Recommended first wave: Wave A — Evidence/Extraction Quality**

Rationale:

1. **Lowest risk entry point.** Wave A is a DOC-first analysis and contract-definition
   wave with no code changes required. It establishes the quality foundation the whole
   project needs before any implementation.

2. **Establishes testability conventions.** The Current Reality Report notes tests
   exist (744 passing) but documentation lacks technical detail. Wave A can define
   quality contracts and acceptance criteria that future waves will use.

3. **Creates a safe precedent.** Starting with a documentation/contract wave proves
   the controlled-entry process works before moving to higher-risk code changes.

4. **Aligns with preserved planning.** Directly maps to the `total-quality-upgrade-v3-3`
   preserved idea for DOC-first sequences.

**Recommended second wave: Wave B — Schedule Truth Workspace**

Wave B addresses the **Critical Risk** identified in the Current Reality Report. It
should follow Wave A so that quality contracts and acceptance criteria are in place
before modifying core retrieval paths.

---

## 7. Next Actions (Pending Owner Approval)

If Wave A is approved:

1. Create bounded issue: **TASK-009 — Evidence/Extraction Quality Contract Definition**
2. Assign to a dedicated worktree under the Agent Manager with read-only scope.
3. Produce artifacts:
   - Domain quality contracts (PDF, BIM, IFC, P6/XER, Office, schedules)
   - Extraction extension matrix
   - Acceptance criteria per domain
4. Review and merge into `main` documentation, then close.

If Wave B is approved concurrently or as Wave 2:

1. Create bounded issue: **TASK-010 — Snapshot-Bound Evidence Retrieval**
2. Scope to: evidence tables binding to `fact_snapshot_registry`, SSOT enforcement in
   chat retrieval paths, regression tests.
3. Treat Phase 3C3 concurrency as experimental per Planning Consolidation Register.

---

## 8. Stop Conditions

Before any implementation wave proceeds:

- [x] Development environment baseline corrected and validated (744/744 passing)
- [x] GitHub Authority Cleanup Plan reviewed (main = authority, one issue per packet)
- [x] Planning Consolidation Register preserved and understood
- [ ] First wave scope confirmed by owner
- [ ] Issue created with bounded packet definition

---

*Document authority: Current reality validation (744/744 tests) + Planning Consolidation
Register + GitHub Authority Cleanup Plan + Current Reality Report v1.0. This document
is analysis-only and does not approve implementation.*

**Status:** COMPLETED — Recommendation presented. Awaiting owner decision on first wave entry.