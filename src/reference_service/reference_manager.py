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
reference_manager — manages reference corpora used for grounding, citations, and lookups.

Concepts
--------
ReferenceSet: a named collection of items (documents or external pointers) the user
may switch between when chatting/analyzing.

Storage
-------
- KV: reference:sets:index               -> [ {id,name,created,meta}, ... ]
- KV: reference:set:<id>                 -> { id, name, items: [ {type, doc_id|href|path, title, tags, meta}, ... ] }
- KV: reference:active:<project_id>      -> <set_id>  (which set is active for a project)

Item types (minimal)
--------------------
- "doc"     : internal document; requires doc_id
- "external": any URL or path; requires href or path

Public API
----------
ReferenceManager(db)
  - list_sets() -> list[dict]
  - get_set(set_id) -> dict|None
  - create_set(name, items=None, meta=None) -> dict
  - add_items(set_id, items) -> dict
  - remove_item(set_id, predicate) -> dict
  - set_active(project_id, set_id) -> None
  - get_active(project_id) -> dict|None
  - build_context(set_id, *, max_chars=200_000) -> str  # concatenated text of doc items (for quick contexts)
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Sequence

from src.infra.persistence.database_manager import DatabaseManager


class ReferenceManager:
    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    # ------------------------------ Sets --------------------------------- #

    def list_sets(self) -> List[Dict[str, Any]]:
        idx = self.db.get_kv("reference:sets:index") or []
        return [x for x in idx if isinstance(x, dict)]

    def get_set(self, set_id: str) -> Optional[Dict[str, Any]]:
        s = self.db.get_kv(f"reference:set:{set_id}") or None
        return s if isinstance(s, dict) else None

    def create_set(self, name: str, *, items: Optional[Sequence[Dict[str, Any]]] = None, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        set_id = self._new_id(name)
        rec = {"id": set_id, "name": name, "created": int(time.time()), "meta": meta or {}, "items": list(items or [])}
        self.db.set_kv(f"reference:set:{set_id}", rec)

        idx = self.list_sets()
        idx = [x for x in idx if x.get("id") != set_id]
        idx.append({"id": set_id, "name": name, "created": rec["created"], "meta": rec["meta"]})
        self.db.set_kv("reference:sets:index", idx)
        return rec

    def add_items(self, set_id: str, items: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
        s = self.get_set(set_id) or {"id": set_id, "name": set_id, "created": int(time.time()), "meta": {}, "items": []}
        cur = list(s.get("items") or [])
        for it in items:
            if isinstance(it, dict):
                cur.append(it)
        s["items"] = cur
        self.db.set_kv(f"reference:set:{set_id}", s)
        return s

    def remove_item(self, set_id: str, predicate) -> Dict[str, Any]:
        """
        predicate: callable(item_dict) -> bool; items returning True are REMOVED
        """
        s = self.get_set(set_id) or {"id": set_id, "name": set_id, "created": int(time.time()), "meta": {}, "items": []}
        cur = list(s.get("items") or [])
        keep = [it for it in cur if not predicate(it)]
        s["items"] = keep
        self.db.set_kv(f"reference:set:{set_id}", s)
        return s

    # ------------------------------ Active -------------------------------- #

    def set_active(self, project_id: str, set_id: str) -> None:
        self.db.set_kv(f"reference:active:{project_id}", set_id)

    def get_active(self, project_id: str) -> Optional[Dict[str, Any]]:
        set_id = self.db.get_kv(f"reference:active:{project_id}") or None
        if not isinstance(set_id, str):
            return None
        return self.get_set(set_id)

    # ------------------------------ Context -------------------------------- #

    def build_context(self, set_id: str, *, max_chars: int = 200_000) -> str:
        """
        Concatenate text from doc items up to max_chars. Best-effort if docs missing.
        """
        s = self.get_set(set_id)
        if not s:
            return ""
        out = []
        total = 0
        for it in s.get("items") or []:
            if not isinstance(it, dict):
                continue
            if it.get("type") == "doc":
                doc_id = str(it.get("doc_id") or "")
                if not doc_id:
                    continue
                payload = self.db.get_document_payload(doc_id)
                txt = payload.get("text") or ""
                if not txt:
                    continue
                left = max(0, int(max_chars) - total)
                if left <= 0:
                    break
                frag = txt[:left]
                out.append(frag)
                total += len(frag)
        return "\n\n".join(out)

    # ------------------------------ Utils ---------------------------------- #

    def _new_id(self, name: str) -> str:
        import hashlib
        # SHA1 used for ID generation only, not cryptography
        h = hashlib.sha1(usedforsecurity=False)
        h.update(f"{name}:{time.time()}".encode("utf-8", errors="ignore"))
        return h.hexdigest()[:16]
