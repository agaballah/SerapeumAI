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
standards_classifier.py — Intelligent document classification
------------------------------------------------------------

Detects whether a document is a standard/manual or a project document.

Uses:
    • Filename pattern matching
    • LLM-based content analysis (first page)
    • Confidence scoring

Returns:
    {
        "is_standard": bool,
        "confidence": float,
        "category": str,  # building_code, safety_standard, mechanical, etc.
        "organization": str  # SBC, IBC, ASHRAE, etc.
    }
"""

from __future__ import annotations

import os
import re
import json
from typing import Dict, Any


class StandardsClassifier:
    """Classify documents as standards or project documents."""
    
    # Filename patterns that strongly indicate standards
    STANDARD_PATTERNS = [
        # International codes
        r'(?i)\b(ibc|irc|ifc|ipc|imc|iecc|ipmc|iwuic)[\s\-_]?\d{4}\b',  # IBC, IRC, etc.
        r'(?i)\b(sbc|ksa[\s\-_]code)\b',  # Saudi Building Code
        r'(?i)\b(nfpa)[\s\-_]?\d+\b',  # NFPA standards
        r'(?i)\b(ashrae)[\s\-_]?\d+\b',  # ASHRAE standards
        r'(?i)\bbs[\s\-_]en[\s\-_]\d+\b',  # British/European standards
        r'(?i)\biso[\s\-_]\d+\b',  # ISO standards
        r'(?i)\bastm[\s\-_][a-z]\d+\b',  # ASTM standards
        
        # Arabic standards keywords
        r'(?i)(اشتراطات|مواصفات|كود|لائحة|دليل)',  # Requirements, Specs, Code, Regulation, Guide
        
        # Generic patterns
        r'(?i)\b(standard|code|regulation|requirement|specification|guideline|manual)\b',
    ]
    
    # Organization names
    ORGANIZATIONS = {
        'ibc': 'International Code Council',
        'sbc': 'Saudi Building Code',
        'nfpa': 'National Fire Protection Association',
        'ashrae': 'American Society of Heating, Refrigerating and Air-Conditioning Engineers',
        'astm': 'American Society for Testing and Materials',
        'iso': 'International Organization for Standardization',
        'bs': 'British Standards',
        'en': 'European Standards',
    }
    
    CATEGORIES = {
        'building_code': ['ibc', 'irc', 'sbc', 'building code', 'البناء', 'إنشاء'],
        'fire_safety': ['ifc', 'nfpa', 'fire', 'حريق', 'إطفاء'],
        'mechanical': ['imc', 'ashrae', 'hvac', 'تهوية', 'تكييف'],
        'plumbing': ['ipc', 'plumbing', 'سباكة'],
        'electrical': ['nec', 'electrical', 'كهرباء'],
        'energy': ['iecc', 'energy', 'طاقة'],
        'local_regulation': ['اشتراطات', 'لائحة', 'قرار'],
    }
    
    def __init__(self, llm=None):
        """
        Initialize classifier.
        
        Args:
            llm: Optional LLMService instance for content-based classification
        """
        self.llm = llm
    
    def classify(self, file_path: str, use_llm: bool = True) -> Dict[str, Any]:
        """
        Classify a document as standard or project document.
        
        Args:
            file_path: Path to document
            use_llm: Whether to use LLM for content analysis (slower but more accurate)
        
        Returns:
            Classification result dict
        """
        filename = os.path.basename(file_path)
        
        # Step 1: Filename-based classification
        filename_result = self._classify_by_filename(filename)
        
        # If high confidence from filename, return early
        if filename_result['confidence'] >= 0.9:
            return filename_result
        
        # Step 2: LLM-based classification (if available and requested)
        if use_llm and self.llm and os.path.exists(file_path):
            llm_result = self._classify_by_content(file_path)
            
            # Combine results (weighted average)
            combined_confidence = (filename_result['confidence'] * 0.3 + 
                                 llm_result['confidence'] * 0.7)
            
            return {
                'is_standard': llm_result['is_standard'],
                'confidence': combined_confidence,
                'category': llm_result['category'] or filename_result['category'],
                'organization': llm_result['organization'] or filename_result['organization'],
                'method': 'combined'
            }
        
        return filename_result
    
    def _classify_by_filename(self, filename: str) -> Dict[str, Any]:
        """Classify based on filename patterns."""
        filename_lower = filename.lower()
        
        # Check against known patterns
        matched_patterns = []
        for pattern in self.STANDARD_PATTERNS:
            if re.search(pattern, filename):
                matched_patterns.append(pattern)
        
        if matched_patterns:
            # Extract organization
            org = self._extract_organization(filename)
            category = self._infer_category(filename)
            
            return {
                'is_standard': True,
                'confidence': 0.95,
                'category': category,
                'organization': org,
                'method': 'filename'
            }
        
        # Check for generic keywords with lower confidence
        generic_keywords = ['standard', 'code', 'specification', 'guideline', 'manual']
        if any(kw in filename_lower for kw in generic_keywords):
            return {
                'is_standard': True,
                'confidence': 0.6,
                'category': 'unknown',
                'organization': 'Unknown',
                'method': 'filename'
            }
        
        # Default: not a standard
        return {
            'is_standard': False,
            'confidence': 0.8,
            'category': 'project_document',
            'organization': None,
            'method': 'filename'
        }
    
    def _classify_by_content(self, file_path: str) -> Dict[str, Any]:
        """Classify based on document content using LLM."""
        # Extract first page text
        first_page_text = self._extract_first_page(file_path)
        
        if not first_page_text:
            return {
                'is_standard': False,
                'confidence': 0.5,
                'category': 'unknown',
                'organization': None,
                'method': 'content'
            }
        
        # Use LLM to analyze
        system_prompt = (
            "You are a document classifier specializing in construction and building standards.\n"
            "Analyze the provided text and determine if it is a STANDARD/CODE/REGULATION or a PROJECT DOCUMENT.\n\n"
            "Standards include: building codes (IBC, SBC), safety standards (NFPA), technical standards (ASHRAE, ASTM), "
            "local regulations, and official guidelines.\n\n"
            "Project documents include: contracts, specifications, drawings, reports, correspondence.\n\n"
            "Return ONLY a JSON object:\n"
            "{\n"
            '  "is_standard": true/false,\n'
            '  "confidence": 0.0-1.0,\n'
            '  "category": "building_code|fire_safety|mechanical|electrical|plumbing|energy|local_regulation|project_document",\n'
            '  "organization": "Name of standards organization or null"\n'
            "}"
        )
        
        user_prompt = f"Document excerpt:\n\n{first_page_text[:2000]}"
        
        try:
            response = self.llm.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1
            )
            
            # Extract content
            content = response
            if isinstance(response, dict) and 'choices' in response:
                content = response['choices'][0]['message']['content']
            
            # Parse JSON
            clean = str(content).strip()
            if clean.startswith('```json'):
                clean = clean[7:]
            if clean.startswith('```'):
                clean = clean[3:]
            if clean.endswith('```'):
                clean = clean[:-3]
            clean = clean.strip()
            
            result = json.loads(clean)
            result['method'] = 'content'
            return result
            
        except Exception as e:
            # Fallback
            return {
                'is_standard': False,
                'confidence': 0.5,
                'category': 'unknown',
                'organization': None,
                'method': 'content_error',
                'error': str(e)
            }
    
    def _extract_first_page(self, file_path: str) -> str:
        """Extract text from first page of document."""
        ext = os.path.splitext(file_path)[1].lower()
        
        # For PDFs, try to get first page
        if ext == '.pdf':
            try:
                # Using pypdf instead of PyMuPDF (GPL-free alternative)
                from pypdf import PdfReader
                reader = PdfReader(file_path)
                if len(reader.pages) > 0:
                    text = reader.pages[0].extract_text()
                    return text
            except Exception:
                pass
        
        # For images, would need OCR (skip for now to keep it fast)
        # For other types, return empty
        return ""
    
    def _extract_organization(self, filename: str) -> str:
        """Extract organization name from filename."""
        filename_lower = filename.lower()
        
        for org_key, org_name in self.ORGANIZATIONS.items():
            if org_key in filename_lower:
                return org_name
        
        return "Unknown"
    
    def _infer_category(self, filename: str) -> str:
        """Infer category from filename."""
        filename_lower = filename.lower()
        
        for category, keywords in self.CATEGORIES.items():
            if any(kw in filename_lower for kw in keywords):
                return category
        
        return "unknown"
