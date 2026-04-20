import logging
import csv
from typing import List, Dict, Any, Optional
import io

from src.engine.extractors.base import BaseExtractor, ExtractionResult

logger = logging.getLogger(__name__)

class P6Extractor(BaseExtractor):
    """
    Extracts data from Primavera P6 XER and XML files.
    Focuses on: PROJECT, WBSS, TASK (Activity), TASKPRED (Relationship).
    """
    
    @property
    def id(self) -> str:
        return "p6-extractor-standard"
        
    @property
    def version(self) -> str:
        return "1.0.0"
        
    @property
    def supported_extensions(self) -> List[str]:
        return [".xer"] # XML validation later

    def extract(self, file_path: str, context: Dict[str, Any] = None) -> ExtractionResult:
        records = []
        diagnostics = []
        
        try:
            with open(file_path, 'r', encoding='latin-1') as f: # XER often latin-1 or cp1252
                content = f.read()
                
            tables = self._parse_xer(content)
            
            # Map XER tables to Staging Records
            
            # 1. Projects
            if "PROJECT" in tables:
                for row in tables["PROJECT"]:
                    records.append({
                        "type": "p6_project",
                        "data": row,
                        "provenance": {"table": "PROJECT"}
                    })
                    
            # 2. WBS
            if "PROJWBS" in tables:
                 for row in tables["PROJWBS"]:
                    records.append({
                        "type": "p6_wbs",
                        "data": row,
                        "provenance": {"table": "PROJWBS"}
                    })

            # 3. Tasks (Activities) & 4. Relationships (Logic Engine)
            if "TASK" in tables:
                task_map = {t.get("task_id"): t for t in tables["TASK"]}
                
                # Phase 1.3: Native Logic Engine Computation
                # Map Predecessors / Successors from TASKPRED
                if "TASKPRED" in tables:
                    for rel in tables["TASKPRED"]:
                        succ_id = rel.get("task_id")
                        pred_id = rel.get("pred_task_id")
                        if succ_id in task_map and pred_id in task_map:
                            # Explicitly link IDs for the truth engine
                            task_map[succ_id].setdefault("predecessor_ids", []).append(pred_id)
                            task_map[pred_id].setdefault("successor_ids", []).append(succ_id)

                for row in tables["TASK"]:
                    # Refine Float & Critical Path Logic
                    float_hr = row.get("total_float_hr_cnt")
                    is_critical = False
                    row["total_float_hours"] = None
                    row["total_float"] = None
                    row["total_float_days"] = None

                    try:
                        if float_hr not in (None, ""):
                            f_val = float(float_hr)
                            total_float_days = round(f_val / 8.0, 2)
                            is_critical = f_val <= 0
                            row["total_float_hours"] = f_val
                            row["total_float"] = total_float_days
                            row["total_float_days"] = total_float_days
                    except (ValueError, TypeError):
                        row["total_float_hours"] = None
                        row["total_float"] = None
                        row["total_float_days"] = None

                    row["is_critical"] = is_critical
                    
                    # Create Activity Record
                    records.append({
                        "type": "p6_activity",
                        "data": row,
                        "provenance": {
                            "table": "TASK", 
                            "has_logic": "predecessor_ids" in row
                        }
                    })

            # 5. Raw Relationships (for trace preservation)
            if "TASKPRED" in tables:
                for row in tables["TASKPRED"]:
                    records.append({
                        "type": "p6_relation",
                        "data": row,
                        "provenance": {"table": "TASKPRED"}
                    })
            
            return ExtractionResult(records=records, diagnostics=diagnostics, success=True)
            
        except Exception as e:
            logger.error(f"P6 Extraction failed: {e}")
            return ExtractionResult(success=False, diagnostics=[str(e)])

    def _parse_xer(self, content: str) -> Dict[str, List[Dict[str, str]]]:
        """
        Custom XER Parser.
        XER structure:
        %T  TableName
        %F  Field1  Field2 ...
        %R  Val1    Val2 ...
        """
        tables = {}
        lines = content.splitlines()
        
        current_table = None
        fields = []
        
        for line in lines:
            line = line.strip()
            if not line: continue
            
            parts = line.split('\t')
            type_code = parts[0]
            
            if type_code == '%T':
                current_table = parts[1]
                tables[current_table] = []
                fields = []
            elif type_code == '%F':
                fields = parts[1:]
            elif type_code == '%R':
                if not current_table or not fields:
                    continue
                values = parts[1:]
                # Zip into dict
                row = dict(zip(fields, values))
                tables[current_table].append(row)
                
        return tables
