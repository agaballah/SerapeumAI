"""
quality_scoring.py - Vision Model Output Quality Assessment
------------------------------------------------------------
PHASE 1 FIX: Scores VLM output quality to detect vague/generic descriptions.
"""

def assess_vision_quality(description: str, full_text: str, image_path: str) -> dict:
    """
    Score VLM output quality on 0-1 scale.
    
    Args:
        description: VLM's description field
        full_text: VLM's extracted text
        image_path: Path to image (for future enhancements)
    
    Returns:
        {
            "quality_score": float (0-1),
            "flags": List[str],
            "needs_retry": bool,
            "human_review": bool
        }
    """
    score = 1.0
    flags = []
    
    # [FIX] Handle structured input (dict/list) from VLM
    if not isinstance(description, str):
        import json
        try:
            description = json.dumps(description)
        except Exception:
            description = str(description)
    
    # 1. Hedging language detection (-0.3)
    hedging = [
        "appears to be", "possibly", "might be", "seems", 
        "could be", "looks like", "maybe", "perhaps"
    ]
    if any(phrase in description.lower() for phrase in hedging):
        score -= 0.3
        flags.append("hedging_language")
    
    # 2. Length check - too short = vague (-0.2)
    if len(description.strip()) < 100:
        score -= 0.2
        flags.append("too_short")
    
    # 3. Generic phrases detection (-0.25)
    generic = [
        "mix of text and numbers",
        "scattered throughout",
        "not clearly structured",
        "various elements",
        "contains information"
    ]
    if any(phrase in description.lower() for phrase in generic):
        score -= 0.25
        flags.append("generic_description")
    
    # 4. Technical detail check (-0.15)
    technical_indicators = [
        "table", "column", "row", "drawing", "specification",
        "standard", "code", "requirement", "section", "diagram",
        "equipment", "contractor", "schedule"
    ]
    if not any(ind in description.lower() for ind in technical_indicators):
        score -= 0.15
        flags.append("lacks_technical_detail")
    
    # 5. OCR quality check - garbled text (-0.2)
    if full_text and len(full_text.split()) > 10:
        words = full_text.split()
        # Check for excessive short tokens (possible OCR errors)
        short_tokens = sum(1 for w in words if len(w) <= 2)
        if short_tokens / len(words) > 0.5:
            score -= 0.2
            flags.append("garbled_ocr")
    
    # Clamp score to [0, 1]
    score = max(0.0, min(1.0, score))
    
    return {
        "quality_score": round(score, 2),
        "flags": flags,
        "needs_retry": score < 0.6,
        "human_review": score < 0.4 or "garbled_ocr" in flags
    }
