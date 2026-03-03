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
RoleManager — strict router for Chat heroes.

Roles: Contractor, Owner, Technical Consultant, PMC
Disciplines: Arch, Elec, Mech, Str, Project Manager
"""

from __future__ import annotations
from typing import Any, Optional

from src.domain.personas.contractor_adapter import ContractorAdapter
from src.domain.personas.owner_adapter import OwnerAdapter
from src.domain.personas.technical_consultant_adapter import TechnicalConsultantAdapter
from src.domain.personas.pmc_adapter import PMCAdapter

_ALLOWED_ROLES = {
    "Contractor": ContractorAdapter,
    "Owner": OwnerAdapter,
    "Technical Consultant": TechnicalConsultantAdapter,
    "PMC": PMCAdapter,
}

_ALLOWED_SPECIALTIES = {"Arch", "Elec", "Mech", "Str", "Project Manager"}


class RoleManager:
    def __init__(self, db: Any) -> None:
        self.db = db

    def get_adapter(self, role: str):
        role = (role or "").strip()
        cls = _ALLOWED_ROLES.get(role)
        if not cls:
            # Strict routing: no Architect/Engineer back-compat
            raise ValueError(
                f"Unsupported role: {role!r}. Allowed: {', '.join(_ALLOWED_ROLES.keys())}"
            )
        return cls()

    def get_persona_name(self, role: str, specialty: str) -> str:
        """Helper to get a combined persona name for UI consistency."""
        r = (role or "PMC").strip()
        s = self.validate_specialty(specialty)
        
        # Mapping for natural sounding names
        if r == "Technical Consultant" and s == "Project Manager":
            return "Consultant PM"
        if r == "Technical Consultant":
            return f"Consultant {s}"
        if s == "Project Manager":
            return f"{r} PM"
        
        return f"{r} {s}"

    def get_global_research_policy(self) -> str:
        """Centralized mandatory research lifecycle rules."""
        return (
            "MANDATORY RESEARCH LIFECYCLE (UNLEASHED):\n"
            "1. PLAN: Start every response with a '<plan>' tag (steps + tool sequence).\n"
            "2. RESEARCH-FIRST MANDATE: If the query asks for 'exact mentions', 'where', or specific 'clauses', you MUST use research tools (search_headings, search_pages).\n"
            "3. NO FILLER: If a tool is required, output ONLY the <plan> and the JSON tool call.\n"
            "4. ESCAPE HATCH: If search tools return no results after 3 keyword variations, STOP and report missing data.\n"
        )

    def validate_specialty(self, specialty: Optional[str]) -> str:
        s = (specialty or "").strip().title()
        # Ensure 'Project Manager' is not 'Project Manager' (titled) if it has two words, 
        # but the set has "Project Manager". title() makes it "Project Manager".
        if s.lower() == "project manager":
            return "Project Manager"
            
        aliases = {
            "Electrical": "Elec",
            "Mechanical": "Mech",
            "Structural": "Str",
            "Architecture": "Arch",
            "Architectural": "Arch",
        }
        s = aliases.get(s, s)
        return s if s in _ALLOWED_SPECIALTIES else "Project Manager"

