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
cross_doc_linker.py — Cross-Document Entity Linking
---------------------------------------------------
Builds entity graph across all analyzed documents in a project.
Merges duplicate entities and identifies conflicts.
"""

import time
from typing import Dict, Any, List, Tuple

from src.infra.persistence.database_manager import DatabaseManager


class CrossDocLinker:
    """
    Processes analysis results to build cross-document entity graph.
    """
    
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    def link_project(self, project_id: str) -> Dict[str, Any]:
        """
        Build entity graph for entire project.
        
        Returns:
            {
                "entities_created": int,
                "links_created": int,
                "conflicts_found": int,
                "entities_merged": int
            }
        """
        print(f"[CrossDocLinker] Starting link process for project {project_id}")
        
        stats = {
            "entities_created": 0,
            "links_created": 0,
            "conflicts_found": 0,
            "entities_merged": 0
        }
        
        # 1. Extract entities from all analysis results
        entity_map = self._extract_entities(project_id)
        stats["entities_created"] = len(entity_map)
        
        # 2. Create entity nodes in database
        self._create_entity_nodes(project_id, entity_map)
        
        # 3. Create links between entities
        links_created = self._create_entity_links(project_id, entity_map)
        stats["links_created"] = links_created
        
        # 4. Detect conflicts
        conflicts = self._detect_conflicts(project_id)
        stats["conflicts_found"] = conflicts
        
        print(f"[CrossDocLinker] Complete: {stats}")
        return stats
    
    def _extract_entities(self, project_id: str) -> Dict[Tuple[str, str], List[Dict]]:
        """
        Extract entities from analysis results, grouped by (type, value).
        
        Returns:
            {
                ("building", "Tower A"): [
                    {"doc_id": "doc1", "confidence": 0.9, "extra": {...}},
                    {"doc_id": "doc2", "confidence": 0.85, "extra": {...}}
                ]
            }
        """
        entity_map: Dict[Tuple[str, str], List[Dict]] = {}
        
        docs = self.db.list_documents(project_id=project_id)
        
        for doc in docs:
            doc_id = doc["doc_id"]
            analysis = self.db.get_analysis(doc_id)
            
            if not analysis:
                continue
            
            entities = analysis.get("entities", [])
            
            for ent in entities:
                ent_type = ent.get("type", "")
                ent_value = ent.get("value", "")
                
                if not ent_type or not ent_value:
                    continue
                
                key = (ent_type, ent_value)
                
                if key not in entity_map:
                    entity_map[key] = []
                
                entity_map[key].append({
                    "doc_id": doc_id,
                    "confidence": ent.get("confidence", 0.0),
                    "extra": ent.get("attributes", {})
                })
        
        print(f"[CrossDocLinker] Extracted {len(entity_map)} unique entities")
        return entity_map
    
    def _create_entity_nodes(
        self,
        project_id: str,
        entity_map: Dict[Tuple[str, str], List[Dict]]
    ) -> None:
        """
        Create entity_nodes records in database.
        One node per (project_id, entity_type, value, doc_id) combination.
        """
        import json
        
        for (ent_type, ent_value), instances in entity_map.items():
            for inst in instances:
                try:
                    self.db._exec(
                        """
                        INSERT OR IGNORE INTO entity_nodes
                        (project_id, entity_type, value, doc_id, extra_json, confidence, created_ts)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            project_id,
                            ent_type,
                            ent_value,
                            inst["doc_id"],
                            json.dumps(inst.get("extra", {})),
                            inst.get("confidence", 0.0),
                            int(time.time())
                        )
                    )
                except Exception as e:
                    print(f"[WARN] Failed to insert entity node: {e}")
    
    def _create_entity_links(
        self,
        project_id: str,
        entity_map: Dict[Tuple[str, str], List[Dict]]
    ) -> int:
        """
        Create entity_links based on hierarchical relationships.
        
        Examples:
        - space → floor (part_of)
        - floor → building (part_of)
        - building → site (part_of)
        - site → project (part_of)
        
        Returns count of links created.
        """
        link_count = 0
        
        # Get all entity IDs
        entity_ids = self._get_entity_id_map(project_id)
        
        # Define hierarchical relationships
        hierarchies = [
            ("space", "floor", "part_of"),
            ("floor", "building", "part_of"),
            ("building", "site", "part_of"),
            ("site", "project", "part_of"),
            ("detail", "sheet", "part_of"),
            ("sheet", "drawing", "part_of"),
        ]
        
        for child_type, parent_type, rel_type in hierarchies:
            # Find all child entities
            child_entities = [
                key for key in entity_map.keys() if key[0] == child_type
            ]
            
            # Find all parent entities
            parent_entities = [
                key for key in entity_map.keys() if key[0] == parent_type
            ]
            
            # Create links for entities from same document
            for child_key in child_entities:
                for child_inst in entity_map[child_key]:
                    child_doc = child_inst["doc_id"]
                    
                    # Find parent from same doc
                    for parent_key in parent_entities:
                        for parent_inst in entity_map[parent_key]:
                            if parent_inst["doc_id"] == child_doc:
                                # Create link
                                child_id = entity_ids.get((child_key, child_doc))
                                parent_id = entity_ids.get((parent_key, parent_inst["doc_id"]))
                                
                                if child_id and parent_id:
                                    try:
                                        self.db._exec(
                                            """
                                            INSERT OR IGNORE INTO entity_links
                                            (project_id, from_entity_id, to_entity_id, rel_type, source_doc_id, confidence, created_ts)
                                            VALUES (?, ?, ?, ?, ?, ?, ?)
                                            """,
                                            (
                                                project_id,
                                                child_id,
                                                parent_id,
                                                rel_type,
                                                child_doc,
                                                0.8,  # Default confidence for hierarchical links
                                                int(time.time())
                                            )
                                        )
                                        link_count += 1
                                    except Exception as e:
                                        print(f"[WARN] Failed to create link: {e}")
        
        return link_count
    
    def _get_entity_id_map(self, project_id: str) -> Dict[Tuple[Tuple[str, str], str], int]:
        """
        Get mapping of (entity_key, doc_id) -> entity node ID.
        """
        rows = self.db._query(
            "SELECT id, entity_type, value, doc_id FROM entity_nodes WHERE project_id=?",
            (project_id,)
        )
        
        id_map = {} 
        for row in rows:
            key = ((row["entity_type"], row["value"]), row["doc_id"])
            id_map[key] = row["id"]
        
        return id_map
    
    def _detect_conflicts(self, project_id: str) -> int:
        """
        Detect conflicting entity definitions.
        
        For entities with same (type, value) but different extra_json,
        create conflict links.
        
        Returns count of conflicts found.
        """
        import json
        
        conflict_count = 0
        
        # Group entities by (type, value)
        rows = self.db._query(
            """
            SELECT id, entity_type, value, doc_id, extra_json
            FROM entity_nodes
            WHERE project_id=?
            """,
            (project_id,)
        )
        
        grouped: Dict[Tuple[str, str], List[Dict]] = {}
        for row in rows:
            key = (row["entity_type"], row["value"])
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(dict(row))
        
        # Check for conflicts within each group
        for key, entities in grouped.items():
            if len(entities) < 2:
                continue
            
            # Compare extra_json for conflicts
            for i, ent1 in enumerate(entities):
                for ent2 in entities[i+1:]:
                    extra1 = json.loads(ent1.get("extra_json", "{}") or "{}")
                    extra2 = json.loads(ent2.get("extra_json", "{}") or "{}")
                    
                    # Check for conflicting values in same keys
                    has_conflict = False
                    for attr_key in set(extra1.keys()) & set(extra2.keys()):
                        if extra1[attr_key] != extra2[attr_key]:
                            has_conflict = True
                            break
                    
                    if has_conflict:
                        # Create conflict link
                        try:
                            self.db._exec(
                                """
                                INSERT OR IGNORE INTO entity_links
                                (project_id, from_entity_id, to_entity_id, rel_type, confidence, created_ts)
                                VALUES (?, ?, ?, ?, ?, ?)
                                """,
                                (
                                    project_id,
                                    ent1["id"],
                                    ent2["id"],
                                    "conflicts_with",
                                    1.0,
                                    int(time.time())
                                )
                            )
                            conflict_count += 1
                        except Exception as e:
                            print(f"[WARN] Failed to create conflict link: {e}")
        
        return conflict_count
