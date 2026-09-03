# SerapeumAI Parked Plan Modernization v1.0

**Date:** 2026-09-03
**Type:** Strategic planning artifact — read-only modernization & reconciliation
**Scope:** Modernize all parked strategic plans against current repository reality, established evidence/quality findings, knowledge-coverage analysis, and the September 2026 evidence-first doctrine. No implementation, no dependency changes, no packaging changes.
**Constraint:** This document does not implement, install, build, commit, push, open PRs, change runtime models, or modify code/tests. It defines sequenced, gated future work — not implementation instructions.

---

## 1. Purpose

The SerapeumAI repository contains a body of parked planning artifacts accumulated across multiple iterations. The objective of this document is to:

1. Preserve the useful strategic direction already present in parked documents.
2. Correct obsolete assumptions where repository evidence or accepted findings contradict them.
3. Clearly separate **stable strategic intent** from **mutable live repository / project state**.
4. Define **sequenced, gated future work** — never implementation instructions.
5. Assign each technology candidate exactly one of: **ADOPT / TRIAL / DEFER / REJECT**.
6. Make explicit the dependencies, Windows/local-first/privacy-first/portable-packaging implications, and rollback concerns for any future implementation.
7. Preserve the evidence-first chain intact: **source → controlled extraction → evidence/provenance → structured facts → validation/certification where required → retrieval → local LLM answer**.

This document does **not** discard or wholesale replace existing parked plans. It modernizes them.

---

## 2. Document Boundaries

### 2.1 This Document Does

- Reconciles existing parked plans against current evidence.
- Ranks knowledge-impact priorities using the established coverage map, trust map, and expansion roadmap.
- Assigns single-status technology decisions (ADOPT/TRIAL/DEFER/REJECT).
- Sequences future work as gated packets, each gated by an explicit precondition.
- Separates stable intent from mutable state explicitly.

### 2.2 This Document Does NOT

- Implement code, tests, fixtures, dependencies, packaging, or build scripts.
- Modify `src/**`, `tests/**`, `requirements*`, `pyproject.toml`, `*.spec`, `build_portable.*`, or any packaging surface.
- Embed branch names, commit SHAs, test counts, active blockers, or release-readiness claims into stable strategy.
- Rewrite historical release / provenance evidence because HEAD differs.
- Replace the post-publish upgrade plan, planning consolidation register, evidence quality contract, or any existing parked artifact with a single broad plan.

### 2.3 Stable vs Mutable

| Class | Examples | Mutable? |
|---|---|---|
| **Stable strategic intent** | "SerapeumAI is Windows-first, local-first, AECO review workspace"; "evidence must precede narration"; "deterministic extraction before AI support"; "lab output never governs truth"; "human-in-the-loop certification required for formal claims"; "no silent internet, install, or model download" | **No** — strategy changes require a new decision artifact. |
| **Mutable live state** | Branch name, HEAD commit, current task ID, working-tree status, test counts, optional dependency availability, exact extractor maturity ratings, packaging artifact size | **Yes** — changes between reads. Never embedded as strategy. |

This document's stable sections intentionally avoid mutable values; live state is referenced via the stable strategic plan numbers (e.g., Upgrade 5), not via branches or commits.

---

## 3. Foundational Authority (Stable)

The following established artifacts remain authoritative and are not modified by this modernization:

- **Post-Publish Upgrade Plan** (`docs/internal/POST_PUBLISH_UPGRADE_PLAN.md`) — the master numbered roadmap.
- **Evidence Quality Contract** (`docs/internal/SERAPEUMAI_EVIDENCE_QUALITY_CONTRACT_v1.0.md`) — defines what counts as valid evidence.
- **Evidence Quality Baseline** (`docs/internal/SERAPEUMAI_EVIDENCE_QUALITY_BASELINE_v1.0.md`) — current extractor maturity ratings.
- **Gold Fixture Framework + Implementation Plan** (`docs/internal/SERAPEUMAI_GOLD_FIXTURE_FRAMEWORK_v1.0.md` + `_IMPLEMENTATION_PLAN_v1.0.md`) — defines acceptance fixtures.
- **Information Quality / Database Trust Map** (`docs/internal/SERAPEUMAI_INFORMATION_QUALITY_DATABASE_TRUST_MAP_v1.0.md`) — engineer answer trust levels.
- **Knowledge Coverage Map** (`docs/internal/SERAPEUMAI_KNOWLEDGE_COVERAGE_MAP_v1.0.md`) — engineer question catalogue.
- **Knowledge Expansion Roadmap** (`docs/internal/SERAPEUMAI_KNOWLEDGE_EXPANSION_ROADMAP_v1.0.md`) — value-based prioritization.
- **Historical Plan Knowledge-Impact Reconciliation** (`docs/internal/SERAPEUMAI_HISTORICAL_PLAN_KNOWLEDGE_IMPACT_RECONCILIATION_v1.0.md`) — earlier reconciliation matrix.
- **Publish Truth Statement** (`docs/internal/PUBLISH_TRUTH_STATEMENT.md`) — release-candidate truth.
- **Planning Consolidation Register** (`docs/internal/PLANNING_CONSOLIDATION_REGISTER.md`) — preserved ideas from stale planning branches.

This document does **not** override those artifacts. It modernizes the **parked** plans listed in §5 against them.

---

## 4. Evidence-First Chain (Stable Doctrine)

Every modernization action must preserve the chain:

