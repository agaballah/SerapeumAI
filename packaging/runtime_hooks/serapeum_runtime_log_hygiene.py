# -*- coding: utf-8 -*-
"""
Runtime log hygiene for the packaged SerapeumAI app.

This hook runs before run.py in the PyInstaller bundle. It keeps noisy optional
library loggers from flooding the packaged app log during startup while leaving
SerapeumAI's own loggers untouched.
"""

import logging
import os


# Keep matplotlib from emitting thousands of DEBUG font-discovery records into
# the packaged app log when the application/root logger is in DEBUG mode.
for logger_name in (
    "matplotlib",
    "matplotlib.font_manager",
    "PIL",
):
    logging.getLogger(logger_name).setLevel(logging.WARNING)


# Prefer a package-local matplotlib config/cache location so startup does not
# repeatedly scan/rebuild more than necessary across packaged runs.
try:
    app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cache_root = os.path.join(app_root, ".serapeum", "cache", "matplotlib")
    os.makedirs(cache_root, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", cache_root)
except Exception:
    # Never block application startup from a log-hygiene hook.
    pass
