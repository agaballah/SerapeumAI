# -*- coding: utf-8 -*-
"""
Modern Settings Dialog - Clean, resizable, user-friendly
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

try:
    import ttkbootstrap as ttk  # type: ignore
    _HAS_TTKB = True
except ImportError:
    from tkinter import ttk  # type: ignore
    _HAS_TTKB = False


def _kw(**kwargs):
    if not _HAS_TTKB:
        kwargs.pop("bootstyle", None)
    return kwargs


from src.infra.config.configuration_manager import get_config


class SettingsDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Settings")
        self.geometry("800x600")
        self.minsize(700, 500)

        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        self.parent = parent
        self.config = get_config()

        self._load_values()
        self._build_ui()
        self._center_window()

    def _load_values(self):
        self.threshold_val = tk.IntVar(value=int(self.config.get("pdf_processing.min_text_threshold", 500)))
        self.ocr_lang_val = tk.StringVar(value=str(self.config.get("pdf_processing.ocr_languages", "eng+ara")))
        self.vector_val = tk.IntVar(value=int(self.config.get("pdf_processing.vector_threshold", 1000)))
        self.force_ocr_val = tk.BooleanVar(value=bool(self.config.get("pdf_processing.force_ocr", False)))

        self.parallel_workers_val = tk.IntVar(value=int(self.config.get("vision.parallel_workers", 1)))

        self.max_tokens_val = tk.IntVar(value=int(self.config.get("analysis.max_tokens", 4096)))
        self.temp_val = tk.DoubleVar(value=float(self.config.get("analysis.temperature", 0.0)))

        self.lm_studio_enabled = tk.BooleanVar(value=bool(self.config.get("lm_studio.enabled", False)))
        self.lm_studio_url = tk.StringVar(value=str(self.config.get("lm_studio.url", "http://127.0.0.1:1234")))

    def _build_ui(self):
        main = ttk.Frame(self, padding=0)  # type: ignore[attr-defined]
        main.pack(fill=tk.BOTH, expand=True)

        self.notebook = ttk.Notebook(main)  # type: ignore[attr-defined]
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self._build_general_tab()
        self._build_lm_studio_tab()
        self._build_advanced_tab()

        btn_frame = ttk.Frame(main, padding=(10, 0, 10, 10))  # type: ignore[attr-defined]
        btn_frame.pack(fill=tk.X)

        ttk.Button(btn_frame, text="Save", command=self._save, **_kw(bootstyle="success")).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy, **_kw(bootstyle="secondary")).pack(side=tk.RIGHT)

    def _build_general_tab(self):
        tab = ttk.Frame(self.notebook, padding=20)  # type: ignore[attr-defined]
        self.notebook.add(tab, text="General")

        pdf_frame = ttk.Labelframe(tab, text="📄 PDF Processing", padding=15)  # type: ignore[attr-defined]
        pdf_frame.pack(fill=tk.X, pady=(0, 15))

        row1 = ttk.Frame(pdf_frame)  # type: ignore[attr-defined]
        row1.pack(fill=tk.X, pady=5)
        ttk.Label(row1, text="Min Text Threshold:", width=20).pack(side=tk.LEFT)
        ttk.Spinbox(row1, from_=0, to=5000, textvariable=self.threshold_val, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Label(row1, text="chars (lower = more OCR)", foreground="gray").pack(side=tk.LEFT)

        row2 = ttk.Frame(pdf_frame)  # type: ignore[attr-defined]
        row2.pack(fill=tk.X, pady=5)
        ttk.Label(row2, text="OCR Languages:", width=20).pack(side=tk.LEFT)
        ttk.Entry(row2, textvariable=self.ocr_lang_val, width=20).pack(side=tk.LEFT, padx=5)
        ttk.Label(row2, text="e.g., eng+ara", foreground="gray").pack(side=tk.LEFT)

        row3 = ttk.Frame(pdf_frame)  # type: ignore[attr-defined]
        row3.pack(fill=tk.X, pady=5)
        ttk.Checkbutton(row3, text="Force OCR on all pages", variable=self.force_ocr_val).pack(side=tk.LEFT)

        vision_frame = ttk.Labelframe(tab, text="👁️ Vision Processing", padding=15)  # type: ignore[attr-defined]
        vision_frame.pack(fill=tk.X, pady=(0, 15))

        row4 = ttk.Frame(vision_frame)  # type: ignore[attr-defined]
        row4.pack(fill=tk.X, pady=5)
        ttk.Label(row4, text="Parallel Workers:", width=20).pack(side=tk.LEFT)
        ttk.Spinbox(row4, from_=1, to=8, textvariable=self.parallel_workers_val, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Label(row4, text="(1 = sequential, 4 = fast)", foreground="gray").pack(side=tk.LEFT)

        analysis_frame = ttk.Labelframe(tab, text="🔍 Analysis", padding=15)  # type: ignore[attr-defined]
        analysis_frame.pack(fill=tk.X)

        row5 = ttk.Frame(analysis_frame)  # type: ignore[attr-defined]
        row5.pack(fill=tk.X, pady=5)
        ttk.Label(row5, text="Max Tokens:", width=20).pack(side=tk.LEFT)
        ttk.Spinbox(row5, from_=512, to=8192, textvariable=self.max_tokens_val, width=10).pack(side=tk.LEFT, padx=5)

        row6 = ttk.Frame(analysis_frame)  # type: ignore[attr-defined]
        row6.pack(fill=tk.X, pady=5)
        ttk.Label(row6, text="Temperature:", width=20).pack(side=tk.LEFT)
        ttk.Scale(row6, from_=0.0, to=1.0, variable=self.temp_val, orient=tk.HORIZONTAL, length=200).pack(side=tk.LEFT, padx=5)
        ttk.Label(row6, textvariable=self.temp_val, width=5).pack(side=tk.LEFT)

    def _build_lm_studio_tab(self):
        tab = ttk.Frame(self.notebook, padding=20)  # type: ignore[attr-defined]
        self.notebook.add(tab, text="LM Studio")

        enable_frame = ttk.Frame(tab)  # type: ignore[attr-defined]
        enable_frame.pack(fill=tk.X, pady=(0, 20))

        ttk.Checkbutton(
            enable_frame,
            text="Enable LM Studio Integration",
            variable=self.lm_studio_enabled,
            command=self._toggle_lm_studio,
            **_kw(bootstyle="success-round-toggle"),
        ).pack(side=tk.LEFT)

        conn_frame = ttk.Labelframe(tab, text="Connection", padding=15)  # type: ignore[attr-defined]
        conn_frame.pack(fill=tk.X, pady=(0, 20))

        row1 = ttk.Frame(conn_frame)  # type: ignore[attr-defined]
        row1.pack(fill=tk.X, pady=5)
        ttk.Label(row1, text="Server URL:", width=15).pack(side=tk.LEFT)
        ttk.Entry(row1, textvariable=self.lm_studio_url, width=40).pack(side=tk.LEFT, padx=5)
        ttk.Button(row1, text="Test", command=self._test_lm_studio, **_kw(bootstyle="info-outline")).pack(side=tk.LEFT, padx=5)

        status_frame = ttk.Frame(tab)  # type: ignore[attr-defined]
        status_frame.pack(fill=tk.X, pady=(10, 0))

        self.lm_status_label = ttk.Label(status_frame, text="Status: Not connected", foreground="gray")
        self.lm_status_label.pack(side=tk.LEFT)

    def _build_advanced_tab(self):
        tab = ttk.Frame(self.notebook, padding=20)  # type: ignore[attr-defined]
        self.notebook.add(tab, text="Advanced")

        vec_frame = ttk.Labelframe(tab, text="Vector Processing", padding=15)  # type: ignore[attr-defined]
        vec_frame.pack(fill=tk.X, pady=(0, 15))

        row1 = ttk.Frame(vec_frame)  # type: ignore[attr-defined]
        row1.pack(fill=tk.X, pady=5)
        ttk.Label(row1, text="Vector Op Threshold:", width=20).pack(side=tk.LEFT)
        ttk.Spinbox(row1, from_=0, to=10000, textvariable=self.vector_val, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Label(row1, text="operations", foreground="gray").pack(side=tk.LEFT)

    def _toggle_lm_studio(self):
        if self.lm_studio_enabled.get():
            self.lm_status_label.config(text="Status: Enabled (restart may be required)", foreground="orange")
        else:
            self.lm_status_label.config(text="Status: Disabled", foreground="gray")

    def _test_lm_studio(self):
        try:
            import requests

            url = self.lm_studio_url.get()
            response = requests.get(f"{url}/api/v1/models", timeout=3)
            response.raise_for_status()

            models = response.json()
            count = len(models) if isinstance(models, list) else 0

            messagebox.showinfo("Connection Successful", f"✅ Connected to LM Studio!\n\nFound {count} model(s) available.")
            self.lm_status_label.config(text=f"Status: Connected ({count} models)", foreground="green")
        except Exception as e:
            messagebox.showerror(
                "Connection Failed",
                f"❌ Could not connect to LM Studio.\n\nError: {e}\n\nMake sure:\n1. LM Studio is running\n2. Server is enabled\n3. URL is correct",
            )
            self.lm_status_label.config(text="Status: Connection failed", foreground="red")

    def _save(self):
        """
        Save settings to the local writable override:
            <APP_ROOT>/.serapeum/config.yaml
        """
        try:
            # Write into LOCAL layer only (user/machine)
            self.config.set("pdf_processing.min_text_threshold", int(self.threshold_val.get()), scope="local")
            self.config.set("pdf_processing.ocr_languages", str(self.ocr_lang_val.get()), scope="local")
            self.config.set("pdf_processing.vector_threshold", int(self.vector_val.get()), scope="local")
            self.config.set("pdf_processing.force_ocr", bool(self.force_ocr_val.get()), scope="local")

            self.config.set("vision.parallel_workers", int(self.parallel_workers_val.get()), scope="local")

            self.config.set("analysis.max_tokens", int(self.max_tokens_val.get()), scope="local")
            self.config.set("analysis.temperature", round(float(self.temp_val.get()), 2), scope="local")

            self.config.set("lm_studio.enabled", bool(self.lm_studio_enabled.get()), scope="local")
            self.config.set("lm_studio.url", str(self.lm_studio_url.get()), scope="local")

            saved_path = self.config.save(scope="local")

            messagebox.showinfo(
                "Success",
                f"Settings saved to:\n{saved_path}\n\nSome changes may require restarting workers or the app.",
            )
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings:\n{e}")

    def _center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
