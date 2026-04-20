# -*- coding: utf-8 -*-
import os
import tkinter as tk
import customtkinter as ctk
from typing import Dict, Any, List, Optional, Callable
from src.ui.styles.theme import Theme
from src.ui.components.attachment_handler import AttachmentHandler

class ChatInputArea(ctk.CTkFrame):
    def __init__(
        self, 
        master, 
        project_dir: str,
        on_send: Callable[[], None],
        on_cancel: Callable[[], None],
        on_return_key: Callable[[tk.Event], Any],
        **kwargs
    ):
        super().__init__(master, fg_color=Theme.BG_DARKER, corner_radius=15, border_width=1, border_color=Theme.BG_DARK, **kwargs)
        self.project_dir = project_dir
        self.on_send = on_send
        self.on_cancel = on_cancel

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 1. Attachment Button Handler (Wrapped)
        self.attachment_handler = AttachmentHandler(self, self.project_dir)
        # Re-grid the attachment button inside our new layout
        self.attachment_handler.btn_attach.destroy() # We'll provide our own button
        
        self.btn_attach = ctk.CTkButton(
            self, 
            text="Attach", 
            width=72, height=40,
            fg_color=Theme.BG_DARKEST,
            hover_color=Theme.BG_DARK,
            command=self.attachment_handler.on_attach
        )
        self.btn_attach.grid(row=0, column=0, padx=10, pady=10, sticky="sw")

        # 2. Progress/Status Label (Overlayed)
        self.lbl_status = ctk.CTkLabel(
            self,
            text="Ready",
            font=("Segoe UI", 10, "italic"),
            text_color=Theme.TEXT_MUTED
        )
        self.lbl_status.grid(row=1, column=1, sticky="w", padx=10, pady=(0, 10))

        # 3. Modern Textbox
        self.txt_input = ctk.CTkTextbox(
            self,
            height=100,
            fg_color=Theme.BG_DARKEST,
            text_color=Theme.TEXT_MAIN,
            font=Theme.FONT_BODY,
            border_width=0,
            corner_radius=10
        )
        self.txt_input.grid(row=0, column=1, sticky="nsew", padx=5, pady=10)
        self.txt_input.bind("<Return>", on_return_key)

        # 4. Action Buttons
        self.btn_send = ctk.CTkButton(
            self,
            text="Send",
            width=80,
            fg_color=Theme.PRIMARY,
            hover_color=Theme.ACCENT,
            command=self.on_send
        )
        self.btn_send.grid(row=0, column=2, padx=(5, 10), pady=10, sticky="nsew")

    def toggle_send_button(self, stop: bool):
        if stop:
            self.btn_send.configure(text="Stop", fg_color=Theme.DANGER)
        else:
            self.btn_send.configure(text="Send", fg_color=Theme.PRIMARY)

    def get_query(self) -> str:
        return self.txt_input.get("1.0", "end-1c").strip()

    def clear_input(self):
        self.txt_input.delete("1.0", "end")
