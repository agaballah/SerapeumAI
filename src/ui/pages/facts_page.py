import customtkinter as ctk
import tkinter as tk
from src.ui.pages.base_page import BasePage
from src.ui.widgets.fact_table import FactTable
from src.ui.styles.theme import Theme

class FactsPage(BasePage):
    REFRESH_MS = 2500

    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        self._refresh_after_id = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.scroll_body = ctk.CTkScrollableFrame(self, fg_color=Theme.BG_DARKEST, bg_color=Theme.BG_DARKEST)
        self.scroll_body.grid(row=0, column=0, sticky="nsew")
        self.scroll_body.grid_columnconfigure(0, weight=1)

        # Header Section
        self.frame_header = ctk.CTkFrame(self.scroll_body, fg_color=Theme.BG_DARKEST)
        self.frame_header.grid(row=0, column=0, pady=(40, 20), padx=40, sticky="ew")

        self.lbl_title = tk.Label(
            self.frame_header,
            text="Project Facts",
            font=Theme.FONT_H1,
            fg=Theme.TEXT_MAIN,
            bg=Theme.BG_DARKEST,
        )
        self.lbl_title.pack(side="left")

        self.lbl_scope = tk.Label(
            self.frame_header,
            text="Review stored facts for the selected project state. Select a fact to inspect its meaning, provenance, and approval state.",
            font=Theme.FONT_BODY,
            fg=Theme.TEXT_MUTED,
            bg=Theme.BG_DARKEST,
            justify="left",
        )
        self.lbl_scope.pack(side="left", padx=(16, 0))

        # Fact Table
        self.tbl_facts = FactTable(self.scroll_body, controller.db if controller else None)
        self.tbl_facts.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)

    def on_show(self):
        self._refresh_visible_facts()
        self._schedule_refresh()

    def _get_snapshot_context(self):
        snapshot_id = None
        snapshot_label = None
        if self.controller and hasattr(self.controller, "get_selected_snapshot_id"):
            snapshot_id = self.controller.get_selected_snapshot_id()
        if self.controller and hasattr(self.controller, "get_selected_snapshot_label"):
            snapshot_label = self.controller.get_selected_snapshot_label()
        return snapshot_id, snapshot_label

    def _refresh_visible_facts(self):
        if not self.controller or not self.controller.db:
            return

        self.tbl_facts.db = self.controller.db
        snapshot_id, snapshot_label = self._get_snapshot_context()

        if snapshot_label:
            self.lbl_scope.configure(text=f"Review facts stored for: {snapshot_label}. Select a fact to inspect meaning, provenance, and approval state.")
        else:
            self.lbl_scope.configure(text="Review stored facts for the selected project state. Select a fact to inspect its meaning, provenance, and approval state.")

        self.tbl_facts.load_facts(snapshot_id=snapshot_id)

    def _schedule_refresh(self):
        if self._refresh_after_id is not None:
            try:
                self.after_cancel(self._refresh_after_id)
            except Exception:
                pass
        self._refresh_after_id = self.safe_ui_after(self.REFRESH_MS, self._poll_for_new_facts)

    def on_app_close(self):
        super().on_app_close()
        if self._refresh_after_id is not None:
            try:
                self.after_cancel(self._refresh_after_id)
            except Exception:
                pass
            self._refresh_after_id = None

    def _poll_for_new_facts(self):
        self._refresh_after_id = None
        if not self.winfo_exists():
            return

        try:
            is_visible = self.winfo_ismapped() and self.winfo_viewable()
        except Exception:
            is_visible = False

        if not is_visible:
            return

        self._refresh_visible_facts()
        self._schedule_refresh()
