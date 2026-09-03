# SerapeumAI CAD Drawing Intelligence Plan v1.0

**Date:** 2026-09-03
**Type:** Narrow strategic plan — read-only, gated, scoped to CAD/DWG/DXF knowledge
**Authority:** Derived from SerapeumAI Parked Plan Modernization v1.0 §7
**Scope:** CAD/DWG/DXF extraction and engineering knowledge representation. Excludes image OCR, scanned-PDF OCR, photo VLM, and BIM geometry (which are covered by other plans).

---

## 1. Purpose

CAD drawings are the **primary AECO deliverable**. Every project produces them; every discipline references them daily; design intent, dimensions, annotations, and spatial relationships all live inside them.

Per the September 2026 Knowledge Coverage Map and Knowledge Expansion Roadmap, CAD drawing intelligence is the **#1 highest-impact knowledge gap** in SerapeumAI. This plan defines the **narrowly scoped strategic path** to close that gap without violating the evidence-first doctrine.

This plan does **not** implement. It defines gates, scope, and acceptance criteria for future bounded implementation packets.

---

## 2. Strategic Objectives

1. Make CAD drawing content **queryable** by engineers through the existing chat workflow.
2. Preserve **drawing knowledge as evidence** with full provenance (file version, entity handle, layer, block, sheet).
3. Treat all CAD-derived facts as **CANDIDATE** until they pass the Evidence Quality Contract acceptance gates; HUMAN_CERTIFIED remains the formal path for engineering decisions.
4. Maintain **Windows-first, local-first, privacy-first, portable-packaging** compatibility.
5. Preserve the **evidence-first chain**: source → controlled extraction → evidence/provenance → structured facts → validation/certification → retrieval → local LLM answer.

---

## 3. Out of Scope (Explicit)

- Image OCR and scanned-PDF OCR — covered by Post-Publish Upgrade Plan Upgrade 5 (`Optional OCR / Layout / Vision Lab`).
- Photo / site VLM — covered by Upgrade 5.
- BIM geometry, IFC element filtering — covered by Post-Publish Upgrade Plan Upgrade 6 (`Safe Revit Bridge`) and IFC Gold Fixture Validation.
- Schedule / cost / BOQ — out of scope for this plan.
- DWG-to-DXF conversion strategies that depend on unlicensed / unverified proprietary SDKs (see §7).

---

## 4. Source Format Targets

| Format | Strategic Target | Technology Decision |
|---|---|---|
| **DXF** (open text format) | Primary, deterministic extraction | `ezdxf` — **TRIAL** (per Parked Plan Modernization §8 / T1) |
| **DWG** (proprietary binary) | Deferred; requires fidelity & licensing research | **DEFER** (T2) until Gate G5 research packet closes |
| **DWG via ODA converter** | Optional lab-only | Gate G5 decision |
| **DWG via LibreDWG** | Optional lab-only | Gate G5 decision |
| **DWG via proprietary SDK** | **DEFER** until license admission review | T2 |

DXF is the **first-class** target because it is open, deterministic, and license-friendly. DWG is the **second-class** target pending Gate G5.

---

## 5. Knowledge Subset (Minimum Viable)

The plan targets the **minimum viable CAD knowledge subset** that produces engineer-useful facts:

| Knowledge Subset | Example Engineer Query | Evidence Type |
|---|---|---|
| **Layer inventory** | "What layers exist on this drawing?" | DXF layer table; deterministic. |
| **Entity enumeration by layer** | "How many polylines are on the WATER layer?" | DXF entity listing; deterministic. |
| **Block references** | "What symbols are used and where?" | DXF INSERT entities + block names; deterministic. |
| **Text annotations** | "What room labels appear on plan A-101?" | DXF TEXT/MTEXT entities + positions; deterministic. |
| **Dimension values** | "What is the dimension of room R-201?" | DXF DIMENSION entities + values; deterministic. |
| **Sheet / layout metadata** | "How many sheets are in this drawing set?" | DXF layout/section metadata; deterministic. |
| **Bounding geometry (bbox)** | "What is the extent of the structural grid?" | DXF entity bounding boxes; deterministic. |
| **Cross-reference set** | "Which other drawings does this one reference?" | XREF headers when present; deterministic. |

