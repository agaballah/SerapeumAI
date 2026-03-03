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
document_report_generator — minimal Markdown export used by ReportManager.
No schema changes; reads via existing DatabaseManager APIs.
"""

from __future__ import annotations
from typing import Any
import os

def generate_markdown(db: Any, project_id: str, out_dir: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"project_{project_id}_report.md")

    docs = db.list_documents(limit=100000, offset=0) or []
    lines = [f"# Project Report — {project_id}", ""]

    for d in docs:
        did = d.get("doc_id") or d.get("id")  # tolerate both shapes
        if not did:
            continue
        meta = d.get("meta") or {}
        file_name = meta.get("file_name") or meta.get("name") or ""
        lines.append(f"## {file_name}  \n`doc_id`: {did}")
        a = db.get_analysis(did) or {}
        summary = a.get("summary") or ""
        ents = a.get("entities") or []
        rels = a.get("relationships") or []
        lines.append(f"**Summary:** {summary}")
        lines.append(f"- Entities: {len(ents)}")
        lines.append(f"- Relationships: {len(rels)}")
        lines.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path
