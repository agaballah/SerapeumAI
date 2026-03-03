import customtkinter as ctk
from src.ui.pages.base_page import BasePage
from src.ui.widgets.fact_table import FactTable

class FactsPage(BasePage):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.scroll_body = ctk.CTkScrollableFrame(self, fg_color="#1e1e1e")
        self.scroll_body.grid(row=0, column=0, sticky="nsew")
        self.scroll_body.grid_columnconfigure(0, weight=1)
        
        # Header
        self.lbl_title = ctk.CTkLabel(self.scroll_body, text="Certified Facts Registry", font=("Arial", 24, "bold"), text_color="#DCE4EE", fg_color="transparent")
        self.lbl_title.grid(row=0, column=0, pady=20, padx=20, sticky="w")
        
        # Fact Table
        self.tbl_facts = FactTable(self.scroll_body, controller.db if controller else None)
        self.tbl_facts.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        
    def on_show(self):
        if self.controller.db:
            self.tbl_facts.db = self.controller.db
            self.tbl_facts.load_facts()
