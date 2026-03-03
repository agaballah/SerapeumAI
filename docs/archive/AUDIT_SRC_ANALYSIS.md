# Audit: src/analysis_engine/ (Line-by-Line)

This document contains the exhaustive investigation of the `src/analysis_engine/` directory.

## 📄 [analysis_engine.py](file:///d:/SerapeumAI/src/analysis_engine/analysis_engine.py)

| Line Range | Description | Feature Contribution | Hardening Recommendation |
|------------|-------------|----------------------|---------------------------|
| 82-98 | Model Locking | Resource management | None (Good use of `ModelManager` semaphores). |
| 154-156 | Hierarchical RAG | Multi-tier context analysis | None (Solid architectural foundation). |
| 174-192 | Summary Polling | DB sync synchronization | **CRITICAL**: Replace the 5-second arbitrary poll with an event-driven trigger or async queue. |
| 271-275 | Rollup Prompts | LLM task instruction | Move hardcoded prompt strings to `prompts.yaml`. |
| 379-404 | Entity Normalization| Data quality engineering | Move normalization rules (Vendor/Standard) to a centralized `SchemaService`. |
| 440-548 | JSON Repair | Output resilience | Extract to a specialized `LLMOutputParser` utility. |

---

## 📄 [cross_doc_linker.py](file:///d:/SerapeumAI/src/analysis_engine/cross_doc_linker.py)

| Line Range | Description | Feature Contribution | Hardening Recommendation |
|------------|-------------|----------------------|---------------------------|
| 176-183 | Hierarchy Rules | Entity relationship mapping | **CRITICAL**: Move hardcoded hierarchy (space->floor->building) to `hierarchy_rules.yaml`. |
| 223 | Link Confidence | Baseline for graph edges | Externalize default confidence and decay math. |
| 285-296 | Conflict Detection | Data integrity verification | Standardize conflict resolution strategies (e.g., trust Specs over Drawings). |

---

## 📂 Sub-components
The following files provide supporting logic for the analysis engine:
- `page_analysis.py`: Tier 2 per-page summarization logic.
- `entity_analyzer.py`: Regex and LLM-assisted entity extraction.
- `transformation_engine.py`: Data format conversion for analysis tasks.
- `geometry_analyzer.py`: Spatial reasoning for layout-aware analysis.
