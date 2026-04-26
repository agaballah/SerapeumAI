# Runtime Distribution Consent Matrix

Task class: release task / post-publish runtime-distribution planning

Status: authoritative planning guardrail before runtime-provider implementation

This document defines how SerapeumAI should distinguish bundled baseline capability, detected local dependencies, optional providers, optional model downloads, and future workstation/enterprise lanes.

It exists to prevent three product failures:

1. bundling experimental or provider-specific runtime stacks into the normal desktop baseline by accident,
2. silently installing, downloading, launching, or using external components without user consent,
3. weakening SerapeumAI's local-first, privacy-first, evidence-first product contract while adding runtime flexibility.

---

## 1. Product doctrine

SerapeumAI remains a Windows-first, desktop-first, local-first AECO review workspace.

The normal app must be able to open, manage projects, inspect deterministic evidence, browse facts, and show clear runtime status without silently requiring cloud access, hidden downloads, or hidden provider installation.

AI runtimes, AI models, OCR tools, GPU acceleration, and enterprise services are capability lanes. They must be explicit, detectable, consent-gated, and optional unless a future release explicitly changes the product contract.

---

## 2. Non-negotiable consent rules

### 2.1 No silent internet

SerapeumAI must not use the internet without a clear user-triggered action or explicit consent.

Examples requiring consent:

- downloading model files,
- downloading runtime installers,
- opening external provider download pages,
- checking online model catalogs,
- checking online software updates,
- sending diagnostics outside the machine.

### 2.2 No silent model download

Models are large, license-sensitive, hardware-sensitive artifacts. The app must show at least:

- model name,
- model role,
- model source,
- license or license link where available,
- quantization / format,
- approximate download size,
- approximate disk footprint,
- target local storage path,
- whether internet is required,
- whether the model can be removed later.

### 2.3 No silent runtime installation

The app must not silently install LM Studio, Ollama, LocalAI, llama.cpp binaries, CUDA, TensorRT, Tesseract, Poppler, or other external dependencies.

The app may detect missing tools and offer setup guidance or consent-gated provisioning in a future wave.

### 2.4 No silent provider launch

Starting a provider process is a local side effect. It must be explicit unless the user has configured a persistent preference.

Examples:

- starting LM Studio server,
- starting Ollama service,
- launching a local inference server,
- loading/unloading a large model.

### 2.5 No silent truth promotion

Runtime memory, provider state, model output, vector retrieval, and chat history must never become certified project truth without the normal evidence/fact/review path.

---

## 3. Distribution categories

Every runtime-related component must be placed into exactly one category.

| Category | Meaning | Consent needed? | Example |
|---|---|---:|---|
| Bundled baseline | Included in normal EXE/package because the app needs it to operate safely | No, disclosed in docs | UI, SQLite, core Python runtime in PyInstaller bundle |
| Detected local dependency | Not bundled; app checks whether it already exists | No for detection; yes before use if side effects occur | LM Studio installed, Ollama installed, Tesseract installed |
| User-installed dependency | App explains what is missing; user installs outside app | User action outside app | LM Studio UI, Ollama installer, Poppler |
| Consent-gated app provisioning | App may download/install only after explicit approval | Yes | future model downloader, future runtime installer helper |
| Optional model artifact | Downloaded or selected by user; not required for app boot | Yes | GGUF text model, embedding model, VLM model |
| Workstation acceleration lane | Hardware-specific acceleration; never baseline | Yes | TensorRT, ONNX/Windows ML helper, CUDA-specific lane |
| Enterprise lane | Server/control-plane service; not desktop baseline | Yes + admin setup | Milvus, OpenSearch, Keycloak, NIM |
| Lab/experimental lane | Evaluation only; cannot govern baseline truth | Yes + feature flag | PaddleOCR-VL, Docling experiments, advanced VLM trials |

---

## 4. Baseline EXE policy

The baseline EXE/package should include only what is required for the stable desktop app and its already-approved local deterministic behavior.

### 4.1 Baseline bundled components

| Component | Baseline status | Notes |
|---|---|---|
| SerapeumAI desktop UI | Mandatory bundled | Core product surface |
| App boot path | Mandatory bundled | Must open without provider setup |
| SQLite/project DB logic | Mandatory bundled | Authoritative local truth store |
| Project/global `.serapeum` handling | Mandatory bundled | Storage topology contract |
| Deterministic local calculators/tools | Mandatory bundled | Calculations must be local and non-LLM |
| Deterministic extractors already supported safely | Mandatory bundled where stable | Must remain evidence-oriented |
| Logging/diagnostics | Mandatory bundled | Local logs only unless user exports them |
| Runtime discovery/advisor shell | Mandatory bundled | Read-only detection first |
| Consent UI/state model | Mandatory bundled before provisioning | Required before downloads/installs |

