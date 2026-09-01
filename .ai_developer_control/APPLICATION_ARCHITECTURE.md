# SerapeumAI Architecture Audit Report
**Date**: 2026-08-31
**Type**: Read-Only — No code changes proposed
**Performed by**: Nara + Aider (mistral-large)

---

## 1. Repository Tree

```
SerapeumAI/
├── .gitignore
├── CONTRIBUTING.md
├── INSTALL.md
├── README.md
├── THIRD_PARTY_NOTICES.md
├── SerapeumAI_Portable.spec
├── build_portable.bat
├── build_portable.ps1
├── run.py
├── .ai_developer_control/
├── DeveloperTools/
└── src/
    ├── application/
    │   ├── api/fact_api.py
    │   ├── services/file_inspector_presentation.py
    │   └── tools/ (tool_invocation_contract, tool_registry, tool_resolver)
    ├── domain/
    │   ├── facts/models.py
    │   └── templates/loader.py
    ├── engine/extractors/base.py
    ├── infra/
    │   ├── adapters/ (cancellation, lm_studio_service, model_manager, model_router)
    │   ├── persistence/database_manager.py
    │   ├── services/ (runtime_provider_discovery, runtime_setup_service)
    │   └── telemetry/ (llm_logger, safety_validator, structured_logging)
    ├── tests/ (5 test files)
    ├── ui/
    │   ├── components/ (attachment_handler, message_renderer)
    │   ├── settings/model_manager_panel.py
    │   └── styles/theme.py
    └── utils/ (error_handler, path_validator)
```

---

## 2. Entry Points

| Entry Point | File | Purpose |
|-------------|------|---------|
| Development | `run.py` | Sets APP_ROOT, applies Theme, checks Tesseract/Poppler, init logging/config/DB, launches MainApp |
| Packaged | `dist\SerapeumAI_Portable\SerapeumAI.exe` | Built via PyInstaller (SerapeumAI_Portable.spec) |
| Build | `build_portable.bat` → `build_portable.ps1` | Portable Windows build |

---

## 3. Architecture Layers

| Layer | Location | Key Components |
|-------|----------|----------------|
| Presentation | `src/ui/` | MainApp, MessageRenderer, AttachmentHandler, ModelManagerPanel, Theme |
| Application | `src/application/` | FactQueryAPI, FileInspectorPresentation, ToolRegistry, ToolResolver |
| Domain | `src/domain/` | Facts models (CANDIDATE/VALIDATED/HUMAN_CERTIFIED/REJECTED), Template loader |
| Engine | `src/engine/` | BaseExtractor (abstract), ExtractionResult dataclass |
| Infrastructure | `src/infra/` | DatabaseManager, LocalRuntimeSetupService, ModelRouter, LMStudioService, ModelManager, LLMLogger |
| Utils | `src/utils/` | ErrorHandler (severity-based), PathValidator (traversal protection) |

---

## 4. Key Technical Facts

### UI Framework
- **customtkinter (CTK)** — themed Tkinter
- Dark theme, Segoe UI / Consolas fonts

### Database
- **SQLite** with thread-local connection pooling (WAL mode, busy_timeout)
- Global DB: `.serapeum/global.sqlite3`
- Per-project DB: `.serapeum/<project>/serapeum.sqlite3`

### Key Tables (inferred)
`facts`, `fact_inputs`, `file_versions`, `documents`, `pages`, `doc_blocks`, `analysis`, `compliance`, `chat_history`, `entity_nodes`, `links`, `bim_elements`, `schedule_activities`, `vision_queue`, `vlm_audit_trail`, `model_preferences`, `model_benchmarks`, `model_usage`, `schema_version`

### Runtime / Model Integration
- **LM Studio** as primary local runtime
- **RuntimeProviderDiscovery** supports: LM Studio, Ollama, OpenAI-compatible
- Default generative model: `qwen2.5-coder-7b-instruct`
- Default embedding model: `sentence-transformers/all-MiniLM-L6-v2`
- Model selection priority: explicit config → cached → DB preference → benchmark → built-in → first available

