import logging
import json
from typing import List, Dict, Any
from collections import defaultdict

from src.domain.facts.models import Fact, FactStatus, FactInput, ValueType
from src.infra.persistence.database_manager import DatabaseManager

logger = logging.getLogger(__name__)

class BIMBuilder:
    """
    Builder: BIM
    Consumes: ifc_projects, ifc_spatial_structure, ifc_elements
    Produces: Fact(bim.project), Fact(bim.zone), Fact(bim.element), Fact(bim.element_inventory_*)
    """
    
    def __init__(self, db: DatabaseManager):
        self.db = db

    def build(self, project_id: str, snapshot_id: str) -> List[Fact]:
        facts = []
        now = self.db._ts()
        
        # 1. Project
        projs = self.db.execute("SELECT * FROM ifc_projects WHERE file_version_id=?", (snapshot_id,)).fetchall()
        for p in projs:
            facts.append(Fact(
                fact_id=f"fact_bim_proj_{p['global_id']}",
                project_id=project_id,
                fact_type="bim.project",
                subject_kind="bim_project",
                subject_id=p["global_id"],
                as_of={"file_version_id": snapshot_id},
                value_type=ValueType.JSON,
                value={"name": p["name"], "phase": p["phase"]},
                status=FactStatus.CANDIDATE,
                method_id="bim_builder_v1",
                created_at=now,
                updated_at=now,
                inputs=[FactInput(file_version_id=snapshot_id, location={"row_id": p["global_id"]})]
            ))
            
        # 2. Spatial (Sites, Buildings, Storeys)
        spatial = self.db.execute("SELECT * FROM ifc_spatial_structure WHERE file_version_id=?", (snapshot_id,)).fetchall()
        level_map = {}  # element_id -> name (for level lookups)
        
        for s in spatial:
            # We map IfcSite/Building/Storey to "bim.zone" or "bim.facility"
            ftype = "bim.zone"
            if s["entity_type"] == "IFCSITE": ftype = "bim.site"
            elif s["entity_type"] == "IFCBUILDING": ftype = "bim.facility"
            elif s["entity_type"] == "IFCBUILDINGSTOREY": 
                ftype = "bim.level"
                level_map[s["element_id"]] = s["name"]
            
            facts.append(Fact(
                fact_id=f"fact_bim_spatial_{s['element_id']}",
                project_id=project_id,
                fact_type=ftype,
                subject_kind="bim_spatial",
                subject_id=s["element_id"],
                as_of={"file_version_id": snapshot_id},
                value_type=ValueType.JSON,
                value={"name": s["name"], "type": s["entity_type"]},
                status=FactStatus.CANDIDATE,
                method_id="bim_builder_v1",
                created_at=now,
                updated_at=now,
                inputs=[FactInput(file_version_id=snapshot_id, location={"row_id": s["element_id"]})]
            ))
       
        # 3. NEW: Elements with inventory tracking
        elements = self.db.execute("SELECT * FROM ifc_elements WHERE file_version_id=?", (snapshot_id,)).fetchall()
        
        element_type_counts = defaultdict(int)  # entity_type -> count
        element_level_counts = defaultdict(lambda: defaultdict(int))  # level_name -> {entity_type -> count}
        
        for elem in elements:
            e_dict = dict(elem)
            entity_type = e_dict.get("entity_type", "UNKNOWN")
            element_type_counts[entity_type] += 1
            
            # Track by level if available
            container_id = e_dict.get("spatial_container_id")
            if container_id and container_id in level_map:
                level_name = level_map[container_id]
                element_level_counts[level_name][entity_type] += 1
            
            # Individual element fact (optional - can be verbose)
            # Uncomment if you want per-element facts:
            # facts.append(Fact(
            #     fact_id=f"fact_bim_elem_{elem['element_id']}",
            #     project_id=project_id,
            #     fact_type="bim.element",
            #     subject_kind="bim_element",
            #     subject_id=elem["element_id"],
            #     as_of={"file_version_id": snapshot_id},
            #     value_type=ValueType.JSON,
            #     value={"name": elem["name"], "type": entity_type, "tag": elem.get("tag")},
            #     status=FactStatus.CANDIDATE,
            #     method_id="bim_builder_v1",
            #     created_at=now,
            #     updated_at=now,
            #     inputs=[FactInput(file_version_id=snapshot_id, location={"row_id": elem["element_id"]})]
            # ))
        
        # 4. NEW: Computed Inventory Facts
        
        # 4a. Element count by type
        for entity_type, count in element_type_counts.items():
            f_type_count = Fact(
                fact_id=f"fact_bim_inv_type_{entity_type}_{snapshot_id[:8]}",
                project_id=project_id,
                fact_type="bim.element_inventory_count_by_type",
                subject_kind="project",
                subject_id=project_id,
                scope={"entity_type": entity_type},
                as_of={"file_version_id": snapshot_id},
                value_type=ValueType.NUM,
                value=count,
                unit="elements",
                status=FactStatus.CANDIDATE,
                method_id="bim_builder_v1_inventory",
                created_at=now,
                updated_at=now
            )
            f_type_count.inputs.append(FactInput(file_version_id=snapshot_id, location={"table": "ifc_elements"}))
            facts.append(f_type_count)
        
        # 4b. Element count by level (per type)
        for level_name, type_counts in element_level_counts.items():
            for entity_type, count in type_counts.items():
                f_level_count = Fact(
                    fact_id=f"fact_bim_inv_level_{level_name}_{entity_type}_{snapshot_id[:8]}",
                    project_id=project_id,
                    fact_type="bim.element_inventory_count_by_level",
                    subject_kind="project",
                    subject_id=project_id,
                    scope={"level": level_name, "entity_type": entity_type},
                    as_of={"file_version_id": snapshot_id},
                    value_type=ValueType.NUM,
                    value=count,
                    unit="elements",
                    status=FactStatus.CANDIDATE,
                    method_id="bim_builder_v1_inventory",
                    created_at=now,
                    updated_at=now
                )
                f_level_count.inputs.append(FactInput(file_version_id=snapshot_id, location={"table": "ifc_elements"}))
                facts.append(f_level_count)
        
        # 4c. Spatial hierarchy depth
        hierarchy_depth = self._compute_hierarchy_depth(spatial)
        f_depth = Fact(
            fact_id=f"fact_bim_hierarchy_depth_{snapshot_id[:8]}",
            project_id=project_id,
            fact_type="bim.spatial_hierarchy_depth",
            subject_kind="project",
            subject_id=project_id,
            as_of={"file_version_id": snapshot_id},
            value_type=ValueType.NUM,
            value=hierarchy_depth,
            unit="levels",
            status=FactStatus.CANDIDATE,
            method_id="bim_builder_v1",
            created_at=now,
            updated_at=now
        )
        f_depth.inputs.append(FactInput(file_version_id=snapshot_id, location={"table": "ifc_spatial_structure"}))
        facts.append(f_depth)
        
        logger.info(f"[BIMBuilder] Generated {len(facts)} facts ({len(element_type_counts)} element types)")
        return facts
    
    def _compute_hierarchy_depth(self, spatial_rows: List[Dict]) -> int:
        """Compute max depth of spatial hierarchy tree."""
        if not spatial_rows:
            return 0
        
        # Build parent map
        parent_map = {}
        for row in spatial_rows:
            r_dict = dict(row)
            parent_map[r_dict["element_id"]] = r_dict.get("parent_id")
        
        # Find max depth
        max_depth = 0
        for elem_id in parent_map.keys():
            depth = 0
            current = elem_id
            visited = set()
            while current and current in parent_map:
                if current in visited:  # Cycle detection
                    break
                visited.add(current)
                current = parent_map[current]
                depth += 1
            max_depth = max(max_depth, depth)
        
        return max_depth
