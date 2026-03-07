import customtkinter as ctk
import tkinter as tk
from src.ui.pages.base_page import BasePage
from src.ui.styles.theme import Theme
from src.ui.panels.p6_visualizer import P6Visualizer

class SchedulePage(BasePage):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.scroll_body = ctk.CTkScrollableFrame(self, fg_color=Theme.BG_DARKEST, bg_color=Theme.BG_DARKEST)
        self.scroll_body.grid(row=0, column=0, sticky="nsew")
        self.scroll_body.grid_columnconfigure(0, weight=1)
        
        # Header
        self.lbl_title = tk.Label(self.scroll_body, text="Project Schedule & Milestones", 
                                  font=Theme.FONT_H2, fg=Theme.TEXT_MAIN, bg=Theme.BG_DARKEST)
        self.lbl_title.grid(row=0, column=0, pady=30, padx=40, sticky="w")
        
        # Visualizer
        self.visualizer = P6Visualizer(self.scroll_body, controller.db)
        self.visualizer.grid(row=1, column=0, sticky="nsew", padx=40, pady=20)
        
    def on_show(self):
        # Trigger load
        if self.visualizer and self.controller.db:
             self.visualizer.db = self.controller.db # Ensure DB is set
             self.visualizer.load_gantt()
