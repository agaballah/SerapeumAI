import os
import sys
import threading
import logging
import customtkinter as ctk
import tkinter as tk
from typing import Optional

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

# Pages
from src.ui.pages.dashboard_page import DashboardPage
from src.ui.pages.facts_page import FactsPage
from src.ui.pages.documents_page import DocumentsPage
from src.ui.pages.schedule_page import SchedulePage
from src.ui.pages.chat_page import ChatPage
from src.ui.pages.truth_map_page import TruthMapPage

from src.utils.hardening import safe_ui_command

from src.ui.styles.theme import Theme

logger = logging.getLogger(__name__)


class MainApp(ctk.CTk):
    def __init__(self, root_dir: str = None):
        super().__init__()
        self.title("Serapeum AI | Engineering Truth Engine")
        self.geometry("1400x900")

        # Absolute Nuclear Hardening
        # Theme.apply_to_all() already handles global bg configuration in run.py

        # State
        self.config = get_config()
        self.global_db: Optional[DatabaseManager] = None
        self.db: Optional[DatabaseManager] = None
        self.project_root: Optional[str] = None
        self.active_project_id: Optional[str] = None
        self.job_manager: Optional[JobManager] = None
        self.llm_service: Optional[LLMService] = None
        self.orchestrator: Optional[AgentOrchestrator] = None
        self.rag_service: Optional[RAGService] = None

        # Initialize Global DB
        try:
            g_path = global_db_path()
            g_root = os.path.dirname(g_path)
            g_name = os.path.basename(g_path)
            m_dir = os.path.join(os.path.dirname(__file__), "..", "infra", "persistence", "global_migrations")
            self.global_db = DatabaseManager(root_dir=g_root, db_name=g_name, migrations_dir=m_dir)
            logger.info(f"MainApp: Global DB initialized at {g_path}")
        except Exception as e:
            logger.error(f"MainApp: Global DB init failed: {e}")

        # Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_content_area()

        # Load Project if provided
        if root_dir and os.path.exists(root_dir):
            self.after(100, lambda: self._load_project_env(root_dir))
        else:
             self._open_project_dialog()

    def _build_sidebar(self):
        self.frame_sidebar = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=Theme.BG_DARKER, border_width=0)
        self.frame_sidebar.grid(row=0, column=0, sticky="nsew")
        self.frame_sidebar.grid_rowconfigure(10, weight=1)

        # Logo using standard tk.Label to bypass CTK white-box bug
        self.lbl_logo = tk.Label(self.frame_sidebar, text="SERAPEUM", font=Theme.FONT_H1,
                                 fg=Theme.TEXT_MAIN, bg=Theme.BG_DARKER,
                                 padx=0, pady=0, borderwidth=0, highlightthickness=0)
        self.lbl_logo.grid(row=0, column=0, padx=20, pady=(30, 20))

        self.btn_dashboard = self._nav_btn("ðŸ  Dashboard", "dashboard", 1)
        self.btn_facts = self._nav_btn("ðŸ›ï¸ Facts", "facts", 2)
        self.btn_schedule = self._nav_btn("ðŸ“… Schedule", "schedule", 3)
        self.btn_docs = self._nav_btn("ðŸ“‚ Documents", "documents", 4)
        self.btn_chat = self._nav_btn("ðŸ¤– Expert Chat", "chat", 5)
        self.btn_truth_map = self._nav_btn("ðŸŒ Truth Map", "truth_map", 6)

        # Primary Action
        self.lbl_snapshot = tk.Label(self.frame_sidebar, text="Snapshot (As-Of)", anchor="w",
                                     fg=Theme.TEXT_MUTED, bg=Theme.BG_DARKER, font=Theme.FONT_BODY,
                                     borderwidth=0, highlightthickness=0)
        self.lbl_snapshot.grid(row=6, column=0, padx=20, pady=(20, 0), sticky="w")

        self.combo_snapshot = ctk.CTkComboBox(self.frame_sidebar, values=["Current"], command=self._on_snapshot_change,
                                            fg_color=Theme.BG_DARKEST,
                                            bg_color=Theme.BG_DARKER,
                                            border_color=Theme.BG_DARK,
                                            button_color=Theme.BG_DARK, button_hover_color=Theme.ACCENT)
        self.combo_snapshot.grid(row=7, column=0, padx=20, pady=(5, 10), sticky="ew")

        # Helper frame for buttons
        self.frame_actions = ctk.CTkFrame(self.frame_sidebar, fg_color=Theme.BG_DARKER, bg_color=Theme.BG_DARKER)
        self.frame_actions.grid(row=8, column=0, sticky="ew", padx=0)

        self.btn_sync = ctk.CTkButton(self.frame_actions, text="âš¡ Sync Project",
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

        # Bottom Status
        self.lbl_status = tk.Label(self.frame_sidebar, text="Not Loaded",
                                   fg=Theme.TEXT_MUTED, bg=Theme.BG_DARKER,
                                   borderwidth=0, highlightthickness=0)
        self.lbl_status.grid(row=10, column=0, padx=20, pady=10)

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

        for p in self.pages.values():
            p.grid(row=0, column=0, sticky="nsew")
            p.configure(fg_color=Theme.BG_DARKEST) # Explicit enforcement

        self.show_page("dashboard")

    def _on_snapshot_change(self, value):
        print(f"Snapshot changed to: {value}")
        # Notify all pages to refresh with filter
        for page in self.pages.values():
            if hasattr(page, 'on_show'):
                page.on_show()

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
         else:
             print("No folder selected.")

    @safe_ui_command("Project Sync Error")
    def _run_full_scan(self):
        if not self.project_root: return
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

            self.after(0, lambda: self.lbl_status.configure(text=f"Queued {count} files", fg="green"))
            # Trigger dashboard refresh
            self.after(2000, lambda: self.pages["dashboard"].on_show())

        threading.Thread(target=_scan, daemon=True).start()

    @safe_ui_command("Project Load Error")
    def _load_project_env(self, root_path: str):
        try:
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
            self.btn_sync.pack(pady=5, padx=20, fill="x")
            self.switch_auto.pack(pady=5, padx=20, anchor="w")
            self.btn_close.pack(pady=5, padx=20, fill="x")

            # Populate Snapshots (As-Of Dates)
            # Use distinct imported_at dates, formatted
            try:
                dates = self.db.execute("SELECT DISTINCT date(imported_at, 'unixepoch') FROM file_versions ORDER BY imported_at DESC").fetchall()
                values = ["Current"] + [d[0] for d in dates]
                self.combo_snapshot.configure(values=values)
            except Exception as e:
                print(f"Snapshot load error: {e}")

            # Propagate DB to Pages
            for page in self.pages.values():
                page.controller = self # Refresh ref
                if hasattr(page, 'db'): page.db = self.db # Deprecated but safe
                if hasattr(page, 'on_show'):
                    self.after(0, page.on_show)

            print(f"Project Loaded: {self.active_project_id}")
            if self.switch_auto.get() == 1:
                self._run_full_scan()

        except Exception as e:
            print(f"Error loading project: {e}")
            self.lbl_status.configure(text="Error Loading Project", fg="red")
            print(f"Error: {e}")

    def _close_project(self):
        if self.job_manager:
            self.job_manager.stop()

        self.active_project_id = None
        self.project_root = None
        self.db = None
        self.job_manager = None

        # Hide Controls
        self.btn_sync.pack_forget()
        self.switch_auto.pack_forget()
        self.btn_close.pack_forget()

        self.lbl_status.configure(text="No Project Loaded", text_color="gray")
        self._open_project_dialog()

    def mainloop(self):
        super().mainloop()

if __name__ == "__main__":
    app = MainApp()
    app.mainloop()
