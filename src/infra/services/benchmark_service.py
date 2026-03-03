# -*- coding: utf-8 -*-
"""
Benchmark Service - Lightweight on-device benchmarking for automatic model selection.

Goal:
- Run tiny, deterministic benchmarks per task (chat/analysis/vision/summarization/etc.)
- Measure:
    * duration
    * tokens/sec (best-effort)
    * quality score (0..1) using simple validators
- Persist results in:
    * model_benchmarks
    * model_preferences
- Provide a single call used by router/recommender:
    get_or_benchmark_winner(task, models, force=False)

This is intentionally lightweight: it should finish quickly on-device.

IMPORTANT:
- DB schema in your repo (006_lm_studio_support.sql) uses:
    model_preferences(task, preferred_model, last_updated)
- model_benchmarks.benchmark_id is PRIMARY KEY; must be UNIQUE per inserted row.
"""

from __future__ import annotations

import json
import time
import uuid
import logging
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Callable

logger = logging.getLogger(__name__)


# ----------------------------- Embedding model guard ---------------------- #

def _is_embedding_model(model_id: str) -> bool:
    """
    Returns True if this model ID is an embedding model that does NOT support
    /v1/chat/completions. Embedding models must never be sent to the chat endpoint.

    Detection heuristics (model ID substrings):
      - 'embed' / 'embedding'  (e.g. nomic-embed, text-embedding-*)
      - 'e5-'                  (e.g. e5-large, multilingual-e5)
      - 'bge-'                 (e.g. bge-large-zh)
      - 'minilm'               (e.g. all-MiniLM-L6-v2)
      - 'gte-'                 (e.g. gte-large)
    """
    m = (model_id or "").lower()
    return any(marker in m for marker in (
        "embed",
        "e5-",
        "bge-",
        "minilm",
        "gte-",
    ))


def _get_free_vram_mb() -> float:
    """Return free VRAM in MB, or a large number if CUDA unavailable."""
    try:
        import torch
        if torch.cuda.is_available():
            free, total = torch.cuda.mem_get_info(0)
            return free / (1024 * 1024)
    except Exception:
        pass
    return 9999.0  # CPU or unavailable — don't block


def _clear_cuda_cache() -> None:
    """Clear CUDA cache after model unload to prevent VRAM fragmentation."""
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            logger.debug("[Benchmark] CUDA cache cleared.")
    except Exception:
        pass


# ----------------------------- Validators --------------------------------- #

def _norm(s: str) -> str:
    return (s or "").strip()


def _score_exact(output: str, expected: str) -> float:
    return 1.0 if _norm(output) == _norm(expected) else 0.0


def _score_contains(output: str, expected_substring: str) -> float:
    out = (output or "").lower()
    sub = (expected_substring or "").lower()
    return 1.0 if sub and sub in out else 0.0


def _score_json_has_keys(output: str, keys: List[str]) -> float:
    try:
        obj = json.loads(output)
        if not isinstance(obj, dict):
            return 0.0
        for k in keys:
            if k not in obj:
                return 0.0
        return 1.0
    except Exception:
        return 0.0


def _score_bullets(output: str, min_bullets: int = 3) -> float:
    lines = [ln.strip() for ln in (output or "").splitlines() if ln.strip()]
    bullets = [ln for ln in lines if ln.startswith("-") or ln.startswith("•")]
    return 1.0 if len(bullets) >= min_bullets else 0.0


def _score_jaccard(output: str, expected: str) -> float:
    """
    Lightweight fuzzy scoring for legacy test-cases.
    """
    if not expected:
        return 1.0
    set_output = set((output or "").lower().split())
    set_expected = set((expected or "").lower().split())
    inter = set_output & set_expected
    uni = set_output | set_expected
    return (len(inter) / len(uni)) if uni else 0.0


# ----------------------------- Test cases --------------------------------- #

_ONE_BY_ONE_PNG_RED = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR42mP8z8AARwMBy1oXGQAAAABJRU5ErkJggg=="
)


@dataclass(frozen=True)
class TestCase:
    messages: List[Dict[str, Any]]
    expected: str = ""
    validator: Optional[Callable[[str, str], float]] = None
    max_tokens: int = 96
    temperature: float = 0.0


