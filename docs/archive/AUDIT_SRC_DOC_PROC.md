# Audit: src/document_processing/ (Line-by-Line)

This document contains the exhaustive investigation of the `src/document_processing/` directory.

## 📄 [document_service.py](file:///d:/SerapeumAI/src/document_processing/document_service.py)

| Line Range | Description | Feature Contribution | Hardening Recommendation |
|------------|-------------|----------------------|---------------------------|
| 50-89 | `SUPPORTED_EXT` | Ingestion scope defining | Move to `config.yaml` to allow user-defined extensions. |
| 173 | REQUEUE_VISION | Auto-trigger for VLM | Make auto-queueing configurable (some may want OCR only). |
| 200-204 | Hash Check | Process idempotency | Add a `force_reprocess` flag to override hash matches. |
| 224-228 | Standards Routing | Global knowledge separation | **CRITICAL**: Move hardcoded keywords to a `standards_registry.yaml`. Upgrade to regex/ML classifier. |
| 272-287 | Page Ingestion | DB persistence | Ensure `layout_json` schema is consistent across PDF and Image processors. |
| 300-304 | Structured Route | Specialized processing | Decouple from file extensions; use `DocumentClassifier` results instead. |
| 333-341 | `ignore_dirs` | File system safety | Move list to `config.yaml`. |
| 438-443 | Vision Prio | Resource-aware queueing | None (Excellent engineering priority logic). |

---

## 📄 [pdf_processor.py](file:///d:/SerapeumAI/src/document_processing/pdf_processor.py)

| Line Range | Description | Feature Contribution | Hardening Recommendation |
|------------|-------------|----------------------|---------------------------|
| 109-113 | Tesseract Search | Windows environment setup | Move static paths to `config.yaml`. |
| 173 | `merge_text_signals` | Arabic-aware consolidation | Ensure consistent normalization across all processors. |
| 302 | `Y_TOLERANCE` | Line-grouping heuristic | Make configurable or derive from median font size. |
| 500 | Vector Thresholds | CAD drawing detection | **CRITICAL**: Move `VECTOR_OP_THRESHOLD` (250) and Area (500k) to `config.yaml`. |
| 543-569 | Page Classifier | Intelligent Vision Gating | Extract to a separate `PageTypeStrategy` module for testability. |
| 703 | `MAX_DIM` | Image compute caps | Move 2048px limit to global resource policy. |
| 942 | Title Keywords | AECO document identification | Move to `domain_constants.yaml`. |
| 995 | Dotted Leaders | TOC/Index detection | None (Excellent regex heuristic). |
| 1000-1060 | Heading Parser | Semantic block foundation | Standardize regex patterns in a shared `AECO_patterns.py` file. |
| 1061-1138| `_build_blocks` | Structural RAG orchestration | Support recursive block nesting for multi-level headings. |

---

## 📄 [ifc_processor.py](file:///d:/SerapeumAI/src/document_processing/ifc_processor.py)

| Line Range | Description | Feature Contribution | Hardening Recommendation |
|------------|-------------|----------------------|---------------------------|
| 40-46 | Dependency Check | `ifcopenshell` validation | Standardize error messages for missing binary dependencies. |
| 98-246 | BIM Flattening | Structured attribute extraction | Move target element types (IfcWall, etc.) to `bim_registry.yaml`. |
| 108-131 | LLM Summary | Markdown generation | Use Jinja2 for flexible BIM-to-text templating. |
| 284-289 | Importance Filter | Key property selection | **CRITICAL**: Make `important_keys` configurable by discipline/role. |
| 305-333 | Spatial Relations | Semantic graph building | Store relationship types in a standardized BIM schema. |
| 372-379 | Group Mapping | MEP/Structural categorization | Externalize conceptual grouping to a schema file. |

---

## 📄 [schedule_processor.py](file:///d:/SerapeumAI/src/document_processing/schedule_processor.py)

| Line Range | Description | Feature Contribution | Hardening Recommendation |
|------------|-------------|----------------------|---------------------------|
| 114-161 | XER Extraction | Primavera P6 support | Implement robust P6 schema mapping (e.g., UDFs and specific task types). |
| 164-232 | XML Extraction | MS Project support | Ensure consistent date/time parsing for international formats. |
| 234-266 | MPP Processor | Stub for binary format | **CRITICAL**: Implement `python-msp` or `mpxj` wrapper to enable native MPP support. |
| 268-299 | XER Section Parser | Custom delimiter logic | Support multi-encoding (UTF-8/UTF-16) common in project exports. |
| 302-315 | Critical Path Calc | Simplified float heuristic| Upgrade to full CPM (Critical Path Method) logical traversal. |
| 333 | Narrative Limit | Hardcoded 10-task cap | Move narrative summarization to `PromptOptimizer` logic. |
