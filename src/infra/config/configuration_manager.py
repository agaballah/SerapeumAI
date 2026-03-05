# -*- coding: utf-8 -*-
"""
Configuration Manager - Layered configuration with clear ownership.

Best-practice layers (lowest -> highest):
0) Built-in safe defaults (in code)  <-- survives missing config/config.json
1) Committed defaults (source-controlled, but auto-created if missing):
      <APP_ROOT>/config/config.json

2) Local writable override (user/machine):
      <APP_ROOT>/.serapeum/config.yaml

3) Optional per-project override:
      <PROJECT_ROOT>/.serapeum/config.yaml

4) Environment overrides (highest priority):
      SERAPEUM_LLM_API_KEY, SERAPEUM_LLM_BASE_URL, SERAPEUM_LLM_MODEL
      SERAPEUM_LM_STUDIO_ENABLED, SERAPEUM_LM_STUDIO_URL
      SERAPEUM_MODELS_CHAT_MODEL, SERAPEUM_MODELS_ANALYSIS_MODEL, SERAPEUM_MODELS_VISION_MODEL
      SERAPEUM_MODELS_SUMMARIZATION_MODEL, SERAPEUM_MODELS_UNIVERSAL_MODEL
      SERAPEUM_MODELS_N_CTX

Notes:
- Zero legacy support: we do NOT read or migrate <APP_ROOT>/config.yaml.
- Saving never writes into repo root EXCEPT to bootstrap a missing/invalid config/config.json.
  (Once committed defaults exist and are valid, we do not overwrite them.)
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional, Literal

import yaml

Scope = Literal["local", "project"]


# ------------------------------- helpers ---------------------------------- #

def _infer_app_root() -> Path:
    """
    Infer repo/app root (folder containing 'src') from this file location.
    Expected path: <ROOT>/src/infra/config/configuration_manager.py
    """
    here = Path(__file__).resolve()
    for p in here.parents:
        if (p / "src").is_dir():
            return p
    return Path(os.getcwd()).resolve()


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Return a new dict = base merged with override (override wins).
    """
    out: Dict[str, Any] = dict(base or {})
    for k, v in (override or {}).items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _builtin_defaults() -> Dict[str, Any]:
    """
    Safe defaults to keep the app operational even if config/config.json is absent.
    Local/project overrides still win.
    """
    return {
        "pdf_processing": {
            "min_text_threshold": 500,
            "ocr_languages": "eng+ara",
            "vector_threshold": 1000,
            "force_ocr": False,
        },
        "analysis": {
            "max_tokens": 4096,
            "temperature": 0.7,
        },
        "vision": {
            "max_tokens": 2048,
            "temperature": 0.2,
            "parallel_workers": 1,
        },
        "lm_studio": {
            # Target mode: LM Studio multi-model
            "enabled": True,
            "url": "http://127.0.0.1:1234",

            # Headless control defaults (service may use these)
            "autostart_server": True,
            "start_daemon": True,
            "start_server": True,
            "startup_timeout_s": 90,
            "healthcheck_interval_s": 1.0,
            "lms_path": "",     # optional
            "cors": False,
            "tokens": {"chat": "", "admin": ""},
            "profiles": {},     # optional
        },
        "models": {
            # legacy / llama.cpp (only used if lm_studio.enabled == False)
            "n_ctx": 8192,

            # per-task routing ("auto" triggers benchmark-based selection)
            "chat": {"backend": "lm_studio", "model": "auto"},
            "analysis": {"backend": "lm_studio", "model": "auto"},
            "vision": {"backend": "lm_studio", "model": "auto"},
            "summarization": {"backend": "lm_studio", "model": "auto"},
            "universal": {"backend": "lm_studio", "model": "auto"},

            # auto-selection knobs (router/benchmark may read these)
            "auto_select": {
                "enabled": True,
                "strategy": "benchmark",
                "max_models_per_task": 8,
                "runs": 1,
                "timeout_s": 30,
                "min_quality": 0.50,
                "cache_ttl_s": 3600,
            },
        },
        # kept for backward compatibility
        "llm": {
            "api_key": "",
            "base_url": "",
            "model_name": "",
        },
    }


