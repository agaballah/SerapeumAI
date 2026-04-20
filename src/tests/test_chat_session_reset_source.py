from pathlib import Path


def test_chat_page_has_reset_view_and_session_token_guard():
    source = Path('src/ui/pages/chat_page.py').read_text(encoding='utf-8')
    assert 'self._chat_session_token = 0' in source
    assert 'def reset_view(self):' in source
    assert 'self._chat_session_token += 1' in source
    assert 'request_token = self._chat_session_token' in source
    assert 'if request_token != self._chat_session_token:' in source
    assert 'if request_project_id != getattr(self.controller, "active_project_id", None):' in source


def test_chat_reset_clears_attached_files_and_last_query():
    source = Path('src/ui/pages/chat_page.py').read_text(encoding='utf-8')
    reset_block = source.split('def reset_view(self):', 1)[1].split('def attach_files', 1)[0]
    assert 'self._last_user_query = ""' in reset_block
    assert 'self.feedback_events = []' in reset_block
    assert 'self._clear_attachments()' in reset_block
    assert 'child.destroy()' in reset_block


def test_chat_reset_drops_late_answers_from_old_project_or_session():
    source = Path('src/ui/pages/chat_page.py').read_text(encoding='utf-8')
    assert 'request_token = self._chat_session_token' in source
    assert 'request_project_id = getattr(self.controller, "active_project_id", None)' in source
    assert 'if request_token != self._chat_session_token:' in source
    assert 'if request_project_id != getattr(self.controller, "active_project_id", None):' in source
