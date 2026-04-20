"""
standard_enricher.py

Small helper that looks up standard clauses that map to a given "concept" tag.

This module intentionally stays lightweight: it does not do embedding/vector work;
it just performs deterministic lookups against the standards SQLite DB.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

try:
    # Package import
    from .standards_service import StandardsService
except ImportError:  # pragma: no cover
    # Script / local import fallback
    from standards_service import StandardsService


class StandardEnricher:
    def __init__(self, db_path: Optional[str] = None) -> None:
        # StandardsService resolves the canonical runtime global DB and ensures schema.
        self.svc = StandardsService(db_path=db_path)

    def lookup_clauses_by_concept(self, concept: str, limit: int = 25) -> List[Dict[str, Any]]:
        """
        Return up to `limit` clauses mapped to `concept`.

        The mapping is an exact match on mappings.concept; normalize concept
        values at ingestion time if you need broader matching.
        """
        sql = """
        SELECT c.id, c.standard_id, c.path, c.text, c.meta
        FROM mappings m
        JOIN clauses c ON c.id = m.clause_id
        WHERE m.concept = ?
        ORDER BY c.standard_id, c.path
        LIMIT ?
        """

        with self.svc._connect() as conn:
            rows = conn.execute(sql, (concept, limit)).fetchall()

        out: List[Dict[str, Any]] = []
        for r in rows:
            meta = r["meta"]
            out.append(
                {
                    "id": r["id"],
                    "standard_id": r["standard_id"],
                    "path": r["path"],
                    "text": r["text"],
                    "meta": json.loads(meta) if meta else None,
                }
            )
        return out
