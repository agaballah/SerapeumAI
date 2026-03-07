import customtkinter as ctk
import tkinter as tk
from src.ui.pages.base_page import BasePage
from src.ui.widgets.fact_table import FactTable
from src.ui.styles.theme import Theme

class FactsPage(BasePage):
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
        
        self.lbl_title = tk.Label(self.frame_header, text="Qualified Fact Repository", 
                                  font=Theme.FONT_H1, fg=Theme.TEXT_MAIN, bg=Theme.BG_DARKEST)
        self.lbl_title.pack(side="left")
        
        # Fact Table
        self.tbl_facts = FactTable(self.scroll_body, controller.db if controller else None)
        self.tbl_facts.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        
    def on_show(self):
        if self.controller.db:
            self.tbl_facts.db = self.controller.db
            self.tbl_facts.load_facts()
