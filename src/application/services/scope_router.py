# -*- coding: utf-8 -*-
import os
from dataclasses import dataclass, field
from typing import List, Literal, Optional, Dict, Any

ScopeDecisionStatus = Literal["resolved", "ambiguous", "rejected"]
ScopeDest = Literal["project", "global", "ambiguous"]

@dataclass
class ScopeDecision:
    status: ScopeDecisionStatus
    scope: ScopeDest
    confidence: float
    reason_codes: List[str] = field(default_factory=list)
    normalized_title: str = ""
    doc_type: str = "general_document"
    discipline: str = ""
    source_channel: str = "unknown"
    suggested_doc_key_basis: str = ""
    requires_user_resolution: bool = False

class ScopeRouter:
    """
    Pure decision logic for document routing. No persistence.
    """
    def __init__(self, standards_classifier=None, doc_classifier=None):
        self.standards_classifier = standards_classifier
        self.doc_classifier = doc_classifier

    def route_file(
        self,
        abs_path: str,
        source_channel: str = "unknown",
        origin_context: str = "",
        explicit_scope: Optional[ScopeDest] = None
    ) -> ScopeDecision:
        if not os.path.exists(abs_path):
            return ScopeDecision(
                status="rejected",
                scope="ambiguous",
                confidence=1.0,
                reason_codes=["FILE_NOT_FOUND"],
            )

        filename = os.path.basename(abs_path)
        
        # 1. Explicit UI/User override is respected
        if explicit_scope in ("project", "global"):
            return ScopeDecision(
                status="resolved",
                scope=explicit_scope,
                confidence=1.0,
                reason_codes=["EXPLICIT_USER_OVERRIDE"],
                normalized_title=filename,
                source_channel=source_channel,
                suggested_doc_key_basis=filename
            )

        # 2. Standards tool explicitly implies global structure
        if origin_context == "standards_import" or source_channel == "standards_ui":
            return ScopeDecision(
                status="resolved",
                scope="global",
                confidence=0.9,
                doc_type="standard",
                reason_codes=["STANDARDS_IMPORT_CONTEXT"],
                normalized_title=filename,
                source_channel=source_channel,
                suggested_doc_key_basis=filename
            )
            
        # 3. Consult standard classifier
        if self.standards_classifier:
            try:
                std_hint = self.standards_classifier.classify(abs_path, use_llm=False)
                if std_hint and std_hint.get("is_standard"):
                    return ScopeDecision(
                        status="resolved",
                        scope="global",
                        confidence=std_hint.get("confidence", 0.8),
                        doc_type=std_hint.get("category", "standard"),
                        reason_codes=["CLASSIFIER_DETECTED_STANDARD"],
                        normalized_title=filename,
                        source_channel=source_channel,
                        suggested_doc_key_basis=filename
                    )
            except Exception:
                pass

        # 4. Chat attachments are highly ambiguous unless classified
        if source_channel == "chat_upload":
            return ScopeDecision(
                status="ambiguous",
                scope="ambiguous",
                confidence=0.5,
                reason_codes=["CHAT_ATTACHMENT_NEEDS_SCOPE_CONFIRMATION"],
                requires_user_resolution=True,
                normalized_title=filename,
                source_channel=source_channel,
                suggested_doc_key_basis=filename
            )

        # 5. Project scans default to project
        if source_channel in ("project_scan", "project_ui_upload"):
            return ScopeDecision(
                status="resolved",
                scope="project",
                confidence=0.7,
                reason_codes=["PROJECT_CONTEXT_DEFAULT"],
                normalized_title=filename,
                source_channel=source_channel,
                suggested_doc_key_basis=filename
            )

        # 6. Fallback
        return ScopeDecision(
            status="ambiguous",
            scope="ambiguous",
            confidence=0.0,
            reason_codes=["NO_STRONG_SCOPE_SIGNAL"],
            requires_user_resolution=True,
            normalized_title=filename,
            source_channel=source_channel,
            suggested_doc_key_basis=filename
        )
