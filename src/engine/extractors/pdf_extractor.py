import logging
import json
import re
import os
import io
import tempfile
from typing import List, Dict, Any, Optional
from pypdf import PdfReader
import fitz # PyMuPDF
import pytesseract
from PIL import Image

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
            update_stage("INITIALIZING", "Sniffing PDF metadata and routing tools")
            reader = PdfReader(file_path)
            doc = fitz.open(file_path) # PyMuPDF
            
            full_text = ""
            page_texts = {}
            
            # Phase 1.1 Structural PDF Metadata Router
            update_stage("ROUTING_EXTRACTION", f"Processing {len(reader.pages)} pages dynamically")
            
            for i in range(len(reader.pages)):
                p_pypdf = reader.pages[i]
                p_fitz = doc[i]
                
                # 1. Sniff composition
                composition = self._sniff_composition(p_pypdf, p_fitz)
                
                # 2. Route to appropriate handler
                text = ""
                method = "native"
                
                if composition == "empty":
                    text = ""
                    method = "skipped_empty"
                elif composition == "vector":
                    text = self._extract_native(p_pypdf)
                    method = "pypdf_vector"
                elif composition == "scanned":
                    text = self._extract_ocr(p_fitz)
                    method = "pytesseract_ocr"
                elif composition == "combined":
                    # For complex pages, we use a mix or VLM if possible
                    # Fallback to OCR + Native
                    t_nat = self._extract_native(p_pypdf)
                    t_ocr = self._extract_ocr(p_fitz)
                    text = f"{t_nat}\n--OCR--\n{t_ocr}"
                    method = "hybrid_mixed"
                
                full_text += text + "\n"
                page_texts[i] = text
                
                # Register Page Record
                records.append({
                    "type": "pdf_page",
                    "data": {
                        "page_no": i + 1,
                        "text_content": text,
                        "metadata": json.dumps({
                            "composition": composition,
                            "method": method,
                            "is_visual": composition in ("scanned", "combined")
                        })
                    },
                    "provenance": {"page": i + 1, "method": method, "composition": composition}
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

    # ------------------------------------------------------------------
    # Phase 1.1 Structural PDF Metadata Router Handlers
    # ------------------------------------------------------------------

    def _sniff_composition(self, pypdf_page, fitz_page) -> str:
        """Categorize page based on text-to-graphics ratio."""
        text = pypdf_page.extract_text() or ""
        text_len = len(text.strip())
        img_count = len(pypdf_page.images)
        
        # 1. EMPTY?
        if text_len == 0 and img_count == 0:
            return "empty"
        
        # 2. VECTOR? (High text-to-image ratio)
        if text_len > 300 and img_count < 2:
            return "vector"
            
        # 3. SCANNED? (Low text, high image)
        if text_len < 100 and img_count > 0:
            return "scanned"
            
        # 4. COMPLEX/COMBINED? (Lots of images + text)
        if text_len > 0 and img_count > 0:
            return "combined"
            
        return "vector" # Default

    def _extract_native(self, pypdf_page) -> str:
        """Handler: Native PDF text extraction."""
        return (pypdf_page.extract_text() or "").strip()

    def _extract_ocr(self, fitz_page) -> str:
        """Handler: Tesseract OCR for scanned pages."""
        # Render fitz page to Pixmap then PIL
        pix = fitz_page.get_pixmap(dpi=150)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        return pytesseract.image_to_string(img).strip()

    def _extract_vlm(self, fitz_page, context: Dict[str, Any]) -> str:
        """Handler: VLM OCR for highly complex pages (mixed layouts)."""
        from src.infra.adapters.llm_service import LLMService
        
        pix = fitz_page.get_pixmap(dpi=150)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            pix.save(tmp.name)
            tmp_path = tmp.name
        
        try:
            llm = (context or {}).get("llm_service")
            if not llm:
                llm = LLMService()
            
            prompt = (
                "Extract all text from this building document page accurately. "
                "Include IDs, tables, and numeric notes. Output RAW TEXT ONLY."
            )
            return llm.analyze_image(image_path=tmp_path, prompt=prompt)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

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
