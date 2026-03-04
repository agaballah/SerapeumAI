# -*- coding: utf-8 -*-
"""
PageRecord - Domain model for a document page in the persistence layer.
Replaces the 37-column fragile tuple.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any
import time

@dataclass
class PageRecord:
    doc_id: str
    page_index: int
    width: Optional[int] = None
    height: Optional[int] = None
    
    # Python extraction
    py_text_extracted: bool = False
    py_text_len: int = 0
    py_text: Optional[str] = None
    
    # Vision OCR
    vision_ocr_done: bool = False
    vision_ocr_len: int = 0
    vision_model: Optional[str] = None
    vision_ocr_text: Optional[str] = None
    
    # Vision Analysis
    vision_general: Optional[str] = None
    vision_detailed: Optional[str] = None
    vision_timestamp: Optional[int] = None
    img_path: Optional[str] = None
    
    # Legacy/Merged
    ocr_text: Optional[str] = None
    text_hint: Optional[str] = None
    image_path: Optional[str] = None
    image_hash: Optional[str] = None
    quality: Optional[str] = None
    caption_json: Optional[str] = None
    
    # Quality assessment
    vision_quality_score: float = 0.0
    vision_quality_flags: Optional[str] = None
    vision_needs_retry: bool = False
    vision_human_review: bool = False
    
    # AI Summarization & RAG
    page_summary_short: Optional[str] = None
    page_summary_detailed: Optional[str] = None
    page_entities: Optional[str] = None  # JSON string
    ai_summary_generated: bool = False
    ai_model_used: Optional[str] = None
    
    # Graphics & Layout
    has_raster: bool = False
    has_vector: bool = False
    layout_json: Optional[str] = None
    unified_context: Optional[str] = None
    
    # Internal
    updated: int = field(default_factory=lambda: int(time.time()))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database insertion."""
        return asdict(self)

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> 'PageRecord':
        """Create a PageRecord from a database row dictionary."""
        # Standard filter to only include fields defined in the dataclass
        field_names = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in row.items() if k in field_names}
        return cls(**filtered)
