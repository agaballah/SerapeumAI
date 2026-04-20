# -*- coding: utf-8 -*-
import logging
import customtkinter as ctk
from tkinter import ttk
import tkinter as tk

from src.application.services.fact_review_presentation import (
    build_fact_review_view,
    build_filter_options,
    filter_fact_rows,
)
from src.ui.styles.theme import Theme

logger = logging.getLogger(__name__)


class FactTable(ctk.CTkFrame):
    """
    Mounted fact review workspace.
    Preserves the table/grid while making the selected fact understandable enough
    for meaningful human review and certification.
    """

    def __init__(self, parent, db_manager):
        super().__init__(
            parent,
            fg_color=Theme.BG_DARKER,
            corner_radius=12,
            border_width=1,
            border_color=Theme.BG_DARK,
        )
        self.db = db_manager
        self.snapshot_id = None
        self.page_size = 150
        self.offset = 0
        self.all_rows = []
        self.filtered_rows = []
        self.row_by_fact_id = {}
        self.selected_fact_id = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._setup_tree_style()
        self._build_filters()
        self._build_content_area()
        self._build_actions()

    def _build_filters(self):
        self.frame_filters = ctk.CTkFrame(self, fg_color=Theme.BG_DARKEST, corner_radius=10)
        self.frame_filters.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        for col in range(8):
            self.frame_filters.grid_columnconfigure(col, weight=1 if col in (1, 3, 5, 7) else 0)

        self._add_filter_label(0, "Family")
        self.cmb_family = self._make_filter_combo(1, ["All families"])

        self._add_filter_label(2, "Fact Type")
        self.cmb_type = self._make_filter_combo(3, ["All fact types"])

        self._add_filter_label(4, "Review State")
        self.cmb_state = self._make_filter_combo(5, ["All states"])

        self._add_filter_label(6, "Source")
        self.cmb_source = self._make_filter_combo(7, ["All sources"])

        self.btn_clear_filters = ctk.CTkButton(
            self.frame_filters,
            text="Clear Filters",
            width=120,
            command=self._clear_filters,
        )
        self.btn_clear_filters.grid(row=1, column=7, sticky="e", padx=10, pady=(8, 10))

    def _add_filter_label(self, column, text):
        ctk.CTkLabel(
            self.frame_filters,
            text=text,
            font=Theme.FONT_BODY,
            text_color=Theme.TEXT_MUTED,
        ).grid(row=0, column=column, sticky="w", padx=10, pady=(10, 4))

    def _make_filter_combo(self, column, values):
        combo = ctk.CTkComboBox(
            self.frame_filters,
            values=values,
            command=lambda _value: self._apply_filters(),
            state="readonly",
        )
        combo.grid(row=1, column=column, sticky="ew", padx=10, pady=(8, 10))
        combo.set(values[0])
        return combo

    def _build_content_area(self):
        self.frame_content = ctk.CTkFrame(self, fg_color=Theme.BG_DARKER)
        self.frame_content.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        self.frame_content.grid_columnconfigure(0, weight=3)
        self.frame_content.grid_columnconfigure(1, weight=2)
        self.frame_content.grid_rowconfigure(0, weight=1)

        columns = ("review_title", "family", "source", "status")
        self.frame_table = ctk.CTkFrame(self.frame_content, fg_color="transparent")
        self.frame_table.grid(row=0, column=0, sticky="nsew", padx=(0, 12), pady=0)
        self.frame_table.grid_columnconfigure(0, weight=1)
        self.frame_table.grid_rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(self.frame_table, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("review_title", text="Fact")
        self.tree.heading("family", text="Family")
        self.tree.heading("source", text="Source")
        self.tree.heading("status", text="Review State")
        self.tree.column("review_title", width=360)
        self.tree.column("family", width=130)
        self.tree.column("source", width=220)
        self.tree.column("status", width=150)
        self.tree.grid(row=0, column=0, sticky="nsew")

        self.scrollbar = ctk.CTkScrollbar(self.frame_table, command=self.tree.yview)
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=self.scrollbar.set)

        self.frame_detail = ctk.CTkFrame(self.frame_content, fg_color=Theme.BG_DARKEST, corner_radius=12)
        self.frame_detail.grid(row=0, column=1, sticky="nsew")
        self.frame_detail.grid_columnconfigure(0, weight=1)
        self.frame_detail.grid_rowconfigure(5, weight=1)

        self.lbl_detail_heading = ctk.CTkLabel(
            self.frame_detail,
            text="Fact Review Detail",
            font=Theme.FONT_H3,
            text_color=Theme.TEXT_MAIN,
        )
        self.lbl_detail_heading.grid(row=0, column=0, sticky="w", padx=18, pady=(18, 6))

        self.lbl_detail_title = ctk.CTkLabel(
            self.frame_detail,
            text="Select a fact to review",
            font=Theme.FONT_H2,
            text_color=Theme.TEXT_MAIN,
            anchor="w",
            justify="left",
            wraplength=420,
        )
        self.lbl_detail_title.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 8))

        self.lbl_detail_meta = ctk.CTkLabel(
            self.frame_detail,
            text="Readable meaning, provenance, and review state will appear here.",
            font=Theme.FONT_BODY,
            text_color=Theme.TEXT_MUTED,
            justify="left",
            anchor="w",
            wraplength=420,
        )
        self.lbl_detail_meta.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 10))

        self.lbl_status_box = ctk.CTkLabel(
            self.frame_detail,
            text="Review State: No fact selected",
            font=Theme.FONT_BODY,
            text_color=Theme.TEXT_MAIN,
            justify="left",
            anchor="w",
            wraplength=420,
        )
        self.lbl_status_box.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 8))

        self.lbl_source_box = ctk.CTkLabel(
            self.frame_detail,
            text="Source: Not available",
            font=Theme.FONT_BODY,
            text_color=Theme.TEXT_MAIN,
            justify="left",
            anchor="w",
            wraplength=420,
        )
        self.lbl_source_box.grid(row=4, column=0, sticky="ew", padx=18, pady=(0, 8))

        self.txt_meaning = ctk.CTkTextbox(self.frame_detail, fg_color=Theme.BG_DARK, text_color=Theme.TEXT_OFFWHITE)
        self.txt_meaning.grid(row=5, column=0, sticky="nsew", padx=18, pady=(0, 10))
        self.txt_meaning.insert("1.0", "Select a fact to see a plain-language explanation and review guidance.")
        self.txt_meaning.configure(state="disabled")

        self.lbl_action_meaning = ctk.CTkLabel(
            self.frame_detail,
            text="Certify and Reject will explain their effect for the selected fact.",
            font=Theme.FONT_BODY,
            text_color=Theme.TEXT_MUTED,
            justify="left",
            anchor="w",
            wraplength=420,
        )
        self.lbl_action_meaning.grid(row=6, column=0, sticky="ew", padx=18, pady=(0, 8))

        self.btn_lineage = ctk.CTkButton(
            self.frame_detail,
            text="Open Lineage / Evidence",
            width=190,
            command=self._open_lineage,
            state="disabled",
        )
        self.btn_lineage.grid(row=7, column=0, sticky="w", padx=18, pady=(0, 18))

        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-1>", self._on_double_click)

    def _build_actions(self):
        self.frame_actions = ctk.CTkFrame(self, fg_color=Theme.BG_DARKEST, height=80, corner_radius=0)
        self.frame_actions.grid(row=2, column=0, sticky="ew")

        self.lbl_selected = ctk.CTkLabel(
            self.frame_actions,
            text="Select a fact to review its meaning, provenance, and approval state.",
            font=Theme.FONT_BODY,
            text_color=Theme.TEXT_MUTED,
        )
        self.lbl_selected.pack(side="left", padx=30, pady=20)

        self.btn_reject = ctk.CTkButton(
            self.frame_actions,
            text="Reject Selected Fact",
            fg_color=Theme.DANGER,
            hover_color=Theme.DANGER_RED,
            width=170,
            command=self._on_reject,
            state="disabled",
        )
        self.btn_reject.pack(side="right", padx=10, pady=20)

        self.btn_approve = ctk.CTkButton(
            self.frame_actions,
            text="Certify Selected Fact",
            fg_color=Theme.SUCCESS,
            hover_color="#1FAF55",
            width=190,
            command=self._on_approve,
            state="disabled",
        )
        self.btn_approve.pack(side="right", padx=10, pady=20)

    def _setup_tree_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Treeview",
            background=Theme.BG_DARKEST,
            foreground=Theme.TEXT_MAIN,
            fieldbackground=Theme.BG_DARKEST,
            borderwidth=0,
            font=Theme.FONT_BODY,
            rowheight=42,
        )
        style.map("Treeview", background=[("selected", Theme.PRIMARY)])
        style.configure(
            "Treeview.Heading",
            background=Theme.BG_DARK,
            foreground=Theme.TEXT_MAIN,
            relief="flat",
            padding=10,
            font=Theme.FONT_H3,
        )

    def load_facts(self, snapshot_id=None):
        if not self.db:
            return
        self.snapshot_id = snapshot_id
        self.offset = 0

        try:
            params = []
            query = """
                SELECT f.fact_id, f.fact_type, f.subject_id,
                       f.value_text, f.value_num, f.value_json, f.unit,
                       f.status, f.method_id, f.created_at,
                       (
                           SELECT fv.source_path
                           FROM fact_inputs fi
                           LEFT JOIN file_versions fv ON fv.file_version_id = fi.file_version_id
                           WHERE fi.fact_id = f.fact_id
                           LIMIT 1
                       ) AS source_path,
                       (
                           SELECT fi.location_json
                           FROM fact_inputs fi
                           WHERE fi.fact_id = f.fact_id
                           LIMIT 1
                       ) AS location_json,
                       (
                           SELECT fi.input_kind
                           FROM fact_inputs fi
                           WHERE fi.fact_id = f.fact_id
                           LIMIT 1
                       ) AS input_kind
                FROM facts f
            """
            if snapshot_id:
                query += " WHERE f.fact_id IN (SELECT fact_id FROM fact_snapshot_registry WHERE snapshot_id = ?)"
                params.append(snapshot_id)
            query += " ORDER BY f.created_at DESC LIMIT ? OFFSET ?"
            params.extend([self.page_size, self.offset])
            rows = [dict(r) for r in self.db.execute(query, tuple(params)).fetchall()]
            self.offset += len(rows)
            self.all_rows = rows
            self._refresh_filter_options()
            self._apply_filters()
        except Exception as e:
            logger.error(f"Facts Load Error: {e}")

    def _refresh_filter_options(self):
        options = build_filter_options(self.all_rows)
        self._set_combo_values(self.cmb_family, options["families"])
        self._set_combo_values(self.cmb_type, options["types"])
        self._set_combo_values(self.cmb_state, options["states"])
        self._set_combo_values(self.cmb_source, options["sources"])

    def _set_combo_values(self, combo, values):
        current = combo.get() if hasattr(combo, "get") else values[0]
        combo.configure(values=values)
        combo.set(current if current in values else values[0])

    def _clear_filters(self):
        self.cmb_family.set("All families")
        self.cmb_type.set("All fact types")
        self.cmb_state.set("All states")
        self.cmb_source.set("All sources")
        self._apply_filters()

    def _apply_filters(self):
        family = self.cmb_family.get()
        fact_type = self.cmb_type.get()
        state = self.cmb_state.get()
        source = self.cmb_source.get()
        self.filtered_rows = filter_fact_rows(
            self.all_rows,
            family_filter=family,
            type_filter=fact_type,
            status_filter=state,
            source_filter=source,
        )
        self.row_by_fact_id = {row["fact_id"]: row for row in self.filtered_rows}
        self._reload_tree()

    def _reload_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for row in self.filtered_rows:
            self.tree.insert(
                "",
                "end",
                iid=row["fact_id"],
                values=(row["title"], row["family_label"], row["source_label"], row["status_label"]),
            )

        if self.filtered_rows:
            first = self.filtered_rows[0]["fact_id"]
            self.tree.selection_set(first)
            self._select_fact(first)
        else:
            self.selected_fact_id = None
            self._render_detail(None)
            self.lbl_selected.configure(text="No facts match the current review filters.", text_color=Theme.TEXT_MUTED)

    def _on_select(self, _event):
        item = self.tree.selection()
        if not item:
            return
        self._select_fact(item[0])

    def _select_fact(self, fact_id: str):
        row = self.row_by_fact_id.get(fact_id)
        self.selected_fact_id = fact_id if row else None
        self._render_detail(row)

    def _render_detail(self, row):
        if not row:
            self.lbl_detail_title.configure(text="Select a fact to review")
            self.lbl_detail_meta.configure(text="Readable meaning, provenance, and review state will appear here.")
            self.lbl_status_box.configure(text="Review State: No fact selected")
            self.lbl_source_box.configure(text="Source: Not available")
            self._set_textbox("Select a fact to see a plain-language explanation and review guidance.")
            self.lbl_action_meaning.configure(text="Certify and Reject will explain their effect for the selected fact.", text_color=Theme.TEXT_MUTED)
            self.btn_lineage.configure(state="disabled")
            self.btn_approve.configure(state="disabled")
            self.btn_reject.configure(state="disabled")
            return

        self.lbl_detail_title.configure(text=row["title"])
        self.lbl_detail_meta.configure(
            text=(
                f"Meaning: {row['meaning']}\n"
                f"Fact family: {row['family_label']} | Internal type: {row['type_code']}"
            )
        )
        self.lbl_status_box.configure(
            text=f"Review State: {row['status_label']}\n{row['status_explanation']}"
        )
        self.lbl_source_box.configure(
            text=(
                f"Source: {row['source_label']}\n"
                f"Origin: {row['origin_label']}\n"
                f"Location: {row['location_label']}"
            )
        )
        self._set_textbox(
            f"Readable meaning\n\n{row['meaning']}\n\n"
            f"Recorded value\n\n{row['value_summary']}"
        )
        self.lbl_action_meaning.configure(text=row["action_explanation"], text_color=Theme.TEXT_MAIN)
        self.btn_lineage.configure(state="normal")

        status = row["status_code"]
        if status in ("CANDIDATE", "VALIDATED"):
            self.btn_approve.configure(state="normal")
            self.btn_reject.configure(state="normal")
        elif status == "HUMAN_CERTIFIED":
            self.btn_approve.configure(state="disabled")
            self.btn_reject.configure(state="normal")
        else:
            self.btn_approve.configure(state="disabled")
            self.btn_reject.configure(state="disabled")

        self.lbl_selected.configure(
            text=f"Selected: {row['title']} | {row['status_label']} | {row['source_document']}",
            text_color=Theme.TEXT_MAIN,
        )

    def _set_textbox(self, text: str):
        self.txt_meaning.configure(state="normal")
        self.txt_meaning.delete("1.0", "end")
        self.txt_meaning.insert("1.0", text)
        self.txt_meaning.configure(state="disabled")

    def _on_approve(self):
        self._update_status("HUMAN_CERTIFIED")

    def _on_reject(self):
        self._update_status("REJECTED")

    def _update_status(self, new_status):
        if not self.selected_fact_id or not self.db:
            return

        try:
            self.db.execute(
                "UPDATE facts SET status = ?, updated_at = ? WHERE fact_id = ?",
                (new_status, self.db._ts(), self.selected_fact_id),
            )
            self.db.commit()
            logger.info("Fact %s status updated to %s", self.selected_fact_id, new_status)
            self.load_facts(snapshot_id=self.snapshot_id)
            if self.selected_fact_id in self.row_by_fact_id:
                self.tree.selection_set(self.selected_fact_id)
                self._select_fact(self.selected_fact_id)
            self.lbl_selected.configure(text=f"Successfully updated to {new_status}", text_color=Theme.SUCCESS)
        except Exception as e:
            logger.error(f"Fact Status Update Failed: {e}")
            self.lbl_selected.configure(text=f"Update Failed: {e}", text_color=Theme.DANGER)

    def _open_lineage(self):
        if not self.selected_fact_id:
            return
        from src.ui.widgets.fact_lineage_popup import FactLineagePopup
        FactLineagePopup(self, self.db, self.selected_fact_id)

    def _on_double_click(self, _event):
        self._open_lineage()
