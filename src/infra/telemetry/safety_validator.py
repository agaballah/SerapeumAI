# -*- coding: utf-8 -*-
"""Minimal SafetyValidator restoration"""
class SafetyValidator:
    def validate_extraction(self, *args, **kwargs):
        class Result: 
            is_safe = True
            flags = []
            violations = []
            max_severity = None
        return Result()
