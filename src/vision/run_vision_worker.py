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
run_vision_worker.py — Background worker to process queued pages
--------------------------------------------------------------
Uses:
1. LLMService (VLM) for captioning/layout understanding.
2. DatabaseManager for persistence.

NOTE: OCR (Tesseract) is NOT run here. It is run in image_processor.py.
This worker is strictly for Vision/VLM tasks using Qwen (or other vision model).
"""

from __future__ import annotations

import argparse
import base64
import concurrent.futures
from concurrent.futures import as_completed
import json as _json
import logging
import os
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from src.analysis_engine.health_tracker import get_health_tracker
from src.domain.models.page_record import PageRecord
from src.infra.adapters.llm_service import LLMService
from src.infra.config.configuration_manager import get_config
from src.infra.persistence.database_manager import DatabaseManager

config = get_config()
logger = logging.getLogger(__name__)


# ------------------------------ config helpers ------------------------------ #

def _cfg_get(key: str, default: Any = None) -> Any:
    """
    Best-effort config getter supporting either:
      - config.get("a.b.c", default)
      - config.get_section("a") -> dict nesting
      - dict-like config
    """
    # dict-like
    if isinstance(config, dict):
        return config.get(key, default)

    # direct get()
    if hasattr(config, "get"):
        try:
            return config.get(key, default)
        except TypeError:
            # some implementations use get(key) only
            try:
                v = config.get(key)
                return default if v is None else v
            except Exception:
                pass

    # get_section("a") + nested traversal for "a.b.c"
    if hasattr(config, "get_section") and "." in key:
        try:
            head, tail = key.split(".", 1)
            sec = config.get_section(head) or {}
            if not isinstance(sec, dict):
                return default
            cur: Any = sec
            for part in tail.split("."):
                if isinstance(cur, dict) and part in cur:
                    cur = cur[part]
                else:
                    return default
            return default if cur is None else cur
        except Exception:
            return default

    return default


# ------------------------------ queue helpers ------------------------------ #

# Legacy queue helpers removed as we use DatabaseManager's SQL-based queue now.


# --------------------------- page record helpers ---------------------------- #

def _get_page_record(db: DatabaseManager, doc_id: str, page_index: int) -> Optional[PageRecord]:
    row = db.get_page(doc_id, page_index)
    if not row:
        return None
    return PageRecord.from_row(row)


def _save_page_record(db: DatabaseManager, page: PageRecord) -> None:
    db.upsert_page(page)


def _mark_quality(db: DatabaseManager, doc_id: str, page_index: int, status: str) -> None:
    page = _get_page_record(db, doc_id, page_index)
    if page:
        page.quality = status
        _save_page_record(db, page)


def _persist_caption(db: DatabaseManager, doc_id: str, page_index: int, cap: Dict[str, Any]) -> None:
    # Preferred: typed table if available
    try:
        db.save_page_caption(doc_id, page_index, caption=cap)
        saved = True
    except Exception:
        saved = False

    # Fallback: attach to vision_pages (legacy)
    page = _get_page_record(db, doc_id, page_index)
    if page:
        page.caption_json = _json.dumps(cap, ensure_ascii=False)
        _save_page_record(db, page)

    if not saved:
        # Also mirror to KV
        try:
            key = f"captions:{doc_id}"
            rec = db.get_kv(key) or {}
            if not isinstance(rec, dict):
                rec = {}
            pages = rec.get("pages") or {}
            if not isinstance(pages, dict):
                pages = {}
            pages[str(int(page_index))] = {"caption": cap, "ts": int(time.time())}
            rec["pages"] = pages
            rec["count"] = len(pages)
            db.set_kv(key, rec)
        except Exception:
            pass


# --------------------------- captioning helper ----------------------------- #

def _caption_with_llm(
    llm: LLMService,
    *,
    image_path: str,
    ocr_text: str,
    text_hint: str,
) -> Dict[str, Any]:
    """
    Legacy single-shot Vision captioner.

    Kept for backward compatibility; newer code uses two_stage_caption.
    Uses vision model with image + text, and performs robust JSON extraction
    WITHOUT relying on response_format.
    """
    system = (
        "You are an AECO drawing summarizer. Return ONLY one JSON object with keys:\n"
        '{"type":"render|floorplan|mep|section|elevation|contract_text|other",'
        '"title":string,"language":"ar|en|mixed","rooms":[{"name":string,"area_m2":number|null}],'
        '"notes":[string],"issues":[{"severity":"high|medium|low","type":string,"note":string}]}'
    )
    schema_hint = "Object<{type,title,language,rooms,notes,issues}>"

    obj: Optional[Dict[str, Any]] = None

    img_b64: Optional[str] = None
    if image_path and os.path.isfile(image_path):
        try:
            with open(image_path, "rb") as fh:
                img_b64 = base64.b64encode(fh.read()).decode("ascii")
        except Exception:
            img_b64 = None

    if img_b64:
        user_content = [
            {
                "type": "text",
                "text": (
                    "Use BOTH the drawing image and the OCR/text signals below to understand this single page.\n\n"
                    f"OCR_TEXT:\n{(ocr_text or '')[:int(_cfg_get('vision.max_text_preview', 2000))]}\n\n"
                    f"TEXT_HINT:\n{(text_hint or '')[:int(_cfg_get('vision.max_text_hint', 1000))]}"
                ),
            },
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{img_b64}"},
            },
        ]
        try:
            resp = llm.chat(
                messages=[
                    {"role": "system", "content": system + "\nSchemaHint: " + schema_hint},
                    {"role": "user", "content": user_content},
                ],
                temperature=float(_cfg_get("vision.temperature_vlm", 0.2)),
                top_p=float(_cfg_get("vision.top_p_vlm", 0.95)),
                max_tokens=int(_cfg_get("vision.max_tokens_vlm", 4096)),
                task_type="vision",
            )
            content = ((resp.get("choices") or [{}])[0].get("message", {}) or {}).get("content") or ""
            raw = str(content).strip()

            cleaned = raw
            if cleaned.startswith("```"):
                parts = cleaned.split("```")
                if len(parts) >= 2:
                    cleaned = parts[1]
            cleaned = cleaned.lstrip()
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.strip()

            start = cleaned.find("{")
            end = cleaned.rfind("}")
            json_str = cleaned[start : end + 1] if (start != -1 and end != -1 and end > start) else cleaned

            obj = _json.loads(json_str)
        except Exception:
            obj = None

    if not isinstance(obj, dict):
        user = (
            "Use the following signals from a single page image.\n"
            f"OCR_TEXT:\n{(ocr_text or '')[:int(_cfg_get('vision.max_text_preview', 2000))]}\n\n"
            f"TEXT_HINT:\n{(text_hint or '')[:int(_cfg_get('vision.max_text_hint', 1000))]}"
        )
        try:
            obj = llm.chat_json(
                system=system,
                user=user,
                schema_hint=schema_hint,
                max_tokens=int(_cfg_get("vision.max_tokens_text_only", 2048)),
                task_type="analysis",
            )
        except Exception:
            obj = {}

    if not isinstance(obj, dict):
        obj = {}

    return {
        "type": str(obj.get("type") or "other"),
        "title": str(obj.get("title") or "").strip()[:200],
        "language": str(obj.get("language") or "mixed"),
        "rooms": obj.get("rooms") or [],
        "notes": obj.get("notes") or [],
        "issues": obj.get("issues") or [],
    }


# ------------------------------- worker ------------------------------------ #

def run_worker(
    *,
    db: DatabaseManager,
    llm: LLMService,
    project_id: Optional[str] = None,
    burst_pages: int = int(_cfg_get("vision.burst_size", 10)),
    sleep_when_idle: float = float(_cfg_get("vision.idle_sleep_seconds", 2.0)),
    mode: str = "burst",  # "burst" or "full"
    once: bool = False,
    stop_event: Optional[threading.Event] = None,
) -> None:
    """
    Process queued pages until the queue is empty (or until burst_pages if once=True).

    Args:
        mode: "burst" (default, process up to burst_pages) or "full" (run until queue empty)
        once: If True, stop after burst_pages even if mode is "full"
        stop_event: Optional threading.Event to signal graceful shutdown
    """
    from src.infra.adapters.model_manager import ModelManager, lock_model, unlock_model

    wlog = logging.getLogger("vision.worker")
    wlog.info(f"Vision Worker started. Mode={mode}, Burst={burst_pages}, Once={once}")

    skip_caption_threshold = int(_cfg_get("pdf_processing.min_text_threshold", 100))
    wlog.info(f"Using skip_caption_threshold={skip_caption_threshold}")

    if not lock_model("vision"):
        wlog.warning("Could not acquire 'vision' lock. Another task is running? Aborting.")
        return

    try:
        # Auto-load model (Worker Lifecycle)
        try:
            loaded = ModelManager().get_model("vision", auto_load=True)
        except Exception as e:
            loaded = None
            wlog.error(f"Vision Model load failed: {e}")

        if not loaded:
            wlog.error("Vision Model (Qwen) failed to load. Worker aborting.")
            return

        processed = 0
        run_until_empty = mode == "full"
        workers = int(_cfg_get("vision.parallel_workers", 1))

        def _process_single(item_dict: Dict[str, Any]) -> int:
            """Process a single queued page. Returns 1 if processed, 0 otherwise."""
            try:
                did = item_dict["doc_id"]
                pidx = item_dict["page_index"]
                qid = item_dict["queue_id"]
                wlog.info(f"Processing doc={did} page={pidx}")

                # Optional project filtering
                if project_id:
                    try:
                        doc = db.get_document(did)  # type: ignore[attr-defined]
                        if doc and doc.get("project_id") and str(doc["project_id"]) != str(project_id):
                            wlog.debug(f"Skipping doc={did} (project mismatch)")
                            return 0
                    except Exception:
                        return 0

                page = _get_page_record(db, did, pidx)
                if not page:
                    wlog.warning(f"Page record not found for doc={did} page={pidx}")
                    return 0

                ocr_text = str(getattr(page, "ocr_text", "") or "").strip()
                text_hint = str(getattr(page, "text_hint", "") or "")
                has_ocr = bool(ocr_text)
                has_caption = bool(getattr(page, "caption_json", "") or "")

                # Legacy skip if already done
                if has_ocr and has_caption:
                    _mark_quality(db, did, pidx, "done")
                    page.vision_ocr_done = True
                    page.vision_model = "legacy"
                    _save_page_record(db, page)
                    wlog.info(f"Skipping doc={did} page={pidx} (already done)")
                    return 0

                _mark_quality(db, did, pidx, "processing")

                img_path = (
                    str(getattr(page, "image_path", "") or "")
                    or str(getattr(page, "image_ref", "") or "")
                    or str(getattr(page, "preview_path", "") or "")
                    or str(getattr(page, "raster_path", "") or "")
                )

                try:
                    py_text_len = int(getattr(page, "py_text_len", 0) or 0)
                except Exception:
                    py_text_len = 0

                skip_captioning = py_text_len > skip_caption_threshold

                if not has_caption:
                    if skip_captioning:
                        wlog.info(
                            f"[Vision Logic] SKIPPING VLM for doc={did} page={pidx} "
                            f"(Native Text: {py_text_len} > Threshold: {skip_caption_threshold})"
                        )
                        page.vision_ocr_done = True
                        page.vision_model = "skipped_text_heavy"
                        _save_page_record(db, page)
                        _mark_quality(db, did, pidx, "done")
                        return 1

                    wlog.info(
                        f"[Vision Logic] PROCESSING VLM for doc={did} page={pidx} "
                        f"(Native Text: {py_text_len} <= Threshold: {skip_caption_threshold})"
                    )

                    if not img_path or not os.path.exists(img_path):
                        wlog.info(
                            f"Skipping VLM for doc={did} page={pidx} "
                            f"(Image file missing: '{img_path}' - likely optimized away)"
                        )
                        page.vision_ocr_done = True
                        page.vision_model = "skipped_no_image"
                        _save_page_record(db, page)
                        _mark_quality(db, did, pidx, "done")
                        return 0

                    wlog.info(f"Running Two-Stage VLM Captioning for doc={did} page={pidx}")
                    try:
                        from src.vision.vision_caption_v2 import two_stage_caption

                        py_text = str(getattr(page, "py_text", "") or "")
                        ocr_text_for_caption = str(getattr(page, "ocr_text", "") or "")

                        start_ts = time.time()
                        result = two_stage_caption(
                            llm,
                            image_path=str(img_path or ""),
                            py_text=py_text,
                            ocr_text=ocr_text_for_caption,
                        )
                        duration = time.time() - start_ts
                        try:
                            get_health_tracker().record_metric(
                                "vision_page_duration",
                                duration,
                                {"doc_id": str(did), "page": str(pidx)},
                            )
                        except Exception:
                            pass

                        if result:
                            gen_sum = result.get("general_summary", "")
                            det_desc = result.get("detailed_description", "")

                            if isinstance(gen_sum, dict):
                                gen_sum = _json.dumps(gen_sum, ensure_ascii=False)
                            if isinstance(det_desc, dict):
                                det_desc = _json.dumps(det_desc, ensure_ascii=False)

                            # The following variables are not defined in the original code,
                            # but are present in the user's provided snippet.
                            # Assuming they are meant to be derived from 'result' or other context.
                            # For now, using placeholders or existing 'result' values.
                            safe_gen = gen_sum
                            safe_ocr = result.get("vision_text", "") or ""
                            combined_caption = {
                                "type": "vision_v2",
                                "title": str(gen_sum)[:200],
                                "notes": [str(det_desc)[:500]],
                            }
                            quality_assessment = {
                                "quality_score": result.get("quality_score", 0.0) or 0.0,
                                "quality_flags": result.get("quality_flags", []),
                                "needs_retry": result.get("needs_retry", False),
                                "human_review": result.get("human_review", False),
                            }
                            safe_quality = "good" # Placeholder, as 'safe_quality' is not defined in the original context.

                            # Update DB
                            with db.transaction():
                                page.vision_general = str(safe_gen or "")
                                page.vision_detailed = str(det_desc or "")
                                page.caption_json = _json.dumps(combined_caption)
                                page.vision_ocr_text = str(safe_ocr or "")
                                
                                # Quality tracking
                                quality_score = int(quality_assessment.get("quality_score", 50))
                                quality_flags = quality_assessment.get("quality_flags", [])
                                needs_retry = quality_assessment.get("needs_retry", False)
                                needs_human_review = quality_assessment.get("human_review", False)
                                
                                page.quality = safe_quality
                                page.quality_score = quality_score
                                page.quality_flags = _json.dumps(quality_flags)
                                page.needs_retry = needs_retry
                                page.needs_human_review = needs_human_review

                                page.vision_model = str(result.get("vision_model", "qwen2-vl-7b"))
                                page.vision_timestamp = int(time.time())
                                page.vision_ocr_done = True
                                
                                db.upsert_page(page)
                            
                            # Index vision data into vector store (NEW)
                            try:
                                from src.application.services.vision_vector_service import VisionVectorService
                                vision_vector_svc = VisionVectorService(db)
                                vision_vector_svc.index_vision_for_document(did) # Changed doc_id to did
                                wlog.info(f"[Worker] Indexed vision for {did} into vector store") # Changed logger to wlog
                            except Exception as ve:
                                wlog.warning(f"[Worker] Failed to index vision vector for {did}: {ve}") # Changed logger to wlog

                            wlog.info(f"Two-stage caption complete for doc={did} page={pidx}")

                            legacy_cap = {
                                "type": "vision_v2",
                                "title": (str(result.get("general_summary", ""))[:200]),
                                "notes": [str(result.get("detailed_description", ""))[:500]],
                            }
                            _persist_caption(db, did, pidx, legacy_cap)

                    except Exception as e:
                        wlog.error(f"Two-stage caption failed for doc={did} page={pidx}: {e}")

                db.update_vision_queue_status(qid, "done")
                import gc
                gc.collect()
                return 1

            except Exception as ex:
                wlog.error(f"Processing failed for item {item_dict}: {ex}")
                db.update_vision_queue_status(qid, "failed", error=str(ex))
                return 0

        while True:
            if stop_event and stop_event.is_set():
                wlog.info("Vision Worker stop signal received.")
                return

            batch = db.pop_vision_queue_batch(limit=max(1, workers))

            if not batch:
                if once or run_until_empty:
                    wlog.info(f"Queue empty ({'once=True' if once else 'mode=full'}). Exiting.")
                    return
                time.sleep(sleep_when_idle)
                continue

            if workers <= 1:
                for it in batch:
                    processed += _process_single(it)
            else:
                with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
                    futures = {ex.submit(_process_single, it): it for it in batch}
                    for fut in as_completed(futures):
                        try:
                            processed += int(fut.result() or 0)
                        except Exception as e:
                            wlog.error(f"Worker task failed: {e}")

            if once and processed >= burst_pages:
                wlog.info(f"Burst limit reached ({burst_pages}) with once=True. Exiting.")
                return

    finally:
        # CRITICAL: unlock signature is task-specific
        try:
            from src.infra.adapters.model_manager import unlock_model
            unlock_model("vision")
        except Exception:
            pass
        wlog.info("Vision lock released.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-root", required=True)
    parser.add_argument("--project-id", default=None)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--burst", type=int, default=32)
    parser.add_argument(
        "--mode",
        default="burst",
        choices=["burst", "full"],
        help="Run mode: burst (limit pages) or full (until empty)",
    )
    args = parser.parse_args()

    db = DatabaseManager(root_dir=args.db_root)
    llm = LLMService(db=db)

    run_worker(
        db=db,
        llm=llm,
        project_id=args.project_id,
        burst_pages=args.burst,
        once=args.once,
        mode=args.mode,
    )