```text
Source File
    → Controlled Extraction (BaseExtractor, Evidence Quality Contract §2-§8)
    → Evidence + Provenance (typed record, deterministic, lineage-bound)
    → Structured Facts (FactRepository, status: CANDIDATE → VALIDATED → HUMAN_CERTIFIED)
    → Validation / Certification (RuleRunner + governance gate)
    → Retrieval (project-scoped, snapshot-aware)
    → Local LLM Answer (narrator only; never computes, certifies, or invents truth)
```

**Lab output and AI narration never enter this chain as governing facts.** They may appear as support lanes only, and must be visually separable from governing facts.

This chain is stable across all parked plans. Any parked plan that implies bypassing this chain (e.g., memory as certified truth, LLM arithmetic, mock IR/NCR data) is **retired or corrected**.

---

## 5. Historical-Plan Inventory & Reconciliation Matrix

Each row identifies an existing parked artifact, the disposition, the reason, and which knowledge/coverage domain it touches. Disposition values:

- **RETAIN** — file remains authoritative as-is; no changes needed.
- **MODERNIZE** — file remains authoritative; targeted edits update priority/status/gates to align with September 2026 findings.
- **RETIRE-AS-PARKED** — file's content is preserved; its prior "live" status is removed; superseded by a more current parked or authoritative artifact. File stays on disk as historical record.
- **SUPERSEDE-NEW** — narrow new strategic plan introduced because this gap is uncovered by all existing parked plans.

