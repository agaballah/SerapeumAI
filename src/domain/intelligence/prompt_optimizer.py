"""
Phase 2: Dynamic Prompt Engineering

Generates optimized prompts tailored to document type, role, and field characteristics.
Leverages engineer feedback and correction patterns to improve extraction quality.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class DocumentType(Enum):
    """Document type classifications."""
    SPECIFICATION = "specification"
    DRAWING = "drawing"
    SCHEDULE = "schedule"
    CALCULATION = "calculation"
    REPORT = "report"
    MANUAL = "manual"
    UNKNOWN = "unknown"


class RoleType(Enum):
    """User role types."""
    ENGINEER = "engineer"
    ARCHITECT = "architect"
    CONTRACTOR = "contractor"
    OWNER = "owner"
    TECHNICIAN = "technician"
    GENERAL = "general"


@dataclass
class PromptTemplate:
    """A parameterized prompt template."""
    name: str
    stage: str                  # "stage1" or "stage2"
    document_type: str          # DocumentType enum value
    role: str                   # RoleType enum value
    base_template: str          # Template with placeholders like {unified_context}, {field_name}
    instructions: List[str]     # Specific extraction instructions
    examples: List[Dict]        # Few-shot examples: [{"input": "...", "output": "..."}]
    field_guidance: Dict[str, str]  # Field-specific guidance
    confidence_hints: str       # Guidance for confidence scoring


@dataclass
class OptimizedPrompt:
    """A generated optimized prompt."""
    full_prompt: str
    field_name: str
    model_name: str
    document_type: str
    role: str
    includes_examples: bool
    dynamic_adjustments: List[str]  # Adjustments made (e.g., "added_examples", "adjusted_instructions")


class PromptOptimizer:
    """
    Generates optimized prompts based on document type, role, and learned patterns.
    
    Responsibilities:
    - Maintain prompt templates for different document types and roles
    - Apply dynamic adjustments based on engineer feedback and field performance
    - Generate few-shot examples from corrections
    - Apply chain-of-thought and step-by-step prompting for complex fields
    - Suggest confidence scoring guidance
    """
    
    def __init__(self, db=None, correction_collector=None, confidence_learner=None):
        """Initialize optimizer with optional services and persona adapters."""
        self.db = db
        self.correction_collector = correction_collector
        self.confidence_learner = confidence_learner
        
        # Initialize legacy persona adapters for fortification
        from src.domain.personas.contractor_adapter import ContractorAdapter
        from src.domain.personas.owner_adapter import OwnerAdapter
        from src.domain.personas.pmc_adapter import PMCAdapter
        from src.domain.personas.technical_consultant_adapter import TechnicalConsultantAdapter
        
        self.adapters = {
            "contractor": ContractorAdapter(),
            "owner": OwnerAdapter(),
            "pmc": PMCAdapter(),
            "technical_consultant": TechnicalConsultantAdapter()
        }
        
        # Template cache and loader
        from src.domain.templates.loader import get_template_loader
        self.loader = get_template_loader()
        self.templates: Dict[str, PromptTemplate] = {}
        self._initialize_templates()

    def _get_persona_refinement(self, role: str, query: str = "", project_context: Dict = None) -> str:
        """Get refinement string from legacy adapters."""
        adapter = self.adapters.get(role.lower())
        if adapter and hasattr(adapter, "refine"):
            # Some adapters might not need all args, but we provide them for compatibility
            return adapter.refine(query, "", project_context or {})
        return query

    def _get_persona_system_guidance(self, role: str, project_json: str = "") -> str:
        """Get system-level persona guidance."""
        adapter = self.adapters.get(role.lower())
        if adapter and hasattr(adapter, "system_prompt"):
            return adapter.system_prompt(role, "", project_json)
        return ""

    def postprocess_result(self, role: str, llm_answer: str, project_context: Dict = None) -> str:
        """Apply persona-specific post-processing to the LLM answer."""
        adapter = self.adapters.get(role.lower())
        if adapter and hasattr(adapter, "postprocess"):
            return adapter.postprocess(llm_answer, "", project_context or {})
        return llm_answer
    
    def generate_stage1_prompt(self, 
                              unified_context: str,
                              document_type: str = "unknown",
                              role: str = "general") -> OptimizedPrompt:
        """
        Generate Stage 1 (classification) prompt fortified with persona logic.
        """
        template_key = f"stage1_{document_type}_{role}"
        template = self.templates.get(template_key)
        
        if not template:
            # Fallback to generic template
            template = self.templates.get("stage1_unknown_general", self._default_stage1_template())
        
        # Fortify with persona-specific system guidance
        persona_guidance = self._get_persona_system_guidance(role)
        base_template = template.base_template
        if persona_guidance:
            base_template = f"{persona_guidance}\n\n{base_template}"

        # Build prompt by substituting template variables
        full_prompt = self._substitute_template(
            base_template,
            {
                "unified_context": unified_context,
                "document_type": document_type,
                "role": role,
                "instructions": "\n".join(template.instructions),
                "confidence_hints": template.confidence_hints
            }
        )
        
        return OptimizedPrompt(
            full_prompt=full_prompt,
            field_name="document_type",
            model_name="generic",
            document_type=document_type,
            role=role,
            includes_examples=False,
            dynamic_adjustments=["injected_persona_guidance"] if persona_guidance else []
        )
    
    def generate_stage2_prompt(self,
                              unified_context: str,
                              field_name: str,
                              document_type: str,
                              role: str,
                              model_name: str = "Qwen2-VL-7B",
                              add_examples: bool = True) -> OptimizedPrompt:
        """
        Generate Stage 2 (specialized extraction) prompt fortified with persona logic.
        """
        template_key = f"stage2_{document_type}_{field_name}_{role}"
        template = self.templates.get(template_key)
        
        if not template:
            # Try generic field template
            template = self.templates.get(f"stage2_unknown_{field_name}_general")
        
        if not template:
            # Ultimate fallback
            template = self._default_stage2_template(field_name)
        
        # Start with persona-fortified system guidance
        persona_guidance = self._get_persona_system_guidance(role)
        full_prompt = ""
        if persona_guidance:
            full_prompt = f"{persona_guidance}\n\n"
        
        full_prompt += template.base_template
        
        # Apply persona-specific refinement (e.g., adding "Focus on constructability")
        refinement = self._get_persona_refinement(role)
        if refinement:
            full_prompt += f"\n\nAdditional Guidance: {refinement}"
        
        # Apply field guidance if available
        if field_name in template.field_guidance:
            full_prompt += f"\n\nField-specific guidance:\n{template.field_guidance[field_name]}"
        
        # Optionally add few-shot examples
        adjustments = []
        if add_examples:
            examples = self._get_examples_for_field(field_name)
            if examples:
                full_prompt += self._format_few_shot_examples(examples)
                adjustments.append("added_examples")
        
        # Apply confidence-aware adjustments
        if self.confidence_learner:
            confidence_guidance = self._get_confidence_guidance(field_name, model_name)
            if confidence_guidance:
                full_prompt += f"\n\nConfidence scoring guidance:\n{confidence_guidance}"
                adjustments.append("adjusted_confidence_guidance")
        
        # Add problem-area-specific instructions
        if self.correction_collector:
            problem_instructions = self._get_problem_area_instructions(field_name)
            if problem_instructions:
                full_prompt += f"\n\nImportant: {problem_instructions}"
                adjustments.append("adjusted_for_problem_areas")
        
        # Substitute template variables
        full_prompt = self._substitute_template(
            full_prompt,
            {
                "unified_context": unified_context,
                "field_name": field_name,
                "document_type": document_type,
                "role": role,
                "instructions": "\n".join(template.instructions),
                "confidence_hints": template.confidence_hints
            }
        )
        
        return OptimizedPrompt(
            full_prompt=full_prompt,
            field_name=field_name,
            model_name=model_name,
            document_type=document_type,
            role=role,
            includes_examples=add_examples and len(self._get_examples_for_field(field_name)) > 0,
            dynamic_adjustments=adjustments
        )
    
    def get_prompt_template(self, template_name: str) -> Optional[PromptTemplate]:
        """Retrieve a prompt template by name."""
        return self.templates.get(template_name)
    
    def register_template(self, template: PromptTemplate) -> None:
        """Register a custom prompt template."""
        key = f"{template.stage}_{template.document_type}_{template.role}"
        self.templates[key] = template
        logger.info(f"Registered template: {key}")
    
    def suggest_prompt_improvements(self, 
                                   field_name: str,
                                   correction_rate: float,
                                   common_errors: List[Tuple[str, int]]) -> List[str]:
        """
        Suggest prompt improvements based on correction patterns.
        
        Args:
            field_name: Field with extraction issues
            correction_rate: Rate of corrections for this field
            common_errors: List of common error patterns
            
        Returns:
            List of improvement suggestions
        """
        suggestions = []
        
        # High correction rate
        if correction_rate > 0.3:
            suggestions.append(
                f"Add explicit negative examples for {field_name} to show what NOT to extract"
            )
            suggestions.append(
                f"Include step-by-step instructions for {field_name} extraction"
            )
        
        # Common error patterns
        if common_errors:
            error_pattern = common_errors[0][0]
            suggestions.append(
                f"Add instruction: 'Avoid {error_pattern} pattern' in {field_name} extraction"
            )
        
        # Consider complexity
        if len(common_errors) > 2:
            suggestions.append(
                f"{field_name} has variable extraction patterns; consider using chain-of-thought prompting"
            )
        
        return suggestions
    
    def generate_few_shot_examples(self,
                                  field_name: str,
                                  correction_records: List) -> List[Dict]:
        """
        Generate few-shot examples from engineer corrections.
        
        Args:
            field_name: Field to generate examples for
            correction_records: List of CorrectionRecord objects
            
        Returns:
            List of few-shot examples with input and expected output
        """
        examples = []
        
        # Filter to field-specific corrections
        field_corrections = [c for c in correction_records if c.field_name == field_name]
        
        # Use up to 3 corrections as examples
        for correction in field_corrections[:3]:
            example = {
                "input": correction.vlm_output or "empty",
                "output": correction.engineer_correction,
                "feedback": correction.feedback_type,
                "instruction": f"Correct the extraction: change '{correction.vlm_output}' to '{correction.engineer_correction}'"
            }
            examples.append(example)
        
        return examples
    
    def apply_role_specific_guidance(self, 
                                    base_prompt: str,
                                    role: str) -> str:
        """
        Apply role-specific guidance to a prompt.
        """
        guidance = self.loader.get(f"vision.roles.{role}")
        if not guidance:
            guidance = self.loader.get("vision.roles.general")
        
        return f"{base_prompt}\n\nRole-specific focus:\n{guidance}"
    
    def _initialize_templates(self) -> None:
        """Initialize default prompt templates."""
        # Stage 1: Classification templates
        self.templates["stage1_unknown_general"] = self._default_stage1_template()
        
        # Specialist Agent Templates (Stage 2 Style)
        self.templates["stage2_doc_text"] = PromptTemplate(
            name="text_agent", stage="stage2", document_type="doc", role="general",
            base_template="You answer based ONLY on document text. Be factual.",
            instructions=["Cite specific sections.", "If not in text, say exactly 'No information available'."],
            examples=[], field_guidance={}, confidence_hints="Report high confidence only if verbatim match."
        )
        self.templates["stage2_doc_layout"] = PromptTemplate(
            name="layout_agent", stage="stage2", document_type="doc", role="general",
            base_template="You are an AECO spatial reasoning agent. Use OCR and layout cues.",
            instructions=["Look for table headers.", "Notice spatial relationships (above/below)."],
            examples=[], field_guidance={}, confidence_hints="Lower confidence if OCR is garbled."
        )
        self.templates["stage2_doc_compliance"] = PromptTemplate(
            name="compliance_agent", stage="stage2", document_type="doc", role="general",
            base_template="You are a standards/compliance auditor.",
            instructions=["Check for references to SBC/IBC.", "Flag missing mandatory clauses."],
            examples=[], field_guidance={}, confidence_hints="Cite specific standard numbers."
        )
        self.templates["stage2_meta_synthesis"] = PromptTemplate(
            name="meta_agent", stage="stage2", document_type="any", role="general",
            base_template="You are a Meta-Agent Synthesis Engine. Choose the most reliable pieces.",
            instructions=["Prioritize higher reliability scores.", "Note conflicts clearly."],
            examples=[], field_guidance={}, confidence_hints="Final synthesis should be engineering-grade."
        )
        self.templates["stage2_main_contract"] = PromptTemplate(
            name="main_contract", stage="stage2", document_type="any", role="general",
            base_template=(
                "You are a World-Class Agentic Brain for AECO. SSOT §7 Strict Chat Protocol.\n\n"
                "CONTEXT:\n{unified_context}\n\n"
                "INSTRUCTIONS:\n{instructions}"
            ),
            instructions=[
                "The 'CERTIFIED FACTS' (Layer 4) block is your ONLY source of truth for engineering data.",
                "The '[SUPPLEMENTARY DISCOVERY CONTEXT]' (Layer 1-3) provides enrichment but MUST NOT override Layer 4 facts.",
                "Answer ONLY using the provided evidence. Do NOT invent data or assume beyond the facts.",
                "If no certified facts match the core requirement of the query, explicitly state: 'No certified facts available for this request.'",
                "Cite every fact used: [Fact <fact_id>].",
                "If CONFLICTS are flagged in Layer 4, DISCLOSE all values and do not choose between them."
            ],
            examples=[], field_guidance={}, confidence_hints="Prioritize Layer 4 over all other context layers."
        )

        # Stage 2: Extraction templates for common fields
        for field in ["equipment_name", "system_type", "capacity", "material", "location"]:
            self.templates[f"stage2_unknown_{field}_general"] = \
                self._default_stage2_template(field)
    
    def _default_stage1_template(self) -> PromptTemplate:
        """Create default Stage 1 classification template from externalized YAML."""
        data = self.loader.get("optimizer.defaults.stage1")
        if not data:
            return PromptTemplate(name="default_stage1", stage="stage1", document_type="unknown", role="general", base_template="", instructions=[], examples=[], field_guidance={}, confidence_hints="")
        return PromptTemplate(
            name="default_stage1",
            stage="stage1",
            document_type="unknown",
            role="general",
            base_template=data.get("system", ""),
            instructions=data.get("instructions", []),
            examples=[],
            field_guidance={},
            confidence_hints=data.get("confidence_hints", "")
        )
    
    def _default_stage2_template(self, field_name: str) -> PromptTemplate:
        """Create default Stage 2 extraction template from externalized YAML."""
        data = self.loader.get("optimizer.defaults.stage2")
        if not data:
            return PromptTemplate(name=f"default_stage2_{field_name}", stage="stage2", document_type="unknown", role="general", base_template="", instructions=[], examples=[], field_guidance={}, confidence_hints="")

        return PromptTemplate(
            name=f"default_stage2_{field_name}",
            stage="stage2",
            document_type="unknown",
            role="general",
            base_template=data.get("system", ""),
            instructions=[i.replace("{field_name}", field_name) for i in data.get("instructions", [])],
            examples=[],
            field_guidance={},
            confidence_hints=data.get("confidence_hints", "")
        )
    
    def _substitute_template(self, template: str, variables: Dict[str, str]) -> str:
        """Substitute variables in template."""
        result = template
        for key, value in variables.items():
            # Replace both {key} and {{key}} patterns
            result = result.replace("{{" + key + "}}", str(value or ""))
            result = result.replace("{" + key + "}", str(value or ""))
        return result
    
    def _get_examples_for_field(self, field_name: str) -> List[Dict]:
        """Get few-shot examples for a field from correction history."""
        if not self.correction_collector:
            return []
        
        # Would call correction_collector to get examples
        return []
    
    def _format_few_shot_examples(self, examples: List[Dict]) -> str:
        """Format few-shot examples into prompt text."""
        if not examples:
            return ""
        
        text = "\n\nExamples of correct extractions:\n"
        for i, example in enumerate(examples, 1):
            text += f"\nExample {i}:\n"
            text += f"Input: {example.get('input', '')}\n"
            text += f"Output: {example.get('output', '')}\n"
            if 'instruction' in example:
                text += f"Note: {example['instruction']}\n"
        
        return text
    
    def _get_confidence_guidance(self, field_name: str, model_name: str) -> str:
        """Get confidence guidance from learner."""
        if not self.confidence_learner:
            return ""
        
        accuracy = self.confidence_learner.predict_extraction_accuracy(
            field_name=field_name,
            model_name=model_name
        )
        
        if accuracy < 0.70:
            return f"This field historically has lower accuracy ({accuracy:.0%}). Be conservative with confidence scores."
        elif accuracy > 0.85:
            return f"This field historically extracts well ({accuracy:.0%}). Report high confidence when extraction is clear."
        
        return ""
    
    def _get_problem_area_instructions(self, field_name: str) -> str:
        """Get special instructions for problem areas."""
        if not self.correction_collector:
            return ""
        
        # Would query problem areas and return specific instructions
        return ""
    
    def _format_stage2_prompt_with_context(self,
                                          template: str,
                                          unified_context: str,
                                          field_name: str,
                                          examples: List[Dict]) -> str:
        """Build complete Stage 2 prompt with all components."""
        prompt = template.format(
            unified_context=unified_context,
            field_name=field_name,
            examples=self._format_few_shot_examples(examples) if examples else ""
        )
        return prompt
