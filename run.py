# -*- coding: utf-8 -*-
# Copyright (c) 2025 Ahmed Gaballa
# Licensed under the Apache License, Version 2.0 (the "License");

"""
run.py — Entry point for Serapeum AECO Desktop App

Responsibilities:
    • Detect APP_ROOT from this file’s location
    • Initialize canonical global app logging (file + console) with a session id
    • Initialize config manager rooted at APP_ROOT (creates <APP_ROOT>/.serapeum/config.yaml if missing)
    • Ensure global standards DB under <APP_ROOT>/.serapeum/standards.sqlite3
    • Launch Tk main window (MainApp)
"""

from __future__ import annotations

import sys
from pathlib import Path
import logging

# Force UTF-8 for Windows consoles to prevent emoji crashes
try:
    enc = (sys.stdout.encoding or "").lower()
    if "utf-8" not in enc:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


def get_app_root() -> Path:
    """Return installation root where 'src' folder lives."""
    return Path(__file__).resolve().parent


def check_system_dependencies():
    """Verify that Tesseract and Poppler are in the system path."""
    import shutil
    import tkinter.messagebox as messagebox
    from tkinter import Tk

    missing = []
    if not shutil.which("tesseract"):
        missing.append("- Tesseract OCR (Required for reading PDFs)")
    if not shutil.which("pdfinfo"):
        missing.append("- Poppler (Required for rendering PDFs)")

    if missing:
        # Create hidden root for messagebox if needed
        root = Tk()
        root.withdraw()
        
        msg = "Some required system tools were not found:\n\n" + "\n".join(missing)
        msg += "\n\nSerapeumAI will still open, but PDF processing will fail.\n"
        msg += "Please run Setup.bat again or follow the guide in INSTALL.md."
        
        messagebox.showwarning("System Dependencies Missing", msg)
        root.destroy()


def main() -> int:
    app_root = get_app_root()

    # Set Global UI Theme immediately
    from src.ui.styles.theme import Theme
    Theme.apply_to_all()

    # Early check for system tools (Tesseract, Poppler)
    try:
        check_system_dependencies()
    except Exception:
        pass

    # Ensure APP_ROOT is on sys.path so `import src....` works reliably
    app_root_str = str(app_root)
    if app_root_str not in sys.path:
        sys.path.insert(0, app_root_str)

    # Canonical logging (the ONLY place global handlers are configured)
    from src.infra.telemetry.logging_setup import setup_logging
    setup_logging(app_root=app_root_str)

    # Pin config manager to APP_ROOT early (no cwd ambiguity)
    from src.infra.config.configuration_manager import get_config
    get_config(app_root_str)

    # Now safe to import app modules
    from src.infra.persistence.global_db_initializer import ensure_global_db, global_db_path
    from src.ui.main_window import MainApp

    # Global standards & preferences DB
    try:
        gdb_path = global_db_path(app_root)
        ensure_global_db(gdb_path, app_root)
        logging.getLogger("run").info(f"Global DB ready at {gdb_path}")
    except Exception as e:
        logging.getLogger("run").error(
            f"Failed to initialize Global DB: {e}", exc_info=True
        )

    # Launch UI
    try:
        app = MainApp()
        app.mainloop()
        return 0
    except Exception as e:
        logging.getLogger("run").error(f"UI launch failed: {e}", exc_info=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
