# SerapeumAI Historical Plan vs Knowledge Impact Reconciliation v1.0

**Date:** 2026-09-02  
**Type:** Strategic Reconciliation — Read-Only Analysis  
**Purpose:** Do existing plans still address the highest-value engineering knowledge problems?  
**Constraint:** No code changes. No implementation decisions. Analysis only.

**Modernization note (2026-09-03):** Per `SERAPEUMAI_PARKED_PLAN_MODERNIZATION_v1.0.md`:
- The previously missing **CAD Drawing Intelligence plan** has been created: `SERAPEUMAI_CAD_DRAWING_INTELLIGENCE_PLAN_v1.0.md` (narrowly scoped, P1).
- **Field Inspection Records (P2)** are gated by an explicit **field-data validation gate** (Modernization §9 Gate G12). Mock/filename-based fabrication remains REJECTED (Technology T11).
- Upgrade 5 elevated from "optional" to "P1-consideration gated by lab".
- Upgrade 6 accelerated from "long-term" to "P2-consideration gated by Revit API research".

This document's conclusions remain valid; the modernization note adds the missing CAD plan reference and the field validation gate.

---

## 1. Existing Plan Inventory

### 1.1 Post-Publish Upgrade Plan (`POST_PUBLISH_UPGRADE_PLAN.md`)

| Item | Original Objective | Current Status | Implemented Parts | Remaining Parts |
|---|---|---|---|---|
| **Upgrade 0** — GitHub cleanup | Consolidate `main` as sole authority; close stale branches/issues | 🟡 In progress | Planning document exists; issue #138 created; cleanup plan written | Branch deletion, issue closure not yet executed |
| **Upgrade 1** — Smarter Local Intelligence | Embedded GGUF + llama.cpp as baseline runtime; hardware-aware model selection | 🟡 Not started | `model_router.py` exists (referenced); `LocalRuntimeSetupService` referenced | RuntimeProfile, HardwareProfile, ModelCatalog, ProviderRegistry, RecommendationEngine, manifest-driven runtime selection |
| **Upgrade 1B** — Tool-Using Chat, Skills, Memory Spine | Bounded AECO tool-using truth assistant; typed tool registry; safety-gated skills | 🟡 Not started | Tool shell exists (`CalculatorTool`, `N8NTool`); skill files exist in `.agents/` | Full tool registry contract, skill definitions, memory separation, forbidden-pattern enforcement |
| **Upgrade 1C** — Quantization Strategy | Hardware-aware quantization profiles; role-based model fit; QuantBench testing | 🟡 Not started | None | Quantization policy table, model role manifest, QuantBench test suite |
| **Upgrade 2** — Workspace Honesty | Canonical status vocabulary; scope-bound chat; real snapshot object; unified review state machine | 🟡 Partially implemented | FactStatus enum exists; CoverageGate exists; `fact_api.py` partially implements; schema v17 adds domain/auth columns | Scope router, startup schema audit, storage topology audit, one mounted review/truth chain |
| **First visible slice** — Schedule Truth Workspace | Schedule page authority from certified facts; evidence-linked task view; schedule-specific refusal | 🔴 Not started | None (P6 extraction exists but no workspace) | Schedule fact builder hardening, graph engine, float/critical path gate, query tool, evidence-linked view, refusal behavior |
| **Upgrade 3** — Engineering-Grade Evidence Baseline | Typed, provenance-rich evidence for all file types; gold fixtures per domain | 🟢 Partially started | Gold fixture framework designed; PDF/P6/IFC/Office/Excel fixtures created; governance gate implemented | Scanned PDF (OCR), images/drawings (OCR/vision), IFC validation, acceptance fixtures for all domains |
| **Upgrade 4** — Document Center / File Inspector | Human verification cockpit with 4 tabs: Consolidated Review, Full Metadata, Raw Extraction, AI Output Only | 🔴 Not started | File Inspector exists (referenced in RELEASE_NOTES) | Tab structure, lane labeling rules, source attribution enforcement |
| **Upgrade 5** — Optional OCR / Layout / Vision Lab | Benchmark Docling, PaddleOCR, VLM helpers without polluting baseline | 🔴 Not started | None | Lab lane boundaries, candidate tool evaluation, quality gates, non-governing output labeling |
| **Upgrade 6** — Safe Revit Bridge | Thin read-only Revit add-in; local file-based handoff; no authoring | 🔴 Not started | None | Revit API integration, export commands, BCF package support, GUID mapping |
| **Upgrade 7** — Optional Acceleration & Ecosystem Lanes | Tiered support: baseline → optional → workstation → enterprise | 🔴 Not started | Distribution consent matrix defined | Provider tiers, optional lane implementation, graceful degradation |
| **Runtime Platform Wave** | ProviderAdapter, ProviderRegistry, HardwareProfile, ModelCatalog, RecommendationEngine, consent-gated actions | 🟡 Partially implemented | Read-model foundation (Wave 1B) deployed; provider discovery works; consent framework defined | Actual provisioning actions, model download/install, active runtime mutation |