| # | Existing Document | Disposition | Reason | Knowledge / Coverage Domain |
|---|---|---|---|---|
| 1 | `POST_PUBLISH_UPGRADE_PLAN.md` | **MODERNIZE** | Master upgrade roadmap; numbering is the stable reference. Modernize Upgrade 5 priority elevation (P1-consideration), insert CAD packet reference, insert BIM/field refinement notes, and add technology decision cross-reference. | All — strategic umbrella |
| 2 | `PLANNING_CONSOLIDATION_REGISTER.md` | **RETAIN** | Stable register of preserved ideas from stale planning branches; not implementation authority. | Process / governance |
| 3 | `GITHUB_AUTHORITY_CLEANUP_PLAN.md` | **RETAIN** | Branch/issue hygiene; rules remain valid and orthogonal to engineering content. | Process / governance |
| 4 | `PUBLISH_TRUTH_STATEMENT.md` | **RETAIN** | Release-candidate truth statement; do not rewrite because HEAD differs (rule explicitly forbidden). | Release authority |
| 5 | `RUNTIME_PLATFORM_STATUS.md` | **MODERNIZE** | Add cross-reference to ADOPT/DEFER technology decisions for runtime lane (Upgrade 1, 1C, 7, Runtime Platform Wave). Preserve all non-enabled behavior language. | Local runtime / model selection |
| 6 | `RUNTIME_DISTRIBUTION_CONSENT_MATRIX.md` | **MODERNIZE** | Align consent category language with Upgrade 1/7/Runtime Platform Wave tech decisions; preserve non-negotiables. | Distribution / consent |
| 7 | `SERAPEUMAI_EVIDENCE_QUALITY_CONTRACT_v1.0.md` | **RETAIN** | Authoritative extractor contract; do not rewrite. | Extractor contract |
| 8 | `SERAPEUMAI_EVIDENCE_QUALITY_BASELINE_v1.0.md` | **RETAIN** | Authoritative maturity ratings. | Extractor maturity |
| 9 | `SERAPEUMAI_EVIDENCE_PIPELINE_GOVERNANCE_GAP_REPORT_v1.0.md` | **RETAIN** | Authoritative gap analysis; cited by Evidence Quality Contract. | Governance |
| 10 | `SERAPEUMAI_EVIDENCE_AUTHORITY_BOUNDARY_DESIGN_v1.0.md` | **RETAIN** | Authority boundary design; cited by governance gate. | Governance |
| 11 | `SERAPEUMAI_EVIDENCE_TRUST_INTEGRATION_VALIDATION_v1.0.md` | **MODERNIZE** | Cross-link the evidence-first chain; preserve validation tables. | Trust integration |
| 12 | `SERAPEUMAI_EVIDENCE_TRUST_REGRESSION_BASELINE_v1.0.md` | **RETAIN** | Regression baseline snapshot; do not rewrite because HEAD differs. | Regression baseline |
| 13 | `SERAPEUMAI_GOLD_FIXTURE_FRAMEWORK_v1.0.md` | **RETAIN** | Authoritative fixture framework; cited by all fixture validations. | Fixture framework |
| 14 | `SERAPEUMAI_GOLD_FIXTURE_IMPLEMENTATION_PLAN_v1.0.md` | **MODERNIZE** | Insert CAD, vision/OCR, and field fixture placeholders that are gated by the new CAD plan and Upgrade 5 lab. Do not change existing PDF/P6/IFC/Office/Excel sections. | Fixture implementation |
| 15 | `SERAPEUMAI_PDF_GOLD_FIXTURE_VALIDATION_v1.0.md` | **RETAIN** | Domain-specific fixture validation. | PDF |
| 16 | `SERAPEUMAI_P6_GOLD_FIXTURE_VALIDATION_v1.0.md` | **RETAIN** | Domain-specific fixture validation. | P6/XER |
| 17 | `SERAPEUMAI_IFC_GOLD_FIXTURE_VALIDATION_v1.0.md` | **MODERNIZE** | Add P2 BIM-semantic enhancement cross-reference; preserve existing dependency-honesty validation. | IFC/BIM |
| 18 | `SERAPEUMAI_OFFICE_GOLD_FIXTURE_VALIDATION_v1.0.md` | **RETAIN** | Domain-specific fixture validation. | Word / PPTX |
| 19 | `SERAPEUMAI_EXCEL_GOLD_FIXTURE_VALIDATION_v1.0.md` | **MODERNIZE** | Insert structured-table P3 cross-reference; preserve current register coverage. | XLSX |
| 20 | `SERAPEUMAI_KNOWLEDGE_COVERAGE_MAP_v1.0.md` | **RETAIN** | Authoritative engineer question catalogue and coverage matrix. | Coverage baseline |
| 21 | `SERAPEUMAI_INFORMATION_QUALITY_DATABASE_TRUST_MAP_v1.0.md` | **RETAIN** | Authoritative trust map and engineer question test. | Trust baseline |
| 22 | `SERAPEUMAI_KNOWLEDGE_EXPANSION_ROADMAP_v1.0.md` | **RETAIN** | Authoritative value-based prioritization matrix (CAD #1, Visual #2). | Expansion priority |
| 23 | `SERAPEUMAI_HISTORICAL_PLAN_KNOWLEDGE_IMPACT_RECONCILIATION_v1.0.md` | **MODERNIZE** | Update the inventory table to reference this v1.0 document; insert new CAD plan reference; insert field-data validation gate. | Reconciliation |
| 24 | `SERAPEUMAI_DEVELOPMENT_ENVIRONMENT_HEALTH_REPORT_v1.0.md` | **RETAIN** | Local environment snapshot; mutable but cited as authoritative for its date. | Environment |
| 25 | `SERAPEUMAI_DEVELOPMENT_ENVIRONMENT_VALIDATION_RESULT_v1.0.md` | **RETAIN** | Local environment validation result. | Environment |
| 26 | `SERAPEUMAI_CONTROLLED_DEVELOPMENT_ENTRY_DECISION_v1.0.md` | **RETAIN** | Authoritative entry decision; cited by Manager bootstrap. | Process |
| 27 | `TEST_ENVIRONMENT_BASELINE.md` | **RETAIN** | Older baseline explicitly superseded in spirit by Health Report; preserved as historical record. | Environment (historical) |
| 28 | `DEVELOPER_TEST_BOOTSTRAP.md` | **RETAIN** | Test reporting lane definitions. | Test process |

**Summary (count proof):**

- **RETAIN: 20** (rows 2, 3, 4, 7, 8, 9, 10, 12, 13, 15, 16, 18, 20, 21, 22, 24, 25, 26, 27, 28).
- **MODERNIZE: 8** (rows 1, 5, 6, 11, 14, 17, 19, 23).
- **RETIRE-AS-PARKED: 0**.
- **SUPERSEDE-NEW: 0** within the historical 28-file corpus.
- **Total rows in matrix: 28** (matching the 28 historical `.md` files under `docs/internal/` that existed before TASK-028).
- **New files created by TASK-028 locally: 2** — this document (`SERAPEUMAI_PARKED_PLAN_MODERNIZATION_v1.0.md`) and the narrowly scoped CAD plan (`SERAPEUMAI_CAD_DRAWING_INTELLIGENCE_PLAN_v1.0.md`, per the CAD rule in §7).
- **Total `docs/internal/*.md` files after TASK-028: 30** (28 historical + 2 new).
- **GitHub PR #158 impact:** PR #158 introduces **7 complete new-file additions** (the 2 new plans above plus 5 previously-untracked `docs/internal/*.md` files that were created in prior task cycles but committed to the repo via this PR) and **3 incremental modifications** to existing tracked files (`POST_PUBLISH_UPGRADE_PLAN.md`, `RUNTIME_DISTRIBUTION_CONSENT_MATRIX.md`, `RUNTIME_PLATFORM_STATUS.md`). This distinction is relevant when reviewing merge impact on `main`: the PR carries 10 file changes total (7 new + 3 modified), not merely 2 new files.

Arithmetic check: 20 + 8 + 0 + 0 = 28 historical rows. 28 + 2 new = 30 total `docs/internal/*.md` files.

---

## 6. Coverage Reconciliation into Existing Plans

The September 2026 findings identify two uncovered P1 gaps and two uncovered P2 gaps. Each is reconciled into an existing parked plan; no new umbrella plan is created beyond the narrow CAD plan permitted by the CAD rule.

### 6.1 P1 — CAD Drawing Intelligence (DWG/DXF)

- **Existing coverage:** Gold Fixture Implementation Plan (item 14) and Post-Publish Upgrade Plan Upgrade 3 mention "images/drawings" only in passing. No dedicated CAD extraction plan exists.
- **Reconciliation:** Per the CAD rule, create the new narrow strategic plan `SERAPEUMAI_CAD_DRAWING_INTELLIGENCE_PLAN_v1.0.md` (see §7). Cross-reference it from:
  - Post-Publish Upgrade Plan Upgrade 3 (evidence baseline) — single line linking the new plan.
  - Gold Fixture Implementation Plan — placeholder fixture design tied to the new plan's validation gate.
  - Historical Plan Reconciliation — single row referencing the new plan.
- **Coverage:** Layer 2/3 (evidence), Layer 5 (fact-building) for geometry-poor subset.

### 6.2 P1 — Visual / Scanned Evidence (Images / Scans)

- **Existing coverage:** Post-Publish Upgrade Plan Upgrade 5 (`Optional OCR / Layout / Vision Lab`) and Gold Fixture Implementation Plan mention "gold drawing/image" fixture.
- **Reconciliation:** Modernize Upgrade 5 to elevate its **strategic priority** from "optional" to **P1-consideration gated by lab validation**. No new plan created. Lab framing (non-governing output, deterministic baseline primary) is preserved and reinforced as the gate.
- **Coverage:** Layer 2 (evidence) via lab lane, **non-governing** until acceptance criteria from Gold Fixture Framework are met.

### 6.3 P2 — BIM Semantic Intelligence

- **Existing coverage:** Post-Publish Upgrade Plan Upgrade 6 (`Safe Revit Bridge`) and the IFC Gold Fixture Validation document.
- **Reconciliation:** Modernize Upgrade 6 priority from long-term to **P2 consideration** gated by Revit API licensing/deployment research outcome and IFC baseline solidification. Modernize the IFC fixture validation document to reference Upgrade 6 as the future path. Geometry remains an explicit accepted limitation until Upgrade 6 or an IfcOpenShell geometry-extension is researched and approved.
- **Coverage:** Layer 2/3 (evidence), Layer 5 (fact-building) for property-filtered queries.

### 6.4 P2 — Real Field Inspection Evidence (IR/NCR)

- **Existing coverage:** Evidence Quality Contract §14.6 explicitly marks `FieldExtractor` as PLACEHOLDER with strict registration rules. Governance gate blocks fabricated output.
- **Reconciliation:** No new plan is created (the "field inspection plan" is intentionally deferred per Historical Reconciliation §6.4). Modernize the Historical Reconciliation document to reference an explicit **field-data validation gate** before any future field plan is added: methodology must pass the Evidence Quality Contract and the existing 8-test suite for certification.
- **Coverage:** Layer 2 (evidence) — currently **blocked**, not retired.

### 6.5 Supporting — Structured Document / Table / Layout Intelligence

- **Existing coverage:** Post-Publish Upgrade Plan Upgrade 3 (PDF table loss) and Excel Gold Fixture Validation (heuristic header detection).
- **Reconciliation:** P3 priority is preserved as **deferrable**. No new plan created. Modernize the Excel fixture validation document with a single cross-reference to the Knowledge Expansion Roadmap P3 rationale.

### 6.6 Supporting — Document Control / Workflow Intelligence

- **Existing coverage:** Post-Publish Upgrade Plan Upgrade 4 (Document Center / File Inspector) and Historical Reconciliation §6.2.
- **Reconciliation:** P3 priority is preserved. No new plan created. Upgrade 4 remains a UI/verification refinement, not a knowledge-expansion packet.

---

## 7. CAD Rule Application & New Plan Decision

The CAD rule requires either (a) modernizing an existing dedicated CAD/DWG/DXF plan if one exists, or (b) creating a narrowly scoped new strategic CAD Drawing Intelligence plan if no such plan exists.

**Decision:** No existing dedicated CAD/DWG/DXF plan exists. All existing references are indirect:
- Post-Publish Upgrade Plan Upgrade 3 mentions "images/drawings" inside a generic OCR/vision bullet.
- Gold Fixture Implementation Plan includes "gold drawing/image" in the acceptance-fixture list.
- Historical Reconciliation flags CAD as the highest-impact uncovered gap.

Therefore, **a new narrowly scoped strategic plan is created**: `docs/internal/SERAPEUMAI_CAD_DRAWING_INTELLIGENCE_PLAN_v1.0.md`.

**Narrow scope constraints:**
- Covers CAD/DWG/DXF only. Does not include image OCR, scanned-PDF OCR, or photo VLM (those remain in Upgrade 5 lab).
- Does not include BIM geometry (Remains Upgrade 6 / P2).
- Does not include cost/schedule/BOM (not in scope of any current plan).
- Defines gates; contains no implementation instructions.

---

## 8. Technology Candidates — Single Status Assignment

Each candidate gets exactly one status. Status changes require a new decision artifact.

**TASK-028 non-authorization statement:** This document does **not** authorize any new dependency, provider behavior, runtime provisioning, packaging inclusion, or production deployment. ADOPT status is reserved for capability that is already admitted and already shipped under the existing doctrine.

**Adoption discipline and the production-vs-strategic boundary:**

ADOPT status means one of two strictly bounded cases:

- **(a) Existing previously accepted capability retained in strategy:** the candidate is already present in the repository or in the admitted dependency baseline, and the strategy merely confirms what is already permitted.
- **(b) Future technology / dependency / behavior not admitted to production:** the candidate is a strategic target only. It may not be added, installed, downloaded, configured, or wired into production without a separate owner-approved bounded packet passing the gate sequence in §9 and the dependency-admission review in `RUNTIME_DISTRIBUTION_CONSENT_MATRIX.md`. Candidates in this class must NOT carry ADOPT status — they must carry TRIAL, DEFER, or REJECT.

**Repository-evidence check for current ADOPT candidates (final table below):**

| Candidate | Class | Repository evidence | Verdict |
|---|---|---|---|
| T17 — small local ONNX embeddings/reranker | (b) | **Historical snapshot evidence** (dated 2026-09-02): None in this checkout. `SERAPEUMAI_DEVELOPMENT_ENVIRONMENT_HEALTH_REPORT_v1.0.md` §2.4 does not list any ONNX embeddings package at that date. This classification is a dated validation observation, not a settled fact for all future checkouts. | **Not ADOPT-eligible.** Reclassified to TRIAL in the final table. |
| T18 — GGUF + llama.cpp baseline runtime | (a) | **Historical snapshot evidence** (dated 2026-09-02): `llama_cpp_python 0.3.30` installed per environment health report §2.4. Present in this checkout at this date; subject to change in future environments or after dependency upgrades. | **ADOPT-eligible.** Already admitted; strategy retains what is permitted. No packaging validation gate has been executed for this dependency in TASK-028. |
| T19 — LM Studio / Ollama / OpenAI-compatible providers | (a) | Provider discovery implemented per `RUNTIME_PLATFORM_STATUS.md`; `PUBLISH_TRUTH_STATEMENT.md` §5 lists runtime provisioning, download, and control as explicit non-enabled behavior. Note: "OpenAI-compatible" refers only to endpoints explicitly configured in the local runtime; it does **not** imply all OpenAI-compatible services are local or permitted. | **ADOPT-eligible** as read-model only. Active provisioning remains REJECTED. Non-local endpoints require explicit user consent and owner-approved optional-lane policy. |

**Final technology-status assignments (single status per candidate; corrected from the original draft):**

| # | Candidate | Status | Rationale (with boundary distinction) |
|---|---|---|---|
| T1 | **ezdxf** for deterministic DXF extraction | **TRIAL** | Class (b). **Historical snapshot evidence** (dated 2026-09-02): Library 1.4.4 installed per env report §2.4, but no registered V02 extractor exists. Not admitted to production. Bounded validation gate against Gold Fixture Framework required. |
| T2 | **DWG paths requiring fidelity** (LibreDWG, ODA, proprietary SDK) | **DEFER** | Class (b). No repository evidence. Licensing/packaging research required. |
| T3 | **Docling** (IBM) | **TRIAL** | Class (b). No repository evidence of admission. License-admission review required before any packaging. |
| T4 | **PaddleOCR / PaddleOCR-VL** | **TRIAL** | Class (b). **Historical snapshot evidence** (dated 2026-09-02): Not installed per env report §2.4. Lab-only. |
| T5 | **Tesseract via pytesseract** | **TRIAL** | Class (b). **Historical snapshot evidence** (dated 2026-09-02): Library `pytesseract 0.3.13` installed per env report §2.4, but not wired into a registered extractor and engineering-trust acceptance threshold is unproven (Knowledge Coverage Map §2.8). Lab-only. |
| T6 | **IfcOpenShell (deeper semantic extraction)** | **TRIAL** | Class (b). **Historical snapshot evidence** (dated 2026-09-02): Geometry extension; `ifcopenshell` not installed in this env per env report §2.4. Existing IFCExtractor uses it conditionally. |
| T7 | **Read-only-first Revit bridge** | **DEFER** | Class (b). No repository evidence. Owner-approved research packet required. |
| T8 | **Deterministic schedule parsing / CPM / validation** | **TRIAL** | Class (b). Future hardening of existing P6Extractor heuristic; pure-Python. |
| T9 | **Bounded typed tools; MCP only as possible protocol** | **TRIAL** | Class (b). MCP explicitly excluded from baseline per Upgrade 1B. |
| T10 | **Dynamic hardware → benchmark → model recommendation** | **DEFER** | Class (b). Read-model only per PUBLISH_TRUTH_STATEMENT §5. |
| T11 | **Mock / fabricated IR/NCR data** | **REJECT** | Forbidden pattern. Evidence Quality Contract §14.6. |
| T12 | **MCP as a baseline execution protocol** | **REJECT** | Forbidden by Upgrade 1B and doctrine. |
| T13 | **Cloud-required OCR / VLM / foundation APIs as default** | **REJECT** | Doctrine conflict. |
| T14 | **Runtime provider provisioning actions** | **REJECT (in baseline)** | Explicit non-enabled behavior per PUBLISH_TRUTH_STATEMENT §5. |
| T15 | **PaddlePaddle / paddlepaddle GPU runtime** | **DEFER** | Class (b). Native GPU blob. Packaging hostile. |
| T16 | **TensorRT / TensorRT-LLM / AWQ / GPTQ / EXL2** | **DEFER** | Class (b). Workstation-experimental. Forbidden in baseline per Upgrade 1C. |
| T17 | **Embeddings/reranker small local ONNX** | **TRIAL** (reclassified from ADOPT) | Class (b). No repository evidence of acceptance. Requires dependency-admission review before any baseline integration. |
| T18 | **GGUF + llama.cpp baseline runtime** | **ADOPT (optional lane, already admitted)** | Class (a). `llama_cpp_python 0.3.30` installed per env report §2.4. Strategy retains what is already permitted; no new admission. |
| T19 | **LM Studio / Ollama / OpenAI-compatible providers** | **ADOPT (optional lane, read-model, already admitted)** | Class (a). Provider discovery already implemented; active provisioning remains REJECTED per PUBLISH_TRUTH_STATEMENT §5. |

**Status totals (final):** ADOPT (2) · TRIAL (8) · DEFER (5) · REJECT (4). All 19 candidates accounted for exactly once.

**Adoption discipline:**
- ADOPT status means the candidate is admitted to the optional lane under its existing-admitted scope. It does **not** mean the candidate is admitted to production baseline, and it does **not** authorize any new dependency, provider behavior, runtime provisioning, packaging inclusion, or production deployment.
- TRIAL status means the candidate may be benchmarked under the Upgrade 5 Lab rules or an equivalent bounded lab; output is **non-governing** and clearly labeled. Admittance to production requires Evidence Quality Contract §12 acceptance + dependency-admission review.
- DEFER status means no current work; a future bounded research packet may reclassify.
- REJECT status means the candidate is forbidden in baseline; any re-introduction requires a new decision artifact.

---

## 9. Sequenced Gated Future Work (Not Implementation)

The future work is expressed as **gated packets**, not implementation tasks. Each packet's named prerequisite gates must pass before that packet opens. Independent approved research lanes may proceed in parallel. No implementation may bypass its own named gates.

### 9.1 Parallel Research Lanes

Three independent research lanes are recognized. They share only the foundational gates (G0, G2) and may proceed in parallel after those pass:

- **Lane C — CAD Drawing Intelligence** (DXF first, DWG-path research parallel). DXF progression (G3 → G4 → G8) is independent of the DWG-path decision (G5); the DWG-path decision does not gate DXF acceptance. The two may reach their own future acceptance gates independently.
- **Lane V — Visual / Scanned Evidence** (G6 → G7 → G8). Independent of Lane C; may reach its own future acceptance gate without Lane C progress.
- **Lane F — Real Field Inspection Evidence** (G12). Independent research lane for IR/NCR methodology.

The **CAD Evidence Baseline** (G8) is the integration point where Lane C and Lane V outputs become **eligible for bounded integration/promotion**. Passage through G8 does not itself admit output to governing status; governing authority still requires the Evidence Quality Contract, applicable promotion rules, and explicit Owner authorization. Lane F joins the integration only after its own validation gate is passed.

### 9.2 Gate Sequence (Linked to Post-Publish Upgrade Plan Numbering)

| Gate | Packet | Type | Named Gating Prerequisites | Owner Decision Required |
|---|---|---|---|---|
| G0 | **Publish Closure** | Release | Existing publish-closure rail remains green; no publish defect hidden behind upgrades. | Owner publish decision. |
| G1 | **PP-001 GitHub Authority Cleanup** | Process | G0. | Owner. |
| G2 | **Upgrade 2 — Workspace Honesty (completion)** | Foundational | G0. Required before any new knowledge-domain domain enters. | Owner. |
| G3 | **Lane C — CAD Packet A — Deterministic DXF Extraction (TRIAL ezdxf)** | Lab | G0; G2; ezdxf license-admission review passed. New `SERAPEUMAI_CAD_DRAWING_INTELLIGENCE_PLAN_v1.0.md` defines lab scope; output is **non-governing** and labeled support. | Owner + admission-review outcome. |
| G4 | **Lane C — CAD Packet B — Gold Fixtures for CAD** | Fixture | G3 demonstrates repeatable deterministic output on canonical DXF fixtures. | Owner. |
| G5 | **Lane C — CAD Packet C — DWG Path Decision** | Research | G0; G2; may proceed in parallel with G3/G4; decision matrix between LibreDWG / ODA / proprietary / hybrid; reclassification of T2 required. | Owner. |
| G6 | **Lane V — Upgrade 5 OCR / Layout / Vision Lab (P1-consideration elevation)** | Lab | G0; G2. Docling, PaddleOCR, Tesseract remain TRIAL. Lab framing preserved. | Owner. |
| G7 | **Lane V — Upgrade 3 Visual Evidence Fixtures** | Fixture | G6 demonstrates acceptance threshold for site-photo and scanned-drawing OCR. | Owner. |
| G8 | **Integration — CAD + Visual Evidence Baseline (post-fixture)** | Baseline | G4; G7. Promotes verified CAD and verified Vision extracts from CANDIDATE-only to VALIDATED-eligible. G5 is **not** a prerequisite — DWG-path decision may remain open while DXF and Vision reach their own acceptance gates. Requires Evidence Quality Contract §12 acceptance criteria met. | Owner. |
| G9 | **Schedule Truth Workspace hardening (CPM validation, T8)** | Truth | G0. Pure-Python bounded validation against Gold Fixture Framework. | Owner. |
| G10 | **Upgrade 6 — Safe Revit Bridge (research)** | Research | G0; IFC baseline solid. Revit API deployment / licensing research packet required. | Owner. |
| G11 | **Upgrade 6 — BIM Semantic Enhancement (TRIAL IfcOpenShell extension)** | Lab | G10. Geometry extension is TRIAL; never auto-promoted. | Owner. |
| G12 | **Lane F — Field Inspection (P2) Validation Gate** | Research | G0; lab methodology research demonstrates non-fabricated IR/NCR extraction that passes Evidence Quality Contract §14.6. Rejects mock data (T11). | Owner. |
| G13 | **Upgrade 1 — Smarter Local Intelligence** | Deferred-Optional | G8. Model improvement only after P1 knowledge is sufficient. | Owner. |
| G14 | **Upgrade 1B — Tool-Using Chat** | Optional | G0; G2. Typed tool registry, MCP explicitly forbidden (T12). | Owner. |
| G15 | **Upgrade 1C — Quantization** | Optional | G13. GGUF baseline; workstation lanes deferred. | Owner. |
| G16 | **Upgrade 4 — Document Center / File Inspector** | UI | G0. UI/verification refinement, not knowledge. | Owner. |
| G17 | **Upgrade 7 — Optional Acceleration / Ecosystem Lanes** | Optional | G13. Read-model only. | Owner. |
| G18 | **Runtime Platform Wave (active provisioning)** | Blocked | G17. T14 (active provisioning) remains REJECTED in baseline. | Owner. |

### 9.3 Gating Principle

- **Only the named prerequisite gates for a packet must pass;** independent approved research lanes may proceed in parallel.
- **Every packet requires explicit owner approval** before opening, regardless of which lane it belongs to.
- **G8 integrates Lane C (DXF) and Lane V outputs** but does not require Lane C's DWG-path decision (G5) or Lane F's validation gate (G12). DWG, Vision, and Field Inspection may each reach their own future acceptance gates independently.
- No implementation, dependency admission, or runtime provisioning may occur under any packet without first passing all named prerequisite gates **and** receiving owner authorization for that packet.

---

## 10. Windows / Local-First / Privacy-First / Portable-Packaging Implications

Any future implementation touching the following must preserve each property:

- **Windows-first:** All packaging must remain Windows-portable (SerapeumAI_Portable.spec, build_portable.ps1, build_portable.bat untouched). No POSIX-only assumptions.
- **Local-first:** No network calls in baseline runtime. Lab lanes may simulate network but must be clearly non-governing.
- **Privacy-first:** Project data never leaves the machine in baseline. Optional lanes for LM Studio and Ollama operate on locally configured endpoints only; OpenAI-compatible providers refer to explicitly configured local endpoints — any non-local endpoint remains outside baseline and requires explicit user consent and owner-approved optional-lane policy.
- **Portable-packaging:** No silent dependency upgrades. No native blobs added without owner-approved admission review (RUNTIME_DISTRIBUTION_CONSENT_MATRIX.md).

**TASK-028 non-authorization statement:** This document does **not** authorize any new dependency, provider behavior, runtime provisioning, packaging inclusion, or production deployment. The ADOPT (2) designations in §8 (T18, T19) refer to capability that is already admitted and already shipped under the existing doctrine; they do not constitute new approval. All other candidates remain TRIAL / DEFER / REJECT until a future bounded packet passes the gate sequence in §9.

Specific implications by technology status:

- **ADOPT T18 (GGUF + llama.cpp, already admitted)** — `llama_cpp_python` wheel exists in this checkout (dated 2026-09-02). Packaging portability has **not** been validated by TASK-028; any future integration requires a packaging validation gate. Already installed in this environment. No new admission.
- **ADOPT T19 (LM Studio / Ollama / OpenAI-compatible, already admitted read-model)** — Provider discovery is read-model only. "OpenAI-compatible" refers to endpoints explicitly configured in the local runtime; non-local endpoints remain outside baseline and require explicit user consent and owner-approved optional-lane policy. Active provisioning remains REJECTED.
- **TRIAL T17 (small local ONNX embeddings/reranker)** — No repository evidence of acceptance in this checkout (dated 2026-09-02). Reclassified from ADOPT because no evidence exists. Requires dependency-admission review before any baseline integration.
- **TRIAL ezdxf (T1)** — Wheel exists in this checkout (dated 2026-09-02). Windows-portability **not validated** by TASK-028; license admission required before baseline integration.
- **TRIAL Docling (T3)** — License review required; lab isolation prevents baseline packaging impact. Portability/licensing assertions are validation requirements, not settled facts.
- **TRIAL PaddleOCR (T4)** — Native/runtime packaging impact is unvalidated by TASK-028. Candidate remains lab-only. Windows and portable-packaging compatibility must pass a bounded validation/admission review before any baseline integration.
- **TRIAL Tesseract (T5)** — System-binary path; portability depends on external binary availability, not bundled.
- **TRIAL IfcOpenShell (T6)** — Dependency licensing and Windows/portable-packaging suitability require explicit admission and validation review before any baseline integration.
- **DEFER DWG paths (T2)** — licensing and packaging research required.
- **DEFER Revit bridge (T7)** — client distribution constraint; separate owner-approved research packet.
- **REJECT active provisioning (T14)** — privacy conflict if executed.

---

## 11. Rollback Concerns by Future Packet

| Packet | Rollback Concern | Mitigation |
|---|---|---|
| G3 — CAD ezdxf TRIAL | Lab-only; rollback is removing the lab extractor. | Keep TRIAL output non-governing. |
| G4 — CAD gold fixtures | If acceptance criteria prove unstable, rollback is removing fixtures. | Fixture framework requires legality + reproducibility before promotion. |
| G6 — Vision lab | Lab output must never govern truth. | Lab framing enforced; deterministic baseline remains primary. |
| G9 — Schedule CPM hardening | If CPM validation proves unstable, rollback is reverting to heuristic float-only. | Pure-Python; package-level rollback. |
| G11 — BIM semantic extension | If geometry extension corrupts IFC baseline, rollback is reverting to identity-only IFC. | Staging registry already split (Evidence Quality Contract §14.3). |
| G12 — Field validation | If validation fails, no field plan is added. | T11 (mock data) explicitly REJECTED. |
| G13 — Upgrade 1 model improvements | If model introduction breaks packaging, rollback is removing runtime profiles. | Runtime selection remains manifest-driven. |
| G14 — Upgrade 1B tool-using chat | If typed tools over-claim authority, rollback is reducing tool surface. | Tool registry contract forbids `can_govern_truth` for LLM-driven tools. |
| G18 — Runtime active provisioning | If active provisioning executed against doctrine, rollback requires disabling all provisioning actions. | T14 explicitly REJECTED in baseline; gated. |

---

## 12. Updated Technology & Priority Cross-Reference Table

This table maps the modernization conclusions back to existing parked plans.

| Modernization Conclusion | Cross-Reference |
|---|---|
| Upgrade 5 elevated to P1-consideration (gated by lab) | POST_PUBLISH_UPGRADE_PLAN.md §13 |
| Upgrade 6 accelerated to P2-consideration (gated by Revit API research) | POST_PUBLISH_UPGRADE_PLAN.md §14 |
| Upgrade 1 / 1C / 7 / Runtime Platform Wave remain deferred-optional | POST_PUBLISH_UPGRADE_PLAN.md §6, §8, §15, §16 |
| Gold Fixture Implementation Plan gains CAD + Vision fixture placeholders | SERAPEUMAI_GOLD_FIXTURE_IMPLEMENTATION_PLAN_v1.0.md |
| IFC Gold Fixture Validation gains Upgrade 6 cross-reference | SERAPEUMAI_IFC_GOLD_FIXTURE_VALIDATION_v1.0.md |
| Excel Gold Fixture Validation gains P3 structured-table cross-reference | SERAPEUMAI_EXCEL_GOLD_FIXTURE_VALIDATION_v1.0.md |
| Historical Reconciliation updated to include new CAD plan and field validation gate | SERAPEUMAI_HISTORICAL_PLAN_KNOWLEDGE_IMPACT_RECONCILIATION_v1.0.md |
| Runtime Platform Status gains ADOPT/DEFER cross-reference | RUNTIME_PLATFORM_STATUS.md |
| Runtime Distribution Consent Matrix gains tech-decision alignment | RUNTIME_DISTRIBUTION_CONSENT_MATRIX.md |
| Evidence Trust Integration Validation gains evidence-first chain restatement | SERAPEUMAI_EVIDENCE_TRUST_INTEGRATION_VALIDATION_v1.0.md |

---

## 13. Documentation Validation Performed (Lightweight)

- **Link consistency:** cross-references between parked documents are confirmed by file path; no path edits required.
- **No semantic rewriting:** historical release/provenance documents are NOT rewritten.
- **No branch/commit/test-count embedding:** no stable section embeds mutable state.
- **No implementation instructions:** all "future work" is expressed as gated packets with owner-decision prerequisites.
- **No technology status duplication:** each candidate appears exactly once in §8 with a single status.
- **Evidence-first chain preserved:** §4 restates the chain; chain integrity is a precondition for any gate in §9.

---

## 14. Remaining Ambiguities, Risks, Owner Decisions

These items cannot be resolved in this document; they require owner direction before any corresponding gate can open.

1. **CAD DWG path (T2 DEFER):** Which DWG strategy (LibreDWG / ODA / proprietary / hybrid) is acceptable given Windows-portable-packaging and license-admission constraints? Owner-approved research packet required.
2. **CAD lab boundary:** Should ezdxf TRIAL output ever be promoted to VALIDATED facts, or remain CANDIDATE-only and require human certification? Owner decision required.
3. **Vision lab acceptance threshold (T5 Tesseract, T4 PaddleOCR):** What OCR accuracy is "engineering-trustworthy" for site photos and scanned drawings? Owner decision required.
4. **Field validation gate (G12):** Which extraction methodology (VLM, structured forms, hybrid) is the correct research direction? Owner decision required.
5. **Upgrade 1 / 1C / 7 ordering (G13-G17):** Confirm optional-lane sequencing relative to G8 (knowledge-p1 baseline).
6. **DXF / DWG variant coverage:** Which DXF variants (AC1009 through AC1032) must the TRIAL extractor accept before VERIFIED promotion?
7. **BIM semantic extension scope (G11):** Confirm whether geometry coordinates (currently lost) become part of the same TRIAL packet or a separate research packet.
8. **CAD as VALIDATED vs CANDIDATE:** Even after Gold Fixture acceptance, should CAD facts require HUMAN_CERTIFIED for engineering decisions? Owner decision required.

---

## 15. Closing Statement

The SerapeumAI parked-plan corpus remains directionally sound. The September 2026 evidence-first doctrine, the Coverage/Trust/Expansion findings, and the Historical Reconciliation all point to the same conclusion: **the highest-impact engineering-knowledge expansion is CAD Drawing Intelligence (P1)**, with Visual / Scanned Evidence (P1), BIM Semantic Intelligence (P2), and Real Field Inspection Evidence (P2) following in priority order.

The original Post-Publish Upgrade Plan numbering remains the stable roadmap reference. This modernization:

- Preserves existing parked plans.
- Corrects Upgrade 5 priority from "optional" to "P1-consideration gated by lab".
- Accelerates Upgrade 6 to "P2-consideration gated by Revit API research".
- Introduces one narrowly scoped CAD Drawing Intelligence plan to fill the only remaining uncovered P1 gap.
- Assigns single ADOPT/TRIAL/DEFER/REJECT status to every technology candidate.
- Sequences future work as gated packets, not implementation.
- Keeps the evidence-first chain intact.

No code, dependency, packaging, build, commit, push, or PR action is implied or performed by this document.

---

## 16. TASK-029 Input — Live-State Separation Concern

A live-state separation concern was discovered during TASK-028 evidence inspection. It is recorded here **without remediation**; no fix is authorized in this document.

**Disposition:** TASK-029 must establish **Contract-v7 separation of stable governance from verified live state**, addressing this concern under the authority of `SerapeumAI_AI_Developer_Contract.md` Section I (Chain of Command — Manager / Owner). No implementation, file edit, runtime change, or governance-file change is authorized here.

---

*This document is a strategic planning artifact. It does not implement, install, build, commit, push, open PRs, or modify code/tests, governance files, or historical release/provenance artifacts. All gated future work requires explicit owner approval before opening.*