### 4.2 Not automatically bundled in baseline

| Component | Why not baseline-bundled |
|---|---|
| LM Studio application | Separate third-party runtime/provider |
| Ollama application/service | Separate third-party runtime/provider |
| LocalAI server | Server/provider lane, not desktop baseline |
| Large LLM model files | Too large, license/hardware-specific |
| Large VLM model files | Too large, optional, high hardware variance |
| TensorRT/TensorRT-LLM | Hardware/vendor-specific workstation lane |
| Milvus/OpenSearch/Keycloak/NIM | Enterprise/server lanes |
| Experimental OCR/VLM stacks | Packaging and license risk until proven |

---

## 5. Runtime provider matrix

| Provider | Baseline handling | Detection | Start/stop policy | Model policy | Data boundary |
|---|---|---|---|---|---|
| LM Studio UI/server | Optional provider | Probe local app/server/CLI when available | Do not auto-start without consent or saved preference | User selects/loads model in LM Studio or app requests explicit load if supported | Localhost only |
| LM Studio CLI | Optional provider control seam | Detect CLI path/version | All CLI actions are side effects; require explicit user action or saved preference | Load/unload must be visible in status/logs | Localhost/local process |
| Ollama | Optional provider | Probe localhost and CLI/service if installed | Do not install/start silently | Model pull requires explicit consent | Localhost/local process unless configured otherwise |
| Embedded GGUF / llama.cpp | Future baseline candidate | Detect bundled/runtime binary and model catalog | Session-owned local runtime; no internet unless downloading models | Recommended profile-based GGUF models | Local process |
| LocalAI/OpenAI-compatible local server | Optional advanced provider | Probe configured endpoint only | Do not install/start silently | User-managed or consent-gated future setup | Must disclose endpoint; local by default |
| Cloud OpenAI-compatible endpoint | Not baseline | Only if user configures | Never implicit | User-managed | Data leaves machine; must be labeled clearly |

---

## 6. Model artifact matrix

| Model role | Baseline policy | Download policy | Recommended format | Authority level |
|---|---|---|---|---|
| Router/classifier | Optional small local helper | Consent-gated if not bundled | GGUF Q4 or ONNX INT8 after proof | Support only |
| Main narrator | Optional local model | Consent-gated | GGUF Q4_K_M / Q5_K_M | Narrates retrieved governed truth; not authority |
| Structured JSON/tool model | Optional local model | Consent-gated | GGUF Q5_K_M preferred | Produces structured support; schema-validated |
| Evidence compressor | Optional local model | Consent-gated | GGUF Q4_K_M / Q5_K_M | Support only |
| Vision helper | Optional/on-demand | Consent-gated | VLM-specific profile | Labeled AI support only |
| Embedding model | Baseline candidate only if small and license-safe | Consent-gated if large | small local/ONNX/GGUF-compatible path | Derived retrieval only |
| Reranker | Optional | Consent-gated | small local/ONNX after proof | Derived retrieval support only |
| Calculator | Mandatory deterministic tool | No model | Python/local arithmetic | Deterministic authority for calculations |

---

## 7. Dependency matrix

| Dependency | Category | Baseline decision | Consent/instruction policy |
|---|---|---|---|
| Python runtime inside packaged build | Bundled baseline | Required for PyInstaller package | Disclosed; no user install required |
| SQLite | Bundled baseline | Required | No external setup |
| Tesseract OCR | Detected/user-installed or future provisioning | Optional OCR enhancement | Detect; explain missing capability; ask before install/download |
| Poppler/pdfinfo | Detected/user-installed or future provisioning | Optional PDF rendering/enhancement | Detect; explain missing capability; ask before install/download |
| CUDA toolkit | Workstation/system dependency | Not baseline | Detect only; do not install silently |
| TensorRT / TensorRT-LLM | Workstation acceleration | Not baseline | Feature-flagged; explicit setup |
| ONNX Runtime / Windows ML | Optional helper lane | Only after proof | Detect capability; no silent provider switch |
| OCRmyPDF | Optional evidence enhancement | Not baseline until packaging/legal proof | Consent-gated/lab first |
| PaddleOCR/PaddleOCR-VL | Lab lane | Not baseline | Feature flag; no truth authority |
| Docling/docling-parse | Lab lane | Not baseline | Feature flag; compare against deterministic baseline |
| Milvus/OpenSearch/Keycloak | Enterprise lane | Not desktop baseline | Admin-controlled deployment only |

