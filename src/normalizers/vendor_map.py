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
vendor_map — lightweight vendor/product name normalizer.

Design
------
- No external deps.
- Normalizes case, punctuation, company suffixes, dotted initials, and whitespace.
- Maps many variants to a canonical brand name via an alias table.
"""

from __future__ import annotations

import re
from typing import Dict

_SUFFIX_RE = re.compile(r"\b(ltd|l\.?l\.?c|inc|co\.?|corp|gmbh|ag|sa|se|plc)\b\.?", re.IGNORECASE)
_PUNCT_RE = re.compile(r"[^A-Za-z0-9]+")

# Aliases keyed by normalized form (post-clean). Values are canonical labels to show in UI.
_ALIASES: Dict[str, str] = {
    # ABB
    "abb": "ABB",
    "abbgroup": "ABB",
    "abbspa": "ABB",
    # Schneider
    "schneiderelectric": "Schneider Electric",
    "schneider": "Schneider Electric",
    "schneiderelectricse": "Schneider Electric",
    # Siemens
    "siemens": "Siemens",
    "siemensag": "Siemens",
    # Honeywell
    "honeywell": "Honeywell",
    "honeywellinternational": "Honeywell",
    # Daikin
    "daikin": "Daikin",
    "daikinindustries": "Daikin",
    # Carrier
    "carrier": "Carrier",
    "carrierglobal": "Carrier",
    # Johnson Controls
    "johnsoncontrols": "Johnson Controls",
    "jci": "Johnson Controls",
    # Eaton
    "eaton": "Eaton",
    "eatoncorp": "Eaton",
    # Legrand
    "legrand": "Legrand",
    # Leviton
    "leviton": "Leviton",
    # Midea
    "midea": "Midea",
    # Trane
    "trane": "Trane",
    # GE
    "ge": "GE",
    "generalelectric": "GE",
}


def _collapse_initials(s: str) -> str:
    # "A.B.B." -> "ABB", "A B B" -> "ABB"
    return re.sub(r"[\W_]+", "", s).upper()


def _clean(s: str) -> str:
    s = (s or "").strip()
    if not s:
        return ""
    # Remove company suffixes
    s = _SUFFIX_RE.sub("", s)
    # Collapse whitespace/punctuations
    s = re.sub(r"[&]", "and", s, flags=re.IGNORECASE)
    s = re.sub(r"\s+", " ", s)
    s = s.strip()
    # Handle dotted initials
    if re.fullmatch(r"(?:[A-Za-z]\W*){2,}", s):
        return _collapse_initials(s)
    # Remove remaining punctuation and spaces to form alias key
    return _PUNCT_RE.sub("", s).lower()


def normalize_vendor(name: str) -> str:
    """
    Normalize a vendor/manufacturer string to a canonical brand name.
    If we cannot map confidently, return the cleaned original (title/case preserved by caller).
    """
    if not isinstance(name, str):
        return ""
    raw = name.strip()
    if not raw:
        return ""
    key = _clean(raw)
    # initials special case (e.g., "A.B.B.")
    if len(key) <= 6 and key.isupper():
        key = key.lower()
    return _ALIASES.get(key, raw)
