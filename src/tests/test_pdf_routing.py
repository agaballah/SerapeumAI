import os
import sys
import unittest
from unittest.mock import MagicMock

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.engine.extractors.pdf_extractor import UniversalPdfExtractor

class TestUniversalPdfExtractor(unittest.TestCase):
    def setUp(self):
        self.extractor = UniversalPdfExtractor()
        
    def test_sniff_composition_vector(self):
        p_pypdf = MagicMock()
        p_pypdf.extract_text.return_value = "This is a lot of vector text " * 20
        p_pypdf.images = []
        
        p_fitz = MagicMock()
        
        comp = self.extractor._sniff_composition(p_pypdf, p_fitz)
        self.assertEqual(comp, "vector")

    def test_sniff_composition_scanned(self):
        p_pypdf = MagicMock()
        p_pypdf.extract_text.return_value = "   "
        p_pypdf.images = [MagicMock()]
        
        p_fitz = MagicMock()
        
        comp = self.extractor._sniff_composition(p_pypdf, p_fitz)
        self.assertEqual(comp, "scanned")

    def test_extract_native(self):
        p_pypdf = MagicMock()
        p_pypdf.extract_text.return_value = "Hello World"
        text = self.extractor._extract_native(p_pypdf)
        self.assertEqual(text, "Hello World")

if __name__ == "__main__":
    unittest.main()
