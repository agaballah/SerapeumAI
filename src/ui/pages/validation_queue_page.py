import customtkinter as ctk
import tkinter as tk
from src.ui.pages.base_page import BasePage
from tkinter import ttk
from src.ui.styles.theme import Theme

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
        self.frame_header = ctk.CTkFrame(self, fg_color=Theme.BG_DARKEST)
        self.frame_header.grid(row=0, column=0, sticky="ew", padx=30, pady=(20, 10))
        
        self.lbl_title = tk.Label(self.frame_header, text="Validation Queue", 
                                  font=Theme.FONT_H1, fg=Theme.TEXT_MAIN, bg=Theme.BG_DARKEST)
        self.lbl_title.pack(side="left")
        
        self.lbl_count = tk.Label(self.frame_header, text="(0 items)", 
                                  font=Theme.FONT_BODY, fg=Theme.TEXT_MUTED, bg=Theme.BG_DARKEST)
        self.lbl_count.pack(side="left", padx=15)
        
        # New: Confidence Filter
        self.combo_filter = ctk.CTkComboBox(
            self.frame_header, 
            values=["Candidates Only", "Show All", "Auto-Validated Only"],
            command=lambda _: self._load_queue()
        )
        self.combo_filter.set("Candidates Only")
        self.combo_filter.pack(side="right", padx=10)
        
        self.lbl_filter = ctk.CTkLabel(self.frame_header, text="Filter:", font=("Arial", 12))
        self.lbl_filter.pack(side="right", padx=5)

        # Table for Candidates
        self.frame_table = ctk.CTkFrame(self, fg_color=Theme.BG_DARKER, corner_radius=15, 
                                      border_width=1, border_color=Theme.BG_DARK)
        self.frame_table.grid(row=1, column=0, sticky="nsew", padx=30, pady=0)
        
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
        
        # Configure Row Colors (Tags - Subtle Dark Shades)
        self.tree.tag_configure("VALIDATED", background="#064e3b", foreground="white") 
        self.tree.tag_configure("DRAFT", background="#78350f", foreground="white")     
        self.tree.tag_configure("REJECTED", background="#7f1d1d", foreground="white")   
        self.tree.tag_configure("SUPERSEDED", background="#18181b", foreground="#52525b") 
        self.tree.tag_configure("CANDIDATE", background="#1e3a8a", foreground="white")    
        
        self.tree.pack(side="left", fill="both", expand=True)
        
        # Buttons
        self.frame_controls = ctk.CTkFrame(self, fg_color=Theme.BG_DARKEST)
        self.frame_controls.grid(row=3, column=0, sticky="ew", padx=30, pady=20)
        
        self.btn_approve = ctk.CTkButton(self.frame_controls, text="Certify Selection", 
                                       fg_color=Theme.SUCCESS, hover_color="#16a34a", command=self._on_approve)
        self.btn_approve.pack(side="right", padx=10)
        
        self.btn_reject = ctk.CTkButton(self.frame_controls, text="Reject", 
                                      fg_color=Theme.DANGER, hover_color="#dc2626", command=self._on_reject)
        self.btn_reject.pack(side="right", padx=10)

    def on_show(self):
        self._load_queue()

    def _load_queue(self):
        if not self.controller.db: return
        
        filter_mode = self.combo_filter.get()
        
        # Clear
        for i in self.tree.get_children():
            self.tree.delete(i)
            
        # 1. Fetch ALL facts (not just CANDIDATE) to show comprehensive queue
        facts = self.controller.db.execute("SELECT fact_id, status, domain, fact_type, COALESCE(value_text, CAST(value_num AS TEXT)) as val, confidence FROM facts ORDER BY created_at DESC LIMIT 100").fetchall()
        for f in facts:
            status = f[1] or "UNKNOWN"
            # Currently facts don't have tiers as prominently as links, but we apply status filtering if needed
            self.tree.insert("", "end", values=(f[0], status, f[2], f[3], f[4], f"{f[5]:.2f}", "N/A"), tags=(status,))
            
        # 2. Fetch ALL links with Tier filtering
        q_links = "SELECT link_id, status, 'LINK' as domain, link_type, from_id || ' -> ' || to_id, confidence, confidence_tier FROM links"
        params = []
        
        if filter_mode == "Candidates Only":
            q_links += " WHERE confidence_tier != 'AUTO_VALIDATED'"
        elif filter_mode == "Auto-Validated Only":
            q_links += " WHERE confidence_tier = 'AUTO_VALIDATED'"
            
        q_links += " ORDER BY created_at DESC LIMIT 100"
        
        links = self.controller.db.execute(q_links, params).fetchall()
        for l in links:
            status = l[1] or "UNKNOWN"
            tier = l[6] or "CANDIDATE"
            self.tree.insert("", "end", values=(l[0], status, l[2], l[3], l[4], f"{l[5]:.2f}", tier), tags=(status,))
            
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
