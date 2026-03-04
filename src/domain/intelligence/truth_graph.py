# -*- coding: utf-8 -*-
import logging
from typing import List, Dict, Any, Optional, Set
from src.infra.persistence.database_manager import DatabaseManager

logger = logging.getLogger(__name__)

class TruthGraphService:
    """
    Service for traversing the Project Knowledge Graph (Truth Graph).
    Ties together Canonical Entities from Schedule, BIM, and Documents.
    """
    
    def __init__(self, db: DatabaseManager):
        self.db = db

    def get_neighbors(self, entity_id: int) -> List[Dict[str, Any]]:
        """Find all entities directly linked to this one."""
        sql = """
            SELECT en.id, en.entity_type, en.value, el.rel_type, el.confidence_tier
            FROM entity_links el
            JOIN entity_nodes en ON el.to_entity_id = en.id
            WHERE el.from_entity_id = ?
            UNION
            SELECT en.id, en.entity_type, en.value, el.rel_type, el.confidence_tier
            FROM entity_links el
            JOIN entity_nodes en ON el.from_entity_id = en.id
            WHERE el.to_entity_id = ?
        """
        rows = self.db.execute(sql, (entity_id, entity_id)).fetchall()
        return [dict(row) for row in rows]

    def find_path_to_domain(self, start_entity_id: int, target_domain: str, max_depth: int = 3) -> List[Dict[str, Any]]:
        """
        BFS to find entities of a specific domain/type linked to the start entity.
        Target domains: 'SCHEDULE', 'BIM', 'DOC_CONTROL', etc. (mapped from entity_type)
        """
        queue = [(start_entity_id, [])]
        visited = {start_entity_id}
        
        results = []
        
        while queue:
            current_id, path = queue.pop(0)
            if len(path) >= max_depth:
                continue
                
            neighbors = self.get_neighbors(current_id)
            for n in neighbors:
                nid = n["id"]
                if nid in visited:
                    continue
                
                visited.add(nid)
                new_path = path + [n]
                
                # Check if this neighbor belongs to the target domain
                # Rough mapping for now: entity_type 'activity' -> SCHEDULE, 'element' -> BIM
                if self._matches_domain(n["entity_type"], target_domain):
                    results.append({"entity": n, "path": new_path})
                
                queue.append((nid, new_path))
                
        return results

    def _matches_domain(self, entity_type: str, domain: str) -> bool:
        mapping = {
            "SCHEDULE": ["activity", "wbs", "milestone"],
            "BIM": ["element", "zone", "spatial_container"],
            "DOC_CONTROL": ["drawing", "document", "revision"],
            "PROCUREMENT": ["submittal", "equipment", "po"]
        }
        return entity_type in mapping.get(domain, [])

    def get_certified_evidence_path(self, fact_id: str) -> List[Dict[str, Any]]:
        """
        Combines Fact Lineage with Graph Traversal to show the full Truth Map for a fact.
        """
        # 1. Get direct evidence from fact_inputs
        evidence_sql = """
            SELECT fi.*, fv.source_path 
            FROM fact_inputs fi
            JOIN file_versions fv ON fi.file_version_id = fv.file_version_id
            WHERE fi.fact_id = ?
        """
        direct_evidence = [dict(row) for row in self.db.execute(evidence_sql, (fact_id,)).fetchall()]
        
        # 2. Get the subject entity of the fact
        fact_sql = "SELECT subject_id, subject_kind FROM facts WHERE fact_id = ?"
        fact_row = self.db.execute(fact_sql, (fact_id,)).fetchone()
        
        if not fact_row:
            return direct_evidence
            
        # 3. Find the graph node for the subject
        node_sql = "SELECT id FROM entity_nodes WHERE value = ? AND entity_type = ?"
        node_row = self.db.execute(node_sql, (fact_row["subject_id"], fact_row["subject_kind"])).fetchone()
        
        graph_context = []
        if node_row:
            graph_context = self.get_neighbors(node_row["id"])
            
        return {
            "direct_evidence": direct_evidence,
            "graph_context": graph_context
        }
