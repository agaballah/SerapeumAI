# -*- coding: utf-8 -*-
from typing import List, Dict, Any
import re

class TextChunker:
    """
    Standardizes text chunking/blocking across all document processors.
    """
    
    @staticmethod
    def chunk_text(text: str, source_type: str = "txt", min_chunk_size: int = 100, max_chunk_size: int = 2000) -> List[Dict[str, Any]]:
        """
        Split text into logical blocks (paragraphs).
        """
        if not text:
            return []
            
        # Basic paragraph splitting by double newline
        # Normalize line endings
        normalized = text.replace("\r\n", "\n")
        paragraphs = re.split(r'\n\s*\n', normalized)
        
        blocks = []
        for i, p in enumerate(paragraphs):
            content = p.strip()
            if not content:
                continue
                
            # Naive word count or char count
            # Here we just store it as a block
            blocks.append({
                "block_index": i,
                "content": content,
                "char_count": len(content),
                "source_type": source_type
            })
            
        return blocks
