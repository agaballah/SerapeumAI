# -*- coding: utf-8 -*-
"""
Model Role Manifest - Defines the canonical model roles and their typical properties.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional


class ModelRole(str, Enum):
    """Canonical model roles in SerapeumAI."""
    ROUTER = "router"
    NARRATOR = "narrator"
    STRUCTURED_JSON = "structured_json"
    EVIDENCE_COMPRESSOR = "evidence_compressor"
    VISION_HELPER = "vision_helper"
    EMBEDDING = "embedding"
    RERANKER = "reranker"


class ModelSize(str, Enum):
    """Relative model size categories."""
    TINY = "tiny"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    XLARGE = "xlarge"


class QuantizationQuality(str, Enum):
    """Relative quantization quality (higher is better)."""
    Q2 = "q2"
    Q3 = "q3"
    Q4 = "q4"
    Q5 = "q5"
    Q6 = "q6"
    Q8 = "q8"
    F16 = "f16"
    F32 = "f32"


@dataclass(frozen=True)
class RoleCharacteristics:
    """Characteristics that define what a model should be good at for a given role."""
    role: ModelRole
    description: str
    preferred_size: ModelSize
    preferred_quantization: List[QuantizationQuality]  # Ordered by preference
    min_vram_mb: int  # Minimum VRAM required for comfortable operation
    ram_sensitive: bool = False  # Whether performance is significantly impacted by RAM
    description_template: str = ""  # Template for generating human-readable descriptions

    def get_description(self, model_id: str = "") -> str:
        """Get a human-readable description for this role."""
        if self.description_template:
            return self.description_template.format(model_id=model_id)
        return self.description


# Define the canonical role characteristics
ROLE_CHARACTERISTICS: Dict[ModelRole, RoleCharacteristics] = {
    ModelRole.ROUTER: RoleCharacteristics(
        role=ModelRole.ROUTER,
        description="Task routing and intent classification - lightweight and fast.",
        preferred_size=ModelSize.TINY,
        preferred_quantization=[QuantizationQuality.Q4, QuantizationQuality.Q5],
        min_vram_mb=512,
        ram_sensitive=False,
        description_template="Router model ({model_id}) for fast task classification.",
    ),
    ModelRole.NARRATOR: RoleCharacteristics(
        role=ModelRole.NARRATOR,
        description="Main storyteller / conversational model - balanced for chat and reasoning.",
        preferred_size=ModelSize.MEDIUM,
        preferred_quantization=[QuantizationQuality.Q4, QuantizationQuality.Q5],
        min_vram_mb=4096,  # 4GB for 7B Q4
        ram_sensitive=True,
        description_template="Narrator model ({model_id}) for general conversation and reasoning.",
    ),
    ModelRole.STRUCTURED_JSON: RoleCharacteristics(
        role=ModelRole.STRUCTURED_JSON,
        description="Structured output / tool calling - reliable JSON generation.",
        preferred_size=ModelSize.MEDIUM,
        preferred_quantization=[QuantizationQuality.Q5, QuantizationQuality.Q6],
        min_vram_mb=4096,
        ram_sensitive=False,
        description_template="Structured JSON model ({model_id}) for tool calls and data extraction.",
    ),
    ModelRole.EVIDENCE_COMPRESSOR: RoleCharacteristics(
        role=ModelRole.EVIDENCE_COMPRESSOR,
        description="Evidence compression and summarization - concise and accurate.",
        preferred_size=ModelSize.MEDIUM,
        preferred_quantization=[QuantizationQuality.Q4, QuantizationQuality.Q5],
        min_vram_mb=4096,
        ram_sensitive=True,
        description_template="Compressor model ({model_id}) for summarizing evidence.",
    ),
    ModelRole.VISION_HELPER: RoleCharacteristics(
        role=ModelRole.VISION_HELPER,
        description="Vision-language model for image understanding, OCR, and diagram parsing.",
        preferred_size=ModelSize.MEDIUM,
        preferred_quantization=[QuantizationQuality.Q4, QuantizationQuality.Q5],
        min_vram_mb=6144,  # 6GB for 7B VL Q4 (vision models are larger)
        ram_sensitive=True,
        description_template="Vision helper model ({model_id}) for image and document understanding.",
    ),
    ModelRole.EMBEDDING: RoleCharacteristics(
        role=ModelRole.EMBEDDING,
        description="Text embedding model for retrieval and semantic search.",
        preferred_size=ModelSize.SMALL,
        preferred_quantization=[QuantizationQuality.F16],  # Embeddings often use float16
        min_vram_mb=512,
        ram_sensitive=False,
        description_template="Embedding model ({model_id}) for semantic search and retrieval.",
    ),
    ModelRole.RERANKER: RoleCharacteristics(
        role=ModelRole.RERANKER,
        description="Re-ranking model to improve search result relevance.",
        preferred_size=ModelSize.SMALL,
        preferred_quantization=[QuantizationQuality.Q4, QuantizationQuality.Q5],
        min_vram_mb=2048,
        ram_sensitive=False,
        description_template="Reranker model ({model_id}) for improving search relevance.",
    ),
}


def get_role_characteristics(role: ModelRole) -> RoleCharacteristics:
    """Get the characteristics for a given model role."""
    return ROLE_CHARACTERISTICS.get(role, ROLE_CHARACTERISTICS[ModelRole.NARRATOR])


def get_all_roles() -> List[ModelRole]:
    """Get all defined model roles."""
    return list(ModelRole)