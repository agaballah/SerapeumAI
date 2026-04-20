# -*- coding: utf-8 -*-
# Copyright (c) 2025 Ahmed Gaballa
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
adaptive_extraction.py — Two-stage intelligent prompting with VLM-guided specialization
-----------------------------------------------------------------------------------
Implements:
1. Stage 1: Quick Classification (Classifier)
2. Stage 2: Specialized Extraction (Specialized Extractor)
"""

import json
import logging
import time
from typing import Dict, Any, List, Optional, Tuple, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from src.utils.retry import retry, RetryStrategy, RetryError
from src.domain.vision.cross_modal_validator import CrossModalValidator
from src.domain.intelligence.prompt_validator import validate_prompt, sanitize_user_prompt
from src.infra.telemetry.safety_validator import SafetyValidator
from src.infra.telemetry.metrics_collector import MetricsCollector
from src.infra.telemetry.structured_logging import AILogger

logger = logging.getLogger("vision.adaptive")
ai_logger = AILogger("vision.adaptive")


class DocumentClassification(Enum):
    """AECO document types requiring different extraction strategies"""
    FLOOR_PLAN = "floor_plan"
    SECTION = "section"
    ELEVATION = "elevation"
    DETAIL = "detail"
    ELECTRICAL_PLAN = "electrical_plan"
    MECHANICAL_PLAN = "mechanical_plan"
    PLUMBING_PLAN = "plumbing_plan"
    STRUCTURAL_PLAN = "structural_plan"
    SCHEDULE = "schedule"
    SPECIFICATION = "specification"
    DETAIL_SHEET = "detail_sheet"
    ROOF_PLAN = "roof_plan"
    SITE_PLAN = "site_plan"
    RISER_DIAGRAM = "riser_diagram"
    EQUIPMENT_SCHEDULE = "equipment_schedule"
    DOOR_SCHEDULE = "door_schedule"
    WINDOW_SCHEDULE = "window_schedule"
    LEGEND = "legend"
    TITLE_BLOCK = "title_block"
    UNKNOWN = "unknown"
    EMBEDDED_GRAPHIC = "embedded_graphic"


@dataclass
class QuickIdentificationResult:
    """Stage 1 output: Quick document classification"""
    document_type: DocumentClassification
    sheet_number: str
    revision: str
    project_name: str
    page_context: str  # What is on this page
    key_systems: List[str]  # HVAC, Electrical, Plumbing, etc.
    confidence: float  # 0-100
    extracted_text_snippets: List[str]  # Key readable text
    raw_response: Dict[str, Any]


@dataclass
class DetailedExtractionResult:
    """Stage 2 output: Specialized detailed extraction"""
    document_identity: Dict[str, Any]
    geometric_data: List[Dict[str, Any]]
    technical_systems: List[Dict[str, Any]]
    cross_references: List[str]
    specifications: List[Dict[str, Any]]
    notes_and_legends: List[str]
    quality_assessment: Dict[str, Any]
    raw_response: Dict[str, Any]


class AdaptivePromptSelector:
    """Selects specialized prompts based on document classification"""
    
    # Stage 1 and Stage 2 prompts are now externalized in src/domain/templates/prompts.yaml
    # Use TemplateLoader to retrieve them.
    
    def __init__(self):
        from src.domain.templates.loader import get_template_loader
        self.loader = get_template_loader()

    def get_specialized_prompt(self, doc_type: DocumentClassification) -> Tuple[str, str]:
        """Get specialized system/user prompts for document type"""
        # Map enum to YAML key
        key_map = {
            DocumentClassification.FLOOR_PLAN: "floor_plan",
            DocumentClassification.ELECTRICAL_PLAN: "electrical_plan",
            DocumentClassification.MECHANICAL_PLAN: "mechanical_plan",
            DocumentClassification.SCHEDULE: "schedule",
            DocumentClassification.SECTION: "section",
            DocumentClassification.DETAIL: "detail",
            DocumentClassification.EMBEDDED_GRAPHIC: "embedded_graphic",
        }
        
        persona_key = key_map.get(doc_type, "generic")
        p = self.loader.get_prompt("vision.personas", persona_key)
        
        if not p["system"]:
            # Final fallback to generic
            p = self.loader.get_prompt("vision.personas", "generic")
            
        return p["system"], p["user"]

    def get_stage1_prompts(self) -> Tuple[str, str]:
        """Get Stage 1 system and user prompts"""
        p = self.loader.get_prompt("vision")
        return p["system"], p["user"]


class TwoStageVisionEngine:
    """Two-stage adaptive VLM extraction with self-guided specialization"""
    
    def __init__(self, llm_service, db=None, safety_validator=None, metrics_collector=None):
        self.llm = llm_service
        self.selector = AdaptivePromptSelector()
        # Cross-modal validator to reconcile native/vision/spatial sources
        try:
            self.cross_validator = CrossModalValidator()
        except Exception:
            self.cross_validator = None
            
        # Phase 3: Safety and Observability
        self.safety = safety_validator or SafetyValidator()
        self.metrics = metrics_collector or MetricsCollector(db=db)
        
        # Optional resilience integration
        self.db = db
        try:
            from src.core.resilience_framework import ResilienceFramework
            self.resilience = ResilienceFramework(db) if db is not None else None
        except Exception:
            self.resilience = None
    
    def _parse_stage1_json(self, content: str) -> Dict[str, Any]:
        """Robustly parse JSON from Stage 1 response using centralized parser"""
        from src.utils.parser_utils import robust_json_parse
        
        obj = robust_json_parse(content)
        
        if not obj:
            logger.warning("Failed to parse Stage 1 JSON. Using fallback.")
            # Fallback extraction if JSON fails
            return {
                "document_type": "unknown",
                "sheet_number": "unknown",
                "revision": "unknown",
                "what_is_shown": content[:200],
                "confidence": 0
            }
        
        return obj

    def process_page_two_stage(
        self,
        image_path: str,
        py_text: str = "",
        ocr_text: str = "",
        doc_id: Optional[str] = None,
        page_index: int = 0,
        field_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        End-to-end two-stage processing
        Returns a consolidated result dict.
        """
        try:
            # Stage 1: Quick classification
            start_time = time.time()
            stage1_result = self.stage1_quick_identification(image_path, py_text)
            self.metrics.record_latency("vision_stage1", time.time() - start_time)
            self.metrics.record_accuracy("classification", stage1_result.confidence / 100.0)
            
            # Stage 2: Specialized extraction
            start_time = time.time()
            stage2_result = self.stage2_specialized_extraction(image_path, stage1_result)
            self.metrics.record_latency("vision_stage2", time.time() - start_time)
            
            # Phase 3.1: Safety Validation
            # Merge provided metadata with context-specific defaults
            default_meta = {"document_type": stage1_result.document_type.value}
            combined_meta = {**default_meta}
            if field_metadata:
                combined_meta.update(field_metadata)
                
            safety_result = self.safety.validate_extraction(
                stage2_result.raw_response,
                field_metadata=combined_meta
            )
            
            self.metrics.record_metric("safety_violations", len(safety_result.violations))
            if not safety_result.is_safe:
                ai_logger.track_pipeline_event(
                    "safety_failure", page_index, "blocked", 
                    violations=[v.message for v in safety_result.violations]
                )
            
            # Cross-modal reconciliation (native text, VLM outputs, spatial)
            try:
                if self.cross_validator:
                    native_data = {
                        "py_text": py_text or "",
                        "ocr_text": ocr_text or "",
                        "stage1_page_context": stage1_result.page_context or "",
                    }
                    vlm_data = stage2_result.raw_response or {}
                    # Spatial summary - convert geometric_data list into a short summary
                    spatial_summary = {
                        "spatial_count": len(stage2_result.geometric_data) if stage2_result.geometric_data else 0
                    }
                    reconciled, conflicts, resolutions = self.cross_validator.validate_cross_modal_data(
                        native_data, vlm_data, spatial_summary
                    )
                    # Summarize conflicts/resolutions for downstream use
                    conflicts_summary = [
                        {"field": c.field_name, "type": c.conflict_type.value, "similarity": c.similarity_score}
                        for c in conflicts
                    ]
                    resolutions_summary = [
                        {
                            "field": r.field_name,
                            "resolved_value": r.resolved_value,
                            "source": r.source.value if r.source else None,
                            "confidence": r.confidence,
                            "is_resolved": r.is_conflict_resolved,
                        }
                        for r in resolutions
                    ]
                else:
                    reconciled, conflicts_summary, resolutions_summary = ({}, [], [])
            except Exception as e:
                logger.exception("Cross-modal reconciliation failed: %s", e)
                reconciled, conflicts_summary, resolutions_summary = ({}, [], [])
            
            # Consolidate
            return {
                "stage1": asdict(stage1_result),
                "stage2": asdict(stage2_result),
                "safety": {
                    "is_safe": safety_result.is_safe,
                    "max_severity": safety_result.max_severity.value if safety_result.max_severity else None,
                    "violations": [asdict(v) for v in safety_result.violations]
                },
                "combined_summary": stage1_result.page_context,
                "combined_description": json.dumps(stage2_result.raw_response, indent=2, ensure_ascii=False),
                "reconciled": reconciled,
                "conflicts": conflicts_summary,
                "resolutions": resolutions_summary,
                "is_blocked": not safety_result.is_safe
            }
            
        except Exception as e:
            logger.error(f"Two-stage processing failed: {e}", exc_info=True)
            # If resilience framework available, log failure for retry
            try:
                if getattr(self, "resilience", None) and doc_id:
                    failure_id = f"tsv_fail_{int(time.time()*1000)}"
                    self.resilience.handle_extraction_failure(
                        failure_id=failure_id,
                        doc_id=doc_id,
                        page_num=page_index,
                        stage="stage2",
                        error_msg=str(e),
                        error_type="exception",
                    )
            except Exception:
                logger.exception("Failed to log extraction failure to resilience framework")

            return {
                "error": str(e),
                "stage1": None,
                "stage2": None
            }

    def stage1_quick_identification(
        self,
        image_path: str,
        py_text: str = ""
    ) -> QuickIdentificationResult:
        """STAGE 1: Quick 3-second classification"""
        logger.info(f"Starting Stage 1 identification for {image_path}")
        
        system_prompt, user_prompt = self.selector.get_stage1_prompts()
        
        if py_text:
            user_prompt += f"\n\nContext Hint (Native Text):\n{py_text[:1000]}..."

        # Validate prompts before calling LLM
        ok, reason = validate_prompt(system_prompt, user_prompt)
        if not ok:
            logger.warning("Stage1 prompt validation failed: %s", reason)
            user_prompt = sanitize_user_prompt(user_prompt)

        @retry(
            max_attempts=3,
            strategy=RetryStrategy.EXPONENTIAL,
            base_delay=2.0,
            max_delay=10.0,
            on_retry=lambda attempt, err: logger.warning(f"Stage 1 retry {attempt}/3: {err}")
        )
        def _call_vlm():
            resp = self.llm.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": [
                        {"type": "text", "text": user_prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{self._load_img_b64(image_path)}"}}
                    ]}
                ],
                temperature=0.1,
                max_tokens=500,
                task_type="vision"
            )
            if isinstance(resp, dict) and "error" in resp:
                raise RuntimeError(f"VLM call failed: {resp['error']}")
            return resp

        try:
            resp = _call_vlm()
        except Exception as e:
            logger.error(f"Stage 1 final failure: {e}")
            # Fallback values if all retries fail
            return QuickIdentificationResult(
                document_type=DocumentClassification.UNKNOWN,
                sheet_number="N/A",
                revision="N/A",
                project_name="N/A",
                page_context=f"Error: {str(e)}",
                key_systems=[],
                confidence=0,
                extracted_text_snippets=[],
                raw_response={"error": str(e)}
            )
        
        content = (resp.get("choices") or [{}])[0].get("message", {}).get("content", "")
        stage1_data = self._parse_stage1_json(content)
        
        # Map to classification
        doc_type_str = stage1_data.get("document_type", "unknown").lower()
        try:
            doc_type = DocumentClassification(doc_type_str)
        except ValueError:
            doc_type = DocumentClassification.UNKNOWN
            
        return QuickIdentificationResult(
            document_type=doc_type,
            sheet_number=stage1_data.get("sheet_number", "N/A"),
            revision=stage1_data.get("revision", "N/A"),
            project_name=stage1_data.get("project_name", "N/A"),
            page_context=stage1_data.get("what_is_shown", ""),
            key_systems=stage1_data.get("key_systems", []),
            confidence=stage1_data.get("confidence", 0),
            extracted_text_snippets=stage1_data.get("readable_text_snippets", []),
            raw_response=stage1_data
        )

    def stage2_specialized_extraction(
        self,
        image_path: str,
        stage1_result: QuickIdentificationResult
    ) -> DetailedExtractionResult:
        """STAGE 2: Specialized detailed extraction"""
        logger.info(f"Starting Stage 2 specialized extraction: {stage1_result.document_type}")
        
        system_prompt, base_user_prompt = self.selector.get_specialized_prompt(stage1_result.document_type)
        
        # Enhance user prompt with Stage 1 findings
        enhancement = f"""
STAGE 1 IDENTIFICATION RESULTS:
- Document Type: {stage1_result.document_type.value}
- Sheet Number: {stage1_result.sheet_number}
- Revision: {stage1_result.revision}
- Project: {stage1_result.project_name}
- Content: {stage1_result.page_context}
- Key Systems: {', '.join(stage1_result.key_systems)}

Use these findings to focus your detailed extraction."""
        
        user_prompt = f"{base_user_prompt}\n{enhancement}"

        # Validate prompts before calling LLM
        ok, reason = validate_prompt(system_prompt, user_prompt)
        if not ok:
            logger.warning("Stage2 prompt validation failed: %s", reason)
            user_prompt = sanitize_user_prompt(user_prompt)

        @retry(
            max_attempts=3,
            strategy=RetryStrategy.EXPONENTIAL,
            base_delay=2.0,
            max_delay=15.0,
            on_retry=lambda attempt, err: logger.warning(f"Stage 2 retry {attempt}/3: {err}")
        )
        def _call_vlm_stage2():
            resp = self.llm.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": [
                        {"type": "text", "text": user_prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{self._load_img_b64(image_path)}"}}
                    ]}
                ],
                temperature=0.1,
                max_tokens=2000,
                task_type="vision"
            )
            if isinstance(resp, dict) and "error" in resp:
                raise RuntimeError(f"VLM Stage 2 failed: {resp['error']}")
            return resp

        try:
            resp = _call_vlm_stage2()
        except Exception as e:
            logger.error(f"Stage 2 final failure: {e}")
            # Simplified fallback for stage 2
            return DetailedExtractionResult(
                document_identity={
                    "type": stage1_result.document_type.value,
                    "sheet_number": stage1_result.sheet_number,
                    "revision": stage1_result.revision,
                    "project": stage1_result.project_name
                },
                geometric_data=[],
                technical_systems=[],
                cross_references=[],
                specifications=[],
                notes_and_legends=[f"Error in extraction: {str(e)}"],
                quality_assessment={
                    "stage1_confidence": stage1_result.confidence,
                    "completeness": "failed"
                },
                raw_response={"error": str(e)}
            )
        
        content = (resp.get("choices") or [{}])[0].get("message", {}).get("content", "")
        stage2_data = self._parse_stage2_json(content)
        
        return DetailedExtractionResult(
            document_identity={
                "type": stage1_result.document_type.value,
                "sheet_number": stage1_result.sheet_number,
                "revision": stage1_result.revision,
                "project": stage1_result.project_name
            },
            geometric_data=stage2_data.get("geometric_data", []) or stage2_data.get("rooms", []),
            technical_systems=stage2_data.get("technical_systems", []) or stage2_data.get("systems", []),
            cross_references=stage2_data.get("cross_references", []) or stage2_data.get("details_referenced", []),
            specifications=stage2_data.get("specifications", []) or stage2_data.get("materials", []),
            notes_and_legends=stage2_data.get("notes", []),
            quality_assessment={
                "stage1_confidence": stage1_result.confidence,
                "completeness": stage2_data.get("extraction_completeness", "unknown")
            },
            raw_response=stage2_data
        )

    def _parse_stage2_json(self, content: str) -> Dict[str, Any]:
        """Robustly parse JSON from Stage 2 response using centralized parser"""
        from src.utils.parser_utils import robust_json_parse
        
        obj = robust_json_parse(content)
        
        if not obj:
            return {"raw_text": content}
        
        return obj

    def _load_img_b64(self, path: str) -> str:
        import base64
        import os
        if not os.path.exists(path):
            return ""
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("ascii")
