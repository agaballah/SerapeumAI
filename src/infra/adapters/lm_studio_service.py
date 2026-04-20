# -*- coding: utf-8 -*-
"""
lm_studio_service.py â€” LM Studio v1 REST + OpenAI-compat integration (headless-capable)
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

from src.infra.telemetry.metrics_collector import MetricsCollector
from src.infra.telemetry.llm_logger import get_llm_logger

logger = logging.getLogger(__name__)


class LMStudioRuntimeContractError(RuntimeError):
    """Raised when the connected LM Studio server mode is not supported for the requested operation."""


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

    def __init__(self, config, db=None):
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
        self._runtime_contract: Optional[Dict[str, Any]] = None

        # Telemetry
        self.db = db
        self.metrics = MetricsCollector(db=db)
        self.llm_logger = get_llm_logger()

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
                encoding="utf-8",
                errors="replace",
                timeout=timeout_s,
                check=False
            )
            return res.returncode, (res.stdout + res.stderr).strip()
        except subprocess.TimeoutExpired:
            return -1, "Command timed out"
        except Exception as e:
            return -1, f"Execution error: {e}"

    def _find_lms_cli(self) -> Optional[str]:
        """Locate the lms CLI executable without installing anything implicitly."""
        if self.lms_path:
            if os.path.exists(self.lms_path):
                return self.lms_path
            logger.warning(f"[LMStudio] lms_path configured but not found: {self.lms_path}")

        exe = "lms.exe" if os.name == "nt" else "lms"
        found = shutil.which(exe) or shutil.which("lms")
        if found:
            return found

        if os.name == "nt":
            local_app = os.environ.get("LOCALAPPDATA", "")
            program_files = os.environ.get("ProgramFiles", "")
            program_files_x86 = os.environ.get("ProgramFiles(x86)", "")
            candidates = [
                os.path.join(local_app, "Programs", "LM Studio", "lms.exe"),
                os.path.join(local_app, "Programs", "LM Studio", "resources", "bin", "lms.exe"),
                os.path.join(program_files, "LM Studio", "lms.exe"),
                os.path.join(program_files_x86, "LM Studio", "lms.exe"),
            ]
            for candidate in candidates:
                if candidate and os.path.exists(candidate):
                    return candidate

        logger.warning("[LMStudio] `lms` CLI is not available. Runtime setup requires explicit user-approved installation.")
        return None

    def _auto_install_lms_cli(self) -> Optional[str]:
        """
        Attempt to install the LM Studio CLI using npm.
        Returns the path to the installed lms binary, or None if it failed.
        """
        npm = shutil.which("npm")
        if not npm:
            logger.error(
                "[LMStudio] npm not found â€” cannot auto-install `lms`. "
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
                "[LMStudio] Server not reachable and the `lms` CLI is not available. "
                "Run the in-app Runtime Setup flow or install LM Studio / llmster with the official installer, then retry."
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

    def _endpoint_probe(self, path: str, token_type: str = "chat", timeout_s: float = 3.0) -> Dict[str, Any]:
        """Probe a GET endpoint without raising and record whether the route exists."""
        self._ensure_server_running()
        url = f"{self.url}{path}"
        try:
            resp = requests.get(url, headers=self._get_headers(token_type), timeout=timeout_s)
            status = int(resp.status_code)
            exists = status != 404 and status < 500
            payload = None
            try:
                payload = resp.json()
            except Exception:
                payload = None
            return {
                "reachable": True,
                "status_code": status,
                "exists": exists,
                "payload": payload,
            }
        except requests.exceptions.RequestException:
            return {
                "reachable": False,
                "status_code": None,
                "exists": False,
                "payload": None,
            }

    def _action_probe(
        self,
        method: str,
        path: str,
        *,
        token_type: str = "chat",
        json_body: Optional[Dict[str, Any]] = None,
        timeout_s: float = 3.0,
    ) -> Dict[str, Any]:
        """Probe non-GET routes and treat any non-404 client error as route existence."""
        self._ensure_server_running()
        url = f"{self.url}{path}"
        try:
            resp = requests.request(
                method=method,
                url=url,
                headers=self._get_headers(token_type),
                json=json_body,
                timeout=timeout_s,
            )
            status = int(resp.status_code)
            exists = status != 404 and status < 500
            payload = None
            try:
                payload = resp.json()
            except Exception:
                payload = None
            return {
                "reachable": True,
                "status_code": status,
                "exists": exists,
                "payload": payload,
            }
        except requests.exceptions.RequestException:
            return {
                "reachable": False,
                "status_code": None,
                "exists": False,
                "payload": None,
            }

    def _extract_model_ids(self, payload: Any) -> List[str]:
        out: List[str] = []
        rows = []
        if isinstance(payload, dict):
            rows = payload.get("data") or payload.get("models") or []
        if not isinstance(rows, list):
            return out
        for row in rows:
            if not isinstance(row, dict):
                continue
            model_id = row.get("id") or row.get("key") or row.get("name")
            if isinstance(model_id, str) and model_id.strip():
                out.append(model_id.strip())
        return out

    def _refresh_runtime_contract(self, force: bool = False) -> Dict[str, Any]:
        if self._runtime_contract is not None and not force:
            return dict(self._runtime_contract)

        native_probe = self._endpoint_probe("/api/v1/models", token_type="admin")
        native_chat_probe = self._action_probe("GET", "/api/v1/chat", token_type="chat")
        native_load_probe = self._action_probe("GET", "/api/v1/models/load", token_type="admin")
        openai_probe = self._endpoint_probe("/v1/models", token_type="chat")

        native_models = self._extract_model_ids(native_probe.get("payload"))
        openai_models = self._extract_model_ids(openai_probe.get("payload"))

        native_rest = bool(native_probe.get("exists") or native_chat_probe.get("exists") or native_load_probe.get("exists"))
        native_chat = bool(native_chat_probe.get("exists"))
        native_model_management = bool(native_load_probe.get("exists"))
        openai_compat = bool(openai_probe.get("exists"))
        connected = bool(
            native_probe.get("reachable")
            or native_chat_probe.get("reachable")
            or native_load_probe.get("reachable")
            or openai_probe.get("reachable")
        )

        if native_chat and native_model_management:
            mode = "native_rest"
            message = "LM Studio native REST chat and model management are available."
        elif native_chat:
            mode = "native_chat_only"
            message = (
                "LM Studio native chat is available, but native model load/unload endpoints are unavailable. "
                "SerapeumAI will use the active model without calling /api/v1/models/load."
            )
        elif openai_compat:
            mode = "openai_compat_only"
            message = (
                "LM Studio is reachable in OpenAI-compatible mode only. "
                "SerapeumAI can chat only with already available models in this mode; "
                "native /api/v1 model load/unload endpoints are unavailable."
            )
        elif connected:
            mode = "unsupported"
            message = (
                "LM Studio is reachable, but no supported chat runtime was detected. "
                "Use LM Studio native REST chat (/api/v1/chat) or the OpenAI-compatible local server with /v1/models enabled."
            )
        else:
            mode = "unreachable"
            message = f"LM Studio server is not reachable at {self.url}."

        contract = {
            "connected": connected,
            "native_rest": native_rest,
            "native_chat": native_chat,
            "native_model_management": native_model_management,
            "openai_compat": openai_compat,
            "mode": mode,
            "message": message,
            "native_models": native_models,
            "openai_models": openai_models,
        }
        self._runtime_contract = dict(contract)
        return dict(contract)

    def get_runtime_contract(self, force_refresh: bool = False) -> Dict[str, Any]:
        return self._refresh_runtime_contract(force=force_refresh)

    def _require_runtime(self, *, require_model_management: bool = False) -> Dict[str, Any]:
        contract = self._refresh_runtime_contract()
        if not contract.get("connected"):
            raise LMStudioRuntimeContractError(contract.get("message") or "LM Studio server is not reachable.")
        if not contract.get("native_chat") and not contract.get("openai_compat"):
            raise LMStudioRuntimeContractError(contract.get("message") or "Unsupported LM Studio server mode.")
        if require_model_management and not contract.get("native_model_management"):
            raise LMStudioRuntimeContractError(
                "Current LM Studio server does not expose native model load/unload endpoints. "
                "SerapeumAI cannot auto-load analysis models in this mode. "
                "Load the required model in LM Studio first or use a native REST runtime that supports /api/v1/models/load."
            )
        return contract

    def _resolve_chat_target_model(self, model_name: Optional[str]) -> str:
        want = (model_name or "").strip()
        contract = self._refresh_runtime_contract()

        if want and want not in ("local-model", "lm-studio", "auto"):
            if contract.get("openai_compat") and not contract.get("native_rest"):
                available = contract.get("openai_models") or []
                if available:
                    want_aliases = set(self._model_aliases(want))
                    for candidate in available:
                        candidate_text = str(candidate or "").strip()
                        if want_aliases & set(self._model_aliases(candidate_text)):
                            return candidate_text
                    raise LMStudioRuntimeContractError(
                        f"LM Studio is running in OpenAI-compatible mode only, and model '{want}' is not available via /v1/models. "
                        f"Available models: {', '.join(available)}"
                    )
            return want

        loaded = self._get_loaded_instance()
        if loaded:
            model_key, _instance_id = loaded
            if model_key:
                return model_key

        available_openai = contract.get("openai_models") or []
        if available_openai:
            return str(available_openai[0])

        status = self.get_status()
        resolved = (status.get("model") or "").strip() if isinstance(status, dict) else ""
        if resolved:
            return resolved

        if contract.get("openai_compat") and not contract.get("native_rest"):
            raise LMStudioRuntimeContractError(
                "LM Studio OpenAI-compatible server is reachable, but no model is exposed via /v1/models. "
                "Load a model in LM Studio or switch to native REST mode (/api/v1/*)."
            )

        return want or "local-model"

    def verify_chat_runtime(self, *, target_model: Optional[str] = None, require_stateful: bool = False) -> Dict[str, Any]:
        contract = self._require_runtime(require_model_management=False)
        if require_stateful and not contract.get("native_chat"):
            raise LMStudioRuntimeContractError(
                "This SerapeumAI workflow requires LM Studio native REST stateful chat (/api/v1/chat), "
                "but the current server does not expose that endpoint."
            )

        resolved_model = self._resolve_chat_target_model(target_model)
        if contract.get("openai_compat") and not contract.get("native_rest"):
            available = contract.get("openai_models") or []
            if available and resolved_model not in available:
                raise LMStudioRuntimeContractError(
                    f"LM Studio OpenAI-compatible mode cannot serve model '{resolved_model}'. "
                    f"Available models: {', '.join(available)}"
                )

        contract["resolved_model"] = resolved_model
        return contract

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

    def _normalize_openai_message_content(self, content: Any, *, text_only: bool = False) -> Any:
        if isinstance(content, str):
            return content

        if isinstance(content, list):
            text_parts: List[str] = []
            normalized_parts: List[Dict[str, Any]] = []
            for part in content:
                if isinstance(part, dict):
                    ptype = str(part.get("type") or "").strip().lower()
                    if ptype == "text":
                        text = str(part.get("text") or "")
                        text_parts.append(text)
                        if not text_only:
                            normalized_parts.append({"type": "text", "text": text})
                        continue
                    if ptype in {"image_url", "image"}:
                        url = ""
                        if ptype == "image_url":
                            url = str((part.get("image_url") or {}).get("url") or "")
                        else:
                            url = str(part.get("data_url") or part.get("url") or "")
                        if url:
                            if text_only:
                                text_parts.append("[image]")
                            else:
                                normalized_parts.append({"type": "image_url", "image_url": {"url": url}})
                        continue
                    fallback_text = str(part.get("content") or part.get("text") or "")
                    if fallback_text:
                        text_parts.append(fallback_text)
                        if not text_only:
                            normalized_parts.append({"type": "text", "text": fallback_text})
                    continue

                if part is None:
                    continue
                text = str(part)
                text_parts.append(text)
                if not text_only:
                    normalized_parts.append({"type": "text", "text": text})

            if text_only:
                return "\n".join(t for t in text_parts if t)
            return normalized_parts or "\n".join(t for t in text_parts if t)

        if content is None:
            return ""

        return str(content)

    def _normalize_openai_messages(self, messages: List[Dict[str, Any]], *, text_only: bool = False) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        for message in messages or []:
            role = str(message.get("role") or "user").strip().lower() or "user"
            normalized.append({
                "role": role,
                "content": self._normalize_openai_message_content(message.get("content"), text_only=text_only),
            })
        return normalized

    def _prepare_openai_chatcompletions_payload(self, payload: Dict[str, Any], *, text_only: bool = False) -> Dict[str, Any]:
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
        prepared: Dict[str, Any] = {}
        for key, value in (payload or {}).items():
            if key not in safe_keys:
                continue
            if value is None:
                continue
            if key == "messages":
                prepared[key] = self._normalize_openai_messages(value, text_only=text_only)
                continue
            if key in {"tools", "stop"} and not value:
                continue
            if key in {"response_format", "tool_choice"} and not value:
                continue
            if key == "model":
                prepared[key] = str(value).strip()
                continue
            if key in {"temperature", "top_p", "frequency_penalty", "presence_penalty"}:
                prepared[key] = float(value)
                continue
            if key == "max_tokens":
                prepared[key] = max(1, int(value))
                continue
            prepared[key] = value
        return prepared

    def _build_openai_retry_payload(self, payload: Dict[str, Any], resolved_model: str) -> Dict[str, Any]:
        retry_payload = {
            "model": resolved_model,
            "messages": payload.get("messages") or [],
            "stream": bool(payload.get("stream", False)),
            "max_tokens": int(payload.get("max_tokens") or 1024),
        }
        return self._prepare_openai_chatcompletions_payload(retry_payload, text_only=True)

    def _model_aliases(self, model_name: Optional[str]) -> List[str]:
        raw = str(model_name or "").strip()
        if not raw:
            return []
        lowered = raw.lower().replace("\\", "/")
        aliases = {lowered}
        aliases.add(lowered.split("/")[-1])
        aliases.add(lowered.split(":")[0])
        aliases.add(lowered.split("/")[-1].split(":")[0])
        return [a for a in aliases if a]

    def _resolve_openai_model_name(self, model_name: Optional[str]) -> str:
        """Resolve aliases to the exact model id exposed by /v1/models when available."""
        requested = str(model_name or "").strip()
        fallback = self._resolve_chat_target_model(requested)
        contract = self._refresh_runtime_contract()
        available = contract.get("openai_models") or []
        if not available:
            return fallback

        aliases = set(self._model_aliases(requested or fallback))
        if not aliases:
            return fallback

        for candidate in available:
            cand = str(candidate or "").strip()
            cand_aliases = set(self._model_aliases(cand))
            if aliases & cand_aliases:
                return cand

        return fallback


    def _openai_chat_to_normalized(self, payload: Dict[str, Any], model: str) -> Dict[str, Any]:
        result = dict(payload or {})
        result.setdefault("model", model)
        result.setdefault("object", "chat.completion")
        result.setdefault("created", int(time.time()))

        content = ""
        reasoning_content = ""
        choices = result.get("choices")
        if isinstance(choices, list) and choices:
            msg = choices[0].get("message", {})
            if isinstance(msg, dict):
                content = str(msg.get("content", "") or "")
                reasoning_content = str(msg.get("reasoning_content", "") or "")

        if content:
            result["content"] = content
        elif reasoning_content:
            result["content"] = reasoning_content
            result.setdefault("reasoning_content", reasoning_content)

        if not isinstance(result.get("usage"), dict):
            result["usage"] = {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            }

        return result

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
        requested_model = model or settings.get("model") or "local-model"
        start_time = time.time()

        contract = self.verify_chat_runtime(
            target_model=requested_model,
            require_stateful=bool(previous_response_id),
        )
        target_model = contract.get("resolved_model") or requested_model

        # Log Call
        call_id = self.llm_logger.log_call(
            task_type=profile,
            model=target_model,
            system_prompt=next((m.get("content") for m in messages if m.get("role") == "system"), "") or "",
            user_prompt=str([m.get("content") for m in messages if m.get("role") == "user"]),
            temperature=settings.get("temperature", 0.3),
            max_tokens=settings.get("max_tokens", 1024),
            context_length=0,
            metadata=overrides
        )

        if stream:
            payload = {
                "model": self._resolve_openai_model_name(target_model),
                "messages": messages,
                "stream": True,
                **settings,
            }
            openai_payload = self._prepare_openai_chatcompletions_payload(payload)
            if previous_response_id:
                logger.warning("[LMStudio] previous_response_id not supported for /v1/chat/completions streaming; ignored.")

            # Streaming telemetry is handled within the generator
            return self._chat_completions_stream(openai_payload, call_id, start_time, profile)

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

        result = None
        native_error = None

        if contract.get("native_chat"):
            try:
                native_resp = self._request(
                    "POST",
                    "/api/v1/chat",
                    token_type="chat",
                    json_body=native_payload,
                    timeout=180,
                ).json()

                result = self._native_chat_to_openai_chatcompletions(native_resp, model=target_model)
            except requests.exceptions.HTTPError as e:
                status_code = getattr(getattr(e, "response", None), "status_code", None)
                native_error = e
                if status_code == 404:
                    logger.warning("[LMStudio] Native /api/v1/chat is unavailable; retrying in OpenAI-compatible mode.")
                    contract = self._refresh_runtime_contract(force=True)
                elif status_code == 400 and not contract.get("openai_compat"):
                    raise LMStudioRuntimeContractError(
                        f"LM Studio native chat rejected the request for model '{target_model}'. "
                        "If this runtime does not support auto-loading, load the model in LM Studio first."
                    ) from e
                else:
                    logger.warning("[LMStudio] Native chat failed, trying OpenAI-compatible fallback: %s", e)
            except Exception as e:
                native_error = e
                logger.warning("[LMStudio] Native chat failed, trying OpenAI-compatible fallback: %s", e)

        if result is None:
            if not contract.get("openai_compat"):
                if native_error is not None:
                    raise native_error
                raise LMStudioRuntimeContractError(contract.get("message") or "No supported LM Studio chat endpoint is available.")

            payload = {
                "model": self._resolve_openai_model_name(target_model),
                "messages": messages,
                "stream": False,
                **settings,
            }
            openai_payload = self._prepare_openai_chatcompletions_payload(payload)
            try:
                resp = self._request(
                    "POST",
                    "/v1/chat/completions",
                    token_type="chat",
                    json_body=openai_payload,
                    timeout=180,
                ).json()
            except requests.exceptions.HTTPError as e:
                status_code = getattr(getattr(e, "response", None), "status_code", None)
                if status_code == 400:
                    retry_payload = self._build_openai_retry_payload(openai_payload, self._resolve_openai_model_name(target_model))
                    try:
                        logger.warning("[LMStudio] OpenAI-compatible chat request returned 400; retrying with normalized payload.")
                        resp = self._request(
                            "POST",
                            "/v1/chat/completions",
                            token_type="chat",
                            json_body=retry_payload,
                            timeout=180,
                        ).json()
                    except requests.exceptions.HTTPError as retry_error:
                        retry_status = getattr(getattr(retry_error, "response", None), "status_code", None)
                        if retry_status == 400:
                            raise LMStudioRuntimeContractError(
                                f"LM Studio rejected the OpenAI-compatible chat request for model '{retry_payload.get('model')}'. "
                                "Load the required model in LM Studio or switch to native REST mode (/api/v1/*)."
                            ) from retry_error
                        raise
                else:
                    raise

            result = self._openai_chat_to_normalized(resp, model=str((openai_payload or {}).get("model") or target_model))

        duration = time.time() - start_time
        usage = result.get("usage", {})
        self.llm_logger.log_response(
            call_id=call_id,
            response=result,
            duration_seconds=duration,
            success=True,
            tokens_used=usage
        )
        self.metrics.record_latency(f"llm_{profile}", duration)
        if usage:
            self.metrics.record_metric("llm_tokens_total", usage.get("total_tokens", 0))

        return result

    def _chat_completions_stream(
        self,
        openai_payload: Dict[str, Any],
        call_id: str,
        start_time: float,
        profile: str
    ) -> Iterator[Dict[str, Any]]:
        resp = self._request(
            "POST",
            "/v1/chat/completions",
            token_type="chat",
            json_body=openai_payload,
            stream=True,
            timeout=180,
        )

        full_content = []
        try:
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
                    chunk = json.loads(s)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    if "content" in delta:
                        full_content.append(delta["content"])
                    yield chunk
                except json.JSONDecodeError:
                    continue

            # Log successful stream completion
            duration = time.time() - start_time
            self.llm_logger.log_response(
                call_id=call_id,
                response={"content": "".join(full_content)},
                duration_seconds=duration,
                success=True
            )
            self.metrics.record_latency(f"llm_stream_{profile}", duration)

        except Exception as e:
            duration = time.time() - start_time
            self.llm_logger.log_response(
                call_id=call_id,
                response=None,
                duration_seconds=duration,
                success=False,
                error=str(e)
            )
            raise

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
        contract = self.verify_chat_runtime(
            target_model=model or settings.get("model") or "local-model",
            require_stateful=bool(previous_response_id),
        )
        target_model = contract.get("resolved_model") or model or settings.get("model") or "local-model"

        data_url = self._to_data_url(image)
        native_settings = self._native_settings_from_profile(settings)

        if not contract.get("native_chat"):
            raise LMStudioRuntimeContractError(
                "Vision analysis currently requires LM Studio native REST chat (/api/v1/chat). "
                "The connected server does not expose that endpoint."
            )

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
        """Return list of available models as OpenAI-like entries (each has 'id')."""
        if not self.enabled:
            return []

        contract = self._refresh_runtime_contract()
        if contract.get("native_rest"):
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

        if contract.get("openai_compat"):
            try:
                data = self._request("GET", "/v1/models", token_type="chat", timeout=30).json()
                return data.get("data", []) or []
            except Exception as e:
                logger.warning(f"[LMStudio] Failed to list OpenAI-compatible models: {e}")

        return []

    def _get_loaded_instance(self) -> Optional[Tuple[str, str]]:
        """Returns (model_key, instance_id) for the first loaded instance found, or None."""
        contract = self._refresh_runtime_contract()
        if contract.get("native_rest"):
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
        elif contract.get("openai_compat"):
            models = self.list_models()
            if models:
                model_id = models[0].get("id")
                if model_id:
                    return str(model_id), str(model_id)
        return None

    def load_model(self, model_name: str) -> Dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("LM Studio integration is disabled")

        self._require_runtime(require_model_management=True)

        # â”€â”€ VRAM Governance â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        from src.utils.hardware_utils import reserve_vram, check_resource_availability
        lowered = model_name.lower()
        is_vision = "vl" in lowered or "vision" in lowered
        tier = "vision" if is_vision else "analysis"

        # Estimate reservation (4GB for vision, 2GB for others)
        reserve_mb = 4096 if is_vision else 2048

        if not check_resource_availability(tier):
            logger.error(f"[LMStudio] Insufficient VRAM to load {model_name} (tier: {tier})")
            return {"error": "insufficient_vram", "tier": tier}

        if not reserve_vram(reserve_mb):
            logger.error(f"[LMStudio] VRAM reservation failed for {model_name} ({reserve_mb}MB)")
            return {"error": "vram_reservation_failed", "mb": reserve_mb}

        logger.info(f"[LMStudio] Loading model: {model_name} (reserved {reserve_mb}MB)")
        payload = {"model": model_name}
        try:
            resp = self._request(
                "POST",
                "/api/v1/models/load",
                token_type="admin",
                json_body=payload,
                timeout=120,
            ).json()
            self._refresh_runtime_contract(force=True)
            return resp
        except Exception as e:
            from src.utils.hardware_utils import release_vram
            release_vram(reserve_mb) # Cleanup reservation on failure
            raise e

    def unload_model(self, instance_id: Optional[str] = None) -> Dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("LM Studio integration is disabled")

        self._require_runtime(require_model_management=True)

        if not instance_id:
            loaded = self._get_loaded_instance()
            if not loaded:
                return {"unloaded": False, "reason": "no model loaded"}
            _, instance_id = loaded

        logger.info(f"[LMStudio] Unloading model instance: {instance_id}")
        payload = {"instance_id": instance_id}
        resp = self._request(
            "POST",
            "/api/v1/models/unload",
            token_type="admin",
            json_body=payload,
            timeout=60,
        ).json()

        # Release ALL reserved VRAM from the orchestration layer upon explicit unload
        from src.utils.hardware_utils import release_vram
        # We don't know the exact MB, so we release the maximum likely reserved (4GB)
        # hardware_utils.release_vram handles the floor at 0.
        release_vram(4096)

        return resp

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

        contract = self._refresh_runtime_contract()
        connected = bool(contract.get("connected"))
        if not connected:
            return {"loaded": False, "model": None, "connected": False, "mode": contract.get("mode")}

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
                "vram_free_mb": vram_free_mb,
                "mode": contract.get("mode")
            }

        model_key, instance_id = loaded
        return {
            "loaded": True,
            "model": model_key,
            "instance_id": instance_id,
            "connected": True,
            "vram_total_mb": vram_total_mb,
            "vram_mb": vram_used_mb,
            "vram_free_mb": vram_free_mb,
            "mode": contract.get("mode")
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
