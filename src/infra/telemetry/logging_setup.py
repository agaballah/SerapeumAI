# -*- coding: utf-8 -*-
# Copyright (c) 2025 Ahmed Gaballa
# Licensed under the Apache License, Version 2.0 (the "License");

"""
logging_setup.py — canonical logging for Serapeum

Goals:
- ONE global app log: <APP_ROOT>/.serapeum/logs/serapeum.log (rotating, append)
- ONE active project log at a time: <PROJECT_ROOT>/.serapeum/logs/project.log (rotating, append)
- Session ID injected into every record (sid=xxxx)
- Idempotent: safe to call setup_logging() multiple times (no duplicate handlers)
- Switching projects: cleanly removes old project handler + closes file handle
- Re-attaching same project: no handler churn (keeps current handler)
"""

from __future__ import annotations

import logging
import os
import sys
import threading
import uuid
from pathlib import Path
from typing import Optional, Union
from logging.handlers import RotatingFileHandler

_LOCK = threading.Lock()

_SESSION_ID: Optional[str] = None
_APP_ROOT: Optional[Path] = None

_APP_HANDLER_FILE: Optional[logging.Handler] = None
_APP_HANDLER_CONSOLE: Optional[logging.Handler] = None
_PROJECT_HANDLER_FILE: Optional[logging.Handler] = None

_ROLE_ATTR = "_serapeum_role"
ROLE_APP_FILE = "serapeum.app.file"
ROLE_APP_CONSOLE = "serapeum.app.console"
ROLE_PROJECT_FILE = "serapeum.project.file"


class _SessionIdFilter(logging.Filter):
    def __init__(self, sid: str):
        super().__init__()
        self.sid = sid

    def filter(self, record: logging.LogRecord) -> bool:
        record.sid = self.sid  # type: ignore[attr-defined]
        return True


def _infer_app_root() -> Path:
    """
    Attempt to infer the repo/app root (folder containing 'src') from this file location.
    logging_setup.py is expected at: <ROOT>/src/infra/telemetry/logging_setup.py
    """
    here = Path(__file__).resolve()
    for p in here.parents:
        if (p / "src").is_dir():
            return p
    return Path(os.getcwd()).resolve()


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _close_handler(h: Optional[logging.Handler]) -> None:
    if not h:
        return
    try:
        h.flush()
    except Exception:
        pass
    try:
        h.close()
    except Exception:
        pass


def _mk_formatter() -> logging.Formatter:
    return logging.Formatter(
        fmt="%(asctime)s | %(levelname)-7s | sid=%(sid)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _handler_target_path(h: logging.Handler) -> Optional[str]:
    base = getattr(h, "baseFilename", None)
    if not base:
        return None
    try:
        return os.path.abspath(str(base))
    except Exception:
        return str(base)


def setup_logging(
    app_root: Optional[Union[str, Path]] = None,
    *,
    verbose: bool = True,
    session_id: Optional[str] = None,
) -> str:
    """
    Configure APP-level logging to:
      <APP_ROOT>/.serapeum/logs/serapeum.log

    Idempotent:
    - Removes/replaces only Serapeum APP handlers (console + app file).
    - Leaves current project handler intact (if any).
    Returns the app log file path as string.
    """
    global _SESSION_ID, _APP_ROOT, _APP_HANDLER_FILE, _APP_HANDLER_CONSOLE

    with _LOCK:
        if _SESSION_ID is None:
            _SESSION_ID = (session_id or uuid.uuid4().hex[:8])

        sid = _SESSION_ID
        root = Path(app_root).resolve() if app_root is not None else _infer_app_root()
        _APP_ROOT = root

        logs_dir = root / ".serapeum" / "logs"
        _ensure_dir(logs_dir)
        app_log_path = logs_dir / "serapeum.log"

        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)

        # Remove prior Serapeum APP handlers only (do NOT remove project handler here)
        for h in list(root_logger.handlers):
            role = getattr(h, _ROLE_ATTR, None)
            if role in (ROLE_APP_FILE, ROLE_APP_CONSOLE):
                root_logger.removeHandler(h)
                _close_handler(h)

        _APP_HANDLER_FILE = None
        _APP_HANDLER_CONSOLE = None

        sid_filter = _SessionIdFilter(sid)
        fmt = _mk_formatter()

        # Console handler
        ch = logging.StreamHandler(stream=sys.stdout)
        setattr(ch, _ROLE_ATTR, ROLE_APP_CONSOLE)
        ch.setLevel(logging.INFO if verbose else logging.WARNING)
        ch.addFilter(sid_filter)
        ch.setFormatter(fmt)

        # App file handler (rotating, append)
        fh = RotatingFileHandler(
            filename=str(app_log_path),
            mode="a",
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=10,
            encoding="utf-8",
            delay=True,
        )
        setattr(fh, _ROLE_ATTR, ROLE_APP_FILE)
        fh.setLevel(logging.DEBUG)
        fh.addFilter(sid_filter)
        fh.setFormatter(fmt)

        root_logger.addHandler(ch)
        root_logger.addHandler(fh)

        _APP_HANDLER_CONSOLE = ch
        _APP_HANDLER_FILE = fh

        # Defensive: if someone configured "serapeum" logger with its own handlers, clear them.
        ser = logging.getLogger("serapeum")
        for h in list(ser.handlers):
            ser.removeHandler(h)
            _close_handler(h)
        ser.propagate = True

        # Session banner (only once per process)
        if not getattr(root_logger, "_serapeum_session_banner", False):
            setattr(root_logger, "_serapeum_session_banner", True)
            root_logger.info("!!! SERAPEUM SESSION START: %s !!!", sid)

        root_logger.info("logging ready at %s", str(app_log_path))
        return str(app_log_path)


