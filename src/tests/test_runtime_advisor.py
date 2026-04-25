import unittest
from unittest.mock import patch
from urllib import error

from src.infra.services.runtime_advisor import (
    HardwareAdvisor,
    LMStudioProviderAdapter,
    ProviderRegistry,
    ProviderStatus,
    RecommendationEngine,
    RuntimeAdvisorService,
)


class _StubProvider:
    def __init__(self, name, status: ProviderStatus):
        self.name = name
        self._status = status

    def discover(self):
        return self._status


class TestRuntimeAdvisor(unittest.TestCase):
    def test_balanced_classification_for_8gb_16gb_laptop_tier(self):
        profile = HardwareAdvisor.profile_from_snapshot(
            gpu_available=True,
            gpu_name="NVIDIA RTX 4060 Laptop GPU",
            vram_total_mb=8192,
            ram_total_mb=16384,
            os_name="nt",
        )
        self.assertEqual(profile.hardware_class, "BALANCED")

    def test_provider_registry_is_deterministic(self):
        registry = ProviderRegistry([
            _StubProvider("zeta", ProviderStatus("zeta", False, "n/a", "test", [])),
            _StubProvider("alpha", ProviderStatus("alpha", True, "http://127.0.0.1", "ok", [])),
        ])
        self.assertEqual([p.name for p in registry.discover_providers()], ["alpha", "zeta"])

    def test_recommendation_contains_required_schema(self):
        profile = HardwareAdvisor.profile_from_snapshot(
            gpu_available=True,
            gpu_name="RTX 4060",
            vram_total_mb=8192,
            ram_total_mb=16384,
            os_name="nt",
        )
        rec = RecommendationEngine.recommend(
            profile,
            [ProviderStatus("lm_studio", True, "http://127.0.0.1:1234", "reachable", ["chat_completions"])],
        )
        self.assertEqual(rec["recommended_profile_class"], "BALANCED")
        self.assertEqual(rec["recommended_runtime_posture"], "local_balanced")
        self.assertEqual(rec["recommended_model_posture"], "balanced_7b_quantized")

    def test_lmstudio_disabled_in_config_is_unavailable(self):
        st = LMStudioProviderAdapter(enabled=False, url="http://127.0.0.1:1234").discover()
        self.assertFalse(st.available)
        self.assertEqual(st.reason, "disabled_in_config")

    def test_lmstudio_unreachable_is_unavailable(self):
        provider = LMStudioProviderAdapter(enabled=True, url="http://127.0.0.1:1234")
        with patch("src.infra.services.runtime_advisor.request.urlopen", side_effect=error.URLError("offline")):
            st = provider.discover()
        self.assertFalse(st.available)
        self.assertTrue(st.reason.startswith("unreachable:"))

    def test_disabled_config_hides_start_and_stop_even_with_cli(self):
        class _Cfg:
            def get_section(self, name):
                return {"enabled": False, "url": "http://127.0.0.1:1234"} if name == "lm_studio" else {}

        svc = RuntimeAdvisorService(_Cfg())
        with patch.object(
            svc._control_adapter,
            "detect_cli",
            return_value={"lms_cli_detected": True, "lms_cli_path": "/usr/bin/lms", "install_attempted": False},
        ):
            advisory = svc.get_advisory()
        caps = advisory["runtime_control_capability"]
        self.assertFalse(caps["start_action_exposable"])
        self.assertFalse(caps["stop_action_exposable"])

    def test_start_exposed_stop_hidden_when_cli_detected_but_provider_unreachable(self):
        class _Cfg:
            def get_section(self, name):
                return {"enabled": True, "url": "http://127.0.0.1:1234"} if name == "lm_studio" else {}

        svc = RuntimeAdvisorService(_Cfg())
        with patch("src.infra.services.runtime_advisor.request.urlopen", side_effect=error.URLError("offline")), patch.object(
            svc._control_adapter,
            "detect_cli",
            return_value={"lms_cli_detected": True, "lms_cli_path": "/usr/bin/lms", "install_attempted": False},
        ):
            advisory = svc.get_advisory()
        self.assertTrue(advisory["runtime_control_capability"]["start_action_exposable"])
        self.assertFalse(advisory["runtime_control_capability"]["stop_action_exposable"])

    def test_blocked_control_returns_latest_control_status(self):
        class _Cfg:
            def get_section(self, name):
                return {"enabled": True, "url": "http://127.0.0.1:1234"} if name == "lm_studio" else {}

        svc = RuntimeAdvisorService(_Cfg())
        with patch.object(svc._control_adapter, "detect_cli", return_value={"lms_cli_detected": False, "lms_cli_path": ""}):
            out = svc.execute_safe_action("start_lm_studio_server", confirmed=True)
        self.assertFalse(out["executed"])
        self.assertIn("latest_control_status", out)
        self.assertEqual(out["latest_control_status"]["last_control_dispatch_reason"], "blocked_by_gating_truth")


if __name__ == "__main__":
    unittest.main()
