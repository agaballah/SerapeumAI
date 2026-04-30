# -*- coding: utf-8 -*-
from pathlib import Path


def test_excel_register_extractor_does_not_write_absolute_debug_file():
    source = Path("src/engine/extractors/register_extractor.py").read_text(encoding="utf-8-sig")

    assert "D:\\SerapeumAI\\extractor_debug.txt" not in source
    assert "extractor_debug.txt" not in source
    assert "with open(" not in source
    assert "diagnostics.append" in source
    assert "logger.debug" in source
