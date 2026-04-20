from __future__ import annotations

import os
from pathlib import Path

from src.infra.persistence.global_db_initializer import global_db_path


def test_global_db_path_uses_explicit_app_root_independent_of_cwd(tmp_path, monkeypatch):
    app_root = tmp_path / "app"
    app_root.mkdir()
    other_cwd = tmp_path / "elsewhere"
    other_cwd.mkdir()
    monkeypatch.chdir(other_cwd)

    path = global_db_path(app_root)

    assert Path(path) == (app_root / ".serapeum" / "global.sqlite3").resolve()


def test_global_db_path_uses_serapeum_app_root_env(tmp_path, monkeypatch):
    app_root = tmp_path / "app_env"
    app_root.mkdir()
    monkeypatch.setenv("SERAPEUM_APP_ROOT", str(app_root))
    monkeypatch.chdir(tmp_path)

    path = global_db_path()

    assert Path(path) == (app_root / ".serapeum" / "global.sqlite3").resolve()


def test_run_and_main_window_pin_same_app_root_contract():
    run_text = Path("run.py").read_text(encoding="utf-8")
    main_window_text = Path("src/ui/main_window.py").read_text(encoding="utf-8")

    assert 'SERAPEUM_APP_ROOT' in run_text
    assert 'MainApp(app_root=app_root_str)' in run_text
    assert 'self.app_root: Optional[str] = app_root or os.environ.get("SERAPEUM_APP_ROOT") or None' in main_window_text
    assert 'global_db_path(self.app_root)' in main_window_text
