from pathlib import Path


def test_file_inspector_uses_semantic_tab_names():
    source = Path("src/ui/panels/file_detail_panel.py").read_text(encoding="utf-8")
    assert 'Consolidated Review' in source
    assert 'Full Metadata' in source
    assert 'Raw Deterministic Extraction' in source
    assert 'AI Output Only' in source


def test_file_inspector_reuses_presentation_helper():
    source = Path("src/ui/panels/file_detail_panel.py").read_text(encoding="utf-8")
    assert 'build_file_inspector_payload' in source
