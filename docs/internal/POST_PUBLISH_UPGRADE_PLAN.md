# SerapeumAI Post-Publish Upgrade Plan

Task class: release task / post-publish planning artifact
Status: authoritative internal plan after current publish closure
Branch policy: `main` is the only long-lived authority

---

## 1. Purpose

This document freezes the post-publish upgrade direction for SerapeumAI after the current publish rail is closed. It replaces scattered planning issues and stale runtime branches as the active upgrade-control artifact.

The plan is intentionally repo-aware and release-protective. It is not an implementation patch and it is not permission to widen the current publish closure scope.

---

## 2. Fixed product line

SerapeumAI remains a Windows-first, desktop-first, local-first AECO truth workspace.

It is not:

- a generic chatbot,
- a loose RAG viewer,
- a cloud-required product,
- a design-authoring tool,
- an autonomous agent that edits files or models without user trigger,
- or a compliance certifier that guarantees legal approval.

The core product chain remains:

```text
Ingest -> Extract -> Normalize/Link -> Build Facts -> Validate/Certify -> Snapshot -> Chat
```

The governing doctrine remains:

- deterministic extraction before AI narration,
- facts and lineage before fluent answers,
- certified/trusted facts as the strongest authority,
- refusal when required truth is missing,
- human-in-the-loop review,
- explicit separation between deterministic evidence, linked support, and AI-generated support.

---

## 3. GitHub cleanup policy after this plan is merged

After this file is merged to `main`, GitHub should be cleaned so `main` is the only durable authority.

### Keep

- `main`
- this internal plan
- future short-lived packet branches only

### Delete or close after confirmation

- stale planning issues,
- stale runtime-advisor branches,
- stale packet branches identical to `main`,
- PRs that represent partial runtime work but not the full approved upgrade plan.

### Important

Do not merge broad runtime-advisor branches into `main` merely because they contain useful ideas. Mine useful design decisions, then reimplement in bounded packets.

---

## 4. Publish boundary before upgrades

Post-publish upgrade implementation starts only after the publish closure rail passes.

Current publish closure must prove:

1. storage topology is clean,
2. Facts page and chat agree on trusted facts,
3. review/certify/reject actions work on the mounted Facts page,
4. dashboard labels do not overclaim trust or health,
5. File Inspector tabs are real and separated,
6. retrieval is project-isolated,
7. extractor/build outputs are evidence-built,
8. UI shutdown and project close are clean on Windows,
9. user docs match shipped behavior,
10. packaging proof passes last.

No post-publish upgrade may be used to hide an unresolved publish defect.

---

## 5. Upgrade roadmap overview

Recommended post-publish order:

```text
0. Clean GitHub authority after this plan is merged
1. Smarter Local Intelligence
2. Tool-Using Chat, Skills, and Memory Spine
3. Quantization Strategy and Model Fit Matrix
4. Workspace Honesty
5. Schedule Truth Workspace
6. Engineering-Grade Evidence Baseline
7. Document Center / File Inspector Upgrade
8. Optional OCR / Layout / Vision Lab
9. Safe Revit Bridge
10. Optional Acceleration and Ecosystem Lanes
11. Runtime Platform Wave
```

---

## 6. Upgrade 1 — Smarter Local Intelligence

### Objective

Make SerapeumAI smarter on normal engineering laptops, especially Windows machines around 16 GB RAM and RTX 4060 Laptop / 8 GB VRAM class, without requiring a giant always-on model.

### Baseline direction

- Embedded GGUF + llama.cpp becomes the preferred future baseline runtime.
- LM Studio remains an optional provider mode.
- Ollama and LocalAI-style OpenAI-compatible providers may be added later behind the same provider contract.
- Runtime selection must be manifest/profile driven.
- Model loading must avoid heavy user-visible churn.

### Required components

- `RuntimeProfile`: Safe, Balanced, Visual, Workstation.
- `HardwareProfile`: CPU/GPU/RAM/VRAM detection.
- `ModelCatalog`: model role, quant, provider, memory requirements.
- `ProviderRegistry`: installed/runtime provider discovery.
- `RecommendationEngine`: profile/model recommendation.
- `ModelRoleManifest`: router, narrator, structured JSON, compressor, vision, embeddings, reranker.

### Non-negotiable

Calculations never run through the LLM. The app executes deterministic calculation tools and the LLM only narrates verified results.

### Likely future surfaces

- `src/infra/adapters/llm_service.py`
- `src/infra/adapters/model_manager.py`
- `src/infra/adapters/model_router.py`
- `src/infra/services/benchmark_service.py`
- `src/infra/services/model_recommender.py`
- runtime setup / settings UI

### Risks

- Packaging risk: high if native runtimes are mixed too early.
- Windows risk: medium/high because of GPU/native binaries.
- Rollback risk: low if runtime choices remain manifest-driven.

---

## 7. Upgrade 1B — Tool-Using Chat, Skills, and Memory Spine

### Objective

Convert chat into a bounded AECO tool-using truth assistant.

### Core rule

```text
The LLM may choose tools and fill arguments.
The application executes tools.
The LLM narrates verified results.
The LLM does not calculate, certify, or silently create truth.
```

