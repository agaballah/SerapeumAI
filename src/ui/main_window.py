import os
import sys
import threading
import logging
import customtkinter as ctk
import tkinter as tk
from typing import Optional
from tkinter import messagebox

# Config
from src.infra.config.configuration_manager import get_config
from src.infra.telemetry.logging_setup import attach_project_logging

# Services
from src.infra.persistence.database_manager import DatabaseManager
from src.infra.persistence.global_db_initializer import global_db_path
from src.application.services.document_service import DocumentService
from src.application.services.project_service import ProjectService
from src.infra.adapters.llm_service import LLMService
from src.application.orchestrators.pipeline import Pipeline
from src.application.jobs.manager import JobManager
from src.application.jobs.ingest_file_job import IngestFileJob
from src.application.jobs.extract_job import ExtractJob
from src.application.jobs.file_linker_job import FileLinkerJob
from src.application.jobs.build_facts_job import BuildFactsJob
from src.application.jobs.analyze_doc_job import AnalyzeDocJob

# Orchestrators & RAG
from src.application.services.rag_service import RAGService
from src.application.orchestrators.agent_orchestrator import AgentOrchestrator
from src.infra.services.runtime_setup_service import LocalRuntimeSetupService, STATUS_READY
from src.ui.dialogs.runtime_manager_dialog import RuntimeManagerDialog

# Pages
from src.ui.pages.dashboard_page import DashboardPage
from src.ui.pages.facts_page import FactsPage
from src.ui.pages.documents_page import DocumentsPage
from src.ui.pages.schedule_page import SchedulePage
from src.ui.pages.chat_page import ChatPage
from src.ui.pages.truth_map_page import TruthMapPage
from src.ui.pages.project_explorer import ProjectExplorerPage

from src.utils.hardening import safe_ui_command

from src.ui.styles.theme import Theme

logger = logging.getLogger(__name__)


