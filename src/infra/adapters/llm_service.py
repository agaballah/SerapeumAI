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
llm_service.py — Unified LLM interface for SerapeumAI
-----------------------------------------------------

Supports:
    • LM Studio (multi-model) via local REST API + intelligent routing
    • Legacy embedded llama-cpp-python (single-model / universal VLM)
    • Vision capabilities (multimodal)
    • Best-effort strict JSON helper

Exposes:
    LLMService.chat(...)
    LLMService.chat_json(...)
    LLMService.analyze_image(...)
"""

from __future__ import annotations

import json
import os
import logging
from contextlib import nullcontext
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Check if llama-cpp-python is available (legacy mode only)
try:
    from llama_cpp import Llama  # noqa: F401
    _HAS_LLAMA_CPP = True
except Exception:
    _HAS_LLAMA_CPP = False


DEFAULT_MODEL_PATH = "models/Qwen2-VL-7B-Instruct-Q6_K_L.gguf"
DEFAULT_CONTEXT_WINDOW = 4096
DEFAULT_GPU_LAYERS = 33  # 0 = CPU only, 33 = full GPU offload for 7B model


class LLMService:
    def __init__(
        self,
        db=None,
        *,
        global_db=None,
        model_path: str = None,
        use_gpu: bool = True,
        n_gpu_layers: int = None,
        n_ctx: int = DEFAULT_CONTEXT_WINDOW,
        verbose: bool = False,
    ):
        """
        Initialize LLM service with LM Studio or legacy llama-cpp-python.

        Args:
            db: Project database manager (optional)
            global_db: Global database manager (for shared benchmarks/prefs)
            model_path: Path to GGUF model file (legacy mode only)
            use_gpu: Enable GPU acceleration (legacy mode only)
            n_gpu_layers: Number of layers to offload to GPU (legacy mode only)
            n_ctx: Context window size (legacy mode only)
            verbose: Enable llama.cpp debug logging (legacy mode only)
        """
        from src.infra.config.configuration_manager import get_config

        self.db = db
        self.global_db = global_db
        self.router = None
        self.lm_studio = None
        self.llm = None
        self._get_model = None

        config = get_config()

        # Check if LM Studio integration is enabled
        lm_config = config.get_section("lm_studio") or {}
        self.use_lm_studio = bool(lm_config.get("enabled", False))

        if self.use_lm_studio:
            # Use LM Studio v1 API + model router (auto benchmark selection)
            from src.infra.adapters.lm_studio_service import LMStudioService
            from src.infra.adapters.model_router import ModelRouter

            self.lm_studio = LMStudioService(config)

            # Router uses global_db for benchmarks/preferences if available, falls back to project db
            target_db = global_db or db
            self.router = ModelRouter(target_db, self.lm_studio, config=config) if target_db else None

            self.model = "lm-studio"
            logger.info("[LLMService] Using LM Studio (multi-model) with intelligent routing")
            return

        # Legacy mode: llama-cpp-python
        if not _HAS_LLAMA_CPP:
            raise ImportError(
                "llama-cpp-python not installed (required for legacy mode). "
                "Install with: pip install llama-cpp-python"
            )

        # Legacy: Unified Single Model Architecture
        from .model_manager import get_model_for_task

        self._get_model = get_model_for_task
        self.model = "universal-vlm"
        self.use_gpu = use_gpu

        # Legacy knobs (kept for signature compatibility; actual values are applied in ModelManager)
        self._legacy_model_path = model_path or DEFAULT_MODEL_PATH
        self._legacy_n_ctx = int(n_ctx or DEFAULT_CONTEXT_WINDOW)
        self._legacy_n_gpu_layers = int(n_gpu_layers if n_gpu_layers is not None else DEFAULT_GPU_LAYERS)
        self._legacy_verbose = bool(verbose)

        logger.info("[LLMService] Initialized in legacy llama.cpp mode (single-model)")

    def load_model(self, task_type: str = "universal"):
        """Explicitly trigger model loading."""
        if self.use_lm_studio:
            logger.info("[LLMService] LM Studio mode - models managed by server")
            return None
        return self._get_model(task_type, auto_load=True)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _extract_message_content(self, resp: Any) -> str:
        """
        Extract assistant text from:
        - OpenAI-like dict {"choices":[{"message":{"content":...}}]}
        - dict {"content": "..."} (some adapters)
        - raw string
        """
        if isinstance(resp, dict):
            c = resp.get("content")
            if isinstance(c, str) and c.strip():
                return c.strip()

            choices = resp.get("choices")
            if isinstance(choices, list) and choices:
                msg = choices[0].get("message", {})
                if isinstance(msg, dict):
                    return str(msg.get("content", "")).strip()

        if isinstance(resp, str):
            return resp.strip()

        return str(resp).strip()

    def _cancel_requested(self, cancellation_token) -> bool:
        """Best-effort cancellation check without assuming a specific token API."""
        if not cancellation_token:
            return False

        if hasattr(cancellation_token, "is_cancelled"):
            try:
                return bool(cancellation_token.is_cancelled())
            except Exception:
                return False

        if hasattr(cancellation_token, "is_set"):
            try:
                return bool(cancellation_token.is_set())
            except Exception:
                return False

        if hasattr(cancellation_token, "check"):
            try:
                out = cancellation_token.check()
                return bool(out) if isinstance(out, bool) else False
            except Exception:
                return True

        return False

    def _inference_lock_ctx(self):
        """
        Return a context manager for the global inference lock if present,
        otherwise a no-op context manager.
        """
        try:
            from .model_manager import ModelManager  # local module
        except Exception:
            ModelManager = None  # type: ignore

        lock_obj = None

        if ModelManager is not None:
            try:
                inst = ModelManager()
                lock_obj = getattr(inst, "inference_lock", None)
            except Exception:
                lock_obj = None

            if lock_obj is None:
                lock_obj = getattr(ModelManager, "inference_lock", None)

        return lock_obj if lock_obj is not None else nullcontext()

    # ------------------------------------------------------------------ #
    # Core Chat
    # ------------------------------------------------------------------ #

    def chat(self, **kwargs) -> Any:
        from src.utils.hardening import llm_circuit
        return llm_circuit(self._chat_core)(**kwargs)

    def _chat_core(
        self,
        *,
        messages: List[Dict[str, Any]],
        task_type: str = "universal",
        temperature: float = 0.3,
        top_p: float = 0.92,
        max_tokens: int = 1024,
        stream: bool = False,
        model: Optional[str] = None,  # explicit override (LM Studio mode)
        timeout: Optional[int] = None,  # accepted for compatibility
        cancellation_token=None,
        **extra,
    ) -> Any:
        """
        Internal core chat implementation.
        """
        import time as _time

        extra = dict(extra or {})
        extra.pop("extra", None)
        extra.pop("cancellation_token", None)
        extra.pop("timeout", None)

        # LM Studio mode
        if self.use_lm_studio:
            return self._chat_lm_studio(
                messages=messages,
                task_type=task_type,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                stream=stream,
                model=model,
                **extra,
            )

        # Legacy mode
        from src.infra.telemetry.llm_logger import get_llm_logger
        from src.utils.retry import retry, RetryStrategy
        from src.analysis_engine.health_tracker import get_health_tracker

        llm_logger = get_llm_logger()
        start_time = _time.time()

        # Optional dynamic task profiles (kept)
        if task_type == "analysis":
            if temperature == 0.7:
                temperature = 0.1
            if top_p == 0.95:
                top_p = 0.1
        elif task_type == "vision":
            if max_tokens == 1000:
                max_tokens = 2000

        user_prompt_log = ""
        try:
            # Always get Universal Model
            model_obj = self._get_model(task_type, auto_load=True)
            if not model_obj:
                raise RuntimeError("Universal Model failed to load.")

            inference_messages = messages  # keep multimodal list intact

            # Prepare user prompt log (text only)
            for m in messages:
                if m.get("role") == "user":
                    content = m.get("content", "")
                    if isinstance(content, list):
                        parts = [
                            x.get("text", "")
                            for x in content
                            if isinstance(x, dict) and x.get("type") == "text"
                        ]
                        user_prompt_log = " ".join(parts)
                    else:
                        user_prompt_log = str(content)

            call_id = llm_logger.log_call(
                task_type=task_type,
                model=self.model,
                system_prompt=next((m.get("content") for m in messages if m.get("role") == "system"), "") or "",
                user_prompt=user_prompt_log,
                temperature=temperature,
                max_tokens=max_tokens,
                context_length=0,
                metadata=extra,
            )

            llama_kwargs = dict(extra or {})
            llama_kwargs.pop("response_format", None)

            # --- STREAMING PATH ---
            if stream:

                def _stream_generator():
                    full_content: List[str] = []
                    ok = True
                    try:
                        with self._inference_lock_ctx():
                            response_gen = model_obj.create_chat_completion(
                                messages=inference_messages,
                                temperature=float(temperature),
                                top_p=float(top_p),
                                max_tokens=int(max_tokens),
                                stream=True,
                                **(llama_kwargs or {}),
                            )

                            for chunk in response_gen:
                                if self._cancel_requested(cancellation_token):
                                    logger.info("[LLMService] Generation cancelled by user.")
                                    break

                                delta = (
                                    (chunk.get("choices") or [{}])[0].get("delta", {})
                                    if isinstance(chunk, dict)
                                    else {}
                                )
                                content = delta.get("content", "")
                                if content:
                                    full_content.append(content)
                                    yield content

                    except Exception as e:
                        ok = False
                        logger.error(f"[LLMService] Streaming error: {e}")
                        yield f"\n[Error: {e}]"
                    finally:
                        duration = _time.time() - start_time
                        llm_logger.log_response(
                            call_id=call_id,
                            response={"content": "".join(full_content)},
                            duration_seconds=duration,
                            success=ok,
                        )
                        try:
                            get_health_tracker().record_metric("llm_latency", duration, {"task_type": task_type})
                        except Exception:
                            pass

                return _stream_generator()

            # --- STANDARD BLOCKING PATH ---

            @retry(
                max_attempts=3,
                strategy=RetryStrategy.EXPONENTIAL,
                base_delay=2.0,
                max_delay=10.0,
                on_retry=lambda attempt, err: logger.warning(f"[LLMService] Retry {attempt}/3: {err}"),
            )
            def _call_with_retry():
                if self._cancel_requested(cancellation_token):
                    raise RuntimeError("Operation cancelled before start")

                with self._inference_lock_ctx():
                    return model_obj.create_chat_completion(
                        messages=inference_messages,
                        temperature=float(temperature),
                        top_p=float(top_p),
                        max_tokens=int(max_tokens),
                        stream=False,
                        **(llama_kwargs or {}),
                    )

            response = _call_with_retry()
            duration = _time.time() - start_time
            response_content = self._extract_message_content(response)

            # Optional DB audit log
            if self.db and task_type in ["vision", "analysis"]:
                try:
                    self.db.log_vlm_call(
                        task_type=task_type,
                        system_prompt=next((m.get("content") for m in messages if m.get("role") == "system"), "") or "",
                        user_prompt=user_prompt_log,
                        response_raw=response_content,
                        duration_ms=int(duration * 1000),
                        model=self.model,
                        status="success",
                        error_msg=None,
                    )
                except Exception as db_err:
                    logger.debug(f"[LLMService] Failed to log to audit trail: {db_err}")

            llm_logger.log_response(
                call_id=call_id,
                response=response,
                duration_seconds=duration,
                success=True,
                tokens_used=response.get("usage", {}) if isinstance(response, dict) else None,
            )
            try:
                get_health_tracker().record_metric("llm_latency", duration, {"task_type": task_type})
            except Exception:
                pass

            return response

        except Exception as e:
            duration = _time.time() - start_time

            if self.db and task_type in ["vision", "analysis"]:
                try:
                    self.db.log_vlm_call(
                        task_type=task_type,
                        system_prompt=next((m.get("content") for m in messages if m.get("role") == "system"), "") or "",
                        user_prompt=user_prompt_log,
                        response_raw="",
                        duration_ms=int(duration * 1000),
                        model=self.model,
                        status="error",
                        error_msg=str(e),
                    )
                except Exception:
                    pass

            try:
                if "call_id" in locals():
                    llm_logger.log_response(
                        call_id=call_id,
                        response=None,
                        duration_seconds=duration,
                        success=False,
                        error=str(e),
                    )
            except Exception:
                pass

            return {
                "choices": [{"message": {"content": f"[llm.error] {type(e).__name__}: {e}"}}],
                "error": str(e),
            }

    # ------------------------------------------------------------------ #
    # Strict JSON
    # ------------------------------------------------------------------ #

    def chat_json(
        self,
        *,
        system: str,
        user: str,
        schema: Optional[Dict[str, Any]] = None,
        schema_hint: str = None,
        max_tokens: int = 1000,
        temperature: float = 0.2,
        timeout: int = 120,
        task_type: str = "analysis",
    ) -> Optional[Dict[str, Any]]:
        """
        Best-effort JSON helper for analysis / tooling calls.

        Behavior:
        - Strengthens the system prompt to demand raw JSON.
        - If `schema` is provided, includes it in the system prompt for guidance.
        - Cleans markdown fences and extracts the JSON object between the first '{' and last '}'.
        """
        base_system = (system or "").strip()

        if schema:
            schema_str = json.dumps(schema, indent=2, ensure_ascii=False)
            base_system += (
                "\n\nYou MUST respond with JSON matching this exact schema:\n"
                f"```json\n{schema_str}\n```"
            )
        elif schema_hint:
            base_system += f"\n\nJSON SCHEMA HINT:\n{schema_hint.strip()}"

        json_system = (
            base_system
            + "\n\nCRITICAL:\n"
            "- Respond with a SINGLE JSON object only.\n"
            "- No markdown code fences.\n"
            "- No explanations, comments, or prose.\n"
            "- Do NOT add any keys outside the requested JSON shape."
        )

        resp = self.chat(
            messages=[
                {"role": "system", "content": json_system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            task_type=task_type,
        )

        txt = self._extract_message_content(resp)
        if not txt:
            return None

        raw = str(txt)
        cleaned = raw.strip()

        # Strip markdown code fences if present
        if cleaned.startswith("```"):
            parts = cleaned.split("```")
            if len(parts) >= 2:
                cleaned = parts[1]
            cleaned = cleaned.lstrip()
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:]
        cleaned = cleaned.strip()

        # Fast path
        try:
            return json.loads(cleaned)
        except Exception:
            pass

        # Extract { ... } span
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        candidate = cleaned[start:end + 1] if (start != -1 and end != -1 and end > start) else cleaned

        # Trailing comma repair
        import re
        candidate = re.sub(r",\s*\}", "}", candidate)
        candidate = re.sub(r",\s*\]", "]", candidate)

        try:
            return json.loads(candidate)
        except Exception:
            pass

        tail = candidate.rfind("}")
        if tail != -1:
            candidate2 = candidate[:tail + 1]
            try:
                return json.loads(candidate2)
            except Exception:
                pass

        logger.warning("[LLMService] JSON parse failed")
        logger.debug(f"[LLMService] Raw text (first 200 chars): {raw[:200]}")
        return None

    # ------------------------------------------------------------------ #
    # Vision (Image Analysis)
    # ------------------------------------------------------------------ #

    def analyze_image(
        self,
        *,
        image_path: str,
        prompt: str = "Describe this image in detail.",
        max_tokens: int = 500,
        temperature: float = 0.7,
    ) -> str:
        """
        Analyze an image using vision capabilities.
        Works in both LM Studio mode and legacy embedded mode.
        """
        if not os.path.exists(image_path):
            return f"[error] Image not found: {image_path}"

        try:
            import base64

            with open(image_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("ascii")

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a vision AI that analyzes document images. "
                        "Describe what you see in the image based on the user's request. "
                        "Be factual and concise."
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                    ],
                },
            ]

            if self.use_lm_studio:
                resp = self.chat(
                    messages=messages,
                    task_type="vision",
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=False,
                )
                return self._extract_message_content(resp)

            model_obj = self._get_model("vision", auto_load=True)
            if not model_obj:
                return "[error] Failed to load vision model."

            with self._inference_lock_ctx():
                response = model_obj.create_chat_completion(
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )

            return self._extract_message_content(response)

        except Exception as e:
            logger.error(f"[LLMService] Vision analysis failed: {e}")
            return f"Error analyzing image: {e}"

    # ------------------------------------------------------------------ #
    # LM Studio chat path
    # ------------------------------------------------------------------ #

    def _chat_lm_studio(
        self,
        messages: List[Dict[str, Any]],
        task_type: str,
        temperature: float,
        top_p: float,
        max_tokens: int,
        stream: bool,
        model: Optional[str] = None,  # explicit override
        **extra,
    ) -> Any:
        """
        LM Studio chat with intelligent model routing and telemetry.
        """
        import time as _time

        # Keep profiles aligned with BenchmarkService + your pipeline semantics
        profile_map = {
            "vision": "vision_classification",
            "vision_drawing": "vision_extraction",
            "vision_classification": "vision_classification",
            "vlm": "vision_classification",
            "analysis": "qa",
            "reasoning": "qa",
            "qa": "qa",
            "chat": "qa",
            "entity_extraction": "entity_extraction",
            "summarization": "summarization",
            "summary": "summarization",
            "creative_writing": "creative_writing",
            "creative": "creative_writing",
            "universal": "qa",
        }
        profile = profile_map.get((task_type or "qa").strip().lower(), "qa")

        chosen_model: Optional[str] = model  # explicit override wins
        status: Dict[str, Any] = {}

        # If no explicit model, use router selection
        if not chosen_model and self.router:
            chosen_model = self.router.get_best_model(task_type)

        # Best-effort ensure correct model loaded (LM Studio single-loaded-instance policy)
        try:
            status = self.lm_studio.get_status() or {}
            current_model = (status.get("model") or "").strip()
            if chosen_model:
                if (not status.get("loaded")) or (current_model and current_model != chosen_model):
                    logger.info(f"[LLMService] Loading model for {task_type}: {chosen_model}")
                    self.lm_studio.load_model(chosen_model)
        except Exception as e:
            logger.warning(f"[LLMService] Model load check failed (continuing): {e}")

        start_time = _time.time()

        try:
            with self._inference_lock_ctx():
                response = self.lm_studio.chat(
                    messages=messages,
                    profile=profile,
                    model=chosen_model,  # if None, LMStudioService may use profile defaults
                    stream=stream,
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                    **(extra or {}),
                )

            # Usage logging only for non-stream responses
            if (not stream) and self.router and isinstance(response, dict):
                duration_ms = int((_time.time() - start_time) * 1000)
                usage = response.get("usage", {}) if isinstance(response.get("usage"), dict) else {}
                used_model = chosen_model or (status.get("model") if isinstance(status, dict) else None) or "unknown"

                self.router.record_usage(
                    model=used_model,
                    task_type=task_type,
                    tokens_in=int(usage.get("prompt_tokens", 0) or 0),
                    tokens_out=int(usage.get("completion_tokens", 0) or 0),
                    duration_ms=duration_ms,
                )

            return response

        except Exception as e:
            logger.error(f"[LLMService] LM Studio chat failed: {e}")
            return {
                "choices": [{"message": {"content": f"Error: {e}"}}],
                "error": str(e),
            }

    # ------------------------------------------------------------------ #
    # Compatibility Methods (for existing code)
    # ------------------------------------------------------------------ #

    @property
    def base_url(self):
        """Compatibility property."""
        return "embedded://qwen2-vl-7b" if not self.use_lm_studio else "lmstudio://local"

    @property
    def api_key(self):
        """Compatibility property."""
        return ""