### Tool registry contract

Every tool must declare:

- `tool_id`
- `input_schema`
- `output_schema`
- `authority_level`
- `scope`
- `side_effects`
- `requires_consent`
- `can_govern_truth`
- `audit_log_required`

### First deterministic tools

- calculator tool,
- unit conversion tool,
- quantity/formula tool,
- fact query tool,
- evidence retrieval tool,
- schedule query tool,
- metadata inspection tool,
- register/table comparison tool,
- file inspector query tool.

### Serapeum skills

- `schedule_review.skill`
- `drawing_inspection.skill`
- `submittal_tracker.skill`
- `quantity_check.skill`
- `metadata_audit.skill`
- `claim_clause_review.skill`
- `ifc_ids_validation.skill`

### Memory separation

- session memory: active chat only,
- project memory: project DB only,
- user preferences: global DB only,
- runtime/tool memory: diagnostics only.

Memory may support UX, but it must never silently become certified truth.

### Forbidden

- arbitrary MCP execution in baseline,
- autonomous file edits,
- internet tools by default,
- memory as certified fact,
- LLM arithmetic.

---

## 8. Upgrade 1C — Quantization Strategy and Model Fit Matrix

### Objective

Make local model selection hardware-aware, role-aware, and truth-aware.

### Baseline quantization policy

| Profile | Quantization |
|---|---|
| Safe | GGUF Q4_K_M / Q4_K_S |
| Balanced | GGUF Q4_K_M |
| Preferred quality | GGUF Q5_K_M |
| Quality/reference | GGUF Q6_K / Q8_0 |
| Helper ONNX | INT8 only after proof |
| Workstation lab | AWQ / GPTQ / EXL2 / TensorRT experiments only |

### Model role fit

| Role | Preferred quantization |
|---|---|
| router/classifier | small GGUF Q4 or ONNX INT8 |
| answer narrator | GGUF Q4_K_M / Q5_K_M |
| structured JSON/tool model | Q5_K_M preferred |
| evidence compressor | Q4_K_M / Q5_K_M |
| vision helper | optional/on-demand |
| embeddings/reranker | small local/ONNX |
| calculations | no LLM |

### QuantBench must test

- tool-call correctness,
- JSON validity,
- refusal behavior,
- citation discipline,
- evidence preservation,
- schedule-tool routing,
- no hallucinated calculation,
- Arabic/English routing,
- repeatability.

### Rule

GGUF is baseline. AWQ/GPTQ/EXL2/TensorRT stay workstation experiments until proven and explicitly approved.

---

## 9. Upgrade 2 — Workspace Honesty

### Objective

Make every visible surface mean exactly one thing.

### Locked rules

- Chat means this project + this snapshot + this truth scope.
- Normal DB is authority.
- Vector DB is derived retrieval only.
- Snapshot is real or not shown as real.
- Facts page and chat must agree.
- Project A must never answer from Project B.

### Canonical status vocabulary

- `CANDIDATE`
- `VALIDATED`
- `HUMAN_CERTIFIED`
- `REJECTED`
- `REFUSED`

### Required work

- scope-bound chat sessions,
- real snapshot object,
- unified review state machine,
- startup schema audit,
- storage topology audit,
- one mounted review/truth chain.

### Likely future surfaces

- `src/application/api/fact_api.py`
- `src/application/services/coverage_gate.py`
- `src/application/services/scope_router.py`
- `src/application/orchestrators/agent_orchestrator.py`
- `src/domain/facts/models.py`
- `src/domain/facts/repository.py`
- `src/infra/persistence/database_manager.py`
- `src/infra/adapters/vector_store.py`
- chat/facts/snapshot UI surfaces

### Risks

- Packaging risk: low.
- Windows risk: medium due path/storage behavior.
- Rollback risk: medium because semantics tighten.

---

## 10. First visible slice — Schedule Truth Workspace

### Objective

Deliver one strong AECO-native workflow early after publish.

### Direction

- Schedule page authority comes from certified schedule facts.
- Raw P6/XER staging remains diagnostic only.
- Snapshot governs schedule view.
- Schedule chat uses schedule-specific tools/templates.
- Clicking activities reveals evidence and lineage.
- Critical path/float are shown only when deterministic data supports them.

### Deliverables

- schedule fact builder hardening,
- schedule graph engine,
- float/critical path gate,
- schedule query tool,
- evidence-linked task view,
- schedule-specific refusal behavior.

### Acceptance

- known XER fixture passes,
- activity dates match,
- missing float/critical path support refuses instead of overclaiming,
- schedule UI and chat agree.

---

## 11. Upgrade 3 — Engineering-Grade Evidence Baseline

### Objective

Turn evidence into typed, provenance-rich engineering data.

### Baseline evidence stack

| File type | Baseline |
|---|---|
| PDF | PyMuPDF/native extraction plus qpdf/pikepdf inspection/repair |
| Scanned PDF | OCRmyPDF/Tesseract/OpenCV after classification |
| IFC | IfcOpenShell traversal |
| IFC validation | IfcTester / IDS lane |
| P6/XER | deterministic schedule graph |
| Office | native DOCX/XLSX/PPTX extraction |
| Images/drawings | OCR/vision support with quality gates |