def _default_suite_for_task(task: str) -> List[TestCase]:
    """
    Tiny suites. Deterministic scoring; low token budgets.
    """
    t = (task or "").strip().lower()

    if t in ("chat", "qa", "universal"):
        return [
            TestCase(
                messages=[{"role": "user", "content": "Return ONLY the number: 7*13"}],
                expected="91",
                validator=lambda out, exp: _score_exact(out, exp),
                max_tokens=8,
                temperature=0.0,
            ),
            TestCase(
                messages=[{"role": "user", "content": "Reply with ONLY 'OK' (no punctuation)."}],
                expected="OK",
                validator=lambda out, exp: _score_exact(out, exp),
                max_tokens=6,
                temperature=0.0,
            ),
        ]

    if t in ("analysis", "reasoning"):
        return [
            TestCase(
                messages=[{"role": "user", "content": "Return ONLY the number: (19*3) - (5*7)"}],
                expected=str((19 * 3) - (5 * 7)),
                validator=lambda out, exp: _score_exact(out, exp),
                max_tokens=10,
                temperature=0.0,
            ),
            TestCase(
                messages=[{"role": "user", "content": "Return ONLY the number: 144 / 12"}],
                expected="12",
                validator=lambda out, exp: _score_exact(out, exp),
                max_tokens=10,
                temperature=0.0,
            ),
        ]

    if t in ("entity_extraction", "extraction"):
        prompt = (
            "Extract entities from the sentence and return STRICT JSON ONLY.\n"
            "Schema: {\"people\": [..], \"orgs\": [..]}\n"
            "Sentence: \"Alice joined ACME Corp in 2020.\""
        )
        return [
            TestCase(
                messages=[{"role": "user", "content": prompt}],
                expected='{"people":["Alice"],"orgs":["ACME Corp"]}',
                validator=lambda out, _exp: _score_json_has_keys(out, ["people", "orgs"]),
                max_tokens=96,
                temperature=0.0,
            )
        ]

    if t in ("summarization", "summary"):
        text = (
            "Text:\n"
            "SerapeumAI is a local desktop app for document intelligence. "
            "It supports PDFs, OCR, embeddings, and LLM-assisted extraction. "
            "The goal is to process large project folders reliably.\n\n"
            "Task: Summarize in at least 3 bullet points. Use '-' bullets."
        )
        return [
            TestCase(
                messages=[{"role": "user", "content": text}],
                expected="",
                validator=lambda out, _exp: _score_bullets(out, min_bullets=3),
                max_tokens=128,
                temperature=0.2,
            )
        ]

    if t in ("vision", "vision_classification", "vision_drawing", "vlm"):
        prompt = (
            "You will receive an image. Return STRICT JSON ONLY: {\"ok\": true}.\n"
            "No extra text."
        )
        return [
            TestCase(
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": _ONE_BY_ONE_PNG_RED}},
                    ],
                }],
                expected='{"ok":true}',
                validator=lambda out, _exp: _score_json_has_keys(out, ["ok"]),
                max_tokens=32,
                temperature=0.0,
            )
        ]

    return _default_suite_for_task("qa")


# ----------------------------- Benchmark service ---------------------------- #

