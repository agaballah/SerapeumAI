from __future__ import annotations

import importlib
import json
import sys

from src.application.tools.calculator_tool import TOOL_ID as CALCULATOR_TOOL_ID


APPROVED_EXPORTS = sorted(
    [
        "ChatToolBridgeContractError",
        "ChatToolBridgeResult",
        "ToolExecutionOrchestrationResult",
        "ToolExecutionOrchestratorContractError",
        "ToolRequestAdapterContractError",
        "ToolRequestAdapterResult",
        "ToolUsePresentation",
        "ToolUsePresentationContractError",
        "adapt_tool_request",
        "build_chat_tool_bridge_envelope",
        "execute_tool_with_audit",
        "present_tool_adapter_result",
        "present_tool_orchestration_result",
    ]
)


FORBIDDEN_POLICY_EXPORTS = {
    "chat_tool_policy",
    "ChatToolPolicy",
    "ToolUsePolicy",
    "tool_policy",
    "tool_router",
    "autonomous_tool_router",
    "chat_tool_router",
    "parse_llm_tool_call",
    "llm_tool_call",
    "llm_tool_call_parser",
    "mcp",
    "agent_loop",
    "tool_agent",
    "audit_persistence",
    "persist_tool_audit",
    "certify_fact",
    "candidate_fact",
    "can_govern_certified_truth",
}


FORBIDDEN_IMPORTED_MODULES = {
    "src.ui.pages.chat_page",
    "src.ui.chat_page",
    "src.application.chat",
    "src.application.chat.tool_router",
    "src.application.chat.tool_policy",
    "src.application.tools.chat_tool_policy",
    "src.application.tools.autonomous_tool_router",
    "src.application.tools.chat_tool_router",
    "src.application.tools.llm_tool_call_parser",
    "src.application.tools.mcp",
    "src.application.tools.agent_loop",
    "src.application.tools.audit_persistence",
    "src.application.tools.tool_execution_orchestrator",
}


LAZY_TARGETS = {
    "src.application.tools.chat_tool_bridge",
    "src.application.tools.tool_request_adapter",
    "src.application.tools.tool_use_presentation",
    "src.application.tools.tool_execution_orchestrator",
}


def _purge_modules() -> None:
    for module_name in [
        "src.application.tools",
        *sorted(LAZY_TARGETS),
        *sorted(FORBIDDEN_IMPORTED_MODULES),
    ]:
        sys.modules.pop(module_name, None)


def _valid_payload() -> dict[str, object]:
    return {
        "request_id": "req-chat-tool-policy-surface",
        "tool_id": CALCULATOR_TOOL_ID,
        "arguments": {"operation": "add", "operands": [1, 2]},
        "correlation_id": "chat-policy-surface-gate",
        "requested_by": "chat_tool_policy_surface_gate",
        "consent_granted": False,
    }


def test_tool_package_exports_only_approved_contract_surface():
    _purge_modules()

    tools = importlib.import_module("src.application.tools")

    assert tools.__all__ == APPROVED_EXPORTS
    for name in FORBIDDEN_POLICY_EXPORTS:
        assert name not in tools.__all__


def test_plain_tool_package_import_does_not_load_chat_or_policy_modules():
    _purge_modules()

    importlib.import_module("src.application.tools")

    for module_name in FORBIDDEN_IMPORTED_MODULES:
        assert module_name not in sys.modules
    for module_name in LAZY_TARGETS:
        assert module_name not in sys.modules


def test_building_bridge_envelope_does_not_activate_policy_or_execution_surface():
    _purge_modules()

    tools = importlib.import_module("src.application.tools")
    result = tools.build_chat_tool_bridge_envelope(_valid_payload()).to_dict()

    assert result["status"] == "ready"
    assert result["executed"] is False
    assert result["can_govern_truth"] is False
    assert result["source"] == "chat_tool_bridge"
    assert json.loads(json.dumps(result, sort_keys=True)) == result

    assert "src.application.tools.chat_tool_bridge" in sys.modules
    assert "src.application.tools.tool_request_adapter" in sys.modules
    assert "src.application.tools.tool_use_presentation" in sys.modules

    for module_name in FORBIDDEN_IMPORTED_MODULES:
        assert module_name not in sys.modules


def test_forbidden_policy_symbols_raise_attribute_error():
    import src.application.tools as tools

    for name in FORBIDDEN_POLICY_EXPORTS:
        try:
            getattr(tools, name)
        except AttributeError:
            pass
        else:
            raise AssertionError(f"Forbidden policy symbol was exposed: {name}")


def test_bridge_outputs_never_claim_certified_truth_governance():
    from src.application.tools import build_chat_tool_bridge_envelope

    ready = build_chat_tool_bridge_envelope(_valid_payload()).to_dict()
    clarification = build_chat_tool_bridge_envelope(
        {
            "request_id": "req-policy-missing-tool",
            "arguments": {},
            "consent_granted": False,
        }
    ).to_dict()
    error = build_chat_tool_bridge_envelope(
        {
            "request_id": "req-policy-bad-args",
            "tool_id": CALCULATOR_TOOL_ID,
            "arguments": ["bad"],
            "consent_granted": False,
        }
    ).to_dict()

    for result in [ready, clarification, error]:
        assert result["executed"] is False
        assert result["can_govern_truth"] is False
        assert "certified" not in result
        assert "can_govern_certified_truth" not in result
        assert json.loads(json.dumps(result, sort_keys=True)) == result
