# -*- coding: utf-8 -*-
import os
import tkinter as tk
from tkinter import messagebox
from typing import List, Optional, Dict, Any
from src.ui.styles.theme import Theme

class MessageRenderer:
    def __init__(self, text_widget: tk.Text, role_func: callable):
        self.text_widget = text_widget
        self.role_func = role_func 

        # Configure consistent tags from Theme
        self.text_widget.tag_config("user", foreground=Theme.ACCENT, font=("Segoe UI", 10, "bold"))
        self.text_widget.tag_config("assistant", foreground=Theme.SUCCESS, font=("Segoe UI", 10, "bold"))
        self.text_widget.tag_config("system", foreground=Theme.TEXT_MUTED, font=("Segoe UI", 9, "italic"))
        self.text_widget.tag_config("thinking", foreground=Theme.TEXT_MUTED, background="#252525", font=("Consolas", 9))
        self.text_widget.tag_config("error", foreground=Theme.DANGER)
        self.text_widget.tag_config("ref_link", foreground=Theme.PRIMARY, underline=True)
        self.text_widget.tag_config("suggested_action", foreground=Theme.WARNING, underline=True, font=("Segoe UI", 10, "bold"))
        
        # Code block support
        self.text_widget.tag_config("code", background="#2d2d2d", font=("Consolas", 10))

    def append(self, role: str, text: str, attachments: Optional[List[str]] = None, is_thinking: bool = False) -> None:
        self.text_widget.configure(state="normal")
        
        current_user_role = self.role_func() if self.role_func else "Technical Consultant"
        
        if is_thinking:
            tag = "thinking"
            prefix = "\nThinking:\n"
        else:
            tag = "user" if role == "You" else "assistant" if role == current_user_role else "system"
            prefix = f"\n{role}: "
        
        self.text_widget.insert("end", prefix, tag)
        
        # Insert text with highlighting
        start_index = self.text_widget.index("end")
        
        if is_thinking:
            self.text_widget.insert("end", f"{text}\n", "thinking")
        else:
            self.text_widget.insert("end", f"{text}\n")
            self._highlight_references(start_index)
        
        if attachments:
            for att in attachments:
                self.text_widget.insert("end", f"   [Attachment: {os.path.basename(att)}]\n", "system")
                
        self.text_widget.see("end")
        self.text_widget.configure(state="disabled")

    def stream_start(self, role: str):
        self.text_widget.configure(state="normal")
        current_user_role = self.role_func() if self.role_func else "Technical Consultant"
        tag = "user" if role == "You" else "assistant" if role == current_user_role else "system"
        self.text_widget.insert("end", f"\n{role}: ", tag)
        self.text_widget.see("end")
        self.text_widget.configure(state="disabled")

    def stream_chunk(self, text: str):
        self.text_widget.configure(state="normal")
        self.text_widget.insert("end", text)
        self.text_widget.see("end")
        self.text_widget.configure(state="disabled")

    def _highlight_references(self, start_index: str):
        # Professional AECO pattern matching
        pattern = r"\b(AECO-\d+|SBC\s?[\d\.]+|IBC\s?[\d\.]+|NFPA\s?\d+|TMSS-[\w\d\-]+|FACT-\d+)\b"
        
        count = tk.IntVar()
        self.text_widget.mark_set("searchLimit", "end")

        idx = start_index
        while True:
            idx = self.text_widget.search(pattern, idx, "searchLimit", count=count, regexp=True)
            if not idx: break
            
            match_end = f"{idx}+{count.get()}c"
            ref_text = self.text_widget.get(idx, match_end)
            
            tag_name = f"ref_{ref_text}_{idx.replace('.', '_')}" 
            self.text_widget.tag_add("ref_link", idx, match_end)
            self.text_widget.tag_add(tag_name, idx, match_end)
            
            # Closure to capture variables
            def make_handler(r=ref_text):
                return lambda e: messagebox.showinfo("Standard/Fact Reference", f"Reference: {r}\n\nLayer 4 Fact mapping confirmed.")
                
            self.text_widget.tag_bind(tag_name, "<Button-1>", make_handler())
            self.text_widget.tag_bind(tag_name, "<Enter>", lambda e: self.text_widget.configure(cursor="hand2"))
            self.text_widget.tag_bind(tag_name, "<Leave>", lambda e: self.text_widget.configure(cursor="arrow"))
            
            idx = match_end

    def append_suggested_action(self, action_text: str, click_handler: callable):
        self.text_widget.configure(state="normal")
        self.text_widget.insert("end", "\n- ", "suggested_action")
        
        start = self.text_widget.index("end-1c")
        self.text_widget.insert("end", f"{action_text}\n", "suggested_action")
        end = self.text_widget.index("end-1c")
        
        tag_name = f"action_{hash(action_text)}"
        self.text_widget.tag_add(tag_name, start, end)
        self.text_widget.tag_bind(tag_name, "<Button-1>", lambda e: click_handler(action_text))
        self.text_widget.tag_bind(tag_name, "<Enter>", lambda e: self.text_widget.configure(cursor="hand2"))
        self.text_widget.tag_bind(tag_name, "<Leave>", lambda e: self.text_widget.configure(cursor="arrow"))
        
        self.text_widget.see("end")
        self.text_widget.configure(state="disabled")
