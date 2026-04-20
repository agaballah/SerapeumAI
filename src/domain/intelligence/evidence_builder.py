# -*- coding: utf-8 -*-
class EvidencePackBuilder:
    """Minimal restoration of EvidencePackBuilder"""
    def __init__(self, db):
        self.db = db
    def build_pack(self, query, doc_ids, task_mode):
        return {"documents": [], "status": "No Evidence Found"}
