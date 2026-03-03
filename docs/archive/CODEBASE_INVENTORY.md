# SerapeumAI Codebase Inventory

This document tracks the line-by-line audit and production hardening status of every file in the repository.

## Inventory Legend
- **Audit Status**: ⚪ Not Started | 🟡 In-Progress | ✅ Complete
- **Hardening Status**: ⚪ Not Started | 🟡 In-Progress | ✅ Complete

---

## 📂 src/core/

| File | Feature Contribution | Audit | Hardened |
|------|----------------------|-------|----------|
| `correction_collector.py` | Feedback collection for learning | ✅ | ⚪ |
| `confidence_learner.py` | Historical accuracy blending | ✅ | ⚪ |
| `prompt_optimizer.py` | Dynamic prompt engineering | ✅ | ⚪ |
| `model_selector.py` | Resource-aware model choice | ✅ | ⚪ |
| `cross_modal_validator.py`| OCR/VLM/Spatial reconciliation| ✅ | ⚪ |
| `resilience_framework.py`| Failure handling & DLQ | ✅ | ⚪ |
| `prompt_validator.py` | Security & Length validation | ✅ | ⚪ |
| `resource_monitor.py` | VRAM/Memory detection | ✅ | ⚪ |
| `pdf_processor.py` | Multi-modal PDF ingestion | ✅ | ⚪ |
| `ifc_processor.py` | BIM/IFC data extraction | ✅ | ⚪ |
| `schedule_processor.py` | Project schedule analysis | ✅ | ⚪ |

---

## 📂 src/core/safety/

| File | Feature Contribution | Audit | Hardened |
|------|----------------------|-------|----------|
| `safety_validator.py` | Gate orchestration | ✅ | ⚪ |
| `confidence_gate.py` | Precision thresholds | ✅ | ⚪ |
| `anomaly_detector.py` | Statistical outlier detection| ✅ | ⚪ |
| `consistency_validator.py`| Logical rule enforcement | ✅ | ⚪ |
| `safety_types.py` | Error schemas | ✅ | ⚪ |

## 📂 src/db/

| File | Feature Contribution | Audit | Hardened |
|------|----------------------|-------|----------|
| `database_manager.py` | Multi-tenant SQLite storage | ✅ | ⚪ |

## 📂 src/analysis_engine/

| File | Feature Contribution | Audit | Hardened |
|------|----------------------|-------|----------|
| `analysis_engine.py` | Hierarchical RAG orchestration | ✅ | ⚪ |
| `compliance_analyzer.py`| Rules-based verification | ✅ | ⚪ |
| `cross_doc_linker.py` | Entity graph construction | ✅ | ⚪ |

---

## 📂 src/telemetry/

| File | Feature Contribution | Audit | Hardened |
|------|----------------------|-------|----------|
| `structured_logging.py` | JSONL pipeline logs | ✅ | ⚪ |
| `metrics.py` | Performance time-series | ✅ | ⚪ |
| `metrics_collector.py` | Aggregated dashboard stats | ✅ | ⚪ |
