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
project_service.py — Project Manager (DatabaseManager v3 Compatible)
"""

from __future__ import annotations

import os
import hashlib
from typing import Dict, Any, Optional


class ProjectService:
    def __init__(self, *, db, doc_service) -> None:
        self.db = db
        self.docs = doc_service

    # ------------------------------------------------------------------
    # PROJECT RECORD CREATION
    # ------------------------------------------------------------------

    def create_or_get_project_by_root(
        self,
        *,
        root: str,
        name: Optional[str] = None
    ) -> Dict[str, Any]:

        root_abs = os.path.abspath(root)
        pid = self._stable_id(root_abs)
        display_name = name or os.path.basename(root_abs) or "Project"

        # NEW API — DatabaseManager v3
        self.db.upsert_project(project_id=pid, name=display_name, root=root_abs)

        return {
            "id": pid,
            "name": display_name,
            "root": root_abs,
        }

    # ------------------------------------------------------------------
    # INGEST WRAPPER
    # ------------------------------------------------------------------

    def ingest_project(
        self,
        *,
        project_id: str,
        root: str,
        recursive: bool = True,
        force: bool = False,
        on_progress=None,
        max_chars: int = 2_000_000,
    ) -> Dict[str, Any]:
        """
        Delegate to DocumentService (already upgraded)
        """
        return self.docs.ingest_files_from_root(
            project_id=project_id,
            root=root,
            recursive=recursive,
            force=force,
            on_progress=on_progress,
            max_chars=max_chars,
        )

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    @staticmethod
    def _stable_id(s: str) -> str:
        h = hashlib.sha1(s.encode("utf-8"), usedforsecurity=False).hexdigest()[:16]
        return f"proj-{h}"
