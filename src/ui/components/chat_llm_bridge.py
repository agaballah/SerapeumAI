import sqlite3
import logging
from typing import Dict, Any, List, Optional
from src.infra.adapters.cancellation import CancellationToken

logger = logging.getLogger(__name__)

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
        Classify user query intent for Truth Engine V2.
        """
    def classify_intent(self, query: str) -> Dict[str, Any]:
        """
        Classify user query intent for Truth Engine V2.
        """
        q = query.lower()
        role = self.panel.role_var.get()
        spec = self.panel.spec_var.get()

        # Intent Mapping (Simplified for V2 Routing)
        intent = "GENERAL"
        mode = "Mode B"
        desc = "Spec/Doc Summary (General)"
        
        if any(w in q for w in ["risk", "priority", "critical", "issue", "danger"]):
            intent = "RISK"
        elif any(w in q for w in ["exact mention", "where exactly", "cite clause", "quote"]):
            intent = "CLAUSE"
            mode = "Mode A"
            desc = "Clause Finder (Strict Evidence)"
        elif any(w in q for w in ["artifact", "deliverable", "export", "write sow"]):
            intent = "DELIVERABLE"
            mode = "Mode F"
            desc = "Actionable Deliverables"
            
        # UI Message (Truth Engine V2 Requirement)
        self.panel.after(0, lambda: self.panel._append("System", f"🧭 Routed to Intent: **{intent}** for Persona: **{role}-{spec}**"))
        
        return {
            "mode": mode,
            "intent": intent, 
            "role": role, 
            "discipline": spec,
            "strict": mode == "Mode A",
            "scope": "local_only",
            "desc": desc
        }

    def _fetch_persona_template(self, role: str, disc: str, intent: str) -> Optional[str]:
        from src.infra.persistence.global_db_initializer import global_db_path
        try:
            conn = sqlite3.connect(global_db_path())
            # Try specific match
            row = conn.execute(
                "SELECT system_instructions FROM persona_templates WHERE role = ? AND discipline = ? AND intent = ?",
                (role, disc, intent)
            ).fetchone()
            if row: 
                conn.close()
                return row[0]
            
            # Try default match for intent
            row = conn.execute(
                "SELECT system_instructions FROM persona_templates WHERE role = '*' AND discipline = '*' AND intent = ?",
                (intent,)
            ).fetchone()
            if row:
                conn.close()
                return row[0]
            
            conn.close()
        except Exception as e:
            logger.warning(f"Failed to fetch persona template: {e}")
        return None

    def get_mode_instructions(self, mode_info: Dict[str, Any], query: str = "") -> str:
        """
        Generate system instructions including Persona Templates from the Global DB.
        """
        mode = mode_info["mode"]
        intent = mode_info.get("intent", "GENERAL")
        role = mode_info.get("role", "PMC")
        disc = mode_info.get("discipline", "Project Manager")
        
        # 1. Fetch Global Persona Template
        template_instr = self._fetch_persona_template(role, disc, intent)
        
        # 2. Get Agent Instructions
        if hasattr(self.panel, 'orchestrator') and self.panel.orchestrator:
            try:
                op = self.panel.orchestrator.optimizer.generate_stage1_prompt(
                    query=query,
                    user_role=role,
                    model_name=self.panel.llm.model
                )
                base_instr = op.full_prompt
            except Exception as e:
                logger.warning(f"[ChatLLMBridge] Optimizer failed: {e}")
                base_instr = f"You are a helpful {role} specializing in {disc}."

        else:
            base_instr = f"Summarize and synthesize based on context as a {role}."

        # Merge
        final_instr = f"FORCE PERSONALITY: {template_instr}\n\n{base_instr}" if template_instr else base_instr
        return final_instr

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
