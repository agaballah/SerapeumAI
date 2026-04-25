# -*- coding: utf-8 -*-
"""
test_runtime_setup_service_subprocess_windowing.py

Wave 1A-1B: suppress packaged LM Studio CLI console windows from Runtime Setup.

Locks the Windows behavior that LocalRuntimeSetupService helper CLI calls are
launched without flashing transient console windows in packaged/windowed builds.
"""

import os
import subprocess
from types import SimpleNamespace

from src.infra.services.runtime_setup_service import LocalRuntimeSetupService


def _service_shell():
    return object.__new__(LocalRuntimeSetupService)


def test_runtime_setup_subprocess_window_options_are_empty_on_non_windows(monkeypatch):
    service = _service_shell()

    monkeypatch.setattr(os, "name", "posix", raising=False)

    assert service._subprocess_window_options() == {}


def test_runtime_setup_subprocess_window_options_hide_windows_console(monkeypatch):
    service = _service_shell()

    monkeypatch.setattr(os, "name", "nt", raising=False)

    options = service._subprocess_window_options()

    assert options["creationflags"] == getattr(subprocess, "CREATE_NO_WINDOW", 0)
    assert options["startupinfo"].dwFlags & subprocess.STARTF_USESHOWWINDOW
    assert options["startupinfo"].wShowWindow == subprocess.SW_HIDE


def test_runtime_setup_run_cli_passes_hidden_window_options_to_subprocess(monkeypatch):
    service = _service_shell()
    captured = {}

    fake_startupinfo = object()

    monkeypatch.setattr(service, "_find_lms_cli", lambda: "C:/LM Studio/lms.exe")
    monkeypatch.setattr(
        service,
        "_subprocess_window_options",
        lambda: {"creationflags": 12345, "startupinfo": fake_startupinfo},
    )

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["kwargs"] = kwargs
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = service._run_cli(["load", "qwen2.5-coder-7b-instruct"], timeout_s=33)

    assert result.returncode == 0
    assert captured["cmd"] == ["C:/LM Studio/lms.exe", "load", "qwen2.5-coder-7b-instruct"]
    assert captured["kwargs"]["creationflags"] == 12345
    assert captured["kwargs"]["startupinfo"] is fake_startupinfo
    assert captured["kwargs"]["capture_output"] is True
    assert captured["kwargs"]["text"] is True
    assert captured["kwargs"]["encoding"] == "utf-8"
    assert captured["kwargs"]["errors"] == "replace"
    assert captured["kwargs"]["timeout"] == 33
    assert captured["kwargs"]["check"] is False
