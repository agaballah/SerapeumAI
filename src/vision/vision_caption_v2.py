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
vision_caption_v2.py — Two-Stage VLM Captioning
------------------------------------------------
Implements the user's specified two-stage prompting:
  1. General Summary: Quick 2-3 sentence description
  2. Detailed Description: Uses py_text + ocr_text + general summary
"""

import os
import base64
import logging
from typing import Dict, Any, Optional

from src.infra.adapters.llm_service import LLMService
from src.infra.config.configuration_manager import get_config

_config = get_config()
logger = logging.getLogger("vision.worker")


def two_stage_caption(
    llm: LLMService,
    *,
    image_path: str,
    py_text: str = "",
    ocr_text: str = "",
) -> Dict[str, Any]:
    """
    Two-Stage VLM captioning using Adaptive Extraction Engine.
    
    Args:
        llm: LLMService instance
        image_path: Path to page image
        py_text: Python-extracted text (pypdf)
        ocr_text: Tesseract OCR text
        
    Returns:
        {
            "general_summary": str,
            "detailed_description": str,
            "vision_text": str,
            "vision_model": str,
            ...
        }
    """
    from src.vision.adaptive_extraction import TwoStageVisionEngine
    
    # Initialize engine
    engine = TwoStageVisionEngine(llm)
    
    # Run two-stage processing
    logger.info(f"Starting Two-Stage Adaptive Extraction for {os.path.basename(image_path)}")
    result = engine.process_page_two_stage(
        image_path=image_path,
        py_text=py_text,
        ocr_text=ocr_text
    )
    
    # Initialize default quality assessment
    quality_assessment = {
        "quality_score": 0.0,
        "flags": ["error"],
        "needs_retry": True,
        "human_review": True
    }
    
    if "error" in result:
        return {
            "general_summary": "Error performing analysis.",
            "detailed_description": f"[Error: {result['error']}]",
            "vision_text": "",
            "vision_model": "error",
            "quality_score": 0.0,
            "quality_flags": ["error"],
            "needs_retry": True,
            "human_review": True
        }

    # Extract data from engine result
    general_summary = result.get("combined_summary", "")
    detailed_description = result.get("combined_description", "")
    vision_text = result.get("stage2", {}).get("raw_response", {}).get("full_text", "")
    
    # Quality assessment
    try:
        from src.vision.quality_scoring import assess_vision_quality
        quality_assessment = assess_vision_quality(
            description=detailed_description,
            full_text=vision_text,
            image_path=image_path
        )
    except Exception as e:
        logger.error(f"Quality assessment failed: {e}")

    return {
        "general_summary": general_summary,
        "detailed_description": detailed_description,
        "vision_text": vision_text,
        "vision_model": "qwen2-vl-7b-adaptive",
        "quality_score": quality_assessment.get("quality_score", 0.0),
        "quality_flags": quality_assessment.get("flags", []),
        "needs_retry": quality_assessment.get("needs_retry", True),
        "human_review": quality_assessment.get("human_review", True)
    }

