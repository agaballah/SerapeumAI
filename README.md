# SerapeumAI

SerapeumAI is a **Windows-first, local-first AECO review workspace** for evidence-backed project review.

It helps engineers and reviewers:

- ingest project files into a local project workspace;
- inspect deterministic extraction and AI-generated support separately;
- review facts on the Facts page with lineage and evidence;
- ask project questions in Expert Chat with direct answers and optional evidence lanes.

SerapeumAI is **review assistance** with evidence and provenance. It is **not** a guaranteed-compliance engine, legal approval engine, autonomous design-authoring tool, or generic chatbot.

---

## Current publication status

Current release candidate authority:

```text
main includes PR #123
commit: 51bc3280e1adf9e3cc53859cb2f99bc0b8847548
latest completed gate: #125 — Final Packaging Proof Gate
artifact: dist\SerapeumAI_Portable\SerapeumAI.exe
artifact size: 110206723 bytes
```

Release evidence currently recorded:

- final Windows source regression: **PASS**;
- manual source smoke: **PASS with caveats**;
- documentation honesty checkpoint: **PASS**;
- final packaging proof: **PASS**;
- packaged app smoke: **PASS**;
- final owner publish decision: **pending** in issue #126.

A GitHub Release/tag has not been created by this README.

---

## Supported posture

- Baseline platform: **Windows**.
- Core posture: **local-first** and **project-local**.
- Runtime expectation: local LM Studio-compatible runtime for the current mounted runtime path.
- Current publish generative runtime: `qwen2.5-coder-7b-instruct`.
- Embeddings remain separate from the generative model.
- Calculations and deterministic checks must be performed by application code/tools, not by LLM arithmetic.

---

## Quick start

Development run path:

```powershell
python run.py
```

Packaged release-candidate path after a successful local build:

```powershell
.\dist\SerapeumAI_Portable\SerapeumAI.exe
```

For setup and runtime notes, see:

- `INSTALL.md`
- `TROUBLESHOOTING.md`
- `RELEASE_NOTES.md`

---

## Mounted workflow

- **Dashboard**: project counts, runtime state, pipeline diagnostics, and honesty-oriented health labels.
- **Documents**: browse project documents and open the File Inspector.
- **File Inspector**:
  1. Consolidated Review
  2. Full Metadata
  3. Raw Deterministic Extraction
  4. AI Output Only
- **Facts**: review facts, inspect meaning/source/review state, and open lineage/evidence.
- **Expert Chat**:
  - shows a direct answer first;
  - labels the basis of the answer;
  - exposes optional evidence lanes;
  - resets visible chat history when the active project closes or changes;
  - drops late responses/errors from old project sessions.

---

## Trust and provenance model

- `VALIDATED` and `HUMAN_CERTIFIED` facts are trusted answer sources.
- `CANDIDATE` facts are visible for review but do not silently govern answers.
- `REJECTED` facts are excluded from trusted answer paths.
- Deterministic extraction and parser/OCR output remain separate from AI-generated support.
- AI Output Only is non-governing unless promoted through review/certification.
- Vector/retrieval stores are derived support, not governing truth.
- Project A must not answer from Project B.

---

## Current proven behavior

Completed proof rails include:

- mounted chat active-project authority and project isolation;
- sourced answer authority labeling;
- support-only answer labeling;
- snapshot/imported-date wording honesty;
- PDF metadata completeness and routing proof;
- IFC dependency/no-fallback honesty;
- Office/DGN flattened extraction contract;
- P6 critical-path unknown honesty;
- P6 relation uniqueness/fidelity;
- File Inspector four-lane separation;
- final packaging proof and packaged-app smoke.

---

## Explicit non-enabled behavior

The current repository does **not** enable or claim:

- autonomous chat tool execution;
- LLM tool-call parser in the visible chat UI;
- MCP integration;
- autonomous agent loops;
- audit persistence implementation;
- project memory implementation;
- runtime/provider provisioning or model download control;
- snapshot governance implementation;
- Revit bridge;
- Schedule Truth Workspace implementation;
- CPM engine;
- PDF VLM routing;
- IFC fallback parser when `ifcopenshell` is missing;
- typed Office/CAD persistence;
- generic Excel workbook semantic persistence;
- guaranteed legal, contractual, regulatory, or compliance approval.

---

## Known caveats

The current artifact passed packaging and packaged smoke, but these caveats remain important for release notes and troubleshooting:

- constrained 8 GB VRAM laptops may show runtime, VRAM, or GPU-temperature warnings;
- model routing may downgrade analysis to chat when VRAM is limited;
- embeddings may load on CPU when VRAM is reserved or insufficient;
- page-level LLM JSON parse retries/errors can occur during analysis;
- these caveats do not change deterministic extraction, facts, evidence lanes, or packaged smoke proof.

---

## Repository and contribution rules

- `src/**` is the primary editable source surface.
- `run.py` and `run_tests.py` are editable only when needed.
- `SerapeumAI_Portable.spec`, `build_portable.ps1`, and `build_portable.bat` are sensitive packaging files.
- Do not treat `build/**`, `dist/**`, `.serapeum/**`, `models/**`, or `**/__pycache__/**` as normal editing targets.
- Avoid dependency upgrades unless explicitly approved.
- Preserve Windows portability and packaging behavior.
- Prefer minimal, reviewable diffs.

See `CONTRIBUTING.md` for details.

---

## License

SerapeumAI is released under the Apache License, Version 2.0. See `LICENSE` and `NOTICE`.

Third-party dependency and runtime notes are summarized in `THIRD_PARTY_NOTICES.md`.

---

## Future planning

The branch below is preserved as a parked future-upgrade planning branch only:

```text
docs/total-quality-upgrade-v3-3
```

It is not the current release authority and must be reconciled against `main` before future implementation.
