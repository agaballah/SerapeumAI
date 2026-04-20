from src.application.services.file_inspector_presentation import _reflow_deterministic_text, _build_raw_deterministic


def test_reflow_deterministic_text_preserves_clause_and_table_structure():
    text = 'B-23 D. Contractor shall provide electrical work\n\nITEM  QTY  UNIT\nCable  10  m\nDuct  5  ea\n'
    out = _reflow_deterministic_text(text)
    assert '[Clause] B-23 D. Contractor shall provide electrical work' in out
    assert '[Table] ITEM | QTY | UNIT' in out
    assert '[Table] Cable | 10 | m' in out


def test_raw_deterministic_xlsx_empty_state_is_explicit_and_honest():
    out = _build_raw_deterministic(document={'file_ext': '.xlsx'}, file_version={'file_ext': '.xlsx'}, pages=[], blocks=[])
    assert 'Structured deterministic spreadsheet extraction is not yet available in this build' in out
    assert 'workbook semantics remain limited' in out
