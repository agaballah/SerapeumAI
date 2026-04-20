# -*- coding: utf-8 -*-
import logging
import json
import time
from typing import Any, Dict, Optional

class LLMLogger:
    def __init__(self):
        self.logger = logging.getLogger("llm_audit")

    def log_call(self, task_type: str, model: str, system_prompt: str, user_prompt: str, temperature: float, max_tokens: int, context_length: int, metadata: Optional[Dict[str, Any]] = None) -> str:
        call_id = f"llm_{int(time.time())}"
        self.logger.info(f"LLM Call [{call_id}] - Task: {task_type}, Model: {model}")
        return call_id

    def log_response(self, call_id: str, response: Any, duration_seconds: float, success: bool, tokens_used: Optional[Dict[str, int]] = None, error: Optional[str] = None):
        status = "SUCCESS" if success else f"FAILURE: {error}"
        self.logger.info(f"LLM Response [{call_id}] - Status: {status}, Duration: {duration_seconds:.2f}s")

_llm_logger = LLMLogger()

def get_llm_logger():
    return _llm_logger
