# -*- coding: utf-8 -*-
# Copyright (c) 2025 Ahmed Gaballa
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
ChatPanel — role + discipline aware chat for Serapeum AECO.
Modularized version.
"""

from __future__ import annotations
import json
import os
import threading
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable

import tkinter as tk
from tkinter import ttk as tk_ttk, messagebox

from tkinter import ttk
ScrolledText = tk.Text

_USING_TTKBOOTSTRAP = False

logger = logging.getLogger(__name__)

from src.infra.adapters.llm_service import LLMService
from src.infra.adapters.cancellation import CancellationToken
from src.role_management.role_manager import RoleManager
from src.ui.components.attachment_handler import AttachmentHandler
from src.ui.components.message_renderer import MessageRenderer
from src.ui.components.conversation_manager import ConversationManager
from src.utils.hardening import safe_ui_command
from src.ui.components.chat_toolbar import ChatToolbar
from src.ui.components.chat_input_area import ChatInputArea

def _ensure_dir(path: str) -> None:
    try:
        os.makedirs(path, exist_ok=True)
    except Exception:
        pass

def _profile_path(project_dir: str) -> str:
    return os.path.join(project_dir, ".serapeum", "_context", "profile.json")

def _read_profile(project_dir: str) -> Dict[str, Any]:
    try:
        with open(_profile_path(project_dir), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _write_profile(project_dir: str, data: Dict[str, Any]) -> None:
    try:
        path = _profile_path(project_dir)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data or {}, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def _strip_bootstyle(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    if _USING_TTKBOOTSTRAP:
        return kwargs
    kwargs.pop("bootstyle", None)
    return kwargs

def _token_is_cancelled(token: Any) -> bool:
    if token is None:
        return False
    try:
        v = getattr(token, "is_cancelled", None)
        if callable(v):
            return bool(v())
        if isinstance(v, bool):
            return v
    except Exception:
        pass
    try:
        v = getattr(token, "is_set", None)
        if callable(v):
            return bool(v())
    except Exception:
        pass
    return False

class _ChatLogger:
    def __init__(self, project_dir: str) -> None:
        self.project_dir = project_dir
        _ensure_dir(os.path.join(project_dir, "_logs"))

    def write(self, role: str, text: str, meta: Optional[dict] = None) -> None:
        day = datetime.now().strftime("%Y%m%d")
        path = os.path.join(self.project_dir, "_logs", f"chat-{day}.jsonl")
        rec = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "role": role,
            "text": text,
            "meta": meta or {},
        }
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except Exception:
            pass

class ChatPanel(ttk.Frame):
    def __init__(self, master, *, db=None, llm: Optional[LLMService] = None, project_id: Optional[str] = None) -> None:
        super().__init__(master)
        self.db = db
        self.llm = llm
        self.project_id = project_id
        self.project_dir = getattr(db, "root_dir", os.getcwd()) if db else os.getcwd()
        self.logger = _ChatLogger(self.project_dir) if db else None
        self.role_mgr = RoleManager(db) if db else None

        self._session_state = {
            "mode": "Mode B",
            "strict_evidence": False,
            "validation_scope": "local_only",
            "variations_tried": 0,
            "turns_used": 0,
            "found_context": [],
        }

        self.renderer: Optional[MessageRenderer] = None
        self.conv_mgr: Optional[ConversationManager] = None

        try:
            from src.ui.components.chat_llm_bridge import ChatLLMBridge
            self.llm_bridge = ChatLLMBridge(self)
        except Exception:
            self.llm_bridge = None

        self.on_artifact_generated: Optional[Callable[[str, str, str, Optional[str]], None]] = None

        try:
            from src.reference_service.reference_manager import ReferenceManager
            self.ref_mgr = ReferenceManager(db) if db else None
        except Exception:
            self.ref_mgr = None

        prof = _read_profile(self.project_dir)
        default_role = prof.get("role", "PMC")
        default_spec = prof.get("specialty", "Project Manager")

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # --- Toolbar ---
        ref_sets = ["None"]
        if self.ref_mgr:
            try:
                ref_sets += [s["name"] for s in self.ref_mgr.list_sets()]
            except Exception:
                pass

        self.toolbar = ChatToolbar(
            self,
            default_role=default_role,
            default_spec=default_spec,
            ref_sets=ref_sets,
            on_ref_change=self._on_ref_set_changed,
            on_new_chat=self._new_chat_session,
            on_clear=self._clear_chat,
            on_history_toggle=self._toggle_history,
            on_db_info=self._show_db_info,
            on_settings=self._open_settings
        )
        self.toolbar.grid(row=0, column=0, sticky="ew", padx=6, pady=6)

        # Compatibility Aliases
        self.role_var = self.toolbar.role_var
        self.spec_var = self.toolbar.spec_var
        self.ref_var = self.toolbar.ref_var
        self.structured_var = self.toolbar.structured_var
        self.advanced_var = self.toolbar.advanced_var
        self.smart_query_var = self.toolbar.smart_query_var
        self.compliance_var = self.toolbar.compliance_var
        self.show_history = self.toolbar.show_history

        # --- Main Layout (Paned) ---
        self.paned = tk.PanedWindow(self, orient="horizontal")
        self.paned.grid(row=1, column=0, sticky="nsew", padx=6, pady=4)

        self.chat_frame = ttk.Frame(self.paned)
        self.paned.add(self.chat_frame)

        self.history_frame = ttk.Frame(self.paned)
        self._history_added = False

        if ScrolledText is not tk.Text:
            self.text = ScrolledText(self.chat_frame, padding=10, autohide=True)
            self.text_widget = getattr(self.text, "text", self.text)
        else:
            self.text = tk.Text(self.chat_frame, wrap="word")
            self.text_widget = self.text

        self.text_widget.configure(
            font=("Segoe UI", 10),
            foreground="#ffffff",
            background="#1e1e1e",
            insertbackground="#ffffff",
            selectforeground="#ffffff",
            selectbackground="#474747",
        )
        self.text.pack(fill="both", expand=True)

        def _persona_name() -> str:
            try:
                if self.role_mgr:
                    return self.role_mgr.get_persona_name(self.role_var.get(), self.spec_var.get())
            except Exception:
                pass
            return "AI"

        self.renderer = MessageRenderer(self.text_widget, _persona_name)

        self.text_widget.bind("<Key>", lambda e: "break")
        self.text_widget.bind("<Control-c>", lambda e: None)
        self.text_widget.bind("<<Copy>>", lambda e: None)

        # --- Input area ---
        self.input_area = ChatInputArea(
            self,
            project_dir=self.project_dir,
            on_send=self._on_send,
            on_cancel=self._on_cancel,
            on_return_key=self._on_return_key
        )
        self.input_area.grid(row=2, column=0, sticky="ew", padx=6, pady=(0, 6))

        # Compatibility Aliases
        self.attachment_handler = self.input_area.attachment_handler
        self.txt_input = self.input_area.txt_input
        self.btn_send = self.input_area.btn_send
        self.btn_cancel = self.input_area.btn_cancel
        self.lbl_status = self.input_area.lbl_status

        self.conv_mgr = ConversationManager(self.db, self.project_id, self.history_frame)
        self._setup_drag_drop()

        if not default_role or not default_spec:
            self._persist_profile()

        if self.db and self.project_id:
            self._load_history()

        self.cancellation_token: Optional[CancellationToken] = None

    def set_components(self, db, llm):
        """Update components after init."""
        self.db = db
        self.llm = llm
        self.project_dir = getattr(db, "root_dir", os.getcwd())
        self.logger = _ChatLogger(self.project_dir)
        self.role_mgr = RoleManager(db)

        try:
            from src.reference_service.reference_manager import ReferenceManager
            self.ref_mgr = ReferenceManager(db)
        except Exception:
            self.ref_mgr = None

        if hasattr(self, "toolbar") and self.toolbar.ref_combo:
            ref_sets = ["None"]
            if self.ref_mgr:
                try:
                    ref_sets += [s["name"] for s in self.ref_mgr.list_sets()]
                except Exception:
                    pass
            self.toolbar.update_ref_sets(ref_sets)

        if self.conv_mgr:
            self.conv_mgr.db = db

    def load_project(self, project_id):
        """Load project-specific state."""
        self.project_id = project_id
        if self.conv_mgr:
            self.conv_mgr.project_id = project_id

        try:
            self.text_widget.delete("1.0", "end")
        except Exception:
            pass

        self._load_history()

        try:
            if self.ref_mgr:
                active = self.ref_mgr.get_active(project_id)
                if active:
                    self.ref_var.set(active["name"])
                else:
                    self.ref_var.set("None")
        except Exception as e:
            logger.warning(f"Failed to load reference manager: {e}")
            self.ref_var.set("None")

    def _update_status(self, text: str) -> None:
        try:
            self.after(0, lambda: self.lbl_status.configure(text=text))
        except Exception:
            pass

    def focus_entry(self) -> None:
        try:
            self.txt_input.focus_set()
        except Exception:
            pass

    def _persist_profile(self) -> None:
        _write_profile(self.project_dir, {"role": self.role_var.get(), "specialty": self.spec_var.get()})

    def _setup_drag_drop(self) -> None:
        pass

    def _clean_context(self, text: str) -> str:
        if not text:
            return ""
        if "\0" in text:
            text = text.replace("\0", "")
        import string
        printable = set(string.printable)
        garbage_count = sum(1 for c in text if c not in printable)
        if len(text) > 100 and (garbage_count / len(text)) > 0.20:
            return "[System: Binary content removed]"
        return text

    @safe_ui_command("Reference Update Error")
    def _on_ref_set_changed(self, name: str) -> None:
        if not self.project_id:
            return
        try:
            if self.ref_mgr:
                if name == "None":
                    self.ref_mgr.set_active(self.project_id, None)
                else:
                    s_idx = next((s for s in self.ref_mgr.list_sets() if s["name"] == name), None)
                    if s_idx:
                        self.ref_mgr.set_active(self.project_id, s_idx["id"])
            self._update_status(f"Ref set: {name}")
        except Exception as e:
            logger.warning(f"Failed to set active ref: {e}")

    def _on_return_key(self, event) -> str:
        try:
            if event.state & 0x1:
                return None
        except Exception:
            pass
        self._on_send()
        return "break"

    def _get_project_context(self) -> dict:
        return self.conv_mgr.get_context() if self.conv_mgr else {}

    def _append(self, role: str, text: str, attachments: Optional[List[str]] = None) -> None:
        if self.renderer:
            self.renderer.append(role, text, attachments)
            # Performance Tuning: Truncate extremely long chat views
            try:
                line_count = int(self.text_widget.index("end-1c").split(".")[0])
                if line_count > 5000:
                    # Remove oldest 1000 lines to keep UI snappy
                    self.text_widget.configure(state="normal")
                    self.text_widget.delete("1.0", "1000.0")
                    self.text_widget.insert("1.0", "[--- Older messages truncated for performance ---]\n\n", "system")
                    self.text_widget.configure(state="disabled")
            except Exception:
                pass

    def _load_history(self) -> None:
        if self.conv_mgr and self.renderer:
            self.conv_mgr.load_history_to_view(self.renderer)

    def _toggle_history(self) -> None:
        if self.show_history.get():
            if not self._history_added:
                try:
                    self.paned.add(self.history_frame)
                    self._history_added = True
                except Exception:
                    pass
            self._refresh_history_panel()
        else:
            if self._history_added:
                try:
                    self.paned.forget(self.history_frame)
                except Exception:
                    pass
                self._history_added = False

    def _refresh_history_panel(self) -> None:
        if self.conv_mgr:
            self.conv_mgr.refresh_history_panel()

    def _toggle_send_button(self, stop: bool) -> None:
        if hasattr(self, "input_area"):
            self.input_area.toggle_send_button(stop)

    @safe_ui_command("Chat Execution Error")
    def _on_send(self) -> None:
        if self.cancellation_token and not _token_is_cancelled(self.cancellation_token):
            try:
                self.cancellation_token.cancel("User requested stop")
            except Exception:
                pass
            self._update_status("Stopping...")
            return

        user_query = self.txt_input.get("1.0", "end-1c").strip()
        current_atts = self.attachment_handler.get_attachments() if self.attachment_handler else []
        if not user_query and not current_atts:
            return

        self.txt_input.delete("1.0", "end")
        if self.attachment_handler:
            self.attachment_handler.clear()

        self._append("You", user_query, current_atts)
        self._update_status("Thinking...")
        self._toggle_send_button(stop=True)

        self.cancellation_token = CancellationToken()

        if self.db and self.project_id:
            try:
                self.db.save_chat_message(self.project_id, "user", user_query, current_atts)
            except Exception as e:
                logger.warning(f"Failed to save user message to history: {e}")

        threading.Thread(
            target=self._run_llm_thread,
            args=(user_query, current_atts, self.cancellation_token),
            daemon=True,
        ).start()

    def _on_cancel(self) -> None:
        try:
            if self.cancellation_token and not _token_is_cancelled(self.cancellation_token):
                self.cancellation_token.cancel("User cancelled via Cancel button")
                self._update_status("Cancelled")
        except Exception:
            pass
        finally:
            self.after(0, lambda: self._toggle_send_button(stop=False))

    def _run_llm_thread(self, user_query: str, attachments: List[str], token: Any) -> None:
        try:
            self._run_llm_logic(user_query, attachments, token)
        except Exception as e:
            import traceback
            traceback.print_exc()
            err_msg = f"Chat Error: {str(e)}"
            self.after(0, lambda: self._append("System", f"❌ {err_msg}"))
        finally:
            self.cancellation_token = None
            self._update_status("Ready")
            self.after(0, lambda: self._toggle_send_button(stop=False))

    def _classify_intent(self, query: str) -> Dict[str, Any]:
        q = query.lower()
        artifact_triggers = ["artifact", "deliverable", "full sow", "write sow", "generate sow", "export", "docx", "pdf"]
        if any(w in q for w in artifact_triggers):
            return {"mode": "Mode F", "strict": False, "scope": "local_only", "desc": "Actionable Deliverables / Artifact (Deterministic)"}
        if self.compliance_var.get():
            return {"mode": "Mode C", "strict": False, "scope": "local+web", "desc": "Compliance / Standards Check (Forced)"}
        mode_a_words = ["exact mention", "cite clause", "quote", "where exactly", "clause", "page", "verbatim"]
        if any(w in q for w in mode_a_words) or ('"' in query):
            return {"mode": "Mode A", "strict": True, "scope": "local_only", "desc": "Clause Finder (Strict Evidence)"}
        return {"mode": "Mode B", "strict": False, "scope": "local_only", "desc": "Spec/Doc Summary (General)"}

    def _get_mode_instructions(self, mode_info: Dict[str, Any]) -> str:
        mode, desc, strict, scope = mode_info["mode"], mode_info["desc"], mode_info["strict"], mode_info["scope"]
        instr = f"You are operating in '{mode}: {desc}' mode. "
        if strict:
            instr += "Find and cite EXACT mentions/clauses. DO NOT paraphrase. "
        else:
            instr += "Summarize and synthesize based on context. "
        instr += "Always provide a procedural <plan> only. No private reasoning."
        return instr

    def _run_llm_logic(self, user_query: str, attachments: List[str], token: CancellationToken) -> None:
        self._update_status("Resolving Scope...")
        if attachments and self.db:
            try:
                from src.application.services.document_service import DocumentService
                doc_service = DocumentService(db=self.db, project_root=self.project_dir)
                for att_path in attachments:
                    if _token_is_cancelled(token): return
                    doc_service.ingest_document(abs_path=att_path, project_id=self.project_id)
            except Exception as e:
                self.after(0, lambda: self._append("System", f"⚠️ Attachment ingestion failed: {e}"))

        if _token_is_cancelled(token): return

        if hasattr(self, "orchestrator") and self.orchestrator:
            self._update_status("Agentic Reasoning...")
            result = self.orchestrator.answer_question(query=user_query)
            if _token_is_cancelled(token): return

            thinking = result.get("thinking", "")
            if thinking:
                self.after(0, lambda: self._append("System", f"🧠 Thinking:\n{thinking}"))

            answer = result.get("answer", "No answer generated.")
            citations = result.get("citations", [])
            if citations:
                answer += "\n\n### Citations:\n"
                for c in citations:
                    answer += f"- *{c.get('source')}*: \"{c.get('quote')}\"\n"

            self.after(0, lambda: self._append("AI", answer))
            
            actions = result.get("suggested_actions", [])
            if actions:
                for a in actions:
                    def _do_action(text=a):
                        self.txt_input.delete("1.0", "end")
                        self.txt_input.insert("end", text)
                        self._on_send()
                    self.after(0, lambda t=a, h=_do_action: self.renderer.append_suggested_action(t, h))

            if self.db and self.project_id:
                try:
                    self.db.save_chat_message(self.project_id, "assistant", answer)
                except Exception as e:
                    logger.warning(f"Failed to save assistant message to history: {e}")
        else:
            self.after(0, lambda: self._append("System", "❌ Agent Orchestrator not initialized."))

    def _show_db_info(self) -> None:
        if not self.db or not self.project_id:
            messagebox.showinfo("Database Info", "No database/project loaded.")
            return
        try:
            docs = self.db.list_documents(project_id=self.project_id, limit=1000) or []
            info = f"Project: {self.project_id}\nDocuments: {len(docs)}"
            messagebox.showinfo("Database Info", info)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _new_chat_session(self) -> None:
        try:
            if self.db and self.project_id and hasattr(self.llm, "use_lm_studio") and getattr(self.llm, "use_lm_studio", False):
                self.db.execute("DELETE FROM lm_studio_sessions WHERE project_id = ?", (self.project_id,))
                self.db.commit()
                self._append("System", "✅ New chat session started")
            else:
                self._append("System", "ℹ️ New session (LM Studio not enabled)")
        except Exception as e:
            self._append("System", f"⚠️ Error: {e}")

    def _clear_chat(self) -> None:
        try: self.text_widget.delete("1.0", tk.END)
        except Exception: pass
        self._update_status("Chat cleared.")

    def _open_settings(self) -> None:
        try:
            from src.ui.settings_dialog import SettingsDialog
            SettingsDialog(self)
        except Exception as e:
            messagebox.showerror("Error", str(e))
