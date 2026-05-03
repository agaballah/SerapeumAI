# SerapeumAI

**Windows-first local AECO review workspace for engineers.**

SerapeumAI helps engineering and construction reviewers inspect project documents, separate deterministic evidence from AI-generated support, certify facts, and ask project questions with visible evidence lanes.

It is built for engineers who need a local review workspace, not a generic chatbot.

---

## Download for Windows

### Current status

```text
Release candidate built and smoke-passed.
GitHub Release download asset: pending owner release decision / upload.
```

The Windows executable proven during packaging is:

```text
dist\SerapeumAI_Portable\SerapeumAI.exe
size: 110206723 bytes
```

After the GitHub Release asset is uploaded, engineers should download the Windows portable package from:

```text
GitHub Releases -> Latest release
```

Expected release asset name:

```text
SerapeumAI_Windows_Portable_v0.1.0-rc1.zip
```

Expected run path after unzip:

```text
SerapeumAI_Portable\SerapeumAI.exe
```

> The repository does **not** currently claim a live direct download asset until the GitHub Release is created and the portable ZIP is uploaded.

---

## What SerapeumAI does

SerapeumAI helps engineers:

- ingest project files into a local project workspace;
- review project documents from a mounted Documents page;
- inspect evidence through File Inspector lanes;
- review and certify facts with lineage;
- ask Expert Chat questions with evidence-labeled answers;
- keep AI-generated support separate from trusted facts.

SerapeumAI is **review assistance with evidence and provenance**. It is **not** a guaranteed-compliance engine, legal approval engine, autonomous design-authoring tool, or generic chatbot.

---

## Current release candidate authority

```text
Repository authority: main after PR #128
Current remote main SHA: 8c4b87372a85d592ec45409eac24e3ef79499114
Packaging proof issue: #125 — PASS
Publication hygiene issue: #127 / PR #128 — PASS
Final publish decision: #126 — pending
Broader Windows validation: #129 — pending
```

Packaging-proof source authority:

```text
51bc3280e1adf9e3cc53859cb2f99bc0b8847548
```

PR #128 was documentation/repository metadata only. It did not change source, tests, packaging files, dependencies, build outputs, or `dist` artifacts.

---

## Fast start

### For users after a GitHub Release is published

1. Open the latest GitHub Release.
2. Download the Windows portable ZIP.
3. Unzip it.
4. Run:

```text
SerapeumAI_Portable\SerapeumAI.exe
```

### For local development

From the repository root:

```powershell
python run.py
```

See:

- `INSTALL.md`
- `TROUBLESHOOTING.md`
- `RELEASE_NOTES.md`

---

## Runtime expectation

The current mounted runtime path expects a local LM Studio-compatible runtime for model-backed analysis and chat features.

The application should report runtime state honestly:

```text
READY — local runtime/model is reachable and loaded
MODEL_NOT_LOADED / not ready — runtime or model is unavailable
```

Current publish generative runtime:

```text
qwen2.5-coder-7b-instruct
```

Embeddings are separate from the generative model.

Calculations and deterministic checks must be performed by application code/tools, not by LLM arithmetic.

---

## Engineering workflow

### 1. Dashboard

Project counts, runtime state, pipeline diagnostics, and health/honesty indicators.

### 2. Documents

Browse ingested project documents and open the File Inspector.

### 3. File Inspector

File Inspector separates evidence into four lanes:

```text
Consolidated Review
Full Metadata
Raw Deterministic Extraction
AI Output Only
```

AI Output Only is non-governing unless promoted through review/certification.

### 4. Facts

Review facts, inspect meaning/source/review state, and open lineage/evidence.

Trusted answer sources are:

```text
VALIDATED
HUMAN_CERTIFIED
```

Candidate facts are visible for review but do not silently govern answers. Rejected facts are excluded from trusted answer paths.

### 5. Expert Chat

Expert Chat gives a direct answer first, labels the basis of the answer, and exposes optional evidence lanes.

The visible chat is bound to the active project. Project A must not answer from Project B.

---

## Trust and evidence model

SerapeumAI separates:

- deterministic extraction;
- parser/OCR output;
- reviewed facts;
- linked support;
- AI-generated synthesis.

Rules:

- trusted facts outrank retrieval/vector support;
- vector/retrieval stores are derived support, not governing truth;
- AI Output Only is non-governing unless reviewed/promoted;
- support-only answers must not be presented as certified truth.

---

## Proven release-candidate behavior

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
- final packaging proof;
- packaged-app smoke on the owner Windows machine;
- publication documentation/license/repository hygiene.

---

## Known caveats

The current artifact passed packaging and packaged smoke, but these caveats remain important:

- broader Windows machine validation is still pending;
- constrained 8 GB VRAM laptops may show runtime, VRAM, or GPU-temperature warnings;
- model routing may downgrade analysis to chat when VRAM is limited;
- embeddings may load on CPU when VRAM is reserved or insufficient;
- page-level model-output parse retries can occur during AI-assisted analysis;
- `THIRD_PARTY_NOTICES.md` is a summary and is not a full legal dependency audit.

These caveats do not change the owner-machine packaging proof, but they are relevant before a wider public announcement.

---

## Explicit non-enabled behavior

The current release candidate does **not** enable or claim:

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

## Repository rules for contributors

- `src/**` is the primary editable source surface.
- `run.py` and `run_tests.py` are editable only when needed.
- `SerapeumAI_Portable.spec`, `build_portable.ps1`, and `build_portable.bat` are sensitive packaging files.
- Do not treat `build/**`, `dist/**`, `.serapeum/**`, `models/**`, or `**/__pycache__/**` as normal editing targets.
- Avoid dependency upgrades unless explicitly approved.
- Preserve Windows portability and packaging behavior.
- Prefer minimal, reviewable diffs.

See `CONTRIBUTING.md`.

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
