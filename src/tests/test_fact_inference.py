import os
import sys
import unittest
from unittest.mock import MagicMock

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.application.api.fact_api import FactQueryAPI

class TestFactApiPatch(unittest.TestCase):
    def setUp(self):
        self.db = MagicMock()
        self.api = FactQueryAPI(self.db)
        
    def test_infer_document_intent(self):
        # Multi-word phrases
        q1 = "summarize this document"
        inferred1 = self.api._infer_fact_types(q1)
        self.assertIn("document.profile", inferred1)
        
        q2 = "how many pages"
        inferred2 = self.api._infer_fact_types(q2)
        self.assertIn("document.page_count", inferred2)
        
        # New keywords
        q3 = "metadata of this file"
        inferred3 = self.api._infer_fact_types(q3)
        self.assertIn("document.profile", inferred3)
        
        q4 = "analyze this document"
        inferred4 = self.api._infer_fact_types(q4)
        self.assertIn("document.profile", inferred4)
        
    def test_fallback_includes_document(self):
        q = "random question about nothing"
        inferred = self.api._infer_fact_types(q)
        self.assertIn("document.profile", inferred)

if __name__ == "__main__":
    unittest.main()
