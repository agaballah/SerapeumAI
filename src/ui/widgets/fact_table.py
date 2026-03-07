
import customtkinter as ctk
from tkinter import ttk
import tkinter as tk
from src.ui.styles.theme import Theme

class FactTable(ctk.CTkFrame):
    def __init__(self, parent, db_window):
        super().__init__(parent, fg_color=Theme.BG_DARKER, corner_radius=0)
        self.db = db_window
        
        # Style Treeview
        style = ttk.Style()
        style.theme_use("clam")
        
        # Noir Mode Colors
        bg_color = Theme.BG_DARKER
        fg_color = Theme.TEXT_MAIN
        hl_color = Theme.PRIMARY
        
        style.configure("Treeview", 
                        background=bg_color, 
                        foreground=fg_color, 
                        fieldbackground=bg_color, 
                        bordercolor=bg_color, 
                        borderwidth=0,
                        font=Theme.FONT_BODY)
                        
        style.map("Treeview", background=[("selected", hl_color)], foreground=[("selected", "#ffffff")])
        
        style.configure("Treeview.Heading", 
                        background=Theme.BG_DARK, 
                        foreground=Theme.TEXT_MAIN, 
                        relief="flat",
                        font=Theme.FONT_H3)
        
        # Columns
        columns = ("fact_id", "type", "subject", "value", "status")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", selectmode="browse")
        
        self.tree.heading("fact_id", text="ID")
        self.tree.heading("type", text="Fact Type")
        self.tree.heading("subject", text="Subject")
        self.tree.heading("value", text="Value")
        self.tree.heading("status", text="Status")
        
        self.tree.column("fact_id", width=100)
        self.tree.column("type", width=150)
        self.tree.column("subject", width=150)
        self.tree.column("value", width=300)
        self.tree.column("status", width=80)
        
        # Scrollbar
        self.scrollbar = ctk.CTkScrollbar(self, command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.scrollbar.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # Pagination state
        self.page_size = 50
        self.offset = 0
        self.is_loading = False
        
        # Bind double click for Lineage
        self.tree.bind("<Double-1>", self.on_double_click)
        
        # Bind scroll for infinite loading
        self.scrollbar.configure(command=self._on_scroll)
        self.tree.configure(yscrollcommand=self._on_tree_scroll)

    def _on_scroll(self, *args):
        self.tree.yview(*args)

    def _on_tree_scroll(self, first, last):
        self.scrollbar.set(first, last)
        # Check if we're near the bottom (last > 0.9)
        if float(last) > 0.9 and not self.is_loading:
            self.load_next_page()

    def load_facts(self):
        """Initial load - clears and starts from offset 0."""
        self.offset = 0
        # Clear
        for i in self.tree.get_children():
            self.tree.delete(i)
        self.load_next_page()

    def load_next_page(self):
        if not self.db or self.is_loading: return
        self.is_loading = True
        
        # Fetch filter from controller (MainApp) on MAIN THREAD
        snapshot_date = "Current"
        if hasattr(self.master, 'controller'):
             snapshot_date = self.master.controller.combo_snapshot.get()

        import threading
        threading.Thread(target=self._query_and_populate, args=(snapshot_date,), daemon=True).start()

    def _query_and_populate(self, snapshot_date):
        query = """
            SELECT fact_id, fact_type, subject_id, 
                   COALESCE(value_text, CAST(value_num AS TEXT), value_json) as val, 
                   status 
            FROM facts
        """
        params = []
        
        if snapshot_date and snapshot_date != "Current":
             query += " WHERE date(created_at, 'unixepoch') <= ?"
             params.append(snapshot_date)
             
        query += f" ORDER BY created_at DESC LIMIT {self.page_size} OFFSET {self.offset}"
        
        try:
            rows = self.db.execute(query, params).fetchall()
            
            # Update UI from main thread
            self.after(0, lambda: self._append_rows(rows))
            
        except Exception as e:
            print(f"FactTable Error: {e}")
            self.is_loading = False

    def _append_rows(self, rows):
        if not rows:
            self.is_loading = False
            return
            
        for r in rows:
            val_str = str(r[3])[:50] if r[3] else ""
            self.tree.insert("", "end", values=(r[0], r[1], r[2], val_str, r[4]))
            
        self.offset += len(rows)
        self.is_loading = False

    def on_double_click(self, event):
        item = self.tree.selection()
        if not item: return
        vals = self.tree.item(item, "values")
        fact_id = vals[0]
        
        from src.ui.widgets.fact_lineage_popup import FactLineagePopup
        FactLineagePopup(self, self.db, fact_id)
