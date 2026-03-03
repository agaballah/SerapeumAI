# -*- coding: utf-8 -*-
"""
Model Router - Automatic per-task model selection (LM Studio) with lightweight benchmarking.

Priority order (highest -> lowest):
1) Explicit per-task config: models.<task>.model (if not "auto")
2) Cached recent selection (in-memory TTL)
3) User preference in DB (model_preferences)   <-- always honored
4) BenchmarkService.get_or_benchmark_winner()  (reuses DB preference if fresh; otherwise benchmarks and persists)
5) Historical benchmark winner in DB (model_benchmarks) if quality is acceptable
6) Fallback: currently loaded model or first available model from LM Studio
7) Config keys used:
    models.auto_select.enabled
    models.auto_select.max_age_seconds
    models.auto_select.force
    models.auto_select.max_models_per_task
    models.auto_select.candidates
    models.auto_select.cache_ttl_s
    models.auto_select.min_quality
"""

from __future__ import annotations

import logging
import time
import threading
from typing import Optional, Dict, Any, List, Tuple

logger = logging.getLogger(__name__)


class ModelRouter:
    """
    Automatic model selection for LM Studio multi-model mode.
    """

    def __init__(self, db, lm_studio_service, config=None):
        """
        Args:
            db: DatabaseManager-like object with execute()/commit()
            lm_studio_service: LM Studio adapter with list_models/load_model/chat/get_status
            config: optional ConfigurationManager; if None we lazy-load get_config()
        """
        self.db = db
        self.lms = lm_studio_service
        self._cfg = config  # lazy if None

        # In-memory cache: task -> (model_id, timestamp)
        self.cache: Dict[str, Tuple[str, float]] = {}

        # Prevent concurrent benchmark storms per-task
        self._bench_locks: Dict[str, threading.Lock] = {}
        self._bench_locks_guard = threading.Lock()

    # Task → hardware resource tier map
    _TASK_RESOURCE_TIER: Dict[str, str] = {
        # Heavy vision tasks
        "vision": "vision",
        "vlm": "vision",
        "vision_drawing": "vision",
        "vision_classification": "vision",
        "ocr": "vision",
        # Medium analysis tasks
        "analysis": "analysis",
        "reasoning": "analysis",
        "entity_extraction": "analysis",
        "summarization": "analysis",
        "summary": "analysis",
        # Light chat tasks
        "qa": "chat",
        "chat": "chat",
        "creative_writing": "chat",
        "universal": "chat",
    }

    # --------------------------- public API ---------------------------

    def get_best_model(self, task_type: str) -> str:
        """
        Resource-aware model selection. Checks available VRAM before
        selecting model tier, gracefully degrading heavy tasks if needed.

        Returns:
            LM Studio model id (string). Always tries to return a real id if possible.
        """
        task = self._norm_task(task_type)

        # Resource-aware degradation: downgrade task tier if not enough VRAM
        effective_task = self._degrade_task_if_needed(task)
        if effective_task != task:
            logger.warning(f"[ModelRouter] VRAM limited: downgrading '{task}' -> '{effective_task}'")
            task = effective_task

        # 1) cache
        cached = self._cache_get(task)
        if cached:
            return cached

        # 2) explicit config (if not "auto")
        configured = self._get_configured_model(task)
        if configured and configured.lower() != "auto":
            resolved = self._resolve_to_installed_id(configured)
            self._cache_set(task, resolved)
            logger.info(f"[ModelRouter] Using explicit config for {task}: {resolved} (from {configured})")
            return resolved

        # 3) user preference in DB (always honored)
        preferred = self._get_preference(task)
        if preferred:
            resolved = self._resolve_to_installed_id(preferred)
            self._cache_set(task, resolved)
            logger.info(f"[ModelRouter] Using DB preference for {task}: {resolved}")
            return resolved

        # 4) auto-selection via BenchmarkService (may benchmark + persist)
        if self._auto_select_enabled():
            chosen = self._auto_select(task)
            if chosen:
                self._cache_set(task, chosen)
                return chosen

        # 5) historical benchmark winner (DB) (best-effort)
        winner = self._get_benchmark_winner(task)
        if winner:
            resolved = self._resolve_to_installed_id(winner)
            self._cache_set(task, resolved)
            logger.info(f"[ModelRouter] Using benchmark history for {task}: {resolved}")
            return resolved

        # 6) fallback
        fallback = self._fallback_model()
        self._cache_set(task, fallback)
        logger.warning(f"[ModelRouter] Falling back for {task} -> {fallback}")
        return fallback

    def get_resource_tier(self, task_type: str) -> str:
        """Return the hardware resource tier for a task type."""
        task = self._norm_task(task_type)
        return self._TASK_RESOURCE_TIER.get(task, "chat")

    def _degrade_task_if_needed(self, task: str) -> str:
        """
        If resources are insufficient for the ideal tier, gracefully degrade:
          vision -> analysis -> chat
        """
        try:
            from src.utils.hardware_utils import check_resource_availability
            tier = self._TASK_RESOURCE_TIER.get(task, "chat")

            if tier == "vision" and not check_resource_availability("vision"):
                # Check if analysis tier works
                if check_resource_availability("analysis"):
                    return "analysis"   # downgrade to text-only analysis
                return "chat"           # absolute fallback

            if tier == "analysis" and not check_resource_availability("analysis"):
                return "chat"

        except Exception as e:
            logger.debug(f"[ModelRouter] Resource check failed (safe pass): {e}")

        return task

    def set_preference(self, task_type: str, model: str) -> None:
        """
        Persist a user preference (overrides auto).
        """
        task = self._norm_task(task_type)
        model_id = self._resolve_to_installed_id(model)

        try:
            cols = self._table_columns("model_preferences")
            now = int(time.time())

            if "task" in cols and "preferred_model" in cols:
                self.db.execute(
                    """
                    INSERT OR REPLACE INTO model_preferences (task, preferred_model, last_updated)
                    VALUES (?, ?, ?)
                    """,
                    (task, model_id, now),
                )
            elif "task" in cols and "model" in cols:
                if "last_updated" in cols:
                    self.db.execute(
                        """
                        INSERT OR REPLACE INTO model_preferences (task, model, last_updated)
                        VALUES (?, ?, ?)
                        """,
                        (task, model_id, now),
                    )
                elif "updated_at" in cols:
                    self.db.execute(
                        """
                        INSERT OR REPLACE INTO model_preferences (task, model, updated_at)
                        VALUES (?, ?, ?)
                        """,
                        (task, model_id, now),
                    )
                else:
                    self.db.execute(
                        """
                        INSERT OR REPLACE INTO model_preferences (task, model)
                        VALUES (?, ?)
                        """,
                        (task, model_id),
                    )
            else:
                logger.warning("[ModelRouter] model_preferences schema not recognized; preference not saved.")
                return

            self.db.commit()
            self.cache[task] = (model_id, time.time())
            logger.info(f"[ModelRouter] Set preference: {task} -> {model_id}")

        except Exception as e:
            logger.error(f"[ModelRouter] Failed to set preference: {e}")

    def record_usage(self, model: str, task_type: str, tokens_in: int, tokens_out: int, duration_ms: int) -> None:
        """
        Log model usage for analytics (best-effort).
        """
        try:
            task = self._norm_task(task_type)
            model_id = self._resolve_to_installed_id(model)
            tokens_per_sec = tokens_out / (duration_ms / 1000) if duration_ms > 0 else 0.0
            usage_id = f"{model_id}_{task}_{int(time.time())}"

            cols = self._table_columns("model_usage")
            if not cols:
                return

            wanted = {
                "usage_id", "model_name", "task_type", "tokens_in", "tokens_out",
                "duration_ms", "tokens_per_sec", "created_at"
            }
            if wanted.issubset(cols):
                self.db.execute(
                    """
                    INSERT INTO model_usage
                    (usage_id, model_name, task_type, tokens_in, tokens_out, duration_ms, tokens_per_sec, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (usage_id, model_id, task, tokens_in, tokens_out, duration_ms, tokens_per_sec, int(time.time())),
                )
                if hasattr(self.db, "commit"):
                    self.db.commit()
        except Exception as e:
            logger.debug(f"[ModelRouter] record_usage failed (ignored): {e}")

    def clear_cache(self) -> None:
        self.cache.clear()
        logger.info("[ModelRouter] Cache cleared")

    # --------------------------- auto-selection ---------------------------

    def _auto_select_enabled(self) -> bool:
        v = self._cfg_get("models.auto_select.enabled", None)
        if isinstance(v, bool):
            return v
        v2 = self._cfg_get("benchmark.enabled", None)
        if isinstance(v2, bool):
            return v2
        return True

    def _auto_select(self, task: str) -> Optional[str]:
        """
        Use BenchmarkService.get_or_benchmark_winner() with a bounded candidate set.
        """
        lock = self._get_task_lock(task)
        if not lock.acquire(blocking=False):
            logger.info(f"[ModelRouter] Auto-select already running for {task}; waiting briefly.")
            time.sleep(1.0)
            pref = self._get_preference(task)
            if pref:
                return self._resolve_to_installed_id(pref)
            hist = self._get_benchmark_winner(task)
            return self._resolve_to_installed_id(hist) if hist else self._fallback_model()

        try:
            candidates = self._select_candidate_models(task)

            max_age = int(self._cfg_get("models.auto_select.max_age_seconds", 7 * 24 * 3600) or (7 * 24 * 3600))
            force = bool(self._cfg_get("models.auto_select.force", False))

            from src.infra.services.benchmark_service import BenchmarkService

            bench = BenchmarkService(self.lms, self.db)
            winner = bench.get_or_benchmark_winner(
                task=task,
                models=candidates if candidates else None,
                force=force,
                max_age_seconds=max_age,
            )

            if winner:
                winner_id = self._resolve_to_installed_id(winner)
                logger.info(f"[ModelRouter] AUTO selected for {task}: {winner_id}")
                return winner_id

            return self._fallback_model()

        except Exception as e:
            logger.error(f"[ModelRouter] Auto-select failed for {task}: {e}")
            return self._fallback_model()
        finally:
            try:
                lock.release()
            except Exception:
                pass

    def _select_candidate_models(self, task: str) -> List[str]:
        installed = self._installed_model_ids()
        if not installed:
            return []

        max_n = int(self._cfg_get("models.auto_select.max_models_per_task", 8) or 8)

        explicit = self._cfg_get("models.auto_select.candidates", None)
        if isinstance(explicit, list) and explicit:
            chosen = [self._resolve_to_installed_id(x) for x in explicit if x]
            chosen = [c for c in chosen if c in installed]
            return chosen[:max_n] if chosen else installed[:max_n]

        # Filter by task relevance
        # e.g. vision tasks need vision models

        t = task.lower()

        def score(mid: str) -> int:
            s = mid.lower()
            sc = 0
            if "instruct" in s or "chat" in s:
                sc += 5
            if t.startswith("vision") or t in ("vision", "vlm"):
                if "vl" in s or "vision" in s:
                    sc += 9
            if t in ("summarization", "summary"):
                if "instruct" in s:
                    sc += 3
            if t in ("analysis", "reasoning"):
                if "instruct" in s:
                    sc += 2
            if "q4" in s or "q5" in s or "q6" in s:
                sc += 1
            return sc

        ranked = sorted(installed, key=score, reverse=True)
        return ranked[:max_n]

    # --------------------------- config helpers ---------------------------

    def _cfg_get(self, key_path: str, default: Any = None) -> Any:
        if self._cfg is None:
            try:
                from src.infra.config.configuration_manager import get_config
                self._cfg = get_config()
            except Exception:
                self._cfg = None

        if self._cfg is None:
            return default

        try:
            return self._cfg.get(key_path, default)
        except Exception:
            return default

    def _get_configured_model(self, task: str) -> Optional[str]:
        v = self._cfg_get(f"models.{task}.model", None)
        if isinstance(v, str) and v.strip():
            return v.strip()

        v = self._cfg_get("models.universal.model", None)
        if isinstance(v, str) and v.strip():
            return v.strip()

        return None

    # --------------------------- LM Studio helpers ---------------------------

    def _installed_model_ids(self) -> List[str]:
        try:
            if not self.lms:
                return []
            models = self.lms.list_models()
            ids: List[str] = []
            for m in models or []:
                if isinstance(m, dict) and "id" in m:
                    ids.append(str(m["id"]))
                elif isinstance(m, str):
                    ids.append(m)

            out: List[str] = []
            seen = set()
            for mid in ids:
                if mid and mid not in seen:
                    out.append(mid)
                    seen.add(mid)
            return out
        except Exception as e:
            logger.debug(f"[ModelRouter] list_models failed: {e}")
            return []

    def _fallback_model(self) -> str:
        try:
            if self.lms:
                try:
                    status = self.lms.get_status()
                    loaded = status.get("model") or status.get("loaded_model") or ""
                    if isinstance(loaded, str) and loaded.strip():
                        return loaded.strip()
                except Exception:
                    pass

                installed = self._installed_model_ids()
                if installed:
                    return installed[0]
        except Exception:
            pass

        return "auto"

    def _resolve_to_installed_id(self, name_or_id: str) -> str:
        s = str(name_or_id or "").strip()
        if not s:
            return self._fallback_model()

        installed = self._installed_model_ids()
        if not installed:
            return s

        if s in installed:
            return s

        sl = s.lower()

        subs = [mid for mid in installed if sl in mid.lower()]
        if subs:
            instruct = [x for x in subs if ("instruct" in x.lower() or "chat" in x.lower())]
            return instruct[0] if instruct else subs[0]

        parts = [p for p in sl.replace("-", " ").replace("_", " ").split() if p]
        if parts:
            cand = [mid for mid in installed if all(p in mid.lower() for p in parts)]
            if cand:
                instruct = [x for x in cand if ("instruct" in x.lower() or "chat" in x.lower())]
                return instruct[0] if instruct else cand[0]

        return s

    # --------------------------- DB helpers ---------------------------

    def _table_columns(self, table: str) -> set:
        try:
            rows = self.db.execute(f"PRAGMA table_info({table})").fetchall()
            return {r[1] for r in rows} if rows else set()
        except Exception:
            return set()

    def _get_preference(self, task: str) -> Optional[str]:
        try:
            cols = self._table_columns("model_preferences")
            if not cols:
                return None

            if "task" in cols and "preferred_model" in cols:
                row = self.db.execute(
                    "SELECT preferred_model FROM model_preferences WHERE task = ?",
                    (task,),
                ).fetchone()
                return row[0] if row and row[0] else None

            if "task" in cols and "model" in cols:
                row = self.db.execute(
                    "SELECT model FROM model_preferences WHERE task = ?",
                    (task,),
                ).fetchone()
                return row[0] if row and row[0] else None

        except Exception as e:
            logger.debug(f"[ModelRouter] preference lookup failed: {e}")

        return None

    def _get_benchmark_winner(self, task: str) -> Optional[str]:
        try:
            cols = self._table_columns("model_benchmarks")
            if not cols or "task" not in cols:
                return None

            if {"model", "quality_score", "tokens_per_sec"}.issubset(cols):
                row = self.db.execute(
                    """
                    SELECT model, AVG(quality_score) as q, AVG(tokens_per_sec) as s
                    FROM model_benchmarks
                    WHERE task = ?
                    GROUP BY model
                    ORDER BY q DESC, s DESC
                    LIMIT 1
                    """,
                    (task,),
                ).fetchone()

                if row and row[0]:
                    q = float(row[1] or 0.0)
                    min_q = float(self._cfg_get("models.auto_select.min_quality", 0.55) or 0.55)
                    if q >= min_q:
                        return str(row[0])

        except Exception as e:
            logger.debug(f"[ModelRouter] benchmark lookup failed: {e}")

        return None

    # --------------------------- misc helpers ---------------------------

    def _norm_task(self, task_type: str) -> str:
        t = str(task_type or "").strip().lower()
        return t or "universal"

    def _cache_get(self, task: str) -> Optional[str]:
        ttl_s = float(self._cfg_get("models.auto_select.cache_ttl_s", 3600) or 3600)
        v = self.cache.get(task)
        if not v:
            return None
        model_id, ts = v
        if (time.time() - ts) <= ttl_s:
            return model_id
        try:
            del self.cache[task]
        except Exception:
            pass
        return None

    def _cache_set(self, task: str, model_id: str) -> None:
        self.cache[task] = (model_id, time.time())

    def _get_task_lock(self, task: str) -> threading.Lock:
        with self._bench_locks_guard:
            if task not in self._bench_locks:
                self._bench_locks[task] = threading.Lock()
            return self._bench_locks[task]
