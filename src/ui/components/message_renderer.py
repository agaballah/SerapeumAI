# -*- coding: utf-8 -*-
import os
import tkinter as tk
from tkinter import messagebox
from typing import List, Optional

class MessageRenderer:
    def __init__(self, text_widget: tk.Text, role_func: callable):
        self.text_widget = text_widget
        self.role_func = role_func # Function to get current user role name (for highlighting)

        # Configure tags
        self.text_widget.tag_config("user", foreground="#375a7f", font=("Segoe UI", 10, "bold"))
        self.text_widget.tag_config("assistant", foreground="#00bc8c", font=("Segoe UI", 10, "bold"))
        self.text_widget.tag_config("system", foreground="#adb5bd", font=("Segoe UI", 9, "italic"))
        self.text_widget.tag_config("error", foreground="#e74c3c")
        self.text_widget.tag_config("ref_link", foreground="#4da6ff", underline=True)
        self.text_widget.tag_config("suggested_action", foreground="#ffcc00", underline=True, font=("Segoe UI", 10, "bold"))

    def append(self, role: str, text: str, attachments: Optional[List[str]] = None) -> None:
        self.text_widget.configure(state="normal")
        
        current_user_role = self.role_func() if self.role_func else "Technical Consultant"
        tag = "user" if role == "You" else "assistant" if role == current_user_role else "system"
        
        self.text_widget.insert("end", f"\n{role}: ", tag)
        
        # Insert text with highlighting
        start_index = self.text_widget.index("end")
        self.text_widget.insert("end", f"{text}\n")
        
        self._highlight_references(start_index)
        
        if attachments:
            for att in attachments:
                self.text_widget.insert("end", f"   [Attachment: {os.path.basename(att)}]\n", "system")
                
        self.text_widget.see("end")
        self.text_widget.configure(state="disabled")

    def stream_start(self, role: str):
        """Start a streamed message (just the header)."""
        self.text_widget.configure(state="normal")
        current_user_role = self.role_func() if self.role_func else "Technical Consultant"
        tag = "user" if role == "You" else "assistant" if role == current_user_role else "system"
        self.text_widget.insert("end", f"\n{role}: ", tag)
        self.text_widget.see("end")
        # Keep state normal during streaming for performance? Or toggle? Toggle is safer.
        # But for high freq updates, keep normal until done? 
        # For now, locking it back is safer to prevent user edits.
        self.text_widget.configure(state="disabled")

    def stream_chunk(self, text: str):
        """Append a chunk to the current message."""
        self.text_widget.configure(state="normal")
        self.text_widget.insert("end", text)
        self.text_widget.see("end")
        self.text_widget.configure(state="disabled")

    def _highlight_references(self, start_index: str):
        # Highlight standard references (e.g., AECO-101, SBC 101.2, NFPA 13)
        pattern = r"\b(AECO-\d+|SBC\s?[\d\.]+|IBC\s?[\d\.]+|NFPA\s?\d+|TMSS-[\w\d\-]+)\b"
        
        count = tk.IntVar()
        self.text_widget.mark_set("matchStart", start_index)
        self.text_widget.mark_set("matchEnd", start_index)
        self.text_widget.mark_set("searchLimit", "end")

        while True:
            index = self.text_widget.search(pattern, "matchEnd", "searchLimit", count=count, regexp=True)
            if not index:
                break
            if count.get() == 0:
                break
            
            self.text_widget.mark_set("matchStart", index)
            self.text_widget.mark_set("matchEnd", f"{index}+{count.get()}c")
            
            # Add tag and binding
            ref_text = self.text_widget.get("matchStart", "matchEnd")
            tag_name = f"ref_{ref_text}_{index}" # Unique tag per instance
            self.text_widget.tag_add("ref_link", "matchStart", "matchEnd")
            self.text_widget.tag_add(tag_name, "matchStart", "matchEnd")
            
            # Bind click
            def show_clause(event, ref=ref_text):
                messagebox.showinfo("Standard Reference", f"Reference: {ref}\n\n(Clause lookup not yet connected to Standards DB)")
                
            self.text_widget.tag_bind(tag_name, "<Button-1>", show_clause)
            self.text_widget.tag_bind(tag_name, "<Enter>", lambda e: self.text_widget.configure(cursor="hand2"))
            self.text_widget.tag_bind(tag_name, "<Leave>", lambda e: self.text_widget.configure(cursor="arrow"))

    def append_suggested_action(self, action_text: str, click_handler: callable):
        """Append a clickable yellow suggestion."""
        self.text_widget.configure(state="normal")
        self.text_widget.insert("end", "\n➜ ", "suggested_action")
        
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
