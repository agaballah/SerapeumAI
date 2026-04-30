import sqlite3
import logging
from typing import Dict, Any, List, Optional
from src.infra.adapters.cancellation import CancellationToken

logger = logging.getLogger(__name__)

class ChatLLMBridge:
    """Handles LLM interaction logic for the chat interface (Truth Engine V2)."""
    
    def __init__(self, chat_panel):
        self.panel = chat_panel
    
    def classify_intent(self, query: str) -> Dict[str, Any]:
        q = query.lower()
        role = self.panel.role_var.get()
        spec = self.panel.spec_var.get()

        intent = "GENERAL"
        if any(w in q for w in ["risk", "priority", "critical", "issue", "danger"]):
            intent = "RISK"
        elif any(w in q for w in ["exact mention", "where exactly", "cite clause", "quote"]):
            intent = "CLAUSE"
        elif any(w in q for w in ["artifact", "deliverable", "export", "write sow"]):
            intent = "DELIVERABLE"
            
        self.panel.after(0, lambda: self.panel._append("System", f"Intent: **{intent}** | Persona: **{role}-{spec}**"))
        return {"intent": intent, "role": role, "discipline": spec}

    def run_llm_logic(self, user_query: str, attachments: List[str], token: CancellationToken) -> None:
        self.panel._update_status("Resolving Scope...")
        if attachments:
            from src.application.services.document_service import DocumentService
            doc_service = DocumentService(db=self.panel.db, project_root=self.panel.project_dir)
            for att_path in attachments:
                doc_service.ingest_document(abs_path=att_path, project_id=self.panel.project_id)

        if hasattr(self.panel, 'orchestrator') and self.panel.orchestrator:
            self.panel._update_status("Agentic Reasoning...")
            project_id = getattr(self.panel, "project_id", None)
            if not project_id:
                self.panel._append("System", "No active project is loaded for this chat.")
                return

            result = self.panel.orchestrator.answer_question(
                query=user_query,
                project_id=project_id,
                snapshot_id=None,
                cancellation_token=token,
            )

            if isinstance(result, dict) and result.get("answer"):
                # Handle Diagnostic Thinking Stream
                thinking = result.get("thinking", "")
                if thinking:
                    self.panel._append("System", thinking, is_thinking=True)

                answer = result.get("answer", "No answer generated.")
                citations = result.get("citations", [])
                if citations:
                    answer += "\n\n### Citations:\n"
                    for c in citations:
                        answer += f"- *{c.get('source')}*: \"{c.get('quote')}\"\n"

                suggested = result.get("suggested_actions", [])
                if suggested:
                    for s in suggested:
                        def _do_action(text=s):
                            self.panel.txt_input.delete("1.0", "end")
                            self.panel.txt_input.insert("end", text)
                            self.panel._on_send()
                        self.panel.after(0, lambda t=s, h=_do_action: self.panel.renderer.append_suggested_action(t, h))

                self.panel._append("AI", answer)
                
                if self.panel.db and self.panel.project_id:
                    try:
                        self.panel.db.save_chat_message(self.panel.project_id, "assistant", answer)
                    except Exception:
                        pass
        else:
            self.panel._append("System", "Agent Orchestrator not initialized.")

