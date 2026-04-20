import logging
import tkinter as tk
import customtkinter as ctk
from tkinter import ttk
from src.ui.pages.base_page import BasePage
from src.ui.styles.theme import Theme

logger = logging.getLogger(__name__)

class ProjectExplorerPage(BasePage):
    """
    Project Explorer / Database Inspector (Phase 5.1)
    Provides a read-only tabular view of the active SQLite project database.
    """
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Header
        self.lbl_title = tk.Label(self, text="Project Database Inspector", 
                                font=Theme.FONT_H1, fg=Theme.TEXT_MAIN, bg=Theme.BG_DARKEST)
        self.lbl_title.grid(row=0, column=0, pady=(40, 20), padx=40, sticky="w")
        
        # Main Viewer
        self.frame_viewer = ctk.CTkFrame(self, fg_color=Theme.BG_DARKER, corner_radius=15, 
                                       border_width=1, border_color=Theme.BG_DARK)
        self.frame_viewer.grid(row=1, column=0, sticky="nsew", padx=40, pady=(0, 40))
        self.frame_viewer.grid_columnconfigure(0, weight=1)
        self.frame_viewer.grid_rowconfigure(1, weight=1)

        # Table Selection
        self.combo_tables = ctk.CTkComboBox(self.frame_viewer, values=["file_versions", "facts", "fact_inputs"], 
                                         command=self._on_table_change,
                                         fg_color=Theme.BG_DARKEST, bg_color=Theme.BG_DARKER, 
                                         button_color=Theme.BG_DARK)
        self.combo_tables.grid(row=0, column=0, padx=25, pady=20, sticky="w")
        
        # Treeview (The actual SQL viewport)
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background=Theme.BG_DARKEST, foreground=Theme.TEXT_MAIN, 
                        fieldbackground=Theme.BG_DARKEST, borderwidth=0, font=Theme.FONT_BODY)
        style.map("Treeview", background=[("selected", Theme.PRIMARY)])
        
        self.tree = ttk.Treeview(self.frame_viewer, columns=(), show="headings")
        self.tree.grid(row=1, column=0, sticky="nsew", padx=25, pady=(0, 25))
        
        # Scrollbars
        self.yscroll = ttk.Scrollbar(self.frame_viewer, orient="vertical", command=self.tree.yview)
        self.yscroll.grid(row=1, column=1, sticky="ns", pady=(0, 25))
        self.tree.configure(yscrollcommand=self.yscroll.set)

    def on_show(self):
        if not self.controller or not self.controller.db:
            self.reset_view()
            return

        self._refresh_table_list()
        self._on_table_change()

    def reset_view(self, message: str = "Open a project to inspect the database."):
        self.combo_tables.configure(values=["No project loaded"])
        self.combo_tables.set("No project loaded")

        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = ("details",)
        self.tree.heading("#0", text="State")
        self.tree.heading("details", text="Details")
        self.tree.column("#0", width=220, anchor="w")
        self.tree.column("details", width=500, anchor="w")
        self.tree.insert("", "end", text="No project loaded", values=(message,))

    def _refresh_table_list(self):
        if not self.controller or not self.controller.db:
            self.reset_view()
            return

        try:
            rows = self.controller.db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            tables = [r[0] for r in rows if not r[0].startswith("sqlite_")]
            if not tables:
                self.reset_view("No database tables are available for the current project.")
                return

            self.combo_tables.configure(values=tables)
            if self.combo_tables.get() not in tables:
                self.combo_tables.set(tables[0])
        except Exception as exc:
            logger.error("Inspector table refresh failed: %s", exc)
            self.reset_view("The database inspector could not read the current project database.")

    def _on_table_change(self, *args):
        table = self.combo_tables.get()
        if not self.controller or not self.controller.db:
            self.reset_view()
            return
        if not table or table == "No project loaded":
            return

        try:
            schema = self.controller.db.execute(f"PRAGMA table_info({table})").fetchall()
            cols = [s[1] for s in schema]
            if not cols:
                self.reset_view(f"Table '{table}' is not available in the current project database.")
                return

            self.tree.delete(*self.tree.get_children())
            self.tree["columns"] = cols
            self.tree.heading("#0", text="Row")
            self.tree.column("#0", width=0, stretch=False)
            for col in cols:
                self.tree.heading(col, text=col)
                self.tree.column(col, width=150, anchor="w")

            data = self.controller.db.execute(f"SELECT * FROM {table} LIMIT 500").fetchall()
            for row in data:
                self.tree.insert("", "end", values=row)

            if not data:
                self.tree.insert("", "end", values=["No rows found" if i == 0 else "" for i in range(len(cols))])

        except Exception as exc:
            logger.error("Inspector Error: %s", exc)
            self.reset_view(f"The database inspector could not open table '{table}'.")
