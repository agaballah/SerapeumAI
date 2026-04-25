# -*- coding: utf-8 -*-
"""
Read-only Runtime Advisor view helpers.
"""


def resolve_runtime_action_feedback_message(action_id: str, result: dict) -> str:
    action = str(action_id or "").strip()
    fallback = (result or {}).get("message", "Action completed." if (result or {}).get("executed") else "Action not executed.")
    status = (result or {}).get("latest_control_status", {})
    if action in {"start_lm_studio_server", "stop_lm_studio_server"} and isinstance(status, dict):
        rich = str(status.get("last_control_message", "")).strip()
        if rich:
            return rich
    return fallback


def build_runtime_advisor_status_summary(latest_control_status: dict, latest_probe_captured_at: str) -> str:
    control = latest_control_status if isinstance(latest_control_status, dict) else {}
    probe_ts = str(latest_probe_captured_at or "").strip()
    if control:
        control_msg = str(control.get("last_control_message", "")).strip()
        if control_msg:
            return f"Latest control: {control_msg}"
    if probe_ts:
        return f"Latest probe captured at (UTC): {probe_ts}"
    return "No recent runtime advisor action."


def format_runtime_advisory_text(advisory: dict) -> str:
    hw = advisory.get("hardware_profile", {}) if isinstance(advisory, dict) else {}
    rec = advisory.get("recommendation", {}) if isinstance(advisory, dict) else {}
    providers = rec.get("detected_providers", []) if isinstance(rec, dict) else []
    plan = advisory.get("action_plan", {}) if isinstance(advisory, dict) else {}
    actions = advisory.get("available_actions", []) if isinstance(advisory, dict) else []
    probe = advisory.get("latest_probe_diagnostics", {}) if isinstance(advisory, dict) else {}
    probe_captured_at = advisory.get("latest_probe_captured_at", "") if isinstance(advisory, dict) else ""
    control = advisory.get("latest_control_status", {}) if isinstance(advisory, dict) else {}
    caps = advisory.get("runtime_control_capability", {}) if isinstance(advisory, dict) else {}

    lines = [
        "Runtime Advisor (Advisory + Safe Local Actions)",
        "No install/download/provisioning actions are executed automatically here.",
        "",
        f"Hardware class: {hw.get('hardware_class', 'unknown')}",
        f"GPU: {hw.get('gpu_name', 'unknown')} (available={hw.get('gpu_available', False)})",
        f"VRAM total (MB): {hw.get('vram_total_mb', 0)}",
        f"RAM total (MB): {hw.get('ram_total_mb', 0)}",
        f"Detection method: {hw.get('detection_method', 'unknown')}",
        "",
        f"Recommended profile: {rec.get('recommended_profile_class', 'unknown')}",
        f"Runtime posture: {rec.get('recommended_runtime_posture', 'unknown')}",
        f"Model posture: {rec.get('recommended_model_posture', 'unknown')}",
        "",
        "Providers:",
    ]
    if providers:
        for p in providers:
            lines.append(
                f"- {p.get('name', 'unknown')}: available={p.get('available', False)} reason={p.get('reason', '')}"
            )
    else:
        lines.append("- (none detected)")

    warnings = rec.get("warnings", []) if isinstance(rec, dict) else []
    constraints = rec.get("constraints", []) if isinstance(rec, dict) else []
    lines.append("")
    lines.append("Warnings:")
    lines.extend([f"- {w}" for w in warnings] or ["- none"])
    lines.append("")
    lines.append("Constraints:")
    lines.extend([f"- {c}" for c in constraints] or ["- none"])

    lines.append("")
    lines.append("Next Action Plan:")
    lines.append(f"Status: {plan.get('status', 'unknown')}")
    lines.append(f"Consent required: {plan.get('consent_required', False)}")
    lines.append(f"Planned next step: {plan.get('planned_next_step', 'unknown')}")
    lines.append("Signals:")
    plan_signals = plan.get("signals", []) if isinstance(plan, dict) else []
    lines.extend([f"- {s}" for s in plan_signals] or ["- none"])
    lines.append("Notes:")
    plan_notes = plan.get("notes", []) if isinstance(plan, dict) else []
    lines.extend([f"- {n}" for n in plan_notes] or ["- none"])

    lines.append("")
    lines.append("Available Safe Actions:")
    if actions:
        for a in actions:
            lines.append(
                f"- {a.get('id', 'unknown')}: {a.get('label', '')} "
                f"(confirm={a.get('requires_confirmation', False)}, mutates_config={a.get('mutates_config', False)})"
            )
    else:
        lines.append("- none")

    probe_providers = probe.get("providers", []) if isinstance(probe, dict) else []
    if probe_providers:
        lines.append("")
        lines.append("-----")
        lines.append("Latest Probe Diagnostics:")
        lines.append(f"Captured at (UTC): {probe_captured_at or 'unknown'}")
        for p in probe_providers:
            lines.append(f"- Provider: {p.get('name', 'unknown')}")
            lines.append(f"  endpoint: {p.get('endpoint', '')}")
            lines.append(f"  available: {p.get('available', False)}")
            lines.append(f"  reason: {p.get('reason', '')}")
            provider_caps = p.get("capabilities", []) if isinstance(p, dict) else []
            lines.append(f"  capabilities: {', '.join(provider_caps) if provider_caps else '(none)'}")

    if control:
        lines.append("")
        lines.append("-----")
        lines.append("Latest Control Status:")
        lines.append(f"- action: {control.get('last_control_action', 'unknown')}")
        lines.append(f"- dispatch_executed: {control.get('last_control_dispatch_executed', False)}")
        lines.append(f"- dispatch_reason: {control.get('last_control_dispatch_reason', 'unknown')}")
        lines.append(f"- immediate_recheck_reachable: {control.get('last_control_recheck_reachable', False)}")
        lines.append(f"- checked_at_utc: {control.get('last_control_checked_at_utc', 'unknown')}")
        lines.append(f"- message: {control.get('last_control_message', '')}")

    if caps:
        lines.append("")
        lines.append("-----")
        lines.append("Runtime Control Capability (Truth):")
        lines.append(f"- runtime_control_supported: {caps.get('runtime_control_supported', False)}")
        lines.append(f"- control_execution_supported: {caps.get('control_execution_supported', False)}")
        lines.append(f"- advisory_probe_supported: {caps.get('advisory_probe_supported', False)}")
        lines.append(f"- safe_control_seam_available: {caps.get('safe_control_seam_available', False)}")
        lines.append(f"- lms_cli_detected: {caps.get('lms_cli_detected', False)}")
        lines.append(f"- provider_reachable_now: {caps.get('provider_reachable_now', False)}")
        lines.append(f"- start_action_exposable: {caps.get('start_action_exposable', False)}")
        lines.append(f"- stop_action_exposable: {caps.get('stop_action_exposable', False)}")
        lines.append(f"- start_supported: {caps.get('start_supported', False)}")
        lines.append(f"- stop_supported: {caps.get('stop_supported', False)}")
        lines.append(
            f"- explicit_confirmation_required_for_control: {caps.get('explicit_confirmation_required_for_control', True)}"
        )
        for lim in caps.get("limitations", []) if isinstance(caps, dict) else []:
            lines.append(f"- limitation: {lim}")
        blockers = caps.get("blockers", []) if isinstance(caps, dict) else []
        for blk in blockers:
            if isinstance(blk, dict):
                lines.append(f"- blocker: {blk.get('seam', 'unknown')} -> {blk.get('reason', '')}")

    return "\n".join(lines)
