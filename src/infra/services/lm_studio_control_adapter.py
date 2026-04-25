# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import shutil
import subprocess as sp
from typing import Callable, Dict, List, Optional, Tuple
from urllib.parse import urlparse


class LMStudioControlAdapter:
    def __init__(
        self,
        *,
        url: str = "http://127.0.0.1:1234",
        lms_path: Optional[str] = None,
        runner: Optional[Callable[[List[str], int], Tuple[int, str]]] = None,
        which: Optional[Callable[[str], Optional[str]]] = None,
    ) -> None:
        self.url = (url or "http://127.0.0.1:1234").rstrip("/")
        self.lms_path = lms_path or None
        self._runner = runner or self._run_cli
        self._which = which or shutil.which

    @staticmethod
    def _run_cli(cmd: List[str], timeout_s: int = 45) -> Tuple[int, str]:
        try:
            res = sp.run(cmd, capture_output=True, text=True, timeout=timeout_s, check=False)
            return res.returncode, (res.stdout + res.stderr).strip()
        except sp.TimeoutExpired:
            return -1, "Command timed out"
        except Exception as e:
            return -1, f"Execution error: {e}"

    def _parse_port(self) -> int:
        parsed = urlparse(self.url)
        return int(parsed.port or 1234)

    def _resolve_lms_binary(self) -> Optional[str]:
        if self.lms_path:
            return self.lms_path if os.path.exists(self.lms_path) else None
        return self._which("lms.exe" if os.name == "nt" else "lms") or self._which("lms")

    def detect_cli(self) -> Dict[str, object]:
        cli_path = self._resolve_lms_binary()
        return {
            "lms_cli_detected": bool(cli_path),
            "lms_cli_path": cli_path or "",
            "install_attempted": False,
        }

    def start_server(self, *, start_daemon: bool = True, cors: bool = False, timeout_s: int = 30) -> Dict[str, object]:
        lms = self._resolve_lms_binary()
        if not lms:
            return {
                "executed": False,
                "reason": "lms_cli_not_found",
                "install_attempted": False,
                "commands": [],
            }

        commands_run: List[List[str]] = []
        if start_daemon:
            daemon_cmd = [lms, "daemon", "up"]
            commands_run.append(daemon_cmd)
            self._runner(daemon_cmd, timeout_s)

        server_cmd = [lms, "server", "start", "--port", str(self._parse_port())]
        if cors:
            server_cmd.append("--cors")
        commands_run.append(server_cmd)
        code, out = self._runner(server_cmd, timeout_s)
        return {
            "executed": code == 0,
            "reason": "ok" if code == 0 else "server_start_failed",
            "install_attempted": False,
            "commands": commands_run,
            "output": out,
        }

    def stop_server(self, *, timeout_s: int = 30) -> Dict[str, object]:
        lms = self._resolve_lms_binary()
        if not lms:
            return {
                "executed": False,
                "reason": "lms_cli_not_found",
                "install_attempted": False,
                "commands": [],
            }
        cmd = [lms, "server", "stop"]
        code, out = self._runner(cmd, timeout_s)
        return {
            "executed": code == 0,
            "reason": "ok" if code == 0 else "server_stop_failed",
            "install_attempted": False,
            "commands": [cmd],
            "output": out,
        }
