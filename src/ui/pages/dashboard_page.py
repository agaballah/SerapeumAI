import os
import customtkinter as ctk
from src.ui.pages.base_page import BasePage
from src.ui.widgets.fact_table import FactTable

class DashboardPage(BasePage):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Main Scrollable Body
        self.scroll_body = ctk.CTkScrollableFrame(self, fg_color="#1e1e1e", bg_color="#1e1e1e")
        self.scroll_body.grid(row=0, column=0, sticky="nsew")
        self.scroll_body.grid_columnconfigure(0, weight=1)
        
        # Header
        self.lbl_title = ctk.CTkLabel(self.scroll_body, text="Project Dashboard", font=("Arial", 24, "bold"), text_color="#ffffff", fg_color="transparent")
        self.lbl_title.grid(row=0, column=0, pady=20, padx=20, sticky="w")
        
        # Stats Cards
        self.frame_stats = ctk.CTkFrame(self.scroll_body, fg_color="#252525") # Slightly lighter card
        self.frame_stats.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        
        self.lbl_files = ctk.CTkLabel(self.frame_stats, text="Files Ingested: --", font=("Arial", 16), text_color="#ffffff", fg_color="transparent")
        self.lbl_files.pack(side="left", padx=20, pady=20)
        
        self.lbl_facts = ctk.CTkLabel(self.frame_stats, text="Facts Qualified: --", font=("Arial", 16), text_color="#ffffff", fg_color="transparent")
        self.lbl_facts.pack(side="left", padx=20, pady=10)
        
        # Recent Activity (Logs) - Occupies more space in new layout
        self.frame_logs = ctk.CTkFrame(self.scroll_body, fg_color="#1e1e1e")
        self.frame_logs.grid(row=2, column=0, sticky="nsew", padx=20, pady=10)
        self.frame_logs.grid_columnconfigure(0, weight=1)
        self.frame_logs.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(self.frame_logs, text="Mission Control Activity Log", font=("Arial", 14, "bold"), text_color="#ffffff", fg_color="transparent").grid(row=0, column=0, pady=5)
        
        self.txt_logs = ctk.CTkTextbox(self.frame_logs, font=("Consolas", 11), text_color="#00FF00", fg_color="black", height=300) # Terminal look
        self.txt_logs.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.txt_logs.insert("0.0", "System Initialized. Waiting for project load...\n")
        self.txt_logs.configure(state="disabled")
        
    def on_show(self):
        self.update_stats()
        
    def update_stats(self):
        if not self.winfo_exists(): return
        
        import threading
        # Run DB work in background
        threading.Thread(target=self._fetch_stats_bg, daemon=True).start()
        
        # Schedule next update (Live UI)
        self.after(2000, self.update_stats)

    def _fetch_stats_bg(self):
        if not self.controller.db: return
        
        try:
            db = self.controller.db
            f_count = db.execute("SELECT count(*) FROM file_versions").fetchone()[0]
            fact_count = db.execute("SELECT count(*) FROM facts").fetchone()[0]
            
            log_entries = []
            
            # Extraction Runs - Optimized with JOIN to avoid N+1
            query_ext = """
                SELECT er.started_at, fv.source_path, er.status 
                FROM extraction_runs er
                JOIN file_versions fv ON er.file_version_id = fv.file_version_id
                ORDER BY er.started_at DESC LIMIT 5
            """
            ext_runs = db.execute(query_ext).fetchall()
            for r in ext_runs:
                fname = os.path.basename(r[1])
                log_entries.append((r[0], f"Extract: {fname}", r[2]))
            
            # Job Queue
            job_runs = db.execute("SELECT type_name, status, updated_at, payload_json FROM job_queue ORDER BY updated_at DESC LIMIT 5").fetchall()
            for jr in job_runs:
                j_type = jr[0]
                j_status = jr[1]
                try:
                    import json as _json
                    payload = _json.loads(jr[3])
                    ref = payload.get("doc_id") or payload.get("builder_type") or "Job"
                    log_entries.append((jr[2], f"{j_type}: {ref}", j_status))
                except:
                    log_entries.append((jr[2], j_type, j_status))

            # Ensure all timestamps are consistent types (int) for sorting
            final_log = []
            for ts, label, status in log_entries:
                try:
                    # Try to parse as float/int if it looks like a timestamp
                    if isinstance(ts, str) and "-" in ts: # ISO string
                        from datetime import datetime
                        # Basic ISO parse
                        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                        ts_val = int(dt.timestamp())
                    else:
                        ts_val = int(float(ts)) if ts else 0
                    final_log.append((ts_val, label, status))
                except:
                    final_log.append((0, label, status))

            final_log.sort(key=lambda x: x[0], reverse=True)
            
            # Update UI on main thread
            self.after(0, lambda: self._update_ui_elements(f_count, fact_count, final_log))
                
        except Exception as e:
            import traceback
            logger.error(f"Dashboard Refresh Error: {e}\n{traceback.format_exc()}")

    def _update_ui_elements(self, f_count, fact_count, log_entries):
        if not self.winfo_exists(): return
        
        self.lbl_files.configure(text=f"Files Ingested: {f_count}")
        self.lbl_facts.configure(text=f"Facts Qualified: {fact_count}")
        
        if log_entries:
            log_text = ""
            for ts, label, status in log_entries[:10]:
                 status_icon = "✓" if status in ('SUCCESS', 'COMPLETED') else "x" if status == 'FAILED' else "..."
                 log_text += f"[{status_icon}] {label} ({status})\n"
            
            self.txt_logs.configure(state="normal")
            self.txt_logs.delete("0.0", "end")
            self.txt_logs.insert("0.0", log_text)
            self.txt_logs.configure(state="disabled")
