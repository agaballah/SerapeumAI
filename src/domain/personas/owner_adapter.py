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

class OwnerAdapter:
    """
    Persona: Owner.
    Emphasize cost, schedule, risk, approvals, and decision clarity.
    """

    def _discipline_focus(self, specialty: str) -> str:
        s = (specialty or "Project Manager").title()
        if s == "Arch":
            return "architectural vision, aesthetic quality, and occupancy comfort impact"
        if s == "Elec":
            return "electrical capacity, resilience, safety, and cost impact"
        if s == "Mech":
            return "energy efficiency, maintainability, and lifecycle cost"
        if s == "Str":
            return "structural safety, durability, and change-order risk"
        if s == "Project Manager":
            return "budget control, stakeholder reporting, and strategic risk assessment"
        return "General project governance, cost/schedule impact, and required approvals."

    def system_prompt(self, role: str, specialty: str, project_json: str) -> str:
        persona = "Owner"
        if (specialty or "").title() == "Project Manager":
            persona = "Owner Representative / Project Manager"
            
        return (
            f"You are an {persona}. Your role is CONSTRAINT SETTING and STRATEGIC VALUE.\n"
            "Default to a 'Decision-Ready' framing: clearly state if action is needed.\n"
            "STRUCTURE YOUR FINAL ANSWER WITH:\n"
            "- Decision Required (Yes/No)\n"
            "- Options / Evidence\n"
            "- Risk / Cost Impact\n"
            "Project Context (Reference):\n" + (project_json or "")[:8000]
        )


    def refine(self, user_query: str, specialty: str, project_context: Dict[str, Any]) -> str:
        q = (user_query or "").strip()
        if not q:
            return q
        return q + " Highlight cost/schedule impacts and decision points."

    def postprocess(self, llm_answer: str, specialty: str, project_context: Dict[str, Any]) -> str:
        return llm_answer or ""
