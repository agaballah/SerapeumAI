from pathlib import Path


def test_mounted_snapshot_wording_is_informational_only():
    source = Path("src/ui/main_window.py").read_text(encoding="utf-8-sig")

    assert "Informational only - does not change chat, facts, or answer authority yet." in source
    assert "snapshot_id=None" in Path("src/application/services/mounted_chat_runtime.py").read_text(encoding="utf-8-sig")


def test_facts_page_does_not_claim_selected_project_state_governs():
    source = Path("src/ui/pages/facts_page.py").read_text(encoding="utf-8-sig")

    forbidden_phrases = [
        "selected project state",
        "selected snapshot",
        "as-of answer state",
    ]
    lowered = source.lower()
    for phrase in forbidden_phrases:
        assert phrase not in lowered

    assert "current project fact set" in source
    assert "does not change fact or chat authority yet" in source
