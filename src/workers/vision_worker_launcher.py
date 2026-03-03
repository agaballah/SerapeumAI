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
vision_worker_launcher.py — Safe starter for run_vision_worker.py

Used by UI (ChatPanel, MainWindow) to launch the async VLM caption worker.
"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import Optional


class VisionWorkerLauncher:
    """
    Launch run_vision_worker.py in a robust, cross-platform way.
    """

    def __init__(self, *, app_root: str) -> None:
        self.app_root = os.path.abspath(app_root)

    # ------------------------------------------------------------------
    def start_worker(self, *, project_root: str, project_id: Optional[str] = None) -> dict:
        """
        Launches:
            python -m src.vision.run_vision_worker --db-root <project> --project-id <id>

        Returns:
            { "ok": bool, "pid": <process id or None>, "error": <optional> }
        """

        exe = sys.executable or "python"
        DETACHED = 0x00000008 if os.name == "nt" else 0

        args = [
            exe,
            "-m",
            "src.vision.run_vision_worker",
            "--db-root",
            os.path.abspath(project_root),
        ]

        if project_id:
            args += ["--project-id", str(project_id)]

        try:
            proc = subprocess.Popen(
                args,
                cwd=self.app_root,
                creationflags=DETACHED if os.name == "nt" else 0,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            pid = getattr(proc, "pid", None)
            return {"ok": True, "pid": pid}
        except Exception as e:
            return {"ok": False, "error": str(e), "pid": None}

    # ------------------------------------------------------------------
    def check_health(self, *, base_url: str = "http://127.0.0.1:1234/v1") -> dict:
        """
        Optional: check LM Studio server status.
        Only performs a HEAD request to avoid overhead.
        """
        import requests

        try:
            r = requests.head(base_url, timeout=2)
            if r.status_code in (200, 400, 404):
                return {"ok": True}
            return {"ok": False, "status": r.status_code}
        except Exception as e:
            return {"ok": False, "error": str(e)}
