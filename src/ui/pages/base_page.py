import customtkinter as ctk
from src.ui.styles.theme import Theme

class BasePage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color=Theme.BG_DARKEST, corner_radius=0)
        self.controller = controller
        
    def on_show(self):
        """Called when this page is displayed."""
        pass