Geometry **without visual interpretation** is in scope (entities, coordinates, bounding boxes). **Visual interpretation** of geometry (semantic recognition of walls vs ducts vs rebar) is out of scope for v1.0 and is **DEFERRED** to a future visual-semantic research packet.

---

## 6. Evidence-Governance Requirements

This section states what CAD-derived knowledge must look like before any future implementation packet is admitted to the project. Detailed technical design (specific class names, registry names, function names, test-count prescriptions) belongs only in later B-012 controlled implementation packets and is intentionally absent here.

The evidence-first chain remains:

```text
Source File (.dxf / .dwg)
    → Controlled Extraction (governed by Evidence Quality Contract §2-§8)
    → Evidence + Provenance (typed records with required provenance fields)
    → Structured Facts (CANDIDATE only at first; promotion rules explicit)
    → Validation / Certification (governance gate; honesty on missing inputs)
    → Retrieval (typed, bounded; authority declared)
    → Local LLM Answer (narrator only; never computes, certifies, or invents truth)
```

**Governance requirements** (must hold for any future CAD implementation):

1. **Provenance completeness.** Every evidence record carries the provenance fields required by Evidence Quality Contract §3-§4 plus the CAD-specific fields: layer name, entity type, entity handle, block name when present, sheet/layout reference when present. No record may be persisted without its provenance.
2. **Honesty on unsupported inputs.** When a candidate library, file format variant, or feature is unsupported, the controlled extraction must report honest failure with a named diagnostic. No silent fallback to a degraded path. No claim of partial or approximate extraction.
3. **Determinism.** Identical input must produce identical records. Non-determinism sources (UUID generation in output IDs, timestamps in data, random record ordering) are forbidden in the evidence path.
4. **Staging / non-governing requirement.** Until CAD extraction reaches the **VERIFIED** maturity level, its output is **non-governing** and visibly labeled as such. It must not participate in any governing-truth answer. Promotion to governing status requires passing the Evidence Quality Contract §12 acceptance criteria and the owner's authorization.
5. **No mock / fabricated data.** Production CAD extraction must not return hardcoded records, filename-derived mocks, or UUID-generated lookalike IDs (Evidence Quality Contract §9).
6. **CANDIDATE-first promotion.** All CAD-derived facts enter the fact system as **CANDIDATE**. Promotion to **VALIDATED** requires either (a) an explicit rule-based promotion accepted by the governance gate for narrowly defined structural facts only, or (b) human certification via the existing review workflow. Promotion to **HUMAN_CERTIFIED** remains the formal path for engineering decisions.
7. **Authority labeling.** CAD evidence appears in retrieval with its authority level declared. Any LLM answer citing CAD evidence must distinguish CAD-derived support from governing certified facts.
8. **Retrieval boundary.** CAD queries, when admitted, must be served by typed, bounded retrieval whose contract declares that it cannot govern truth on its own. The LLM narrates retrieved CAD evidence; it does not compute, decide, or certify.

## 7. Maturity / Acceptance Gates

The future CAD work advances through maturity levels defined by the Evidence Quality Contract §10. Each promotion requires an explicit acceptance gate.

### 7.1 EXPERIMENTAL Gate

Purpose: bounded exploration without affecting governing truth.

- Output is non-governing and labeled as support.
- Output is isolated from any governing-truth retrieval path.
- All records carry full provenance.
- Honest failure on unsupported inputs (named diagnostic, no fallback).
- Determinism for identical inputs.

Exit condition: a controlled experiment demonstrates repeatable EXPERIMENTAL behavior on canonical DXF inputs, with a written record of what was learned and what remains unproven.

### 7.2 VERIFIED Gate

