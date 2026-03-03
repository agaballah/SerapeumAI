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
plugin_registry — lightweight plugin system for analysis/enrichment passes.

Plugin interface (duck-typed)
-----------------------------
A plugin is any object with:
  - id: str
  - name: str
  - run(db, *, project_id: str, doc_id: str | None = None, **kwargs) -> dict

Registration
------------
- Programmatic: registry.register(plugin_instance)
- Declarative  : registry.enable("<id>") / disable("<id>")

Storage (KV)
------------
plugins:index               -> [ {id,name,enabled}, ... ]
plugin:cfg:<id>            -> {enabled: bool, meta: {...}}

Notes
-----
- This is intentionally small. Advanced discovery (entry points, dynamic import)
  can be added later without breaking the API.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.infra.persistence.database_manager import DatabaseManager


class PluginRegistry:
    def __init__(self, db: DatabaseManager) -> None:
        self.db = db
        self._plugins: Dict[str, Any] = {}

    # -------------------------- Registration ------------------------------ #

    def register(self, plugin: Any) -> None:
        pid = getattr(plugin, "id", None)
        name = getattr(plugin, "name", None)
        if not pid or not isinstance(pid, str):
            raise ValueError("plugin must expose string attribute 'id'")
        if not name or not isinstance(name, str):
            name = pid

        self._plugins[pid] = plugin

        idx = self.db.get_kv("plugins:index") or []
        if not isinstance(idx, list):
            idx = []
        # upsert visible row; default enabled=False unless previously enabled
        old = next((x for x in idx if x.get("id") == pid), None)
        enabled = bool(old.get("enabled")) if isinstance(old, dict) else False
        rec = {"id": pid, "name": name, "enabled": enabled}
        idx = [x for x in idx if x.get("id") != pid]
        idx.append(rec)
        self.db.set_kv("plugins:index", idx)

        # ensure cfg row exists
        cfg = self.db.get_kv(f"plugin:cfg:{pid}") or {}
        if not isinstance(cfg, dict):
            cfg = {}
        if "enabled" not in cfg:
            cfg["enabled"] = enabled
        self.db.set_kv(f"plugin:cfg:{pid}", cfg)

    def list_plugins(self) -> List[Dict[str, Any]]:
        idx = self.db.get_kv("plugins:index") or []
        return [x for x in idx if isinstance(x, dict)]

    def enable(self, plugin_id: str) -> None:
        self._set_enabled(plugin_id, True)

    def disable(self, plugin_id: str) -> None:
        self._set_enabled(plugin_id, False)

    def _set_enabled(self, plugin_id: str, enabled: bool) -> None:
        idx = self.db.get_kv("plugins:index") or []
        if isinstance(idx, list):
            for x in idx:
                if x.get("id") == plugin_id:
                    x["enabled"] = bool(enabled)
            self.db.set_kv("plugins:index", idx)

        cfg = self.db.get_kv(f"plugin:cfg:{plugin_id}") or {}
        if not isinstance(cfg, dict):
            cfg = {}
        cfg["enabled"] = bool(enabled)
        self.db.set_kv(f"plugin:cfg:{plugin_id}", cfg)

    # ------------------------------- Run ---------------------------------- #

    def run(self, plugin_id: str, *, project_id: str, doc_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            raise KeyError(f"plugin not registered: {plugin_id}")

        cfg = self.db.get_kv(f"plugin:cfg:{plugin_id}") or {}
        if isinstance(cfg, dict) and not cfg.get("enabled", False):
            return {"ok": False, "reason": "disabled"}

        if not hasattr(plugin, "run") or not callable(plugin.run):
            raise TypeError(f"plugin '{plugin_id}' has no callable run()")

        # actual call
        try:
            return plugin.run(self.db, project_id=project_id, doc_id=doc_id, **kwargs)
        except Exception as e:
            return {"ok": False, "error": f"{type(e).__name__}: {e}"}
