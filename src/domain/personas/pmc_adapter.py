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

from __future__ import annotations
from typing import Any, Dict

class PMCAdapter:
    """
    Persona: Project Management Consultant (PMC).
    Emphasize milestones, dependencies, risks, and next actions with owners/dates.
    """

    def _discipline_focus(self, specialty: str) -> str:
        s = (specialty or "Project Manager").title()
        if s == "Arch":
            return "architectural milestones, design intent alignment, and occupancy permit coordination"
        if s == "Elec":
            return "electrical package interfaces, shutdowns, and approvals"
        if s == "Mech":
            return "MEP coordination, sequencing, and commissioning"
        if s == "Str":
            return "structural hold points, inspections, and long-lead items"
        if s == "Project Manager":
            return "master schedule alignment, critical path analysis, and cross-entity risk auditing"
        return "General project coordination. Include a one-line status and next-step owner with date."

    def system_prompt(self, role: str, specialty: str, project_json: str) -> str:
        persona = "Project Management Consultant (PMC)"
        if (specialty or "").title() == "Project Manager":
            persona = "PMC Project Manager (Multi-Entity Coordinator)"
            
        return (
            f"You are a {persona}. Your role is NOT just to plan, but to AUDIT and VERIFY.\n"
            "TIGHTEN OUTPUT TO THIS STRUCTURE:\n"
            "1. Status: [Green/Yellow/Red] One-line summary.\n"
            "2. Evidence: Key clauses/citations.\n"
            "3. Coordination Impacts: What other parties are affected.\n"
            "4. Next Actions: [Owner] [Task] [Due Date].\n"
            "Project Context (Reference):\n" + (project_json or "")[:8000]
        )


    def refine(self, user_query: str, specialty: str, project_context: Dict[str, Any]) -> str:
        q = (user_query or "").strip()
        if not q:
            return q
        return q + " Identify next steps, owners, and dates."

    def postprocess(self, llm_answer: str, specialty: str, project_context: Dict[str, Any]) -> str:
        return llm_answer or ""
