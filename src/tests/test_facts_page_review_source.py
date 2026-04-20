from pathlib import Path


def test_fact_table_contains_review_filters_and_detail_pane():
    source = Path("src/ui/widgets/fact_table.py").read_text(encoding="utf-8")
    assert 'text="Family"' in source
    assert '_add_filter_label(2, "Fact Type")' in source
    assert '_add_filter_label(4, "Review State")' in source
    assert '_add_filter_label(6, "Source")' in source
    assert 'text="Fact Review Detail"' in source
    assert 'text="Open Lineage / Evidence"' in source
    assert 'text="Certify Selected Fact"' in source
    assert 'text="Reject Selected Fact"' in source


def test_facts_page_guides_review_workspace_behavior():
    source = Path("src/ui/pages/facts_page.py").read_text(encoding="utf-8")
    assert "Select a fact to inspect its meaning, provenance, and approval state." in source