Purpose: bounded admission of CAD evidence into the project, still non-governing unless explicitly promoted.

- All EXPERIMENTAL conditions hold.
- Provenance completeness is checked for every record.
- Honest failure on missing optional dependencies, unsupported format variants, and malformed entities.
- Behavior tests cover: routing, determinism, provenance, dependency honesty, and at least one negative case.
- Acceptance criteria from Evidence Quality Contract §12 are met.
- Legality and reproducibility of fixtures are reviewed per the Gold Fixture Framework.
- No mock / fabricated data in the production code path.

Exit condition: written declaration of VERIFIED maturity, accepted by the owner. VERIFIED does **not** grant governing status; it grants admission as non-governing evidence.

### 7.3 PRODUCTION Gate

Purpose: admission of CAD evidence as a candidate source for engineering workflows, with all standard promotion rules applying.

- All VERIFIED conditions hold.
- No TODO comments in the critical extraction path.
- Test coverage satisfies the Evidence Quality Contract §10.1 PRODUCTION criteria.
- Owner authorization recorded.

Exit condition: written declaration of PRODUCTION maturity.

### 7.4 Promotion-to-VALIDATED Gate (Optional, Owner-Approved)

Purpose: allow narrowly defined structural CAD facts (e.g., layer count, block count, entity count) to reach VALIDATED via rule-based promotion rather than requiring human certification per fact.

- Owner must explicitly approve which structural facts (if any) may auto-promote.
- The promotion rule must be accepted by the governance gate and visible in the rule registry.
- HUMAN_CERTIFIED remains required for any semantic CAD claim.
- Any structural-fact auto-promotion must be reversible by the owner.

Exit condition: written owner decision recorded in the rule registry and in the planning corpus.

## 8. Strategic Outcomes and Owner Decisions

This section enumerates the strategic outcomes this plan exists to deliver and the owner decisions that must be resolved before any future implementation packet can open. No code-level instructions appear here.

### 8.1 Strategic Outcomes

The plan, once its acceptance gates pass, delivers:

1. **CAD drawing content becomes queryable** through the existing chat workflow for engineers, subject to the maturity gates above.
2. **Drawing knowledge is preserved as evidence** with full provenance (file version, entity handle, layer, block, sheet), enabling replay and verification.
3. **CAD-derived facts enter the fact system as CANDIDATE** by default, with explicit owner-controlled promotion rules for any narrow structural-fact auto-promotion to VALIDATED.
4. **DWG handling follows the research packet outcome**, not the DXF path; DXF and DWG may each reach their own future acceptance gates independently.
5. **Windows-first, local-first, privacy-first, portable-packaging** compatibility is preserved end-to-end.

### 8.2 Owner Decisions Required Before Any Future Packet Opens

1. **T2 reclassification timing.** When does the DWG research packet open? Independent of the DXF progression.
2. **DXF / DWG source-variant coverage.** Which DXF variants (AC1009 through AC1032) must the TRIAL extractor accept before VERIFIED promotion? (Carried forward from the modernization plan §14.)
3. **Structural-fact auto-promotion.** Should narrowly defined structural CAD facts (counts, layer existence, block existence) auto-promote to VALIDATED via a rule, or always require HUMAN_CERTIFIED?
4. **CAD retrieval authority level.** When CAD evidence is admitted, what authority level is declared for retrieval-bound CAD facts?
5. **Evidence-of-record labeling.** What visible label distinguishes CAD-derived support from governing certified facts in chat answers?
6. **Lab boundary for any visual-semantic recognition.** If a future packet re-introduces visual-semantic interpretation of geometry (walls vs ducts vs rebar), what lab boundary and gating gate apply? (Currently out of scope.)

Each decision above requires a written owner-approved artifact before any future implementation packet may open.

---

## 9. Windows / Local-First / Privacy-First / Portable-Packaging Implications

