# -*- coding: utf-8 -*-
import json
import tkinter as tk
from tkinter import ttk
from typing import Any

# Duck typing for ScrolledText
try:
    from ttkbootstrap.scrolled import ScrolledText
except ImportError:
    ScrolledText = tk.Text

class ConversationManager:
    def __init__(self, db: Any, project_id: str, history_frame: ttk.Frame):
        self.db = db
        self.project_id = project_id
        self.history_frame = history_frame
        
        # UI Setup
        ttk.Label(self.history_frame, text="Conversation History", font=("Segoe UI", 10, "bold")).pack(pady=5)
        
        if ScrolledText != tk.Text:
            self.history_text = ScrolledText(self.history_frame, padding=5, autohide=True, width=30)
        else:
            self.history_text = tk.Text(self.history_frame, wrap="word", width=30)
            
        self.history_text.pack(fill="both", expand=True, padx=2, pady=2)
        
        # Configure widget
        txt = self.history_text.text if hasattr(self.history_text, 'text') else self.history_text
        txt.configure(state="disabled", font=("Segoe UI", 9))

    def load_history_to_view(self, renderer) -> None:
        """Load history into the main chat view asynchronously."""
        import threading
        
        def _load_task():
            try:
                # Use a larger limit for initial load, or no limit if preferred
                hist = self.db.get_chat_history(self.project_id, limit=100)
                if not hist:
                    return
                
                # Reverse to show oldest first
                messages = []
                for h in reversed(hist):
                    role_display = "You" if h["role"] == "user" else h["role"]
                    atts = json.loads(h.get("attachments_json", "[]"))
                    messages.append((role_display, h["content"], atts))
                
                # Batch update UI
                def _update_ui():
                    for role, content, atts in messages:
                        renderer.append(role, content, atts)
                    renderer.append("System", "--- History Loaded ---")
                
                self.history_frame.after(0, _update_ui)
            except Exception:
                pass

        threading.Thread(target=_load_task, daemon=True).start()

    def refresh_history_panel(self) -> None:
        """Refresh the side panel history asynchronously."""
        import threading
        
        def _refresh_task():
            try:
                hist = self.db.get_chat_history(self.project_id, limit=50)
                
                # Format content in background
                formatted_lines = []
                for h in hist:
                    role = "You" if h["role"] == "user" else h["role"]
                    content = h["content"][:100] + "..." if len(h["content"]) > 100 else h["content"]
                    ts = h.get("ts", "")
                    formatted_lines.append((role, ts, content))
                
                def _update_ui():
                    txt_widget = self.history_text.text if hasattr(self.history_text, 'text') else self.history_text
                    txt_widget.configure(state="normal")
                    txt_widget.delete("1.0", "end")
                    
                    for role, ts, content in formatted_lines:
                        txt_widget.insert("end", f"[{role}] {ts}\n", "bold")
                        txt_widget.insert("end", f"{content}\n\n")
                    
                    txt_widget.configure(state="disabled")
                
                self.history_frame.after(0, _update_ui)
            except Exception as e:
                def _show_error():
                    txt_widget = self.history_text.text if hasattr(self.history_text, 'text') else self.history_text
                    txt_widget.configure(state="normal")
                    txt_widget.insert("end", f"Error loading history: {e}")
                    txt_widget.configure(state="disabled")
                self.history_frame.after(0, _show_error)

        threading.Thread(target=_refresh_task, daemon=True).start()

    def get_context(self) -> dict:
        """Get basic project context for the LLM."""
        try:
            count = self.db.count_documents(project_id=self.project_id)
            return {
                "document_count": count,
                "project_id": self.project_id,
            }
        except Exception:
            return {"document_count": 0, "project_id": self.project_id}