class MainApp(ctk.CTk):
    def __init__(self, root_dir: str = None, app_root: str | None = None):
        super().__init__()
        self.title("Serapeum AI | Engineering Truth Engine")
        self.geometry("1400x900")
        self.protocol("WM_DELETE_WINDOW", self._on_app_close)
        self._is_closing = False
        self._after_ids: set[str] = set()

        # Absolute Nuclear Hardening
        # Theme.apply_to_all() already handles global bg configuration in run.py

        # State
        self.config = get_config()
        self.app_root: Optional[str] = app_root or os.environ.get("SERAPEUM_APP_ROOT") or None
        self.global_db: Optional[DatabaseManager] = None
        self.db: Optional[DatabaseManager] = None
        self.project_root: Optional[str] = None
        self.active_project_id: Optional[str] = None
        self.job_manager: Optional[JobManager] = None
        self.llm_service: Optional[LLMService] = None
        self.orchestrator: Optional[AgentOrchestrator] = None
        self.rag_service: Optional[RAGService] = None
        self._last_runtime_alert_key: Optional[str] = None
        self._runtime_setup_prompted: bool = False
        self._runtime_status_code: Optional[str] = None
        self._runtime_status_message: str = "Runtime state unavailable."
        self._runtime_setup_in_progress: bool = False
        self.runtime_setup_service = LocalRuntimeSetupService(self.config)
        self.runtime_dialog = None

        # Initialize Global DB
        try:
            g_path = global_db_path(self.app_root)
            g_root = os.path.dirname(g_path)
            g_name = os.path.basename(g_path)
            m_dir = os.path.join(os.path.dirname(__file__), "..", "infra", "persistence", "global_migrations")
            self.global_db = DatabaseManager(root_dir=g_root, db_name=g_name, migrations_dir=m_dir)
            logger.info(f"MainApp: Global DB initialized at {g_path}")
        except Exception as e:
            logger.error(f"MainApp: Global DB init failed: {e}")

        # Layout
        self.sidebar_width = 320
        self.grid_columnconfigure(0, weight=0, minsize=self.sidebar_width)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_content_area()

        # Load Project if provided
        if root_dir and os.path.exists(root_dir):
            self.after(100, lambda: self._load_project_env(root_dir))
        else:
             self._open_project_dialog()

        self._safe_after(400, lambda: self._refresh_runtime_status(prompt_if_needed=False))
        self._safe_after(1500, self._poll_runtime_alerts)

    def _wrap_safe_callback(self, callback):
        def _runner():
            if self._is_closing:
                return
            try:
                if not self.winfo_exists():
                    return
            except Exception:
                return
            try:
                callback()
            except Exception:
                return
        return _runner

    def _safe_after(self, delay_ms: int, callback):
        if self._is_closing:
            return None
        try:
            after_id = self.after(delay_ms, self._wrap_safe_callback(callback))
            if after_id:
                self._after_ids.add(after_id)
            return after_id
        except tk.TclError:
            return None

    def _safe_after_cancel(self, after_id):
        if not after_id:
            return
        try:
            self.after_cancel(after_id)
        except Exception:
            pass
        self._after_ids.discard(after_id)

    def _cancel_all_after_callbacks(self):
        for after_id in list(self._after_ids):
            self._safe_after_cancel(after_id)


    def _install_shutdown_bgerror_guard(self):
        try:
            self.tk.eval(r"""
                proc bgerror {msg} {
                    if {[string first "application has been destroyed" $msg] >= 0} { return }
                    if {[string first "invalid command name" $msg] >= 0} { return }
                    if {[string first "bgerror failed to handle background error" $msg] >= 0} { return }
                    return
                }
            """)
        except Exception:
            logger.debug("Failed to install shutdown bgerror guard.", exc_info=True)

    def report_callback_exception(self, exc, val, tb):
        msg = f"{exc.__name__}: {val}" if exc else str(val)
        if self._is_closing and any(token in msg for token in (
            "application has been destroyed",
            "invalid command name",
            "bgerror failed to handle background error",
        )):
            logger.debug("Suppressed late Tk callback during controlled shutdown: %s", msg)
            return
        try:
            super().report_callback_exception(exc, val, tb)
        except Exception:
            logger.error("Unhandled Tk callback exception: %s", msg, exc_info=True)

    def _teardown_pages(self):
        for page in getattr(self, "pages", {}).values():
            teardown = getattr(page, "on_app_close", None) or getattr(page, "teardown", None)
            if callable(teardown):
                try:
                    teardown()
                except Exception:
                    logger.debug("Page teardown failed during app close.", exc_info=True)

    def _build_sidebar(self):
        self.frame_sidebar = ctk.CTkFrame(self, width=self.sidebar_width, corner_radius=0, fg_color=Theme.BG_DARKER, border_width=0)
        self.frame_sidebar.grid(row=0, column=0, sticky="ns")
        self.frame_sidebar.grid_propagate(False)
        self.frame_sidebar.grid_columnconfigure(0, weight=1)
        self.frame_sidebar.grid_rowconfigure(10, weight=1)

        # Logo using standard tk.Label to bypass CTK white-box bug
        self.lbl_logo = tk.Label(self.frame_sidebar, text="SERAPEUM", font=Theme.FONT_H1,
                                 fg=Theme.TEXT_MAIN, bg=Theme.BG_DARKER,
                                 padx=0, pady=0, borderwidth=0, highlightthickness=0)
        self.lbl_logo.grid(row=0, column=0, padx=20, pady=(30, 20))

        self.btn_dashboard = self._nav_btn("Dashboard", "dashboard", 1)
        self.btn_facts = self._nav_btn("Facts", "facts", 2)
        self.btn_schedule = self._nav_btn("Schedule", "schedule", 3)
        self.btn_docs = self._nav_btn("Documents", "documents", 4)
        self.btn_chat = self._nav_btn("Expert Chat", "chat", 5)
        self.btn_truth_map = self._nav_btn("Truth Map", "truth_map", 6)

        # Primary Action
        # Packet A — State contract freeze:
        # The mounted shell currently does not propagate a selected snapshot into
        # answer-governing mounted surfaces. Keep the control visible as project
        # timeline context only, and do not imply real "as-of" answer binding yet.
        self.lbl_snapshot = tk.Label(self.frame_sidebar, text="Imported file dates", anchor="w",
                                     fg=Theme.TEXT_MUTED, bg=Theme.BG_DARKER, font=Theme.FONT_BODY,
                                     borderwidth=0, highlightthickness=0)
        self.lbl_snapshot.grid(row=15, column=0, padx=20, pady=(20, 0), sticky="w")

        self.combo_snapshot = ctk.CTkComboBox(self.frame_sidebar, values=["Current project view"], command=self._on_snapshot_change,
                                            state="disabled",
                                            fg_color=Theme.BG_DARKEST,
                                            bg_color=Theme.BG_DARKER,
                                            border_color=Theme.BG_DARK,
                                            button_color=Theme.BG_DARK, button_hover_color=Theme.ACCENT)
        self.combo_snapshot.grid(row=16, column=0, padx=20, pady=(5, 4), sticky="ew")

        self.lbl_snapshot_hint = tk.Label(
            self.frame_sidebar,
            text="Informational only - does not change chat or facts yet.",
            anchor="w",
            justify="left",
            wraplength=self.sidebar_width - 40,
            fg=Theme.TEXT_MUTED,
            bg=Theme.BG_DARKER,
            font=Theme.FONT_BODY,
            borderwidth=0,
            highlightthickness=0,
        )
        self.lbl_snapshot_hint.grid(row=17, column=0, padx=20, pady=(0, 10), sticky="w")

        # Helper frame for buttons
        self.frame_actions = ctk.CTkFrame(self.frame_sidebar, fg_color=Theme.BG_DARKER, bg_color=Theme.BG_DARKER)
        self.frame_actions.grid(row=8, column=0, sticky="ew", padx=0)

        self.btn_open = ctk.CTkButton(self.frame_actions, text="Open Project",
                                    fg_color=Theme.BG_DARK,
                                    hover_color=Theme.ACCENT,
                                    bg_color=Theme.BG_DARKER,
                                    command=self._open_project_dialog)

        self.btn_runtime_setup = ctk.CTkButton(self.frame_actions, text="Re-check Runtime",
                                             fg_color=Theme.BG_DARK,
                                             hover_color=Theme.ACCENT,
                                             bg_color=Theme.BG_DARKER,
                                             command=self._open_runtime_manager)

        self.btn_sync = ctk.CTkButton(self.frame_actions, text="Sync Project",
                                    fg_color=Theme.PRIMARY, hover_color=Theme.ACCENT,
                                    bg_color=Theme.BG_DARKER,
                                    command=self._run_full_scan)

        self.switch_auto = ctk.CTkSwitch(self.frame_actions, text="Auto-Ingest",
                                        fg_color=Theme.BG_DARKER,
                                        bg_color=Theme.BG_DARKER,
                                        progress_color=Theme.PRIMARY)

        self.btn_close = ctk.CTkButton(self.frame_actions, text="Close Project",
                                     fg_color=Theme.DANGER_RED, hover_color=Theme.DANGER_DARK,
                                     bg_color=Theme.BG_DARKER,
                                     command=self._close_project)

        self.btn_open.pack(pady=5, padx=20, fill="x")
        self.btn_runtime_setup.pack(pady=5, padx=20, fill="x")
        self._update_runtime_controls()

        # Bottom Status
        self.lbl_status = tk.Label(self.frame_sidebar, text="No project loaded",
                                   fg=Theme.TEXT_MUTED, bg=Theme.BG_DARKER,
                                   borderwidth=0, highlightthickness=0)
        self.lbl_status.grid(row=10, column=0, padx=20, pady=(10, 4))

        self.lbl_runtime = tk.Label(self.frame_sidebar, text="Runtime: checking...",
                                    fg=Theme.TEXT_MUTED, bg=Theme.BG_DARKER,
                                    justify="left", wraplength=self.sidebar_width - 40,
                                    borderwidth=0, highlightthickness=0)
        self.lbl_runtime.grid(row=11, column=0, padx=20, pady=(0, 10), sticky="w")

    def _nav_btn(self, text, page_name, row):
        # We explicitly set fg_color AND bg_color to match the sidebar frame hex
        btn = ctk.CTkButton(self.frame_sidebar, text=text, command=lambda: self.show_page(page_name),
                           fg_color=Theme.BG_DARKER,
                           bg_color=Theme.BG_DARKER,
                           border_width=1, border_color=Theme.BG_DARK,
                           text_color=Theme.TEXT_MAIN, hover_color=Theme.BG_DARK, font=Theme.FONT_BODY,
                           anchor="w")
        btn.grid(row=row, column=0, padx=15, pady=3, sticky="ew")
        return btn

    def _build_content_area(self):
        self.frame_content = ctk.CTkFrame(self, corner_radius=0, fg_color=Theme.BG_DARKEST)
        self.frame_content.grid(row=0, column=1, sticky="nsew")
        self.frame_content.grid_columnconfigure(0, weight=1)
        self.frame_content.grid_rowconfigure(0, weight=1)

        self.pages = {}
        self.pages["dashboard"] = DashboardPage(self.frame_content, self)
        self.pages["facts"] = FactsPage(self.frame_content, self)
        self.pages["documents"] = DocumentsPage(self.frame_content, self)
        self.pages["schedule"] = SchedulePage(self.frame_content, self)
        self.pages["chat"] = ChatPage(self.frame_content, self)
        self.pages["truth_map"] = TruthMapPage(self.frame_content, self)
        self.pages["explorer"] = ProjectExplorerPage(self.frame_content, self)

        for p in self.pages.values():
            p.grid(row=0, column=0, sticky="nsew")
            p.configure(fg_color=Theme.BG_DARKEST) # Explicit enforcement

        self.show_page("dashboard")

    def _on_snapshot_change(self, value):
        # Packet A contract: mounted selector is intentionally non-authoritative
        # until selected state is fully propagated into mounted answer/facts paths.
        logger.info("[MainApp] Ignoring imported-date selector change (informational only): %s", value)

    def show_page(self, page_name):
        page = self.pages.get(page_name)
        if page:
            page.tkraise()
            page.on_show()

    def _open_project_dialog(self):
         from tkinter import filedialog
         path = filedialog.askdirectory(title="Select Project Folder")
         if path and os.path.exists(path):
             self._load_project_env(path)
             return True

         logger.info("No project folder selected.")
         return False

    def _update_runtime_controls(self):
        project_loaded = bool(self.project_root and self.active_project_id and self.job_manager)
        runtime_ready = self._runtime_status_code == STATUS_READY
        sync_allowed = project_loaded and runtime_ready and not self._runtime_setup_in_progress
        setup_allowed = not self._runtime_setup_in_progress

        try:
            self.btn_runtime_setup.configure(state="normal" if setup_allowed else "disabled")
        except Exception:
            logger.debug("Runtime Setup button state update failed.", exc_info=True)

        try:
            self.btn_sync.configure(state="normal" if sync_allowed else "disabled")
        except Exception:
            logger.debug("Sync button state update failed.", exc_info=True)

        try:
            self.switch_auto.configure(state="normal" if sync_allowed else "disabled")
        except Exception:
            logger.debug("Auto-ingest switch state update failed.", exc_info=True)

    def _apply_runtime_status(self, state):
        status = str((state or {}).get("status") or "").strip() or "UNKNOWN"
        message = str((state or {}).get("message") or "Runtime state unavailable.").strip()
        self._runtime_status_code = status
        self._runtime_status_message = message

        friendly = {
            STATUS_READY: "Runtime: ready",
            "LMSTUDIO_NOT_INSTALLED": "Runtime: LM Studio not installed",
            "CLI_NOT_AVAILABLE": "Runtime: CLI not available",
            "SERVER_NOT_RUNNING": "Runtime: server not running",
            "CHAT_MODEL_MISSING": "Runtime: model selection required",
            "EMBEDDING_RUNTIME_NOT_READY": "Runtime: embedding runtime not ready",
            "MODEL_NOT_LOADED": "Runtime: selected model not loaded",
        }
        display_text = friendly.get(status, f"Runtime: {status}")
        if status == STATUS_READY:
            self.lbl_runtime.configure(text=display_text, fg=Theme.SUCCESS)
        elif status in ("LMSTUDIO_NOT_INSTALLED", "CLI_NOT_AVAILABLE"):
            self.lbl_runtime.configure(text=display_text, fg=Theme.DANGER_RED)
        elif status in ("SERVER_NOT_RUNNING", "CHAT_MODEL_MISSING", "EMBEDDING_RUNTIME_NOT_READY", "MODEL_NOT_LOADED", "PROVISIONING"):
            self.lbl_runtime.configure(text=display_text, fg=Theme.WARNING)
        else:
            self.lbl_runtime.configure(text=display_text, fg=Theme.DANGER_RED)

        self._update_runtime_controls()
        logger.info("[MainApp] Runtime state %s - %s", status, message)

    def _apply_runtime_progress(self, payload):
        status = str((payload or {}).get("status") or "PROVISIONING").strip() or "PROVISIONING"
        message = str((payload or {}).get("message") or "Runtime action in progress.").strip()
        self._runtime_status_code = status
        self._runtime_status_message = message
        self.lbl_runtime.configure(text="Runtime: checking session state", fg=Theme.WARNING)
        try:
            self.lbl_status.configure(text=message, fg=Theme.WARNING)
        except Exception:
            logger.debug("Main status update during runtime progress failed.", exc_info=True)
        self._update_runtime_controls()
        logger.info("[MainApp] Runtime progress %s - %s", status, message)

    def _refresh_runtime_status(self, prompt_if_needed: bool = False):
        def _worker():
            state = self.runtime_setup_service.detect_state()
            def _finish():
                self._apply_runtime_status(state)
                if prompt_if_needed and state.get("status") != STATUS_READY and not self._runtime_setup_prompted:
                    self._runtime_setup_prompted = True
                    self._prompt_runtime_setup(state)
            self._safe_after(0, _finish)

        threading.Thread(target=_worker, daemon=True).start()

    def _prompt_runtime_setup(self, state):
        self._open_runtime_manager()

    def _run_runtime_setup_flow(self, skip_consent: bool = False):
        self._open_runtime_manager()

    def _open_runtime_manager(self):
        try:
            if self.runtime_dialog and self.runtime_dialog.winfo_exists():
                self.runtime_dialog.focus()
                self.runtime_dialog.refresh_inventory(show_popup=False)
                return
        except Exception:
            self.runtime_dialog = None
        self.runtime_dialog = RuntimeManagerDialog(self, self, self.runtime_setup_service)

    def _poll_runtime_alerts(self):
        try:
            if self.db and self.active_project_id:
                row = self.db.execute(
                    """
                    SELECT updated_at, error_text
                    FROM job_queue
                    WHERE type_name='ANALYZE_DOC' AND status='FAILED' AND error_text IS NOT NULL AND trim(error_text) != ''
                    ORDER BY updated_at DESC
                    LIMIT 1
                    """
                ).fetchone()
                if row:
                    ts = row[0]
                    err = str(row[1] or "").strip()
                    if "LM Studio" in err or "Local runtime" in err or "runtime" in err.lower():
                        alert_key = f"{ts}|{err}"
                        if alert_key != self._last_runtime_alert_key:
                            self._last_runtime_alert_key = alert_key
                            short_msg = err.splitlines()[0][:180] if err else "Analysis runtime failed."
                            self.lbl_runtime.configure(text="Runtime: action required", fg=Theme.DANGER_RED)
                            try:
                                messagebox.showerror(
                                    "Local Runtime Error",
                                    short_msg,
                                    parent=self,
                                )
                            except Exception:
                                logger.debug("Runtime error popup could not be displayed.", exc_info=True)
        except Exception:
            logger.debug("Runtime alert polling failed.", exc_info=True)
        finally:
            try:
                self._safe_after(1500, self._poll_runtime_alerts)
            except Exception:
                pass

    @safe_ui_command("Project Sync Error")
    def _run_full_scan(self):
        if not self.project_root:
            return

        if self._runtime_setup_in_progress:
            self.lbl_status.configure(text="Sync blocked - runtime setup in progress", fg=Theme.DANGER_RED)
            messagebox.showwarning(
                "Project Sync Blocked",
                "Sync Project is unavailable while local runtime setup is running.\n\nWait for runtime setup to finish, then try again.",
                parent=self,
            )
            return

        if self._runtime_status_code != STATUS_READY:
            try:
                state = self.runtime_setup_service.detect_state()
                self._apply_runtime_status(state)
            except Exception:
                state = {"status": self._runtime_status_code or "UNKNOWN", "message": self._runtime_status_message or "Local runtime is not ready."}
            status = str(state.get("status") or self._runtime_status_code or "UNKNOWN")
            message = str(state.get("message") or self._runtime_status_message or "Local runtime is not ready.")
            self.lbl_status.configure(text="Sync blocked - runtime setup required", fg=Theme.DANGER_RED)
            messagebox.showwarning(
                "Project Sync Blocked",
                f"Sync Project is unavailable until the local runtime is ready.\n\nCurrent state: {status}\n{message}",
                parent=self,
            )
            return

        self.lbl_status.configure(text="Scanning...", fg="orange")

        # Background Thread for Walking
        def _scan():
            count = 0
            for root, dirs, files in os.walk(self.project_root):
                for file in files:
                    ext = os.path.splitext(file)[1].lower()
                    if ext in [".xlsx", ".xls", ".pdf", ".jpg", ".png", ".xer", ".ifc"]:
                        path = os.path.join(root, file)
                        import uuid
                        # Check duplication logic? IngestFileJob handles it? logic is inside job usually
                        # But we just fire scan
                        job = IngestFileJob(f"scan_{uuid.uuid4().hex[:6]}", self.active_project_id, path)
                        self.job_manager.submit(job)
                        count += 1

            self._safe_after(0, lambda: self.lbl_status.configure(text=f"Queued {count} files", fg="green"))
            # Trigger dashboard refresh
            self._safe_after(2000, lambda: self.pages["dashboard"].on_show())

        threading.Thread(target=_scan, daemon=True).start()

    @safe_ui_command("Project Load Error")
    def _load_project_env(self, root_path: str):
        try:
            self._reset_shell_state()

            self.project_root = root_path
            self.active_project_id = os.path.basename(os.path.normpath(root_path))

            attach_project_logging(root_path, project_id=self.active_project_id)
            self.config.set_project_root(root_path)
            self.active_project_id = os.path.basename(root_path)

            # Init Manager
            db_dir = os.path.join(root_path, ".serapeum")
            os.makedirs(db_dir, exist_ok=True)
            self.db = DatabaseManager(db_dir, project_id=self.active_project_id)
            self.job_manager = JobManager(self.db, self.active_project_id)

            # Register Handlers (Essential for v02 Spine)
            self.job_manager.register_handler(IngestFileJob)
            self.job_manager.register_handler(ExtractJob)
            self.job_manager.register_handler(FileLinkerJob)
            self.job_manager.register_handler(BuildFactsJob)
            self.job_manager.register_handler(AnalyzeDocJob)

            self.job_manager.start()

            # v02 Intelligence Wiring
            # Note: Services now take both project db and global db where needed
            self.llm_service = LLMService(db=self.db, global_db=self.global_db)
            self.rag_service = RAGService(db=self.db, global_db=self.global_db)
            self.orchestrator = AgentOrchestrator(
                db=self.db,
                global_db=self.global_db,
                llm=self.llm_service,
                rag=self.rag_service
            )

            self.lbl_status.configure(text=f"Project: {self.active_project_id}", fg="green")

            # Show Controls
            self.btn_open.pack_forget()
            self.btn_sync.pack(pady=5, padx=20, fill="x")
            self.switch_auto.pack(pady=5, padx=20, anchor="w")
            self.btn_close.pack(pady=5, padx=20, fill="x")

            # Packet A contract: keep imported dates visible as informational
            # project timeline context only. They do not select answer state yet.
            try:
                dates = self.db.execute(
                    "SELECT DISTINCT date(imported_at, 'unixepoch') "
                    "FROM file_versions ORDER BY imported_at DESC"
                ).fetchall()
                values = ["Current project view"] + [d[0] for d in dates if d and d[0]]
                self.combo_snapshot.configure(values=values)
                self.combo_snapshot.set(values[0])
            except Exception as e:
                print(f"Snapshot load error: {e}")

            # Propagate DB to Pages
            for page in self.pages.values():
                page.controller = self # Refresh ref
                if hasattr(page, 'db'): page.db = self.db # Deprecated but safe
                if hasattr(page, 'on_show'):
                    self._safe_after(0, page.on_show)

            self._update_runtime_controls()
            self._safe_after(300, lambda: self._refresh_runtime_status(prompt_if_needed=False))
            print(f"Project Loaded: {self.active_project_id}")
            if self.switch_auto.get() == 1 and self._runtime_status_code == STATUS_READY:
                self._run_full_scan()

        except Exception as e:
            logger.error("Error loading project: %s", e, exc_info=True)
            self._reset_shell_state()
            self.lbl_status.configure(text="Error loading project", fg=Theme.DANGER_RED)

    def _reset_shell_state(self, for_shutdown: bool = False):
        if self.job_manager:
            self.job_manager.stop(reason="Project closed by user", cancel_incomplete=True)

        try:
            self.config.clear_project_root()
        except Exception:
            logger.debug("Project configuration was not active during reset.", exc_info=True)

        try:
            DatabaseManager.close_all_instances()
        except Exception:
            logger.debug("Database connection cleanup did not complete cleanly.", exc_info=True)

        self.active_project_id = None
        self.project_root = None
        self.db = None
        self.job_manager = None
        self.llm_service = None
        self.orchestrator = None
        self.rag_service = None

        if not for_shutdown:
            self.btn_sync.pack_forget()
            self.switch_auto.pack_forget()
            self.btn_close.pack_forget()
            if not self.btn_open.winfo_manager():
                self.btn_open.pack(pady=5, padx=20, fill="x")

            self.combo_snapshot.configure(values=["Current project view"])
            self.combo_snapshot.set("Current project view")

            self.lbl_status.configure(text="No project loaded", fg=Theme.TEXT_MUTED)
            self.lbl_runtime.configure(text="Runtime: checking...", fg=Theme.TEXT_MUTED)
        self._runtime_status_code = None
        self._runtime_status_message = "Runtime state unavailable."
        self._runtime_setup_in_progress = False
        self._last_runtime_alert_key = None
        try:
            if self.runtime_dialog and self.runtime_dialog.winfo_exists():
                self.runtime_dialog.destroy()
        except Exception:
            logger.debug("Runtime dialog cleanup failed during shell reset.", exc_info=True)
        self.runtime_dialog = None
        if not for_shutdown:
            self._update_runtime_controls()

            for page in self.pages.values():
                reset_view = getattr(page, "reset_view", None)
                if callable(reset_view):
                    reset_view()

            self.show_page("dashboard")

    def _close_project(self):
        self._reset_shell_state()
        self._open_project_dialog()

    def _on_app_close(self):
        if self._is_closing:
            return
        self._is_closing = True
        self._install_shutdown_bgerror_guard()
        try:
            self.protocol("WM_DELETE_WINDOW", lambda: None)
        except Exception:
            pass
        try:
            self.withdraw()
        except Exception:
            logger.debug("Main window withdraw during app close failed.", exc_info=True)
        self._cancel_all_after_callbacks()
        try:
            self._teardown_pages()
        except Exception:
            logger.debug("Page teardown during app close failed.", exc_info=True)
        try:
            if self.active_project_id or self.project_root:
                self._reset_shell_state(for_shutdown=True)
        except Exception:
            logger.debug("Project close sequence during app close failed.", exc_info=True)
        try:
            if self.runtime_dialog and self.runtime_dialog.winfo_exists():
                try:
                    self.runtime_dialog.safe_close()
                except Exception:
                    self.runtime_dialog.destroy()
        except Exception:
            logger.debug("Runtime dialog teardown failed during app close.", exc_info=True)
        try:
            if self.job_manager:
                self.job_manager.stop(reason="Application window closed by user", cancel_incomplete=True)
        except Exception:
            logger.debug("Job manager shutdown during app close failed.", exc_info=True)
        try:
            if self.runtime_setup_service:
                self.runtime_setup_service.cleanup_provisioned_runtime()
        except Exception:
            logger.debug("Runtime cleanup on app close failed.", exc_info=True)
        try:
            DatabaseManager.close_all_instances()
        except Exception:
            logger.debug("Database cleanup on app close failed.", exc_info=True)
        try:
            self.update_idletasks()
        except Exception:
            pass
        try:
            self.quit()
        except Exception:
            logger.debug("Main loop quit during app close failed.", exc_info=True)
        try:
            self.destroy()
        except Exception:
            logger.debug("Main window destroy failed.", exc_info=True)

    def mainloop(self):
        super().mainloop()

if __name__ == "__main__":
    app = MainApp()
    app.mainloop()
