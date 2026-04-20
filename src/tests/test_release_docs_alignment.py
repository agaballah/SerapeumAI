from pathlib import Path


def test_readme_is_short_honest_and_user_facing():
    text = Path('README.md').read_text(encoding='utf-8')
    assert 'python run.py' in text
    assert 'LM Studio' in text
    assert 'Facts page' in text
    assert 'File Inspector' in text
    assert 'review assistance' in text.lower()
    assert 'Show Evidence' in text
    assert 'Clean shutdown' in text
    assert 'Schedule interaction' in text
    assert 'Interactive priority over backlog' in text
    assert 'Red-X close should internally close the project before destroying the app window.' in text
    assert 'direct answer first' in text
    assert 'guaranteed compliance' not in text.lower()
    assert 'Closing the main window should end the live session cleanly.' in text
    assert 'Schedule page' in text
    assert 'Interactive chat should stay responsive' in text
    assert 'Chat history should reset when the active project closes or changes.' in text


def test_windows_release_proof_doc_exists():
    text = Path('WINDOWS_RELEASE_PROOF.md').read_text(encoding='utf-8')
    assert 'Dashboard honesty' in text
    assert 'project-only retrieval' in text
    assert 'P6 truth' in text
    assert 'answer-first' in text
    assert 'Show Evidence' in text
    assert 'Clean shutdown' in text
    assert 'Schedule interaction' in text
    assert 'Interactive priority over backlog' in text
    assert 'Red-X close should internally close the project before destroying the app window.' in text
