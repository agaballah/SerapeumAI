# -*- coding: utf-8 -*-
"""
Modern Settings Dialog - Clean, resizable, user-friendly
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk

from src.infra.config.configuration_manager import get_config
from src.infra.services.runtime_advisor import RuntimeAdvisorService
from src.infra.services.runtime_advisor_view import (
    build_runtime_advisor_status_summary,
    format_runtime_advisory_text,
    resolve_runtime_action_feedback_message,
)

logger = logging.getLogger(__name__)


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
        self._build_runtime_advisor_tab()
        self._build_governance_tab()
        self._build_advanced_tab()

        btn_frame = ttk.Frame(main, padding=(10, 0, 10, 10))  # type: ignore[attr-defined]
        btn_frame.pack(fill=tk.X)

        ttk.Button(btn_frame, text="Save", command=self._save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side=tk.RIGHT)

    def _build_general_tab(self):
        tab = ttk.Frame(self.notebook, padding=20)  # type: ignore[attr-defined]
        self.notebook.add(tab, text="General")

        pdf_frame = ttk.Labelframe(tab, text="PDF Processing", padding=15)  # type: ignore[attr-defined]
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

        vision_frame = ttk.Labelframe(tab, text="Vision Processing", padding=15)  # type: ignore[attr-defined]
        vision_frame.pack(fill=tk.X, pady=(0, 15))

        row4 = ttk.Frame(vision_frame)  # type: ignore[attr-defined]
        row4.pack(fill=tk.X, pady=5)
        ttk.Label(row4, text="Parallel Workers:", width=20).pack(side=tk.LEFT)
        ttk.Spinbox(row4, from_=1, to=8, textvariable=self.parallel_workers_val, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Label(row4, text="(1 = sequential, 4 = fast)", foreground="gray").pack(side=tk.LEFT)

        analysis_frame = ttk.Labelframe(tab, text="Analysis", padding=15)  # type: ignore[attr-defined]
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
        ).pack(side=tk.LEFT)

        conn_frame = ttk.Labelframe(tab, text="Connection", padding=15)  # type: ignore[attr-defined]
        conn_frame.pack(fill=tk.X, pady=(0, 20))

        row1 = ttk.Frame(conn_frame)  # type: ignore[attr-defined]
        row1.pack(fill=tk.X, pady=5)
        ttk.Label(row1, text="Server URL:", width=15).pack(side=tk.LEFT)
        ttk.Entry(row1, textvariable=self.lm_studio_url, width=40).pack(side=tk.LEFT, padx=5)
        ttk.Button(row1, text="Test", command=self._test_lm_studio).pack(side=tk.LEFT, padx=5)

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

    def _build_runtime_advisor_tab(self):
        tab = ttk.Frame(self.notebook, padding=20)  # type: ignore[attr-defined]
        self.notebook.add(tab, text="Runtime Advisor")

        hdr = ttk.Frame(tab)  # type: ignore[attr-defined]
        hdr.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(
            hdr,
            text="Advisory data + explicit local actions. No install/download/provisioning actions are performed automatically here.",
            foreground="gray",
        ).pack(side=tk.LEFT)
        ttk.Button(hdr, text="Refresh", command=self._refresh_runtime_advisor).pack(side=tk.RIGHT)

        actions_row = ttk.Frame(tab)  # type: ignore[attr-defined]
        actions_row.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(actions_row, text="Safe action:", foreground="gray").pack(side=tk.LEFT)
        self.runtime_action_var = tk.StringVar(value="")
        self.runtime_action_combo = ttk.Combobox(actions_row, textvariable=self.runtime_action_var, state="readonly")
        self.runtime_action_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 8))
        ttk.Button(actions_row, text="Run Action", command=self._run_runtime_advisor_action).pack(side=tk.RIGHT)
        ttk.Button(actions_row, text="Clear Control Status", command=self._clear_runtime_control_status).pack(
            side=tk.RIGHT, padx=(0, 6)
        )
        ttk.Button(actions_row, text="Clear Probe", command=self._clear_runtime_probe_diagnostics).pack(side=tk.RIGHT, padx=(0, 6))
        self.runtime_status_var = tk.StringVar(value="No recent runtime advisor action.")
        ttk.Label(tab, textvariable=self.runtime_status_var, foreground="gray").pack(fill=tk.X, pady=(0, 8))

        self.runtime_advisor_text = tk.Text(tab, height=26, wrap="word", state=tk.DISABLED)
        self.runtime_advisor_text.pack(fill=tk.BOTH, expand=True)
        self._runtime_available_actions = []
        self._runtime_last_probe_diagnostics = None
        self._runtime_last_probe_captured_at = None
        self._runtime_last_control_status = None
        self._refresh_runtime_advisor()

    def _refresh_runtime_advisor(self):
        try:
            self._runtime_advisor_service = RuntimeAdvisorService(self.config)
            advisory = self._runtime_advisor_service.get_advisory()
            self._runtime_available_actions = advisory.get("available_actions", []) if isinstance(advisory, dict) else []
            combo_values = [f"{a.get('id')} — {a.get('label')}" for a in self._runtime_available_actions]
            self.runtime_action_combo.configure(values=combo_values)
            if combo_values:
                self.runtime_action_var.set(combo_values[0])
            else:
                self.runtime_action_var.set("")
            advisory_for_view = dict(advisory)
            if self._runtime_last_probe_diagnostics:
                advisory_for_view["latest_probe_diagnostics"] = self._runtime_last_probe_diagnostics
                advisory_for_view["latest_probe_captured_at"] = self._runtime_last_probe_captured_at
            if self._runtime_last_control_status:
                advisory_for_view["latest_control_status"] = self._runtime_last_control_status
            self.runtime_status_var.set(
                build_runtime_advisor_status_summary(
                    self._runtime_last_control_status,
                    self._runtime_last_probe_captured_at,
                )
            )
            rendered = format_runtime_advisory_text(advisory_for_view)
        except Exception as e:
            rendered = f"Runtime Advisor unavailable.\nError: {e}"

        self.runtime_advisor_text.configure(state=tk.NORMAL)
        self.runtime_advisor_text.delete("1.0", tk.END)
        self.runtime_advisor_text.insert("1.0", rendered)
        self.runtime_advisor_text.configure(state=tk.DISABLED)

    def _run_runtime_advisor_action(self):
        raw = self.runtime_action_var.get().strip()
        if not raw:
            messagebox.showwarning("Runtime Advisor", "No action selected.")
            return
        action_id = raw.split("—", 1)[0].strip()
        selected = next((a for a in self._runtime_available_actions if a.get("id") == action_id), None)
        if not selected:
            messagebox.showwarning("Runtime Advisor", "Selected action is no longer available. Please refresh.")
            return

        confirmed = True
        if bool(selected.get("requires_confirmation", False)):
            confirmed = messagebox.askyesno(
                "Confirm Runtime Action",
                f"Run action:\n\n{selected.get('label', action_id)}\n\n"
                "This never installs/downloads/provisions. Runtime start/stop actions (if shown) run only through explicit bounded control.",
            )

        result = self._runtime_advisor_service.execute_safe_action(action_id, confirmed=confirmed)
        if "diagnostics" in result:
            self._runtime_last_probe_diagnostics = result.get("diagnostics")
            self._runtime_last_probe_captured_at = datetime.now(timezone.utc).isoformat()
        if "latest_control_status" in result:
            self._runtime_last_control_status = result.get("latest_control_status")
        user_msg = resolve_runtime_action_feedback_message(action_id, result)
        if result.get("executed"):
            messagebox.showinfo("Runtime Advisor", user_msg)
        else:
            messagebox.showwarning("Runtime Advisor", user_msg)

        self._refresh_runtime_advisor()

    def _clear_runtime_probe_diagnostics(self):
        self._runtime_last_probe_diagnostics = None
        self._runtime_last_probe_captured_at = None
        self._refresh_runtime_advisor()

    def _clear_runtime_control_status(self):
        self._runtime_last_control_status = None
        self._refresh_runtime_advisor()

    def _build_governance_tab(self):
        """
        Builds the Governance tab - Role/Discipline vs Fact Domain matrix.
        Persists to authority_policies in the Project DB.
        """
        tab = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(tab, text="Governance")

        lbl_instr = ttk.Label(tab, text="Define which Personas can certify specific Fact Domains:", font=("Arial", 11, "bold"))
        lbl_instr.pack(fill=tk.X, pady=(0, 10))

        ROLES = ["Owner", "Contractor", "PMC", "Consultant"]
        DISCIPLINES = ["Arch", "Str", "Mech", "Elec", "Project Manager"]
        DOMAINS = ["SCHEDULE", "BIM", "DOC_CONTROL", "REGISTERS", "FIELD", "COMPLETION"]

        grid_container = ttk.Frame(tab)
        grid_container.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(grid_container, borderwidth=0, highlightthickness=0)
        scroll_y = ttk.Scrollbar(grid_container, orient="vertical", command=canvas.yview)
        scroll_x = ttk.Scrollbar(grid_container, orient="horizontal", command=canvas.xview)

        matrix_frame = ttk.Frame(canvas)
        matrix_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        canvas.create_window((0, 0), window=matrix_frame, anchor="nw")
        canvas.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        canvas.pack(side="top", fill="both", expand=True)
        scroll_y.pack(side="right", fill="y", before=canvas)
        scroll_x.pack(side="bottom", fill="x")

        ttk.Label(matrix_frame, text="Persona (Role-Disc) \\ Domain", font=("Arial", 9, "bold"), width=30).grid(row=0, column=0, padx=5, pady=5)
        for i, domain in enumerate(DOMAINS):
            ttk.Label(matrix_frame, text=domain, font=("Arial", 9, "bold"), width=15).grid(row=0, column=i + 1, padx=5, pady=5)

        self.governance_vars = {}

        existing_policies = set()
        try:
            if hasattr(self.parent, "db") and self.parent.db:
                rows = self.parent.db.execute("SELECT role, discipline, domain FROM authority_policies WHERE can_certify = 1").fetchall()
                for r in rows:
                    existing_policies.add((r[0], r[1], r[2]))
        except Exception as e:
            logger.warning(f"Failed to load existing governance policies: {e}")

        row_idx = 1
        for role in ROLES:
            for disc in DISCIPLINES:
                persona_label = f"{role} - {disc}"
                ttk.Label(matrix_frame, text=persona_label, width=30).grid(row=row_idx, column=0, padx=5, pady=2, sticky="w")

                for col_idx, domain in enumerate(DOMAINS):
                    var = tk.BooleanVar(value=(role, disc, domain) in existing_policies)
                    self.governance_vars[(role, disc, domain)] = var

                    cb = ttk.Checkbutton(matrix_frame, variable=var)
                    cb.grid(row=row_idx, column=col_idx + 1, padx=5, pady=2)

                row_idx += 1

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

            messagebox.showinfo("Connection Successful", f"Connected to LM Studio.\n\nFound {count} model(s) available.")
            self.lm_status_label.config(text=f"Status: Connected ({count} models)", foreground="green")
        except Exception as e:
            messagebox.showerror(
                "Connection Failed",
                f"Could not connect to LM Studio.\n\nError: {e}\n\nMake sure:\n1. LM Studio is running\n2. Server is enabled\n3. URL is correct",
            )
            self.lm_status_label.config(text="Status: Connection failed", foreground="red")

    def _save(self):
        """
        Save settings to the local writable override:
            <APP_ROOT>/.serapeum/config.yaml
        """
        try:
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

            if hasattr(self.parent, "db") and self.parent.db:
                try:
                    with self.parent.db.transaction():
                        for (role, disc, domain), var in self.governance_vars.items():
                            can_certify = 1 if var.get() else 0
                            self.parent.db.execute(
                                """
                                INSERT OR REPLACE INTO authority_policies
                                (role, discipline, domain, can_certify, updated_at)
                                VALUES (?, ?, ?, ?, strftime('%s','now'))
                                """,
                                (role, disc, domain, can_certify),
                            )
                except Exception as e:
                    logger.error(f"Failed to save governance policies to DB: {e}")

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
