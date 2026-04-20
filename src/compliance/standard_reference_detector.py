# -*- coding: utf-8 -*-
# Copyright (c) 2025 Ahmed Gaballa
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
standard_reference_detector.py — Standard Reference Detection
-------------------------------------------------------------
Detects and extracts standard references from document text.
Supports TMSS, TESP, TESB, SBC, IBC, NFPA, and other patterns.
"""

import re
from typing import List, Dict, Any


class StandardReferenceDetector:
    """
    Detects standard references in text using regex patterns.
    """
    
    # Regex patterns for different standard types
    PATTERNS = {
        "TMSS": re.compile(r'\bTMSS-(\d+)\b', re.IGNORECASE),
        "TESP": re.compile(r'\bTESP-(\d{5})\b', re.IGNORECASE),
        "TESB": re.compile(r'\bTESB-(\d+)\b', re.IGNORECASE),
        "SBC": re.compile(r'\bSBC\s+(?:Section\s+)?(\d+(?:\.\d+)*)\b', re.IGNORECASE),
        "IBC": re.compile(r'\bIBC\s+(?:Section\s+)?(\d+(?:\.\d+)*)\b', re.IGNORECASE),
        "NFPA": re.compile(r'\bNFPA\s+(\d+)\b', re.IGNORECASE),
        "ASHRAE": re.compile(r'\bASHRAE\s+(\d+(?:-\d+)?)\b', re.IGNORECASE),
        "TIA": re.compile(r'\bTIA[-/](\d+(?:-[A-Z])?)\b', re.IGNORECASE),
    }
    
    def __init__(self):
        pass
    
    def detect_references(self, text: str) -> List[Dict[str, Any]]:
        """
        Detect all standard references in text.
        
        Returns:
            List of dictionaries with:
            {
                "standard_type": "TMSS",
                "ref_text": "TMSS-01",
                "clause_hint": "01",
                "position": (start, end)
            }
        """
        if not text:
            return []
        
        references = []
        seen = set()  # Deduplicate
        
        for std_type, pattern in self.PATTERNS.items():
            for match in pattern.finditer(text):
                ref_text = match.group(0)
                clause_hint = match.group(1) if match.groups() else ""
                
                # Create unique key for deduplication
                key = (std_type, ref_text.upper())
                if key in seen:
                    continue
                seen.add(key)
                
                references.append({
                    "standard_type": std_type,
                    "ref_text": ref_text,
                    "clause_hint": clause_hint,
                    "position": (match.start(), match.end())
                })
        
        # Sort by position
        references.sort(key=lambda x: x["position"][0])
        
        return references
    
    def extract_from_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract standard references from entity list.
        
        Args:
            entities: List of entities from analysis_engine
        
        Returns:
            List of standard reference entities
        """
        std_refs = []
        
        for ent in entities:
            if ent.get("type") == "standard_reference":
                value = ent.get("value", "")
                
                # Try to classify the reference
                ref_type = self._classify_reference(value)
                
                std_refs.append({
                    "ref_text": value,
                    "standard_type": ref_type,
                    "confidence": ent.get("confidence", 0.0),
                    "source": "llm_entity"
                })
        
        return std_refs
    
    def _classify_reference(self, ref_text: str) -> str:
        """
        Classify a reference text into a standard type.
        """
        ref_upper = ref_text.upper()
        
        if "TMSS" in ref_upper:
            return "TMSS"
        elif "TESP" in ref_upper:
            return "TESP"
        elif "TESB" in ref_upper:
            return "TESB"
        elif "SBC" in ref_upper:
            return "SBC"
        elif "IBC" in ref_upper:
            return "IBC"
        elif "NFPA" in ref_upper:
            return "NFPA"
        elif "ASHRAE" in ref_upper:
            return "ASHRAE"
        elif "TIA" in ref_upper:
            return "TIA"
        else:
            return "OTHER"
    
    def create_doc_standards_mapping(
        self,
        project_id: str,
        doc_id: str,
        references: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Create doc_standards mapping records.
        
        Returns:
            List of mapping dictionaries ready for database insertion
        """
        mappings = []
        
        for ref in references:
            mappings.append({
                "project_id": project_id,
                "source_doc_id": doc_id,
                "ref_text": ref["ref_text"],
                "standard_type": ref.get("standard_type", "OTHER"),
                "clause_hint": ref.get("clause_hint", ""),
                "heuristic_type": "regex" if ref.get("source") != "llm_entity" else "llm"
            })
        
        return mappings


def detect_and_store_references(db, project_id: str, doc_id: str, text: str, entities: List[Dict[str, Any]]):
    """
    Convenience function to detect references and store in database.
    
    Args:
        db: DatabaseManager instance
        project_id: Project ID
        doc_id: Document ID
        text: Document text
        entities: Entities from analysis
    """
    detector = StandardReferenceDetector()
    
    # Detect from text
    text_refs = detector.detect_references(text)
    
    # Extract from entities
    entity_refs = detector.extract_from_entities(entities)
    
    # Combine and deduplicate
    all_refs = text_refs + entity_refs
    unique_refs = {}
    for ref in all_refs:
        key = ref["ref_text"].upper()
        if key not in unique_refs:
            unique_refs[key] = ref
    
    # Store in doc_references table
    import time
    for ref in unique_refs.values():
        try:
            db._exec(
                """
                INSERT OR IGNORE INTO doc_references
                (project_id, source_doc_id, raw_text, heuristic_type, created_ts)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    doc_id,
                    ref["ref_text"],
                    ref.get("heuristic_type", "regex"),
                    int(time.time())
                )
            )
        except Exception as e:
            print(f"[WARN] Failed to store reference: {e}")
    
    print(f"[StandardRefs] Stored {len(unique_refs)} references for {doc_id}")
    return list(unique_refs.values())
