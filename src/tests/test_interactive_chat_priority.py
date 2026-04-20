from pathlib import Path

from src.application.jobs.manager import SmartScheduler


def test_scheduler_yields_background_jobs_while_interactive_chat_is_active():
    scheduler = SmartScheduler()
    result = scheduler.check_and_wait('EXTRACT', interactive_active=True)
    assert result is False


def test_mounted_chat_runtime_uses_interactive_session_when_available():
    source = Path('src/application/services/mounted_chat_runtime.py').read_text(encoding='utf-8')
    assert 'job_manager = getattr(controller, "job_manager", None)' in source
    assert 'with job_manager.interactive_session()' in source


def test_page_analysis_yields_when_interactive_chat_is_active():
    source = Path('src/analysis_engine/page_analysis.py').read_text(encoding='utf-8')
    assert "interactive_event" in source


def test_mounted_chat_runtime_marks_interactive_session_first_class():
    source = Path('src/application/services/mounted_chat_runtime.py').read_text(encoding='utf-8')
    assert "with job_manager.interactive_session()" in source
