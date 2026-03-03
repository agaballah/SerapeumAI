# -*- coding: utf-8 -*-
"""
chat_llm_bridge.py — LLM Interaction Logic for ChatPanel
---------------------------------------------------------
Extracted from chat_panel.py for better code organization and testability.
Handles intent classification, mode instructions, and LLM reasoning.
"""

from typing import Dict, Any, List
from src.infra.adapters.cancellation import CancellationToken


class ChatLLMBridge:
    """Handles LLM interaction logic for the chat interface."""
    
    def __init__(self, chat_panel):
        """
        Initialize with reference to parent ChatPanel.
        
        Args:
            chat_panel: The parent ChatPanel instance
        """
        self.panel = chat_panel
    
    def classify_intent(self, query: str) -> Dict[str, Any]:
        """
        Classify user query intent to determine response mode.
        
        Args:
            query: User query string
            
        Returns:
            Dict with mode, strict, scope, and desc keys
        """
        q = query.lower()
        
        # Hard Force: Mode F for deliverables/artifacts
        artifact_triggers = ["artifact", "deliverable", "full sow", "write sow", "generate sow", "export", "docx", "pdf"]
        if any(w in q for w in artifact_triggers):
             return {"mode": "Mode F", "strict": False, "scope": "local_only", "desc": "Actionable Deliverables / Artifact (Deterministic)"}

        if self.panel.compliance_var.get():
            return {"mode": "Mode C", "strict": False, "scope": "local+web", "desc": "Compliance / Standards Check (Forced)"}
        
        mode_a_words = [
            "exact mention", "where exactly", "cite clause", "quote", "exact text",
            "where", "section", "clause", "page", "as per spec", "show me", "provide citation", "verbatim"
        ]
        if any(w in q for w in mode_a_words) or ('"' in query or "'" in query):
            return {"mode": "Mode A", "strict": True, "scope": "local_only", "desc": "Clause Finder (Strict Evidence)"}
        
        if any(w in q for w in ["compliance", "compliant", "nfpa", "ashrae", "per code", "standard requires"]):
            return {"mode": "Mode C", "strict": False, "scope": "local+web", "desc": "Compliance / Standards Check"}
        
        if any(w in q for w in ["conflict", "clash", "inconsistency", "disagree"]):
            return {"mode": "Mode D", "strict": True, "scope": "local_only", "desc": "Cross-Doc Conflict Detection"}
        
        if any(w in q for w in ["ifc", "bim", "p6", "ms project", "activity", "schedule", "duration"]):
            return {"mode": "Mode E", "strict": False, "scope": "local_only", "desc": "BIM / Schedule Q&A"}
        
        if any(w in q for w in ["rfi", "draft", "checklist", "memo", "template", "deliverable", "artifact", "sow"]):
            return {"mode": "Mode F", "strict": False, "scope": "local_only", "desc": "Actionable Deliverables"}
        
        return {"mode": "Mode B", "strict": False, "scope": "local_only", "desc": "Spec/Doc Summary (General)"}

    def get_mode_instructions(self, mode_info: Dict[str, Any]) -> str:
        """
        Generate system instructions based on classified mode.
        
        Args:
            mode_info: Dict with mode, desc, strict, scope keys
            
        Returns:
            Instruction string for LLM system prompt
        """
        mode, desc, strict, scope = mode_info["mode"], mode_info["desc"], mode_info["strict"], mode_info["scope"]
        instr = f"You are operating in '{mode}: {desc}' mode. "
        if strict:
            instr += "Find and cite EXACT mentions/clauses. DO NOT paraphrase. State clearly if evidence is missing. "
        else:
            instr += "Summarize and synthesize based on context. "
        if scope == "local_only":
            instr += "Focus EXCLUSIVELY on project documents. No web search unless tool-specific. "
        else:
            instr += "You may use web search for standards/general info. "
        instr += "Always provide a procedural <plan> only (steps + tools). No private reasoning."
        return instr

    def run_llm_logic(self, user_query: str, attachments: List[str], token: CancellationToken) -> None:
        """
        Execute unified agentic logic to answer user query.
        
        Args:
            user_query: User's question/request
            attachments: List of file paths attached to query
            token: Cancellation token for abort capability
        """
        # 1. Scope Resolution & Ingestion
        self.panel._update_status("Resolving Scope...")
        if attachments:
            from src.application.services.document_service import DocumentService
            doc_service = DocumentService(db=self.panel.db, project_root=self.panel.project_dir)
            for att_path in attachments:
                doc_service.ingest_document(abs_path=att_path, project_id=self.panel.project_id)

        # 2. Agentic Reasoning
        if hasattr(self.panel, 'orchestrator') and self.panel.orchestrator:
            self.panel._update_status("Agentic Reasoning...")
            # Request streaming fallback when possible so UI can progressively render tokens
            result = self.panel.orchestrator.answer_question(query=user_query, stream=True, cancellation_token=token)

            # If orchestrator returned a streaming generator, render progressively
            if isinstance(result, dict) and result.get("stream") is not None:
                gen = result.get("stream")
                collected = []
                # Insert a placeholder assistant message, then update it progressively
                self.panel.after(0, lambda: self.panel._append("AI", ""))
                try:
                    for chunk in gen:
                        if token and token.is_cancelled():
                            break
                        text = str(chunk or "")
                        collected.append(text)
                        # Update last appended assistant message by appending new chunk
                        self.panel.after(0, lambda s="".join(collected): self.panel._append("AI", s))
                except Exception:
                    # In case streaming fails, fallback to a final blocking call
                    try:
                        resp = self.panel.llm.chat(
                            messages=[{"role": "system", "content": "Fallback"}, {"role": "user", "content": user_query}],
                            task_type="universal",
                            temperature=0.3
                        )
                        txt = (resp.get("choices") or [{}])[0].get("message", {}).get("content", "")
                        self.panel.after(0, lambda: self.panel._append("AI", txt))
                        collected = [txt]
                    except Exception:
                        pass

                final_answer = "".join(collected)
                try:
                    self.panel.db.save_chat_message(self.panel.project_id, "assistant", final_answer)
                except Exception:
                    pass
                return

            # Otherwise non-streaming result (normal path)
            if isinstance(result, dict) and result.get("answer"):
                thinking = result.get("thinking", "")
                if thinking:
                    self.panel.after(0, lambda: self.panel._append("System", f"🧠 **Thinking Process**:\n{thinking}"))

                answer = result.get("answer", "No answer generated.")
                citations = result.get("citations", [])
                if citations:
                    answer += "\n\n### Citations:\n"
                    for c in citations:
                        answer += f"- *{c.get('source')}*: \"{c.get('quote')}\"\n"

                actions = result.get("suggested_actions", [])
                if actions:
                    answer += "\n\n**Suggested Actions**:\n"
                    for a in actions:
                        answer += f"- {a}\n"

                self.panel.after(0, lambda: self.panel._append("AI", answer))
                try:
                    self.panel.db.save_chat_message(self.panel.project_id, "assistant", answer)
                except Exception:
                    pass
                return

        # If no orchestrator or nothing produced, fallback
        self.panel.after(0, lambda: self.panel._append("System", "❌ Agent Orchestrator not initialized."))
