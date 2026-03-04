import customtkinter as ctk
from src.ui.pages.base_page import BasePage
from src.ui.widgets.smart_import_wizard import SmartImportWizard
from src.application.jobs.ingest_file_job import IngestFileJob

from src.ui.panels.file_detail_panel import FileDetailPanel

class DocumentsPage(BasePage):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.scroll_body = ctk.CTkScrollableFrame(self, fg_color="#1e1e1e")
        self.scroll_body.grid(row=0, column=0, sticky="nsew")
        
        self.lbl_title = ctk.CTkLabel(self.scroll_body, text="Documents & Registers", font=("Arial", 24, "bold"), text_color="#ffffff", fg_color="transparent")
        self.lbl_title.pack(anchor="w", pady=20, padx=20)
        
        # Toolbar
        self.frame_tools = ctk.CTkFrame(self.scroll_body, fg_color="#1a1a1a")
        self.frame_tools.pack(fill="x", padx=20)
        
        self.btn_import = ctk.CTkButton(self.frame_tools, text="Smart Import (Wizard)", command=self.open_wizard)
        self.btn_import.pack(side="left", padx=10, pady=10)
        
        self.btn_refresh = ctk.CTkButton(self.frame_tools, text="Refresh", command=self.refresh_list)
        self.btn_refresh.pack(side="left", padx=10, pady=10)
        
        # File List Area
        self.file_list_frame = ctk.CTkFrame(self.scroll_body, fg_color="#1a1a1a")
        self.file_list_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.scroll_files = self.file_list_frame # Reuse name to avoid deep changes
        
    def open_wizard(self):
        if not self.controller.job_manager:
            print("Job Manager not ready.")
            return
            
        def on_import(path, header_row):
             import uuid
             # We could store header_row in a metadata sidecar or job context
             # For now, just submitting standard ingest, but Wizard proves the UX concept.
             job = IngestFileJob(f"ingest_{uuid.uuid4().hex[:6]}", self.controller.active_project_id, path)
             self.controller.job_manager.submit(job)
             print(f"Submitted {path} (Header: {header_row})")
        
        SmartImportWizard(self, on_import)

    def refresh_list(self):
        """Asynchronous refresh with batch widget creation."""
        # Clear
        for widget in self.scroll_files.winfo_children():
            widget.destroy()
            
        if not self.controller.db:
             return
             
        import threading
        self.lbl_title.configure(text="Documents & Registers (Loading...)")
        threading.Thread(target=self._query_files, daemon=True).start()

    def _query_files(self):
        try:
            # Increase limit slightly for demonstration, but keep batching in mind
            rows = self.controller.db.execute("SELECT source_path, file_id FROM file_versions ORDER BY created_at DESC LIMIT 200").fetchall()
            self.after(0, lambda: self._build_document_rows(rows))
        except Exception as e:
            print(f"DocumentsPage Error: {e}")
            self.after(0, lambda: self.lbl_title.configure(text="Documents & Registers"))

    def _build_document_rows(self, rows, batch_size=20, start_idx=0):
        if not rows:
            self.lbl_title.configure(text="Documents & Registers")
            return
            
        end_idx = min(start_idx + batch_size, len(rows))
        current_batch = rows[start_idx:end_idx]
        
        for r in current_batch:
            path = r[0]
            fname = path.split("\\")[-1]
            fid = r[1]
            
            row = ctk.CTkFrame(self.scroll_files, cursor="hand2", fg_color="#2b2b2b", corner_radius=8, border_width=1, border_color="#3a3a3a")
            row.pack(fill="x", pady=4, padx=10)
            
            # Click Handler
            def open_inspector(event, p=path, f=fid):
                FileDetailPanel(self, self.controller.db, file_id=f, file_path=p)
            
            row.bind("<Button-1>", open_inspector)
            
            lbl = ctk.CTkLabel(row, text=fname, text_color="#DCE4EE", font=("Arial", 13))
            lbl.pack(side="left", padx=15, pady=10)
            lbl.bind("<Button-1>", open_inspector)
            
            status = ctk.CTkLabel(row, text="Ingested", text_color="#00FF00", font=("Arial", 11, "bold"))
            status.pack(side="right", padx=15)
            status.bind("<Button-1>", open_inspector)

        if end_idx < len(rows):
            # Schedule next batch to avoid blocking the UI thread
            self.after(10, lambda: self._build_document_rows(rows, batch_size, end_idx))
        else:
            self.lbl_title.configure(text="Documents & Registers")