- **Windows-first:** ezdxf portability has **not** been validated by TASK-028. Any claim that it is "pure-Python with Windows wheels" or has "no native dependency" is a validation requirement — a bounded packaging validation gate must confirm this before baseline integration. DWG path research must produce a Windows-portable solution or be rejected.
- **Local-first:** No network calls; library-only.
- **Privacy-first:** Drawing content never leaves the machine; no telemetry.
- **Portable-packaging:** ezdxf footprint impact is **unvalidated** by TASK-028. Any claim that it "adds a small footprint" is a validation requirement — packaging impact must be assessed by a bounded validation gate before baseline integration. DWG path selection must not inflate portable distribution beyond owner-approved limits.
- **Packaging files (`SerapeumAI_Portable.spec`, `build_portable.ps1`, `build_portable.bat`) are sensitive and require explicit owner approval before any change.** This plan explicitly forbids editing them.

---

## 10. Technology Status (Reference)

This plan uses the technology statuses assigned by `SERAPEUMAI_PARKED_PLAN_MODERNIZATION_v1.0.md` §8:

- `ezdxf` — **TRIAL** (T1)
- DWG paths — **DEFER** (T2)
- All other related technologies are TRIAL within Upgrade 5 / Upgrade 6 / Schedule / Tooling scopes and are not duplicated here.

---

## 11. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| DXF entity volume exhausts memory on large sets | Medium | Medium | Size caps per Evidence Quality Contract §5.4; fixture-driven validation. |
| ezdxf lacks fidelity for production-grade DXF variants | Medium | Medium | Gold Fixture Framework exercises canonical variants before VERIFIED promotion. |
| DWG path licensing blocks distribution | High | High | Gate G5 / CAD-PP-3; DEFER status until research closes. |
| Geometry interpretation (visual semantic) scope drift | Medium | High | Explicitly out of scope in §3. |
| CAD-derived facts auto-promote to VALIDATED without certification | Medium | High | T11 (mock data) REJECTED; CAD-PP-8 owner decision required before any auto-promotion. |
| Lab output leaks into governing chain | Medium | High | Lab framing enforced; non-governing output must not enter the governing retrieval path. |
| Portable packaging drift | Low | High | No packaging edits without owner approval. |

---

## 12. Rollback

If any packet's exit condition cannot be met:

1. Revert the lab-side admission of the failed packet.
2. Remove the gold fixtures added for the failed packet.
3. Retain the research artifacts as historical record under `docs/internal/`.
4. Reopen the packet with refined scope; do not silently expand scope to "make it work".

This plan never silently expands. Scope changes require a new decision artifact.

---

## 13. Remaining Owner Decisions

The full list of owner decisions for this plan appears in **§8.2** above. This section records additional decisions that emerge from the operating context but are not directly a governance-c or maturity-c decision.

1. **T2 reclassification timing:** When does the DWG-path research packet open? (Independent of DXF progression per Modernization §9.1; the decision does not gate DXF acceptance.)
2. **Lab boundary for any future visual-semantic recognition.** If a future packet re-introduces visual-semantic interpretation of geometry (walls vs ducts vs rebar), what lab boundary and gating gate apply? (Currently out of scope per §3.)
3. **UI surface (if and when).** If a CAD-specific surface is ever introduced, what authority labeling does it declare for CAD-derived support versus governing certified facts? (Currently no UI is planned; this decision becomes live only if a future packet proposes one.)

---

## 14. Closing Statement

This plan closes the single remaining uncovered P1 knowledge gap in SerapeumAI — CAD Drawing Intelligence — without violating the evidence-first doctrine, the Windows/local-first/privacy-first/portable-packaging commitments, or the existing parked-plan corpus.

It is intentionally narrow. Future visual-semantic CAD recognition (walls vs ducts vs rebar) is **out of scope** and **deferred** to a future research packet.

No code, dependency, packaging, build, commit, push, or PR action is implied or performed by this plan.

---

*This document is a strategic planning artifact. It does not implement, install, build, commit, push, open PRs, or modify code/tests. All gated future work requires explicit owner approval before opening.*