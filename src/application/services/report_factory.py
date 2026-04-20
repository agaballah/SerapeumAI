# -*- coding: utf-8 -*-
from typing import Dict, Any, List
from .artifact_service import ArtifactService

class ReportFactory:
    """Manages creation of standardized engineering reports"""
    
    def __init__(self, artifact_service: ArtifactService):
        self.service = artifact_service

    def create_project_summary(self, project_id: str, db: Any) -> str:
        """Generates a comprehensive project summary in DOCX and PDF."""
        # Pull real data from DB
        summary_data = db.get_analysis_result("project_summary", "executive_summary") or {}
        key_findings = db.get_analysis_result("project_summary", "key_findings") or []
        
        title = f"Engineering Analysis Report: {project_id}"
        content = {
            "summary": summary_data.get("text", "No executive summary found in database."),
            "evidence": [{"source": f.get("doc_id", "??"), "text": f.get("fact", "")} for f in key_findings],
            "thinking": "Generated from validated database records via SerapeumAI."
        }
        
        return self.service.generate_docx_report(f"Summary_{project_id}.docx", title, content)

    def create_boq_export(self, project_id: str, db: Any) -> str:
        """Generates a Bill of Quantities Excel export from real entities."""
        entities = db.list_entities(project_id)
        boq_data = []
        for ent in entities:
            # Type safe mapping from DB nodes
            if ent.get("entity_type") in ["material", "equipment", "zone", "component"]:
                boq_data.append({
                    "Category": ent.get("entity_type", "Misc"),
                    "Description": ent.get("value", "N/A"),
                    "Confidence": round(ent.get("confidence", 0.0), 2),
                    "Source Document": ent.get("doc_id", "Multiple")
                })
        
        if not boq_data:
            boq_data.append({"Status": "No qualifying entities found for BOQ."})
            
        return self.service.generate_excel_boq(f"BOQ_{project_id}.xlsx", boq_data)
