# -*- coding: utf-8 -*-
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PRESENTER_PATH = ROOT / "src" / "ui" / "presenters" / "runtime_wizard_presenter.py"


def _load_presenter():
    spec = importlib.util.spec_from_file_location(
        "runtime_wizard_presenter_under_test",
        PRESENTER_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


presenter = _load_presenter()
SECTION_ORDER = presenter.SECTION_ORDER
present_runtime_wizard_sections = presenter.present_runtime_wizard_sections


def _sections_by_id(out):
    return {section["id"]: section for section in out["sections"]}


def test_empty_input_produces_safe_not_ready_unknown_sections():
    out = present_runtime_wizard_sections({})
    sections = _sections_by_id(out)

    assert out["executed"] is False
    assert out["can_execute"] is False
    assert sections["status"]["status"] == "unknown"
    assert sections["provider"]["status"] == "not_ready"
    assert sections["model_selection"]["status"] == "not_ready"
    assert "unknown" in sections["status"]["summary"].lower()
    assert "not ready" in sections["provider"]["summary"].lower()
    assert "not treated as locally available" in sections["model_selection"]["summary"]


def test_provider_model_and_recommendation_data_is_surfaced_deterministically():
    out = present_runtime_wizard_sections(
        {
            "selected_provider": "lm_studio",
            "selected_provider_mode": "lm_studio_manual_openai_compat",
            "selected_chat_model": "qwen2.5-coder-7b-instruct",
            "selected_analysis_model": "qwen2.5-coder-7b-instruct",
            "model_selection_ready": True,
            "model_readiness": "not_verified",
            "available_models": [
                {
                    "model_id": "qwen2.5-coder-7b-instruct",
                    "display_name": "Qwen Coder 7B",
                }
            ],
            "runtime_status": {
                "summary_status": "provider_reachable_model_not_verified",
                "provider_count": 2,
                "reachable_provider_count": 1,
                "providers": [
                    {
                        "provider_name": "lm_studio",
                        "display_status": "Reachable",
                        "provider_mode_label": "LM Studio manual",
                    }
                ],
            },
            "model_recommendation": {
                "profile_class": "balanced",
                "model_posture": "balanced_7b_quantized",
                "recommended_entries": [
                    {
                        "display_name": "Balanced 7B Local Q4",
                        "model_id": "balanced-7b-local-q4",
                        "role": "narrator",
                        "quantization": "Q4_K_M",
                    }
                ],
                "warnings": ["Advisory only."],
                "constraints": ["No automatic runtime action."],
            },
        }
    )
    sections = _sections_by_id(out)

    assert sections["status"]["status"] == "needs_model_verification"
    assert sections["provider"]["rows"][0] == {
        "label": "Selected provider",
        "value": "lm_studio",
    }
    assert any(row["value"] == "Qwen Coder 7B" or row["value"] == "qwen2.5-coder-7b-instruct" for row in sections["model_selection"]["rows"])
    assert any(row["label"] == "Balanced 7B Local Q4" for row in sections["recommendation"]["rows"])
    assert any(row["value"] == "Advisory only." for row in sections["recommendation"]["rows"])


def test_input_dictionary_is_not_mutated():
    read_model = {
        "selected_provider": "ollama",
        "runtime_status": {"providers": [{"provider_name": "ollama"}]},
        "model_recommendation": {"warnings": ["keep"]},
    }
    original = copy.deepcopy(read_model)

    present_runtime_wizard_sections(read_model)

    assert read_model == original


def test_consent_and_side_effect_facts_are_displayed_but_not_executed():
    out = present_runtime_wizard_sections(
        {
            "consent_requirements": ["provider_start"],
            "side_effects": {
                "provider_mutated": False,
                "config_mutated": False,
            },
        }
    )
    section = _sections_by_id(out)["consent_side_effects"]

    assert out["executed"] is False
    assert out["can_execute"] is False
    assert section["status"] == "display_only"
    assert "never executes actions" in section["summary"]
    assert {"label": "Consent requirement", "value": "provider_start"} in section["rows"]
    assert {"label": "provider_mutated", "value": False} in section["rows"]


def test_no_overclaim_when_provider_or_model_readiness_is_absent():
    out = present_runtime_wizard_sections(
        {
            "runtime_status": {"summary_status": "no_provider_reachable"},
            "selected_provider": "",
            "selected_chat_model": "",
            "selected_analysis_model": "",
            "model_recommendation": {
                "recommended_entries": [{"model_id": "balanced-7b-local-q4"}]
            },
        }
    )
    text = json.dumps(out).lower()

    assert "no local provider is reachable" in text
    assert "not treated as locally available" in text
    assert "guidance only" in text
    assert "loaded" not in text


def test_output_is_json_serializable():
    out = present_runtime_wizard_sections(
        {
            "runtime_status": {
                "summary_status": "provider_discovery_unavailable",
                "provider_count": 0,
                "reachable_provider_count": 0,
            }
        }
    )

    assert json.loads(json.dumps(out, sort_keys=True)) == out


def test_section_order_is_deterministic():
    out = present_runtime_wizard_sections({})

    assert out["section_order"] == list(SECTION_ORDER)
    assert [section["id"] for section in out["sections"]] == list(SECTION_ORDER)
