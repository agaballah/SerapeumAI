import unittest
import shutil
import tempfile
import time
from src.infra.persistence.database_manager import DatabaseManager

class TestDatabaseManager(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db = DatabaseManager(root_dir=self.test_dir, project_id="test_proj")

    def tearDown(self):
        self.db.close_connection()
        shutil.rmtree(self.test_dir)

    def test_project_crud(self):
        project_id = "p1"
        self.db.upsert_project(project_id=project_id, name="Test Project", root="/tmp/proj")
        
        proj = self.db.get_project(project_id)
        self.assertIsNotNone(proj)
        self.assertEqual(proj["name"], "Test Project")
        
    def test_document_crud(self):
        doc_id = "d1"
        self.db.upsert_document(
            doc_id=doc_id,
            project_id="p1",
            file_name="test.pdf",
            rel_path="test.pdf",
            abs_path="/tmp/test.pdf",
            file_ext=".pdf",
            created=int(time.time()),
            updated=int(time.time()),
            content_text="Hello world"
        )
        
        doc = self.db.get_document(doc_id)
        self.assertIsNotNone(doc)
        self.assertEqual(doc["file_name"], "test.pdf")
        
        docs = self.db.list_documents(project_id="p1")
        self.assertEqual(len(docs), 1)
        
    def test_fts_search(self):
        self.db.upsert_document(
            doc_id="d1",
            project_id="p1",
            file_name="doc1.pdf",
            rel_path="doc1.pdf",
            abs_path="/tmp/doc1.pdf",
            file_ext=".pdf",
            created=100, updated=100,
            content_text="The quick brown fox jumps over the lazy dog"
        )
        
        # FTS updates might be async or require commit, but SQLite usually immediate within transaction
        # DatabaseManager handles commits.
        
        results = self.db.search_documents("fox")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["doc_id"], "d1")
        
        results = self.db.search_documents("elephant")
        self.assertEqual(len(results), 0)

    def test_doc_blocks(self):
        doc_id = "d2"
        blocks = [
            {
                "block_id": "b1",
                "page_index": 0,
                "text": "Chapter 1: Introduction",
                "heading_title": "Introduction",
                "level": 1
            },
             {
                "block_id": "b2",
                "page_index": 0,
                "text": "This is the content of chapter 1.",
                "level": 0
            }
        ]
        
        self.db.insert_doc_blocks(doc_id, blocks)
        
        results = self.db.search_doc_blocks("Introduction")
        self.assertTrue(len(results) >= 1)
        self.assertEqual(results[0]["text"], "Chapter 1: Introduction")

if __name__ == '__main__':
    unittest.main()
