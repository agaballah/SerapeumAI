# -*- coding: utf-8 -*-
"""
vlm_tools.py — Vision Language Model Tools
Protocol v1.1 compliant: cache-first policy, structured return.
"""
import os
from typing import Any, Dict
from src.tools.base_tool import BaseTool
from src.domain.models.page_record import PageRecord

class AnalyzePageImageTool(BaseTool):
    """
    Tool for on-demand visual analysis of document pages.
    Prioritizes cached vision results to save tokens/time.
    Returns structured dict with provenance.
    """
    
    def __init__(self, db, llm):
        self.db = db
        self.llm = llm

    @property
    def name(self) -> str:
        return "analyze_page_image"

    @property
    def description(self) -> str:
        return (
            "Perform visual analysis or OCR on a specific document page. "
            "Use this for blueprints, photos, or when text extraction is insufficient. "
            "Expects 'doc_id', 'page_index', and an optional 'prompt'."
        )

    def execute(self, doc_id: str, page_index: int, prompt: str = "Perform a detailed structural analysis of this drawing.", bypass_cache: bool = False, **kwargs) -> Dict[str, Any]:
        """Analyze a page image with cache-first policy (unless bypass_cache is True).
        
        Returns:
            Dict with keys: doc_id, page_index, method ("cached"|"generated"|"forced_fresh"), 
                           general_summary, detailed_description, text
        """
        try:
            # 1. Cache Check
            page = self.db.get_page(doc_id, page_index)
            if not page:
                return {
                    "doc_id": doc_id,
                    "page_index": page_index,
                    "method": "error",
                    "text": f"Page {page_index} not found for document {doc_id}."
                }
            
            # Prioritize Smart Recognition (vision_detailed/general) over raw OCR
            # If vision exists, return it immediately UNLESS bypass_cache is True
            if not bypass_cache:
                if page.get("vision_general") or page.get("vision_detailed"):
                    return {
                        "doc_id": doc_id,
                        "page_index": page_index,
                        "method": "cached",
                        "general_summary": page.get("vision_general", ""),
                        "detailed_description": page.get("vision_detailed", ""),
                        "text": page.get("vision_detailed", page.get("vision_general", ""))
                    }
                
                # Fallback to legacy vision_ocr_text if available
                if page.get("vision_ocr_done") and page.get("vision_ocr_text"):
                    return {
                        "doc_id": doc_id,
                        "page_index": page_index,
                        "method": "cached",
                        "text": page["vision_ocr_text"]
                    }
            
            # 2. Path Resolution
            img_path = page.get("img_path") or page.get("image_path")
            if not img_path:
                return {
                    "doc_id": doc_id,
                    "page_index": page_index,
                    "method": "error",
                    "text": "No image available for this page."
                }
            
            # Ensure absolute path
            if not os.path.isabs(img_path):
                img_path = os.path.join(self.db.root_dir, img_path)
            
            if not os.path.exists(img_path):
                return {
                    "doc_id": doc_id,
                    "page_index": page_index,
                    "method": "error",
                    "text": f"Page image file missing at: {img_path}"
                }
            
            # 3. Inference
            # Trigger Two-Stage Captioning logic if available, else fallback to standard analysis
            try:
                from src.vision.vision_caption_v2 import two_stage_caption
                result = two_stage_caption(
                    self.llm, 
                    image_path=img_path, 
                    py_text=page.get("py_text", ""),
                    ocr_text=page.get("ocr_text", "")
                )
                
                # Update DB with new "Eye of the User" results
                page_rec = PageRecord(
                    doc_id=doc_id,
                    page_index=page_index,
                    vision_general=result.get("general_summary", ""),
                    vision_detailed=result.get("detailed_description", ""),
                    vision_ocr_text=result.get("vision_text", ""),
                    vision_ocr_done=True,
                    vision_model="qwen2-vl-7b-eye"
                )
                self.db.upsert_page(page_rec)
                
                return {
                    "doc_id": doc_id,
                    "page_index": page_index,
                    "method": "generated",
                    "general_summary": result.get("general_summary"),
                    "detailed_description": result.get("detailed_description"),
                    "text": result.get("detailed_description")
                }
            except Exception:
                # Basic Fallback
                fallback_res = self.llm.analyze_image(image_path=img_path, prompt=prompt)
                return {
                    "doc_id": doc_id,
                    "page_index": page_index,
                    "method": "generated",
                    "text": fallback_res
                }
            
        except Exception as e:
            return {
                "doc_id": doc_id,
                "page_index": page_index,
                "method": "error",
                "text": f"ERROR in vision analysis: {str(e)}"
            }

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "doc_id": {"type": "string"},
                "page_index": {"type": "integer"},
                "prompt": {"type": "string", "default": "Perform a detailed structural analysis of this drawing."},
                "bypass_cache": {"type": "boolean", "default": False}
            },
            "required": ["doc_id", "page_index"]
        }