### 1.2 Planning Consolidation Register (`PLANNING_CONSOLIDATION_REGISTER.md`)

| Preserved Idea | Source | Current Status | Implemented | Gap |
|---|---|---|---|---|
| Agent layer: read-only, deterministic, local-first, evidence-governed | `local-ai-planning-v0-1` | ✅ Captured | Governance gate (TASK-013) enforces this | Full agent layer not built |
| Auto-Ingest: controlled scheduler over existing pipeline | `local-ai-planning-v0-1` | 🟡 Not started | None | No auto-ingest scheduler |
| Auto-validation: deterministic and policy-based | `local-ai-planning-v0-1` | 🔴 Not started | RuleRunner exists but limited | Full auto-validation policy |
| Allowed/blocked fact classes explicit before auto-certification | `local-ai-planning-v0-1` | 🟡 Partial | Maturity gate in place; fact class policy not fully defined | Explicit allowed/blocked list |
| Evidence anchors: replayable source locations | `local-ai-planning-v0-1` | 🔴 Not started | `fact_inputs.location_json` partial | Replayable anchor schema |
| Tool/skill registries: typed, bounded, safety-gated | `local-ai-planning-v0-1` | 🟡 Partial | Extractor registry split (trusted/staging) | Full tool/skill registry contract |
| Safe trace fields for tool runs | `local-ai-planning-v0-1` | 🔴 Not started | None | Trace schema |
| C3+ concurrency: experimental until proven | `local-ai-planning-v0-1` | ✅ Captured | Policy preserved in register | Concurrency control not implemented |
| DOC-first quality sequence | `total-quality-upgrade-v3-3` | ✅ Applied | Wave A started with PDF first, then P6, IFC, Office, Excel | Quality packets for remaining domains |
| Domain-specific acceptance criteria | `total-quality-upgrade-v3-3` | 🟡 Partial | Quality Contract (TASK-010) defines criteria | Criteria per domain not all filled |
| Gold fixture legality policy | `total-quality-upgrade-v3-3` | ✅ Created | Gold Fixture Framework (TASK-016) + Implementation Plan (TASK-017) | Policy document not separate |
| Dependency/license admission checklist | `total-quality-upgrade-v3-3` | 🔴 Not started | None | Checklist |
| Release gate policy | `total-quality-upgrade-v3-3` | 🟡 Partial | Non-enabled behavior documented in RELEASE_NOTES | Automated gate not implemented |
| Lab boundary policy | `total-quality-upgrade-v3-3` | 🟡 Defined | Vision Lab concept in Upgrade 5; consent matrix defines lanes | Formal lab boundary enforcement |

### 1.3 Runtime Platform Status (`RUNTIME_PLATFORM_STATUS.md`)

