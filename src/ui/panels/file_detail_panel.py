import customtkinter as ctk
import pandas as pd
import json
import logging
import os
from src.ui.styles.theme import Theme

logger = logging.getLogger(__name__)

class FileDetailPanel(ctk.CTkToplevel):
    def __init__(self, parent, db, file_id=None, file_path=None):
        super().__init__(parent, fg_color=Theme.BG_DARKEST)
        
        self.db = db
        self.file_path = file_path
        self.file_id = file_id
        
        self.title("File Inspector")
        self.geometry("900x700")
        
        # Grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # 1. Header
        filename = os.path.basename(file_path) if file_path else "Unknown"
        self.lbl_title = ctk.CTkLabel(self, text=f"Inspecting: {filename}", 
                                    font=Theme.FONT_H2, text_color=Theme.TEXT_MAIN, fg_color=Theme.BG_DARKEST)
        self.lbl_title.grid(row=0, column=0, pady=20, padx=30, sticky="w")
        
        # 2. Tabs
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        
        self.tab_preview = self.tabview.add("Preview")
        self.tab_meta = self.tabview.add("Metadata")
        self.tab_extract = self.tabview.add("Extraction Results")
        self.tab_vision = self.tabview.add("Vision Analysis")
        
        self.tabview.set("Preview")
        
        # 3. Content - Preview
        self.txt_preview = ctk.CTkTextbox(self.tab_preview, font=Theme.FONT_MONO, 
                                        text_color=Theme.TEXT_MAIN, fg_color=Theme.BG_DARKER,
                                        border_width=1, border_color=Theme.BG_DARK)
        self.txt_preview.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 4. Content - Metadata
        self.txt_meta = ctk.CTkTextbox(self.tab_meta, font=Theme.FONT_MONO, 
                                     text_color=Theme.TEXT_MAIN, fg_color=Theme.BG_DARKER,
                                     border_width=1, border_color=Theme.BG_DARK)
        self.txt_meta.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 5. Content - Extraction (Table)
        self.txt_extract = ctk.CTkTextbox(self.tab_extract, text_color=Theme.TEXT_MAIN, 
                                        fg_color=Theme.BG_DARKER, border_width=1, border_color=Theme.BG_DARK) 
        self.txt_extract.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 6. Content - Vision Analysis
        self.txt_vision = ctk.CTkTextbox(self.tab_vision, font=Theme.FONT_MONO, 
                                       text_color=Theme.TEXT_MAIN, fg_color=Theme.BG_DARKER,
                                       border_width=1, border_color=Theme.BG_DARK)
        self.txt_vision.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Load Data
        self._load_data()
        
    def _load_data(self):
        try:
            # 1. Load Preview (First 2kb)
            if self.file_path and os.path.exists(self.file_path):
                try:
                    with open(self.file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read(2000)
                        self.txt_preview.insert("0.0", content + "\n... (Truncated)")
                except Exception as e:
                    self.txt_preview.insert("0.0", f"Cannot read file preview: {e}")
                    
            # 2. Load Metadata (DB)
            if self.db:
                # Find file_version_id
                # Note: We might be passed file_id (Registry) or file_version_id
                # For now assume lookup by PATH if ID not robust
                rows = self.db.execute("SELECT * FROM file_versions WHERE source_path LIKE ?", (f"%{os.path.basename(self.file_path)}%",)).fetchone()
                
                if rows:
                    meta = dict(rows)
                    self.txt_meta.insert("0.0", json.dumps(meta, indent=2, default=str))
                    
                    # 3. Load Extraction Runs
                    file_ver_id = meta.get("file_version_id")
                    if file_ver_id:
                        runs = self.db.execute("SELECT * FROM extraction_runs WHERE file_version_id=?", (file_ver_id,)).fetchall()
                        if runs:
                            run_log = ""
                            for r in runs:
                                run_log += f"Run ID: {r[0]}\nStatus: {r[6]}\nStart: {r[4]}\nDiagnostics: {r[7]}\n"
                                run_log += "-"*40 + "\n"
                            self.txt_extract.insert("0.0", run_log)
                        else:
                            self.txt_extract.insert("0.0", "No extraction runs found for this version.")
                            
                        # 4. Load Vision Analysis (from pages table)
                        try:
                            # doc_id is needed. We can derive it or lookup by version_id
                            doc_row = self.db.execute("SELECT doc_id FROM documents WHERE abs_path = ? OR file_name = ?", (self.file_path, self.file_path)).fetchone()
                            if doc_row:
                                doc_id = doc_row[0]
                                pages = self.db.list_pages(doc_id)
                                if pages:
                                    vision_log = ""
                                    for p in pages:
                                        p_idx = p.get("page_index", 0) + 1
                                        v_gen = p.get("vision_general") or ""
                                        v_det = p.get("vision_detailed") or ""
                                        summary = p.get("page_summary_short") or ""
                                        
                                        vision_log += f"--- PAGE {p_idx} ---\n"
                                        if summary: vision_log += f"Summary: {summary}\n"
                                        if v_gen: vision_log += f"General Vision: {v_gen[:150]}...\n"
                                        if v_det: vision_log += f"Detailed Analysis:\n{v_det}\n"
                                        vision_log += "\n"
                                    self.txt_vision.insert("0.0", vision_log)
                                else:
                                    self.txt_vision.insert("0.0", "No analyzed pages found.")
                            else:
                                self.txt_vision.insert("0.0", "Document ID not found in mapping.")
                        except Exception as ve:
                             self.txt_vision.insert("0.0", f"Error loading vision: {ve}")
                else:
                    self.txt_meta.insert("0.0", "No database record found for this file.")
                    
        except Exception as e:
            logger.error(f"Error loading details: {e}")
