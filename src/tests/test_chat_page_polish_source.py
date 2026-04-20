from pathlib import Path


def test_chat_page_contains_attach_copy_and_feedback_scaffold():
    source = Path("src/ui/pages/chat_page.py").read_text(encoding="utf-8")
    assert 'text="Attach"' in source
    assert 'text="Copy"' in source
    assert 'capture_feedback' in source
    assert 'candidate_fact_suggestions' in source
    assert 'answer_presentation' in source


def test_chat_page_renders_answer_first_with_hidden_evidence_surface():
    source = Path("src/ui/pages/chat_page.py").read_text(encoding="utf-8")
    assert 'source_basis_banner' in source
    assert 'main_answer_text' in source
    assert 'Show Evidence' in source
    assert 'Hide Evidence' in source
    assert 'Copy Evidence' in source
    assert 'Trusted Facts' in source
    assert 'Extracted Evidence' in source
    assert 'Linked Support' in source
    assert 'AI-Generated Synthesis' in source
