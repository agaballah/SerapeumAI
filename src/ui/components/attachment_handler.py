# -*- coding: utf-8 -*-
import os
from tkinter import ttk, filedialog, messagebox
from typing import List
from src.utils.path_validator import validate_attachment_path, PathValidationError


class AttachmentHandler:
    def __init__(self, parent_frame: ttk.Frame, project_root: str):
        self.project_root = project_root
        self.attachments: List[str] = []

        # UI Components
        self.btn_attach = ttk.Button(
            parent_frame,
            text="📎",
            command=self.on_attach,
            width=3,
        )
        self.btn_attach.grid(row=0, column=0, padx=(0, 5), sticky="sw")

        self.lbl_attach = ttk.Label(
            parent_frame,
            text="",
            font=("Segoe UI", 8),
            foreground="gray",
        )
        self.lbl_attach.grid(row=1, column=1, sticky="w")

    def on_attach(self) -> None:
        """Handle attach button click."""
        files = filedialog.askopenfilenames(
            title="Attach Files",
            filetypes=[
                ("All Files", "*.*"),
                ("PDF", "*.pdf"),
                ("Word", "*.doc *.docx"),
                ("Excel", "*.xls *.xlsx"),
                ("Images", "*.png *.jpg *.jpeg"),
            ],
        )

        if files:
            valid_files = []
            for file_path in files:
                try:
                    validated_path = validate_attachment_path(
                        file_path,
                        project_root=self.project_root,
                        allow_external=True,
                    )
                    valid_files.append(validated_path)
                except PathValidationError as e:
                    messagebox.showerror(
                        "Invalid File",
                        f"Cannot attach {os.path.basename(file_path)}:\n{str(e)}",
                    )
                except Exception as e:
                    messagebox.showerror(
                        "Error",
                        f"Failed to validate {os.path.basename(file_path)}:\n{str(e)}",
                    )

            if valid_files:
                self.attachments.extend(valid_files)
                self._update_label()

    def clear(self) -> None:
        """Clear all attachments."""
        self.attachments.clear()
        self._update_label()

    def _update_label(self) -> None:
        """Update the attachment label text."""
        if self.attachments:
            count = len(self.attachments)
            self.lbl_attach.configure(text=f"📎 {count} file(s) attached")
        else:
            self.lbl_attach.configure(text="")

    def get_attachments(self) -> List[str]:
        return list(self.attachments)