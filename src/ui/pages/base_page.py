
import customtkinter as ctk

class BasePage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="#1e1e1e", corner_radius=0)
        self.controller = controller
        
    def on_show(self):
        """Called when this page is displayed."""
        pass
