# -*- coding: utf-8 -*-
"""
parser_utils.py — Centralized JSON Parsing and Repair Utilities
-----------------------------------------------------------------
Robust parsing for LLM outputs that should be JSON but often include:
- Markdown fences ```json ... ```
- Extra pre/post text
- Trailing commas
- Python-literal dicts using single quotes
"""
from __future__ import annotations

import ast
import json
import re
from typing import Any, Dict, Optional


_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.IGNORECASE | re.DOTALL)


def _strip_code_fences(text: str) -> str:
    m = _FENCE_RE.search(text or "")
    return (m.group(1).strip() if m else (text or "").strip())


def _extract_balanced_object(text: str) -> Optional[str]:
    """
    Extract the first balanced JSON-like object from text using a small state machine.
    Handles nested braces and ignores braces inside quoted strings.
    """
    if not text:
        return None

    s = text
    start = s.find("{")
    if start == -1:
        return None

    depth = 0
    in_str = False
    esc = False
    quote = ""

    for i in range(start, len(s)):
        ch = s[i]

        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == quote:
                in_str = False
                quote = ""
            continue

        if ch in ("'", '"'):
            in_str = True
            quote = ch
            continue

        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return s[start : i + 1]

    return None


def _fix_trailing_commas(s: str) -> str:
    # Remove trailing commas before } or ]
    return re.sub(r",\s*([\]}])", r"\1", s)


def _try_json_loads(s: str) -> Optional[Any]:
    try:
        return json.loads(s)
    except Exception:
        return None


def _try_python_literal(s: str) -> Optional[Any]:
    """
    Salvage Python-literal dict/list (single quotes, True/False/None).
    ast.literal_eval is safe for literals.
    """
    try:
        obj = ast.literal_eval(s)
        if isinstance(obj, (dict, list)):
            return obj
        return None
    except Exception:
        return None


def robust_json_parse(content: str) -> Dict[str, Any]:
    """
    Central robust JSON parser with multiple repair strategies.
    Returns dict; if a list is parsed, it is wrapped under {"items": [...]}
    """
    if not content:
        return {}

    cleaned = _strip_code_fences(content)

    # If there's extra text, try extracting a balanced {...} object
    obj = _extract_balanced_object(cleaned)
    if obj:
        cleaned_obj = obj.strip()
    else:
        cleaned_obj = cleaned.strip()

    # Repair common JSON issues
    cleaned_obj = _fix_trailing_commas(cleaned_obj)

    # Strategy 1: strict JSON
    parsed = _try_json_loads(cleaned_obj)
    if parsed is not None:
        if isinstance(parsed, dict):
            return parsed
        if isinstance(parsed, list):
            return {"items": parsed}
        return {}

    # Strategy 2: sometimes the fenced content isn't the JSON object; try again on full text
    obj2 = _extract_balanced_object(content)
    if obj2:
        obj2 = _fix_trailing_commas(obj2)
        parsed2 = _try_json_loads(obj2)
        if parsed2 is not None:
            if isinstance(parsed2, dict):
                return parsed2
            if isinstance(parsed2, list):
                return {"items": parsed2}
            return {}

    # Strategy 3: Python-literal salvage (single quotes dict)
    salvaged = _try_python_literal(cleaned_obj)
    if salvaged is not None:
        if isinstance(salvaged, dict):
            return salvaged
        if isinstance(salvaged, list):
            return {"items": salvaged}

    return {}


def extract_json_block(text: str, marker: str) -> Optional[Dict[str, Any]]:
    """
    Extract a JSON block following a specific marker (e.g., TOOL_CALL_JSON:).
    Returns dict or None.
    """
    if not text or marker not in text:
        return None

    start_idx = text.find(marker) + len(marker)
    remaining = text[start_idx:].strip()

    candidate = _extract_balanced_object(remaining)
    if not candidate:
        return None

    parsed = robust_json_parse(candidate)
    return parsed or None


def parse_llm_response(content: str) -> Dict[str, Any]:
    """
    Parses a raw LLM response for plan, tool calls, and final JSON.
    """
    result: Dict[str, Any] = {"plan": None, "tool_call": None, "final_json": None}

    plan_match = re.search(r"<plan>(.*?)</plan>", content or "", re.DOTALL | re.IGNORECASE)
    if plan_match:
        result["plan"] = plan_match.group(1).strip()

    result["tool_call"] = extract_json_block(content or "", "TOOL_CALL_JSON:")
    result["final_json"] = extract_json_block(content or "", "FINAL_JSON:")

    return result


def extract_openai_content(raw: Any) -> str:
    """
    Extract content string from OpenAI-style response structure.
    """
    if isinstance(raw, str):
        return raw

    if isinstance(raw, dict):
        if "choices" in raw and raw["choices"]:
            return raw["choices"][0].get("message", {}).get("content", "") or ""
        if "content" in raw:
            return str(raw["content"] or "")

    return str(raw or "")
