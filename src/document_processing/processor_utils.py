# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib


PROCESSOR_VERSION = "2026-01-28-real-extractors-v1"


def stable_doc_id(abs_path: str, *, prefix: str) -> str:
    """
    Produce a stable document id based on file bytes.

    Why:
    - Python's built-in hash() is salted per-process on Windows/Linux, so using
      it for doc_id makes IDs change every run.
    - Downstream DB rows (documents/pages/analysis) become fragmented and the UI
      appears as if "nothing happened".
    """
    h = hashlib.sha256()
    with open(abs_path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return f"{prefix}_{h.hexdigest()[:16]}"


def get_processor_version() -> str:
    return PROCESSOR_VERSION

