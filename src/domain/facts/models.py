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
    """Structured evidence location reference for cross-format navigation.

    Wraps FactInput.location with typed accessors. Backward compatible —
    existing FactInput.location dicts continue to work unchanged.
    """
    source_file: str = ""
    source_type: str = ""  # "pdf" | "docx" | "pptx" | "xlsx" | "dxf" | "ifc" | "p6" | "image"
    page_or_slide: Optional[int] = None
    sheet_or_section: Optional[str] = None
    row_or_paragraph: Optional[int] = None
    cell_address: Optional[str] = None
    entity_handle: Optional[str] = None
    element_id: Optional[str] = None
    activity_id: Optional[str] = None
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None
    bbox: Optional[List[float]] = None  # [x0, y0, x1, y1] in PDF points
    excerpt: Optional[str] = None
    excerpt_length: Optional[int] = None

    @classmethod
    def from_fact_input(cls, fi: "FactInput") -> "EvidenceAnchor":
        """Convert existing FactInput to EvidenceAnchor (backward compatible)."""
        loc = fi.location or {}
        return cls(
            source_file=loc.get("source_file", ""),
            source_type=loc.get("source_type", ""),
            page_or_slide=loc.get("page") or loc.get("page_or_slide"),
            sheet_or_section=loc.get("sheet"),
            row_or_paragraph=loc.get("row") or loc.get("paragraph"),
            cell_address=loc.get("cell"),
            entity_handle=loc.get("handle"),
            element_id=loc.get("element_id") or loc.get("global_id"),
            activity_id=loc.get("activity_id"),
            x=loc.get("x"),
            y=loc.get("y"),
            z=loc.get("z"),
            bbox=loc.get("bbox"),
            excerpt=loc.get("excerpt"),
        )

    def to_location_dict(self) -> Dict[str, Any]:
        """Convert back to location dict for FactInput compatibility."""
        d: Dict[str, Any] = {}
        if self.source_file:
            d["source_file"] = self.source_file
        if self.source_type:
            d["source_type"] = self.source_type
        if self.page_or_slide is not None:
            d["page"] = self.page_or_slide
        if self.sheet_or_section:
            d["sheet"] = self.sheet_or_section
        if self.row_or_paragraph is not None:
            d["row"] = self.row_or_paragraph
        if self.cell_address:
            d["cell"] = self.cell_address
        if self.entity_handle:
            d["handle"] = self.entity_handle
        if self.element_id:
            d["element_id"] = self.element_id
        if self.activity_id:
            d["activity_id"] = self.activity_id
        if self.x is not None:
            d["x"] = self.x
        if self.y is not None:
            d["y"] = self.y
        if self.z is not None:
            d["z"] = self.z
        if self.bbox:
            d["bbox"] = self.bbox
        if self.excerpt:
            d["excerpt"] = self.excerpt
        return d

    def format_citation(self, filename: str = "") -> str:
        """Generate human-readable citation string."""
        parts = []
        base = filename or self.source_file
        if self.source_type:
            base = self.source_type.upper()
        if base:
            parts.append(base)
        if self.page_or_slide:
            parts.append(f"p.{self.page_or_slide}")
        elif self.sheet_or_section:
            parts.append(f"sheet:{self.sheet_or_section}")
        elif self.row_or_paragraph:
            parts.append(f"para.{self.row_or_paragraph}")
        if self.cell_address:
            parts[-1] = f"{parts[-1]}!{self.cell_address}" if parts else self.cell_address
        if self.entity_handle:
            parts.append(f"h={self.entity_handle}")
        if self.activity_id:
            parts.append(f"act={self.activity_id}")
        if self.bbox:
            x0, y0, x1, y1 = self.bbox
            parts.append(f"bbox=({x0:.0f},{y0:.0f},{x1:.0f},{y1:.0f})")
        return " ".join(parts) if parts else "(no location)"

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
