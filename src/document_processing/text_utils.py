import re

def normalize_arabic(text: str) -> str:
    """
    Standardizes Arabic characters for searchability:
    - Alef variants (إ، أ، آ) -> ا
    - Ta Marbuta (ة) -> ه
    - Alef Maqsura (ى) -> Maqsura usually stays or goes to Ya depending on region.
      Here we target Alef variants and Ta Marbuta.
    """
    if not text:
        return ""
    
    # 1. Alef variants
    text = re.sub(r"[أإآ]", "ا", text)
    
    # 2. Ta Marbuta to Ha
    text = re.sub(r"ة", "ه", text)
    
    # 3. Alef Maqsura (ى) to Ya (ي) - Based on test requirement
    text = re.sub(r"ى", "ي", text)
    
    return text

def is_gibberish(text: str, custom_threshold: float = 0.5) -> bool:
    """
    Checks if text is likely gibberish (OCR noise or corrupt data).
    Detects based on repeated non-printable or symbol clusters.
    """
    if not text:
        return False
        
    # Heuristic 1: Replacement characters (\ufffd)
    if text.count("\ufffd") > 2:
        return True
        
    # Heuristic 2: Long sequences of identical characters without spaces
    words = text.split()
    if not words and len(text) > 10:
        return True
    
    for word in words:
        if len(word) > 40: # Suspiciously long string
            return True
            
    return False