### Runtime States
`STATUS_READY`, `STATUS_LMSTUDIO_NOT_INSTALLED`, `STATUS_CLI_NOT_AVAILABLE`, `STATUS_SERVER_NOT_RUNNING`, `STATUS_CHAT_MODEL_MISSING`, `STATUS_EMBEDDING_RUNTIME_NOT_READY`, `STATUS_MODEL_NOT_LOADED`, `STATUS_UNSUPPORTED_RUNTIME`, `STATUS_RUNTIME_UNREACHABLE`

### File Inspector — 4 Lanes
1. Consolidated Review
2. Full Metadata
3. Raw Deterministic Extraction (no AI)
4. AI Output Only (non-governing)

### Trust Model
`Deterministic Extraction > HUMAN_CERTIFIED Facts > VALIDATED Facts > AI Support`

---

## 5. Feature Map

| Feature | Status | Notes |
|---------|--------|-------|
| Project Ingestion | ✅ Implemented | PDF, Word, Excel, images |
| File Inspector (4 Lanes) | ✅ Implemented | |
| Facts Review / Certification | ✅ Implemented | CANDIDATE → VALIDATED → HUMAN_CERTIFIED / REJECTED |
| Expert Chat | ✅ Implemented | Evidence-labeled answers |
| Runtime Management | ✅ Implemented | Start/stop LM Studio, load/unload models, VRAM checks |
| Structured Logging | ✅ Implemented | JSON, LLM call logging |
| Path Validation | ✅ Implemented | Traversal protection |
| Tool System (contracts) | ✅ Defined | ToolRegistry + ToolResolver exist — no tools implemented yet |
| Snapshot Management | ✅ Implemented | Locks certified facts at a point in time |
| Vision Queue | ✅ Implemented | Queue-based vision processing |
| BIM Support | ✅ Implemented | `bim_elements` table |
| Schedule Support | ✅ Implemented | `schedule_activities` table |
| Benchmarking | ✅ Implemented | BenchmarkService (referenced in ModelRouter) |
| Packaging (Windows) | ✅ Implemented | PyInstaller → SerapeumAI.exe |
| Autonomous Tool Execution | ❌ Not Enabled | Explicitly excluded |
| MCP Integration | ❌ Not Enabled | |
| Revit Bridge | ❌ Not Enabled | |
| CPM Engine | ❌ Not Enabled | |
| PDF VLM Routing | ❌ Not Enabled | |
| Project Memory / Audit Persistence | ❌ Not Enabled | |

---

## 6. Known Gaps

### From README
- Only tested on owner's machine (Windows validation needed)
- 8 GB VRAM may show warnings; embeddings may fall to CPU
- No autonomous tool execution, no project memory, no snapshot governance

### From Code Analysis
- `main_window.py` not reviewed (referenced in run.py but not provided)
- `configuration_manager.py` not reviewed
- `migrations/*.sql` not reviewed — schema inferred only
- Concrete extractors (PDF, Word, Excel) not reviewed — only `BaseExtractor` abstract class
- `BenchmarkService` referenced in ModelRouter but not reviewed
- Tool system defined (ToolRegistry, ToolResolver) but no tools implemented
- Test coverage: 5 test files visible — no tests for FactQueryAPI, FileInspector, or UI

---

## 7. Architectural Strengths

1. Clear layer separation (Presentation / Application / Domain / Engine / Infrastructure)
2. Thread-safe database (WAL + thread-local pooling + global locks)
3. Evidence-first trust model enforced at data layer
4. Comprehensive runtime state detection
5. Portable Windows packaging with PyInstaller
6. RuntimeProviderDiscovery already supports multiple providers (LM Studio, Ollama, OpenAI-compatible)

---

## 8. Recommended Investigation Order (Next Sessions)

| Priority | File | Why |
|----------|------|-----|
| 1 | `src/ui/main_window.py` | Full startup wiring |
| 2 | `src/infra/config/configuration_manager.py` | Config system |
| 3 | `src/infra/persistence/migrations/*.sql` | True DB schema |
| 4 | `src/engine/extractors/*.py` | Concrete extractor implementations |
| 5 | `src/infra/services/benchmark_service.py` | Model selection logic |
| 6 | `src/infra/adapters/vector_store.py` | Embedding pipeline |
| 7 | `src/application/orchestrators/*.py` | Agent orchestration |
| 8 | All remaining `src/ui/*.py` | Full UI surface |
