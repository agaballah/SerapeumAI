import customtkinter as ctk
from src.ui.pages.base_page import BasePage
from src.ui.panels.p6_visualizer import P6Visualizer

class SchedulePage(BasePage):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.scroll_body = ctk.CTkScrollableFrame(self, fg_color="#1e1e1e")
        self.scroll_body.grid(row=0, column=0, sticky="nsew")
        
        self.lbl_title = ctk.CTkLabel(self.scroll_body, text="Schedule Explorer (P6)", font=("Arial", 24, "bold"), text_color="#DCE4EE", fg_color="transparent")
        self.lbl_title.pack(anchor="w", pady=20, padx=20)
        
        # Visualizer
        self.visualizer = P6Visualizer(self.scroll_body, controller.db)
        self.visualizer.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
    def on_show(self):
        # Trigger load
        if self.visualizer and self.controller.db:
             self.visualizer.db = self.controller.db # Ensure DB is set
             self.visualizer.load_gantt()
