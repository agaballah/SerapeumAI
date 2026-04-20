import logging
import re
import json
from typing import List, Dict, Any, Optional

from src.engine.extractors.base import BaseExtractor, ExtractionResult

logger = logging.getLogger(__name__)

class IFCExtractor(BaseExtractor):
    """
    Extracts data from IFC files (STEP format).
    Strategy:
    1. Try `import ifcopenshell` (Best).
    2. Fallback to `Regex/Text` parsing for structure (Good enough for Phase 1).
    """
    
    @property
    def id(self) -> str:
        return "ifc-extractor-v1"
        
    @property
    def version(self) -> str:
        return "1.0.0"
        
    @property
    def supported_extensions(self) -> List[str]:
        return [".ifc"]

    def extract(self, file_path: str, context: Dict[str, Any] = None) -> ExtractionResult:
        records = []
        diagnostics = []
        
        try:
            import ifcopenshell
            import ifcopenshell.util.element
            
            f = ifcopenshell.open(file_path)
            
            # 1. Project-wide Metadata
            for proj in f.by_type("IfcProject"):
                records.append({
                    "type": "ifc_project",
                    "data": {
                        "GlobalId": proj.GlobalId,
                        "Name": proj.Name or "Unnamed Project",
                        "Units": str(proj.UnitsInContext) if hasattr(proj, "UnitsInContext") else None
                    },
                    "provenance": {"entity": "IfcProject"}
                })
            
            # 2. Spatial Structure (Hierarchical Mapping)
            # site -> building -> storey
            for site in f.by_type("IfcSite"):
                records.append({
                    "type": "ifc_spatial",
                    "data": {"EntityType": "IfcSite", "GlobalId": site.GlobalId, "Name": site.Name or "Unnamed Site"},
                    "provenance": {"entity": site.is_a()}
                })
                
                # Check Site -> Building (IsDecomposedBy)
                for rel_agg in getattr(site, "IsDecomposedBy", []):
                    if rel_agg.is_a("IfcRelAggregates"):
                        for building in rel_agg.RelatedObjects:
                            if building.is_a("IfcBuilding"):
                                records.append({
                                    "type": "ifc_spatial",
                                    "data": {"EntityType": "IfcBuilding", "GlobalId": building.GlobalId, "ParentId": site.GlobalId, "Name": building.Name or "Unnamed Building"},
                                    "provenance": {"entity": building.is_a()}
                                })
                                # Building -> Storey
                                for rel_agg_b in getattr(building, "IsDecomposedBy", []):
                                    if rel_agg_b.is_a("IfcRelAggregates"):
                                        for storey in rel_agg_b.RelatedObjects:
                                            if storey.is_a("IfcBuildingStorey"):
                                                records.append({
                                                    "type": "ifc_spatial",
                                                    "data": {"EntityType": "IfcBuildingStorey", "GlobalId": storey.GlobalId, "ParentId": building.GlobalId, "Name": storey.Name or "Unnamed Storey"},
                                                    "provenance": {"entity": storey.is_a()}
                                                })

            # 3. Product Extraction with PSet & QSet Resolution
            for product in f.by_type("IfcProduct"):
                psets = ifcopenshell.util.element.get_psets(product)
                if psets:
                    for pset_name, props in psets.items():
                        records.append({
                            "type": "ifc_element_metadata",
                            "data": {
                                "EntityType": product.is_a(),
                                "ElementId": product.GlobalId,
                                "PSetName": pset_name,
                                "Properties": props,
                                "IsQuantity": "Quantity" in pset_name
                            },
                            "provenance": {"entity": product.is_a(), "pset": pset_name}
                        })
            
            # 4. Structural Connections
            for connect in f.by_type("IfcRelConnectsElements"):
                records.append({
                    "type": "ifc_connection",
                    "data": {
                        "RelType": "Connectivity",
                        "Element1Id": connect.RelatingElement.GlobalId,
                        "Element2Id": connect.RelatedElement.GlobalId,
                    },
                    "provenance": {"entity": connect.is_a()}
                })

            diagnostics.append(f"Successfully parsed {len(records)} Engineering-Scale IFC entities.")
            return ExtractionResult(records=records, diagnostics=diagnostics, success=True)
            
        except ImportError:
            logger.error("ifcopenshell not installed. IFC extraction requires this library.")
            return ExtractionResult(success=False, diagnostics=["Missing ifcopenshell dependency"])
        except Exception as e:
            logger.error(f"IFC Extraction failed: {e}")
            return ExtractionResult(success=False, diagnostics=[str(e)])
