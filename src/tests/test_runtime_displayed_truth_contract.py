# -*- coding: utf-8 -*-
"""
R1: Runtime displayed-truth contract checks.

This file is intentionally dependency-light. It does not import MainApp,
src.ui, tkinter, customtkinter, extraction jobs, or runtime adapters.
"""

import ast
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MAIN_WINDOW_PATH = ROOT / "src" / "ui" / "main_window.py"
PRESENTER_PATH = ROOT / "src" / "ui" / "presenters" / "runtime_platform_presenter.py"


def _load_runtime_platform_presenter():
    spec = importlib.util.spec_from_file_location(
        "runtime_platform_presenter_under_test",
        PRESENTER_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _apply_runtime_platform_sidebar_node():
    tree = ast.parse(MAIN_WINDOW_PATH.read_text(encoding="utf-8"))

    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "MainApp":
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "_apply_runtime_platform_sidebar":
                    return item

    raise AssertionError("MainApp._apply_runtime_platform_sidebar was not found.")


def _is_ready_guard_return(stmt):
    if not isinstance(stmt, ast.If):
        return False

    test = stmt.test
    if not isinstance(test, ast.Compare):
        return False

    left = test.left
    if not (
        isinstance(left, ast.Attribute)
        and left.attr == "_runtime_status_code"
        and isinstance(left.value, ast.Name)
        and left.value.id == "self"
    ):
        return False

    if len(test.ops) != 1 or not isinstance(test.ops[0], ast.Eq):
        return False

    if len(test.comparators) != 1:
        return False

    right = test.comparators[0]
    if not isinstance(right, ast.Name) or right.id != "STATUS_READY":
        return False

    return any(isinstance(child, ast.Return) for child in stmt.body)


def _is_runtime_label_configure(stmt):
    call = None

    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
        call = stmt.value
    elif isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Call):
        call = stmt.value

    if call is None:
        return False

    func = call.func
    if not isinstance(func, ast.Attribute) or func.attr != "configure":
        return False

    target = func.value
    return (
        isinstance(target, ast.Attribute)
        and target.attr == "lbl_runtime"
        and isinstance(target.value, ast.Name)
        and target.value.id == "self"
    )


def test_ready_guard_precedes_runtime_platform_label_write():
    method = _apply_runtime_platform_sidebar_node()

    for stmt in method.body:
        if _is_ready_guard_return(stmt):
            return
        if _is_runtime_label_configure(stmt):
            raise AssertionError("Runtime platform sidebar writes lbl_runtime before READY guard.")

    raise AssertionError("READY guard was not found before lbl_runtime.configure.")


def test_provider_advisory_presenter_still_reports_non_ready_status():
    presenter = _load_runtime_platform_presenter()

    out = presenter.present_runtime_platform_sidebar(
        {
            "runtime_status": {
                "summary_status": "provider_reachable_model_not_verified",
                "provider_count": 1,
                "reachable_provider_count": 1,
            },
            "model_recommendation": {
                "profile_class": "balanced",
                "model_posture": "balanced_7b_quantized",
            },
        }
    )

    assert out["tone"] == "warning"
    assert out["primary"] == "Runtime: provider reachable - model not verified"
    assert "model/task readiness has not been proven" in out["detail"]


if __name__ == "__main__":
    test_ready_guard_precedes_runtime_platform_label_write()
    test_provider_advisory_presenter_still_reports_non_ready_status()
    print("runtime displayed truth contract checks passed")
