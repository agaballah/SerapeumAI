# Audit: src/db/ (Line-by-Line)

This document contains the exhaustive investigation of the `src/db/` directory.

## 📄 [database_manager.py](file:///d:/SerapeumAI/src/db/database_manager.py)

| Line Range | Description | Feature Contribution | Hardening Recommendation |
|------------|-------------|----------------------|---------------------------|
| 42-111 | `DatabaseManager.__init__` | Connection initialization | Move `SAFETY_MARGIN` and timeouts to `config.yaml`. |
| 138-162 | `transaction` CM | Atomic write orchestration | **THREAD SAFETY CHECK**: Ensure `_current_tx_conn` doesn't cross threads (use `threading.local`). |
| 215-509 | Schema Definition | Database blueprint | **CRITICAL**: Move hardcoded 300-line schema string to external `base_schema.sql`. |
| 519-580 | Manual Migrations | Logic-based schema evolution | Replace manual column checks with a versioned migration manager. |
| 812-838 | FTS5 Search | Global document retrieval | None (Good use of native SQLite FTS). |
| 911-963 | Block RAG | Semantic chunk retrieval | None (Excellent foundation for RAG). |
| 1032-1068 | Page Upsert Tuple | Core data persistence | **CRITICAL**: The 37-column positional tuple is highly fragile. Implement Dict-based binding or lightweight DAO. |
| 1076-1123 | Entity Graph | Phase 2 knowledge mapping | Standardize relationship types via an Enum. |
| 1223 | Aggregation Priority | Multi-source content merging | Move priority logic (Native > Vision > OCR) to a configurable policy. |
| 1438-1512 | Fortification Stats | Accuracy/Conflict tracking | None (Very efficient implementation). |
| 1517-1600 | Schedule Storage | Primavera/MS Project support | Ensure consistent date formatting (ISO-8601) for all start/finish fields. |