class BenchmarkService:
    """
    Run comparative benchmarks across multiple models and persist results.
    """

    def __init__(self, lm_studio_service, db=None, global_db=None):
        self.lms = lm_studio_service
        self.db = db
        self.global_db = global_db or db  # Fallback to project db if global not provided
        self.config = None

    # -------------------------- Public API -------------------------- #

    def get_or_benchmark_winner(
        self,
        task: str,
        models: Optional[List[str]] = None,
        *,
        force: bool = False,
        max_age_seconds: int = 7 * 24 * 3600,
        on_progress: Optional[Callable[[str, int, int], None]] = None,
    ) -> Optional[str]:
        """
        Returns the best model for a task.

        - If a recent preference exists and force=False -> reuse it.
        - Else run a lightweight benchmark suite and persist:
            * model_benchmarks rows
            * model_preferences winner row
        """
        t = (task or "").strip().lower() or "qa"

        if not force:
            cached = self._load_preference(task=t, max_age_seconds=max_age_seconds)
            if cached:
                return cached

        if not models:
            models = self._discover_models()
        models = [m for m in (models or []) if m and str(m).strip()]

        if not models:
            logger.warning("[Benchmark] No models available to benchmark.")
            return None

        result = self.run_benchmark(
            task=t,
            models=models,
            test_cases=None,
            on_progress=on_progress,
            lightweight=True,
        )

        winner = result.get("winner")
        if winner:
            self._save_preference(task=t, model=winner, score=result.get("winner_score", None))
        return winner

    def run_benchmark(
        self,
        task: str,
        models: List[str],
        test_cases: Optional[List[Dict[str, Any]]] = None,
        on_progress: Optional[Callable[[str, int, int], None]] = None,
        *,
        lightweight: bool = False,
    ) -> Dict[str, Any]:
        """
        Backward-compatible benchmark runner.

        If lightweight=True or test_cases is None:
            uses built-in micro-suite for the task.
        """
        t = (task or "").strip().lower() or "qa"

        if lightweight or test_cases is None:
            suite = _default_suite_for_task(t)
        else:
            suite = []
            for c in (test_cases or []):
                suite.append(
                    TestCase(
                        messages=[{"role": "user", "content": c.get("input", "")}],
                        expected=c.get("expected", ""),
                        validator=lambda out, exp: _score_jaccard(out, exp) if exp else 1.0,
                        max_tokens=128,
                        temperature=0.0,
                    )
                )

        logger.info(f"[Benchmark] Starting '{t}' benchmark with {len(models)} models, {len(suite)} cases")

        results: Dict[str, Any] = {}
        speeds_for_norm: List[float] = []

        for model in models:
            # ── Embedding model guard (Issue #2) ─────────────────────────────
            if _is_embedding_model(model):
                logger.warning(
                    f"[Benchmark] Skipping {model!r}: detected as embedding model. "
                    "Embedding models do not support /chat. Use /v1/embeddings instead."
                )
                results[model] = {"error": "embedding_model_skipped"}
                continue

            logger.info(f"[Benchmark] Testing model: {model}")

            # ── VRAM hardware gate (Issue #3) ─────────────────────────────────
            free_vram = _get_free_vram_mb()
            if free_vram < 256:
                logger.warning(
                    f"[Benchmark] Insufficient VRAM ({free_vram:.0f} MB free < 256 MB). "
                    f"Skipping {model!r} to protect system stability."
                )
                results[model] = {"error": f"vram_insufficient_{free_vram:.0f}mb"}
                continue

            try:
                if hasattr(self.lms, "load_model"):
                    self.lms.load_model(model)
            except Exception as e:
                logger.error(f"[Benchmark] Failed to load {model}: {e}")
                results[model] = {"error": str(e)}
                _clear_cuda_cache()  # clear even on load failure
                continue

            outputs: List[str] = []
            speeds: List[float] = []
            qualities: List[float] = []
            durations: List[float] = []

            for idx, case in enumerate(suite):
                if on_progress:
                    on_progress(model, idx, len(suite))

                try:
                    start = time.perf_counter()
                    resp = self._chat_model(
                        model=model,
                        task=t,
                        messages=case.messages,
                        max_tokens=case.max_tokens,
                        temperature=case.temperature,
                    )
                    duration = max(1e-6, time.perf_counter() - start)

                    output = self._extract_content(resp)
                    usage = self._extract_usage(resp)

                    tokens_out = usage.get("completion_tokens")
                    if not isinstance(tokens_out, int) or tokens_out <= 0:
                        tokens_out = max(1, int(len(output.split()) * 1.3))

                    speed = float(tokens_out) / float(duration)

                    if case.validator:
                        q = float(case.validator(output, case.expected))
                    else:
                        q = 1.0 if not case.expected else _score_exact(output, case.expected)

                    outputs.append(output)
                    speeds.append(speed)
                    qualities.append(q)
                    durations.append(duration)

                    self._save_benchmark_row(
                        task=t,
                        model=model,
                        duration_sec=duration,
                        tokens_per_sec=speed,
                        quality_score=q,
                        output_sample=output,
                        case_index=idx,
                    )

                except Exception as e:
                    logger.error(f"[Benchmark] Case {idx} failed for {model}: {e}")
                    outputs.append(f"Error: {e}")
                    speeds.append(0.0)
                    qualities.append(0.0)
                    durations.append(0.0)

            avg_speed = sum(speeds) / len(speeds) if speeds else 0.0
            avg_quality = sum(qualities) / len(qualities) if qualities else 0.0
            avg_duration = sum(durations) / len(durations) if durations else 0.0

            results[model] = {
                "avg_speed": avg_speed,
                "avg_quality": avg_quality,
                "avg_duration": avg_duration,
                "outputs": outputs,
            }
            speeds_for_norm.append(avg_speed)

            # ── CUDA cache clear after each model swap (Issue #3) ─────────────
            _clear_cuda_cache()

        valid = {m: r for m, r in results.items() if isinstance(r, dict) and "error" not in r}
        if not valid:
            return {
                "results": results,
                "winner": None,
                "winner_score": None,
                "recommendation": "All models failed to run.",
            }

        max_speed = max(speeds_for_norm) if speeds_for_norm else 1.0

        def composite(m: str) -> float:
            r = valid[m]
            q = float(r.get("avg_quality", 0.0))
            s = float(r.get("avg_speed", 0.0)) / max_speed if max_speed > 0 else 0.0
            return (0.80 * q) + (0.20 * s)

        winner = max(valid.keys(), key=lambda m: (valid[m]["avg_quality"], valid[m]["avg_speed"]))
        winner_score = composite(winner)
        recommendation = self._generate_recommendation(valid, winner)

        logger.info(f"[Benchmark] Complete. Winner: {winner} (score={winner_score:.3f})")

        return {
            "results": results,
            "winner": winner,
            "winner_score": winner_score,
            "recommendation": recommendation,
        }

    # -------------------------- Internal helpers -------------------------- #

    def _chat_model(
        self,
        *,
        model: str,
        task: str,
        messages: List[Dict[str, Any]],
        max_tokens: int,
        temperature: float,
    ) -> Any:
        profile = self._get_profile(task)
        return self.lms.chat(
            messages=messages,
            model=model,
            profile=profile,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    def _extract_content(self, resp: Any) -> str:
        if isinstance(resp, dict):
            choices = resp.get("choices")
            if isinstance(choices, list) and choices:
                msg = choices[0].get("message", {})
                if isinstance(msg, dict):
                    return str(msg.get("content", "")).strip()
            c = resp.get("content")
            if isinstance(c, str):
                return c.strip()
        if isinstance(resp, str):
            return resp.strip()
        return str(resp).strip()

    def _extract_usage(self, resp: Any) -> Dict[str, Any]:
        if isinstance(resp, dict):
            u = resp.get("usage")
            return u if isinstance(u, dict) else {}
        return {}

    def _get_profile(self, task: str) -> str:
        profile_map = {
            "vision_drawing": "vision_extraction",
            "vision_classification": "vision_classification",
            "vision": "vision_classification",
            "vlm": "vision_classification",
            "entity_extraction": "entity_extraction",
            "extraction": "entity_extraction",
            "qa": "qa",
            "chat": "qa",
            "analysis": "qa",
            "reasoning": "qa",
            "summarization": "summarization",
            "summary": "summarization",
            "creative_writing": "creative_writing",
        }
        return profile_map.get(task, "qa")

    def _discover_models(self) -> List[str]:
        for attr in ("list_models", "get_models", "available_models"):
            if hasattr(self.lms, attr):
                try:
                    val = getattr(self.lms, attr)()
                    return self._parse_model_list(val)
                except Exception:
                    pass
        for attr in ("models", "available"):
            if hasattr(self.lms, attr):
                try:
                    return self._parse_model_list(getattr(self.lms, attr))
                except Exception:
                    pass
        return []

    def _parse_model_list(self, val: Any) -> List[str]:
        if isinstance(val, list):
            out = []
            for x in val:
                if isinstance(x, str):
                    out.append(x)
                elif isinstance(x, dict) and "id" in x:
                    out.append(str(x["id"]))
            return [m for m in out if m]
        if isinstance(val, dict):
            data = val.get("data")
            if isinstance(data, list):
                out = []
                for x in data:
                    if isinstance(x, dict) and "id" in x:
                        out.append(str(x["id"]))
                return [m for m in out if m]
        return []

    # -------------------------- DB persistence (schema-tolerant) -------------------------- #

    def _table_columns(self, table: str) -> List[str]:
        try:
            rows = self.global_db.execute(f"PRAGMA table_info({table})").fetchall()
            return [r[1] for r in rows if len(r) >= 2]
        except Exception:
            return []

    def _save_benchmark_row(
        self,
        *,
        task: str,
        model: str,
        duration_sec: float,
        tokens_per_sec: float,
        quality_score: float,
        output_sample: str,
        case_index: int,
    ) -> None:
        """
        Insert one row into model_benchmarks.
        benchmark_id MUST be unique (PK). We use uuid4 + case_index.
        """
        try:
            table = "model_benchmarks"
            cols = set(self._table_columns(table))
            if not cols:
                return

            now = int(time.time())
            payload: Dict[str, Any] = {}

            if "benchmark_id" in cols:
                # Use time_ns + unique entropy to avoid PK collisions
                safe_task = "".join(c for c in task if c.isalnum() or c in ("-", "_"))
                safe_model = "".join(c for c in model if c.isalnum() or c in ("-", "_"))
                payload["benchmark_id"] = f"{safe_task}_{safe_model}_{time.time_ns()}_{case_index}_{uuid.uuid4().hex[:6]}"
            if "task" in cols:
                payload["task"] = task
            if "model" in cols:
                payload["model"] = model
            if "duration_sec" in cols:
                payload["duration_sec"] = float(duration_sec)
            if "tokens_per_sec" in cols:
                payload["tokens_per_sec"] = float(tokens_per_sec)
            if "quality_score" in cols:
                payload["quality_score"] = float(quality_score)
            if "output_sample" in cols:
                payload["output_sample"] = (output_sample or "")[:500]
            if "created_at" in cols:
                payload["created_at"] = now

            if not payload:
                return

            keys = list(payload.keys())
            qmarks = ",".join(["?"] * len(keys))
            sql = f"INSERT INTO {table} ({','.join(keys)}) VALUES ({qmarks})"
            self.global_db.execute(sql, tuple(payload[k] for k in keys))
            if hasattr(self.global_db, "commit"):
                self.global_db.commit()

        except Exception as e:
            logger.debug(f"[Benchmark] Failed to save benchmark row: {e}")

    def _load_preference(self, *, task: str, max_age_seconds: int) -> Optional[str]:
        """
        Supports BOTH schemas:
          - (task, preferred_model, last_updated)  [your current DB]
          - (task, model, updated_at/last_updated/created_at)
        """
        try:
            table = "model_preferences"
            cols = set(self._table_columns(table))
            if not cols or "task" not in cols:
                return None

            now = int(time.time())

            if "preferred_model" in cols:
                ts_col = "last_updated" if "last_updated" in cols else None
                if ts_col:
                    row = self.global_db.execute(
                        f"SELECT preferred_model, {ts_col} FROM {table} WHERE task=? ORDER BY {ts_col} DESC LIMIT 1",
                        (task,),
                    ).fetchone()
                else:
                    row = self.global_db.execute(
                        f"SELECT preferred_model FROM {table} WHERE task=? LIMIT 1",
                        (task,),
                    ).fetchone()

                if not row:
                    return None

                model = row[0]
                ts = int(row[1]) if (len(row) >= 2 and row[1] is not None) else None
                if ts is not None and max_age_seconds > 0 and (now - ts) > max_age_seconds:
                    return None
                return str(model) if model else None

            if "model" in cols:
                ts_col = None
                for c in ("updated_at", "last_updated", "created_at"):
                    if c in cols:
                        ts_col = c
                        break

                if ts_col:
                    row = self.global_db.execute(
                        f"SELECT model, {ts_col} FROM {table} WHERE task=? ORDER BY {ts_col} DESC LIMIT 1",
                        (task,),
                    ).fetchone()
                else:
                    row = self.global_db.execute(
                        f"SELECT model FROM {table} WHERE task=? LIMIT 1",
                        (task,),
                    ).fetchone()

                if not row:
                    return None

                model = row[0]
                ts = int(row[1]) if (len(row) >= 2 and row[1] is not None) else None
                if ts is not None and max_age_seconds > 0 and (now - ts) > max_age_seconds:
                    return None
                return str(model) if model else None

            return None
        except Exception:
            return None

    def _save_preference(self, *, task: str, model: str, score: Optional[float] = None) -> None:
        """
        Write preference using whatever schema exists.
        For your DB: INSERT OR REPLACE (task, preferred_model, last_updated)
        """
        try:
            table = "model_preferences"
            cols = set(self._table_columns(table))
            if not cols or "task" not in cols:
                return

            now = int(time.time())

            if "preferred_model" in cols:
                if "last_updated" in cols:
                    self.global_db.execute(
                        f"INSERT OR REPLACE INTO {table} (task, preferred_model, last_updated) VALUES (?, ?, ?)",
                        (task, model, now),
                    )
                else:
                    self.global_db.execute(
                        f"INSERT OR REPLACE INTO {table} (task, preferred_model) VALUES (?, ?)",
                        (task, model),
                    )
                if hasattr(self.db, "commit"):
                    self.db.commit()
                return

                if hasattr(self.db, "commit"):
                    self.db.commit()
                return

            # Fallback legacy support (can be removed if migration 006 is guaranteed)
            if "model" in cols:
                ts_col = "updated_at" if "updated_at" in cols else ("last_updated" if "last_updated" in cols else None)
                if ts_col:
                    self.global_db.execute(
                        f"INSERT OR REPLACE INTO {table} (task, model, {ts_col}) VALUES (?, ?, ?)",
                        (task, model, now),
                    )
                else:
                    self.global_db.execute(
                        f"INSERT OR REPLACE INTO {table} (task, model) VALUES (?, ?)",
                        (task, model),
                    )
                if hasattr(self.global_db, "commit"):
                    self.global_db.commit()
                return

        except Exception as e:
            logger.debug(f"[Benchmark] Failed to save preference: {e}")

    # -------------------------- Recommendation string -------------------------- #

    def _generate_recommendation(self, results: Dict[str, Dict[str, Any]], winner: str) -> str:
        fastest = max(results.items(), key=lambda x: x[1].get("avg_speed", 0.0))[0]
        best_quality = max(results.items(), key=lambda x: x[1].get("avg_quality", 0.0))[0]

        if winner == fastest == best_quality:
            return f"✅ {winner} is the clear winner (best quality AND speed)"
        if winner == best_quality:
            return (
                f"✅ {winner} has best quality ({results[winner]['avg_quality']:.1%}), "
                f"but {fastest} is faster ({results[fastest]['avg_speed']:.1f} tok/s)"
            )
        return f"✅ {winner} offers best balance. {best_quality} has higher quality, {fastest} is faster."

    # -------------------------- History API (kept) -------------------------- #

    def get_benchmark_history(self, task: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            table = "model_benchmarks"
            cols = set(self._table_columns(table))
            if not cols or "task" not in cols or "model" not in cols:
                return []

            qcol = "quality_score" if "quality_score" in cols else None
            scol = "tokens_per_sec" if "tokens_per_sec" in cols else None

            if task:
                query = f"""
                    SELECT task, model
                    {', AVG(' + qcol + ')' if qcol else ''}
                    {', AVG(' + scol + ')' if scol else ''}
                    , COUNT(*) as runs
                    FROM {table}
                    WHERE task = ?
                    GROUP BY task, model
                    ORDER BY runs DESC
                """
                rows = self.global_db.execute(query, (task,)).fetchall()
            else:
                query = f"""
                    SELECT task, model
                    {', AVG(' + qcol + ')' if qcol else ''}
                    {', AVG(' + scol + ')' if scol else ''}
                    , COUNT(*) as runs
                    FROM {table}
                    GROUP BY task, model
                    ORDER BY task, runs DESC
                """
                rows = self.global_db.execute(query).fetchall()

            history: List[Dict[str, Any]] = []
            for r in rows:
                entry = {"task": r[0], "model": r[1], "runs": r[-1]}
                idx = 2
                if qcol:
                    entry["avg_quality"] = r[idx]
                    idx += 1
                if scol:
                    entry["avg_speed"] = r[idx]
                history.append(entry)

            return history

        except Exception as e:
            logger.error(f"[Benchmark] Failed to get history: {e}")
            return []
