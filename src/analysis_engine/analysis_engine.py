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
analysis_engine.py — Core document analysis logic
-------------------------------------------------
Orchestrates:
1. Text extraction (via DB)
2. Chunking
3. LLM Analysis
4. Result aggregation
"""

from __future__ import annotations

import json
import logging
import time
from contextlib import contextmanager, nullcontext
from typing import Any, Dict, List, Optional

from src.infra.persistence.database_manager import DatabaseManager
from src.infra.adapters.llm_service import LLMService
from src.infra.config.configuration_manager import get_config

logger = logging.getLogger(__name__)
config = get_config()


class AnalysisOptions:
    def __init__(self, use_llm: bool = True, language_hint: str = "en"):
        self.use_llm = use_llm
        self.language_hint = language_hint


def _cfg_section(name: str) -> Dict[str, Any]:
    """Best-effort config section getter (dict)."""
    try:
        if hasattr(config, "get_section"):
            sec = config.get_section(name)
            return sec if isinstance(sec, dict) else {}
        sec = getattr(config, name, None)
        if isinstance(sec, dict):
            return sec
    except Exception:
        pass
    return {}


def _cfg_int(sec: Dict[str, Any], keys: List[str], default: int) -> int:
    for k in keys:
        v = sec.get(k)
        if v is None:
            continue
        try:
            return int(v)
        except Exception:
            continue
    return default


class AnalysisEngine:
    def __init__(
        self,
        db: DatabaseManager,
        llm: Optional[LLMService],
        options: Optional[AnalysisOptions] = None,
    ) -> None:
        self.db = db
        self.llm = llm
        self.options = options or AnalysisOptions()

        asec = _cfg_section("analysis")
        self.max_docs_limit = _cfg_int(asec, ["MAX_DOCS_LIMIT", "max_docs_limit"], 200)
        self.max_chunk_size = _cfg_int(asec, ["MAX_CHUNK_SIZE", "max_chunk_size"], 12000)
        self.max_snippet_len = _cfg_int(asec, ["MAX_SNIPPET_LEN", "max_snippet_len"], 1500)
        self.max_summary_len = _cfg_int(asec, ["MAX_SUMMARY_LEN", "max_summary_len"], 6000)
        self.max_key_points = _cfg_int(asec, ["MAX_KEY_POINTS", "max_key_points"], 20)
        self.max_risks = _cfg_int(asec, ["MAX_RISKS", "max_risks"], 20)

    # ------------------------------------------------------------------ #
    # Cancellation / model locking helpers
    # ------------------------------------------------------------------ #

    def _raise_cancel(self) -> None:
        """Raise the project-standard CancellationError if available, else RuntimeError."""
        try:
            from src.infra.adapters.cancellation import CancellationError

            raise CancellationError("Cancelled by user")
        except Exception:
            raise RuntimeError("Cancelled by user")

    def _check_cancel(self, cancellation_token) -> None:
        """
        Best-effort cancellation check.
        - If token has .check(), call it (expected to raise on cancel).
        - If token exposes is_cancelled or is_set, raise cancel on True.
        """
        if not cancellation_token:
            return

        if hasattr(cancellation_token, "check"):
            cancellation_token.check()
            return

        if hasattr(cancellation_token, "is_cancelled"):
            try:
                if cancellation_token.is_cancelled:
                    self._raise_cancel()
            except Exception:
                return

        if hasattr(cancellation_token, "is_set"):
            try:
                if cancellation_token.is_set():
                    self._raise_cancel()
            except Exception:
                return

    def _fallback_inference_lock_ctx(self):
        """Fallback: use ModelManager.inference_lock if present, else no-op."""
        try:
            from src.infra.adapters.model_manager import ModelManager

            lock = getattr(ModelManager(), "inference_lock", None) or getattr(ModelManager, "inference_lock", None)
            return lock if lock is not None else nullcontext()
        except Exception:
            return nullcontext()

    def _model_lock_ctx(self, task: str):
        """
        Prefer explicit model lock functions if available; otherwise fall back to
        the global inference lock if present; otherwise no-op.

        IMPORTANT: If lock_model() exists and reports locked, we MUST raise.
        We do NOT swallow that error.
        """
        # First: try to import lock functions. If missing -> fallback.
        try:
            from src.infra.adapters.model_manager import (
                ModelManager,
                lock_model,
                unlock_model,
                get_model_status,
            )
        except Exception:
            return self._fallback_inference_lock_ctx()

        # Ensure model exists/loads before trying to lock
        try:
            if hasattr(ModelManager(), "get_model"):
                ModelManager().get_model(task, auto_load=True)
        except Exception as e:
            logger.warning(f"[AnalysisEngine] Warning: Failed to auto-load '{task}' model: {e}")

        # Enforce lock
        if not lock_model(task):
            status = {}
            try:
                status = get_model_status() or {}
            except Exception:
                pass
            who = status.get("locked_by", "unknown")
            raise RuntimeError(f"Analysis cannot start: Model locked by '{who}'")

        @contextmanager
        def _ctx():
            try:
                yield
            finally:
                try:
                    unlock_model(task)
                except Exception:
                    pass

        return _ctx()

    # ------------------------------------------------------------------ #
    # PROJECT-LEVEL ANALYSIS
    # ------------------------------------------------------------------ #

    def analyze_project(
        self,
        project_id: str,
        force: bool = False,
        fast_mode: bool = False,
        on_progress: Optional[Any] = None,
        cancellation_token=None,
    ) -> Dict[str, Any]:
        """
        Analyze all documents in a project.
        """
        from src.infra.adapters.cancellation import CancellationError

        with self._model_lock_ctx("analysis"):
            try:
                docs = self.db.list_documents(
                    project_id=project_id,
                    limit=self.max_docs_limit,
                    offset=0,
                ) or []

                results: Dict[str, Any] = {"documents": {}, "errors": []}

                logger.info(f"Analyzing project {project_id} ({len(docs)} docs)...")

                for d in docs:
                    self._check_cancel(cancellation_token)

                    did = d.get("doc_id")
                    if not did:
                        continue

                    if on_progress:
                        on_progress("analysis.begin_doc", {"doc_id": did})

                    if not force:
                        try:
                            existing = self.db.get_analysis(did)
                            if existing and existing.get("summary"):
                                results["documents"][did] = {"ok": True, "skipped": True}
                                continue
                        except Exception:
                            pass

                    try:
                        payload = self._analyze_document(did, fast_mode=fast_mode, cancellation_token=cancellation_token)
                        ts = int(time.time())
                        self.db.save_analysis(did, payload, ts)
                        results["documents"][did] = {"ok": True, "ts": ts}

                        if on_progress:
                            on_progress("analysis.done", {"doc_id": did})

                    except Exception as e:
                        err = str(e)
                        results["documents"][did] = {"ok": False, "error": err}
                        results["errors"].append({"doc_id": did, "error": err})

                        if on_progress:
                            on_progress("analysis.warn", {"doc_id": did, "error": err})

                if on_progress:
                    on_progress("analysis.end", {"count": len(docs)})

                return results

            except CancellationError:
                logger.info("[AnalysisEngine] Cancelled by user")
                raise

    # ------------------------------------------------------------------ #

    def _analyze_document(
        self,
        doc_id: str,
        fast_mode: bool = False,
        cancellation_token=None,
    ) -> Dict[str, Any]:
        logger.debug(f"_analyze_document(doc_id={doc_id}, fast_mode={fast_mode})")

        # 1) Page-Level Analysis (Tier 2)
        if not fast_mode and self.options.use_llm and self.llm:
            try:
                from src.analysis_engine.page_analysis import PageAnalyzer

                analyzer = PageAnalyzer(self.db, self.llm)
                logger.info(f"[AnalysisEngine] Starting Page-Based Analysis for {doc_id}...")

                try:
                    analyzer.analyze_document_pages(doc_id, cancellation_token=cancellation_token)
                except TypeError:
                    analyzer.analyze_document_pages(doc_id)

                try:
                    conn = self.db._get_connection()  # type: ignore[attr-defined]
                    conn.commit()
                except Exception:
                    pass

                # Poll briefly for page summaries to be available
                max_wait_seconds = 5.0
                poll_interval = 0.05
                start_poll = time.time()

                pages_after = self.db.list_pages(doc_id) or []
                expected_pages = len(pages_after)

                if expected_pages > 0:
                    ready_count = sum(1 for p in pages_after if p.get("page_summary_short"))
                    while (time.time() - start_poll) < max_wait_seconds and ready_count < expected_pages:
                        self._check_cancel(cancellation_token)
                        time.sleep(poll_interval)
                        pages_after = self.db.list_pages(doc_id) or []
                        ready_count = sum(1 for p in pages_after if p.get("page_summary_short"))

                    if ready_count >= expected_pages:
                        logger.info(
                            f"[AnalysisEngine] All {expected_pages} pages ready for rollup "
                            f"(waited {time.time() - start_poll:.2f}s)"
                        )
                    else:
                        logger.warning(
                            f"[AnalysisEngine] Rollup proceeding with {ready_count}/{expected_pages} pages ready (timeout)"
                        )

            except Exception as e:
                logger.warning(f"[AnalysisEngine] Page analysis failed: {e}")

        # 2) Document-Level Rollup (Tier 1)
        pages = self.db.list_pages(doc_id) or []
        summaries = [p.get("page_summary_short") for p in pages if p.get("page_summary_short")]
        detailed_summaries = [p.get("page_summary_detailed") for p in pages if p.get("page_summary_detailed")]

        logger.info(f"[AnalysisEngine] Document {doc_id}: {len(pages)} pages, {len(summaries)} with summaries")
        if len(pages) > 0 and len(summaries) == 0:
            logger.warning(f"[AnalysisEngine] ROLLUP ISSUE: {len(pages)} pages exist but no summaries available")

        # Collect entities from pages
        all_entities: List[Any] = []
        for p in pages:
            if p.get("page_entities"):
                try:
                    ents = json.loads(p["page_entities"])
                    if isinstance(ents, list):
                        all_entities.extend(ents)
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning(f"[AnalysisEngine] Could not parse page entities: {e}")

        if not summaries:
            logger.warning(f"[AnalysisEngine] No page summaries for {doc_id} - using raw text fallback")

            text_snippets: List[str] = []
            for p in pages[:5]:
                text = p.get("py_text") or p.get("vision_text") or ""
                if text:
                    text_snippets.append(text[: self.max_snippet_len])

            combined = "\n\n".join(text_snippets)

            if not combined:
                return {
                    "summary": "Empty document - no extractable content",
                    "short_summary": "Empty document",
                    "detailed_summary": "",
                    "doc_type": "unknown",
                    "entities": [],
                    "relationships": [],
                    "key_points": [],
                    "risks": [],
                    "fallback_used": True,
                    "rollup_mode": "EMPTY",
                }

            return {
                "summary": combined[: self.max_snippet_len],
                "short_summary": "Page analysis pending - raw text summary",
                "detailed_summary": combined[: self.max_summary_len],
                "doc_type": "unknown",
                "entities": all_entities,
                "relationships": [],
                "key_points": [],
                "risks": [],
                "fallback_used": True,
                "rollup_mode": "FALLBACK",
            }

        combined_short = "\n".join([s for s in summaries if isinstance(s, str)])
        combined_detailed = "\n\n".join([s for s in detailed_summaries if isinstance(s, str)])

        # 3) Generate Document Summary from Page Summaries
        if not fast_mode and self.options.use_llm and self.llm:
            logger.info(f"[AnalysisEngine] Generating document rollup from {len(summaries)} page summaries...")

            system = (
                "You are an AECO document summarizer. Create a document-level summary from the provided page summaries. "
                "Return STRICT JSON only."
            )
            user = (
                f"PAGE_SUMMARIES:\n{combined_short[:10000]}\n\n"
                'Return JSON exactly like: {"short_summary":"...","detailed_summary":"...","doc_type":"..."}'
            )

            try:
                rollup = self.llm.chat_json(system=system, user=user, task_type="analysis")
                if not rollup or not isinstance(rollup, dict):
                    raise RuntimeError("Rollup returned empty/invalid JSON")

                rollup_quality = "COMPLETE" if len(summaries) == len(pages) else "PARTIAL"
                coverage = f"{len(summaries)}/{len(pages)}"

                return {
                    "summary": rollup.get("short_summary", "") or "",
                    "short_summary": rollup.get("short_summary", "") or "",
                    "detailed_summary": rollup.get("detailed_summary", "") or "",
                    "doc_type": rollup.get("doc_type", "unknown") or "unknown",
                    "entities": all_entities,
                    "relationships": [],
                    "key_points": [],
                    "risks": [],
                    "rollup_mode": "STRUCTURED",
                    "rollup_quality": rollup_quality,
                    "summary_coverage": coverage,
                }

            except Exception as e:
                logger.warning(f"[AnalysisEngine] Document rollup failed: {e}")

        # Fallback if rollup fails
        return {
            "summary": (combined_short[:500] + "...") if len(combined_short) > 500 else combined_short,
            "short_summary": (combined_short[:500] + "...") if len(combined_short) > 500 else combined_short,
            "detailed_summary": (combined_detailed[:2000] + "...") if len(combined_detailed) > 2000 else combined_detailed,
            "doc_type": "unknown",
            "entities": all_entities,
            "relationships": [],
            "key_points": [],
            "risks": [],
            "rollup_mode": "DEGRADED",
        }

    # ------------------------------------------------------------------ #

    def _analyze_chunked(self, text: str, cap_str: str, doc_id: str) -> Dict[str, Any]:
        chunks = self._chunk_text(text, max_chars=self.max_chunk_size)
        logger.debug(f"[AnalysisEngine] Split into {len(chunks)} chunks")

        all_entities: List[Dict[str, Any]] = []
        all_relationships: List[Any] = []
        all_key_points: List[Any] = []
        all_risks: List[Any] = []
        summaries: List[str] = []

        if not self.llm:
            return self._fallback(text)

        for i, chunk in enumerate(chunks):
            logger.debug(f"[AnalysisEngine] Processing chunk {i+1}/{len(chunks)}")

            system = (
                "You are an AECO analysis engine. Return ONLY JSON, no markdown.\n"
                "{\n"
                '  "summary": "string",\n'
                '  "doc_type": "drawing|contract|spec|other",\n'
                '  "entities": [{"type": "string", "value": "string"}],\n'
                '  "relationships": [],\n'
                '  "key_points": [],\n'
                '  "risks": []\n'
                "}\n"
                "No code blocks, no explanation. Only JSON."
            )

            user = f"CHUNK {i+1}/{len(chunks)}:\n{chunk}\n\nLANGUAGE_HINT: {self.options.language_hint}"

            try:
                result = self.llm.chat_json(
                    system=system,
                    user=user,
                    task_type="analysis",
                    temperature=0.1,
                )

                if not result:
                    logger.warning(f"[AnalysisEngine] Chunk {i+1} returned empty JSON")
                    continue

                if "error" not in result:
                    summaries.append(result.get("summary", "") or "")
                    all_entities.extend(result.get("entities", []) or [])
                    all_relationships.extend(result.get("relationships", []) or [])
                    all_key_points.extend(result.get("key_points", []) or [])
                    all_risks.extend(result.get("risks", []) or [])

            except Exception as e:
                logger.warning(f"[AnalysisEngine] Chunk {i+1} failed: {e}")
                continue

        seen_entities = set()
        unique_entities: List[Dict[str, Any]] = []
        for ent in all_entities:
            if not isinstance(ent, dict):
                continue
            key = (ent.get("type", ""), ent.get("value", ""))
            if key not in seen_entities:
                seen_entities.add(key)
                unique_entities.append(ent)

        from src.normalizers.vendor_map import normalize_vendor

        for ent in unique_entities:
            ent_type = ent.get("type", "")
            ent_value = ent.get("value", "")

            if ent_type == "vendor" and ent_value:
                normalized = normalize_vendor(ent_value)
                if normalized != ent_value:
                    ent["raw_value"] = ent_value
                    ent["value"] = normalized
                    logger.debug(f"[normalizer] Vendor: '{ent_value}' → '{normalized}'")

            elif ent_type == "standard_reference" and ent_value:
                normalized = ent_value.upper().replace(" ", "-").replace(".", "-")
                import re

                normalized = re.sub(r"-+", "-", normalized)
                if normalized != ent_value:
                    ent["raw_value"] = ent_value
                    ent["value"] = normalized
                    logger.debug(f"[normalizer] Standard: '{ent_value}' → '{normalized}'")

        merged_summary = " ".join([s for s in summaries if s]).strip()
        return {
            "summary": merged_summary[: self.max_summary_len],
            "entities": unique_entities,
            "relationships": all_relationships,
            "key_points": all_key_points[: self.max_key_points],
            "risks": all_risks[: self.max_risks],
        }

    def _chunk_text(self, text: str, max_chars: int = 12000) -> List[str]:
        from src.domain.intelligence.text_chunker import TextChunker

        blocks = TextChunker.chunk_text(text, source_type="analysis", max_chunk_size=max_chars)
        return [block["content"] for block in blocks if isinstance(block, dict) and "content" in block]

    def _parse_llm_response(self, raw: Any, doc_id: str) -> Dict[str, Any]:
        from src.utils.parser_utils import robust_json_parse, extract_openai_content

        try:
            content = extract_openai_content(raw)

            if isinstance(raw, dict) and "error" in raw:
                logger.error(f"[AnalysisEngine] LLM returned error: {raw.get('error')}")
                return {
                    "summary": "",
                    "entities": [],
                    "relationships": [],
                    "key_points": [],
                    "risks": [],
                    "error": "llm_error",
                    "analysis_raw": str(raw),
                }

            obj = robust_json_parse(content)

            if not obj:
                logger.error("[AnalysisEngine] JSON parse failed completely")
                logger.error(f"[AnalysisEngine] Raw output: {str(content)[:500]}")
                return {
                    "summary": "",
                    "entities": [],
                    "relationships": [],
                    "key_points": [],
                    "risks": [],
                    "error": "json_parse_failed",
                    "analysis_raw": str(content)[:2000],
                }

            logger.debug(f"[AnalysisEngine] Parsed JSON successfully, entities={len(obj.get('entities', []))}")

        except Exception as e:
            logger.error(f"[AnalysisEngine] Analysis parsing failed: {e}")
            return {
                "summary": "",
                "entities": [],
                "relationships": [],
                "key_points": [],
                "risks": [],
                "error": "parse_exception",
                "error_detail": str(e),
                "analysis_raw": str(raw)[:2000] if raw else "",
            }

        return {
            "summary": str(obj.get("short_summary") or obj.get("summary") or ""),
            "short_summary": str(obj.get("short_summary") or ""),
            "detailed_summary": str(obj.get("detailed_summary") or obj.get("summary") or ""),
            "entities": obj.get("entities") or [],
            "relationships": obj.get("relationships") or [],
            "key_points": obj.get("key_points") or [],
            "risks": obj.get("risks") or [],
        }

    def _fallback(self, text: str) -> Dict[str, Any]:
        lines = text.split("\n")[:8]
        summ = " ".join(lines).strip()[:500]
        return {
            "summary": summ,
            "entities": [],
            "relationships": [],
            "key_points": [],
            "risks": [],
        }
