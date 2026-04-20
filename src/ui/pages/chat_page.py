import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.application.services.mounted_chat_runtime import run_mounted_chat_query
from src.ui.pages.base_page import BasePage
from src.ui.styles.theme import Theme
from src.ui.widgets.fact_lineage_popup import FactLineagePopup

LANE_TITLES = ("Trusted Facts", "Extracted Evidence", "Linked Support", "AI-Generated Synthesis")

class ChatPage(BasePage):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.attached_files: List[str] = []
        self.feedback_events: List[Dict[str, Any]] = []
        self._last_user_query = ""
        self._chat_session_token = 0

        self.scroll_chat = ctk.CTkScrollableFrame(
            self,
            fg_color=Theme.BG_DARKEST,
            bg_color=Theme.BG_DARKEST,
        )
        self.scroll_chat.grid(row=0, column=0, sticky="nsew", padx=20, pady=(20, 0))
        self.chat_container = self.scroll_chat

        self.frame_input = ctk.CTkFrame(self, fg_color=Theme.BG_DARKEST)
        self.frame_input.grid(row=1, column=0, sticky="ew", padx=20, pady=20)
        self.frame_input.grid_columnconfigure(1, weight=1)

        self.btn_attach = ctk.CTkButton(
            self.frame_input,
            text="Attach",
            width=90,
            fg_color=Theme.BG_DARK,
            hover_color=Theme.BG_DARKER,
            command=self.attach_files,
        )
        self.btn_attach.grid(row=0, column=0, padx=(10, 8), pady=10, sticky="w")

        self.entry_msg = ctk.CTkEntry(
            self.frame_input,
            placeholder_text="Ask about the project...",
            fg_color=Theme.BG_DARKER,
            text_color=Theme.TEXT_MAIN,
            border_color=Theme.BG_DARK,
        )
        self.entry_msg.grid(row=0, column=1, sticky="ew", padx=(0, 8), pady=10)
        self.entry_msg.bind("<Return>", self.send_message)

        self.btn_send = ctk.CTkButton(
            self.frame_input,
            text="Send",
            fg_color=Theme.PRIMARY,
            hover_color=Theme.ACCENT,
            command=self.send_message,
        )
        self.btn_send.grid(row=0, column=2, padx=(0, 10), pady=10)

        self.lbl_attachments = ctk.CTkLabel(
            self.frame_input,
            text="",
            anchor="w",
            text_color=Theme.TEXT_MUTED,
            font=("Segoe UI", 11),
        )
        self.lbl_attachments.grid(row=1, column=0, columnspan=3, sticky="ew", padx=12, pady=(0, 8))

        self._show_welcome_message()

    def _show_welcome_message(self):
        project_id = getattr(self.controller, "active_project_id", None)
        if project_id:
            message = f"Welcome to Serapeum Expert Chat for {project_id}. Ask about scope, schedule, specifications, or drawings."
        else:
            message = "Welcome to Serapeum Expert Chat. Open a project and ask about scope, schedule, specifications, or drawings."
        self.add_message("System", message)

    def reset_view(self):
        self._chat_session_token += 1
        self._last_user_query = ""
        self.feedback_events = []
        self._clear_attachments()
        try:
            self.entry_msg.delete(0, "end")
        except Exception:
            pass
        for child in list(self.chat_container.winfo_children()):
            try:
                child.destroy()
            except Exception:
                pass
        self._show_welcome_message()

    def attach_files(self):
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
        if not files:
            return
        for path in files:
            if path not in self.attached_files:
                self.attached_files.append(path)
        self._refresh_attachment_label()

    def _refresh_attachment_label(self):
        if not self.attached_files:
            self.lbl_attachments.configure(text="")
            return
        names = [Path(p).name for p in self.attached_files[:3]]
        extra = max(0, len(self.attached_files) - 3)
        suffix = f" +{extra} more" if extra else ""
        self.lbl_attachments.configure(text="Attached: " + ", ".join(names) + suffix)

    def _clear_attachments(self):
        self.attached_files = []
        self._refresh_attachment_label()

    def send_message(self, event=None):
        msg = (self.entry_msg.get() or "").strip()
        if not msg and not self.attached_files:
            return
        if not msg and self.attached_files:
            self.add_message("System", "Add a prompt to use the attached files in chat.")
            return

        attachment_names = [Path(p).name for p in self.attached_files]
        self._last_user_query = msg
        self.add_message("User", msg, attachments=attachment_names)
        self.entry_msg.delete(0, "end")
        self._clear_attachments()

        if self.controller.orchestrator:
            request_token = self._chat_session_token
            request_project_id = getattr(self.controller, "active_project_id", None)
            def _ask():
                try:
                    res = run_mounted_chat_query(self.controller, msg)
                    ans = res.get("answer", "No response from brain.")
                    presentation = res.get("answer_presentation")
                    candidate_fact_suggestions = res.get("candidate_fact_suggestions", [])
                    source_lanes = res.get("source_lanes", {})
                    def _deliver():
                        if request_token != self._chat_session_token:
                            return
                        if request_project_id != getattr(self.controller, "active_project_id", None):
                            return
                        self.add_message(
                            "Serapeum",
                            ans,
                            answer_presentation=presentation,
                            candidate_fact_suggestions=candidate_fact_suggestions,
                            source_lanes=source_lanes,
                            query_text=msg,
                        )
                    self.safe_ui_after(0, _deliver)
                except Exception as e:
                    self.safe_ui_after(0, lambda: self.add_message("System", f"Error: {str(e)}"))

            threading.Thread(target=_ask, daemon=True).start()
        else:
            self.add_message("System", "Expert Brain not initialized for this project.")

    def add_message(
        self,
        sender: str,
        text: str,
        attachments: Optional[List[str]] = None,
        answer_presentation: Optional[Dict[str, Any]] = None,
        candidate_fact_suggestions: Optional[List[Dict[str, Any]]] = None,
        source_lanes: Optional[Dict[str, Any]] = None,
        query_text: Optional[str] = None,
    ):
        if self._page_closing or (self.controller is not None and getattr(self.controller, "_is_closing", False)):
            return
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return
        frame = ctk.CTkFrame(self.chat_container, fg_color=Theme.BG_DARKEST)
        frame.pack(fill="x", pady=10)

        bubble_bg = "#2b2b2b" if sender == "Serapeum" else "#333333"
        if sender == "System":
            bubble_bg = "#121212"

        bubble = ctk.CTkFrame(
            frame,
            fg_color=bubble_bg,
            bg_color=Theme.BG_DARKEST,
            corner_radius=10,
            border_width=1,
            border_color="#3a3a3a",
        )
        bubble.pack(anchor="w", fill="x", padx=10)

        header = ctk.CTkFrame(bubble, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=(10, 0))
        ctk.CTkLabel(
            header,
            text=sender,
            text_color=Theme.TEXT_MUTED if sender == "System" else Theme.TEXT_MAIN,
            font=("Segoe UI", 12, "bold"),
        ).pack(side="left")

        if sender == "Serapeum" and answer_presentation:
            self._render_answer_presentation(bubble, text, answer_presentation)
        else:
            lbl_text = tk.Label(
                bubble,
                text=text,
                justify="left",
                wraplength=820,
                fg=Theme.TEXT_MAIN,
                bg=bubble_bg,
                font=Theme.FONT_BODY,
            )
            lbl_text.pack(padx=15, pady=10, anchor="w")
            self._bind_copy_context(lbl_text, text)

        if attachments:
            attach_frame = ctk.CTkFrame(bubble, fg_color="transparent")
            attach_frame.pack(fill="x", padx=15, pady=(0, 8))
            ctk.CTkLabel(
                attach_frame,
                text="Attachments: " + ", ".join(attachments),
                text_color=Theme.TEXT_MUTED,
                font=("Segoe UI", 11),
            ).pack(anchor="w")

        if sender == "Serapeum":
            copy_text = (answer_presentation or {}).get("copy_text") or text
            footer = ctk.CTkFrame(frame, fg_color=Theme.BG_DARKEST)
            footer.pack(anchor="w", pady=(2, 0))

            btn_copy = ctk.CTkButton(
                footer,
                text="Copy",
                width=90,
                height=24,
                fg_color=Theme.BG_DARK,
                hover_color="#3a3a3a",
                command=lambda t=copy_text: self.copy_to_clipboard(t),
            )
            btn_copy.pack(side="left", padx=(0, 6))

            feedback_status = ctk.CTkLabel(
                footer,
                text="",
                text_color=Theme.TEXT_MUTED,
                font=("Segoe UI", 10),
            )

            payload = {
                "query": query_text or self._last_user_query,
                "answer": text,
                "answer_presentation": answer_presentation or {},
                "candidate_fact_suggestions": candidate_fact_suggestions or [],
                "source_lanes": source_lanes or {},
            }

            btn_up = ctk.CTkButton(
                footer,
                text="Helpful",
                width=90,
                height=24,
                fg_color=Theme.BG_DARK,
                hover_color="#3a3a3a",
                command=lambda: self.capture_feedback("helpful", payload, feedback_status, btn_up, btn_down),
            )
            btn_up.pack(side="left", padx=(0, 6))

            btn_down = ctk.CTkButton(
                footer,
                text="Needs work",
                width=90,
                height=24,
                fg_color=Theme.BG_DARK,
                hover_color="#3a3a3a",
                command=lambda: self.capture_feedback("needs_work", payload, feedback_status, btn_up, btn_down),
            )
            btn_down.pack(side="left")
            feedback_status.pack(side="left", padx=(8, 0))

        self._scroll_to_bottom()

    def _render_answer_presentation(self, bubble, fallback_text: str, presentation: Dict[str, Any]):
        summary = presentation.get("summary_block") or {}
        main_answer = presentation.get("main_answer_text") or summary.get("text") or fallback_text
        source_basis_banner = presentation.get("source_basis_banner") or summary.get("source_basis_banner") or ""

        answer_frame = ctk.CTkFrame(bubble, fg_color="transparent")
        answer_frame.pack(fill="x", padx=15, pady=(10, 8))
        if source_basis_banner:
            ctk.CTkLabel(
                answer_frame,
                text=source_basis_banner,
                justify="left",
                anchor="w",
                wraplength=820,
                text_color=Theme.TEXT_MUTED,
                font=("Segoe UI", 10, "italic"),
            ).pack(fill="x", pady=(0, 6))
        answer_label = tk.Label(
            answer_frame,
            text=main_answer,
            justify="left",
            wraplength=820,
            fg=Theme.TEXT_MAIN,
            bg=bubble.cget("fg_color"),
            font=Theme.FONT_BODY,
        )
        answer_label.pack(anchor="w")
        self._bind_copy_context(answer_label, main_answer)

        sections = presentation.get("sections") or []
        details_frame = ctk.CTkFrame(bubble, fg_color=Theme.BG_DARKEST, corner_radius=8)
        details_visible = {"shown": False}

        def _toggle_details():
            if details_visible["shown"]:
                details_frame.pack_forget()
                btn_toggle.configure(text=presentation.get("details_button_label", "Show Evidence"))
                details_visible["shown"] = False
            else:
                details_frame.pack(fill="x", padx=15, pady=(0, 8))
                btn_toggle.configure(text="Hide Evidence")
                details_visible["shown"] = True

        controls = ctk.CTkFrame(bubble, fg_color="transparent")
        controls.pack(fill="x", padx=15, pady=(0, 8))
        btn_toggle = ctk.CTkButton(
            controls,
            text=presentation.get("details_button_label", "Show Evidence"),
            width=140,
            height=26,
            fg_color=Theme.BG_DARK,
            hover_color=Theme.BG_DARKER,
            command=_toggle_details,
        )
        btn_toggle.pack(side="left")
        btn_copy_details = ctk.CTkButton(
            controls,
            text="Copy Evidence",
            width=120,
            height=26,
            fg_color=Theme.BG_DARK,
            hover_color=Theme.BG_DARKER,
            command=lambda: self.copy_to_clipboard(presentation.get("details_copy_text") or presentation.get("copy_text") or main_answer),
        )
        btn_copy_details.pack(side="left", padx=(8, 0))

        for section in sections:
            items = section.get("items") or []
            empty_message = section.get("empty_message")
            if not items and not empty_message:
                continue
            section_kind = section.get("kind", "default")
            section_frame = ctk.CTkFrame(
                details_frame,
                fg_color=Theme.BG_DARKEST if section_kind != "ai" else Theme.BG_DARKER,
                corner_radius=8,
                border_width=1,
                border_color="#353535",
            )
            section_frame.pack(fill="x", padx=10, pady=(8, 0))
            ctk.CTkLabel(
                section_frame,
                text=section.get("title", "Section"),
                text_color=Theme.TEXT_MAIN,
                font=("Segoe UI", 12, "bold"),
            ).pack(anchor="w", padx=10, pady=(8, 4))
            if section.get("note"):
                ctk.CTkLabel(
                    section_frame,
                    text=section["note"],
                    justify="left",
                    anchor="w",
                    wraplength=800,
                    text_color=Theme.TEXT_MUTED,
                    font=("Segoe UI", 10),
                ).pack(fill="x", padx=10, pady=(0, 6))
            if items:
                for item in items:
                    self._render_section_item(section_frame, item)
            elif empty_message:
                ctk.CTkLabel(
                    section_frame,
                    text=empty_message,
                    justify="left",
                    anchor="w",
                    wraplength=800,
                    text_color=Theme.TEXT_MUTED,
                    font=Theme.FONT_BODY,
                ).pack(fill="x", padx=10, pady=(0, 8))

    def _render_section_item(self, parent, item: Dict[str, Any]):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=(0, 8))
        if item.get("is_group_heading"):
            heading = ctk.CTkLabel(
                row,
                text=item.get("text", ""),
                justify="left",
                anchor="w",
                wraplength=800,
                text_color=Theme.TEXT_MAIN,
                font=("Segoe UI", 11, "bold"),
            )
            heading.pack(fill="x", pady=(0, 0))
            return
        chip_widget = self._make_chip(
            row,
            item.get("chip", "Source"),
            kind=item.get("source_class", "default"),
            fact_id=item.get("fact_id"),
        )
        chip_widget.pack(anchor="w")
        text_label = ctk.CTkLabel(
            row,
            text=item.get("text", ""),
            justify="left",
            anchor="w",
            wraplength=800,
            text_color=Theme.TEXT_MAIN,
            font=Theme.FONT_BODY,
        )
        text_label.pack(fill="x", pady=(4, 0))
        if item.get("details"):
            ctk.CTkLabel(
                row,
                text=item.get("details"),
                justify="left",
                anchor="w",
                wraplength=800,
                text_color=Theme.TEXT_MUTED,
                font=("Segoe UI", 10),
            ).pack(fill="x", pady=(2, 0))
        self._bind_copy_context(text_label, item.get("copy_text") or item.get("text", ""))

    def _make_chip(self, parent, text: str, kind: str = "default", fact_id: Optional[str] = None):
        color_map = {
            "trusted_facts": Theme.SUCCESS,
            "extracted_evidence": Theme.PRIMARY,
            "linked_support": Theme.WARNING,
            "ai_analysis": Theme.BG_DARK,
            "ai_synthesis": Theme.BG_DARK,
            "summary": Theme.BG_DARK,
        }
        fg = color_map.get(kind, Theme.BG_DARK)
        if fact_id:
            return ctk.CTkButton(
                parent,
                text=text,
                height=24,
                width=110,
                corner_radius=12,
                fg_color=fg,
                hover_color=Theme.ACCENT,
                font=("Segoe UI", 10, "bold"),
                command=lambda f=fact_id: self.open_citation(f),
            )
        return ctk.CTkLabel(
            parent,
            text=text,
            fg_color=fg,
            corner_radius=12,
            text_color=Theme.TEXT_MAIN,
            font=("Segoe UI", 10, "bold"),
            padx=10,
            pady=4,
        )

    def capture_feedback(self, verdict: str, payload: Dict[str, Any], status_label, btn_up, btn_down):
        event = {
            "verdict": verdict,
            "query": payload.get("query"),
            "answer": payload.get("answer"),
            "source_lanes": payload.get("source_lanes", {}),
            "candidate_fact_suggestions": payload.get("candidate_fact_suggestions", []),
            "answer_presentation": payload.get("answer_presentation", {}),
        }
        self.feedback_events.append(event)
        status_label.configure(text="Feedback captured for follow-up fact review.")
        btn_up.configure(state="disabled")
        btn_down.configure(state="disabled")

    def copy_to_clipboard(self, text: str):
        if self._page_closing or (self.controller is not None and getattr(self.controller, "_is_closing", False)):
            return
        self.clipboard_clear()
        self.clipboard_append(text or "")
        try:
            self.update_idletasks()
        except Exception:
            pass

    def _bind_copy_context(self, widget, text: str):
        menu = tk.Menu(widget, tearoff=0)
        menu.add_command(label="Copy", command=lambda t=text: self.copy_to_clipboard(t))
        widget.bind("<Button-3>", lambda event: menu.tk_popup(event.x_root, event.y_root))

    def _scroll_to_bottom(self):
        if self._page_closing or (self.controller is not None and getattr(self.controller, "_is_closing", False)):
            return
        try:
            self.update_idletasks()
        except Exception:
            return
        try:
            self.scroll_chat._parent_canvas.yview_moveto(1.0)
        except Exception:
            pass

    def on_app_close(self):
        super().on_app_close()

    def open_citation(self, fact_id):
        if self.controller.db:
            FactLineagePopup(self, self.controller.db, fact_id)
        else:
            print(f"Open Fact {fact_id}")
