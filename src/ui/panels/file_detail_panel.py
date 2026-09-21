import customtkinter as ctk
import logging
import os

from src.application.services.cad_evidence_presentation import (
    build_cad_evidence_view,
    render_cad_evidence_text,
)
from src.application.services.file_inspector_presentation import build_file_inspector_payload
from src.ui.styles.theme import Theme

logger = logging.getLogger(__name__)


class FileDetailPanel(ctk.CTkToplevel):
    def __init__(self, parent, db, file_id=None, file_path=None, project_id=None, page_no=None):
        super().__init__(parent, fg_color=Theme.BG_DARKEST)

        self.db = db
        self.file_path = file_path
        self.file_id = file_id
        self.page_no = page_no
        # Project id may be supplied explicitly; otherwise fall back to the
        # parent controller (if it exposes one). This preserves backward
        # compatibility with callers that do not pass project_id.
        if project_id is not None:
            self.project_id = project_id
        else:
            controller = getattr(parent, "controller", None)
            self.project_id = getattr(controller, "active_project_id", None) if controller is not None else None

        self.title("File Inspector")
        self.geometry("980x760")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        filename = os.path.basename(file_path) if file_path else "Unknown"
        page_context = f" — page {page_no}" if page_no else ""
        self.lbl_title = ctk.CTkLabel(
            self,
            text=f"File Inspector — {filename}{page_context}",
            font=Theme.FONT_H2,
            text_color=Theme.TEXT_MAIN,
            fg_color=Theme.BG_DARKEST,
        )
        self.lbl_title.grid(row=0, column=0, pady=(20, 0), padx=30, sticky="w")

        # Citation banner when navigated from a specific page
        if page_no:
            self.lbl_citation = ctk.CTkLabel(
                self,
                text=f"Cited location: page {page_no} of {filename}",
                font=Theme.FONT_BODY,
                text_color=Theme.WARNING,
                fg_color=Theme.BG_DARKER,
                corner_radius=6,
            )
            self.lbl_citation.grid(row=0, column=0, pady=(55, 0), padx=30, sticky="w")

        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)

        self.tab_review = self.tabview.add("Consolidated Review")
        self.tab_meta = self.tabview.add("Full Metadata")
        self.tab_raw = self.tabview.add("Raw Deterministic Extraction")
        self.tab_ai = self.tabview.add("AI Output Only")
        self.tab_cad = self.tabview.add("CAD Evidence")
        self.tabview.set("Consolidated Review")

        self.txt_review = self._make_textbox(self.tab_review)
        self.txt_meta = self._make_textbox(self.tab_meta)
        self.txt_raw = self._make_textbox(self.tab_raw)
        self.txt_ai = self._make_textbox(self.tab_ai)
        self.txt_cad = self._make_textbox(self.tab_cad)

        self._load_data()

    def _make_textbox(self, parent):
        txt = ctk.CTkTextbox(
            parent,
            font=Theme.FONT_MONO,
            text_color=Theme.TEXT_MAIN,
            fg_color=Theme.BG_DARKER,
            border_width=1,
            border_color=Theme.BG_DARK,
        )
        txt.pack(fill="both", expand=True, padx=5, pady=5)
        return txt

    def _load_data(self):
        try:
            payload = build_file_inspector_payload(self.db, file_id=self.file_id, file_path=self.file_path)
            self.lbl_title.configure(text=f"File Inspector — {payload.get('title', 'Unknown file')}")
            self._set_text(self.txt_review, payload.get("consolidated_review", "No consolidated review available."))
            self._set_text(self.txt_meta, payload.get("full_metadata", "No metadata available."))
            self._set_text(self.txt_raw, payload.get("raw_deterministic_extraction", "No deterministic extraction available."))
            self._set_text(self.txt_ai, payload.get("ai_output_only", "No AI output available."))
            cad_view = build_cad_evidence_view(
                self.db,
                file_id=self.file_id,
                file_path=self.file_path,
                project_id=self.project_id,
            )
            self._set_text(self.txt_cad, render_cad_evidence_text(cad_view))
        except Exception as e:
            logger.error(f"Error loading file inspector details: {e}", exc_info=True)
            msg = f"File Inspector failed to load details:\n{e}"
            for widget in (self.txt_review, self.txt_meta, self.txt_raw, self.txt_ai, self.txt_cad):
                self._set_text(widget, msg)

    @staticmethod
    def _set_text(widget, value: str) -> None:
        widget.delete("0.0", "end")
        widget.insert("0.0", value or "")
