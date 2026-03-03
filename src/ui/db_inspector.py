# -*- coding: utf-8 -*-
"""
db_inspector.py — Simple Database Inspection Dialog
---------------------------------------------------
"""
import tkinter as tk
from tkinter import ttk

class DBInspectorDialog(tk.Toplevel):
    def __init__(self, parent, db_manager):
        super().__init__(parent)
        self.title("Database Inspector")
        self.geometry("600x500")
        self.db = db_manager
        
        self.create_widgets()
        self.load_stats()
        
    def create_widgets(self):
        tabs = ttk.Notebook(self)
        tabs.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Tab 1: Overview
        self.tab_overview = ttk.Frame(tabs)
        tabs.add(self.tab_overview, text="Overview")
        
        # Tab 2: Tables
        self.tab_tables = ttk.Frame(tabs)
        tabs.add(self.tab_tables, text="Tables")
        
        # Overview Content
        self.stats_frame = ttk.LabelFrame(self.tab_overview, text="Statistics", padding=10)
        self.stats_frame.pack(fill="x", padx=10, pady=10)
        
        self.lbl_docs = ttk.Label(self.stats_frame, text="Documents: ...")
        self.lbl_docs.pack(anchor="w")
        
        self.lbl_pages = ttk.Label(self.stats_frame, text="Pages: ...")
        self.lbl_pages.pack(anchor="w")
        
        self.lbl_vision = ttk.Label(self.stats_frame, text="Pending Vision: ...")
        self.lbl_vision.pack(anchor="w")

        # Tables Content
        self.tree_tables = ttk.Treeview(self.tab_tables, columns=("Name", "Rows"), show="headings")
        self.tree_tables.heading("Name", text="Table Name")
        self.tree_tables.heading("Rows", text="Row Count")
        self.tree_tables.pack(fill="both", expand=True, padx=5, pady=5)
        
        btn_refresh = ttk.Button(self, text="Refresh", command=self.load_stats)
        btn_refresh.pack(pady=5)
        
    def load_stats(self):
        if not self.db:
            return
            
        try:
            # 1. Overview
            doc_count = self.db.get_document_count() if hasattr(self.db, "get_document_count") else "N/A"
            # Manually query if method missing
            if doc_count == "N/A":
                res = self.db._query("SELECT COUNT(*) as c FROM documents")
                doc_count = res[0]["c"] if res else 0

            page_count_res = self.db._query("SELECT COUNT(*) as c FROM pages")
            page_count = page_count_res[0]["c"] if page_count_res else 0
            
            # Vision needed
            vision_res = self.db._query("SELECT COUNT(*) as c FROM pages WHERE vision_general IS NULL AND (has_raster=1 OR has_vector=1)")
            vision_count = vision_res[0]["c"] if vision_res else 0
            
            self.lbl_docs.config(text=f"Documents: {doc_count}")
            self.lbl_pages.config(text=f"Total Pages: {page_count}")
            self.lbl_vision.config(text=f"Pending Vision: {vision_count} (Estimated)")
            
            # 2. Tables
            for item in self.tree_tables.get_children():
                self.tree_tables.delete(item)
                
            tables = self.db._query("SELECT name FROM sqlite_master WHERE type='table'")
            for t in tables:
                name = t["name"]
                # Count rows
                try:
                    c_res = self.db._query(f"SELECT COUNT(*) as c FROM {name}")
                    count = c_res[0]["c"]
                except Exception:
                    count = "?"
                self.tree_tables.insert("", "end", values=(name, count))
                
        except Exception as e:
            print(f"Stats Error: {e}")
