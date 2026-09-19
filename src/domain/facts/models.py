from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Any, Dict
from datetime import datetime
import json

class FactStatus(str, Enum):
    CANDIDATE = "CANDIDATE"
    VALIDATED = "VALIDATED"
    HUMAN_CERTIFIED = "HUMAN_CERTIFIED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"
    DRAFT = "DRAFT"


class FactProvenanceClass(str, Enum):
    EVIDENCE = "EVIDENCE"
    AI_GENERATED = "AI_GENERATED"
    SUPPLEMENTARY_RETRIEVAL = "SUPPLEMENTARY_RETRIEVAL"


TRUSTED_FACT_STATUSES = (
    FactStatus.VALIDATED.value,
    FactStatus.HUMAN_CERTIFIED.value,
)
TRUSTED_FACT_STATUSES_SQL = ", ".join(f"'{status}'" for status in TRUSTED_FACT_STATUSES)
NON_GOVERNING_FACT_STATUSES = (FactStatus.CANDIDATE.value,)
CANONICAL_REJECTED_STATUS = FactStatus.REJECTED.value
REJECTED_FACT_STATUSES = (FactStatus.REJECTED.value, "REFUSED")
AI_GENERATED_PROVENANCE = FactProvenanceClass.AI_GENERATED.value
SUPPORTING_CONTEXT_CLASSES = (
    FactProvenanceClass.AI_GENERATED.value,
    FactProvenanceClass.SUPPLEMENTARY_RETRIEVAL.value,
)


def canonicalize_fact_status(status: Any) -> str:
    """Return the canonical persisted status for legacy and current fact states."""
    raw = status.value if isinstance(status, FactStatus) else status
    normalized = str(raw or "").strip().upper()
    rejected_aliases = {str(item).upper() for item in REJECTED_FACT_STATUSES}
    if normalized in rejected_aliases:
        return CANONICAL_REJECTED_STATUS
    return normalized


def is_rejected_fact_status(status: Any) -> bool:
    return canonicalize_fact_status(status) == CANONICAL_REJECTED_STATUS


def is_trusted_fact_status(status: Any) -> bool:
    return canonicalize_fact_status(status) in TRUSTED_FACT_STATUSES


def normalize_rejection_status(status: Any) -> str:
    return canonicalize_fact_status(status)

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
    location: Dict[str, Any] # {page: 1, bbox: [...], handle: "1A2B", activity_id: "123"}
    input_kind: str = "evidence"


@dataclass
class EvidenceAnchor:
    """Structured source navigation anchor for a fact.

    Populated from FactInput.location by EvidenceAnchor.from_fact_input().
    Fields are intentionally sparse: only populated when the builder has
    the information available. Missing fields are left as None rather than
    fabricated.
    """
    source_file: Optional[str] = None
    source_type: Optional[str] = None
    page_or_slide: Optional[int] = None
    bbox: Optional[List[float]] = None
    entity_handle: Optional[str] = None
    element_id: Optional[str] = None
    activity_id: Optional[str] = None
    sheet_or_section: Optional[str] = None
    row_or_paragraph: Optional[int] = None
    cell_address: Optional[str] = None

    @classmethod
    def from_fact_input(cls, fact_input: "FactInput") -> "EvidenceAnchor":
        location = fact_input.location or {}
        if not isinstance(location, dict):
            return cls()
        return cls(
            source_file=location.get("source_file"),
            source_type=location.get("source_type"),
            page_or_slide=location.get("page") or location.get("page_or_slide"),
            bbox=location.get("bbox"),
            entity_handle=location.get("entity_handle"),
            element_id=location.get("element_id"),
            activity_id=location.get("activity_id"),
            sheet_or_section=location.get("sheet") or location.get("sheet_or_section"),
            row_or_paragraph=location.get("row") or location.get("row_or_paragraph"),
            cell_address=location.get("cell") or location.get("cell_address"),
        )

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
            "fact_type": self.fact_type,
            "subject_kind": self.subject_kind,
            "subject_id": self.subject_id,
            "value": self.value,
            "status": self.status.value,
            "confidence_tier": self.confidence_tier
        }
