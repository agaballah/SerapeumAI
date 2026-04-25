from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import time
from typing import Any, Dict, List, Optional, Sequence, Set

import requests

from src.infra.adapters.lm_studio_service import LMStudioRuntimeContractError, LMStudioService
from src.infra.adapters.vector_store import EMBEDDING_MODEL

logger = logging.getLogger(__name__)


STATUS_LMSTUDIO_NOT_INSTALLED = "LMSTUDIO_NOT_INSTALLED"
STATUS_CLI_NOT_AVAILABLE = "CLI_NOT_AVAILABLE"
STATUS_SERVER_NOT_RUNNING = "SERVER_NOT_RUNNING"
STATUS_CHAT_MODEL_MISSING = "CHAT_MODEL_MISSING"
STATUS_EMBEDDING_RUNTIME_NOT_READY = "EMBEDDING_RUNTIME_NOT_READY"
STATUS_EMBEDDING_MODEL_MISSING = STATUS_EMBEDDING_RUNTIME_NOT_READY
STATUS_MODEL_NOT_LOADED = "MODEL_NOT_LOADED"
STATUS_READY = "READY"
STATUS_UNSUPPORTED_RUNTIME = "UNSUPPORTED_RUNTIME"
STATUS_RUNTIME_UNREACHABLE = "RUNTIME_UNREACHABLE"


ROLE_IDENTIFIERS = {
    "analysis": "serapeum-analysis",
    "chat": "serapeum-chat",
}

PUBLISH_GENERATIVE_MODEL = "qwen2.5-coder-7b-instruct"
PUBLISH_GENERATIVE_MODEL_ALIASES: List[str] = [
    "qwen2.5-coder-7b-instruct",
    "qwen/qwen2.5-coder-7b-instruct",
    "qwen/qwen2.5-coder-7b-instruct@q4_k_m",
    "lmstudio-community/qwen2.5-coder-7b-instruct-gguf",
    "qwen/qwen2.5-coder-7b-instruct-gguf",
    "qwen/qwen2.5-coder-7b-instruct-gguf/qwen2.5-coder-7b-instruct-q4_k_m.gguf",
    "qwen2.5-coder-7b-instruct-q4_k_m.gguf",
]

DEFAULT_MODEL_ALIASES: Dict[str, List[str]] = {
    "chat": list(PUBLISH_GENERATIVE_MODEL_ALIASES),
    "analysis": list(PUBLISH_GENERATIVE_MODEL_ALIASES),
}


