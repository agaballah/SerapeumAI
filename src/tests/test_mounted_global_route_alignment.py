import unittest
from pathlib import Path

DOCS_PAGE = Path('/mnt/data/phase3repo/src/ui/pages/documents_page.py').read_text()


class MountedGlobalRouteAlignmentTests(unittest.TestCase):
    def test_scope_selector_offers_global_standards(self):
        self.assertIn('values=["Project Scope", "Global Standards"]', DOCS_PAGE)
        self.assertIn('command=self._on_scope_change', DOCS_PAGE)

    def test_global_scope_wording_is_narrow_and_honest(self):
        self.assertIn('Global Standards Library', DOCS_PAGE)
        self.assertIn('canonical global library', DOCS_PAGE)
        self.assertIn('not project truth by itself', DOCS_PAGE)

    def test_global_scope_queries_global_db(self):
        self.assertIn('target_db = self.controller.global_db if is_global_scope else self.controller.db', DOCS_PAGE)
        self.assertIn('SELECT source_path, file_id FROM file_versions ORDER BY imported_at DESC LIMIT 200', DOCS_PAGE)
        self.assertIn('FileDetailPanel(self, target_db, file_id=f, file_path=p)', DOCS_PAGE)


if __name__ == '__main__':
    unittest.main()
