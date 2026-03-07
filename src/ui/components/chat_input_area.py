# -*- coding: utf-8 -*-
import tkinter as tk
from typing import Dict, Any, List, Optional, Callable

from tkinter import ttk
ScrolledText = tk.Text

from src.ui.components.attachment_handler import AttachmentHandler

class ChatInputArea(ttk.Frame):
    def __init__(
        self, 
        master, 
        project_dir: str,
        on_send: Callable[[], None],
        on_cancel: Callable[[], None],
        on_return_key: Callable[[tk.Event], Any],
        **kwargs
    ):
        super().__init__(master, **kwargs)
        self.project_dir = project_dir
        self.on_send = on_send
        self.on_cancel = on_cancel

        self.columnconfigure(1, weight=1)

        # Attachment Handler
        self.attachment_handler = AttachmentHandler(self, self.project_dir)

        # Input Text
        self.txt_input = ScrolledText(self, height=4)
        self.txt_input.grid(row=0, column=1, sticky="ew")
        self.txt_input.bind("<Return>", on_return_key)

        # Buttons
        self.btn_send = ttk.Button(
            self,
            text="Send",
            command=self.on_send
        )
        self.btn_send.grid(row=0, column=2, padx=(5, 0), sticky="sw")

        self.btn_cancel = ttk.Button(
            self,
            text="Cancel",
            command=self.on_cancel
        )
        self.btn_cancel.grid(row=0, column=3, padx=(5, 0), sticky="sw")

        # Status Label
        self.lbl_status = ttk.Label(
            self,
            text="Ready",
            font=("Segoe UI", 8, "italic"),
            foreground="gray"
        )
        self.lbl_status.grid(row=1, column=2, columnspan=2, sticky="e", padx=(0, 5))

    def get_query(self) -> str:
        return self.txt_input.get("1.0", "end-1c").strip()

    def clear_input(self):
        self.txt_input.delete("1.0", "end")

    def set_status(self, text: str):
        self.lbl_status.configure(text=text)

    def toggle_send_button(self, stop: bool):
        if stop:
            self.btn_send.configure(text="Stop")
        else:
            self.btn_send.configure(text="Send")

    def get_attachments(self) -> List[str]:
        return self.attachment_handler.get_attachments()

    def clear_attachments(self):
        self.attachment_handler.clear()
