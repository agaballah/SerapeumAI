# -*- coding: utf-8 -*-
import customtkinter as ctk
from src.ui.pages.base_page import BasePage
from tkinter import ttk

class ValidationQueuePage(BasePage):
    """
    Validation Queue UI - Specifically for HUMAN_REVIEW and CANDIDATE links/facts.
    Priority surface for engineers to certify project truth.
    """
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Header
        self.frame_header = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_header.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        
        self.lbl_title = ctk.CTkLabel(self.frame_header, text="Validation Queue", font=("Arial", 24, "bold"), text_color="#DCE4EE")
        self.lbl_title.pack(side="left")
        
        self.lbl_count = ctk.CTkLabel(self.frame_header, text="(0 items pending)", font=("Arial", 14), text_color="gray")
        self.lbl_count.pack(side="left", padx=10)

        # Table for Candidates
        self.frame_table = ctk.CTkFrame(self, fg_color="#1e1e1e")
        self.frame_table.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        
        # Columns
        columns = ("id", "status", "domain", "type", "description", "confidence", "tier")
        self.tree = ttk.Treeview(self.frame_table, columns=columns, show="headings")
        self.tree.heading("id", text="ID")
        self.tree.heading("status", text="Status")
        self.tree.heading("domain", text="Domain")
        self.tree.heading("type", text="Type")
        self.tree.heading("description", text="Candidate Fact/Link")
        self.tree.heading("confidence", text="Conf.")
        self.tree.heading("tier", text="Tier")

        self.tree.column("status", width=100)
        self.tree.column("confidence", width=80)
        self.tree.column("tier", width=80)
        
        # Configure Row Colors (Tags)
        self.tree.tag_configure("VALIDATED", background="#2a4b2a", foreground="white")  # Dark Green
        self.tree.tag_configure("DRAFT", background="#5b4814", foreground="white")      # Dark Yellow/Gold
        self.tree.tag_configure("REJECTED", background="#5c1e1e", foreground="white")    # Dark Red
        self.tree.tag_configure("SUPERSEDED", background="#333333", foreground="#a0a0a0") # Dim Gray
        self.tree.tag_configure("CANDIDATE", background="#1e3a5f", foreground="white")    # Dark Blue
        
        self.tree.pack(side="left", fill="both", expand=True)
        
        # Buttons
        self.frame_controls = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_controls.grid(row=2, column=0, sticky="ew", padx=20, pady=20)
        
        self.btn_approve = ctk.CTkButton(self.frame_controls, text="Certify Selection", fg_color="green", command=self._on_approve)
        self.btn_approve.pack(side="right", padx=10)
        
        self.btn_reject = ctk.CTkButton(self.frame_controls, text="Reject", fg_color="firebrick", command=self._on_reject)
        self.btn_reject.pack(side="right", padx=10)

    def on_show(self):
        self._load_queue()

    def _load_queue(self):
        if not self.controller.db: return
        
        # Clear
        for i in self.tree.get_children():
            self.tree.delete(i)
            
        # 1. Fetch ALL facts (not just CANDIDATE) to show comprehensive queue
        facts = self.controller.db.execute("SELECT fact_id, status, domain, fact_type, COALESCE(value_text, CAST(value_num AS TEXT)) as val, confidence FROM facts ORDER BY created_at DESC LIMIT 100").fetchall()
        for f in facts:
            status = f[1] or "UNKNOWN"
            self.tree.insert("", "end", values=(f[0], status, f[2], f[3], f[4], f"{f[5]:.2f}", "N/A"), tags=(status,))
            
        # 2. Fetch ALL links
        links = self.controller.db.execute("SELECT link_id, status, 'LINK' as domain, link_type, from_id || ' -> ' || to_id, confidence, confidence_tier FROM links ORDER BY created_at DESC LIMIT 100").fetchall()
        for l in links:
            status = l[1] or "UNKNOWN"
            self.tree.insert("", "end", values=(l[0], status, l[2], l[3], l[4], f"{l[5]:.2f}", l[6]), tags=(status,))
            
        self.lbl_count.configure(text=f"({len(self.tree.get_children())} items total)")

    def _on_approve(self):
        # Implementation of certification logic
        selected = self.tree.selection()
        if not selected: return
        
        for item in selected:
            vals = self.tree.item(item, "values")
            id_val = vals[0]
            domain = vals[2]
            
            if domain == 'LINK':
                self.controller.db.execute("UPDATE links SET status = 'VALIDATED', validated_at = strftime('%s','now') WHERE link_id = ?", (id_val,))
            else:
                self.controller.db.execute("UPDATE facts SET status = 'VALIDATED', updated_at = strftime('%s','now') WHERE fact_id = ?", (id_val,))
        
        self.controller.db.commit()
        self._load_queue()

    def _on_reject(self):
        selected = self.tree.selection()
        if not selected: return
        
        for item in selected:
            vals = self.tree.item(item, "values")
            id_val = vals[0]
            domain = vals[2]
            
            if domain == 'LINK':
                self.controller.db.execute("UPDATE links SET status = 'REJECTED' WHERE link_id = ?", (id_val,))
            else:
                self.controller.db.execute("UPDATE facts SET status = 'REJECTED' WHERE fact_id = ?", (id_val,))
        
        self.controller.db.commit()
        self._load_queue()
