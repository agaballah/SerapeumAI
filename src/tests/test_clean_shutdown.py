from pathlib import Path


def test_red_x_runs_safe_project_close_sequence_before_destroy():
    source = Path('src/ui/main_window.py').read_text(encoding='utf-8')
    close_block = source.split('def _on_app_close', 1)[1]
    assert 'self._is_closing = True' in close_block
    assert 'self._cancel_all_after_callbacks()' in close_block
    assert '_reset_shell_state(for_shutdown=True)' in close_block
    assert 'self.destroy()' in close_block


def test_pages_have_safe_callback_teardown_hooks():
    base = Path('src/ui/pages/base_page.py').read_text(encoding='utf-8')
    assert 'def safe_ui_after' in base
    assert 'def on_app_close' in base
    assert 'self._page_closing = True' in base

    chat = Path('src/ui/pages/chat_page.py').read_text(encoding='utf-8')
    assert 'self.safe_ui_after(' in chat
    assert 'def on_app_close(self):' in chat

    docs = Path('src/ui/pages/documents_page.py').read_text(encoding='utf-8')
    assert 'self.safe_ui_after(' in docs


def test_shutdown_cancels_incomplete_jobs_and_stops_new_callbacks():
    queue_source = Path('src/application/jobs/job_queue.py').read_text(encoding='utf-8')
    assert 'cancel_incomplete_for_project' in queue_source

    manager_source = Path('src/application/jobs/manager.py').read_text(encoding='utf-8')
    assert 'self._stop_event.set()' in manager_source
    assert 'self.queue.cancel_incomplete_for_project' in manager_source

    analyzer_source = Path('src/analysis_engine/page_analysis.py').read_text(encoding='utf-8')
    assert 'raise CancellationError("Page analysis cancelled because the app session is closing.")' in analyzer_source


def test_shutdown_waits_for_clean_worker_stop_without_timeout_warning():
    manager_source = Path('src/application/jobs/manager.py').read_text(encoding='utf-8')
    assert "Worker stopped cleanly." in manager_source
    assert "Worker thread did not stop before timeout." not in manager_source
    assert "_sleep_with_stop" in manager_source
    assert "self._sleep_with_stop(8.0, stop_event)" in manager_source


def test_safe_after_wrappers_guard_callbacks_after_close():
    main_source = Path('src/ui/main_window.py').read_text(encoding='utf-8')
    assert "def _wrap_safe_callback" in main_source
    base_source = Path('src/ui/pages/base_page.py').read_text(encoding='utf-8')
    assert "def _wrap_safe_callback" in base_source
    dialog_source = Path('src/ui/dialogs/runtime_manager_dialog.py').read_text(encoding='utf-8')
    assert "self._after_ids: set[str] = set()" in dialog_source
    assert "def _wrap_safe_callback" in dialog_source


def test_shutdown_installs_bgerror_guard_and_quits_before_destroy():
    source = Path('src/ui/main_window.py').read_text(encoding='utf-8')
    close_block = source.split('def _on_app_close', 1)[1]
    assert 'self._install_shutdown_bgerror_guard()' in close_block
    assert 'self.withdraw()' in close_block
    assert 'self.quit()' in close_block
    assert 'self.destroy()' in close_block
    assert 'def report_callback_exception' in source
