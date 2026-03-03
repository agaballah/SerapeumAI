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
adaptive_analysis.py — Specialized document analysis using fused multi-modal context
----------------------------------------------------------------------------------
Orchestrates:
1. Context Fusion: Merging Native Text, OCR, VLM Extraction, and Layout.
2. Adaptive Prompting: Selecting the right analysis profile based on document type.
3. Cross-Modal Validation: Ensuring text and visual data align.
"""

from __future__ import annotations

import json
import logging
from enum import Enum
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("analysis.adaptive")


class AnalystProfile(Enum):
    TECHNICAL_SPEC = "technical_spec"
    LEGAL_CONTRACT = "legal_contract"
    ENGINEERING_DRAWING = "engineering_drawing"
    FINANCIAL_SCHEDULE = "financial_schedule"
    PROJECT_MANAGEMENT = "project_management"
    BIM_DATA = "bim_data"
    GENERIC = "generic"


class AdaptiveAnalysisEngine:
    """Specialized analysis engine that leverages vision and layout context."""

    def __init__(self, db, llm):
        self.db = db
        self.llm = llm

    # ------------------------------------------------------------------ #
    # Context Fusion
    # ------------------------------------------------------------------ #

    def build_unified_context(self, page_data: Dict[str, Any]) -> str:
        """
        Fuses all available data signals into a high-density engineer-grade context.
        """
        parts = []

        doc_id = page_data.get("doc_id", "Unknown")
        page_idx = int(page_data.get("page_index") or 0)
        parts.append(f"### DOCUMENT: {doc_id} | PAGE: {page_idx + 1}")

        # Native Text (High Precision)
        py_text = str(page_data.get("py_text") or "").strip()
        if py_text:
            parts.append(f"#### NATIVE TEXT CONTENT:\n{py_text[:3000]}")

        # Vision Signals
        vision_general = str(page_data.get("vision_general") or "").strip()
        if vision_general:
            parts.append(f"#### VISION SUMMARY:\n{vision_general[:2000]}")

        vision_detailed = str(page_data.get("vision_detailed") or "").strip()
        if vision_detailed:
            parts.append(f"#### VISION EXTRACTION (FROM IMAGE):\n{vision_detailed[:4000]}")

        # Optional OCR / other extraction channel (if present)
        vision_text = str(page_data.get("vision_text") or "").strip()
        if vision_text and vision_text != vision_detailed:
            parts.append(f"#### VISION TEXT (OCR/EXTRACTION):\n{vision_text[:3000]}")

        # Spatial Layout
        layout_json = page_data.get("layout_json")
        if layout_json:
            try:
                layout = json.loads(layout_json)
                if isinstance(layout, list):
                    parts.append(f"#### SPATIAL LAYOUT HINT: {len(layout)} text blocks identified.")
                elif isinstance(layout, dict):
                    parts.append("#### SPATIAL LAYOUT HINT: layout metadata present.")
            except Exception as e:
                logger.debug(f"layout_json parse failed: {e}")

        return "\n\n".join(parts)

    # ------------------------------------------------------------------ #
    # Profile Selection
    # ------------------------------------------------------------------ #

    def select_analyst_profile(self, page_data: Dict[str, Any]) -> AnalystProfile:
        """
        Determines the analyst profile based on document metadata, vision classification,
        and heuristic fallback based on text content.
        """

        # 0) If upstream already classified doc/page type, prefer it.
        doc_type = str(page_data.get("doc_type") or "").lower().strip()
        if doc_type:
            if any(k in doc_type for k in ["drawing", "plan", "section", "mep", "hvac", "p&id", "pid"]):
                return AnalystProfile.ENGINEERING_DRAWING
            if any(k in doc_type for k in ["schedule", "boq", "bill of quantities", "cost", "pricing"]):
                return AnalystProfile.FINANCIAL_SCHEDULE
            if any(k in doc_type for k in ["contract", "legal", "agreement"]):
                return AnalystProfile.LEGAL_CONTRACT
            if any(k in doc_type for k in ["spec", "specification", "technical"]):
                return AnalystProfile.TECHNICAL_SPEC

        # 1) Vision-based detection (ONLY if vision signals exist)
        v_model = str(page_data.get("vision_model") or "").lower()
        v_sum = str(page_data.get("vision_general") or "").lower()
        v_det = str(page_data.get("vision_detailed") or "").lower()

        has_vision_signal = bool(v_sum.strip() or v_det.strip())
        if has_vision_signal:
            vision_blob = f"{v_sum}\n{v_det}"

            if any(k in vision_blob for k in ["drawing", "plan", "section", "elevation", "detail", "mep", "hvac", "duct", "pipe", "piping", "panel", "sld"]):
                return AnalystProfile.ENGINEERING_DRAWING

            if any(k in vision_blob for k in ["schedule", "table", "tabular", "qty", "quantity", "unit rate", "unit price", "subtotal", "total", "grand total"]):
                return AnalystProfile.FINANCIAL_SCHEDULE

            # If model name explicitly indicates BIM/model outputs
            if any(k in v_model for k in ["bim", "ifc", "revit"]):
                return AnalystProfile.BIM_DATA

        # 2) Heuristic fallback based on native text content
        text = str(page_data.get("py_text") or "").lower()

        if any(k in text for k in ["article", "clause", "agreement", "party", "witnesseth", "hereinafter", "governing law", "indemnify"]):
            return AnalystProfile.LEGAL_CONTRACT

        if any(k in text for k in ["specification", "technical", "submittal", "tolerance", "testing", "material", "finish", "astm", "ansi", "iso", "iec", "saso"]):
            return AnalystProfile.TECHNICAL_SPEC

        if any(k in text for k in ["quantity", "unit price", "unit rate", "subtotal", "total", "bill of quantities", "boq"]):
            return AnalystProfile.FINANCIAL_SCHEDULE

        return AnalystProfile.GENERIC

    # ------------------------------------------------------------------ #
    # Prompting
    # ------------------------------------------------------------------ #

    def get_specialized_prompt(self, profile: AnalystProfile) -> Tuple[str, str]:
        """Returns the system and user template for the specialized analyst."""
        prompts = {
            AnalystProfile.TECHNICAL_SPEC: {
                "system": (
                    "You are a Technical Specification Analyst.\n"
                    "Analyze the text and vision extraction to identify:\n"
                    "1. Performance Requirements: capacity, ratings, tolerances.\n"
                    "2. Material Standards: codes (ASTM, ANSI, SASO), grades, finishes.\n"
                    "3. Quality Control: testing methods, submittal requirements.\n"
                    "4. Validation: Point out if the drawing extraction (Vision) matches the textual specifications."
                ),
                "user": "Analyze this technical specification page and extract high-precision engineering data.",
            },
            AnalystProfile.LEGAL_CONTRACT: {
                "system": (
                    "You are a Legal & Compliance Analyst for AECO contracts.\n"
                    "Analyze the text to identify:\n"
                    "1. Obligations: deliverables, timelines, milestones.\n"
                    "2. Liabilities: penalties, liquidated damages, insurance.\n"
                    "3. Risk Events: termination grounds, force majeure, dispute resolution.\n"
                    "4. Compliance: local regulations, statutory requirements."
                ),
                "user": "Analyze this contract page and identify all binding obligations and risk items.",
            },
            AnalystProfile.ENGINEERING_DRAWING: {
                "system": (
                    "You are a Senior Systems Engineer.\n"
                    "FUSE the textual captions and vision data to identify:\n"
                    "1. Major Equipment Tags: AHUs, Pumps, Panels, etc.\n"
                    "2. Functional Connections: what is connected to what.\n"
                    "3. Design Intent: capacity notes, system boundaries.\n"
                    "4. Coordination Issues: inconsistencies between text hints and visual extraction."
                ),
                "user": "Analyze this engineering drawing context and perform system-level analysis.",
            },
            AnalystProfile.FINANCIAL_SCHEDULE: {
                "system": (
                    "You are a Quantity Surveyor / Cost Analyst.\n"
                    "Analyze the tabular data to extract:\n"
                    "1. Items: Quantities, unit costs, descriptions.\n"
                    "2. Totals: Subtotals, taxes, final sums.\n"
                    "3. Variances: Unit rates compared to market standards if mentioned.\n"
                    "4. Line Items: Mapping tags to costs."
                ),
                "user": "Extract all financial line items and totals from this schedule.",
            },
            AnalystProfile.GENERIC: {
                "system": "You are a comprehensive AECO document analyst. Extract key entities, summaries, and technical insights.",
                "user": "Analyze this document page and provide a technical summary.",
            },
        }

        p = prompts.get(profile, prompts[AnalystProfile.GENERIC])
        return p["system"], p["user"]

    # ------------------------------------------------------------------ #
    # Execution
    # ------------------------------------------------------------------ #

    def analyze_page(self, page_data: Dict[str, Any]) -> Dict[str, Any]:
        """Runs the specialized analysis pipeline for a single page."""

        if not self.llm:
            return {
                "summary": "LLM unavailable",
                "type": "other",
                "entities": [],
                "relationships": [],
                "analyst_profile": AnalystProfile.GENERIC.value,
                "status": "error",
                "error": "llm_missing",
            }

        # 1) Build Context
        context = self.build_unified_context(page_data)

        # 2) Select Profile
        profile = self.select_analyst_profile(page_data)
        logger.info(f"Using Analyst Profile: {profile.value} for page {page_data.get('page_index')}")

        # 3) Get Prompts
        system, user_base = self.get_specialized_prompt(profile)

        # 4) Execute Analysis
        user_prompt = f"{user_base}\n\n### CONTEXT:\n{context}"

        # Prefer schema if available; do not crash if schema import fails.
        schema = None
        try:
            from src.analysis_engine.schemas import PAGE_ANALYSIS_SCHEMA  # type: ignore
            schema = PAGE_ANALYSIS_SCHEMA
        except Exception as e:
            logger.debug(f"PAGE_ANALYSIS_SCHEMA import failed, continuing without schema: {e}")

        try:
            result = self.llm.chat_json(
                system=system,
                user=user_prompt,
                schema=schema,
                task_type="analysis",
            )
        except Exception as e:
            logger.error(f"Adaptive analysis failed: {e}")
            return {
                "summary": "Analysis failed",
                "type": "other",
                "entities": [],
                "relationships": [],
                "analyst_profile": profile.value,
                "status": "error",
                "error": str(e),
            }

        if not result or not isinstance(result, dict):
            return {
                "summary": "Analysis failed",
                "type": "other",
                "entities": [],
                "relationships": [],
                "analyst_profile": profile.value,
                "status": "error",
                "error": "empty_result",
            }

        result["analyst_profile"] = profile.value
        result["status"] = "success"
        return result
