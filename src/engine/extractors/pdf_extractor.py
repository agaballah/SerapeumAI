import logging
import json
import re
from typing import List, Dict, Any
from pypdf import PdfReader

from src.engine.extractors.base import BaseExtractor, ExtractionResult

logger = logging.getLogger(__name__)

class UniversalPdfExtractor(BaseExtractor):
    """
    Extracts text and metadata from ANY PDF.
    Features:
    1. Full Text Extraction (per page).
    2. Doc Type Classification (Scope, Spec, Drawing, Contract).
    """
    
    @property
    def id(self) -> str:
        return "universal-pdf-extractor-v1"
        
    @property
    def version(self) -> str:
        return "1.0.0"
        
    @property
    def supported_extensions(self) -> List[str]:
        return [".pdf"]

    def extract(self, file_path: str, context: Dict[str, Any] = None) -> ExtractionResult:
        records = []
        diagnostics = []
        
        def update_stage(stage: str, msg: str = ""):
            if context and "on_stage" in context:
                context["on_stage"](stage, msg)

        try:
            update_stage("INITIALIZING", "Reading PDF structure")
            reader = PdfReader(file_path)
            full_text = ""
            page_texts = {}  # Track text per page for block attribution
            
            # 1. Extract Text & Pages
            update_stage("EXTRACTING_TEXT", f"Processing {len(reader.pages)} pages")
            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                full_text += text + "\n"
                page_texts[i] = text
                
                # Create Page Record
                records.append({
                    "type": "pdf_page",
                    "data": {
                        "page_no": i + 1,
                        "text_content": text,
                        "metadata": json.dumps({}) # Page metadata often complex/missing
                    },
                    "provenance": {"page": i + 1}
                })
                
            # 2. Classify Document
            doc_type = self._classify_document(file_path, full_text)
            
            # Create Document Classification Record
            records.append({
                "type": "doc_classification",
                "data": {
                    "doc_type": doc_type,
                    "confidence": 0.8, # Heuristic
                    "keywords_found": self._get_keywords(full_text)
                },
                "provenance": {"source": "heuristic_classification"}
            })
            
            # 3. Extract Semantic Blocks for RAG (NEW)
            update_stage("CHUNKING", "Building semantic blocks")
            doc_id = (context or {}).get("doc_id", "unknown")
            blocks = self._extract_semantic_blocks(full_text, doc_id, page_texts)
            
            if blocks:
                records.append({
                    "type": "doc_blocks",
                    "data": {
                        "doc_id": doc_id,
                        "blocks": blocks
                    },
                    "provenance": {"method": "semantic_chunking"}
                })
                diagnostics.append(f"Extracted {len(blocks)} semantic blocks for RAG")
            
            # 4. Compile Metrics
            metadata = {
                "page_count": len(reader.pages),
                "char_count": len(full_text),
                "block_count": len(blocks),
                "image_count": sum(len(p.images) for p in reader.pages)
            }
            
            return ExtractionResult(records=records, diagnostics=diagnostics, metadata=metadata, success=True)
            
        except Exception as e:
            logger.error(f"PDF Extraction failed: {e}")
            return ExtractionResult(success=False, diagnostics=[str(e)])

    def _classify_document(self, file_path: str, text: str) -> str:
        text_lower = text.lower()[:2000] # Check first 2000 chars
        path_lower = file_path.lower()
        
        if "draw" in path_lower or "drawing" in text_lower:
            return "DRAWING"
        if "spec" in path_lower or "specification" in text_lower:
            return "SPECIFICATION"
        if "scope" in path_lower or "scope of work" in text_lower:
            return "SCOPE"
        if "contract" in path_lower or "agreement" in text_lower:
            return "CONTRACT"
        if "sched" in path_lower or "schedule" in text_lower:
            return "SCHEDULE_PDF"
        if "rfi" in path_lower:
            return "RFI"
            
        return "GENERAL_DOC"

    def _get_keywords(self, text: str) -> List[str]:
        # Simple extraction of capitalized terms or specific codes could go here
        return []
    
    def _extract_semantic_blocks(self, full_text: str, doc_id: str, page_texts: Dict[int, str]) -> List[Dict[str, Any]]:
        """
        Extract semantic blocks from PDF text using TextChunker.
        Creates block records compatible with DatabaseManager.insert_doc_blocks().
        """
        from src.domain.intelligence.text_chunker import TextChunker
        import hashlib
        
        # Use TextChunker to split into paragraphs
        raw_blocks = TextChunker.chunk_text(full_text, source_type="pdf")
        
        # Convert to doc_blocks schema format
        formatted_blocks = []
        for block in raw_blocks:
            content = block.get("content", "").strip()
            if not content or len(content) < 50:  # Skip tiny fragments
                continue
            
            # Determine which page this block came from (heuristic)
            page_index = self._find_page_for_text(content, page_texts)
            
            # Detect if this is a heading (simple heuristic)
            heading_title = None
            heading_number = None
            level = 0
            
            lines = content.split('\n')
            if lines:
                first_line = lines[0].strip()
                # Check if first line looks like a heading (short, possibly numbered)
                if len(first_line) < 100 and (first_line.isupper() or re.match(r'^[\d\.\s]+', first_line)):
                    heading_title = first_line
                    # Extract heading number if present
                    num_match = re.match(r'^([\d\.]+)\s+(.+)$', first_line)
                    if num_match:
                        heading_number = num_match.group(1)
                        heading_title = num_match.group(2)
                    level = len(re.findall(r'\.', heading_number or '')) + 1
            
            # Create unique block_id
            block_hash = hashlib.md5(content[:200].encode('utf-8')).hexdigest()[:12]
            block_id = f"{doc_id}_blk_{block.get('block_index', 0)}_{block_hash}"
            
            formatted_blocks.append({
                "block_id": block_id,
                "page_index": page_index,
                "heading_title": heading_title,
                "heading_number": heading_number,
                "level": level,
                "text": content
            })
        
        return formatted_blocks
    
    def _find_page_for_text(self, text_fragment: str, page_texts: Dict[int, str]) -> int:
        """Find which page a text fragment most likely came from."""
        # Simple heuristic: check if fragment appears in page text
        search_snippet = text_fragment[:100]  # First 100 chars
        for page_idx, page_text in page_texts.items():
            if search_snippet in page_text:
                return page_idx
        return 0  # Default to first page if not found
