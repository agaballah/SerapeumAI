# SerapeumAI Publish Truth Statement

Task class: release task / documentation-control artifact  
Status: release-honesty checkpoint, not a final publish pass  
Authority: current `main` after PR #121

---

## 1. Purpose

This document states what the current repository has actually proven during the Workspace Honesty and Engineering Evidence rails.

It is intentionally conservative. It does not claim final publish readiness until the final Windows release test, mounted workflow smoke test, and packaging proof are complete.

---

## 2. Current authority

```text
main includes PR #121
latest main SHA: e5bdf53913cd25ac464ce36feb98ff3ab66b0065
latest completed issue: #120 — Upgrade 3J — P6 Relation Uniqueness/Fidelity Proof/Patch
master backlog: #24
preserved future planning branch: docs/total-quality-upgrade-v3-3
```

---

## 3. Product truth

SerapeumAI is a Windows-first, local-first AECO review workspace.

It provides evidence-backed review assistance through:

- deterministic extraction,
- fact building,
- human review/certification,
- lineage/provenance,
- mounted File Inspector views,
- mounted Facts page,
- mounted Expert Chat.

SerapeumAI is not:

- a guaranteed-compliance engine,
- a legal approval engine,
- a cloud-required product,
- a generic chatbot,
- a design-authoring tool,
- an autonomous agent that silently edits project files or models.

---

## 4. Completed proof rails

### Workspace Honesty rail

Proven:

- mounted chat runtime uses explicit active project authority;
- unsafe legacy no-project chat authority paths were removed or guarded;
- sourced-answer doctrine is multi-lane with explicit authority labeling;
- support-only answers are labeled as support, not certified trusted facts;
- imported-date/snapshot selector wording is informational only;
- cross-project answer isolation has regression coverage.

### Engineering Evidence rail

Proven:

- File Inspector separates:
  1. Consolidated Review
  2. Full Metadata
  3. Raw Deterministic Extraction
  4. AI Output Only
- extractor registry reachability is explicit for current PDF, Word, PPTX, DGN, IFC, P6, field, and Excel register extractors;
- Excel register extraction no longer writes to an absolute debug path;
- IFC emitted metadata and connection records are not silently dropped by `ExtractJob`;
- PDF metadata includes normalized document metadata, raw PDF metadata, page count, and page composition counts;
- PDF routing is test-locked for empty, vector, scanned, and combined pages;
- PDF routing proof confirms OCR boundaries and confirms VLM remains unused;
- missing `ifcopenshell` fails honestly with no fallback IFC parser claim;
- Word/PPTX/DGN extraction is flattened deterministic extraction, not typed Office/CAD persistence;
- Excel extraction is register/log-row oriented, not generic workbook semantic persistence;
- P6 critical-path unknown handling does not convert missing/unusable float into false membership or zero-count facts;
- P6 relation fidelity preserves distinct `TASKPRED` rows when predecessor/successor match but relation type or lag differs.

---

## 5. Explicit non-enabled behavior

The current repository does not enable or claim:

- final publish pass;
- final packaging proof;
- dependency upgrades;
- packaging file changes;
- CPM engine implementation;
- Schedule Truth Workspace implementation;
- PDF VLM routing;
- typed Office/CAD persistence;
- generic Excel workbook semantic persistence;
- IFC fallback parser when `ifcopenshell` is missing;
- autonomous chat tool execution;
- MCP integration;
- runtime provider provisioning, model download, or runtime control;
- Revit bridge implementation;
- audit persistence implementation;
- project memory implementation.

---

## 6. Packaging boundary

Packaging files remain sensitive and must not be edited unless explicitly approved:

- `SerapeumAI_Portable.spec`
- `build_portable.ps1`
- `build_portable.bat`

No dependency upgrades are approved by this statement.

---

## 7. Total Quality Upgrade branch boundary

The Total Quality Upgrade planning dossier is preserved on:

```text
docs/total-quality-upgrade-v3-3
```

It is future planning only.

It is not:

- merged release authority,
- current implementation authority,
- packaging authority,
- a final publish claim.

Before using that branch later, reconcile it against actual `main` repo truth.

---

## 8. Current publish truth

Current state after Workspace Honesty and Engineering Evidence through PR #121:

```text
Source/test closure rail: materially strengthened
Documentation honesty checkpoint: active through #122
Final Windows release test: not yet complete
Mounted workflow smoke test: not yet complete
Packaging proof: not yet complete
Final publish verdict: NOT YET PASSED
```

---

## 9. Remaining release gates

Before a final publish pass:

1. Complete documentation/release honesty checkpoint.
2. Run final local Windows source regression suite.
3. Run mounted workflow smoke test:
   - open project,
   - dashboard refresh,
   - documents/file inspector,
   - facts review actions,
   - expert chat answer with evidence,
   - close/change project,
   - Red-X shutdown.
4. Run packaging proof last.
5. Launch packaged app on Windows and repeat the critical smoke path.
6. Issue final PASS/FAIL publish verdict.

---

## 10. Next action after this document

After this checkpoint is merged and cleaned:

```text
Select either:
- Schedule Truth Workspace design issue, or
- final release-readiness gate,
depending on owner priority and remaining risk.
```