class LocalRuntimeSetupService:
    """Guidance, verification, and app-owned LM Studio session management."""

    DEFAULT_CHAT_MODEL = PUBLISH_GENERATIVE_MODEL
    DEFAULT_ANALYSIS_MODEL = PUBLISH_GENERATIVE_MODEL
    WINDOWS_BOOTSTRAP_COMMAND = r'cmd /c %USERPROFILE%/.lmstudio/bin/lms.exe bootstrap'

    def __init__(self, config):
        self.config = config
        self.url = str(config.get("lm_studio.url", "http://127.0.0.1:1234")).rstrip("/")
        self._embedding_prepared = False
        self._server_started_by_app = False
        self._loaded_models_by_app: Set[str] = set()
        self._role_to_loaded_identifier: Dict[str, str] = {}

    # ------------------------------------------------------------------
    # Discovery / helpers
    # ------------------------------------------------------------------
    def get_required_models(self) -> Dict[str, str]:
        return {
            "chat": self.DEFAULT_CHAT_MODEL,
            "analysis": self.DEFAULT_ANALYSIS_MODEL,
            "embedding": EMBEDDING_MODEL,
        }

    def _find_lmstudio_app(self) -> Optional[str]:
        configured = str(self.config.get("lm_studio.desktop_app_path", "") or "").strip()
        candidates: List[str] = []
        if configured:
            candidates.append(configured)

        if os.name == "nt":
            local_app = os.environ.get("LOCALAPPDATA", "")
            program_files = os.environ.get("ProgramFiles", "")
            program_files_x86 = os.environ.get("ProgramFiles(x86)", "")
            candidates.extend([
                os.path.join(local_app, "Programs", "LM Studio", "LM Studio.exe"),
                os.path.join(program_files, "LM Studio", "LM Studio.exe"),
                os.path.join(program_files_x86, "LM Studio", "LM Studio.exe"),
            ])

        for path in candidates:
            if path and os.path.exists(path):
                return path
        return None

    def _find_lms_cli(self) -> Optional[str]:
        configured = str(self.config.get("lm_studio.lms_path", "") or "").strip()
        if configured and os.path.exists(configured):
            return configured

        exe_name = "lms.exe" if os.name == "nt" else "lms"
        found = shutil.which(exe_name) or shutil.which("lms")
        if found:
            return found

        home = os.path.expanduser("~")
        candidates: List[str] = []
        if os.name == "nt" and home:
            candidates.append(os.path.join(home, ".lmstudio", "bin", "lms.exe"))

        app_path = self._find_lmstudio_app()
        if app_path:
            app_dir = os.path.dirname(app_path)
            candidates.extend([
                os.path.join(app_dir, "lms.exe"),
                os.path.join(app_dir, "resources", "bin", "lms.exe"),
                os.path.join(app_dir, "resources", "app.asar.unpacked", "bin", "lms.exe"),
            ])

        for path in candidates:
            if path and os.path.exists(path):
                return path
        return None

    def _subprocess_window_options(self) -> Dict[str, Any]:
        """
        Return Windows-safe subprocess options that prevent LM Studio helper CLI
        calls from flashing transient console windows in packaged/windowed builds.
        """
        if os.name != "nt":
            return {}

        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE

        return {
            "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0),
            "startupinfo": startupinfo,
        }

    def _run_cli(self, args: List[str], timeout_s: int = 180) -> subprocess.CompletedProcess:
        cli_path = self._find_lms_cli()
        if not cli_path:
            raise RuntimeError("The lms command-line interface is not available.")
        return subprocess.run(
            [cli_path, *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_s,
            check=False,
            **self._subprocess_window_options(),
        )

    def _normalize_token(self, value: Optional[str]) -> str:
        text = str(value or "").strip().lower().replace("\\", "/")
        if not text:
            return ""
        return " ".join(text.split())

    def _dedupe_keep_order(self, items: Sequence[str]) -> List[str]:
        out: List[str] = []
        seen: Set[str] = set()
        for item in items:
            text = str(item or "").strip()
            if not text:
                continue
            key = self._normalize_token(text)
            if key in seen:
                continue
            seen.add(key)
            out.append(text)
        return out

    def _parse_json_output(self, stdout: str) -> Any:
        text = str(stdout or "").strip()
        if not text:
            return []
        try:
            return json.loads(text)
        except Exception:
            logger.debug("LM Studio CLI output was not valid JSON: %s", text[:500], exc_info=True)
            return []

    def _normalize_model_rows(self, payload: Any) -> List[Dict[str, Any]]:
        rows: Any = payload
        if isinstance(payload, dict):
            rows = payload.get("data") or payload.get("models") or []
        if not isinstance(rows, list):
            return []

        normalized: List[Dict[str, Any]] = []
        seen: Set[str] = set()
        for row in rows:
            if not isinstance(row, dict):
                continue
            model_key = str(
                row.get("modelKey")
                or row.get("key")
                or row.get("indexedModelIdentifier")
                or row.get("path")
                or row.get("id")
                or row.get("name")
                or ""
            ).strip()
            identifier = str(
                row.get("identifier")
                or row.get("instance_id")
                or row.get("instanceId")
                or row.get("id")
                or model_key
            ).strip()
            display_name = str(
                row.get("displayName")
                or row.get("display_name")
                or row.get("name")
                or model_key
            ).strip()
            model_type = str(row.get("type") or ("embedding" if "embed" in model_key.lower() else "llm")).strip().lower()
            item = {
                "identifier": identifier,
                "model_key": model_key,
                "display_name": display_name,
                "type": model_type,
                "publisher": str(row.get("publisher") or "").strip(),
                "path": str(row.get("path") or "").strip(),
                "architecture": str(row.get("architecture") or "").strip(),
                "params": str(row.get("paramsString") or row.get("params") or "").strip(),
                "quantization": str((row.get("quantization") or {}).get("name") or row.get("quantization") or "").strip(),
                "status": str(row.get("status") or "").strip(),
            }
            key = self._normalize_token(item["identifier"] or item["model_key"])
            if key in seen:
                continue
            seen.add(key)
            normalized.append(item)
        return normalized

    def _list_local_models(self, kind: str = "llm") -> List[Dict[str, Any]]:
        args = ["ls", "--json"]
        if kind == "llm":
            args.append("--llm")
        elif kind == "embedding":
            args.append("--embedding")
        try:
            result = self._run_cli(args, timeout_s=120)
        except Exception:
            logger.debug("Local model listing failed.", exc_info=True)
            return []
        if result.returncode != 0:
            logger.debug("Local model listing returned non-zero exit code: %s", result.returncode)
            return []
        return self._normalize_model_rows(self._parse_json_output(result.stdout))

    def _list_loaded_models(self) -> List[Dict[str, Any]]:
        try:
            result = self._run_cli(["ps", "--json"], timeout_s=120)
        except Exception:
            logger.debug("Loaded model listing failed.", exc_info=True)
            return []
        if result.returncode != 0:
            return []
        return self._normalize_model_rows(self._parse_json_output(result.stdout))

    def _server_running(self, timeout_s: float = 2.0) -> bool:
        cli_path = self._find_lms_cli()
        if cli_path:
            try:
                result = self._run_cli(["server", "status", "--json", "--quiet"], timeout_s=15)
                if result.returncode == 0:
                    payload = self._parse_json_output(result.stdout)
                    if isinstance(payload, dict):
                        return bool(payload.get("running"))
            except Exception:
                logger.debug("LM Studio CLI server status check failed.", exc_info=True)

        for candidate in (self.url, f"{self.url}/v1/models", f"{self.url}/api/v1/models"):
            try:
                resp = requests.get(candidate, timeout=timeout_s)
                if resp.status_code < 500:
                    return True
            except Exception:
                continue
        return False

    def _build_lm_client(self) -> LMStudioService:
        return LMStudioService(self.config)

    def _emit(self, callback, status: str, message: str, **extra) -> Dict[str, Any]:
        payload = {"status": status, "message": message, **extra}
        phase = str(payload.get("phase") or "").strip()
        active_model = str(payload.get("active_model") or "").strip()
        log_parts = [f"status={status}"]
        if phase:
            log_parts.append(f"phase={phase}")
        if active_model:
            log_parts.append(f"model={active_model}")
        log_parts.append(f"message={message}")
        logger.info("[RuntimeSetup] %s", " | ".join(log_parts))
        if callback:
            try:
                callback(payload)
            except Exception:
                logger.debug("Runtime status callback failed.", exc_info=True)
        return payload

    def _match_downloaded_model(self, wanted: str, downloaded: Sequence[Dict[str, Any]]) -> Optional[str]:
        wanted_norm = self._normalize_token(wanted)
        if not wanted_norm:
            return None
        for row in downloaded:
            candidates = [
                row.get("model_key"),
                row.get("display_name"),
                row.get("path"),
                row.get("identifier"),
            ]
            normalized = {self._normalize_token(value) for value in candidates if str(value or "").strip()}
            if wanted_norm in normalized:
                return str(row.get("model_key") or "").strip()
        return None

    def _suggest_default_model(self, role: str, downloaded: Sequence[Dict[str, Any]]) -> Optional[str]:
        aliases = DEFAULT_MODEL_ALIASES.get(role, [])
        for alias in aliases:
            match = self._match_downloaded_model(alias, downloaded)
            if match:
                return match
        if len(downloaded) == 1:
            return str(downloaded[0].get("model_key") or "").strip() or None
        return None

    def _resolve_publish_generative_model(self, downloaded: Sequence[Dict[str, Any]]) -> Optional[str]:
        for alias in PUBLISH_GENERATIVE_MODEL_ALIASES:
            match = self._match_downloaded_model(alias, downloaded)
            if match:
                return match
        return None

    def _resolve_selected_model(self, configured_value: str, role: str, downloaded: Sequence[Dict[str, Any]]) -> Optional[str]:
        configured = str(configured_value or "").strip()
        if configured and configured.lower() != "auto":
            match = self._match_downloaded_model(configured, downloaded)
            if match:
                return match
        return self._suggest_default_model(role, downloaded)

    def _selected_models(self, downloaded_llms: Sequence[Dict[str, Any]]) -> Dict[str, Optional[str]]:
        selected = self._resolve_publish_generative_model(downloaded_llms)
        return {
            "chat": selected,
            "analysis": selected,
        }

    def _loaded_roles(self, selected_models: Dict[str, Optional[str]], loaded_models: Sequence[Dict[str, Any]]) -> Dict[str, bool]:
        loaded_keys = {self._normalize_token(row.get("model_key")) for row in loaded_models if str(row.get("model_key") or "").strip()}
        loaded_ids = {self._normalize_token(row.get("identifier")) for row in loaded_models if str(row.get("identifier") or "").strip()}
        result: Dict[str, bool] = {}
        for role, selected in selected_models.items():
            selected_norm = self._normalize_token(selected)
            role_id_norm = self._normalize_token(ROLE_IDENTIFIERS.get(role))
            result[role] = bool(selected_norm and (selected_norm in loaded_keys or role_id_norm in loaded_ids))
        return result

    def _inventory(self, app_path: Optional[str], cli_path: Optional[str]) -> Dict[str, Any]:
        downloaded_llms = self._list_local_models("llm") if cli_path else []
        loaded_models = self._list_loaded_models() if cli_path else []
        selected_models = self._selected_models(downloaded_llms)
        loaded_roles = self._loaded_roles(selected_models, loaded_models)
        return {
            "lmstudio_installed": bool(app_path or cli_path),
            "cli_available": bool(cli_path),
            "app_path": app_path,
            "cli_path": cli_path,
            "server_running": self._server_running() if cli_path else False,
            "downloaded_llms": downloaded_llms,
            "loaded_models": loaded_models,
            "selected_models": selected_models,
            "loaded_roles": loaded_roles,
        }

    def _compatible_model_lines(self, downloaded_llms: Sequence[Dict[str, Any]]) -> str:
        if not downloaded_llms:
            return "No downloaded LLM models were detected."
        lines = []
        for row in downloaded_llms[:20]:
            model_key = str(row.get("model_key") or "").strip()
            display_name = str(row.get("display_name") or model_key).strip()
            if display_name and display_name != model_key:
                lines.append(f"- {display_name} ({model_key})")
            else:
                lines.append(f"- {model_key}")
        return "\n".join(lines)

    def _guidance_text(self, state: Dict[str, Any]) -> str:
        inventory = state.get("inventory") or {}
        selected = inventory.get("selected_models") or {}
        lines = [
            "SerapeumAI runtime contract",
            "- User installs LM Studio once.",
            "- User downloads models in LM Studio.",
            "- SerapeumAI verifies runtime state and manages server and model load/unload during the app session.",
            "",
            f"Current state: {state.get('status')}",
            str(state.get("message") or "").strip(),
            "",
            "Supported LM Studio terminal examples",
            "- lms ls --json",
            "- lms ps --json",
            "- lms server start",
            "- lms load <model_key>",
            "- lms unload <identifier>",
            "",
            "Detected downloaded LLM models",
            self._compatible_model_lines(inventory.get("downloaded_llms") or []),
            "",
            f"Selected chat model: {selected.get('chat') or 'Not selected'}",
            f"Selected analysis model: {selected.get('analysis') or 'Not selected'}",
        ]
        if state.get("status") == STATUS_CLI_NOT_AVAILABLE and os.name == "nt":
            lines.extend([
                "",
                "Windows CLI bootstrap example",
                f"- {self.WINDOWS_BOOTSTRAP_COMMAND}",
            ])
        return "\n".join(lines).strip()

    # ------------------------------------------------------------------
    # Runtime state detection
    # ------------------------------------------------------------------
    def detect_state(self) -> Dict[str, Any]:
        required = self.get_required_models()
        app_path = self._find_lmstudio_app()
        cli_path = self._find_lms_cli()
        inventory = self._inventory(app_path, cli_path)

        if not app_path and not cli_path:
            state = {
                "status": STATUS_LMSTUDIO_NOT_INSTALLED,
                "message": "LM Studio is not installed on this machine.",
                "required_models": required,
                "inventory": inventory,
            }
            state["guidance"] = self._guidance_text(state)
            return state

        if not cli_path:
            state = {
                "status": STATUS_CLI_NOT_AVAILABLE,
                "message": (
                    "LM Studio is installed, but the lms command-line interface is not available. "
                    "Open LM Studio once, then bootstrap the CLI and re-check runtime."
                ),
                "required_models": required,
                "inventory": inventory,
            }
            state["guidance"] = self._guidance_text(state)
            return state

        if not inventory.get("server_running"):
            state = {
                "status": STATUS_SERVER_NOT_RUNNING,
                "message": "LM Studio CLI is available, but the local LM Studio server is not running.",
                "required_models": required,
                "inventory": inventory,
            }
            state["guidance"] = self._guidance_text(state)
            return state

        downloaded_llms = inventory.get("downloaded_llms") or []
        selected_models = inventory.get("selected_models") or {}
        if not downloaded_llms:
            state = {
                "status": STATUS_CHAT_MODEL_MISSING,
                "message": f"No downloaded LLM models were detected. Download the publish generative model ({PUBLISH_GENERATIVE_MODEL}) in LM Studio, then re-check runtime.",
                "required_models": required,
                "inventory": inventory,
            }
            state["guidance"] = self._guidance_text(state)
            return state

        if not selected_models.get("chat") or not selected_models.get("analysis"):
            state = {
                "status": STATUS_CHAT_MODEL_MISSING,
                "message": f"Download and load the publish generative model ({PUBLISH_GENERATIVE_MODEL}) for SerapeumAI completion jobs.",
                "required_models": required,
                "inventory": inventory,
            }
            state["guidance"] = self._guidance_text(state)
            return state

        if not self._embedding_model_available(local_only=True):
            state = {
                "status": STATUS_EMBEDDING_RUNTIME_NOT_READY,
                "message": f"Local embedding runtime is not ready for {required['embedding']}.",
                "required_models": required,
                "inventory": inventory,
            }
            state["guidance"] = self._guidance_text(state)
            return state

        loaded_roles = inventory.get("loaded_roles") or {}
        if not loaded_roles.get("analysis") or not loaded_roles.get("chat"):
            missing_roles = [role for role in ("chat", "analysis") if not loaded_roles.get(role)]
            role_text = ", ".join(missing_roles)
            state = {
                "status": STATUS_MODEL_NOT_LOADED,
                "message": f"Load the selected session model(s) for: {role_text}.",
                "required_models": required,
                "inventory": inventory,
            }
            state["guidance"] = self._guidance_text(state)
            return state

        state = {
            "status": STATUS_READY,
            "message": "Local intelligence runtime is ready.",
            "required_models": required,
            "inventory": inventory,
        }
        state["guidance"] = self._guidance_text(state)
        return state

    def get_runtime_inventory(self) -> Dict[str, Any]:
        state = self.detect_state()
        inventory = dict(state.get("inventory") or {})
        inventory["status"] = state.get("status")
        inventory["message"] = state.get("message")
        inventory["guidance"] = state.get("guidance")
        inventory["required_models"] = state.get("required_models")
        return inventory

    # ------------------------------------------------------------------
    # Guidance / session management actions
    # ------------------------------------------------------------------
    def provision(self, on_status=None) -> Dict[str, Any]:
        state = self.detect_state()
        return self._emit(on_status, state["status"], state["message"], guidance=state.get("guidance"), inventory=state.get("inventory"))

    def set_selected_models(self, *, chat_model: Optional[str], analysis_model: Optional[str]) -> Dict[str, Any]:
        selected_model = self.DEFAULT_ANALYSIS_MODEL
        if analysis_model and str(analysis_model).strip():
            selected_model = self.DEFAULT_ANALYSIS_MODEL
        elif chat_model and str(chat_model).strip():
            selected_model = self.DEFAULT_CHAT_MODEL
        self.config.set("models.chat.model", selected_model, scope="local")
        self.config.set("models.analysis.model", selected_model, scope="local")
        try:
            self.config.save(scope="local")
        except Exception:
            logger.debug("Saving local runtime model selection failed.", exc_info=True)
        return self.detect_state()

    def start_server(self, on_status=None) -> Dict[str, Any]:
        self._emit(on_status, STATUS_SERVER_NOT_RUNNING, "Starting the LM Studio local server...", phase="starting_server")
        result = self._run_cli(["server", "start"], timeout_s=60)
        if result.returncode != 0 and not self._server_running():
            detail = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
            raise RuntimeError(f"LM Studio server start failed: {detail.strip()}")
        deadline = time.time() + 30
        while time.time() < deadline:
            if self._server_running():
                self._server_started_by_app = True
                state = self.detect_state()
                return self._emit(on_status, state["status"], state["message"], phase="server_running", inventory=state.get("inventory"))
            time.sleep(0.5)
        raise RuntimeError("LM Studio server did not become ready after start command.")

    def prepare_embedding_runtime(self, on_status=None) -> Dict[str, Any]:
        self._emit(on_status, STATUS_EMBEDDING_RUNTIME_NOT_READY, f"Preparing local embedding runtime: {EMBEDDING_MODEL}", phase="preparing_embedding_runtime")
        try:
            from sentence_transformers import SentenceTransformer
            embedder = SentenceTransformer(EMBEDDING_MODEL, device="cpu")
            embedder.encode(["runtime readiness check"], convert_to_numpy=False)
            self._embedding_prepared = True
        except Exception as exc:
            raise RuntimeError(f"Embedding runtime preparation failed: {exc}") from exc
        state = self.detect_state()
        return self._emit(on_status, state["status"], state["message"], phase="embedding_runtime_ready", inventory=state.get("inventory"))

    def _role_identifier(self, role: str) -> str:
        return ROLE_IDENTIFIERS.get(role, f"serapeum-{role}")

    def _selected_model_for_role(self, role: str) -> str:
        downloaded = self._list_local_models("llm")
        selected = self._selected_models(downloaded).get(role)
        if not selected:
            raise RuntimeError(f"No downloaded model is currently selected for role '{role}'.")
        return selected

    def load_model_for_role(self, role: str, on_status=None) -> Dict[str, Any]:
        role = str(role or "analysis").strip().lower()
        if role not in ("chat", "analysis"):
            raise RuntimeError(f"Unsupported runtime role: {role}")

        selected_model = self._selected_model_for_role(role)
        inventory = self.get_runtime_inventory()
        if not inventory.get("server_running"):
            self.start_server(on_status=on_status)
            inventory = self.get_runtime_inventory()

        # If the same selected model already satisfies another loaded role, reuse it.
        selected_models = inventory.get("selected_models") or {}
        loaded_roles = inventory.get("loaded_roles") or {}
        if loaded_roles.get(role):
            return self._emit(on_status, STATUS_READY, f"Selected {role} model is already loaded.", phase="model_already_loaded", active_model=selected_model, inventory=inventory)
        for other_role in ("analysis", "chat"):
            if other_role == role:
                continue
            if selected_models.get(other_role) == selected_model and loaded_roles.get(other_role):
                return self._emit(on_status, STATUS_READY, f"Selected {role} model is already satisfied by the active {other_role} model.", phase="model_already_loaded", active_model=selected_model, inventory=inventory)

        identifier = self._role_identifier(role)
        self._emit(on_status, STATUS_MODEL_NOT_LOADED, f"Loading selected {role} model: {selected_model}", phase="loading_model", active_model=selected_model)
        result = self._run_cli(["load", selected_model, "--identifier", identifier], timeout_s=900)
        if result.returncode != 0:
            detail = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
            raise RuntimeError(f"Failed to load {role} model '{selected_model}': {detail.strip()}")
        self._loaded_models_by_app.add(identifier)
        self._role_to_loaded_identifier[role] = identifier
        inventory = self.get_runtime_inventory()
        state = self.detect_state()
        return self._emit(on_status, state["status"], state["message"], phase="model_loaded", active_model=selected_model, inventory=inventory)

    def unload_role_model(self, role: str, on_status=None) -> Dict[str, Any]:
        role = str(role or "analysis").strip().lower()
        identifier = self._role_to_loaded_identifier.get(role) or self._role_identifier(role)
        self._emit(on_status, STATUS_MODEL_NOT_LOADED, f"Unloading {role} session model: {identifier}", phase="unloading_model", active_model=identifier)
        result = self._run_cli(["unload", identifier], timeout_s=120)
        if result.returncode != 0:
            detail = ((result.stdout or "") + ("\n" + result.stderr if result.stderr else "")).strip()
            loaded_ids = {self._normalize_token(row.get("identifier")) for row in self._list_loaded_models()}
            if self._normalize_token(identifier) in loaded_ids:
                raise RuntimeError(f"Failed to unload {role} model '{identifier}': {detail}")
        self._loaded_models_by_app.discard(identifier)
        self._role_to_loaded_identifier.pop(role, None)
        state = self.detect_state()
        return self._emit(on_status, state["status"], state["message"], phase="model_unloaded", active_model=identifier, inventory=state.get("inventory"))

    def unload_session_models(self, on_status=None) -> Dict[str, Any]:
        for role in list(self._role_to_loaded_identifier.keys()):
            try:
                self.unload_role_model(role, on_status=on_status)
            except Exception:
                logger.debug("Role unload failed for %s", role, exc_info=True)
        state = self.detect_state()
        return self._emit(on_status, state["status"], state["message"], phase="session_models_unloaded", inventory=state.get("inventory"))

    def cleanup_provisioned_runtime(self) -> None:
        cli_path = self._find_lms_cli()
        if not cli_path:
            return
        for role in list(self._role_to_loaded_identifier.keys()):
            try:
                self.unload_role_model(role)
            except Exception:
                logger.debug("App-managed role unload failed for %s", role, exc_info=True)
        self._loaded_models_by_app.clear()
        self._role_to_loaded_identifier.clear()
        if self._server_started_by_app:
            try:
                result = self._run_cli(["server", "stop"], timeout_s=120)
                if result.returncode == 0:
                    logger.info("[RuntimeSetup] Stopped app-managed LM Studio server.")
                else:
                    logger.warning("[RuntimeSetup] Failed to stop app-managed LM Studio server: %s", (result.stdout or "").strip())
            except Exception:
                logger.debug("App-managed LM Studio server stop failed.", exc_info=True)
            finally:
                self._server_started_by_app = False

    # ------------------------------------------------------------------
    # Embedding readiness helpers
    # ------------------------------------------------------------------
    def _embedding_repo_id(self) -> str:
        model_name = str(EMBEDDING_MODEL or "").strip()
        if not model_name:
            return "sentence-transformers/all-MiniLM-L6-v2"
        if "/" in model_name:
            return model_name
        return f"sentence-transformers/{model_name}"

    def _candidate_embedding_cache_roots(self) -> List[str]:
        roots: List[str] = []
        for env_var in ("SENTENCE_TRANSFORMERS_HOME", "HF_HOME", "HUGGINGFACE_HUB_CACHE", "TRANSFORMERS_CACHE"):
            value = str(os.environ.get(env_var, "") or "").strip()
            if value:
                roots.append(value)
        home = os.path.expanduser("~")
        if home:
            roots.extend([
                os.path.join(home, ".cache", "huggingface", "hub"),
                os.path.join(home, ".cache", "torch", "sentence_transformers"),
                os.path.join(home, ".cache", "sentence_transformers"),
            ])
        if os.name == "nt":
            userprofile = os.environ.get("USERPROFILE", home)
            local_appdata = os.environ.get("LOCALAPPDATA", "")
            if userprofile:
                roots.extend([
                    os.path.join(userprofile, ".cache", "huggingface", "hub"),
                    os.path.join(userprofile, ".cache", "torch", "sentence_transformers"),
                    os.path.join(userprofile, ".cache", "sentence_transformers"),
                ])
            if local_appdata:
                roots.extend([
                    os.path.join(local_appdata, "huggingface", "hub"),
                    os.path.join(local_appdata, "sentence_transformers"),
                ])
        out: List[str] = []
        seen: Set[str] = set()
        for root in roots:
            norm = os.path.normcase(os.path.abspath(root))
            if norm in seen:
                continue
            seen.add(norm)
            out.append(root)
        return out

    def _embedding_cache_marker_present(self) -> bool:
        markers = {str(EMBEDDING_MODEL or "").strip().lower(), self._embedding_repo_id().split("/")[-1].strip().lower()}
        for root in self._candidate_embedding_cache_roots():
            if not root or not os.path.isdir(root):
                continue
            try:
                for name in os.listdir(root):
                    lowered = name.lower()
                    if any(marker and marker in lowered for marker in markers):
                        return True
                for _current_root, dirs, _files in os.walk(root):
                    for directory in dirs:
                        lowered = directory.lower()
                        if any(marker and marker in lowered for marker in markers):
                            return True
                    break
            except Exception:
                logger.debug("Embedding cache scan failed for %s", root, exc_info=True)
        return False

    def _embedding_model_available(self, *, local_only: bool) -> bool:
        if self._embedding_prepared:
            return True
        repo_id = self._embedding_repo_id()
        if local_only and self._embedding_cache_marker_present():
            return True
        try:
            from huggingface_hub import snapshot_download
            snapshot_download(repo_id=repo_id, local_files_only=local_only)
            return True
        except Exception:
            if local_only:
                return self._embedding_cache_marker_present()
            return False

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------
    def verify_ready(self) -> Dict[str, Any]:
        state = self.detect_state()
        if state.get("status") != STATUS_READY:
            raise RuntimeError(f"{state.get('status')}: {state.get('message')}")

        inventory = state.get("inventory") or {}
        selected_models = inventory.get("selected_models") or {}
        lm = self._build_lm_client()
        try:
            analysis_model = selected_models.get("analysis")
            chat_model = selected_models.get("chat")
            lm.verify_chat_runtime(target_model=analysis_model, require_stateful=False)
            if chat_model and chat_model != analysis_model:
                lm.verify_chat_runtime(target_model=chat_model, require_stateful=False)
        except LMStudioRuntimeContractError as exc:
            raise RuntimeError(str(exc)) from exc
        except Exception as exc:
            raise RuntimeError(f"Chat/completion runtime verification failed: {exc}") from exc

        return {
            "status": STATUS_READY,
            "message": "Local intelligence runtime is ready.",
            "inventory": inventory,
        }
