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

class TechnicalConsultantAdapter:
    """
    Persona: Technical Consultant.
    Emphasize code/spec compliance, technical consistency, and cross-document evidence.
    """

    def _discipline_focus(self, specialty: str) -> str:
        s = (specialty or "Project Manager").title()
        if s == "Arch":
            return "SBC/IBC/ADA and specification conformance"
        if s == "Elec":
            return "NFPA 70, protection coordination, short-circuit levels, and grounding/bonding"
        if s == "Mech":
            return "ASHRAE, ventilation rates, plant sizing, and controls integration"
        if s == "Str":
            return "IBC/SBC checks, load paths, ductility/lateral systems"
        if s == "Project Manager":
            return "risk mitigation, inter-disciplinary coordination, and technical milestone alignment"
        return "standards conformance and technical consistency"

    def system_prompt(self, role: str, specialty: str, project_json: str) -> str:
        persona = "Technical Consultant"
        if (specialty or "").title() == "Project Manager":
            persona = "Consultant Project Manager (Technical PMC)"
            
        return (
            f"You are a {persona}. Your role is CODE AUTHORITY and SPECIFICATION COMPLIANCE.\n"
            "If the user asks 'where does the spec say', prioritize LOCAL evidence; do NOT use web unless explicitly asked for compliance verification.\n"
            "Role Focus: " + self._discipline_focus(specialty) + "\n"
            "Project Context (Reference):\n" + (project_json or "")[:8000]
        )


    def refine(self, user_query: str, specialty: str, project_context: Dict[str, Any]) -> str:
        q = (user_query or "").strip()
        if not q:
            return q
        return q + " If applicable, cite specific clauses and drawing/spec locations."

    def postprocess(self, llm_answer: str, specialty: str, project_context: Dict[str, Any]) -> str:
        return llm_answer or ""
