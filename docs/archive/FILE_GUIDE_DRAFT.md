# Repository File Guide (Draft)

This document provides a detailed mapping of every file in the SerapeumAI repository, categorized by functional area.

## 1. Core Logic (`src/core/`)
Responsible for the fundamental AI processing, safety, and learning logic.

- `src/core/correction_collector.py`: Captures human feedback to identify AI error patterns.
- `src/core/confidence_learner.py`: Blends AI self-confidence with historical accuracy data.
- `src/core/prompt_optimizer.py`: Generates specialized, few-shot prompts based on learned errors.
- `src/core/model_selector.py`: Logic for choosing the best model (Qwen2 vs Mistral) for a specific task.
- `src/core/cross_modal_validator.py`: (Phase 1) Reconciles OCR, VLM, and spatial layout data.
- `src/core/resilience_framework.py`: (Phase 1) Handles fallback logic and dead-letter queuing.
- `src/core/safety/safety_validator.py`: Orchestrates safety gates.
- `src/core/safety/confidence_gate.py`: Enforces minimum confidence thresholds.
- `src/core/safety/anomaly_detector.py`: Statistical outlier detection.
- `src/core/safety/consistency_validator.py`: Enforces engineering relationship rules.

## 2. Document Processing (`src/document_processing/`)
Handle ingestion and parsing of various AECO formats.

- `src/document_processing/document_service.py`: Main entry point for project document ingestion.
- `src/document_processing/pdf_processor.py`: Native text and metadata extraction from PDFs.
- `src/document_processing/ifc_processor.py`: BIM element extraction from IFC files.
- `src/document_processing/schedule_processor.py`: Primavera/MS Project schedule parsing.

## 3. Computer Vision (`src/vision/`)
The visual intelligence layer.

- `src/vision/adaptive_extraction.py`: Two-stage VLM extraction (Classification → Specialized).
- `src/vision/vision_caption_v2.py`: Generates detailed visual descriptions of drawing segments.

## 4. Analysis Engine (`src/analysis_engine/`)
High-level derivation of engineering insights.

- `src/analysis_engine/page_analysis.py`: Standard per-page technical summary.
- `src/analysis_engine/adaptive_analysis.py`: Multi-modal "unified context" analyst.

## 5. Database & Infrastructure (`src/db/`)
- `src/db/database_manager.py`: SQLite interface with project-scoped schemas.
- `src/db/migrations/`: SQL scripts for evolving the audit and validation schemas.

## 6. Telemetry & Observability (`src/telemetry/`)
- `src/telemetry/metrics_collector.py`: Tracks latency and quality metrics.
- `src/telemetry/structured_logging.py`: Generates machine-readable JSON logs for pipeline events.

## 7. Configuration & Project Root
- `config.yaml`: Global settings for model paths and thresholds.
- `run.py`: GUI / Application entry point.
