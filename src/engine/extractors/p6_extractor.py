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

            # 3. Tasks
            if "TASK" in tables:
                 for row in tables["TASK"]:
                    records.append({
                        "type": "p6_activity",
                        "data": row,
                        "provenance": {"table": "TASK"}
                    })

            # 4. Relations
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
