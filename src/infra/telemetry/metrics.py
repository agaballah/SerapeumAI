# -*- coding: utf-8 -*-
import time
from contextlib import contextmanager

class Metrics:
    """Minimal restoration of Metrics timer"""
    def __init__(self, project_id=None, project_root=None):
        self.project_id = project_id
    
    @contextmanager
    def timer(self, name, **kwargs):
        start = time.time()
        yield
        duration = time.time() - start
