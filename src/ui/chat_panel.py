# -*- coding: utf-8 -*-
import os
import logging
import json
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable

import tkinter as tk
from tkinter import ttk, messagebox

from src.ui.styles.theme import Theme
from src.infra.adapters.llm_service import LLMService
from src.infra.adapters.cancellation import CancellationToken
from src.role_management.role_manager import RoleManager
from src.ui.components.message_renderer import MessageRenderer
from src.ui.components.conversation_manager import ConversationManager
from src.ui.components.chat_toolbar import ChatToolbar
from src.ui.components.chat_input_area import ChatInputArea
from src.utils.hardening import safe_ui_command

logger = logging.getLogger(__name__)

class ChatPanel(ttk.Frame):
    """
    SerapeumAI Advanced Chat Infrastructure (Phase 5.3)
    Supports diagnostic thinking streams, copy/paste, and agentic reasoning.
    """
    def __init__(self, master, *, db=None, llm: Optional[LLMService] = None, project_id: Optional[str] = None) -> None:
        super().__init__(master)
        self.db = db
        self.llm = llm
        self.project_id = project_id
        self.project_dir = getattr(db, "root_dir", os.getcwd()) if db else os.getcwd()
        self.role_mgr = RoleManager(db) if db else None

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # 1. Toolbar
        self.toolbar = ChatToolbar(
            self,
            on_history_toggle=self._toggle_history,
            on_clear=self._clear_chat,
            on_new_chat=self._new_chat_session
        )
        self.toolbar.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))

        # Variables aliases for compatibility
        self.role_var = self.toolbar.role_var
        self.spec_var = self.toolbar.spec_var
        self.ref_var = self.toolbar.ref_var
        self.compliance_var = self.toolbar.compliance_var
        self.show_history = self.toolbar.show_history

        # 2. Main Chat View (Paned for History)
        self.paned = tk.PanedWindow(self, orient="horizontal", background=Theme.BG_DARKEST, borderwidth=0, sashwidth=4)
        self.paned.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)

        self.chat_viewport_frame = tk.Frame(self.paned, background=Theme.BG_DARKEST)
        self.paned.add(self.chat_viewport_frame)

        self.history_frame = tk.Frame(self.paned, background=Theme.BG_DARKER)
        self._history_visible = False

        # The Text Widget (The Core Chat Log)
        self.text_widget = tk.Text(
            self.chat_viewport_frame, 
            wrap="word",
            font=Theme.FONT_BODY,
            foreground=Theme.TEXT_MAIN,
            background=Theme.BG_DARKEST,
            insertbackground=Theme.TEXT_MAIN,
            selectbackground=Theme.BG_DARK,
            padx=20, pady=20,
            borderwidth=0,
            highlightthickness=0
        )
        self.text_widget.pack(side="left", fill="both", expand=True)
        
        # Scrollbar
        self.scrollbar = ttk.Scrollbar(self.chat_viewport_frame, orient="vertical", command=self.text_widget.yview)
        self.scrollbar.pack(side="right", fill="y")
        self.text_widget.configure(yscrollcommand=self.scrollbar.set)

        # Multi-stage Read-Only Binding (Allows Copy/Selection, Blocks Typing)
        self.text_widget.bind("<Key>", self._handle_read_only_keys)
        self.text_widget.bind("<Control-c>", lambda e: None) # Default copy allowed
        self.text_widget.bind("<Control-a>", lambda e: None) # Default select all allowed

        # 3. Message Renderer
        def _get_role_name():
            if self.role_mgr:
                return self.role_mgr.get_persona_name(self.role_var.get(), self.spec_var.get())
            return "Assistant"
            
        self.renderer = MessageRenderer(self.text_widget, _get_role_name)

        # 4. Input Area
        self.input_area = ChatInputArea(
            self,
            project_dir=self.project_dir,
            on_send=self._on_send,
            on_cancel=self._on_cancel,
            on_return_key=self._on_return_key
        )
        self.input_area.grid(row=2, column=0, sticky="ew", padx=10, pady=(5, 10))
        
        # UI aliases
        self.txt_input = self.input_area.txt_input
        self.lbl_status = self.input_area.lbl_status
        self.attachment_handler = self.input_area.attachment_handler

        # 5. Services
        self.conv_mgr = ConversationManager(self.db, self.project_id, self.history_frame)
        self.cancellation_token: Optional[CancellationToken] = None
        
        try:
            from src.ui.components.chat_llm_bridge import ChatLLMBridge
            self.llm_bridge = ChatLLMBridge(self)
        except Exception:
            self.llm_bridge = None

        if self.db and self.project_id:
            self._load_history()

    def set_orchestrator(self, orchestrator):
        self.orchestrator = orchestrator

    def _handle_read_only_keys(self, event):
        """Block all keys except copy/select combinations."""
        # Allow Control key combinations (Ctrl+C, Ctrl+A, etc.)
        if (event.state & 0x4): 
            return None
        # Allow navigation keys
        if event.keysym in ("Up", "Down", "Left", "Right", "Prior", "Next", "Home", "End"):
            return None
        return "break"

    def _on_return_key(self, event):
        if not (event.state & 0x1): # Shift NOT pressed
            self._on_send()
            return "break"
        return None

    @safe_ui_command("Chat Execution Error")
    def _on_send(self) -> None:
        if self.cancellation_token and not self.cancellation_token.is_cancelled():
            self.cancellation_token.cancel("User-initiated stop")
            self._update_status("Stopping...")
            return

        query = self.txt_input.get("1.0", "end-1c").strip()
        atts = self.attachment_handler.get_attachments()
        if not query and not atts:
            return

        # UI Update
        self.txt_input.delete("1.0", "end")
        self.attachment_handler.clear()
        self.renderer.append("You", query, atts)
        self._update_status("Thinking...")
        self.input_area.toggle_send_button(stop=True)

        self.cancellation_token = CancellationToken()
        threading.Thread(
            target=self._run_llm_flow,
            args=(query, atts, self.cancellation_token),
            daemon=True
        ).start()

    def _on_cancel(self):
        if self.cancellation_token:
            self.cancellation_token.cancel("User cancelled")
        self._update_status("Cancelled")
        self.input_area.toggle_send_button(stop=False)

    def _run_llm_flow(self, query: str, attachments: List[str], token: CancellationToken):
        try:
            if self.llm_bridge:
                self.llm_bridge.run_llm_logic(query, attachments, token)
            else:
                self.after(0, lambda: self.renderer.append("System", "Chat Bridge not initialized."))
        except Exception as e:
            logger.error(f"Chat Execution Failed: {e}", exc_info=True)
            self.after(0, lambda: self.renderer.append("System", f"Error: {str(e)}"))
        finally:
            self.cancellation_token = None
            self._update_status("Ready")
            self.after(0, lambda: self.input_area.toggle_send_button(stop=False))

    def _update_status(self, text: str):
        self.after(0, lambda: self.lbl_status.configure(text=text))

    def _toggle_history(self):
        if self.show_history.get():
            self.paned.add(self.history_frame)
            self.conv_mgr.refresh_history_panel()
        else:
            self.paned.forget(self.history_frame)

    def _clear_chat(self):
        self.text_widget.configure(state="normal")
        self.text_widget.delete("1.0", "end")
        self.text_widget.configure(state="disabled")
        self._update_status("Chat cleared.")

    def _new_chat_session(self):
        self._append("System", "New session initialized.")

    def _append(self, role: str, text: str, attachments: Optional[List[str]] = None, is_thinking: bool = False):
        """Bridge method for MessageRenderer to be called from bridge/orchestrator."""
        self.after(0, lambda: self.renderer.append(role, text, attachments, is_thinking))

    def _load_history(self):
        if self.conv_mgr:
            self.conv_mgr.load_history_to_view(self.renderer)