### Typed evidence packet fields

- file id,
- file version id,
- page/sheet/row/cell/GUID/activity id,
- bbox where applicable,
- extractor name/version,
- source lane,
- confidence/quality,
- lineage anchor.

### Acceptance fixtures

- gold text PDF,
- gold scanned PDF,
- gold mixed PDF,
- gold IFC,
- gold XER/P6,
- gold Excel/register,
- gold drawing/image.

---

## 12. Upgrade 4 — Document Center / File Inspector

### Objective

Make File Inspector the human verification cockpit.

### Required tabs

1. Consolidated Review
2. Full Metadata
3. Raw Deterministic Extraction
4. AI Output Only

### Tab rules

- Consolidated Review may summarize but must label source lanes.
- Full Metadata must expose audit-relevant file/container metadata where available.
- Raw Deterministic Extraction must contain parser/OCR output and counts, not AI narration.
- AI Output Only must contain AI/VLM/support material and must be clearly non-governing unless promoted through review/certification.

---

## 13. Upgrade 5 — Optional OCR / Layout / Vision Lab

### Objective

Benchmark powerful document-AI tools without polluting the baseline.

### Candidate lanes

- Docling / docling-parse,
- PaddleOCR / PaddleOCR-VL,
- layout/table extraction helpers,
- Qwen/Gemma/LFM-style VLM helpers,
- drawing interpretation helpers.

### Rules

- lab output never governs truth,
- all output is labeled support,
- deterministic baseline remains primary,
- no packaging-hostile dependency enters baseline without review,
- no GPL/AGPL component enters distributable baseline without explicit legal/packaging approval.

---

## 14. Upgrade 6 — Safe Revit Bridge

### Objective

Connect Revit to SerapeumAI safely without making SerapeumAI a design-authoring product.

### Locked direction

- thin Revit add-in,
- local file-based handoff first,
- read-only MVP,
- no autonomous authoring,
- no silent model edits,
- no cloud-required path.

### MVP commands

- export selected elements,
- export selected views,
- export review package,
- reopen issue package.

### Future path

- BCF issue package,
- IFC package,
- Revit GUID mapping,
- local report round-trip,
- controlled write-back only after explicit approval.

---

## 15. Upgrade 7 — Optional Acceleration and Ecosystem Lanes

### Objective

Add power without narrowing the product.

### Support tiers

| Tier | Allowed |
|---|---|
| Baseline | llama.cpp/GGUF, SQLite, deterministic tools, local evidence |
| Optional | LM Studio, Ollama, Chroma, OCRmyPDF/Tesseract, ONNX/Windows ML |
| Workstation | TensorRT for RTX, TensorRT-LLM, AWQ/GPTQ/EXL2, advanced VLM/OCR |
| Enterprise | NIM, Milvus, OpenSearch, Keycloak, server/control plane |

### Rules

- NVIDIA improves performance but is not required.
- Containers are not baseline.
- Cloud is not baseline.
- Enterprise stack is not the desktop promise.
- Optional lanes must fail gracefully.

---

## 16. Runtime Platform Wave

### Objective

Build the future shareable runtime/distribution system.

### Required components

- `ProviderAdapter`
- `ProviderRegistry`
- `HardwareProfile`
- `ModelCatalog`
- `RecommendationEngine`
- `SessionOrchestrator`
- consent-gated runtime actions

### Distribution strategy

- bootstrap EXE,
- portable/offline bundle,
- enterprise package later.

### Non-negotiables

- no silent internet,
- no silent installs,
- no silent model downloads,
- ask before using internet,
- ask before downloading models,
- detect before provisioning.

---

## 17. Standing implementation rules

- Treat `src/**` as primary editable code.
- Touch `run.py` only when needed.
- Packaging files are sensitive and require explicit approval:
  - `SerapeumAI_Portable.spec`
  - `build_portable.ps1`
  - `build_portable.bat`
- Do not treat these as edit targets:
  - `build/**`
  - `dist/**`
  - `.serapeum/**`
  - `models/**`
  - `**/__pycache__/**`
- No dependency upgrades unless explicitly approved.
- Preserve Windows portability.
- Prefer minimal, reviewable diffs.

---

## 18. First implementation packet after this document

### Packet PP-001 — GitHub authority cleanup

Task class: release task

Objective: after this file is merged to `main`, close/delete stale GitHub planning surfaces and make `main` the only long-lived authority.

Allowed:

- close stale planning issues,
- close stale partial-runtime PRs,
- delete branches identical to `main`,
- delete partial runtime branches after confirming no unique required code remains.

Forbidden:

- no source edits,
- no packaging edits,
- no dependency edits,
- no broad runtime merge,
- no publish claim.

Exit condition:

- `main` contains this plan,
- no stale planning issue is treated as authority,
- no stale branch is treated as authority,
- future work starts from short packet branches only.

---

## 19. Short status line

Past: publish doctrine and upgrade direction consolidated.
Current: archive plan into repo, then clean GitHub authority.
Next: finish publish closure, then start post-publish Upgrade 1.
