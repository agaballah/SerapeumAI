from __future__ import annotations

from typing import Any, Sequence


def resolve_pick_index(event: Any, artists: Sequence[Any]) -> int | None:
    """Resolve the selected bar index from a matplotlib PickEvent safely.

    Supports both shapes:
    - event.ind = [index]
    - event.artist matching one of the provided bar artists
    """
    ind = getattr(event, 'ind', None)
    if isinstance(ind, (list, tuple)) and ind:
        try:
            return int(ind[0])
        except Exception:
            pass
    artist = getattr(event, 'artist', None)
    if artist is not None:
        try:
            return list(artists).index(artist)
        except ValueError:
            return None
    return None


def build_schedule_audit_text(*, name: str, code: str, fact_data: dict | None, row_summary: dict | None = None) -> str:
    row_summary = row_summary or {}
    facts = (fact_data or {}).get('facts', []) or []
    lines = [
        f"Activity: {name}",
        f"Identifier: {code}",
    ]
    if row_summary:
        if row_summary.get('status'):
            lines.append(f"Status: {row_summary['status']}")
        if row_summary.get('start'):
            lines.append(f"Start: {row_summary['start']}")
        if row_summary.get('finish'):
            lines.append(f"Finish: {row_summary['finish']}")
        if row_summary.get('total_float') not in (None, ''):
            lines.append(f"Total float: {row_summary['total_float']}")
    lines.append('=' * 40)
    lines.append('')
    if not facts:
        lines.append('[NO CERTIFIED SCHEDULE FACTS LINKED]')
        lines.append('The schedule item was selected successfully, but no certified schedule facts are linked to it yet.')
        return '\n'.join(lines)
    for f in facts:
        lines.append(f"TYPE: {f.get('fact_type')}")
        lines.append(f"  VALUE: {f.get('value')}")
        lines.append(f"  STATUS: {f.get('status')}")
        method = f.get('method_id')
        if method:
            lines.append(f"  METHOD: {method}")
        lineage = f.get('lineage', []) or []
        if lineage:
            first = lineage[0] or {}
            src = first.get('source_path') or 'unknown'
            loc = first.get('location') or {}
            if isinstance(loc, dict):
                if 'page_index' in loc:
                    src = f"{src} p.{int(loc.get('page_index', 0)) + 1}"
                elif 'page' in loc:
                    src = f"{src} p.{loc.get('page')}"
            lines.append(f"  SOURCE: {src}")
        lines.append('')
    return '\n'.join(lines)
