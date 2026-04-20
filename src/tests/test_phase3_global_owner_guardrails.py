from __future__ import annotations

from pathlib import Path

from src.compliance.standard_enricher import StandardEnricher
from src.compliance.standards_db import StandardsDatabase
from src.compliance.standards_service import StandardsService
from src.infra.persistence.global_db_initializer import global_db_path


def test_boot_and_runtime_resolve_same_global_owner(tmp_path, monkeypatch):
    monkeypatch.setenv('SERAPEUM_APP_ROOT', str(tmp_path))
    expected = global_db_path()
    run_text = Path('run.py').read_text(encoding='utf-8')
    main_window_text = Path('src/ui/main_window.py').read_text(encoding='utf-8')
    assert Path(expected).parts[-2:] == ('.serapeum', 'global.sqlite3')
    assert 'SERAPEUM_APP_ROOT' in run_text
    assert 'MainApp(app_root=app_root_str)' in run_text
    assert 'global_db_path(self.app_root)' in main_window_text


def test_all_live_standards_services_resolve_to_canonical_owner(tmp_path, monkeypatch):
    monkeypatch.setenv('SERAPEUM_APP_ROOT', str(tmp_path))
    expected = Path(global_db_path()).resolve()
    assert Path(StandardsService().db_path).resolve() == expected
    assert Path(StandardEnricher().svc.db_path).resolve() == expected
    assert Path(StandardsDatabase().db_path).resolve() == expected


def test_mounted_global_route_points_to_global_db_only():
    docs_page = Path('src/ui/pages/documents_page.py').read_text(encoding='utf-8')
    assert 'values=["Project Scope", "Global Standards"]' in docs_page
    assert 'canonical global standards library' in docs_page
    assert 'not project truth by itself' in docs_page
    assert 'target_db = self.controller.global_db if is_global_scope else self.controller.db' in docs_page


def test_no_active_competing_standards_db_path_in_seeding_entrypoint():
    seed_text = Path('src/setup/standards_seed.py').read_text(encoding='utf-8')
    assert 'global.sqlite3' in seed_text
    assert 'standards.sqlite3' not in seed_text