---

## 8. Runtime status language

The UI must use clear status labels.

| Status | Meaning |
|---|---|
| Not detected | Component was not found locally |
| Detected | Component exists but is not necessarily running |
| Reachable | Local endpoint responded |
| Running | Process or service appears active |
| Ready | Required provider/model is available for the selected task |
| Missing optional dependency | Feature will be limited until installed |
| Needs consent | Internet/install/download/action is blocked pending approval |
| Disabled by user | User explicitly turned off this lane |
| Unsupported on this machine | Hardware/OS/profile cannot safely run it |

Avoid vague status labels such as `AI ready` unless the exact task/provider/model scope is known.

---

## 9. User-facing consent copy rules

Use plain language. Avoid service jargon.

### 9.1 Internet consent

Suggested wording:

> SerapeumAI can download this optional component. This will use the internet. Project documents will not be uploaded. Continue?

### 9.2 Model download consent

Suggested wording:

> Download this local AI model? It will be stored on this computer and used by your selected local runtime. Approximate size: `{size}`. Source: `{source}`. Continue?

### 9.3 Provider launch consent

Suggested wording:

> SerapeumAI can start the local `{provider}` service on this computer. This is needed for AI analysis/chat. Continue?

### 9.4 Cloud warning

Suggested wording:

> This endpoint is not local. Project text or prompts may leave this computer. Use only if your project rules allow it.

---

## 10. Privacy/data boundary matrix

| Action | Project data leaves machine? | Consent required | Notes |
|---|---:|---:|---|
| Open app | No | No | Baseline |
| Open project | No | No | Local storage |
| Run deterministic extraction | No | No | Unless external tools are configured remotely, which baseline forbids |
| Use local LM Studio/Ollama | No by default | Provider action may need consent | Localhost only |
| Download model | No project data leaves, but internet is used | Yes | Disclose source/size/license |
| Use cloud endpoint | Yes, prompts/data may leave | Yes + explicit warning | Not baseline |
| Export diagnostics manually | User-controlled | Yes/user action | Must not auto-upload |
| Enterprise server mode | Depends on deployment | Admin policy | Not desktop baseline |

---

## 11. Implementation sequencing

Do not implement provider provisioning before this matrix is accepted.

### Wave 1B-0 — Matrix freeze

- Add this document.
- Create a GitHub PR.
- Treat it as the runtime-distribution authority for the next implementation wave.

### Wave 1B-1 — Read-only provider discovery

- Detect LM Studio, Ollama, and OpenAI-compatible local endpoints.
- No install.
- No start.
- No model download.
- No provider mutation.

### Wave 1B-2 — Runtime status UI

- Show detected/reachable/ready states.
- Show missing optional dependencies honestly.
- No fake readiness.

### Wave 1B-3 — Consent state model

- Represent internet/download/install/provider-start consent as explicit state.
- Persist only user-approved preferences.

### Wave 1B-4 — Model catalog and recommendation

- Hardware-aware model recommendations.
- No download until consent.
- Store model role, quantization, size, license/source metadata.

### Wave 1B-5 — Consent-gated provisioning

- Only after discovery/status/catalog are proven.
- Start with model download, not runtime installer automation.

---

## 12. Acceptance gates

This matrix is accepted only if future implementation proves:

1. the app boots without optional providers,
2. missing providers do not crash the app,
3. internet is never used silently,
4. model downloads are never silent,
5. runtime installs are never silent,
6. provider start/load/unload actions are explicit or saved user preferences,
7. project data remains local unless the user intentionally configures a non-local endpoint,
8. cloud endpoints are visibly labeled as non-local,
9. vector/retrieval stores remain derived support, not truth authority,
10. memory/runtime state never becomes certified truth automatically.

---

## 13. Current decision

The next implementation should not be random packaging reduction.

The correct next direction is to build a runtime platform around:

- bundled baseline,
- read-only detection,
- explicit consent,
- provider abstraction,
- hardware-aware recommendation,
- user-selected models,
- and truthful privacy/status UI.

Heavy package graph reduction remains valid only when tied to this policy: move optional/provider/lab/enterprise components out of the baseline or behind explicit feature lanes without removing product capability.
