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

class LinkStatus(str, Enum):
    CANDIDATE = "CANDIDATE"
    VALIDATED = "VALIDATED"
    AUTO_VALIDATED = "AUTO_VALIDATED" # New for Truth Engine V2
    REJECTED = "REJECTED"

@dataclass
class Link:
    """
    Standardized Cross-Domain Link.
    Corresponds to 'links' table.
    """
    link_id: str
    project_id: str
    link_type: str
    from_kind: str
    from_id: str
    to_kind: str
    to_id: str
    status: LinkStatus = LinkStatus.CANDIDATE
    confidence: float = 1.0
    confidence_tier: str = "CANDIDATE" # 'CANDIDATE', 'AUTO_VALIDATED', 'MANUAL_CERTIFIED'
    method_id: Optional[str] = None
    created_at: int = 0
    validated_at: Optional[int] = None

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

class LinkStatus(str, Enum):
    CANDIDATE = "CANDIDATE"
    VALIDATED = "VALIDATED"
    AUTO_VALIDATED = "AUTO_VALIDATED"
    REJECTED = "REJECTED"

@dataclass
class Link:
    """
    Standardized Cross-Domain Link.
    Corresponds to 'links' table.
    """
    link_id: str
    project_id: str
    link_type: str
    from_kind: str
    from_id: str
    to_kind: str
    to_id: str
    status: LinkStatus = LinkStatus.CANDIDATE
    confidence: float = 1.0
    confidence_tier: str = "CANDIDATE" # 'CANDIDATE', 'AUTO_VALIDATED', 'MANUAL_CERTIFIED'
    method_id: Optional[str] = None
    created_at: int = 0
    validated_at: Optional[int] = None

    def to_dict(self):
        return {
            "link_id": self.link_id,
            "project_id": self.project_id,
            "link_type": self.link_type,
            "from_kind": self.from_kind,
            "from_id": self.from_id,
            "to_kind": self.to_kind,
            "to_id": self.to_id,
            "status": self.status.value,
            "confidence_tier": self.confidence_tier
        }