| Component | Status | Details |
|---|---|---|
| Provider discovery (read-only) | ✅ Implemented | LM Studio, Ollama, OpenAI-compatible endpoints detected |
| Hardware recommendation skeleton | ✅ Implemented | Source-defined catalog; classification advisory only |
| Consent requirements defined | ✅ Defined | Internet, model download, provider start/stop, model load/unload, non-local use, runtime install |
| Consent-gated provisioning actions | 🔴 Not implemented | Actions are modeled but `executes=false`, `can_execute=false` |
| Active runtime mutation | 🔴 Blocked by design | No install, download, start, stop, load, or mutate |
| Persistent approval system | 🔴 Not implemented | Consent state is presentation-only, not a shipped approval system |

### 1.4 Runtime Distribution Consent Matrix (`RUNTIME_DISTRIBUTION_CONSENT_MATRIX.md`)

| Category | Status |
|---|---|
| Distribution tier definitions (9 tiers) | ✅ Defined |
| Consent rules (5 non-negotiables) | ✅ Documented |
| Baseline EXE policy | ✅ Defined |
| Implementation of tier enforcement | 🔴 Not implemented |
| Labeling of optional vs bundled components | 🔴 Not implemented |

### 1.5 GitHub Authority Cleanup Plan (`GITHUB_AUTHORITY_CLEANUP_PLAN.md`)

