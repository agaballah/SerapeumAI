# -*- coding: utf-8 -*-
"""
conflict_detector.py — Cross-source conflict detection for engineering facts.

Detects when two or more facts share the same subject but have different values.
Design principles:
  - Failure-isolated: conflicts never invalidate existing facts
  - Conservative: only flags genuine disagreements, not formatting differences
  - Additive: new table, no schema changes to existing tables
  - Human-required: conflicts are OPEN until a human resolves them
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class FactConflict:
    """Represents a detected conflict between facts."""
    conflict_id: str
    project_id: str
    subject_id: str
    fact_type: str
    source_count: int
    values_json: str  # JSON list of {fact_id, value, source, confidence}
    conflict_type: str  # VALUE | REVISION | DISCIPLINE
    resolution: str = "UNRESOLVED"  # UNRESOLVED | REVIEWED | RESOLVED
    resolved_by: Optional[str] = None
    resolved_at: Optional[int] = None
    created_at: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conflict_id": self.conflict_id,
            "project_id": self.project_id,
            "subject_id": self.subject_id,
            "fact_type": self.fact_type,
            "source_count": self.source_count,
            "values": json.loads(self.values_json),
            "conflict_type": self.conflict_type,
            "resolution": self.resolution,
            "resolved_by": self.resolved_by,
            "resolved_at": self.resolved_at,
            "created_at": self.created_at,
        }


def _normalize_value(value: Any) -> str:
    """Normalize a value for comparison. Returns string representation."""
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, (list, dict)):
        return json.dumps(value, sort_keys=True, default=str)
    return str(value).strip()


def _values_are_equivalent(v1: Any, v2: Any) -> bool:
    """Check if two values represent the same semantic content."""
    n1 = _normalize_value(v1)
    n2 = _normalize_value(v2)
    if not n1 or not n2:
        return n1 == n2
    # Case-insensitive text comparison
    if n1.lower() == n2.lower():
        return True
    # Numeric tolerance (floats that round to same int)
    try:
        f1, f2 = float(n1), float(n2)
        if abs(f1 - f2) < 0.001:
            return True
    except (ValueError, TypeError):
        pass
    return False


def _detect_conflicts_in_batch(
    facts: List[Dict[str, Any]],
    project_id: str,
) -> List[FactConflict]:
    """
    Group facts by (subject_id, fact_type) and detect value conflicts.

    A conflict exists when 2+ facts have the SAME subject+type but DIFFERENT values.
    Formatting-only differences are ignored (false positive control).
    """
    # Group by (subject_id, fact_type)
    groups: Dict[Tuple[str, str], List[Dict]] = {}
    for fact in facts:
        key = (fact.get("subject_id", ""), fact.get("fact_type", ""))
        if key[0] and key[1]:
            groups.setdefault(key, []).append(fact)

    conflicts = []
    for (subject_id, fact_type), group in groups.items():
        if len(group) < 2:
            continue  # Need at least 2 facts to have a conflict

        # Check for value differences (with normalization)
        unique_values = {}
        for fact in group:
            val = fact.get("value")
            val_key = _normalize_value(val)
            if val_key not in unique_values:
                unique_values[val_key] = {
                    "value": val,
                    "facts": [],
                }
            unique_values[val_key]["facts"].append(fact)

        if len(unique_values) <= 1:
            continue  # All same value, no conflict

        # Build conflict record
        values_list = []
        for val_key, bucket in unique_values.items():
            for f in bucket["facts"]:
                values_list.append({
                    "fact_id": f["fact_id"],
                    "value": f.get("value"),
                    "status": f.get("status"),
                    "confidence": f.get("confidence", 1.0),
                    "method_id": f.get("method_id", "unknown"),
                    "inputs": f.get("inputs", []),
                })

        # Generate deterministic conflict ID
        cid_data = f"{project_id}:{subject_id}:{fact_type}"
        conflict_id = "conflict_" + hashlib.sha256(cid_data.encode()).hexdigest()[:12]

        conflicts.append(FactConflict(
            conflict_id=conflict_id,
            project_id=project_id,
            subject_id=subject_id,
            fact_type=fact_type,
            source_count=len(group),
            values_json=json.dumps(values_list, default=str),
            conflict_type="VALUE",
            created_at=0,  # Set by caller
        ))

    return conflicts


def detect_and_store_conflicts(
    db,  # DatabaseManager
    project_id: str,
    facts: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Main entry point: detect conflicts and store in database.

    This function is failure-isolated: if it raises, the caller should catch
    and log but NOT abort fact persistence.

    Returns list of conflict dicts (for UI display).
    """
    try:
        conflicts = _detect_conflicts_in_batch(facts, project_id)
        if not conflicts:
            return []

        now = db._ts()
        result = []
        for c in conflicts:
            c.created_at = now
            result.append(c.to_dict())

            # Store in database
            db.execute(
                """
                INSERT OR REPLACE INTO fact_conflicts
                (conflict_id, project_id, subject_id, fact_type, source_count,
                 values_json, conflict_type, resolution, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'UNRESOLVED', ?)
                """,
                (
                    c.conflict_id, c.project_id, c.subject_id, c.fact_type,
                    c.source_count, c.values_json, c.conflict_type, c.created_at,
                ),
            )

            # Flag affected facts
            values = json.loads(c.values_json)
            for v in values:
                fid = v.get("fact_id")
                if fid:
                    db.execute(
                        "UPDATE facts SET conflict_flag = 1 WHERE fact_id = ?",
                        (fid,),
                    )

        db.commit()
        logger.info("[ConflictDetector] Found %d conflicts for project %s", len(conflicts), project_id)
        return result

    except Exception as e:
        logger.warning("[ConflictDetector] Conflict detection failed (non-fatal): %s", e)
        return []
