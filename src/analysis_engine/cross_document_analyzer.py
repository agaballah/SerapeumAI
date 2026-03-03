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
cross_document_analyzer.py — Normalized cross-document linking
---------------------------------------------------------------

Goals:
    • Merge entities across all documents
    • Detect duplicates (e.g., repeated room names / equipment tags)
    • Detect cross-doc inconsistencies
    • Provide shared entity map for UI + compliance

Output stored in KV keys:
    analysis:entities:<project_id>
    analysis:relationships:<project_id>
"""

from __future__ import annotations
from typing import Any, Dict, List, Tuple
from src.infra.persistence.database_manager import DatabaseManager


class CrossDocumentAnalyzer:
    def __init__(self, db: DatabaseManager):
        self.db = db

    # ------------------------------------------------------------------ #
    def link_project(self, project_id: str) -> Dict[str, Any]:
        """
        Produces:
            {
                "entities": {doc_id: [...entities...]},
                "relationships": {doc_id: [...rels...]},
                "duplicates": [...],
                "conflicts": [...]
            }
        """
        docs = self.db.list_documents(project_id=project_id, limit=100000, offset=0) or []
        ent_map: Dict[str, List[Dict[str, Any]]] = {}
        rel_map: Dict[str, List[Dict[str, Any]]] = {}

        # Flatten all entities and relationships
        for d in docs:
            did = d["doc_id"]
            a = self.db.get_analysis(did) or {}
            ent_map[did] = a.get("entities", [])
            rel_map[did] = a.get("relationships", [])

        # Cross-doc linking
        dups, conflicts = self._detect_duplicates(ent_map)

        # Persist globally
        self.db.set_kv(f"analysis:entities:{project_id}", ent_map)
        self.db.set_kv(f"analysis:relationships:{project_id}", rel_map)

        return {
            "entities": ent_map,
            "relationships": rel_map,
            "duplicates": dups,
            "conflicts": conflicts,
        }

    # ------------------------------------------------------------------ #
    def _detect_duplicates(
        self,
        ent_map: Dict[str, List[Dict[str, Any]]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:

        """
        Rules:
            duplicate = same (type, value), different docs
            conflict  = same (type, value), contradicting attributes
        """
        seen: Dict[Tuple[str, str], List[Tuple[str, Dict[str, Any]]]] = {}
        for did, ents in ent_map.items():
            for e in ents:
                key = (e.get("type", ""), e.get("value", ""))
                seen.setdefault(key, []).append((did, e))

        dups = []
        conflicts = []

        for (etype, val), items in seen.items():
            if len(items) <= 1:
                continue

            doc_ids = [i[0] for i in items]
            dups.append({
                "type": etype,
                "value": val,
                "documents": doc_ids
            })

            # Conflict check
            base_attr = items[0][1].get("attributes") or {}
            for _, ent in items[1:]:
                attrs = ent.get("attributes") or {}
                if attrs != base_attr:
                    conflicts.append({
                        "type": etype,
                        "value": val,
                        "documents": doc_ids,
                        "base_attr": base_attr,
                        "conflict_attr": attrs,
                    })
                    break

        return dups, conflicts
