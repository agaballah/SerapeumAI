# -*- coding: utf-8 -*-
import threading
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ModelManager:
    """
    Minimal production-safe singleton model manager with:
      - per-process model cache
      - global inference lock (serialize llama.cpp calls)
      - lightweight lock_model/unlock_model ownership tracking
      - backward-compatible wrapper signatures
      - task aliasing to avoid loading the same GGUF multiple times
    """
    _instance = None

    # Used by inference callers to serialize llama.cpp access
    inference_lock = threading.Lock()

    # Task aliases are removed to prevent collapsing routed model roles.
    _TASK_ALIASES = {}

    def __new__(cls):
        if cls._instance is None:
            inst = super(ModelManager, cls).__new__(cls)
            inst._models: Dict[str, Any] = {}
            inst._locked_by: Optional[str] = None
            cls._instance = inst
        return cls._instance

    def _normalize_task(self, task_type: str) -> str:
        t = str(task_type or "").strip().lower() or "universal"
        return self._TASK_ALIASES.get(t, t)

    def get_model(self, task_type: str, model_path: Optional[str] = None, auto_load: bool = True) -> Any:
        """
        Load-on-demand. Model roles are now kept separate.
        """
        task = self._normalize_task(task_type)

        if task in self._models:
            return self._models[task]

        if not auto_load or not model_path:
            return None

        # Protect model load (avoid double-load in concurrent startup)
        with self.inference_lock:
            if task in self._models:
                return self._models[task]

            from src.utils.hardware_utils import reserve_vram, check_resource_availability
            tier = task # Use task name as tier hint
            if not check_resource_availability(tier):
                logger.error(f"Insufficient VRAM to load {task} model: {model_path}")
                return None

            from llama_cpp import Llama  # llama-cpp-python

            logger.info(f"Loading '{task}' model from {model_path}...")
            self._models[task] = Llama(
                model_path=model_path,
                n_gpu_layers=33,
                n_ctx=4096,
                verbose=False,
            )
            return self._models[task]

    def unload(self, task_type: str) -> None:
        task = self._normalize_task(task_type)
        if task in self._models:
            del self._models[task]

    # ---------------- lock ownership (coarse orchestration) ---------------- #

    def lock(self, owner: str) -> bool:
        """
        Coarse “who owns the pipeline” lock (analysis vs vision vs other).
        NOTE: This is independent of inference_lock.
        """
        o = str(owner or "").strip() or "unknown"
        if self._locked_by is None:
            self._locked_by = o
            return True
        return False

    def unlock(self, owner: Optional[str] = None) -> None:
        """
        Unlock if:
          - owner is None (force unlock), OR
          - owner matches current locked_by.
        """
        if owner is None:
            self._locked_by = None
            return

        o = str(owner).strip()
        if self._locked_by == o:
            self._locked_by = None

    def get_status(self) -> Dict[str, Any]:
        return {
            "active_models": sorted(list(self._models.keys())),
            "locked": self._locked_by is not None,
            "locked_by": self._locked_by,
        }


# ------------------------- module-level compatibility ------------------------ #

def get_model_status() -> Dict[str, Any]:
    return ModelManager().get_status()


def lock_model(owner: str) -> bool:
    # Existing code passes task name ("vision"/"analysis") as owner — that's fine
    return ModelManager().lock(owner)


def unlock_model(owner: Optional[str] = None) -> None:
    # Backward-compatible with BOTH:
    #   unlock_model()
    #   unlock_model("vision")
    ModelManager().unlock(owner)


def unload_model(task_type: str) -> None:
    ModelManager().unload(task_type)


def get_model_for_task(task_type: str, model_path: Optional[str] = None, auto_load: bool = True) -> Any:
    return ModelManager().get_model(task_type, model_path, auto_load)
