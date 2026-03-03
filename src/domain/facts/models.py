from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Any, Dict
from datetime import datetime
import json

class FactStatus(str, Enum):
    CANDIDATE = "CANDIDATE"
    VALIDATED = "VALIDATED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"
    DRAFT = "DRAFT"

class ValueType(str, Enum):
    NUM = "NUM"
    TEXT = "TEXT"
    BOOL = "BOOL"
    DATE = "DATE"
    JSON = "JSON"

@dataclass
class FactInput:
    """Provenance for a fact (Fact -> Evidence)"""
    file_version_id: str
    location: Dict[str, Any] # {page: 1, bbox: [...]}
    input_kind: str = "evidence"

@dataclass
class Fact:
    """
    The Atomic Unit of Truth.
    Corresponds to 'facts' table.
    """
    fact_id: str
    project_id: str
    fact_type: str
    subject_kind: str
    subject_id: str
    
    # Context
    as_of: Dict[str, Any]
    scope: Optional[Dict[str, Any]] = None
    
    # Value
    value_type: ValueType = ValueType.TEXT
    value: Any = None
    unit: Optional[str] = None
    
    # Control
    status: FactStatus = FactStatus.CANDIDATE
    confidence: float = 1.0
    
    # Lineage
    method_id: str = "unknown"
    inputs: List[FactInput] = field(default_factory=list)
    
    created_at: int = 0
    updated_at: int = 0

    def to_dict(self):
        return {
            "fact_id": self.fact_id,
            "project_id": self.project_id,
            "fact_type": self.fact_type,
            "subject_kind": self.subject_kind,
            "subject_id": self.subject_id,
            "value": self.value,
            "status": self.status.value
        }
