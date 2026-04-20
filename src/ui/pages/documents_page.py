import os
import customtkinter as ctk
import tkinter as tk
from src.ui.pages.base_page import BasePage
from src.ui.styles.theme import Theme
from src.ui.widgets.smart_import_wizard import SmartImportWizard
from src.application.jobs.ingest_file_job import IngestFileJob

from src.ui.panels.file_detail_panel import FileDetailPanel

class DocumentsPage(BasePage):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.scroll_body = ctk.CTkScrollableFrame(self, fg_color=Theme.BG_DARKEST, bg_color=Theme.BG_DARKEST)
        self.scroll_body.grid(row=0, column=0, sticky="nsew")
        self.scroll_body.grid_columnconfigure(0, weight=1)
        
        # Header Section
        self.frame_header = ctk.CTkFrame(self.scroll_body, fg_color=Theme.BG_DARKEST)
        self.frame_header.grid(row=0, column=0, pady=(40, 20), padx=40, sticky="ew")
        
        self.lbl_title = tk.Label(self.frame_header, text="Project Document Center", 
                                  font=Theme.FONT_H1, fg=Theme.TEXT_MAIN, bg=Theme.BG_DARKEST)
        self.lbl_title.pack(side="left")
        
        # Toolbar
        self.frame_tools = ctk.CTkFrame(self.scroll_body, fg_color=Theme.BG_DARKER, border_width=1, border_color=Theme.BG_DARK)
        self.frame_tools.grid(row=1, column=0, sticky="ew", padx=40, pady=10)
        self.frame_tools.grid_columnconfigure(0, weight=0) # Import button
        self.frame_tools.grid_columnconfigure(1, weight=0) # Refresh button
        self.frame_tools.grid_columnconfigure(2, weight=1) # Empty space to push buttons left
        
        self.btn_import = ctk.CTkButton(self.frame_tools, text="Import Documents", 
                                      fg_color=Theme.PRIMARY, hover_color=Theme.ACCENT,
                                      bg_color=Theme.BG_DARKER,
                                      command=self.open_wizard)
        self.btn_import.grid(row=0, column=0, padx=20, pady=15)
        
        self.btn_refresh = ctk.CTkButton(self.frame_tools, text="Refresh", command=self.refresh_list)
        self.btn_refresh.grid(row=0, column=1, padx=10, pady=15)

        self.lbl_scope = tk.Label(self.frame_tools, text="View Scope:", 
                                  font=Theme.FONT_BODY, fg=Theme.TEXT_MUTED, bg=Theme.BG_DARKER)
        self.lbl_scope.grid(row=0, column=2, padx=(20, 5), pady=15)
        
        self.combo_scope = ctk.CTkComboBox(self.frame_tools, values=["Project Scope", "Global Standards"], 
                                         width=180, fg_color=Theme.BG_DARKEST, border_color=Theme.BG_DARK,
                                         command=self._on_scope_change)
        self.combo_scope.set("Project Scope")
        self.combo_scope.grid(row=0, column=3, padx=10, pady=15)
        
        self.lbl_scope_hint = tk.Label(
            self.frame_tools,
            text="Project Scope shows active project files. Global Standards shows the canonical global standards library.",
            font=Theme.FONT_BODY, fg=Theme.TEXT_MUTED, bg=Theme.BG_DARKER, justify="left", wraplength=520
        )
        self.lbl_scope_hint.grid(row=1, column=0, columnspan=4, padx=20, pady=(0, 15), sticky="w")
        
        # Main Grid / Table Area
        self.frame_main = ctk.CTkFrame(self.scroll_body, fg_color="transparent")
        self.frame_main.grid(row=2, column=0, sticky="nsew", padx=40, pady=20)
        self.frame_main.grid_columnconfigure(0, weight=1)
        
        # File List Area
        self.file_list_frame = ctk.CTkFrame(self.frame_main, fg_color=Theme.BG_DARKER)
        self.file_list_frame.grid(row=0, column=0, sticky="nsew")
        self.file_list_frame.grid_columnconfigure(0, weight=1) # Ensure content expands
        
        self.scroll_files = self.file_list_frame # Reuse name to avoid deep changes
        self._update_scope_context()
        
    def _current_scope_is_global(self) -> bool:
        return self.combo_scope.get() == "Global Standards"

    def _update_scope_context(self):
        if self._current_scope_is_global():
            self.lbl_title.configure(text="Global Standards Library")
            self.lbl_scope_hint.configure(text="Browse standards documents from the canonical global library. This route is reference/import scope, not project truth by itself.")
        else:
            self.lbl_title.configure(text="Project Document Center")
            self.lbl_scope_hint.configure(text="Browse documents stored in the active project workspace.")

    def _on_scope_change(self, _value=None):
        self._update_scope_context()
        self.refresh_list()

    def open_wizard(self):
        if not self.controller.job_manager:
            print("Job Manager not ready.")
            return

        is_global_initial = (self.combo_scope.get() == "Global Standards")
            
        def on_import(path, header_row=0, is_global=is_global_initial):
             import uuid
             # 1.4 Global vs Project Routing Gateway
             job = IngestFileJob(
                 job_id=f"ingest_{uuid.uuid4().hex[:6]}", 
                 project_id="GLOBAL" if is_global else self.controller.active_project_id, 
                 file_path=path, 
                 is_global=is_global
             )
             self.controller.job_manager.submit(job)
             print(f"Submitted {path} (Global: {is_global})")
        
        wizard = SmartImportWizard(self, on_import)
        # Pre-set the global flag in wizard if selected in dropdown
        if hasattr(wizard, 'check_global'):
            if is_global_initial:
                wizard.check_global.select()
            else:
                wizard.check_global.deselect()


    def on_app_close(self):
        super().on_app_close()

    def refresh_list(self):
        """Asynchronous refresh with batch widget creation."""
        # Clear
        for widget in self.scroll_files.winfo_children():
            widget.destroy()
            
        if not (self.controller.global_db if self._current_scope_is_global() else self.controller.db):
             return
             
        import threading
        self.lbl_title.configure(text=("Global Standards Library (Loading...)" if self._current_scope_is_global() else "Project Document Center (Loading...)"))
        is_global_scope = self._current_scope_is_global()
        threading.Thread(target=lambda: self._query_files(is_global_scope), daemon=True).start()

    def _query_files(self, is_global_scope=False):
        try:
            target_db = self.controller.global_db if is_global_scope else self.controller.db
            if not target_db:
                self.safe_ui_after(0, lambda: self._build_document_rows([], is_global_scope))
                return
            # Keep the mounted route honest: global scope is backed by the canonical global DB only.
            rows = target_db.execute("SELECT source_path, file_id FROM file_versions ORDER BY imported_at DESC LIMIT 200").fetchall()
            self.safe_ui_after(0, lambda: self._build_document_rows(rows, is_global_scope=is_global_scope))
        except Exception as e:
            print(f"DocumentsPage Error: {e}")
            self.safe_ui_after(0, lambda: self._build_document_rows([], is_global_scope=is_global_scope))

    def _build_document_rows(self, rows, batch_size=20, start_idx=0, is_global_scope=False):
        if not rows:
            self.lbl_title.configure(text=("Global Standards Library" if is_global_scope else "Project Document Center"))
            return
            
        end_idx = min(start_idx + batch_size, len(rows))
        current_batch = rows[start_idx:end_idx]
        
        for r in current_batch:
            path = r[0]
            fname = path.split("\\")[-1]
            fid = r[1]
            
            row = ctk.CTkFrame(self.scroll_files, cursor="hand2", fg_color=Theme.SURFACE, corner_radius=8, border_width=1, border_color=Theme.BORDER_DIM)
            row.pack(fill="x", pady=4, padx=10)
            
            # Click Handler
            def open_inspector(event, p=path, f=fid):
                target_db = self.controller.global_db if is_global_scope else self.controller.db
                FileDetailPanel(self, target_db, file_id=f, file_path=p)
            
            row.bind("<Button-1>", open_inspector)
            
            lbl = ctk.CTkLabel(row, text=fname, text_color=Theme.TEXT_OFFWHITE, font=("Arial", 13))
            lbl.pack(side="left", padx=15, pady=10)
            lbl.bind("<Button-1>", open_inspector)
            
            status = ctk.CTkLabel(row, text="Ingested", text_color=Theme.SUCCESS, font=("Arial", 11, "bold"))
            status.pack(side="right", padx=15)
            status.bind("<Button-1>", open_inspector)

        if end_idx < len(rows):
            # Schedule next batch to avoid blocking the UI thread
            self.safe_ui_after(10, lambda: self._build_document_rows(rows, batch_size, end_idx, is_global_scope=is_global_scope))
        else:
            self.lbl_title.configure(text=("Global Standards Library" if is_global_scope else "Project Document Center"))
