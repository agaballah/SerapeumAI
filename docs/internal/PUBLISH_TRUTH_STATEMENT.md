# SerapeumAI Publish Truth Statement

Task class: release task / documentation-control artifact  
Status: final release-candidate truth statement pending owner publish decision  
Authority: current `main` after PR #123 and packaging proof through #125

---

## 1. Purpose

This document states what the current repository and packaged artifact have actually proven.

It is conservative by design. It records release-candidate truth without expanding the product story beyond tested behavior.

---

## 2. Current authority

```text
main includes PR #123
latest main SHA: 51bc3280e1adf9e3cc53859cb2f99bc0b8847548
latest completed issue: #125 — Upgrade 3M — Final Packaging Proof Gate
master backlog: #24
final publish-decision issue: #126
publication docs/hygiene issue: #127
preserved future planning branch: docs/total-quality-upgrade-v3-3
```

Release-candidate artifact:

```text
dist\SerapeumAI_Portable\SerapeumAI.exe
size: 110206723 bytes
```

---

## 3. Product truth

SerapeumAI is a Windows-first, local-first AECO review workspace.

It provides evidence-backed review assistance through:

- deterministic extraction;
- fact building;
- human review/certification;
- lineage/provenance;
- mounted File Inspector views;
- mounted Facts page;
- mounted Expert Chat.

SerapeumAI is not:

- a guaranteed-compliance engine;
- a legal approval engine;
- a cloud-required product;
- a generic chatbot;
- a design-authoring tool;
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

### Documentation honesty rail

Proven:

- README release honesty checkpoint was updated;
- stale Packet 8 / Packets 1-7 language was removed;
- completed proof rails and explicit non-enabled behavior are documented;
- the parked Total Quality Upgrade branch is documented as future planning only.

### Final source and packaging gates

Proven:

```text
Release-relevant source regression: 115 passed in 1.81s
Manual source smoke: PASS with caveats
Documentation honesty: PASS
Packaging proof: PASS
Packaged app smoke: PASS
```

Packaging proof:

- existing packaging script completed with exit code `0`;
- fresh packaged artifact was produced;
- no source/test/docs/packaging files changed;
- no obvious bundled `src/tests`, `__pycache__`, or pytest cache was found in the dist package;
- packaged executable launched on Windows;
- packaged workflow smoke passed;
- shutdown showed no Tk post-destroy / bgerror / invalid command noise in supplied tail.

---

## 5. Explicit non-enabled behavior

The current repository does not enable or claim:

- autonomous chat UI tool execution;
- LLM tool-call parser in the visible chat UI;
- MCP integration;
- autonomous agent loop;
- audit persistence implementation;
- project memory implementation;
- runtime provider provisioning, model download, or runtime control;
- snapshot governance implementation;
- Revit bridge implementation;
- Schedule Truth Workspace implementation;
- CPM engine implementation;
- PDF VLM routing;
- typed Office/CAD persistence;
- generic Excel workbook semantic persistence;
- IFC fallback parser when `ifcopenshell` is missing;
- guaranteed legal, contractual, regulatory, or compliance approval.

---

## 6. Caveats

The current artifact passed source and packaging gates, but these caveats remain relevant:

```text
LLM JSON parse failed on 2 analysis pages during source smoke
Page analysis health: 28 / 30 healthy during source smoke
GPU overheating warning at 86C on constrained 8 GB VRAM laptop
VRAM-limited downgrade from analysis to chat can occur
Embedding can load on CPU due to VRAM reserved/insufficient
```

Interpretation:

- These are release-note/troubleshooting caveats.
- They are not packaging blockers for the current artifact.
- They should inform broader-machine validation and post-publish runtime/platform work.

---

## 7. Packaging boundary

Packaging files remain sensitive and must not be edited unless explicitly approved:

- `SerapeumAI_Portable.spec`
- `build_portable.ps1`
- `build_portable.bat`

No dependency upgrades are approved by this statement.

---

## 8. Total Quality Upgrade branch boundary

The Total Quality Upgrade planning dossier is preserved on:

```text
docs/total-quality-upgrade-v3-3
```

It is future planning only.

It is not:

- merged release authority;
- current implementation authority;
- packaging authority;
- a final publish claim.

Before using that branch later, reconcile it against actual `main` repo truth.

---

## 9. Current publish truth

```text
Source/test closure rail: PASS
Documentation honesty: PASS
Manual source smoke: PASS with caveats
Packaging proof: PASS
Packaged app smoke: PASS
Final publish candidate artifact: AVAILABLE
GitHub Release/tag: NOT CREATED BY THIS STATEMENT
Owner publish decision: PENDING IN #126
Publication docs/hygiene gate: ACTIVE IN #127
```

---

## 10. Next action

Complete #127 repository publication documentation and hygiene gate, then return to #126 for explicit owner publish decision.
