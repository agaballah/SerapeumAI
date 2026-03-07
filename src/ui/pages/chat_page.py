import customtkinter as ctk
import tkinter as tk
import re
from src.ui.pages.base_page import BasePage
from src.ui.widgets.fact_lineage_popup import FactLineagePopup
from src.ui.styles.theme import Theme

class ChatPage(BasePage):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Chat History
        self.scroll_chat = ctk.CTkScrollableFrame(self, fg_color=Theme.BG_DARKEST, bg_color=Theme.BG_DARKEST)
        self.scroll_chat.grid(row=0, column=0, sticky="nsew", padx=20, pady=(20, 0))
        
        self.chat_container = self.scroll_chat
        
        # Input Area
        self.frame_input = ctk.CTkFrame(self, fg_color=Theme.BG_DARKEST)
        self.frame_input.grid(row=1, column=0, sticky="ew", padx=20, pady=20)
        
        self.entry_msg = ctk.CTkEntry(self.frame_input, placeholder_text="Ask about the project...", 
                                    fg_color=Theme.BG_DARKER, text_color=Theme.TEXT_MAIN,
                                    border_color=Theme.BG_DARK)
        self.entry_msg.pack(side="left", fill="x", expand=True, padx=10, pady=10)
        self.entry_msg.bind("<Return>", self.send_message)
        
        self.btn_send = ctk.CTkButton(self.frame_input, text="Send", 
                                    fg_color=Theme.PRIMARY, hover_color=Theme.ACCENT,
                                    command=self.send_message)
        self.btn_send.pack(side="right", padx=10, pady=10)
        
        self.add_message("System", "Welcome to Serapeum Expert Chat. Ask about schedule, specs, or drawings.")

    def send_message(self, event=None):
        msg = self.entry_msg.get()
        if not msg: return
        
        self.add_message("User", msg)
        self.entry_msg.delete(0, "end")
        
        # Real v02 Orchestration
        if self.controller.orchestrator:
            def _ask():
                try:
                    res = self.controller.orchestrator.answer_question(query=msg)
                    ans = res.get("answer", "No response from brain.")
                    self.after(0, lambda: self.add_message("Serapeum", ans))
                except Exception as e:
                    self.after(0, lambda: self.add_message("System", f"Error: {str(e)}"))
            
            import threading
            threading.Thread(target=_ask, daemon=True).start()
        else:
            self.add_message("System", "Expert Brain not initialized for this project.")

    def add_message(self, sender, text):
        # Container
        frame = ctk.CTkFrame(self.chat_container, fg_color=Theme.BG_DARKEST)
        frame.pack(fill="x", pady=10)
        
        # Message Bubble
        bubble_bg = "#2b2b2b" if sender=="Serapeum" else "#333333"
        if sender == "System": bubble_bg = "#121212"
        
        bubble = ctk.CTkFrame(frame, fg_color=bubble_bg, bg_color=Theme.BG_DARKEST, corner_radius=10, border_width=1, border_color="#3a3a3a")
        bubble.pack(anchor="w", fill="x", padx=10)
        
        lbl_text = tk.Label(bubble, text=text, justify="left", wraplength=800, 
                            fg=Theme.TEXT_MAIN, bg=bubble_bg, font=Theme.FONT_BODY)
        lbl_text.pack(padx=15, pady=10, anchor="w")
        
        # Extract Citations
        citations = re.findall(r"\[Fact:(\w+)\]", text)
        if citations:
            src_frame = ctk.CTkFrame(frame, fg_color=Theme.BG_DARKEST)
            src_frame.pack(anchor="w", pady=5)
            
            tk.Label(src_frame, text="Sources:", font=("Arial", 10, "bold"), 
                     fg=Theme.TEXT_MUTED, bg=Theme.BG_DARKEST).pack(side="left", padx=(0,5))
          
            for fact_id in citations:
                btn = ctk.CTkButton(src_frame, text=f"Fact {fact_id}", 
                                  height=20, width=80, 
                                  font=("Arial", 10),
                                  command=lambda f=fact_id: self.open_citation(f))
                btn.pack(side="left", padx=2)
                
        # Feedback Buttons (Thumbs Up/Down)
        if sender == "Serapeum":
            fb_frame = ctk.CTkFrame(frame, fg_color=Theme.BG_DARKEST)
            fb_frame.pack(anchor="w", pady=(2, 0))
            
            btn_up = ctk.CTkButton(fb_frame, text="👍", width=30, height=20, 
                                 fg_color=Theme.BG_DARK, hover_color="#3a3a3a", command=lambda: print("Thumbs Up"))
            btn_up.pack(side="left")
            
            btn_down = ctk.CTkButton(fb_frame, text="👎", width=30, height=20, 
                                   fg_color=Theme.BG_DARK, hover_color="#3a3a3a", command=lambda: print("Thumbs Down"))
            btn_down.pack(side="left")
                
    def open_citation(self, fact_id):
        if self.controller.db:
             FactLineagePopup(self, self.controller.db, fact_id)
        else:
             print(f"Open Fact {fact_id}")
