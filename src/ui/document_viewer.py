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
DocumentViewer — Viewer for documents + pages under new DB-A schema.

Reads:
    • documents table
    • pages table
    • captions via db.get_page_caption(doc_id, page_index)
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from src.infra.persistence.database_manager import DatabaseManager


class DocumentViewer(ttk.Frame):
    """Simple Viewer Panel"""

    def __init__(self, master, *, db: DatabaseManager):
        super().__init__(master)
        self.db = db

        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # LEFT: Docs list
        left = ttk.Frame(self)
        left.grid(row=0, column=0, sticky="nsw")
        ttk.Label(left, text="Documents").pack(anchor="w", padx=6, pady=6)

        self.lst_docs = tk.Listbox(left, width=40)
        self.lst_docs.pack(fill="y", padx=6)
        self.lst_docs.bind("<<ListboxSelect>>", lambda e: self._on_doc())

        # RIGHT: Pages + metadata
        right = ttk.Frame(self)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        self.lbl_doc = ttk.Label(right, text="(no document)")
        self.lbl_doc.grid(row=0, column=0, sticky="w", padx=6, pady=6)

        body = ttk.Panedwindow(right, orient=tk.HORIZONTAL)
        body.grid(row=1, column=0, sticky="nsew")

        # Pages list
        self.lst_pages = tk.Listbox(body, width=20)
        self.lst_pages.bind("<<ListboxSelect>>", lambda e: self._on_page())
        body.add(self.lst_pages, weight=0)

        # Details area
        detail = ttk.Frame(body)
        detail.columnconfigure(0, weight=1)
        detail.rowconfigure(0, weight=1)
        body.add(detail, weight=1)

        self.txt_meta = tk.Text(detail, wrap="word")
        self.txt_meta.grid(row=0, column=0, sticky="nsew")

        self.refresh()

    # ------------------------------------------------------------------ #

    def refresh(self):
        self.lst_docs.delete(0, "end")
        docs = self.db.list_documents(limit=100000, offset=0) or []
        self._docs = docs
        for d in docs:
            self.lst_docs.insert("end", f"{d['file_name']}")

    # ------------------------------------------------------------------ #

    def _on_doc(self):
        sel = self.lst_docs.curselection()
        if not sel:
            return
        idx = sel[0]
        d = self._docs[idx]
        did = d["doc_id"]

        self.lbl_doc.configure(text=d["file_name"])

        pages = self.db.get_pages(did) or []
        self._pages = pages

        self.lst_pages.delete(0, "end")
        for p in pages:
            self.lst_pages.insert("end", f"Page {p['page_index']}")

        self._set_meta("(select page)")

    # ------------------------------------------------------------------ #

    def _on_page(self):
        sel_doc = self.lst_docs.curselection()
        sel_page = self.lst_pages.curselection()
        if not (sel_doc and sel_page):
            return

        d = self._docs[sel_doc[0]]
        did = d["doc_id"]
        page_idx = int(self._pages[sel_page[0]]["page_index"])

        # fetch caption
        cap = self.db.get_page_caption(did, page_idx) or {}

        # fetch page meta
        p = self._pages[sel_page[0]]

        meta = [
            f"Page: {page_idx}",
            f"Width: {p.get('width')}  Height: {p.get('height')}",
            f"OCR chars: {len(p.get('ocr_text',''))}",
            f"Quality: {p.get('quality')}",
            "",
            "Caption JSON:",
            json_dumps(cap)
        ]

        self._set_meta("\n".join(meta))

    # ------------------------------------------------------------------ #

    def _set_meta(self, text: str):
        self.txt_meta.configure(state="normal")
        self.txt_meta.delete("1.0", "end")
        self.txt_meta.insert("end", text)
        self.txt_meta.configure(state="disabled")


# ---------------------------------------------------------------------- #

def json_dumps(obj: Any) -> str:
    try:
        import json
        return json.dumps(obj, ensure_ascii=False, indent=2)
    except Exception:
        return str(obj)
