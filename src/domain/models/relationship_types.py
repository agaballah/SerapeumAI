# -*- coding: utf-8 -*-
"""
Standard Enums for AECO Knowledge Graph.
Prevents string fragmentation and ensures semantic consistency.
"""

from enum import Enum

class EntityType(Enum):
    # Core AECO Entities
    PROJECT = "project"
    DOCUMENT = "document"
    ORGANIZATION = "organization"
    PERSON = "person"
    LOCATION = "location"
    
    # Technical Entities
    EQUIPMENT = "equipment"
    SYSTEM = "system"
    MATERIAL = "material"
    COMPONENT = "component"
    SPACE = "space"
    LEVEL = "level"
    
    # Process Entities
    ACTIVITY = "activity"
    RISK = "risk"
    REQUIREMENT = "requirement"
    STANDARD = "standard"
    
    # Generic
    ENTITY = "entity"

class RelationshipType(Enum):
    # Structural/Physical
    CONTAINS = "contains"
    PART_OF = "part_of"
    CONNECTS_TO = "connects_to"
    SUPPORTS = "supports"
    LOCATED_IN = "located_in"
    
    # MEP/Functional
    POWERS = "powers"
    FEEDS = "feeds"
    DRAINS_INTO = "drains_into"
    CONTROLS = "controls"
    
    # Procedural/Logic
    DEPENDS_ON = "depends_on"
    REFERENCES = "references"
    COMPLIES_WITH = "complies_with"
    MITIGATES = "mitigates"
    
    # Generic
    RELATED_TO = "related_to"