def attach_project_logging(
    project_root: Union[str, Path],
    *,
    project_id: Optional[str] = None,
    verbose: bool = True,
) -> str:
    """
    Attach/switch project log handler to:
      <PROJECT_ROOT>/.serapeum/logs/project.log

    Behavior:
    - If already active for same project.log: do nothing (no churn)
    - If switching projects: removes old project handler(s) + closes file handle
    - Appends to existing project.log
    - Rotates automatically
    Returns the project log file path as string.
    """
    global _SESSION_ID, _PROJECT_HANDLER_FILE

    with _LOCK:
        if _SESSION_ID is None:
            setup_logging(verbose=verbose)

        sid = _SESSION_ID or "unknown"

        proj_root = Path(project_root).resolve()
        logs_dir = proj_root / ".serapeum" / "logs"
        _ensure_dir(logs_dir)
        project_log_path = logs_dir / "project.log"
        project_log_abs = os.path.abspath(str(project_log_path))

        root_logger = logging.getLogger()

        # If a project handler already exists and points to the same file, keep it
        for h in list(root_logger.handlers):
            if getattr(h, _ROLE_ATTR, None) == ROLE_PROJECT_FILE:
                existing = _handler_target_path(h)
                if existing and os.path.abspath(existing) == project_log_abs:
                    _PROJECT_HANDLER_FILE = h
                    root_logger.info(
                        "project logging already active: %s (project_id=%s)",
                        str(project_log_path),
                        project_id or "N/A",
                    )
                    return str(project_log_path)

        # Otherwise, remove old project handler(s)
        for h in list(root_logger.handlers):
            if getattr(h, _ROLE_ATTR, None) == ROLE_PROJECT_FILE:
                root_logger.removeHandler(h)
                _close_handler(h)

        _PROJECT_HANDLER_FILE = None

        sid_filter = _SessionIdFilter(sid)
        fmt = _mk_formatter()

        ph = RotatingFileHandler(
            filename=str(project_log_path),
            mode="a",
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=10,
            encoding="utf-8",
            delay=True,
        )
        setattr(ph, _ROLE_ATTR, ROLE_PROJECT_FILE)
        ph.setLevel(logging.DEBUG)
        ph.addFilter(sid_filter)
        ph.setFormatter(fmt)

        root_logger.addHandler(ph)
        _PROJECT_HANDLER_FILE = ph

        root_logger.info(
            "project logging active: %s (project_id=%s)",
            str(project_log_path),
            project_id or "N/A",
        )
        return str(project_log_path)
