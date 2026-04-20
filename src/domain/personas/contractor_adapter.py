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

class ContractorAdapter:
    """
    Persona: Contractor.
    Emphasize constructability, sequencing, RFIs, risks, and FIDIC-aware claims phrasing.
    """

    def _discipline_focus(self, specialty: str) -> str:
        s = (specialty or "Project Manager").title()
        if s == "Arch":
            return "architectural detailing, envelope constructability, materials coordination, and finishing benchmarks"
        if s == "Elec":
            return "electrical installation sequencing, panel schedules, and site safety coordination"
        if s == "Mech":
            return "MEP routing, equipment placement, access clearances, and commissioning steps"
        if s == "Str":
            return "formwork/shoring, concrete pours, steel erection sequencing, and tolerances"
        if s == "Project Manager":
            return "production sequencing, subcontractor coordination, and constructability risk management"
        return "General construction execution details, required approvals, and key risks."

    def system_prompt(self, role: str, specialty: str, project_json: str) -> str:
        persona = "Contractor"
        if (specialty or "").title() == "Project Manager":
            persona = "Contractor Project Manager"
            
        return (
            f"You are a {persona}. Your role is EXECUTION and PRECISION.\n"
            "Focus on constructability, site constraints, and sequencing.\n"
            "Project Context (Reference):\n" + (project_json or "")[:8000]
        )


    def refine(self, user_query: str, specialty: str, project_context: Dict[str, Any]) -> str:
        q = (user_query or "").strip()
        if not q:
            return q
        return q + " Focus on constructability, risks, and execution steps."

    def postprocess(self, llm_answer: str, specialty: str, project_context: Dict[str, Any]) -> str:
        return llm_answer or ""
