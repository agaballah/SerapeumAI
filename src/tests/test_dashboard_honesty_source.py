from pathlib import Path


def test_dashboard_uses_honesty_helper_and_p6_truth_row():
    source = Path('src/ui/pages/dashboard_page.py').read_text(encoding='utf-8')
    assert 'assess_p6_truth' in source
    assert 'P6 Schedule Truth' in source
    assert 'governance_status_label' in source
