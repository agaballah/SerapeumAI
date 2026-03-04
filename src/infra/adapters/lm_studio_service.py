# -*- coding: utf-8 -*-
"""
lm_studio_service.py — LM Studio v1 REST + OpenAI-compat integration (headless-capable)
-------------------------------------------------------------------------------------

Goals for SerapeumAI:
- Run without the user opening LM Studio UI
- Auto-start the LM Studio local server (when possible) via `lms` CLI
- Use LM Studio native v1 REST endpoints (/api/v1/*) for model mgmt + stateful chat
- Keep OpenAI-compatible streaming behavior for existing stream parsers

Key behavior:
- If server is not reachable, attempt:
    1) `lms daemon up` (best-effort)
    2) `lms server start --port <port>` (best-effort)
  Then re-check until reachable or timeout.

Config keys (lm_studio section):
- enabled: bool
- url: "http://127.0.0.1:1234"
- tokens: { chat: "", admin: "" }         # optional
- profiles: { qa: {...}, vision_extraction: {...} }

Optional headless controls:
- autostart_server: true|false            # default true
- start_daemon: true|false                # default true
- start_server: true|false                # default true
- startup_timeout_s: 45                   # default 45
- lms_path: "C:/path/to/lms.exe"          # optional; otherwise uses PATH
- cors: true|false                        # passed to `lms server start` (default false)

Notes:
- Streaming: uses OpenAI-compatible /v1/chat/completions (SSE "data: {...}")
- Non-stream chat: uses native /api/v1/chat then adapts response to OpenAI-like dict
- Compatibility: also returns top-level `content` + `usage` for older code.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import shutil
import subprocess
import time
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)


class LMStudioService:
    """
    LM Studio v1 API client with headless auto-start and safe fallbacks.

    Public API kept compatible with existing code:
    - chat(...)
    - vision_chat(...)
    - load_model(...)
    - unload_model(...)
    - download_model(...)
    - get_download_status(...)
    - get_status()
    - list_models()
    - is_model_downloaded(...)
    """

    def __init__(self, config):
        lm_config = (config.get_section("lm_studio") or {}) if config else {}

        self.enabled: bool = bool(lm_config.get("enabled", False))
        self.url: str = str(lm_config.get("url", "http://127.0.0.1:1234")).rstrip("/")

        self.tokens: Dict[str, str] = dict(lm_config.get("tokens", {}) or {})
        self.profiles: Dict[str, Dict[str, Any]] = dict(lm_config.get("profiles", {}) or {})

        # Headless / auto-start controls
        self.autostart_server: bool = bool(lm_config.get("autostart_server", True))
        self.start_daemon: bool = bool(lm_config.get("start_daemon", True))
        self.start_server: bool = bool(lm_config.get("start_server", True))
        self.startup_timeout_s: int = int(lm_config.get("startup_timeout_s", 45))
        self.lms_path: Optional[str] = (lm_config.get("lms_path") or None) or None
        self.cors: bool = bool(lm_config.get("cors", False))

        self._startup_attempted: bool = False

        if self.enabled:
            self._ensure_server_running()
        else:
            logger.info("[LMStudio] Integration disabled in config")

    # ----------------------------
    # Connection management
    # ----------------------------

    def _parse_host_port(self) -> Tuple[str, int]:
        parsed = urlparse(self.url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 1234
        return host, port

    def _is_server_reachable(self, timeout_s: float = 2.0) -> bool:
        """Check if the LM Studio server is responding."""
        try:
            # Short timeout to avoid blocking startup too long
            resp = requests.get(self.url, timeout=timeout_s)
            return resp.status_code < 500
        except Exception:
            try:
                # Fallback check
                resp = requests.get(f"{self.url}/v1/models", timeout=timeout_s)
                return resp.status_code < 500
            except Exception:
                return False

    def _run_cli(self, cmd: List[str], timeout_s: int = 45) -> Tuple[int, str]:
        """Run a command safely and return (exit_code, output)."""
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_s,
                check=False
            )
            return res.returncode, (res.stdout + res.stderr).strip()
        except subprocess.TimeoutExpired:
            return -1, "Command timed out"
        except Exception as e:
            return -1, f"Execution error: {e}"

    def _find_lms_cli(self) -> Optional[str]:
        """Locate the lms CLI executable. Auto-installs via npm if not found."""
        if self.lms_path:
            if os.path.exists(self.lms_path):
                return self.lms_path
            logger.warning(f"[LMStudio] lms_path configured but not found: {self.lms_path}")

        exe = "lms.exe" if os.name == "nt" else "lms"
        found = shutil.which(exe) or shutil.which("lms")
        if found:
            return found

        # lms not in PATH — try to auto-install via npm
        logger.warning("[LMStudio] `lms` CLI not found in PATH. Attempting auto-install via npm...")
        installed = self._auto_install_lms_cli()
        if installed:
            # Re-check PATH after install
            return shutil.which(exe) or shutil.which("lms") or installed
        return None

    def _auto_install_lms_cli(self) -> Optional[str]:
        """
        Attempt to install the LM Studio CLI using npm.
        Returns the path to the installed lms binary, or None if it failed.
        """
        npm = shutil.which("npm")
        if not npm:
            logger.error(
                "[LMStudio] npm not found — cannot auto-install `lms`. "
                "Please install Node.js from https://nodejs.org/, then run: "
                "npm install -g @lmstudio/lms"
            )
            return None

        logger.info("[LMStudio] Installing LM Studio CLI: npm install -g @lmstudio/lms ...")
        code, out = self._run_cli([npm, "install", "-g", "@lmstudio/lms"], timeout_s=120)
        if code == 0:
            logger.info("[LMStudio] `lms` CLI installed successfully.")
            return shutil.which("lms.exe" if os.name == "nt" else "lms") or shutil.which("lms")
        else:
            logger.error(
                f"[LMStudio] Auto-install failed (exit {code}): {out}\n"
                "Please install manually: npm install -g @lmstudio/lms"
            )
            return None

    def _ensure_server_running(self) -> None:
        if not self.enabled:
            return

        if self._is_server_reachable():
            return

        if not self.autostart_server:
            logger.warning("[LMStudio] Server not reachable and autostart_server=false")
            return

        if self._startup_attempted:
            return
        self._startup_attempted = True

        lms = self._find_lms_cli()
        if not lms:
            logger.error(
                "[LMStudio] Server not reachable and `lms` CLI could not be found or installed. "
                "Install Node.js (https://nodejs.org/) then run: npm install -g @lmstudio/lms"
            )
            return

        _, port = self._parse_host_port()
        logger.warning(f"[LMStudio] Server not reachable at {self.url}. Attempting headless start on port {port}...")

        if self.start_daemon:
            code, out = self._run_cli([lms, "daemon", "up"], timeout_s=30)
            if code == 0:
                logger.info("[LMStudio] Daemon is up.")
            else:
                logger.warning(f"[LMStudio] `lms daemon up` returned {code}: {out}")

        if self.start_server:
            cmd = [lms, "server", "start", "--port", str(port)]
            if self.cors:
                cmd.append("--cors")

            code, out = self._run_cli(cmd, timeout_s=30)
            if code == 0:
                logger.info("[LMStudio] Server start command executed.")
            else:
                logger.warning(f"[LMStudio] `lms server start` returned {code}: {out}")

        deadline = time.time() + max(5, self.startup_timeout_s)
        while time.time() < deadline:
            if self._is_server_reachable(timeout_s=1.5):
                logger.info(f"[LMStudio] Connected to {self.url}")
                return
            time.sleep(0.5)

        logger.error(f"[LMStudio] Failed to reach server at {self.url} after {self.startup_timeout_s}s.")

    # ----------------------------
    # HTTP helpers
    # ----------------------------

    def _get_headers(self, token_type: str = "chat") -> Dict[str, str]:
        token = (self.tokens or {}).get(token_type, "") if self.tokens else ""
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _request(
        self,
        method: str,
        path: str,
        *,
        token_type: str = "chat",
        json_body: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        stream: bool = False,
        timeout: int = 120,
    ) -> requests.Response:
        if not self.enabled:
            raise RuntimeError("LM Studio integration is disabled")

        self._ensure_server_running()
        url = f"{self.url}{path}"

        try:
            resp = requests.request(
                method=method,
                url=url,
                headers=self._get_headers(token_type),
                json=json_body,
                params=params,
                stream=stream,
                timeout=timeout,
            )
            resp.raise_for_status()
            return resp
        except requests.exceptions.ConnectionError:
            # Retry once after re-attempting startup
            if self.autostart_server:
                self._startup_attempted = False
                self._ensure_server_running()
                resp = requests.request(
                    method=method,
                    url=url,
                    headers=self._get_headers(token_type),
                    json=json_body,
                    params=params,
                    stream=stream,
                    timeout=timeout,
                )
                resp.raise_for_status()
                return resp
            raise
        except Exception as e:
            logger.error(f"[LMStudio] HTTP {method} {path} failed: {e}")
            raise

    # ----------------------------
    # Profile/settings helpers
    # ----------------------------

    def _profile_settings(self, profile: str, overrides: Dict[str, Any]) -> Dict[str, Any]:
        settings = (self.profiles.get(profile, {}) or {}).copy()
        settings.update(overrides or {})
        return settings

    def _native_settings_from_profile(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        mapped: Dict[str, Any] = {}
        passthrough = {
            "temperature",
            "top_p",
            "top_k",
            "min_p",
            "repeat_penalty",
            "reasoning",
            "context_length",
            "store",
            "integrations",
        }
        for k in passthrough:
            if k in settings:
                mapped[k] = settings[k]

        if "max_tokens" in settings and "max_output_tokens" not in settings:
            mapped["max_output_tokens"] = settings["max_tokens"]
        elif "max_output_tokens" in settings:
            mapped["max_output_tokens"] = settings["max_output_tokens"]

        return mapped

    def _messages_to_native_input(self, messages: List[Dict[str, Any]]) -> Tuple[Optional[str], Any]:
        system_prompt = None
        items: List[Dict[str, Any]] = []

        for m in messages or []:
            role = m.get("role")
            content = m.get("content")

            if role == "system" and system_prompt is None:
                if isinstance(content, str):
                    system_prompt = content
                continue

            if isinstance(content, str):
                items.append({"type": "message", "content": content})
            elif isinstance(content, list):
                for part in content:
                    if not isinstance(part, dict):
                        continue
                    ptype = part.get("type")
                    if ptype == "text":
                        items.append({"type": "message", "content": str(part.get("text", ""))})
                    elif ptype in ("image_url", "image"):
                        if ptype == "image_url":
                            url = (part.get("image_url") or {}).get("url", "")
                            if isinstance(url, str) and url.startswith("data:"):
                                items.append({"type": "image", "data_url": url})
            else:
                items.append({"type": "message", "content": str(content)})

        if len(items) == 1 and items[0].get("type") == "message":
            return system_prompt, items[0].get("content", "")

        return system_prompt, items

    # ----------------------------
    # Response adaptation (native -> OpenAI-like + legacy)
    # ----------------------------

    def _native_chat_to_openai_chatcompletions(self, native: Dict[str, Any], model: str) -> Dict[str, Any]:
        output_items = native.get("output") or []
        texts: List[str] = []

        for item in output_items:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "message":
                texts.append(str(item.get("content", "")))

        assistant_text = "\n".join([t for t in texts if t]).strip()

        usage = {
            "prompt_tokens": int((native.get("stats") or {}).get("input_tokens", 0) or 0),
            "completion_tokens": int((native.get("stats") or {}).get("total_output_tokens", 0) or 0),
        }
        usage["total_tokens"] = int(usage["prompt_tokens"] + usage["completion_tokens"])

        openai_like: Dict[str, Any] = {
            "id": native.get("response_id") or f"lmstudio_resp_{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": assistant_text},
                    "finish_reason": "stop",
                }
            ],
            "usage": usage,
            "_lmstudio": native,
        }

        # Compatibility keys for older callers (e.g., BenchmarkService)
        openai_like["content"] = assistant_text
        openai_like["usage"] = usage
        return openai_like

    def _prepare_openai_chatcompletions_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        safe_keys = {
            "model",
            "messages",
            "temperature",
            "max_tokens",
            "stream",
            "top_p",
            "frequency_penalty",
            "presence_penalty",
            "stop",
            "response_format",
            "tools",
            "tool_choice",
        }
        return {k: v for k, v in (payload or {}).items() if k in safe_keys}

    # ----------------------------
    # Chat
    # ----------------------------

    def chat(
        self,
        messages: List[Dict[str, Any]],
        profile: str = "qa",
        previous_response_id: Optional[str] = None,
        stream: bool = False,
        model: Optional[str] = None,
        **overrides,
    ) -> Dict[str, Any] | Iterator[Dict[str, Any]]:
        if not self.enabled:
            raise RuntimeError("LM Studio integration is disabled")

        settings = self._profile_settings(profile, overrides)
        target_model = model or settings.get("model") or "local-model"

        if stream:
            payload = {
                "model": target_model,
                "messages": messages,
                "stream": True,
                **settings,
            }
            openai_payload = self._prepare_openai_chatcompletions_payload(payload)
            if previous_response_id:
                logger.warning("[LMStudio] previous_response_id not supported for /v1/chat/completions streaming; ignored.")
            return self._chat_completions_stream(openai_payload)

        system_prompt, native_input = self._messages_to_native_input(messages)
        native_settings = self._native_settings_from_profile(settings)

        native_payload: Dict[str, Any] = {
            "model": target_model,
            "input": native_input,
            **native_settings,
        }
        if system_prompt:
            native_payload["system_prompt"] = system_prompt
        if previous_response_id:
            native_payload["previous_response_id"] = previous_response_id

        native_resp = self._request(
            "POST",
            "/api/v1/chat",
            token_type="chat",
            json_body=native_payload,
            timeout=180,
        ).json()

        return self._native_chat_to_openai_chatcompletions(native_resp, model=target_model)

    def _chat_completions_stream(self, openai_payload: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
        resp = self._request(
            "POST",
            "/v1/chat/completions",
            token_type="chat",
            json_body=openai_payload,
            stream=True,
            timeout=180,
        )

        for line in resp.iter_lines():
            if not line:
                continue
            try:
                s = line.decode("utf-8", errors="ignore")
            except Exception:
                continue
            if not s.startswith("data: "):
                continue
            s = s[6:]
            if s.strip() == "[DONE]":
                break
            try:
                yield json.loads(s)
            except json.JSONDecodeError:
                continue

    # ----------------------------
    # Vision chat
    # ----------------------------

    def vision_chat(
        self,
        image: str,
        user_message: str,
        profile: str = "vision_extraction",
        previous_response_id: Optional[str] = None,
        model: Optional[str] = None,
        **overrides,
    ) -> Dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("LM Studio integration is disabled")

        settings = self._profile_settings(profile, overrides)
        target_model = model or settings.get("model") or "local-model"

        data_url = self._to_data_url(image)
        native_settings = self._native_settings_from_profile(settings)

        native_payload: Dict[str, Any] = {
            "model": target_model,
            "input": [
                {"type": "message", "content": user_message},
                {"type": "image", "data_url": data_url},
            ],
            **native_settings,
        }
        if previous_response_id:
            native_payload["previous_response_id"] = previous_response_id

        native_resp = self._request(
            "POST",
            "/api/v1/chat",
            token_type="chat",
            json_body=native_payload,
            timeout=240,
        ).json()

        return self._native_chat_to_openai_chatcompletions(native_resp, model=target_model)

    def _to_data_url(self, image: str) -> str:
        if isinstance(image, str) and image.startswith("data:"):
            return image

        if isinstance(image, str) and os.path.exists(image):
            path = image
            ext = os.path.splitext(path)[1].lower()
            mime = "image/png"
            if ext in (".jpg", ".jpeg"):
                mime = "image/jpeg"
            elif ext == ".webp":
                mime = "image/webp"

            with open(path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
            return f"data:{mime};base64,{b64}"

        # Otherwise treat as raw base64 and assume png
        b64 = str(image or "").strip()
        return f"data:image/png;base64,{b64}"

    # ----------------------------
    # Model management
    # ----------------------------

    def list_models(self) -> List[Dict[str, Any]]:
        """
        Return list of available models as OpenAI-like entries (each has 'id').
        Tries native first, then /v1/models fallback.
        """
        if not self.enabled:
            return []

        try:
            native = self._request("GET", "/api/v1/models", token_type="admin", timeout=30).json()
            models = native.get("data") or native.get("models") or []
            out: List[Dict[str, Any]] = []
            for m in models:
                if not isinstance(m, dict):
                    continue
                key = m.get("key") or m.get("id") or m.get("name")
                if not key:
                    continue
                out.append({"id": key, **m})
            if out:
                return out
        except Exception as e:
            logger.warning(f"[LMStudio] Native model list failed: {e}")

        try:
            data = self._request("GET", "/v1/models", token_type="admin", timeout=30).json()
            return data.get("data", []) or []
        except Exception as e:
            logger.warning(f"[LMStudio] Failed to list models: {e}")
            return []

    def _get_loaded_instance(self) -> Optional[Tuple[str, str]]:
        """
        Returns (model_key, instance_id) for the first loaded instance found, or None.
        """
        try:
            native = self._request("GET", "/api/v1/models", token_type="admin", timeout=30).json()
            models = native.get("data") or native.get("models") or []
            for m in models:
                if not isinstance(m, dict):
                    continue
                key = m.get("key") or m.get("id") or m.get("name")
                loaded = m.get("loaded_instances") or []
                if loaded:
                    inst = loaded[0] if isinstance(loaded[0], dict) else {}
                    inst_id = inst.get("id") or inst.get("instance_id") or key
                    if key and inst_id:
                        return key, inst_id
        except Exception:
            pass
        return None

    def load_model(self, model_name: str) -> Dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("LM Studio integration is disabled")

        logger.info(f"[LMStudio] Loading model: {model_name}")
        payload = {"model": model_name}
        return self._request(
            "POST",
            "/api/v1/models/load",
            token_type="admin",
            json_body=payload,
            timeout=120,
        ).json()

    def unload_model(self, instance_id: Optional[str] = None) -> Dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("LM Studio integration is disabled")

        if not instance_id:
            loaded = self._get_loaded_instance()
            if not loaded:
                return {"unloaded": False, "reason": "no model loaded"}
            _, instance_id = loaded

        logger.info(f"[LMStudio] Unloading model instance: {instance_id}")
        payload = {"instance_id": instance_id}
        return self._request(
            "POST",
            "/api/v1/models/unload",
            token_type="admin",
            json_body=payload,
            timeout=60,
        ).json()

    # ----------------------------
    # Download management
    # ----------------------------

    def download_model(
        self,
        repo: str,
        file: str,
        on_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("LM Studio integration is disabled")

        model_ref = (repo or "").strip()
        if "://" not in model_ref and "/" in model_ref:
            model_ref = f"https://huggingface.co/{model_ref}"

        quant_hint = self._extract_quantization_hint(file)

        logger.info(f"[LMStudio] Downloading model: {model_ref}")
        job_id = self._start_download_job(model_ref, quant_hint=quant_hint)

        if on_progress:
            while True:
                status = self.get_download_status(job_id)
                on_progress(status)
                st = (status.get("status") or "").lower()
                if st in ("complete", "completed", "error", "failed", "canceled", "cancelled"):
                    break
                time.sleep(1)

        return {"job_id": job_id, "download_id": job_id}

    def _start_download_job(self, model_ref: str, quant_hint: Optional[str]) -> str:
        payload = {"model": model_ref}
        if quant_hint:
            payload["quantization"] = quant_hint

        try:
            resp = self._request(
                "POST",
                "/api/v1/models/download",
                token_type="admin",
                json_body=payload,
                timeout=60,
            ).json()
            job_id = resp.get("job_id") or resp.get("download_id")
            if not job_id:
                raise RuntimeError(f"Unexpected download response: {resp}")
            return job_id
        except requests.HTTPError:
            if quant_hint:
                logger.warning("[LMStudio] Download with quantization hint failed; retrying without quantization.")
                resp = self._request(
                    "POST",
                    "/api/v1/models/download",
                    token_type="admin",
                    json_body={"model": model_ref},
                    timeout=60,
                ).json()
                job_id = resp.get("job_id") or resp.get("download_id")
                if not job_id:
                    raise RuntimeError(f"Unexpected download response: {resp}")
                return job_id
            raise

    def get_download_status(self, download_id: str) -> Dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("LM Studio integration is disabled")

        job_id = str(download_id).strip()
        return self._request(
            "GET",
            f"/api/v1/models/download/status/{job_id}",
            token_type="admin",
            timeout=30,
        ).json()

    # ----------------------------
    # Status helpers
    # ----------------------------

    def get_status(self) -> Dict[str, Any]:
        if not self.enabled:
            return {"loaded": False, "model": None, "connected": False}

        connected = self._is_server_reachable()
        if not connected:
            return {"loaded": False, "model": None, "connected": False}

        loaded = self._get_loaded_instance()
        
        # Get GPU/VRAM information
        try:
            from src.utils.hardware_utils import get_gpu_info
            gpu_info = get_gpu_info()
            vram_total_mb = gpu_info.get('vram_total_mb', 0)
            vram_used_mb = gpu_info.get('vram_used_mb', 0)
            vram_free_mb = gpu_info.get('vram_free_mb', 0)
        except Exception as e:
            logger.debug(f"[LMStudio] Failed to get GPU info: {e}")
            vram_total_mb = 0
            vram_used_mb = 0
            vram_free_mb = 0
        
        if not loaded:
            return {
                "loaded": False,
                "model": None,
                "connected": True,
                "vram_total_mb": vram_total_mb,
                "vram_mb": vram_used_mb,
                "vram_free_mb": vram_free_mb
            }

        model_key, instance_id = loaded
        return {
            "loaded": True,
            "model": model_key,
            "instance_id": instance_id,
            "connected": True,
            "vram_total_mb": vram_total_mb,
            "vram_mb": vram_used_mb,
            "vram_free_mb": vram_free_mb
        }

    def is_model_downloaded(self, model_name: str) -> bool:
        want = (model_name or "").strip()
        if not want:
            return False
        return any((m.get("id") or "").strip() == want for m in self.list_models())

    # ----------------------------
    # Helper: quant hint
    # ----------------------------

    def _extract_quantization_hint(self, file_name: str) -> Optional[str]:
        if not file_name:
            return None
        base = os.path.basename(file_name)
        lowered = base.lower()
        stem = base[:-5] if lowered.endswith(".gguf") else base

        for sep in (".Q", "-Q"):
            idx = stem.find(sep)
            if idx != -1:
                return stem[idx + 1:].strip()
        return None
