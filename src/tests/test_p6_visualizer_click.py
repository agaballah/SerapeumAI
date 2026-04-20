from types import SimpleNamespace

from src.application.services.p6_interaction import resolve_pick_index, build_schedule_audit_text


def test_resolve_pick_index_supports_artist_fallback_without_ind():
    bars = ['bar0', 'bar1', 'bar2']
    event = SimpleNamespace(artist='bar1')
    assert resolve_pick_index(event, bars) == 1


def test_schedule_audit_text_is_honest_when_no_certified_facts_exist():
    content = build_schedule_audit_text(
        name='Activity A',
        code='A100',
        fact_data={'facts': []},
        row_summary={'status': 'Not Started', 'start': '2026-01-01', 'finish': '2026-01-10', 'total_float': None},
    )
    assert '[NO CERTIFIED SCHEDULE FACTS LINKED]' in content
    assert 'selected successfully' in content
