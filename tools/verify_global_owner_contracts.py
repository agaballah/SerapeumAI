from __future__ import annotations

import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from src.compliance.standard_enricher import StandardEnricher
from src.compliance.standards_db import StandardsDatabase
from src.compliance.standards_service import StandardsService
from src.infra.persistence.global_db_initializer import global_db_path

ROOT = Path(__file__).resolve().parents[1]
DOCS_PAGE = (ROOT / 'src' / 'ui' / 'pages' / 'documents_page.py').read_text(encoding='utf-8')
RUN_TEXT = (ROOT / 'run.py').read_text(encoding='utf-8')
MAIN_WINDOW_TEXT = (ROOT / 'src' / 'ui' / 'main_window.py').read_text(encoding='utf-8')


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    with TemporaryDirectory() as td:
        app_root = Path(td) / 'app'
        app_root.mkdir(parents=True, exist_ok=True)
        os.environ['SERAPEUM_APP_ROOT'] = str(app_root)
        expected = str((app_root / '.serapeum' / 'global.sqlite3').resolve())

        resolved = global_db_path()
        check(Path(resolved).resolve() == Path(expected), 'Canonical global_db_path() did not resolve to <app_root>/.serapeum/global.sqlite3')
        print(f'PASS Packet B path: {resolved}')

        svc = StandardsService()
        enricher = StandardEnricher()
        legacy_db = StandardsDatabase()
        check(Path(svc.db_path).resolve() == Path(expected), 'StandardsService does not use canonical global owner')
        check(Path(enricher.svc.db_path).resolve() == Path(expected), 'StandardEnricher does not use canonical global owner')
        check(Path(legacy_db.db_path).resolve() == Path(expected), 'Legacy StandardsDatabase does not normalize to canonical global owner')
        print(f'PASS Packet C services: {svc.db_path}')

    check('SERAPEUM_APP_ROOT' in RUN_TEXT, 'run.py does not pin SERAPEUM_APP_ROOT')
    check('MainApp(app_root=app_root_str)' in RUN_TEXT, 'run.py does not pass app_root into MainApp')
    check('global_db_path(self.app_root)' in MAIN_WINDOW_TEXT, 'MainApp does not bind global DB from app_root')
    print('PASS boot/runtime binding contract')

    check('values=["Project Scope", "Global Standards"]' in DOCS_PAGE, 'Mounted scope selector missing Global Standards route')
    check('canonical global standards library' in DOCS_PAGE, 'Mounted Global Standards wording is not aligned to canonical owner')
    check('not project truth by itself' in DOCS_PAGE, 'Mounted Global Standards wording does not narrow truth scope honestly')
    check('target_db = self.controller.global_db if is_global_scope else self.controller.db' in DOCS_PAGE, 'Mounted Global Standards route is not bound to global_db')
    print('PASS Packet D mounted route alignment')

    print('All Phase 3 global-owner contract checks passed.')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except AssertionError as e:
        print(f'FAIL: {e}', file=sys.stderr)
        raise SystemExit(1)
