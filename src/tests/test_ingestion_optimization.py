import os
import unittest
import tempfile
import shutil
import time
from unittest.mock import MagicMock, patch
from src.infra.persistence.database_manager import DatabaseManager
from src.application.jobs.ingest_file_job import IngestFileJob

class TestIngestionOptimization(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_dir = os.path.join(self.test_dir, ".serapeum")
        os.makedirs(self.db_dir)
        
        # Initialize DB with migrations
        self.db = DatabaseManager(root_dir=self.db_dir, project_id="test_proj")
        
        self.project_id = "test_proj"
        self.file_path = os.path.join(self.test_dir, "test_file.pdf")
        with open(self.file_path, "w") as f:
            f.write("Initial content")
            
        self.context = {
            "db": self.db,
            "manager": MagicMock()
        }

    def tearDown(self):
        # Close DB connection before deleting files (essential on Windows)
        self.db.close_connection()
        shutil.rmtree(self.test_dir)

    def test_ingestion_skips_hash_on_metadata_match(self):
        # 1. First Ingestion
        job1 = IngestFileJob("job1", self.project_id, self.file_path)
        with patch.object(IngestFileJob, '_compute_hash', wraps=job1._compute_hash) as mock_hash:
            result1 = job1.run(self.context)
            self.assertEqual(result1["status"], "ingested")
            self.assertEqual(mock_hash.call_count, 1)

        # 2. Second Ingestion (No changes)
        job2 = IngestFileJob("job2", self.project_id, self.file_path)
        with patch.object(IngestFileJob, '_compute_hash', wraps=job2._compute_hash) as mock_hash:
            result2 = job2.run(self.context)
            self.assertEqual(result2["status"], "unchanged")
            # CRITICAL: Hash calculation should be SKIPPED
            self.assertEqual(mock_hash.call_count, 0)
            print("Verified: Hash calculation skipped for unchanged metadata.")

    def test_ingestion_rehashes_on_content_change(self):
        # 1. First Ingestion
        job1 = IngestFileJob("job1", self.project_id, self.file_path)
        job1.run(self.context)

        # 2. Modify file content and ensure mtime updates
        time.sleep(0.1) # Ensure time diff
        with open(self.file_path, "a") as f:
            f.write(" - more content")
        
        # 3. Second Ingestion (Metadata changed)
        job2 = IngestFileJob("job2", self.project_id, self.file_path)
        with patch.object(IngestFileJob, '_compute_hash', wraps=job2._compute_hash) as mock_hash:
            result2 = job2.run(self.context)
            self.assertEqual(result2["status"], "ingested")
            self.assertEqual(mock_hash.call_count, 1)
            print("Verified: Hash calculation triggered for changed metadata.")

if __name__ == "__main__":
    unittest.main()
