# -*- coding: utf-8 -*-
"""
R1: Runtime displayed-truth contract tests.

These tests verify MainApp shell composition without launching Tk.
"""

from src.infra.services.runtime_setup_service import STATUS_READY
from src.ui.main_window import MainApp


class DummyLabel:
    def __init__(self):
        self.configured = []
        self.text = None
        self.fg = None

    def configure(self, **kwargs):
        self.configured.append(dict(kwargs))
        if "text" in kwargs:
            self.text = kwargs["text"]
        if "fg" in kwargs:
            self.fg = kwargs["fg"]


class DummyShell:
    def __init__(self, status_code):
        self.lbl_runtime = DummyLabel()
        self._runtime_status_code = status_code


def _read_model(summary_status):
    reachable = 1 if summary_status == "provider_reachable_model_not_verified" else 0
    return {
        "runtime_status": {
            "summary_status": summary_status,
            "provider_count": 1,
            "reachable_provider_count": reachable,
        },
        "model_recommendation": {
            "profile_class": "balanced",
            "model_posture": "balanced_7b_quantized",
        },
    }


def test_active_ready_is_not_overwritten_by_provider_reachable_advisory():
    shell = DummyShell(STATUS_READY)
    shell.lbl_runtime.configure(text="Runtime: ready", fg="success")

    MainApp._apply_runtime_platform_sidebar(
        shell,
        _read_model("provider_reachable_model_not_verified"),
    )

    assert shell.lbl_runtime.text == "Runtime: ready"
    assert len(shell.lbl_runtime.configured) == 1


def test_active_ready_is_not_overwritten_by_discovery_unavailable():
    shell = DummyShell(STATUS_READY)
    shell.lbl_runtime.configure(text="Runtime: ready", fg="success")

    MainApp._apply_runtime_platform_sidebar(
        shell,
        _read_model("provider_discovery_unavailable"),
    )

    assert shell.lbl_runtime.text == "Runtime: ready"
    assert len(shell.lbl_runtime.configured) == 1


def test_non_ready_status_may_show_provider_advisory():
    shell = DummyShell("MODEL_NOT_LOADED")

    MainApp._apply_runtime_platform_sidebar(
        shell,
        _read_model("provider_reachable_model_not_verified"),
    )

    assert shell.lbl_runtime.text is not None
    assert "provider reachable - model not verified" in shell.lbl_runtime.text
