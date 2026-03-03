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
report_manager — composes and persists structured analysis reports.

Storage
-------
- KV: report:index:<project_id>          -> [ {id,title,created,tags}, ... ]
- KV: report:<id>                        -> {id, project_id, title, sections:[{title, body, meta}], created, tags, meta}
- KV: report:latest:<project_id>:<tag>   -> <report_id>  (fast pointer for UI)

Public API
----------
ReportManager(db)
  - create_report(project_id, title, sections, tags=None, meta=None) -> dict
  - update_report(report_id, **fields) -> dict
  - get_report(report_id) -> dict|None
  - list_reports(project_id, tag=None) -> list[dict]
  - delete_report(report_id) -> None
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Sequence

from src.infra.persistence.database_manager import DatabaseManager


class ReportManager:
    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    # ---------------------------- CRUD ------------------------------------ #

    def create_report(
        self,
        *,
        project_id: str,
        title: str,
        sections: Sequence[Dict[str, Any]],
        tags: Optional[Sequence[str]] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        rid = self._new_id(project_id, title)
        rec = {
            "id": rid,
            "project_id": project_id,
            "title": title,
            "sections": list(sections or []),
            "tags": list(tags or []),
            "meta": meta or {},
            "created": int(time.time()),
        }
        self.db.set_kv(f"report:{rid}", rec)

        idx_key = f"report:index:{project_id}"
        idx = self.db.get_kv(idx_key) or []
        if not isinstance(idx, list):
            idx = []
        idx = [x for x in idx if x.get("id") != rid]
        idx.append({"id": rid, "title": title, "created": rec["created"], "tags": rec["tags"]})
        self.db.set_kv(idx_key, idx)

        for t in rec["tags"]:
            self.db.set_kv(f"report:latest:{project_id}:{t}", rid)

        return rec

    def update_report(self, report_id: str, **fields) -> Optional[Dict[str, Any]]:
        rec = self.get_report(report_id)
        if not rec:
            return None
        for k, v in fields.items():
            if k in ("title", "sections", "tags", "meta"):
                rec[k] = v
        self.db.set_kv(f"report:{report_id}", rec)
        # update index entry
        idx_key = f"report:index:{rec['project_id']}"
        idx = self.db.get_kv(idx_key) or []
        if isinstance(idx, list):
            for x in idx:
                if x.get("id") == report_id:
                    x["title"] = rec["title"]
                    x["tags"] = rec.get("tags", [])
            self.db.set_kv(idx_key, idx)
        return rec

    def get_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        rec = self.db.get_kv(f"report:{report_id}") or None
        return rec if isinstance(rec, dict) else None

    def list_reports(self, project_id: str, *, tag: Optional[str] = None) -> List[Dict[str, Any]]:
        idx = self.db.get_kv(f"report:index:{project_id}") or []
        rows = [x for x in idx if isinstance(x, dict)]
        if tag:
            rows = [x for x in rows if tag in (x.get("tags") or [])]
        # newest first
        rows.sort(key=lambda r: r.get("created", 0), reverse=True)
        return rows

    def delete_report(self, report_id: str) -> None:
        rec = self.get_report(report_id)
        if not rec:
            return
        self.db.set_kv(f"report:{report_id}", {"_deleted": True, "_ts": int(time.time())})
        idx_key = f"report:index:{rec['project_id']}"
        idx = self.db.get_kv(idx_key) or []
        if isinstance(idx, list):
            idx = [x for x in idx if x.get("id") != report_id]
            self.db.set_kv(idx_key, idx)

    # ---------------------------- Utils ----------------------------------- #

    def _new_id(self, project_id: str, title: str) -> str:
        import hashlib
        # SHA1 used for ID generation only, not cryptography
        h = hashlib.sha1(usedforsecurity=False)
        h.update(f"{project_id}:{title}:{time.time()}".encode("utf-8", errors="ignore"))
        return h.hexdigest()[:20]
