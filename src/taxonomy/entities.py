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
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, List

@dataclass
class BaseEntity:
    type: str
    value: str
    attributes: Dict[str, Any]
    page_index: Optional[int] = None
    confidence: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

def make_entities(objs: List[Dict[str, Any]]) -> List[BaseEntity]:
    out: List[BaseEntity] = []
    for o in objs or []:
        if not isinstance(o, dict):
            continue
        out.append(BaseEntity(
            type=str(o.get("type") or "unknown"),
            value=str(o.get("value") or ""),
            attributes=dict(o.get("attributes") or {}),
            page_index=o.get("page_index"),
            confidence=o.get("confidence"),
        ))
    return out
