"""
Phase 2: Confidence Learning Engine

Learns from engineer corrections to improve confidence scoring and model predictions.
Tracks model performance, identifies reliable vs unreliable fields, and helps with model selection.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import logging
import statistics

logger = logging.getLogger(__name__)


class ConfidenceLevel(Enum):
    """Confidence levels for extraction quality."""
    VERY_HIGH = "very_high"    # >= 0.85
    HIGH = "high"              # 0.65-0.85
    MEDIUM = "medium"          # 0.45-0.65
    LOW = "low"                # 0.25-0.45
    VERY_LOW = "very_low"      # < 0.25


@dataclass
class ModelPerformance:
    """Performance metrics for a specific model."""
    model_name: str
    total_extractions: int
    successful_extractions: int
    failure_count: int
    avg_confidence: float
    accuracy_rate: float           # (successful - corrections) / total
    fields_strength: Dict[str, float]  # Field -> accuracy for this model
    fields_weakness: Dict[str, float]  # Field -> error rate for this model
    recommended_fields: List[str]  # Fields where this model excels
    avoid_fields: List[str]        # Fields where this model struggles


@dataclass
class FieldConfidenceProfile:
    """Confidence profile for a specific field."""
    field_name: str
    global_accuracy: float
    avg_vlm_confidence: float
    correction_patterns: Dict[str, int]  # Error type -> frequency
    best_model: str                # Model that performs best
    worst_model: str               # Model that performs worst
    requires_validation: bool      # Should be human-reviewed
    recommended_confidence_threshold: float


@dataclass
class ExtractionConfidenceScore:
    """Detailed confidence score for an extraction."""
    field_name: str
    model_used: str
    vlm_reported_confidence: float
    learned_confidence: float      # Adjusted by learning
    confidence_level: str          # ConfidenceLevel enum value
    reliability: float             # 0.0-1.0 based on model history
    should_validate: bool          # Recommend human review
    uncertainty_factors: List[str] # Reasons for uncertainty


class ConfidenceLearner:
    """
    Learns from engineer corrections to improve confidence scoring.
    
    Responsibilities:
    - Track model performance across fields
    - Compute learned confidence scores
    - Predict extraction accuracy before extraction
    - Identify fields requiring validation
    - Recommend model selection based on field and document type
    """
    
    def __init__(self, db=None):
        """Initialize learner with optional database connection."""
        self.db = db
        # In-memory storage for model performance (would be in DB in production)
        self.model_performance_cache: Dict[str, ModelPerformance] = {}
        self.field_confidence_cache: Dict[str, FieldConfidenceProfile] = {}
        # Bayesian Beta distribution parameters (alpha=successes, beta=failures)
        self.bayesian_params: Dict[str, Dict[str, Tuple[float, float]]] = {}  # {model: {field: (alpha, beta)}}
    
    def track_extraction(self, 
                        field_name: str,
                        model_used: str,
                        vlm_confidence: float,
                        was_correct: bool) -> None:
        """
        Track extraction result to build confidence models.
        
        Args:
            field_name: Name of extracted field
            model_used: Model that performed extraction (e.g., "Qwen2-VL-7B")
            vlm_confidence: Confidence score reported by VLM
            was_correct: Whether engineer validated as correct
        """
        logger.debug(f"Tracking: {field_name} from {model_used}, "
                    f"vlm_conf={vlm_confidence}, correct={was_correct}")
        
        # In-memory tracking for integration/unit tests
        if model_used not in self.model_performance_cache:
             self.model_performance_cache[model_used] = ModelPerformance(
                model_name=model_used,
                total_extractions=0,
                successful_extractions=0,
                failure_count=0,
                avg_confidence=0.0,
                accuracy_rate=0.0,
                fields_strength={},
                fields_weakness={},
                recommended_fields=[],
                avoid_fields=[]
            )
        
        perf = self.model_performance_cache[model_used]
        perf.total_extractions += 1
        if was_correct:
            perf.successful_extractions += 1
        else:
            perf.failure_count += 1
        
        # Bayesian Beta distribution update (PRODUCTION-GRADE)
        if model_used not in self.bayesian_params:
            self.bayesian_params[model_used] = {}
        
        if field_name not in self.bayesian_params[model_used]:
            # Initialize with weak prior: Beta(2, 2) = uniform-ish with slight regularization
            self.bayesian_params[model_used][field_name] = (2.0, 2.0)
        
        alpha, beta = self.bayesian_params[model_used][field_name]
        
        # Bayesian update: add 1 to alpha if correct, add 1 to beta if incorrect
        if was_correct:
            alpha += 1.0
        else:
            beta += 1.0
        
        self.bayesian_params[model_used][field_name] = (alpha, beta)
        
        # Compute posterior mean: alpha / (alpha + beta)
        posterior_accuracy = alpha / (alpha + beta)
        perf.fields_strength[field_name] = posterior_accuracy
        
        # Update field confidence cache
        if field_name not in self.field_confidence_cache:
            self.field_confidence_cache[field_name] = FieldConfidenceProfile(
                field_name=field_name,
                global_accuracy=posterior_accuracy,
                avg_vlm_confidence=vlm_confidence,
                correction_patterns={},
                best_model=model_used,
                worst_model="",
                requires_validation=False,
                recommended_confidence_threshold=0.7
            )
        else:
            # Update global accuracy using Bayesian posterior
            profile = self.field_confidence_cache[field_name]
            profile.global_accuracy = posterior_accuracy
            profile.requires_validation = (posterior_accuracy < 0.7)
    
    def compute_learned_confidence(self,
                                  field_name: str,
                                  model_name: str,
                                  vlm_reported_confidence: float) -> ExtractionConfidenceScore:
        """
        Compute adjusted confidence score based on historical performance.
        
        Args:
            field_name: Name of field
            model_name: Model used for extraction
            vlm_reported_confidence: Confidence reported by VLM (0.0-1.0)
            
        Returns:
            ExtractionConfidenceScore with adjusted confidence and metadata
        """
        # Get historical performance for this field + model combination
        model_perf = self.model_performance_cache.get(model_name)
        field_profile = self.field_confidence_cache.get(field_name)
        
        # Base confidence adjustment
        learned_confidence = vlm_reported_confidence
        uncertainty_factors = []
        
        if not model_perf:
            logger.warning(f"No historical data for model {model_name}")
            learned_confidence *= 0.8  # Reduce confidence if model is new
            uncertainty_factors.append("New model with limited history")
        else:
            # Adjust by model's accuracy on this field
            field_accuracy = model_perf.fields_strength.get(field_name)
            if field_accuracy is not None:
                # Blend VLM confidence with learned accuracy
                learned_confidence = (vlm_reported_confidence * 0.6 +
                                     field_accuracy * 0.4)
            else:
                learned_confidence *= 0.9  # Reduce for untested combination
                uncertainty_factors.append("Model untested on this field")
        
        if not field_profile:
            logger.warning(f"No profile for field {field_name}")
            uncertainty_factors.append("Field has limited correction history")
        else:
            # If field is inherently difficult, reduce confidence
            if field_profile.global_accuracy < 0.75:
                learned_confidence *= 0.9
                uncertainty_factors.append("Field has high error rate historically")
        
        # Clamp confidence to valid range
        learned_confidence = max(0.0, min(1.0, learned_confidence))
        
        # Determine confidence level
        conf_level = self._get_confidence_level(learned_confidence)
        
        # Should validate if confidence is low or field is inherently difficult
        should_validate = (learned_confidence < 0.65 or
                          (field_profile and field_profile.requires_validation))
        
        # Compute reliability based on model history
        reliability = model_perf.accuracy_rate if model_perf else 0.5
        
        return ExtractionConfidenceScore(
            field_name=field_name,
            model_used=model_name,
            vlm_reported_confidence=vlm_reported_confidence,
            learned_confidence=learned_confidence,
            confidence_level=conf_level,
            reliability=reliability,
            should_validate=should_validate,
            uncertainty_factors=uncertainty_factors
        )
    
    def predict_extraction_accuracy(self,
                                   field_name: str,
                                   model_name: str,
                                   document_type: str = "general") -> float:
        """
        Predict accuracy before extraction based on historical data.
        
        Args:
            field_name: Name of field to extract
            model_name: Model that will be used
            document_type: Type of document (e.g., "specification", "drawing")
            
        Returns:
            Predicted accuracy as float (0.0-1.0)
        """
        model_perf = self.model_performance_cache.get(model_name)
        field_profile = self.field_confidence_cache.get(field_name)
        
        if not model_perf or not field_profile:
            # Default prediction
            return 0.7
        
        # Get model's accuracy on this field
        field_accuracy = model_perf.fields_strength.get(field_name, 0.7)
        
        # Adjust by field difficulty
        base_accuracy = field_profile.global_accuracy
        
        # Blend model-specific accuracy with field difficulty
        predicted = (field_accuracy * 0.5 + base_accuracy * 0.5)
        
        return max(0.0, min(1.0, predicted))
    
    def get_field_confidence_profile(self, field_name: str) -> Optional[FieldConfidenceProfile]:
        """
        Get the confidence profile for a specific field.
        
        Args:
            field_name: Name of field
            
        Returns:
            FieldConfidenceProfile or None if not found
        """
        return self.field_confidence_cache.get(field_name)
    
    def build_model_performance_profile(self,
                                       corrections: List,
                                       model_name: str) -> ModelPerformance:
        """
        Build comprehensive performance profile for a model based on corrections.
        
        Args:
            corrections: List of CorrectionRecord objects
            model_name: Name of model to analyze
            
        Returns:
            ModelPerformance with detailed metrics
        """
        # Filter corrections to this model (would be tracked in corrections table)
        model_corrections = corrections  # Simplified; would filter by model_name in DB
        
        total = len(model_corrections)
        if total == 0:
            return ModelPerformance(
                model_name=model_name,
                total_extractions=0,
                successful_extractions=0,
                failure_count=0,
                avg_confidence=0.0,
                accuracy_rate=0.0,
                fields_strength={},
                fields_weakness={},
                recommended_fields=[],
                avoid_fields=[]
            )
        
        # Count corrections by field
        fields_correction_count = {}
        for correction in model_corrections:
            field = correction.field_name
            fields_correction_count[field] = fields_correction_count.get(field, 0) + 1
        
        # Estimate accuracy by field (fewer corrections = higher accuracy)
        fields_strength = {}
        fields_weakness = {}
        for field, correction_count in fields_correction_count.items():
            accuracy = 1.0 - (correction_count / max(total, 1))
            if accuracy > 0.85:
                fields_strength[field] = accuracy
            elif accuracy < 0.7:
                fields_weakness[field] = accuracy
        
        # Recommended and avoid fields
        recommended_fields = sorted(fields_strength.keys(),
                                  key=lambda f: fields_strength[f],
                                  reverse=True)[:3]
        avoid_fields = sorted(fields_weakness.keys(),
                            key=lambda f: fields_weakness[f])[:3]
        
        # Overall accuracy
        failure_count = total  # Simplified: all corrections are failures
        successful_extractions = max(0, total - failure_count)
        accuracy_rate = successful_extractions / max(total, 1)
        
        # Average confidence (would be from actual VLM outputs)
        avg_confidence = 0.7  # Placeholder
        
        return ModelPerformance(
            model_name=model_name,
            total_extractions=total,
            successful_extractions=successful_extractions,
            failure_count=failure_count,
            avg_confidence=avg_confidence,
            accuracy_rate=accuracy_rate,
            fields_strength=fields_strength,
            fields_weakness=fields_weakness,
            recommended_fields=recommended_fields,
            avoid_fields=avoid_fields
        )
    
    def identify_fields_needing_validation(self,
                                          threshold: float = 0.70) -> List[str]:
        """
        Identify fields that should be human-validated due to low accuracy.
        
        Args:
            threshold: Accuracy threshold below which validation is recommended
            
        Returns:
            List of field names
        """
        fields_needing_validation = []
        
        for field_name, profile in self.field_confidence_cache.items():
            if profile.global_accuracy < threshold:
                fields_needing_validation.append(field_name)
        
        return sorted(fields_needing_validation)
    
    def get_best_model_for_field(self, field_name: str) -> Optional[str]:
        """
        Recommend the best model for extracting a specific field.
        
        Args:
            field_name: Name of field
            
        Returns:
            Model name or None if no recommendation
        """
        field_profile = self.field_confidence_cache.get(field_name)
        if field_profile:
            return field_profile.best_model
        return None
    
    def compute_confidence_statistics(self,
                                     confidences: List[float]) -> Dict[str, float]:
        """
        Compute statistical summary of confidence scores.
        
        Args:
            confidences: List of confidence scores (0.0-1.0)
            
        Returns:
            Dict with mean, median, std_dev, min, max
        """
        if not confidences:
            return {
                'mean': 0.0,
                'median': 0.0,
                'std_dev': 0.0,
                'min': 0.0,
                'max': 0.0
            }
        
        return {
            'mean': statistics.mean(confidences),
            'median': statistics.median(confidences),
            'std_dev': statistics.stdev(confidences) if len(confidences) > 1 else 0.0,
            'min': min(confidences),
            'max': max(confidences)
        }
    
    def recommend_model_for_document(self,
                                    document_type: str,
                                    available_memory_gb: float) -> str:
        """
        Recommend model based on document type and available resources.
        
        Args:
            document_type: Type of document (e.g., "specification", "drawing")
            available_memory_gb: Available VRAM in GB
            
        Returns:
            Recommended model name
        """
        # Base model recommendation on resources
        if available_memory_gb >= 6:
            return "Qwen2-VL-7B"  # Best quality
        elif available_memory_gb >= 4.5:
            return "Mistral-7B"   # Fast alternative
        else:
            return "OCR-only"     # Fallback to Stage 1 only
    
    def estimate_learning_readiness(self) -> Dict[str, float]:
        """
        Estimate how much the learning models have matured.
        
        Returns:
            Dict with learning_completeness (0.0-1.0) and sample_sizes
        """
        # Count data in cache
        total_field_profiles = len(self.field_confidence_cache)
        total_model_profiles = len(self.model_performance_cache)
        
        # Learning is ready when we have profiles for multiple fields and models
        learning_completeness = min(1.0, (total_field_profiles / 20.0 +
                                         total_model_profiles / 3.0) / 2.0)
        
        return {
            'learning_completeness': learning_completeness,
            'field_profiles': total_field_profiles,
            'model_profiles': total_model_profiles,
            'is_ready': learning_completeness >= 0.5
        }
    
    def _get_confidence_level(self, confidence: float) -> str:
        """Map confidence score to ConfidenceLevel enum."""
        if confidence >= 0.85:
            return ConfidenceLevel.VERY_HIGH.value
        elif confidence >= 0.65:
            return ConfidenceLevel.HIGH.value
        elif confidence >= 0.45:
            return ConfidenceLevel.MEDIUM.value
        elif confidence >= 0.25:
            return ConfidenceLevel.LOW.value
        else:
            return ConfidenceLevel.VERY_LOW.value
    
    def populate_field_confidence_cache(self, corrections: List) -> None:
        """
        Build field confidence profiles from corrections data.
        
        Args:
            corrections: List of CorrectionRecord objects
        """
        fields = set(c.field_name for c in corrections)
        
        for field_name in fields:
            field_corrections = [c for c in corrections if c.field_name == field_name]
            
            # Compute accuracy as 1 - (corrections / total)
            global_accuracy = 1.0 - (len(field_corrections) / max(len(corrections), 1))
            
            # Average VLM confidence (placeholder)
            avg_vlm_conf = 0.75
            
            # Correction patterns (simplified)
            patterns = {}
            for correction in field_corrections:
                fb_type = correction.feedback_type
                patterns[fb_type] = patterns.get(fb_type, 0) + 1
            
            # Determine if field requires validation
            requires_validation = global_accuracy < 0.8
            
            profile = FieldConfidenceProfile(
                field_name=field_name,
                global_accuracy=global_accuracy,
                avg_vlm_confidence=avg_vlm_conf,
                correction_patterns=patterns,
                best_model="Qwen2-VL-7B",  # Would be determined from DB
                worst_model="Mistral-7B",  # Would be determined from DB
                requires_validation=requires_validation,
                recommended_confidence_threshold=0.75 if requires_validation else 0.65
            )
            self.field_confidence_cache[field_name] = profile
    
    def populate_model_performance_cache(self,
                                        models: List[str],
                                        corrections: List) -> None:
        """
        Build model performance profiles.
        
        Args:
            models: List of model names to profile
            corrections: List of CorrectionRecord objects
        """
        for model_name in models:
            perf = self.build_model_performance_profile(corrections, model_name)
            self.model_performance_cache[model_name] = perf