| Action | Status |
|---|---|
| `main` as sole authority | ✅ Established |
| Stale branch identification | ✅ Complete (`docs/local-ai-planning-v0-1`, `docs/total-quality-upgrade-v3-3`) |
| Issue mapping (#138, #136, #151, #24) | ✅ Complete |
| Branch cleanup execution | 🟡 Not started |
| Issue cleanup (close/supersede) | 🟡 Not started |

### 1.6 Additional Sources

| Source | Key Content | Relevance |
|---|---|---|
| `RELEASE_NOTES.md` | Explicit non-enabled behaviors; v0.1.0-3u provenance | Confirms baseline: no MCP, no autonomous agents, no Revit bridge, no CPM engine |
| `CHANGELOG.md` | v0.1.0-3u publication record | Confirms 115 tests passed at publish; no post-publish upgrades delivered |
| `README.md` | Product positioning: "review assistance with evidence"; NOT autonomous, NOT compliance-certified | Aligns with current narrow scope |
| Git history (10 recent commits) | Runtime wizard presenter, planning consolidation, metadata tool skills, GitHub cleanup plan | Confirms steady incremental progress on non-knowledge-gathering work |

---

## 2. Reality Alignment Check

For each plan, evaluated against: Does it solve a real problem? Does it improve engineer answer reliability? Does it improve knowledge coverage? Is the original priority still valid?

### 2.1 Plans That Still Address Real Problems

| Plan | Real Problem? | Answer Reliability? | Knowledge Coverage? | Priority Valid? |
|---|---|---|---|---|
| **Upgrade 1 — Smarter Local Intelligence** | ✅ Yes — cloud dependency is a product risk | ✅ Yes — better models = better answers | ⚠️ Indirect — improves synthesis, not extraction | ✅ Yes |
| **Upgrade 1B — Tool-Using Chat** | ✅ Yes — structured queries beat free-text RAG | ✅ Yes — calculator, schedule query, evidence retrieval tools | ⚠️ Indirect — better question formulation | ✅ Yes |
| **Upgrade 1C — Quantization Strategy** | ✅ Yes — hardware awareness prevents failure | ✅ Marginal — affects answer speed more than quality | ❌ No — doesn't add knowledge | ✅ Yes (infrastructure) |
| **Upgrade 2 — Workspace Honesty** | ✅ Yes — ambiguous status labels cause trust erosion | ✅ Yes — canonical vocabulary prevents overclaiming | ❌ No — doesn't add knowledge | ✅ Yes (foundational) |
| **Schedule Truth Workspace** | ✅ Yes — #1 engineer question is schedule-related | ✅ Yes — deterministic schedule answers | ⚠️ Partial — enhances P6 knowledge already captured | ✅ Yes (high value) |
| **Upgrade 3 — Engineering-Grade Evidence** | ✅ Yes — current evidence is incomplete | ✅ Yes — typed provenance = trustworthy answers | ✅ Yes — gold fixtures validate all extractors | ✅ Yes (already started) |
| **Upgrade 4 — Document Center** | ✅ Yes — engineers need to verify extraction | ✅ Yes — human review cockpit prevents false trust | ❌ No — UI improvement, not knowledge | ✅ Yes |
| **Upgrade 5 — OCR/Vision Lab** | ✅ Yes — scanned docs and images are blind spots | ⚠️ Conditional — lab output must stay non-governing | ✅ Yes — if vision lab produces usable extraction | ⚠️ Needs evaluation (see §5) |
| **Upgrade 6 — Revit Bridge** | ✅ Yes — Revit is dominant BIM authoring tool | ✅ Yes — direct BIM data > IFC round-trip | ✅ Yes — would dramatically improve BIM knowledge | ✅ Yes (long-term) |
| **Upgrade 7 — Ecosystem Lanes** | ✅ Yes — tiered deployment matches customer segments | ⚠️ Indirect — performance/enhancement not knowledge | ⚠️ Indirect — optional lanes add capability | ✅ Yes |
| **Runtime Platform** | ✅ Yes — distribution complexity needs governance | ⚠️ Indirect — runtime ≠ knowledge | ⚠️ Indirect — enables features, isn't knowledge | ✅ Yes |
| **Planning Consolidation** | ✅ Yes — stale plans cause confusion | ✅ Indirect — clear direction prevents wasted work | ❌ No — administrative | ✅ Yes |
| **GitHub Cleanup** | ✅ Yes — branch hygiene prevents confusion | ❌ No — process improvement | ❌ No — process improvement | ✅ Yes |

### 2.2 Plans That Do NOT Directly Improve Knowledge Coverage

| Plan | Why It Doesn't Help Knowledge | Should It Wait? |
|---|---|---|
| Upgrade 1C (Quantization) | Hardware optimization, not knowledge | Yes — after P1 knowledge gaps |
| Upgrade 7 (Ecosystem Lanes) | Deployment tiers, not knowledge | Yes — after core features |
| Runtime Platform (provisioning) | Infrastructure, not knowledge | Yes — after knowledge foundation |
| GitHub Cleanup | Process, not knowledge | Yes — parallel, low priority |
| Planning Consolidation | Administrative, not knowledge | Yes — already captured in register |

---

## 3. Knowledge Impact Mapping

Mapping existing plans against the knowledge gaps identified in TASK-024:

| Plan | Knowledge Gap Addressed | Gap Severity | Plan Impact |
|---|---|---|---|
| **Upgrade 3 — Engineering-Grade Evidence** | ALL gaps (systematic fix) | N/A | 🔴 **HIGH** — Gold fixtures validate every domain; governance gate ensures quality |
| **Upgrade 1B — Tool-Using Chat** | Structured queries (indirect) | 🟡 Medium | 🟡 **MEDIUM** — Schedule query tool, evidence retrieval tool improve answer paths for existing knowledge |
| **Upgrade 5 — OCR/Vision Lab** | Visual evidence (images/scans) | 🔴 Critical | 🔴 **HIGH** — Would address #2 knowledge gap IF vision lab produces trusted extraction |
| **Upgrade 6 — Revit Bridge** | BIM semantic understanding | 🟡 Medium-High | 🔴 **HIGH** — Direct Revit access would dramatically improve BIM knowledge beyond IFC round-trip |
| **Schedule Truth Workspace** | Schedule knowledge (partial) | 🟡 Medium | 🟡 **MEDIUM** — Hardens P6 knowledge that already exists; adds workflow layer |
| **Upgrade 2 — Workspace Honesty** | Trust boundary clarity | N/A (governance) | 🟡 **MEDIUM** — Ensures existing knowledge is presented with correct confidence labels |
| **Upgrade 4 — Document Center** | Human verification of evidence | N/A (UI) | 🟢 **LOW** — Improves trust in existing knowledge but doesn't add new knowledge |
| **Upgrade 1 — Smarter Local Intelligence** | Answer quality (synthesis) | N/A (infra) | 🟢 **LOW** — Better models improve answer fluency but not knowledge content |
| **Field Inspection (not in any plan)** | Field evidence | 🔴 High | 🔴 **NONE** — No existing plan addresses field inspection data extraction |
| **CAD/DWG (partially in Upgrade 3)** | CAD drawing intelligence | 🔴 Critical | 🟡 **MEDIUM** — Upgrade 3 mentions "images/drawings" but is vague; no specific DWG/DXF plan |

### Critical Observation

**No existing plan specifically addresses CAD drawing intelligence (DWG/DXF) or field inspection records.** The closest references are:
- Upgrade 3 mentions "images/drawings" under a vague "OCR/vision support" bullet
- No plan mentions field inspection, IR/NCR, or construction quality data
- No plan addresses document revision comparison

These are the two highest-impact knowledge gaps (from TASK-024 ranking #1 and #3).

---

## 4. Plan Status Classification

### A. Still Strategically Valid

| Plan | Confidence | Reason |
|---|---|---|
| **Upgrade 3 — Engineering-Grade Evidence Baseline** | 🟢 High | Already started; gold fixtures directly address knowledge gaps; governance gate protects quality |
| **Upgrade 2 — Workspace Honesty** | 🟢 High | Foundational for trust; canonical status vocabulary needed before any expansion |
| **Schedule Truth Workspace** | 🟢 High | First visible slice per original plan; P6 knowledge is strong but needs workspace layer |
| **Upgrade 1B — Tool-Using Chat** | 🟢 High | Structured query tools improve answer reliability for existing knowledge |
| **Planning Consolidation** | 🟢 High | Already captured; register preserves all useful decisions |

### B. Valid but Priority Changed

| Plan | New Priority | Reason |
|---|---|---|
| **Upgrade 5 — OCR/Vision Lab** | ⬆️ **P1 consideration** | Visual evidence is the #2 knowledge gap. Original plan treated it as "optional." Should be elevated. |
| **Upgrade 6 — Revit Bridge** | ⬆️ **P2 consideration** | BIM semantic enhancement is #3 gap. Original plan treated it as long-term. Should be accelerated after IFC baseline solidifies. |
| **Upgrade 1 — Smarter Local Intelligence** | ⬇️ **Deferred** | Model quality improves answer synthesis but doesn't fill knowledge gaps. Can wait until knowledge base is sufficient. |
| **Upgrade 1C — Quantization** | ⬇️ **Deferred** | Infrastructure concern; doesn't affect knowledge coverage. |
| **Upgrade 7 — Ecosystem Lanes** | ⬇️ **Deferred** | Deployment concern; doesn't affect knowledge coverage. |
| **Runtime Platform** | ⬇️ **Deferred** | Infrastructure; Wave 1B read-model is sufficient for now. |
| **Upgrade 4 — Document Center** | ➡️ **Maintained** | UI/verification improvement; supports trust but doesn't add knowledge. |

### C. Completed / Absorbed into Current System

| Plan Element | Where It Landed | Evidence |
|---|---|---|
| GitHub authority cleanup | `GITHUB_AUTHORITY_CLEANUP_PLAN.md` + issue mapping | Issue #138, #136, #151 documented; branches identified |
| Planning consolidation | `PLANNING_CONSOLIDATION_REGISTER.md` | All preserved ideas captured; stale branches identified |
| Runtime read-model | `RUNTIME_PLATFORM_STATUS.md` + Wave 1B commit | Provider discovery, consent framework, hardware recommendations deployed |
| Evidence authority gate | Tasks 013-015 (implemented) | `FactRepository.save_facts()` governance gate; staging registry split |
| Gold fixture framework | Tasks 016-022 (implemented) | 8 golden fixtures across 6 domains; 78 fixture tests; MANIFEST.md |
| Knowledge coverage analysis | Tasks 023-025 (implemented) | Trust Map, Coverage Map, Expansion Roadmap completed |

### D. No Longer Aligned

**None.** All plans remain aligned with the product doctrine. The original upgrade sequence was designed for a different understanding of knowledge gaps (pre-TASK-024). No plan contradicts current reality — some are just incomplete relative to discovered gaps.

### E. Requires External Research Before Decision

| Plan | Research Needed | Why |
|---|---|---|
| **Upgrade 5 — OCR/Vision Lab** | Can Tesseract/D docling produce engineering-trustworthy image text? | Vision Lab was scoped as "benchmark" — need to know if benchmark results would justify elevation |
| **Upgrade 6 — Revit Bridge** | What is the Revit API licensing and deployment constraint? | "Safe" bridge requires read-only add-in — need to confirm feasibility before prioritizing |
| **CAD/DWG extraction** (not explicitly planned) | Can ezdxf produce structural engineering knowledge? | Primary gap has no plan — need research before adding to roadmap |
| **Field inspection extraction** (not explicitly planned) | What extraction method produces reliable IR/NCR data? | Was previously mock data — need validated approach before any plan |

---

## 5. Missing Plans Identification

The following major knowledge gaps have **NO corresponding plan** in any existing document:

| Missing Knowledge Area | Gap Severity | Why No Plan Exists |
|---|---|---|
| **CAD Drawing Intelligence (DWG/DXF)** | 🔴 Critical — #1 gap | Upgrade 3 vaguely mentions "drawings" under OCR/vision; no dedicated plan for structured CAD extraction |
| **Field Inspection Records (IR/NCR)** | 🔴 High — #3 gap (was fabricated) | No plan addresses quality assurance data; previous FieldExtractor was PLACEHOLDER and is now blocked |
| **Document Revision Comparison** | 🟡 Medium — change tracking | No plan for version diff; each import creates new doc_id with no linkage |
| **Cross-Domain Correlation** | 🟡 Medium — linked evidence | No plan connects drawing ↔ spec ↔ schedule; knowledge exists in silos |
| **Structured BOQ / Quantity Extraction** | 🟡 Medium — quantity questions | No plan for Bill of Quantities parsing; Excel register handles values but not structured BOQ logic |

### Assessment of Missing Plans

1. **CAD Drawing Intelligence** is the most critical omission. It is the #1 knowledge gap by engineer value (TASK-024). The existing Upgrade 3 plan mentions "drawings" only as an OCR/vision afterthought. A dedicated CAD extraction plan should exist.

2. **Field Inspection Records** was previously attempted (FieldExtractor PLACEHOLDER) and failed badly (mock data produced VALIDATED facts). The governance gate now blocks it, but no replacement plan exists. Any future field data plan MUST pass the Evidence Quality Contract before registration.

3. **Document Revision Comparison** is a process gap, not a technical gap per se. It would require either a document control system integration or a manual multi-version ingest workflow. No plan exists because the original scope assumed single-version documents.

4. **Cross-Domain Correlation** is a higher-order capability that depends on individual domain knowledge being complete first. It is premature to plan this before CAD and visual gaps are closed.

5. **Structured BOQ Extraction** overlaps with the existing Excel register work. A dedicated BOQ parser would be an enhancement, not a new domain.

---

## 6. Management Conclusion

### 6.1 Are the Original Plans Still Valid?

**Yes, but incomplete.** The original Post-Publish Upgrade Plan provides a sound architectural direction:
- The evidence-first doctrine is correct and has been reinforced by the governance gate (TASK-013)
- The gold fixture framework (TASK-016-022) directly implements Upgrade 3's intent
- The planning consolidation correctly preserved useful decisions from stale branches
- The runtime platform read-model is a solid foundation

However, the original plans **underestimated the importance of visual and graphical knowledge sources**. The plan treated OCR/vision (Upgrade 5) as "optional" and had no specific CAD extraction plan. Both are now understood to be P1 knowledge gaps.

### 6.2 Which Plans Should Be Refined?

| Plan | Refinement Needed |
|---|---|
| **Upgrade 3 — Engineering-Grade Evidence** | Expand scope to explicitly include CAD (DXF) extraction and vision/OCR lab with quality gates. Currently only mentions "images/drawings" in passing. |
| **Upgrade 5 — OCR/Vision Lab** | **Elevate from optional to P1 consideration.** Visual evidence is the #2 knowledge gap. The lab framing (non-governing output) is appropriate — it allows experimentation without risk to truth. |
| **Upgrade 6 — Revit Bridge** | Keep as-is but **accelerate timeline** to P2. Direct Revit access is the best path to BIM semantic enhancement (currently limited to IFC round-trip). |
| **Schedule Truth Workspace** | Keep as the "first visible slice" — it delivers immediate value from existing P6 knowledge. |
| **Upgrade 2 — Workspace Honesty** | Keep as foundational — must be completed before any new knowledge domain is added, to ensure new facts enter with correct trust labels. |

### 6.3 Which Plans Should Wait?

| Plan | Reason to Defer |
|---|---|
| **Upgrade 1 — Smarter Local Intelligence** | Better models don't help if there's no knowledge to synthesize. Defer until P1 knowledge gaps are addressed. |
| **Upgrade 1C — Quantization Strategy** | Infrastructure concern. Can run in parallel with knowledge work but shouldn't block it. |
| **Upgrade 7 — Ecosystem Lanes** | Deployment concern. Relevant after core features are complete. |
| **Runtime Platform (provisioning)** | Infrastructure. Wave 1B read-model is sufficient. Active provisioning can wait. |
| **Upgrade 4 — Document Center** | UI improvement. Can be developed in parallel with knowledge work. |

### 6.4 Which Plans Need External Research Before Updating?

| Area | Research Question |
|---|---|
| **CAD/DXF extraction** | Can ezdxf produce structured layer/entity/annotation knowledge at a level that passes the Evidence Quality Contract? What is the minimum viable DXF knowledge subset? |
| **Vision/OCR quality threshold** | Can Tesseract or equivalent produce text from site photos and scanned drawings at a quality level engineers would trust? What is the acceptance criterion? |
| **Revit API deployment** | Can a read-only Revit add-in be distributed without requiring Revit installation on the client machine? What are the licensing constraints? |
| **Field inspection extraction method** | What extraction approach (VLM, structured forms, hybrid) produces non-fabricated field data that passes the Evidence Quality Contract? |

### 6.5 Summary Statement

**The original plans are directionally correct but knowledge-incomplete.** They were written before the systematic knowledge gap analysis (TASK-023/024) revealed that:

1. **35-40% of project knowledge is captured** — mainly text and schedule data
2. **CAD drawings and site images account for ~50-60% of missing knowledge** — and have no dedicated plans
3. **The vision/OCR lab (Upgrade 5) should be elevated** from optional to P1 consideration
4. **A new CAD extraction plan is needed** — no existing plan addresses the #1 knowledge gap
5. **Field inspection capability needs a validated approach** — the previous attempt produced fabricated evidence

**The single highest-value decision:** Before investing in model intelligence (Upgrade 1) or UI polish (Upgrade 4), the team should resolve whether CAD drawing extraction and visual evidence capture are feasible at engineering-trust quality levels. These two gaps account for the majority of engineer answer unreliability.

---

*This document reconciles existing plans against current knowledge reality. It is a strategic analysis artifact. No implementation decisions are made.*