def _committed_defaults_template() -> Dict[str, Any]:
    """
    Minimal committed defaults file scaffold.
    This is created ONLY if config/config.json is missing or invalid.
    """
    return {
        "lm_studio": {"enabled": True, "url": "http://127.0.0.1:1234"},
        "analysis": {"max_tokens": 4096, "temperature": 0.7},
        "vision": {"max_tokens": 2048, "temperature": 0.2, "parallel_workers": 1},
        "models": {
            "n_ctx": 8192,
            "chat": {"backend": "lm_studio", "model": "auto"},
            "analysis": {"backend": "lm_studio", "model": "auto"},
            "vision": {"backend": "lm_studio", "model": "auto"},
            "summarization": {"backend": "lm_studio", "model": "auto"},
            "universal": {"backend": "lm_studio", "model": "auto"},
            "auto_select": {
                "enabled": True,
                "strategy": "benchmark",
                "max_models_per_task": 8,
                "runs": 1,
                "timeout_s": 30,
                "min_quality": 0.50,
                "cache_ttl_s": 3600,
            },
        },
        "pdf_processing": {
            "min_text_threshold": 500,
            "ocr_languages": "eng+ara",
            "vector_threshold": 1000,
            "force_ocr": False,
        },
    }


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _dump_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data or {}, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _dump_yaml(path: Path, data: Dict[str, Any], *, header: Optional[str] = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(
        data or {},
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )
    with open(path, "w", encoding="utf-8") as f:
        if header:
            f.write(header.rstrip() + "\n")
        f.write(text)


def _env_bool(name: str) -> Optional[bool]:
    """
    Parse common bool env forms. Returns None if unset/empty.
    """
    v = os.getenv(name)
    if v is None:
        return None
    s = str(v).strip().lower()
    if s == "":
        return None
    if s in ("1", "true", "yes", "y", "on"):
        return True
    if s in ("0", "false", "no", "n", "off"):
        return False
    return None


# --------------------------- ConfigurationManager -------------------------- #

class ConfigurationManager:
    """
    Unified configuration manager supporting layered config with project switching.
    """

    def __init__(self, root_dir: str | Path | None = None):
        self.root_dir: Path = (Path(root_dir).resolve() if root_dir else _infer_app_root())

        # Paths
        self._defaults_json_path: Path = self.root_dir / "config" / "config.json"
        self._local_override_path: Path = self.root_dir / ".serapeum" / "config.yaml"

        # Project override (optional/writable)
        self.project_root: Optional[Path] = None
        self._project_override_path: Optional[Path] = None

        # Layers
        self._defaults: Dict[str, Any] = {}
        self._local: Dict[str, Any] = {}
        self._project: Dict[str, Any] = {}

        # Cached merged config
        self._merged: Dict[str, Any] = {}
        self._dirty: bool = True

        # Bootstrap baseline files and load layers
        self._bootstrap_files()
        self._reload_layers()

    # -------------------------
    # Bootstrap & layer files
    # -------------------------

    def _bootstrap_files(self) -> None:
        """
        Ensure baseline config files exist for a clean run.

        Rules:
        - If <APP_ROOT>/config/config.json is missing, create it from template.
        - If it exists and is valid JSON dict, do NOT overwrite it.
        - If it exists but invalid JSON, quarantine it and recreate from template.
        - Always ensure local override exists (empty dict template).
        """
        (self.root_dir / "config").mkdir(parents=True, exist_ok=True)
        (self.root_dir / ".serapeum").mkdir(parents=True, exist_ok=True)

        # 1) committed defaults bootstrap only (or heal invalid)
        if not self._defaults_json_path.exists():
            _dump_json(self._defaults_json_path, _committed_defaults_template())
        else:
            # If it's present but invalid JSON, quarantine and recreate template.
            try:
                with open(self._defaults_json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, dict):
                    raise ValueError("config.json is not a JSON object")
            except Exception:
                bad = self._defaults_json_path.with_suffix(
                    f".bad.{time.strftime('%Y%m%d_%H%M%S')}.json"
                )
                try:
                    self._defaults_json_path.replace(bad)
                except Exception:
                    # If rename fails, we still attempt to overwrite with a good template.
                    pass
                _dump_json(self._defaults_json_path, _committed_defaults_template())

        # 2) local override (always exists)
        self._ensure_local_override_file()

    def _ensure_local_override_file(self) -> None:
        """
        Ensure <APP_ROOT>/.serapeum/config.yaml exists.
        """
        if self._local_override_path.exists():
            return

        _dump_yaml(
            self._local_override_path,
            {},
            header=(
                "# SerapeumAI local overrides (user/machine)\n"
                "# This file overrides committed defaults on THIS machine.\n"
                "# Leave as {} to inherit defaults.\n"
            ),
        )

    def _ensure_project_override_file(self, project_root: Path) -> Path:
        """
        Ensure <PROJECT_ROOT>/.serapeum/config.yaml exists. Create minimal if missing.
        """
        p = project_root.resolve() / ".serapeum" / "config.yaml"
        if not p.exists():
            _dump_yaml(
                p,
                {},
                header=(
                    "# SerapeumAI per-project overrides\n"
                    "# This file overrides app defaults ONLY for THIS project.\n"
                    "# Leave as {} to inherit global/local settings.\n"
                ),
            )
        return p

    # -------------------------
    # Env overrides
    # -------------------------

    def _apply_env_overrides(self, cfg: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply environment overrides with highest precedence.
        """
        out = dict(cfg or {})

        # ---- generic LLM env overrides (kept) ----
        llm = dict(out.get("llm", {}) if isinstance(out.get("llm", {}), dict) else {})
        changed_llm = False

        api_key = os.getenv("SERAPEUM_LLM_API_KEY")
        if api_key:
            llm["api_key"] = api_key
            changed_llm = True

        base_url = os.getenv("SERAPEUM_LLM_BASE_URL")
        if base_url:
            llm["base_url"] = base_url
            changed_llm = True

        model = os.getenv("SERAPEUM_LLM_MODEL")
        if model:
            llm["model_name"] = model
            changed_llm = True

        if changed_llm:
            out["llm"] = llm

        # ---- LM Studio env overrides ----
        lm_studio = dict(out.get("lm_studio", {}) if isinstance(out.get("lm_studio", {}), dict) else {})
        changed_lms = False

        lms_enabled = _env_bool("SERAPEUM_LM_STUDIO_ENABLED")
        if lms_enabled is not None:
            lm_studio["enabled"] = lms_enabled
            changed_lms = True

        lms_url = os.getenv("SERAPEUM_LM_STUDIO_URL")
        if lms_url:
            lm_studio["url"] = lms_url
            changed_lms = True

        if changed_lms:
            out["lm_studio"] = lm_studio

        # ---- models env overrides ----
        models = dict(out.get("models", {}) if isinstance(out.get("models", {}), dict) else {})
        changed_models = False

        n_ctx = os.getenv("SERAPEUM_MODELS_N_CTX")
        if n_ctx:
            try:
                models["n_ctx"] = int(n_ctx)
                changed_models = True
            except Exception:
                pass

        env_map = {
            "SERAPEUM_MODELS_CHAT_MODEL": "chat",
            "SERAPEUM_MODELS_ANALYSIS_MODEL": "analysis",
            "SERAPEUM_MODELS_VISION_MODEL": "vision",
            "SERAPEUM_MODELS_SUMMARIZATION_MODEL": "summarization",
            "SERAPEUM_MODELS_UNIVERSAL_MODEL": "universal",
        }
        for env_name, task in env_map.items():
            v = os.getenv(env_name)
            if not v:
                continue
            models.setdefault(task, {})
            if isinstance(models[task], dict):
                models[task]["backend"] = models[task].get("backend", "lm_studio")
                models[task]["model"] = v
                changed_models = True

        if changed_models:
            out["models"] = models

        return out

    # -------------------------
    # Load layers
    # -------------------------

    def _reload_layers(self) -> None:
        """
        Reload all layers from disk.
        """
        builtins = _builtin_defaults()
        committed = _load_json(self._defaults_json_path)

        # Effective defaults = builtins merged with committed
        self._defaults = _deep_merge(builtins, committed)

        # Overrides
        self._local = _load_yaml(self._local_override_path)
        if self._project_override_path and self._project_override_path.exists():
            self._project = _load_yaml(self._project_override_path)
        else:
            self._project = {}

        self._dirty = True

    def _rebuild_merged_if_needed(self) -> None:
        if not self._dirty:
            return

        merged = _deep_merge(self._defaults, self._local)
        merged = _deep_merge(merged, self._project)
        merged = self._apply_env_overrides(merged)

        self._merged = merged
        self._dirty = False

    # -------------------------
    # Public API
    # -------------------------

    def set_project_root(self, project_root: str | Path) -> None:
        """
        Switch active project override layer to:
            <PROJECT_ROOT>/.serapeum/config.yaml
        """
        # Close any lingering connections from the old project
        try:
            from src.infra.persistence.database_manager import DatabaseManager
            DatabaseManager.close_all_instances()
        except ImportError:
            pass

        proj = Path(project_root).resolve()
        self.project_root = proj
        self._project_override_path = self._ensure_project_override_file(proj)
        self._reload_layers()

    def clear_project_root(self) -> None:
        """
        Disable project override layer.
        """
        # Close any lingering connections
        try:
            from src.infra.persistence.database_manager import DatabaseManager
            DatabaseManager.close_all_instances()
        except ImportError:
            pass

        self.project_root = None
        self._project_override_path = None
        self._reload_layers()

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.
        Example: config.get("lm_studio.url")
        """
        self._rebuild_merged_if_needed()

        keys = key_path.split(".")
        value: Any = self._merged
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    def get_section(self, section: str) -> Dict[str, Any]:
        self._rebuild_merged_if_needed()
        v = self._merged.get(section, {})
        return v if isinstance(v, dict) else {}

    def get_all(self) -> Dict[str, Any]:
        self._rebuild_merged_if_needed()
        return dict(self._merged)

    def set(self, key_path: str, value: Any, *, scope: Scope = "local") -> None:
        """
        Set a value into a specific writable layer.
        Default scope is "local" (user/machine).
        """
        if scope not in ("local", "project"):
            raise ValueError(f"Invalid scope: {scope}")

        if scope == "project" and not self._project_override_path:
            raise RuntimeError("Project scope requested but no project_root is active.")

        target: Dict[str, Any] = self._local if scope == "local" else self._project

        keys = key_path.split(".")
        cur = target
        for k in keys[:-1]:
            nxt = cur.get(k)
            if not isinstance(nxt, dict):
                nxt = {}
                cur[k] = nxt
            cur = nxt
        cur[keys[-1]] = value

        self._dirty = True

    def save(self, *, scope: Scope = "local") -> str:
        """
        Persist the chosen writable layer to disk.
        - local  -> <APP_ROOT>/.serapeum/config.yaml
        - project-> <PROJECT_ROOT>/.serapeum/config.yaml
        """
        if scope not in ("local", "project"):
            raise ValueError(f"Invalid scope: {scope}")

        if scope == "local":
            header = (
                "# SerapeumAI local overrides (user/machine)\n"
                "# This file overrides committed defaults on THIS machine.\n"
                "# Leave as {} to inherit defaults.\n"
            )
            _dump_yaml(self._local_override_path, self._local, header=header)
            return str(self._local_override_path)

        if not self._project_override_path:
            raise RuntimeError("Project scope save requested but no project_root is active.")

        header = (
            "# SerapeumAI per-project overrides\n"
            "# This file overrides app defaults ONLY for THIS project.\n"
            "# Leave as {} to inherit global/local settings.\n"
        )
        _dump_yaml(self._project_override_path, self._project, header=header)
        return str(self._project_override_path)

    def reload(self) -> None:
        """
        Reload all layers from files (keeps active project_root if set).
        """
        self._bootstrap_files()
        self._reload_layers()

    def debug_paths(self) -> Dict[str, str]:
        """
        Useful for debugging what files are active.
        """
        return {
            "app_root": str(self.root_dir),
            "defaults_json": str(self._defaults_json_path),
            "defaults_json_exists": str(self._defaults_json_path.exists()),
            "local_override": str(self._local_override_path),
            "local_override_exists": str(self._local_override_path.exists()),
            "project_override": str(self._project_override_path) if self._project_override_path else "",
            "project_root": str(self.project_root) if self.project_root else "",
        }


# ------------------------------ global API --------------------------------- #

_config_manager: Optional[ConfigurationManager] = None


def get_config(root_dir: str | Path | None = None) -> ConfigurationManager:
    """
    Get or create global configuration manager instance.
    If root_dir is not supplied, it infers app root robustly.
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigurationManager(root_dir)
    return _config_manager


def reload_config() -> None:
    """
    Force reload of global configuration.
    """
    global _config_manager
    if _config_manager:
        _config_manager.reload()
