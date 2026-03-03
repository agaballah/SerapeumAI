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
#
"""
document_service.py — Project-Scoped Normalized Ingestion (DB-A)
----------------------------------------------------------------

Aligned with:
    • project-scoped DatabaseManager (one DB per project folder)
    • GenericProcessor (no DB argument)
    • PDFProcessor / ImageProcessor / CAD & Office processors
    • correct per-project export directories
    • Pipeline v3 (ingest → analysis → compliance)
    • main_window.py expectations

Exports go to:
    <project_root>/.serapeum/exports/pages/<doc_id>/page-#.png

Block-level RAG support:
    - Reads doc_title + blocks from payload meta (when available).
    - Persists doc_title into documents table.
    - Persists blocks into doc_blocks + doc_blocks_fts via
      DatabaseManager.insert_doc_blocks().
"""

from __future__ import annotations

import os
import time
import json
import re
from typing import Dict, Any, List, Optional, Callable

from src.infra.persistence.database_manager import DatabaseManager
from src.domain.models.page_record import PageRecord
from src.document_processing.generic_processor import GenericProcessor

import logging
logger = logging.getLogger(__name__)


# Files we are willing to ingest for a project.
# (Per-project scanning still respects ignore folders below.)
SUPPORTED_EXT = {
    # Text & documents
    ".pdf",
    ".txt",
    ".md",
    ".json",
    ".xml",
    ".yaml",
    ".yml",
    ".log",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".xlsm",
    ".ppt",
    ".pptx",
    ".csv",
    ".tsv",

    # Images
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
    ".tif",
    ".tiff",
    ".webp",

    # CAD / BIM
    ".dgn",
    ".dwg",
    ".dxf",
    ".rvt",
    ".ifc",

    # Schedules / planning
    ".xer",
    ".mpp",
}


