# -*- coding: utf-8 -*-
"""Minimal PromptValidator restoration"""
def validate_prompt(prompt, *args, **kwargs): return True, []
def sanitize_user_prompt(prompt): return prompt
class PromptValidator:
    def validate(self, prompt): return True
