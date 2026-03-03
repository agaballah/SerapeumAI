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
            # TODO: Add ifcopenshell support
            # import ifcopenshell
            # f = ifcopenshell.open(file_path)
            # ...
            
            # For now, Fallback Regex Parser implemented
            logger.info("Using Regex Fallback for IFC Extraction (ifcopenshell not active)")
            self._parse_regex(file_path, records, diagnostics)
            
            return ExtractionResult(records=records, diagnostics=diagnostics, success=True)
            
        except Exception as e:
            logger.error(f"IFC Extraction failed: {e}")
            return ExtractionResult(success=False, diagnostics=[str(e)])

    def _parse_regex(self, file_path: str, records: List[Dict[str, Any]], diagnostics: List[str]):
        """
        Naive Parsing of STEP format to get Header and Project Info.
        """
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # 1. HEADER
        # FILE_NAME('Name', 'TimeStamp', ...)
        # Regex is brittle for STEP, but sufficient for high-level checks
        
        # 2. Extract Project (IfcProject)
        # #123=IFCPROJECT('GlobalId',#Owner,'Name',...)
        # Pattern: #\d+=IFCPROJECT\('([^']+)',.*,'([^']+)'
        
        # GlobalId is always first arg, coded in string '...'
        
        # Find all Entites for rough counting
        # entities = re.findall(r"#(\d+)=([A-Z]+)\((.*)\);", content)
        
        # Better: Search specific Types
        
        # PROJECT
        proj_match = re.search(r"=IFCPROJECT\('([^']+)'.*?,'([^']*)'", content)
        if proj_match:
            gid, name = proj_match.groups()
            records.append({
                "type": "ifc_project",
                "data": {"GlobalId": gid, "Name": name},
                "provenance": {"entity": "IfcProject"}
            })
            
        # SITE / BUILDING / STOREY (Hierarchy)
        # This is hard with regex because relationships are disjoint (IfcRelAggregates).
        # We really need a proper parser for relations.
        # But for Phase 1 "existence", we can just dump the Objects found.
        
        for entity_type in ["IFCSITE", "IFCBUILDING", "IFCBUILDINGSTOREY"]:
            matches = re.findall(rf"=({entity_type})\('([^']+)'.*?,'([^']*)'", content)
            for m in matches:
                # m = (TYPE, GlobalId, Name)
                records.append({
                    "type": "ifc_spatial",
                    "data": {"EntityType": m[0], "GlobalId": m[1], "Name": m[2]},
                    "provenance": {"entity": m[0]}
                })

        diagnostics.append(f"Extracted {len(records)} IFC records via Regex")
