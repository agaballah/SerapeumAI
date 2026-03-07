import os
import logging
import customtkinter as ctk
import tkinter as tk
from src.ui.pages.base_page import BasePage
from src.ui.styles.theme import Theme

logger = logging.getLogger(__name__)

class DashboardPage(BasePage):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Main Scrollable Body
        self.scroll_body = ctk.CTkScrollableFrame(self, fg_color=Theme.BG_DARKEST, bg_color=Theme.BG_DARKEST)
        self.scroll_body.grid(row=0, column=0, sticky="nsew")
        self.scroll_body.grid_columnconfigure(0, weight=1)
        
        # Header Section
        self.frame_header = ctk.CTkFrame(self.scroll_body, fg_color=Theme.BG_DARKEST)
        self.frame_header.grid(row=0, column=0, pady=(40, 20), padx=40, sticky="ew")
        
        self.lbl_title = tk.Label(self.frame_header, text="Project Intelligence Dashboard", 
                                  font=Theme.FONT_H1, fg=Theme.TEXT_MAIN, bg=Theme.BG_DARKEST,
                                  borderwidth=0, highlightthickness=0)
        self.lbl_title.pack(side="left")
        
        # Stats Grid
        self.grid_stats = ctk.CTkFrame(self.scroll_body, fg_color=Theme.BG_DARKEST)
        self.grid_stats.grid(row=1, column=0, sticky="ew", padx=40, pady=10)
        self.grid_stats.grid_columnconfigure((0, 1, 2), weight=1, pad=20)
        
        self.card_files = self._create_stat_card(self.grid_stats, "📂 Files Ingested", "0", 0)
        self.card_facts = self._create_stat_card(self.grid_stats, "🏛️ Facts Qualified", "0", 1)
        self.card_links = self._create_stat_card(self.grid_stats, "🔗 Knowledge Links", "0", 2)
        
        # Activity Section
        self.frame_activity = ctk.CTkFrame(self.scroll_body, fg_color=Theme.BG_DARKER, corner_radius=15, 
                                         border_width=1, border_color=Theme.BG_DARK)
        self.frame_activity.grid(row=2, column=0, sticky="nsew", padx=40, pady=30)
        self.frame_activity.grid_columnconfigure(0, weight=1)
        
        tk.Label(self.frame_activity, text="Mission Control Activity Log", 
                 font=Theme.FONT_H2, fg=Theme.TEXT_MAIN, 
                 bg=Theme.BG_DARKER, borderwidth=0, highlightthickness=0).grid(row=0, column=0, pady=(25, 15), padx=25, sticky="w")
        
        self.txt_logs = ctk.CTkTextbox(self.frame_activity, font=Theme.FONT_MONO, 
                                     text_color=Theme.SUCCESS, fg_color=Theme.BG_DARKEST, 
                                     border_width=1, border_color=Theme.BG_DARK, height=400)
        self.txt_logs.grid(row=1, column=0, sticky="nsew", padx=25, pady=(0, 25))
        self.txt_logs.insert("0.0", ">>> System Ready. Waiting for project telemetry...\n")
        self.txt_logs.configure(state="disabled")
        
    def _create_stat_card(self, master, title, value, col):
        card = ctk.CTkFrame(master, fg_color=Theme.BG_DARKER, corner_radius=12, 
                           border_width=1, border_color=Theme.BG_DARK)
        card.grid(row=0, column=col, sticky="nsew", padx=5)
        
        lbl_t = tk.Label(card, text=title, font=Theme.FONT_BODY, fg=Theme.TEXT_MUTED, bg=Theme.BG_DARKER,
                         borderwidth=0, highlightthickness=0)
        lbl_t.pack(pady=(20, 0), padx=20)
        
        lbl_v = tk.Label(card, text=value, font=Theme.FONT_H1, fg=Theme.PRIMARY, bg=Theme.BG_DARKER,
                         borderwidth=0, highlightthickness=0)
        lbl_v.pack(pady=(5, 20), padx=20)
        
        # Store ref for updates
        setattr(self, f"lbl_val_{col}", lbl_v)
        return card

    def on_show(self):
        self.update_stats()
        
    def update_stats(self):
        if not self.winfo_exists(): return
        
        import threading
        # Run DB work in background
        threading.Thread(target=self._fetch_stats_bg, daemon=True).start()
        
        # Schedule next update
        self.after(3000, self.update_stats)

    def _fetch_stats_bg(self):
        if not self.controller or not self.controller.db: return
        
        try:
            db = self.controller.db
            f_count = db.execute("SELECT count(*) FROM file_versions").fetchone()[0]
            fact_count = db.execute("SELECT count(*) FROM facts").fetchone()[0]
            link_count = db.execute("SELECT count(*) FROM links").fetchone()[0]
            
            log_entries = []
            
            # Extraction Runs
            query_ext = """
                SELECT er.started_at, fv.source_path, er.status, er.diagnostics_json
                FROM extraction_runs er
                JOIN file_versions fv ON er.file_version_id = fv.file_version_id
                ORDER BY er.started_at DESC LIMIT 5
            """
            ext_runs = db.execute(query_ext).fetchall()
            for r in ext_runs:
                fname = os.path.basename(r[1])
                log_entries.append((r[0], f"Extract: {fname}", r[2], r[3]))
            
            # Job Queue (Staging)
            try:
                job_runs = db.execute("SELECT type_name, status, updated_at FROM job_queue ORDER BY updated_at DESC LIMIT 5").fetchall()
                for jr in job_runs:
                    log_entries.append((jr[2], jr[0], jr[1], None))
            except: pass

            # Sort logs by timestamp
            final_log = []
            for ts, label, status, diag in log_entries:
                try:
                    ts_val = int(float(ts)) if ts else 0
                    final_log.append((ts_val, label, status, diag))
                except:
                    final_log.append((0, label, status, diag))

            final_log.sort(key=lambda x: x[0], reverse=True)
            
            # Update UI on main thread
            self.after(0, lambda: self._update_ui_elements(f_count, fact_count, link_count, final_log))
                
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Dashboard Refresh Error: {e}")

    def _update_ui_elements(self, f_count, fact_count, link_count, log_entries):
        if not self.winfo_exists(): return
        
        self.lbl_val_0.configure(text=str(f_count))
        self.lbl_val_1.configure(text=str(fact_count))
        self.lbl_val_2.configure(text=str(link_count))
        
        if log_entries:
            log_text = ""
            for ts, label, status, diag in log_entries[:12]:
                 icon = "✔" if status in ('SUCCESS', 'COMPLETED') else "✖" if status == 'FAILED' else "➤"
                 status_color = "[DONE]" if status in ('SUCCESS', 'COMPLETED') else f"[{status}]"
                 log_text += f"{icon} {label.ljust(40)} {status_color}\n"
                 
                 # Detailed Metrics for Extracts
                 if diag and status == 'SUCCESS' and label.startswith("Extract:"):
                     try:
                         m = json.loads(diag)
                         if isinstance(m, dict) and "page_count" in m:
                             metrics = f"  └─ {m['page_count']} pages, {m['char_count'] // 1000}k chars, {m['image_count']} images, {m['block_count']} blocks"
                             log_text += f"{metrics}\n"
                     except:
                         pass
            
            self.txt_logs.configure(state="normal")
            self.txt_logs.delete("0.0", "end")
            self.txt_logs.insert("0.0", log_text)
            self.txt_logs.configure(state="disabled")
