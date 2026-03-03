# -*- coding: utf-8 -*-
"""
TemplateLoader - Central utility for loading externalized prompts and thresholds.
Single source of truth for all AI instructions.
"""

import os
import yaml
import logging
from typing import Any, Dict, Optional, Union
from pathlib import Path

logger = logging.getLogger(__name__)

class TemplateLoader:
    """
    Loads and manages templated prompts and thresholds from YAML.
    """
    
    def __init__(self, template_path: Optional[str] = None):
        if template_path:
            self.path = Path(template_path)
        else:
            # Default location: src/domain/templates/prompts.yaml
            self.path = Path(__file__).parent / "prompts.yaml"
            
        self._data: Dict[str, Any] = {}
        self.load()
        
    def load(self):
        """Load or reload the YAML template file."""
        if not self.path.exists():
            logger.error(f"Template file not found at {self.path}")
            return
            
        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                self._data = yaml.safe_load(f) or {}
                logger.info(f"Loaded {len(self._data)} template sections from {self.path}")
        except Exception as e:
            logger.error(f"Failed to load templates: {e}")

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get a template value using dot notation (e.g., 'vision.stage1_system').
        """
        keys = key_path.split(".")
        value = self._data
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    def get_prompt(self, section: str, profile: str = None) -> Dict[str, str]:
        """
        Convenience helper to get system/user prompt pairs.
        Example: get_prompt('analysis', 'engineering_drawing')
        """
        if profile:
            path = f"{section}.profiles.{profile}"
        else:
            # Try to find system/user directly in section if no profile
            return {
                "system": self.get(f"{section}_system", ""),
                "user": self.get(f"{section}_user", "")
            }
            
        data = self.get(path)
        if isinstance(data, dict):
            return {
                "system": data.get("system", ""),
                "user": data.get("user", "")
            }
        return {"system": "", "user": ""}

# Singleton instance
_loader = None

def get_template_loader() -> TemplateLoader:
    global _loader
    if _loader is None:
        _loader = TemplateLoader()
    return _loader
