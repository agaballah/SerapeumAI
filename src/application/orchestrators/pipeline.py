# -*- coding: utf-8 -*-
# Copyright (c) 2025 Ahmed Gaballa
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
pipeline.py — Pipeline v3 (Decoupled Architecture)
---------------------------------------------------
Stages:
    1) Ingest (DocumentService) - CPU Only
    2) Vision (VisionWorker) - GPU (Optional)
    3) Analysis (AnalysisEngine) - GPU (Optional)
    4) Compliance/Linking - GPU (Optional)
"""

from __future__ import annotations

import os
import logging

from typing import Any, Callable, Dict, Optional

from src.application.services.document_service import DocumentService
from src.infra.persistence.database_manager import DatabaseManager
from src.infra.adapters.llm_service import LLMService


class Pipeline:
    """Full Project Processing Pipeline (Ingest → Analysis → Linking → Compliance)"""

    def __init__(
        self,
        *,
        db: DatabaseManager,
        llm: Optional[LLMService],
        project_root: str,
        **kwargs
    ):
        self.db = db
        self.llm = llm
        self.project_root = project_root
        self.global_ks = kwargs.get("global_ks")

        # DocumentService is project-scoped (used for ingest only)
        self.docs = DocumentService(db=db, project_root=project_root, global_ks=self.global_ks)
        
        # Telemetry for performance monitoring
        from src.infra.telemetry.metrics import Metrics
        self.metrics = Metrics(project_id="pipeline", project_root=project_root)
        
        from src.application.services.artifact_service import ArtifactService
        art_root = os.path.join(project_root, ".serapeum", "artifacts")
        self.artifact_service = ArtifactService(output_dir=art_root)

    # ------------------------------------------------------------------
    # MODULAR PIPELINE METHODS (Decoupled)
    # ------------------------------------------------------------------
    def run_ingestion(
        self,
        *,
        project_id: str,
        on_progress: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        cancellation_token=None,
        force: bool = False
    ) -> Dict[str, Any]:
        """Stage 1: Ingest project files and identify pending vision work."""
        emit = on_progress or (lambda *_: None)
        
        if cancellation_token:
            cancellation_token.check()
        
        emit("ingest.begin", {"project_id": project_id, "root": self.project_root})

        with self.metrics.timer("pipeline_stage", stage="ingest"):
            result = self.docs.ingest_project(
                project_id=project_id,
                root=self.project_root,
                recursive=True,
                on_progress=emit,
                cancellation_token=cancellation_token,
                force=force,
            )
            
        emit("ingest.complete", result)
        return result

    def run_analysis(
        self,
        *,
        project_id: str,
        fast_mode: bool = False,
        on_progress: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        cancellation_token=None,
    ):
        """
        Run ONLY the Analysis Phase (GPU).
        Requires Analysis Model (Mistral/Llama) to be loaded.
        """
        # Local import to avoid circular dep if any
        from src.analysis_engine.analysis_engine import AnalysisEngine
        
        emit = on_progress or (lambda *_: None)
        
        if cancellation_token:
            cancellation_token.check()
            
        # Ensure LLM is available
        if not self.db or not self.llm:
             raise RuntimeError("Pipeline initialized without Database or LLM for Analysis.")

        emit("analysis.begin", {"project_id": project_id, "mode": "fast" if fast_mode else "deep"})
        
        ae = AnalysisEngine(db=self.db, llm=self.llm)
        
        with self.metrics.timer("pipeline_stage", stage="analysis"):
            ae.analyze_project(
                project_id=project_id,
                fast_mode=fast_mode,
                on_progress=emit,
                cancellation_token=cancellation_token
            )
            
        emit("analysis.complete", {}) # Analysis engine handles granular logs

    # Legacy wrapper for backward compatibility
    def run(self, *args, **kwargs):
        """Deprecated: Use specific run_ingestion or run_analysis methods."""
        raise NotImplementedError("Use run_ingestion() or run_analysis() directly.")
