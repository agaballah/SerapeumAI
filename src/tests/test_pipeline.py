import unittest
from unittest.mock import MagicMock, patch
import tempfile
import shutil

from src.application.orchestrators.pipeline import Pipeline
from src.infra.persistence.database_manager import DatabaseManager

class TestPipeline(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db = MagicMock(spec=DatabaseManager)
        self.llm = MagicMock()
        self.project_root = self.test_dir
        
        # We need to patch DocumentService since Pipeline instantiates it in __init__
        with patch('src.core.pipeline.DocumentService') as MockDocService:
            self.pipeline = Pipeline(
                db=self.db,
                llm=self.llm,
                project_root=self.project_root
            )
            self.mock_docs = self.pipeline.docs

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_run_ingestion(self):
        # Setup mock return
        self.mock_docs.ingest_project.return_value = {"processed": 1, "errors": 0}
        
        # Call
        res = self.pipeline.run_ingestion(project_id="p1")
        
        # Verify
        self.mock_docs.ingest_project.assert_called_once()
        self.assertEqual(res["processed"], 1)

    @patch('src.analysis_engine.analysis_engine.AnalysisEngine')
    def test_run_analysis(self, MockAnalysisEngine):
        # Setup mock instance
        mock_ae_instance = MockAnalysisEngine.return_value
        
        # Call
        self.pipeline.run_analysis(project_id="p1", fast_mode=True)
        
        # Verify AnalysisEngine was instantiated
        MockAnalysisEngine.assert_called_once_with(db=self.db, llm=self.llm)
        
        # Verify analyze_project was called
        mock_ae_instance.analyze_project.assert_called_once()
        call_args = mock_ae_instance.analyze_project.call_args[1]
        self.assertEqual(call_args["project_id"], "p1")
        self.assertEqual(call_args["fast_mode"], True)

if __name__ == '__main__':
    unittest.main()
