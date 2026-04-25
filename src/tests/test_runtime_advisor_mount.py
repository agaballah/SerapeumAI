import unittest

from src.infra.services.runtime_advisor_view import (
    build_runtime_advisor_status_summary,
    format_runtime_advisory_text,
    resolve_runtime_action_feedback_message,
)


class TestRuntimeAdvisorMount(unittest.TestCase):
    def test_format_runtime_advisory_contains_required_fields(self):
        advisory = {
            "hardware_profile": {
                "hardware_class": "BALANCED",
                "gpu_available": True,
                "gpu_name": "RTX 4060 Laptop GPU",
                "vram_total_mb": 8192,
                "ram_total_mb": 16384,
                "detection_method": "torch",
            },
            "recommendation": {
                "detected_providers": [{"name": "lm_studio", "available": True, "reason": "reachable"}],
                "recommended_profile_class": "BALANCED",
                "recommended_runtime_posture": "local_balanced",
                "recommended_model_posture": "balanced_7b_quantized",
                "warnings": ["sample warning"],
                "constraints": ["sample constraint"],
            },
            "action_plan": {
                "status": "provider_reachable",
                "signals": ["provider_reachable", "model_posture_recommended_but_not_verified"],
                "consent_required": False,
                "planned_next_step": "read_only_planning_only",
                "notes": ["sample note"],
            },
            "available_actions": [
                {"id": "recheck_provider", "label": "Re-check provider status", "requires_confirmation": False, "mutates_config": False},
                {"id": "probe_provider_health", "label": "Run provider health/details probe", "requires_confirmation": True, "mutates_config": False},
            ],
            "latest_probe_diagnostics": {
                "providers": [{"name": "lm_studio", "endpoint": "http://127.0.0.1:1234", "available": False, "reason": "http_503", "capabilities": []}]
            },
            "latest_probe_captured_at": "2026-04-21T10:00:00+00:00",
            "latest_control_status": {
                "last_control_action": "start_lm_studio_server",
                "last_control_dispatch_executed": True,
                "last_control_dispatch_reason": "ok",
                "last_control_recheck_reachable": False,
                "last_control_checked_at_utc": "2026-04-21T10:02:00+00:00",
                "last_control_message": "Start command dispatched; provider not yet reachable on immediate re-check.",
            },
            "runtime_control_capability": {
                "runtime_control_supported": False,
                "control_execution_supported": False,
                "advisory_probe_supported": True,
                "safe_control_seam_available": True,
                "lms_cli_detected": False,
                "provider_reachable_now": False,
                "start_action_exposable": False,
                "stop_action_exposable": False,
                "start_supported": False,
                "stop_supported": False,
                "explicit_confirmation_required_for_control": True,
                "limitations": ["Phase 4A classification-only."],
                "blockers": [{"seam": "LMStudioService._ensure_server_running", "reason": "Can execute lms daemon/server start commands."}],
            },
        }
        txt = format_runtime_advisory_text(advisory)
        self.assertIn("No install/download/provisioning actions are executed automatically here.", txt)
        self.assertIn("Hardware class: BALANCED", txt)
        self.assertIn("Recommended profile: BALANCED", txt)
        self.assertIn("Runtime posture: local_balanced", txt)
        self.assertIn("Model posture: balanced_7b_quantized", txt)
        self.assertIn("lm_studio: available=True", txt)
        self.assertIn("Latest Probe Diagnostics:", txt)
        self.assertIn("Latest Control Status:", txt)
        self.assertIn("Runtime Control Capability (Truth):", txt)
        self.assertIn("start_action_exposable: False", txt)
        self.assertIn("stop_action_exposable: False", txt)

    def test_runtime_action_feedback_uses_latest_control_message_for_start(self):
        msg = resolve_runtime_action_feedback_message(
            "start_lm_studio_server",
            {
                "executed": True,
                "message": "generic start message",
                "latest_control_status": {
                    "last_control_message": "Start command dispatched; provider not yet reachable on immediate re-check."
                },
            },
        )
        self.assertEqual(msg, "Start command dispatched; provider not yet reachable on immediate re-check.")

    def test_runtime_action_feedback_keeps_probe_message(self):
        msg = resolve_runtime_action_feedback_message(
            "probe_provider_health",
            {
                "executed": True,
                "message": "Provider health/details probe completed.",
                "latest_control_status": {"last_control_message": "should not be used for probe"},
            },
        )
        self.assertEqual(msg, "Provider health/details probe completed.")

    def test_control_status_block_can_be_cleared_without_affecting_probe_block(self):
        advisory = {
            "latest_probe_diagnostics": {"providers": [{"name": "lm_studio", "endpoint": "http://127.0.0.1:1234"}]},
            "latest_probe_captured_at": "2026-04-22T00:00:00+00:00",
            "latest_control_status": {"last_control_action": "start_lm_studio_server", "last_control_message": "m"},
        }
        with_control = format_runtime_advisory_text(advisory)
        self.assertIn("Latest Probe Diagnostics:", with_control)
        self.assertIn("Latest Control Status:", with_control)
        advisory.pop("latest_control_status", None)
        without_control = format_runtime_advisory_text(advisory)
        self.assertIn("Latest Probe Diagnostics:", without_control)
        self.assertNotIn("Latest Control Status:", without_control)

    def test_status_summary_prefers_latest_control_message(self):
        s = build_runtime_advisor_status_summary(
            {"last_control_message": "Stop command dispatched; provider still reachable on immediate re-check."},
            "2026-04-22T00:00:00+00:00",
        )
        self.assertEqual(s, "Latest control: Stop command dispatched; provider still reachable on immediate re-check.")

    def test_status_summary_falls_back_to_probe_timestamp(self):
        s = build_runtime_advisor_status_summary({}, "2026-04-22T00:00:00+00:00")
        self.assertEqual(s, "Latest probe captured at (UTC): 2026-04-22T00:00:00+00:00")

    def test_status_summary_neutral_when_no_recent_data(self):
        s = build_runtime_advisor_status_summary({}, "")
        self.assertEqual(s, "No recent runtime advisor action.")


if __name__ == "__main__":
    unittest.main()
