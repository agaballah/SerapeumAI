# -*- coding: utf-8 -*-
import yaml
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class TemplateRouter:
    """
    Routes natural language queries to highly-reliable Fact Templates.
    Ensures that the engine knows exactly what facts are needed before answering.
    """
    
    def __init__(self, templates_path: Optional[str] = None):
        if templates_path:
            self.path = Path(templates_path)
        else:
            self.path = Path(__file__).parent.parent / "templates" / "fact_templates.yaml"
            
        self.templates: Dict[str, Any] = {}
        self.load()

    def load(self):
        try:
            if self.path.exists():
                with open(self.path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    self.templates = data.get("templates", {})
                logger.info(f"Loaded {len(self.templates)} fact templates.")
            else:
                logger.warning(f"Fact templates not found at {self.path}")
        except Exception as e:
            logger.error(f"Failed to load fact templates: {e}")

    def route_query(self, query: str) -> List[Dict[str, Any]]:
        """
        Matches a query to one or more fact templates.
        In a production version, this would use an LLM or specialized classifier.
        For now, we use a robust keyword/intent matching strategy.
        """
        query_lower = query.lower()
        candidates = []
        
        for name, template in self.templates.items():
            keywords = template.get("intent_keywords", [])
            # If any keyword matches, we consider it a candidate
            if any(kw in query_lower for kw in keywords):
                templates_copy = template.copy()
                templates_copy["id"] = name
                candidates.append(templates_copy)
                
        # Sort by specificity if needed (e.g. number of keyword matches)
        return candidates

    def get_required_facts(self, template_ids: List[str]) -> Dict[str, List[str]]:
        """
        Aggregates requirements across multiple templates.
        Returns { domain: [fact_type1, fact_type2] }
        """
        requirements = {}
        for tid in template_ids:
            template = self.templates.get(tid)
            if not template:
                continue
                
            domains = template.get("required_domains", [])
            facts = template.get("required_facts", [])
            
            for domain in domains:
                if domain not in requirements:
                    requirements[domain] = []
                # In a real system, we'd map required_facts to specific domains accurately
                # For now, we assume domains contain all listed facts in the template
                requirements[domain].extend(facts)
        
        # Deduplicate
        for domain in requirements:
            requirements[domain] = list(set(requirements[domain]))
            
        return requirements