class DocumentService:
    def __init__(self, *, db: DatabaseManager, project_root: str, job_manager: Optional[Any] = None, global_ks: Optional[Any] = None):
        self.db = db
        self.global_ks = global_ks
        self.job_manager = job_manager
        self.project_root = os.path.abspath(project_root)
        self.generic = GenericProcessor()  # no DB argument

        # per-project export dir
        self.export_root = os.path.join(
            self.project_root,
            ".serapeum",
            "exports",
            "pages",
        )
        os.makedirs(self.export_root, exist_ok=True)

    # =====================================================================
    # UTILITIES
    # =====================================================================
    def _calculate_file_hash(self, filepath: str) -> str:
        import hashlib

        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            # Read and update hash string value in blocks of 4K
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    # =====================================================================
    # INGEST PROJECT
    # =====================================================================
    # =====================================================================
    # INGEST PROJECT
    # =====================================================================
    def ingest_project(
        self,
        *,
        project_id: str,
        root: str,
        recursive: bool = True,
        on_progress: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        cancellation_token=None,
        force: bool = False,
    ) -> Dict[str, Any]:
        """
        Ingest all documents in a project with optional cancellation and force re-scan.
        """
        from src.infra.adapters.cancellation import CancellationError

        logger.info(f"Ingestion project started: {project_id} (force={force})")
        root = os.path.abspath(root)
        ingested_docs: List[str] = []

        try:
            for abs_path in self._scan_files(root, recursive):
                # Check for cancellation
                if cancellation_token:
                    cancellation_token.check()

                rel_path = os.path.relpath(abs_path, root)
                
                try:
                    result = self.ingest_document(
                        abs_path=abs_path,
                        project_id=project_id,
                        rel_path=rel_path,
                        on_progress=on_progress,
                        force=force
                    )
                    if result:
                        ingested_docs.append(result)
                except Exception as e:
                    logger.error(f"Failed to ingest {rel_path}: {e}")
                    if on_progress:
                        on_progress("ingest.error", {"file": rel_path, "error": str(e)})

        except CancellationError:
            logger.info("[DocumentService] Ingestion cancelled by user")
            if on_progress:
                on_progress("ingest.cancelled", {"ingested": len(ingested_docs)})
            raise

        # Auto-queue pages for Vision
        q_count = self.requeue_vision(project_id=project_id, page_selector={"mode": "auto"}, force=force)
        if on_progress:
            on_progress("vision.queued", {"count": q_count})

        return {"count": len(ingested_docs), "docs": ingested_docs, "vision_queued": q_count}

    def ingest_document(
        self,
        *,
        abs_path: str,
        project_id: str,
        rel_path: Optional[str] = None,
        on_progress: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        force: bool = False,
        visited_xrefs: Optional[Set[str]] = None,
    ) -> Optional[str]:
        """
        Ingest a single document into the system. Returns doc_id if successful.
        """
        if visited_xrefs is None:
            visited_xrefs = set()
            
        abs_path = os.path.abspath(abs_path)
        if abs_path in visited_xrefs:
            return None
        visited_xrefs.add(abs_path)

        try:
            if not rel_path:
                rel_path = os.path.relpath(abs_path, self.project_root) if abs_path.startswith(self.project_root) else os.path.basename(abs_path)

            # 1) Calculate hash and stat metadata
            file_hash = self._calculate_file_hash(abs_path)
            file_stats = os.stat(abs_path)
            file_size = file_stats.st_size
            file_mtime = file_stats.st_mtime

            # 2) Check for existing document (idempotency)
            doc_id_override = None
            if not force:
                existing_doc = self.db.get_document_by_hash(project_id, rel_path, file_hash)
                if existing_doc:
                    # If ingestion logic/processor changed, do NOT skip: re-ingest to regenerate
                    # pages/exports and fix older stub payloads.
                    try:
                        from src.document_processing.processor_utils import get_processor_version

                        expected_ver = get_processor_version()
                    except Exception:
                        expected_ver = None

                    should_reingest = False
                    if expected_ver:
                        try:
                            meta_json = existing_doc.get("meta_json") or "{}"
                            meta = json.loads(meta_json) if isinstance(meta_json, str) else {}
                            prev_ver = (meta or {}).get("processor_version")
                            if prev_ver != expected_ver:
                                should_reingest = True
                        except Exception:
                            # If meta is unreadable, prefer re-ingest (safe default)
                            should_reingest = True

                    if not should_reingest:
                        logger.info(f"Skipping unchanged document: {rel_path} (Hash Match)")
                        if on_progress:
                            on_progress("scan.skip", {"file": rel_path, "reason": "unchanged"})
                        
                        # Even if skipping, we should check for XREFs in meta to continue recursion?
                        # For now, if skipped, we assume XREFs are also recorded.
                        return existing_doc["doc_id"]
                    else:
                        logger.info(f"Re-ingesting unchanged document due to processor upgrade: {rel_path}")
                        # IMPORTANT: reuse the existing doc_id to avoid duplicate documents
                        # when only the processor version changes.
                        doc_id_override = existing_doc.get("doc_id")
                        if on_progress:
                            on_progress("scan.file", {"file": rel_path, "reason": "processor_upgrade"})
            else:
                logger.info(f"Force re-scan requested for: {rel_path}")

            if on_progress:
                on_progress("scan.file", {"file": rel_path})

            # 2.5) V02 Registry Ingestion (Async/Job based)
            # We trigger the job but proceed with synchronous V01 legacy processing for now 
            # to maintain dual-compatibility until V02 UI is ready.
            if self.job_manager:
                from src.application.jobs.ingest_file_job import IngestFileJob
                # Use a stable ID for the job based on file path to dedupe if queue depth is managed
                # For now just unique ID
                import uuid
                job = IngestFileJob(
                    job_id=f"ingest_{uuid.uuid4().hex[:8]}", 
                    project_id=project_id, 
                    file_path=abs_path,
                    force=force
                )
                self.job_manager.submit(job)
                logger.info(f"[DocumentService] Submitted V02 Ingest Job for {rel_path}")

            # 3) Process file (V01 Legacy Path - Keep active for UI feedback)
            payload = self.generic.process(
                abs_path=abs_path,
                rel_path=rel_path,
                export_root=self.export_root,
                doc_id_override=doc_id_override,
                project_root=self.project_root,
            )

            # Validate payload structure
            if not payload or "doc_id" not in payload:
                raise ValueError(f"Processor returned invalid payload (missing doc_id): {rel_path}")
            
            doc_id = payload["doc_id"]
            now = int(time.time())
            ext = os.path.splitext(abs_path)[1].lower()
            meta = payload.get("meta") or {}
            # Stamp processor version so future runs can detect upgrades.
            try:
                from src.document_processing.processor_utils import get_processor_version

                meta["processor_version"] = get_processor_version()
            except Exception:
                pass
            doc_title = meta.get("doc_title") or meta.get("document_title")

            # --- SMART ROUTING (Standards vs. Project) ---
            content = payload.get("text", "")
            keywords = ["NFPA", "ASHRAE", "ISO", "ASME", "ANSI", "SBC", "ASTM", "IBC", "IEC", "NEC", "SAUDI BUILDING CODE"]
            filename_upper = os.path.basename(abs_path).upper()
            content_sample = content[:2000].upper()
            
            # Use word boundaries to avoid false positives (e.g. NEC in CONNECTION)
            pattern = r"\b(" + "|".join(re.escape(k) for k in keywords) + r")\b"
            is_standard = bool(re.search(pattern, filename_upper)) or bool(re.search(pattern, content_sample))
            
            if is_standard and self.global_ks:
                logger.info(f"Routing standard to Global DB: {rel_path}")
                self.global_ks.ingest_standard_document(
                    standard_id=doc_id, # Or extract a cleaner ID
                    title=doc_title or os.path.basename(abs_path),
                    content=content
                )
                if on_progress:
                    on_progress("ingest.global", {"file": rel_path, "doc_id": doc_id})
                # We still record it in project DB for reference, or should we skip?
                # User said: "Project Database ... scoped strictly to one project's documents"
                # "Codes & Standards Database ... shared across all projects"
                # If it's a standard, it belongs in the Global DB. 
                # Let's still keep a 'reference' in the Project DB so it appears in the UI.

            # 4) Document Classification (P2.2)
            from src.document_processing.classifier import DocumentClassifier
            classifier = DocumentClassifier()
            doc_type = classifier.classify(os.path.basename(abs_path))

            if not is_standard:
                logger.info(f"Ingesting document: {rel_path} [{doc_type}]")
            
            # 4b) Document Record
            self.db.upsert_document(
                doc_id=doc_id,
                project_id=project_id,
                file_name=os.path.basename(abs_path),
                rel_path=rel_path,
                abs_path=abs_path,
                file_ext=ext,
                created=now,
                updated=now,
                meta_json=json.dumps(meta, ensure_ascii=False),
                content_text=content,
                file_hash=file_hash,
                file_size=file_size,
                file_mtime=file_mtime,
                doc_title=doc_title,
                doc_type=doc_type,
            )

            # 5) Pages
            for p in payload.get("pages", []):
                try:
                    u_text = p.get("unified_text") or p.get("py_text") or ""
                    page_rec = PageRecord(
                        doc_id=doc_id,
                        page_index=p["page_index"],
                        width=p.get("width"),
                        height=p.get("height"),
                        ocr_text=p.get("ocr_text"),
                        text_hint=p.get("text_hint"),
                        image_path=p.get("image_path"),
                        quality=p.get("quality", "queued"),
                        has_raster=bool(p.get("has_raster", 0)),
                        has_vector=bool(p.get("has_vector", 0)),
                        py_text=u_text,
                        py_text_len=len(u_text),
                        py_text_extracted=bool(u_text),
                        layout_json=json.dumps(p.get("layout")) if p.get("layout") else None,
                    )
                    self.db.upsert_page(page_rec)
                except Exception as e:
                    logger.error(f"[ingest.page] Error for page {p.get('page_index')}: {e}", exc_info=True)

            # 6) Blocks
            blocks = payload.get("blocks") or []
            if blocks:
                try: self.db.insert_doc_blocks(doc_id, blocks, source_type=ext.lstrip("."))
                except Exception as e: logger.error(f"[ingest.blocks] Error: {e}", exc_info=True)

            # 7) Structured Data
            structured_data = payload.get("structured_data") or []
            if structured_data:
                try:
                    source_type = meta.get("source", "")
                    if ext in [".ifc"] or source_type == "ifc-processor":
                        self.db.insert_bim_elements(doc_id, structured_data)
                    elif ext in [".xer", ".xml", ".mpp"] or source_type == "schedule-processor":
                        self.db.insert_schedule_activities(doc_id, structured_data)
                except Exception as e: logger.error(f"[ingest.structured] Error: {e}", exc_info=True)

            # 8) XREFs (Recursive)
            xrefs = payload.get("xrefs") or []
            for xref in xrefs:
                x_abs = xref.get("abs_path")
                x_rel = xref.get("rel_path")
                if x_abs and os.path.exists(x_abs):
                    child_id = self.ingest_document(
                        abs_path=x_abs,
                        project_id=project_id,
                        on_progress=on_progress,
                        force=force,
                        visited_xrefs=visited_xrefs
                    )
                    if child_id:
                        # Link parent to child in the links table
                        self.db.insert_link(
                            project_id=project_id,
                            from_kind="document",
                            from_id=doc_id,
                            to_kind="document",
                            to_id=child_id,
                            link_type="CAD_XREF"
                        )

            # [User Request] Verbose logging of what happened
            n_pages = len(payload.get("pages", []))
            n_blocks = len(blocks)
            n_data = len(structured_data)
            n_xrefs = len(xrefs)
            
            total_py_text = sum(len(p.get("py_text") or "") for p in payload.get("pages", []))
            total_ocr_text = sum(len(p.get("ocr_text") or "") for p in payload.get("pages", []))
            
            logger.info(f"   -> Extracted {n_pages} pages | {n_blocks} blocks | {n_data} structured items | {n_xrefs} XREFs")
            logger.info(f"   -> Stats: {total_py_text} chars (Native), {total_ocr_text} chars (OCR)")

            if on_progress:
                on_progress("ingest.doc", {"file": rel_path, "doc_id": doc_id})
            
            return doc_id
        
        except Exception as e:
            logger.error(f"[ingest.fatal] Critical error ingesting {rel_path}: {e}", exc_info=True)
            if on_progress:
                on_progress("ingest.error", {"file": rel_path or abs_path, "error": str(e)})
            raise



    # =====================================================================
    # SCAN FILES  (SKIP INTERNAL FOLDERS)
    # =====================================================================
    def _scan_files(self, root: str, recursive: bool):
        """
        Walk the project tree but ignore internal / generated folders like:

            .serapeum, .git, venv, env, __pycache__, node_modules, logs
        """
        ignore_dirs = {
            ".serapeum",
            ".git",
            "venv",
            "env",
            "__pycache__",
            "node_modules",
            "logs",
        }

        for base, dirs, files in os.walk(root):
            # prune internal dirs in-place so os.walk doesn't descend into them
            # Use case-insensitive check for robustness
            dirs[:] = [
                d
                for d in dirs
                if d.lower() not in ignore_dirs
                and not d.lower().startswith(".serapeum")
            ]

            # Extra safeguard: if we are somehow inside a .serapeum folder, skip
            normalized_base = base.lower().replace("\\", "/")
            if ".serapeum" in normalized_base.split("/"):
                continue

            for fn in files:
                ext = os.path.splitext(fn)[1].lower()
                if ext in SUPPORTED_EXT:
                    yield os.path.join(base, fn)

            if not recursive:
                break


    # =====================================================================
    # REMAINING WORK CHECK
    # =====================================================================
    def check_pending_vision(self, project_id: str) -> int:
        """
        Check if there are pages that require vision processing (VLM)
        but haven't been processed yet.
        """
        # Logic must match requeue_vision's criteria strictly
        sql = """
            SELECT COUNT(*) as cnt
            FROM documents d
            JOIN pages p ON d.doc_id = p.doc_id
            WHERE d.project_id = ?
              AND p.vision_general IS NULL
              AND (
                  p.py_text_len IS NULL
                  OR p.py_text_len <= 2000
                  OR p.has_raster = 1
                  OR p.has_vector = 1
              )
        """
        rows = self.db._query(sql, (project_id,))
        return rows[0]["cnt"] if rows else 0

    # =====================================================================
    # VISION QUEUE
    # =====================================================================
    def requeue_vision(
        self,
        *,
        project_id: str,
        page_selector: Dict[str, Any],
        force: bool = False,
    ) -> int:
        """
        Queue pages that need vision processing using intelligent filtering.

        Only queues pages where:
        - Short text (py_text_len <= 2000 OR NULL), OR
        - Has raster graphics (has_raster = 1), OR
        - Has vector graphics (has_vector = 1)
        AND vision caption not already generated.
        """

        if force:
            # Force mode: queue ALL pages regardless of text length / flags
            sql = """
                SELECT d.doc_id, p.page_index
                FROM documents d
                JOIN pages p ON d.doc_id = p.doc_id
                WHERE d.project_id = ?
                ORDER BY d.doc_id, p.page_index
            """
            rows = self.db._query(sql, (project_id,))
        else:
            # Intelligent mode: only queue pages that actually need vision
            sql = """
                SELECT d.doc_id, p.page_index, p.py_text_len, p.has_raster, p.has_vector
                FROM documents d
                JOIN pages p ON d.doc_id = p.doc_id
                WHERE d.project_id = ?
                  AND p.vision_general IS NULL
                  AND (
                      p.py_text_len IS NULL
                      OR p.py_text_len <= 2000
                      OR p.has_raster = 1
                      OR p.has_vector = 1
                  )
                ORDER BY
                    -- Prioritize: drawings/graphics, then short text, then others
                    CASE
                        WHEN p.has_vector = 1 THEN 1
                        WHEN p.has_raster = 1 THEN 2
                        WHEN p.py_text_len IS NULL OR p.py_text_len < 500 THEN 3
                        ELSE 4
                    END,
                    d.doc_id,
                    p.page_index
            """
            rows = self.db._query(sql, (project_id,))

        # Use SQL-based queue for O(1) pops and better parallelism
        count = 0
        for row in rows:
            # Map priority based on the CASE in SQL
            priority = 0
            if row.get("has_vector") == 1: priority = 10
            elif row.get("has_raster") == 1: priority = 5
            elif (row.get("py_text_len") or 0) < 500: priority = 2
            
            self.db.enqueue_vision_page(row["doc_id"], row["page_index"], priority=priority)
            count += 1
            
        return count
