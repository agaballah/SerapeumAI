# -*- coding: utf-8 -*-
import tkinter as tk
from typing import Dict, Any, List, Optional, Callable

from tkinter import ttk


class ChatToolbar(ttk.Frame):
    def __init__(
        self, 
        master, 
        default_role: str = "PMC",
        default_spec: str = "Project Manager",
        ref_sets: List[str] = None,
        on_ref_change: Callable[[str], None] = None,
        on_new_chat: Callable[[], None] = None,
        on_clear: Callable[[], None] = None,
        on_history_toggle: Callable[[], None] = None,
        on_db_info: Callable[[], None] = None,
        on_settings: Callable[[], None] = None,
        **kwargs
    ):
        super().__init__(master, **kwargs)
        self.on_ref_change = on_ref_change
        self.on_new_chat = on_new_chat
        self.on_clear = on_clear
        self.on_history_toggle = on_history_toggle
        self.on_db_info = on_db_info
        self.on_settings = on_settings

        # Variables
        self.role_var = tk.StringVar(value=default_role)
        self.spec_var = tk.StringVar(value=default_spec)
        self.ref_var = tk.StringVar(value="None")
        self.structured_var = tk.BooleanVar(value=False)
        self.advanced_var = tk.BooleanVar(value=False)
        self.smart_query_var = tk.BooleanVar(value=True)
        self.compliance_var = tk.BooleanVar(value=False)
        self.show_history = tk.BooleanVar(value=False)

        self._build_ui(ref_sets or ["None"])

    def _build_ui(self, ref_sets: List[str]):
        # Role
        ttk.Label(self, text="Role:").pack(side="left", padx=(0, 5))
        self.role_combo = ttk.Combobox(
            self,
            textvariable=self.role_var,
            values=("Contractor", "Owner", "Technical Consultant", "PMC"),
            width=18,
            state="readonly",
        )
        self.role_combo.pack(side="left", padx=(0, 10))

        # Disc
        ttk.Label(self, text="Disc:").pack(side="left", padx=(0, 5))
        self.spec_combo = ttk.Combobox(
            self,
            textvariable=self.spec_var,
            values=("Arch", "Elec", "Mech", "Str", "Project Manager"),
            width=15,
            state="readonly",
        )
        self.spec_combo.pack(side="left", padx=(0, 10))

        # Ref
        ttk.Label(self, text="Ref:").pack(side="left", padx=(0, 5))
        self.ref_combo = ttk.Combobox(
            self,
            textvariable=self.ref_var,
            values=ref_sets,
            width=15,
            state="readonly",
        )
        self.ref_combo.pack(side="left", padx=(0, 10))
        self.ref_combo.bind("<<ComboboxSelected>>", lambda e: self.on_ref_change(self.ref_var.get()) if self.on_ref_change else None)

        # Toggles
        self._add_toggle("Decision-Ready", self.structured_var)
        self._add_toggle("Advanced", self.advanced_var)
        self._add_toggle("Smart Query", self.smart_query_var)
        self._add_toggle("Compliance", self.compliance_var)

        # Buttons (Right-aligned)
        self._add_button("Settings", self.on_settings, side="right", width=10, bootstyle="link")
        self._add_button("DB Info", self.on_db_info, side="right", bootstyle="info-outline-link")
        self._add_button("Clear", self.on_clear, side="right", bootstyle="danger-outline-link")
        self._add_button("New Chat", self.on_new_chat, side="right", bootstyle="success-outline-link")
        
        # History Toggle
        cb = ttk.Checkbutton(
            self,
            text="History",
            variable=self.show_history,
            command=self.on_history_toggle
        )
        cb.pack(side="right", padx=(0, 10))

    def _add_toggle(self, text: str, variable: tk.Variable):
        cb = ttk.Checkbutton(
            self, 
            text=text, 
            variable=variable
        )
        cb.pack(side="left", padx=(0, 10))

    def _add_button(self, text: str, command: Callable, side: str = "left", width: int = None, bootstyle: str = ""):
        btn = ttk.Button(
            self, 
            text=text, 
            command=command, 
            width=width
        )
        btn.pack(side=side, padx=(0, 5))

    def update_ref_sets(self, ref_sets: List[str]):
        self.ref_combo["values"] = ref_sets
