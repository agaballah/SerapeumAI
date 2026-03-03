# -*- coding: utf-8 -*-
# Copyright (c) 2025 Ahmed Gaballa
# Licensed under the Apache License, Version 2.0 (the "License");

"""
utils — helpers + timing + pretty JSON logging (NO handler configuration).

Logging configuration is canonical in:
    src.infra.telemetry.logging_setup

This module must never create handlers or call basicConfig.
It only emits log records to standard Python logging.
"""

from __future__ import annotations

import fnmatch
import json
import logging
import os
import time
from contextlib import contextmanager
from typing import Optional, Sequence, List


def log(msg, level: int = logging.INFO, *, logger_name: str = "serapeum") -> None:
    """
    Emit a log record using the configured logging system.
    Assumes canonical setup_logging() was executed by the entrypoint.
    """
    lgr = logging.getLogger(logger_name)
    if isinstance(msg, (dict, list)):
        lgr.log(level, json.dumps(msg, ensure_ascii=False))
    else:
        lgr.log(level, str(msg))


def log_json(obj, level: int = logging.INFO, *, logger_name: str = "serapeum") -> None:
    log(json.dumps(obj, ensure_ascii=False, indent=2), level, logger_name=logger_name)


@contextmanager
def timer(label: str, *, logger_name: str = "serapeum"):
    t0 = time.time()
    try:
        yield
    finally:
        log(f"{label}: {time.time() - t0:.2f}s", logger_name=logger_name)


def safe_relpath(path: str, start: Optional[str] = None) -> str:
    try:
        return os.path.relpath(path, start) if start else path
    except Exception:
        return path


def walk_files(
    root: str,
    patterns: Optional[Sequence[str]] = None,
    *,
    recursive: bool = True,
    ignore: Optional[Sequence[str]] = None,
) -> List[str]:
    root = os.path.abspath(root)
    if not os.path.isdir(root):
        return []

    pats = list(patterns or ["*"])
    ign = set(ignore or [])
    results: List[str] = []

    def is_ignored(path_abs: str, rel: str) -> bool:
        rel_norm = rel.replace("\\", "/")
        parts = rel_norm.split("/")

        if any(p in (".git", ".hg", ".svn", "__pycache__") for p in parts):
            return True

        # ignore .serapeum/metrics subtree robustly
        if ".serapeum" in parts and "metrics" in parts:
            i = parts.index(".serapeum")
            if "metrics" in parts[i:]:
                return True

        base = os.path.basename(rel)
        if base.startswith("~$") or (base.startswith(".") and base not in (".", "..")):
            return True

        for g in ign:
            if fnmatch.fnmatch(rel_norm, g):
                return True

        return False

    if recursive:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [
                d
                for d in dirnames
                if not is_ignored(
                    os.path.join(dirpath, d),
                    os.path.relpath(os.path.join(dirpath, d), root),
                )
            ]
            for fn in filenames:
                ap = os.path.join(dirpath, fn)
                rel = os.path.relpath(ap, root)
                if is_ignored(ap, rel):
                    continue
                if any(fnmatch.fnmatch(fn, pat) for pat in pats):
                    results.append(os.path.abspath(ap))
    else:
        for fn in os.listdir(root):
            ap = os.path.join(root, fn)
            if not os.path.isfile(ap):
                continue
            rel = os.path.relpath(ap, root)
            if is_ignored(ap, rel):
                continue
            if any(fnmatch.fnmatch(fn, pat) for pat in pats):
                results.append(os.path.abspath(ap))

    results.sort(key=lambda s: s.lower())
    return results
