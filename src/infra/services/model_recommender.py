# -*- coding: utf-8 -*-
"""
Model Recommender - Automatic model suggestions based on project type
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ModelRecommender:
    """
    Recommend models based on project characteristics.
    
    Analyzes:
    - Document types (PDFs, images, CAD files)
    - Project domain (AECO, legal, medical, etc.)
    - Performance requirements
    - Available VRAM
    """
    
    def __init__(self, db, lm_studio_service):
        """
        Initialize model recommender.
        
        Args:
            db: DatabaseManager instance
            lm_studio_service: LMStudioService instance
        """
        self.db = db
        self.lms = lm_studio_service
        
        # Model profiles
        self.models = {
            "granite-4-micro": {
                "size_gb": 2.3,
                "vram_mb": 2100,
                "speed_tok_s": 45,
                "strengths": ["fast", "low_vram", "entity_extraction", "qa"],
                "weaknesses": ["vision", "creative_writing"]
            },
            "mistral-7b-instruct": {
                "size_gb": 4.1,
                "vram_mb": 3800,
                "speed_tok_s": 35,
                "strengths": ["qa", "summarization", "reasoning", "balanced"],
                "weaknesses": ["vision"]
            },
            "qwen2-vl-7b-instruct": {
                "size_gb": 4.5,
                "vram_mb": 4200,
                "speed_tok_s": 28,
                "strengths": ["vision", "multimodal", "technical_drawings", "ocr"],
                "weaknesses": ["speed"]
            }
        }
    
    def recommend_for_project(self, project_id: str) -> Dict[str, any]:
        """
        Recommend models for a project.
        
        Args:
            project_id: Project identifier
            
        Returns:
            {
                "primary": model_name,
                "alternatives": [model_names],
                "reasoning": explanation
            }
        """
        try:
            # Analyze project
            analysis = self._analyze_project(project_id)
            
            # Get system constraints
            status = self.lms.get_status() if self.lms and self.lms.enabled else {}
            vram_available = status.get('vram_total_mb', 8192)
            
            # Score models
            scores = {}
            for model, profile in self.models.items():
                score = self._score_model(model, profile, analysis, vram_available)
                scores[model] = score
            
            # Sort by score
            ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            
            # Generate recommendation
            primary = ranked[0][0]
            alternatives = [m for m, s in ranked[1:3]]
            
            reasoning = self._generate_reasoning(primary, analysis, vram_available)
            
            return {
                "primary": primary,
                "alternatives": alternatives,
                "reasoning": reasoning,
                "scores": scores
            }
            
        except Exception as e:
            logger.error(f"[ModelRecommender] Failed to recommend: {e}")
            return {
                "primary": "granite-4-micro",
                "alternatives": ["mistral-7b-instruct"],
                "reasoning": "Default recommendation (analysis failed)",
                "scores": {}
            }
    
    def _analyze_project(self, project_id: str) -> Dict[str, any]:
        """Analyze project characteristics."""
        try:
            # Get documents
            docs = self.db.list_documents(project_id=project_id, limit=1000) or []
            
            # Count document types
            pdf_count = sum(1 for d in docs if d.get('file_path', '').lower().endswith('.pdf'))
            image_count = sum(1 for d in docs if d.get('file_path', '').lower().endswith(('.png', '.jpg', '.jpeg')))
            cad_count = sum(1 for d in docs if d.get('file_path', '').lower().endswith(('.dwg', '.dxf', '.dgn')))
            
            # Get total pages
            total_pages = sum(len(self.db.list_pages(d["doc_id"]) or []) for d in docs)
            
            # Determine domain
            has_vision = (image_count + cad_count) > 0
            has_text = pdf_count > 0
            is_large = total_pages > 100
            
            return {
                "doc_count": len(docs),
                "pdf_count": pdf_count,
                "image_count": image_count,
                "cad_count": cad_count,
                "total_pages": total_pages,
                "has_vision": has_vision,
                "has_text": has_text,
                "is_large": is_large
            }
            
        except Exception as e:
            logger.warning(f"[ModelRecommender] Analysis failed: {e}")
            return {
                "doc_count": 0,
                "has_vision": False,
                "has_text": True,
                "is_large": False
            }
    
    def _score_model(
        self,
        model: str,
        profile: Dict,
        analysis: Dict,
        vram_available: int
    ) -> float:
        """Score a model for the project."""
        score = 0.0
        
        # VRAM constraint (hard requirement)
        if profile["vram_mb"] > vram_available:
            return 0.0  # Cannot run
        
        # Vision requirement
        if analysis["has_vision"]:
            if "vision" in profile["strengths"]:
                score += 50
            elif "vision" in profile["weaknesses"]:
                score -= 20
        
        # Speed for large projects
        if analysis["is_large"]:
            if "fast" in profile["strengths"]:
                score += 30
            score += profile["speed_tok_s"] * 0.5
        
        # Text processing
        if analysis["has_text"]:
            if "qa" in profile["strengths"] or "summarization" in profile["strengths"]:
                score += 20
        
        # VRAM efficiency bonus
        vram_efficiency = 1.0 - (profile["vram_mb"] / vram_available)
        score += vram_efficiency * 10
        
        return score
    
    def _generate_reasoning(
        self,
        model: str,
        analysis: Dict,
        vram_available: int
    ) -> str:
        """Generate human-readable reasoning."""
        profile = self.models.get(model, {})
        
        reasons = []
        
        # Vision
        if analysis["has_vision"] and "vision" in profile.get("strengths", []):
            reasons.append("✓ Excellent vision capabilities for technical drawings")
        
        # Speed
        if analysis["is_large"] and "fast" in profile.get("strengths", []):
            reasons.append(f"✓ Fast processing ({profile.get('speed_tok_s', 0)} tok/s) for large project")
        
        # VRAM
        vram_used_pct = (profile.get("vram_mb", 0) / vram_available) * 100
        if vram_used_pct < 50:
            reasons.append(f"✓ Low VRAM usage ({vram_used_pct:.0f}% of available)")
        
        # Strengths
        strengths = profile.get("strengths", [])
        if "balanced" in strengths:
            reasons.append("✓ Well-balanced for general tasks")
        
        if not reasons:
            reasons.append("✓ Good general-purpose model")
        
        return " | ".join(reasons)
    
    def get_recommendations_summary(self, project_id: str) -> str:
        """Get formatted recommendation summary."""
        rec = self.recommend_for_project(project_id)
        
        summary = f"""**Recommended Model**: {rec['primary']}

**Why**: {rec['reasoning']}

**Alternatives**:
"""
        for alt in rec['alternatives']:
            summary += f"- {alt}\n"
        
        return summary
