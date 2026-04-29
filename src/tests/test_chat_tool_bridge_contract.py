from __future__ import annotations

import importlib
import json
import sys

from src.application.tools.calculator_tool import TOOL_ID as CALCULATOR_TOOL_ID
from src.application.tools.chat_tool_bridge import (
    ChatToolBridgeResult,
    build_chat_tool_bridge_envelope,
)


def _valid_payload():
    return {
        "request_id": "req-bridge-001",
        "tool_id": CALCULATOR_TOOL_ID,
        "arguments": {"operation": "add", "operands": [1, 2]},
        "correlation_id": "chat-bridge-001",
        "requested_by": "chat_tool_bridge_test",
        "consent_granted": False,
    }


def test_valid_structured_request_builds_ready_non_executing_bridge_envelope():
    result = build_chat_tool_bridge_envelope(_valid_payload()).to_dict()

    assert result["status"] == "ready"
    assert result["source"] == "chat_tool_bridge"
    assert result["executed"] is False
    assert result["can_govern_truth"] is False
    assert result["request_id"] == "req-bridge-001"
    assert result["tool_id"] == CALCULATOR_TOOL_ID
    assert result["correlation_id"] == "chat-bridge-001"
    assert result["adapter_result"]["status"] == "ready"
    assert result["adapter_result"]["can_govern_truth"] is False
    assert result["presentation"]["status"] == "ready"
    assert result["presentation"]["can_govern_truth"] is False


def test_missing_tool_id_returns_controlled_clarification_bridge_envelope():
    payload = _valid_payload()
    payload.pop("tool_id")

    result = build_chat_tool_bridge_envelope(payload).to_dict()

    assert result["status"] == "clarification"
    assert result["executed"] is False
    assert result["can_govern_truth"] is False
    assert result["adapter_result"]["status"] == "clarification"
    assert result["adapter_result"]["clarification"]["missing_field"] == "tool_id"
    assert result["presentation"]["status"] == "clarification"


def test_non_mapping_payload_returns_controlled_error_bridge_envelope():
    result = build_chat_tool_bridge_envelope(["bad"]).to_dict()

    assert result["status"] == "error"
    assert result["executed"] is False
    assert result["can_govern_truth"] is False
    assert result["adapter_result"]["status"] == "error"
    assert result["adapter_result"]["error"]["error_type"] == "invalid_payload"
    assert result["presentation"]["status"] == "error"


def test_non_mapping_arguments_returns_controlled_error_bridge_envelope():
    payload = _valid_payload()
    payload["arguments"] = ["bad"]

    result = build_chat_tool_bridge_envelope(payload).to_dict()

    assert result["status"] == "error"
    assert result["executed"] is False
    assert result["can_govern_truth"] is False
    assert result["adapter_result"]["error"]["error_type"] == "invalid_arguments"
    assert result["presentation"]["metadata"]["error_type"] == "invalid_arguments"


def test_bridge_output_is_json_serializable():
    result = build_chat_tool_bridge_envelope(_valid_payload()).to_dict()

    assert json.loads(json.dumps(result, sort_keys=True)) == result


def test_bridge_contract_rejects_truth_governance():
    result = ChatToolBridgeResult(
        status="ready",
        adapter_result={"status": "ready", "can_govern_truth": False},
        presentation={"status": "ready", "can_govern_truth": False},
        can_govern_truth=True,
    )

    try:
        result.to_dict()
    except Exception as exc:
        assert "cannot govern truth" in str(exc)
    else:
        raise AssertionError("Expected bridge result to reject truth governance.")


def test_bridge_contract_rejects_execution_claim():
    result = ChatToolBridgeResult(
        status="ready",
        adapter_result={"status": "ready", "can_govern_truth": False},
        presentation={"status": "ready", "can_govern_truth": False},
        executed=True,
    )

    try:
        result.to_dict()
    except Exception as exc:
        assert "must not execute tools" in str(exc)
    else:
        raise AssertionError("Expected bridge result to reject execution.")


def test_bridge_module_does_not_expose_chat_router_or_llm_parser_symbols():
    import src.application.tools.chat_tool_bridge as bridge

    forbidden_names = {
        "execute_tool_with_audit",
        "chat_page",
        "chat_panel",
        "tool_router",
        "autonomous_tool_router",
        "parse_llm_tool_call",
        "llm_tool_call",
        "mcp",
        "agent_loop",
        "audit_persistence",
        "certify_fact",
        "candidate_fact",
    }

    for name in forbidden_names:
        assert not hasattr(bridge, name)


def test_bridge_does_not_import_orchestrator_when_building_envelope():
    modules_to_purge = [
        "src.application.tools.chat_tool_bridge",
        "src.application.tools.tool_request_adapter",
        "src.application.tools.tool_use_presentation",
        "src.application.tools.tool_execution_orchestrator",
    ]

    for module_name in modules_to_purge:
        sys.modules.pop(module_name, None)

    bridge = importlib.import_module("src.application.tools.chat_tool_bridge")
    assert "src.application.tools.tool_execution_orchestrator" not in sys.modules

    result = bridge.build_chat_tool_bridge_envelope(_valid_payload()).to_dict()

    assert result["status"] == "ready"
    assert result["executed"] is False
    assert "src.application.tools.tool_execution_orchestrator" not in sys.modules
