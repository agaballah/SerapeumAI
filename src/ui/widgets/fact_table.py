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
from src.domain.facts.repository import FactRepository
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
        self._current_conflict_id = ""
        self._conflict_value_a_id = ""
        self._conflict_value_b_id = ""

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

        columns = ("review_title", "family", "source", "status", "conflict")
        self.frame_table = ctk.CTkFrame(self.frame_content, fg_color="transparent")
        self.frame_table.grid(row=0, column=0, sticky="nsew", padx=(0, 12), pady=0)
        self.frame_table.grid_columnconfigure(0, weight=1)
        self.frame_table.grid_rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(self.frame_table, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("review_title", text="Engineer-readable fact")
        self.tree.heading("family", text="Family")
        self.tree.heading("source", text="Source / evidence")
        self.tree.heading("status", text="Review State")
        self.tree.heading("conflict", text="⚠")
        self.tree.column("review_title", width=460)
        self.tree.column("family", width=130)
        self.tree.column("source", width=220)
        self.tree.column("status", width=150)
        self.tree.column("conflict", width=30)
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

        # Conflict detail frame (shown only when conflict_flag=1)
        self.frame_conflict = ctk.CTkFrame(self.frame_detail, fg_color="#2A1F1F", corner_radius=8, border_width=1, border_color="#FF6B35")
        self.frame_conflict.grid(row=7, column=0, sticky="ew", padx=18, pady=(0, 8))
        self.frame_conflict.grid_remove()  # hidden by default

        self.lbl_conflict_status = ctk.CTkLabel(
            self.frame_conflict, text="Conflict Status: OPEN",
            font=Theme.FONT_H3, text_color="#FF6B35",
        )
        self.lbl_conflict_status.grid(row=0, column=0, sticky="ew", padx=12, pady=(8, 4))

        self.lbl_conflict_value_a = ctk.CTkLabel(
            self.frame_conflict, text="Value A: —",
            font=Theme.FONT_BODY, text_color=Theme.TEXT_MAIN,
            justify="left", anchor="w", wraplength=380,
        )
        self.lbl_conflict_value_a.grid(row=1, column=0, sticky="ew", padx=12, pady=2)

        self.lbl_conflict_source_a = ctk.CTkLabel(
            self.frame_conflict, text="Source A: —",
            font=Theme.FONT_BODY, text_color=Theme.TEXT_MUTED,
            justify="left", anchor="w", wraplength=380,
        )
        self.lbl_conflict_source_a.grid(row=2, column=0, sticky="ew", padx=12, pady=2)

        self.lbl_conflict_value_b = ctk.CTkLabel(
            self.frame_conflict, text="Value B: —",
            font=Theme.FONT_BODY, text_color=Theme.TEXT_MAIN,
            justify="left", anchor="w", wraplength=380,
        )
        self.lbl_conflict_value_b.grid(row=3, column=0, sticky="ew", padx=12, pady=2)

        self.lbl_conflict_source_b = ctk.CTkLabel(
            self.frame_conflict, text="Source B: —",
            font=Theme.FONT_BODY, text_color=Theme.TEXT_MUTED,
            justify="left", anchor="w", wraplength=380,
        )
        self.lbl_conflict_source_b.grid(row=4, column=0, sticky="ew", padx=12, pady=2)

        self.frame_conflict_actions = ctk.CTkFrame(self.frame_conflict, fg_color="transparent")
        self.frame_conflict_actions.grid(row=5, column=0, sticky="ew", padx=12, pady=(4, 10))

        self.btn_conflict_reviewed = ctk.CTkButton(
            self.frame_conflict_actions, text="Mark Reviewed",
            width=110, height=28, fg_color=Theme.BG_DARK,
            command=self._on_conflict_mark_reviewed, state="disabled",
        )
        self.btn_conflict_reviewed.grid(row=0, column=0, sticky="w", padx=(0, 6), pady=0)

        self.btn_conflict_accept_a = ctk.CTkButton(
            self.frame_conflict_actions, text="Accept A",
            width=90, height=28, fg_color=Theme.SUCCESS,
            command=self._on_conflict_accept_a, state="disabled",
        )
        self.btn_conflict_accept_a.grid(row=0, column=1, sticky="w", padx=6, pady=0)

        self.btn_conflict_accept_b = ctk.CTkButton(
            self.frame_conflict_actions, text="Accept B",
            width=90, height=28, fg_color=Theme.SUCCESS,
            command=self._on_conflict_accept_b, state="disabled",
        )
        self.btn_conflict_accept_b.grid(row=0, column=2, sticky="w", padx=(6, 0), pady=0)

        self.frame_detail_actions = ctk.CTkFrame(self.frame_detail, fg_color="transparent")
        self.frame_detail_actions.grid(row=8, column=0, sticky="ew", padx=18, pady=(0, 18))
        self.frame_detail_actions.grid_columnconfigure(0, weight=1)

        self.btn_lineage = ctk.CTkButton(
            self.frame_detail_actions,
            text="Open Lineage / Evidence",
            width=180,
            command=self._open_lineage,
            state="disabled",
        )
        self.btn_lineage.grid(row=0, column=0, sticky="w", padx=(0, 8), pady=0)

        self.btn_open_source = ctk.CTkButton(
            self.frame_detail_actions,
            text="Open Source File",
            width=140,
            command=self._open_source_file,
            state="disabled",
            fg_color=Theme.BG_DARK,
        )
        self.btn_open_source.grid(row=1, column=0, sticky="w", padx=(0, 8), pady=(4, 0))

        self.btn_detail_approve = ctk.CTkButton(
            self.frame_detail_actions,
            text="Certify This Fact",
            fg_color=Theme.SUCCESS,
            hover_color="#1FAF55",
            width=150,
            command=self._on_approve,
            state="disabled",
        )
        self.btn_detail_approve.grid(row=0, column=1, sticky="e", padx=8, pady=0)

        self.btn_detail_reject = ctk.CTkButton(
            self.frame_detail_actions,
            text="Reject This Fact",
            fg_color=Theme.DANGER,
            hover_color=Theme.DANGER_RED,
            width=140,
            command=self._on_reject,
            state="disabled",
        )
        self.btn_detail_reject.grid(row=0, column=2, sticky="e", padx=(8, 0), pady=0)

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
            rowheight=54,
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
                         f.status, f.method_id, f.created_at, f.conflict_flag,
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
                  values=(row["title"], row["family_label"], row["source_label"], row["status_label"], row.get("conflict_flag", 0)),
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
            self._hide_conflict_ui()
            self.btn_lineage.configure(state="disabled")
            self.btn_open_source.configure(state="disabled")
            self.btn_detail_approve.configure(state="disabled")
            self.btn_detail_reject.configure(state="disabled")
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
            "Engineer decision\n\n"
            f"{row['review_question']}\n\n"
            "What this fact says\n\n"
            f"{row['meaning']}\n\n"
            "Evidence to check\n\n"
            f"{row['evidence_excerpt']}\n"
            f"{row['source_warning']}\n\n"
            "Before certifying\n\n"
            f"{row['certification_checklist']}"
        )
        self.lbl_action_meaning.configure(text=row["action_explanation"], text_color=Theme.TEXT_MAIN)
        self.btn_lineage.configure(state="normal")
        self.btn_open_source.configure(state="normal")

        # Conflict UI
        self._render_conflict_ui(row)

        status = row["status_code"]
        if status in ("CANDIDATE", "VALIDATED"):
            self.btn_approve.configure(state="normal")
            self.btn_detail_approve.configure(state="normal")
            self.btn_reject.configure(state="normal")
            self.btn_detail_reject.configure(state="normal")
        elif status == "HUMAN_CERTIFIED":
            self.btn_approve.configure(state="disabled")
            self.btn_detail_approve.configure(state="disabled")
            self.btn_reject.configure(state="normal")
            self.btn_detail_reject.configure(state="normal")
        else:
            self.btn_approve.configure(state="disabled")
            self.btn_detail_approve.configure(state="disabled")
            self.btn_reject.configure(state="disabled")
            self.btn_detail_reject.configure(state="disabled")

        self.lbl_selected.configure(
            text=f"Selected: {row['title']} | {row['status_label']} | {row['source_document']}",
            text_color=Theme.TEXT_MAIN,
        )

    def _hide_conflict_ui(self):
        self.frame_conflict.grid_remove()

    def _render_conflict_ui(self, row):
        """Show conflict detail panel when the selected fact has conflict_flag=1."""
        conflict_flag = row.get("conflict_flag", 0)
        if not conflict_flag or not self.db:
            self._hide_conflict_ui()
            return

        try:
            # Find the conflict for this fact
            conflicts = self.db.get_project_conflicts(
                row.get("project_id", ""), resolution_filter=None
            )
            # Find the conflict that includes this fact
            target_conflict = None
            for c in conflicts:
                values = c.get("values_parsed", [])
                if isinstance(values, str):
                    import json as _json
                    try:
                        values = _json.loads(values)
                    except Exception:
                        values = []
                for v in values:
                    if v.get("fact_id") == row.get("fact_id"):
                        target_conflict = c
                        break
                if target_conflict:
                    break

            if not target_conflict:
                self._hide_conflict_ui()
                return

            resolution = target_conflict.get("resolution", "UNRESOLVED")
            values = target_conflict.get("values_parsed", [])
            if isinstance(values, str):
                import json as _json
                try:
                    values = _json.loads(values)
                except Exception:
                    values = []

            # Set up labels
            val_a = values[0] if len(values) > 0 else {}
            val_b = values[1] if len(values) > 1 else {}

            self.lbl_conflict_status.configure(
                text=f"Conflict Status: {resolution}",
                text_color="#FF6B35" if resolution == "UNRESOLVED" else ("#F0A500" if resolution == "REVIEWED" else Theme.SUCCESS),
            )
            self.lbl_conflict_value_a.configure(text=f"Value A: {val_a.get('value', '—')}")
            self.lbl_conflict_source_a.configure(
                text=f"Source A: {val_a.get('source', val_a.get('method_id', 'unknown'))} "
                     f"(confidence: {val_a.get('confidence', 'n/a')})"
            )
            self.lbl_conflict_value_b.configure(text=f"Value B: {val_b.get('value', '—')}")
            self.lbl_conflict_source_b.configure(
                text=f"Source B: {val_b.get('source', val_b.get('method_id', 'unknown'))} "
                     f"(confidence: {val_b.get('confidence', 'n/a')})"
            )

            # Show the frame
            self.frame_conflict.grid()

            # Enable/disable buttons based on resolution state
            if resolution == "UNRESOLVED":
                self.btn_conflict_reviewed.configure(state="normal")
                self.btn_conflict_accept_a.configure(state="normal")
                self.btn_conflict_accept_b.configure(state="normal")
            elif resolution == "REVIEWED":
                self.btn_conflict_reviewed.configure(state="disabled", text="Reviewed ✓")
                self.btn_conflict_accept_a.configure(state="normal")
                self.btn_conflict_accept_b.configure(state="normal")
            else:  # RESOLVED
                self.btn_conflict_reviewed.configure(state="disabled", text="Reviewed ✓")
                self.btn_conflict_accept_a.configure(state="disabled")
                self.btn_conflict_accept_b.configure(state="disabled")
                # Show which was accepted
                resolved_by = target_conflict.get("resolved_by", "")
                self.lbl_conflict_status.configure(
                    text=f"Conflict Status: RESOLVED (by {resolved_by} or auto)",
                    text_color=Theme.SUCCESS,
                )

            # Store conflict_id for handler methods
            self._current_conflict_id = target_conflict.get("conflict_id", "")
            self._conflict_value_a_id = val_a.get("fact_id", "")
            self._conflict_value_b_id = val_b.get("fact_id", "")

        except Exception as e:
            logger.warning(f"Conflict UI render failed: {e}")
            self._hide_conflict_ui()

    def _on_conflict_mark_reviewed(self):
        """Transition conflict from OPEN to REVIEWED."""
        if not self._current_conflict_id or not self.db:
            return
        try:
            self.db.mark_conflict_reviewed(self._current_conflict_id, reviewer="engineer")
            self.load_facts(snapshot_id=self.snapshot_id)
            self.lbl_selected.configure(text="Conflict marked as REVIEWED", text_color=Theme.TEXT_MUTED)
        except Exception as e:
            logger.error(f"Mark reviewed failed: {e}")
            self.lbl_selected.configure(text=f"Mark reviewed failed: {e}", text_color=Theme.DANGER)

    def _on_conflict_accept_a(self):
        """Resolve conflict by accepting Value A."""
        self._resolve_conflict(self._conflict_value_a_id, "A")

    def _on_conflict_accept_b(self):
        """Resolve conflict by accepting Value B."""
        self._resolve_conflict(self._conflict_value_b_id, "B")

    def _resolve_conflict(self, accepted_fact_id: str, label: str):
        if not self._current_conflict_id or not accepted_fact_id or not self.db:
            return
        try:
            self.db.resolve_conflict(
                self._current_conflict_id,
                accepted_fact_id=accepted_fact_id,
                resolver=f"engineer:accepted_{label}",
            )
            self.load_facts(snapshot_id=self.snapshot_id)
            self.lbl_selected.configure(
                text=f"Conflict resolved — accepted Value {label}. Original evidence preserved.",
                text_color=Theme.SUCCESS,
            )
        except Exception as e:
            logger.error(f"Conflict resolution failed: {e}")
            self.lbl_selected.configure(text=f"Resolution failed: {e}", text_color=Theme.DANGER)

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
            repo = FactRepository(self.db)
            updated = repo.update_fact_status(self.selected_fact_id, new_status)
            if not updated:
                self.lbl_selected.configure(text="Update Failed: selected fact was not found", text_color=Theme.DANGER)
                return

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

    def _open_source_file(self):
        """Open the source document for the selected fact.

        Uses the source_path stored in the fact's provenance (fact_inputs -> file_versions).
        Opens the file with the OS default application. Does NOT navigate to a specific
        page/region — displays location info as text context.
        Platform-specific: uses os.startfile on Windows, equivalent on others.
        """
        if not self.selected_fact_id or not self.db:
            return
        try:
            row = self.db.execute(
                """
                SELECT fv.source_path, fi.location_json
                FROM fact_inputs fi
                LEFT JOIN file_versions fv ON fv.file_version_id = fi.file_version_id
                WHERE fi.fact_id = ?
                LIMIT 1
                """,
                (self.selected_fact_id,),
            ).fetchone()
            if not row or not row[0]:
                self.lbl_selected.configure(
                    text="Source file path not available for this fact.",
                    text_color=Theme.TEXT_MUTED,
                )
                return

            source_path = row[0]
            location_json = row[1]

            # Build location context string
            loc_context = ""
            if location_json:
                import json as _json
                try:
                    loc = _json.loads(location_json)
                    parts = []
                    if loc.get("page"):
                        parts.append(f"page {loc['page']}")
                    if loc.get("bbox"):
                        b = loc["bbox"]
                        parts.append(f"region ({b[0]:.0f},{b[1]:.0f})-({b[2]:.0f},{b[3]:.0f})")
                    if loc.get("row"):
                        parts.append(f"row {loc['row']}")
                    if loc.get("handle"):
                        parts.append(f"handle {loc['handle']}")
                    if parts:
                        loc_context = f" [at: {', '.join(parts)}]"
                except Exception:
                    pass

            # Open file with OS default handler
            import os as _os
            import sys as _sys
            file_exists = _os.path.isfile(source_path)
            if not file_exists:
                self.lbl_selected.configure(
                    text=f"Source file not found: {source_path}",
                    text_color=Theme.WARNING,
                )
                return

            try:
                if _sys.platform == "win32":
                    _os.startfile(source_path)
                elif _sys.platform == "darwin":
                    _os.system(f'open "{source_path}"')
                else:
                    _os.system(f'xdg-open "{source_path}"')
            except Exception as open_err:
                self.lbl_selected.configure(
                    text=f"Could not open file ({open_err}). Path: {source_path}",
                    text_color=Theme.WARNING,
                )
                return

            self.lbl_selected.configure(
                text=f"Opened: {_os.path.basename(source_path)}{loc_context}",
                text_color=Theme.TEXT_MAIN,
            )

        except Exception as e:
            logger.error(f"Open source file failed: {e}")
            self.lbl_selected.configure(text=f"Open source failed: {e}", text_color=Theme.DANGER)

    def _on_double_click(self, _event):
        self._open_lineage()
