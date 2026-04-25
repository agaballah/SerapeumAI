import unittest
from unittest.mock import patch
from urllib import error

from src.infra.services.benchmark_service import get_machine_hardware_snapshot
from src.infra.services.runtime_advisor import (
    HardwareAdvisor,
    LMStudioProviderAdapter,
    ProviderRegistry,
    ProviderStatus,
    RecommendationEngine,
    RuntimeAdvisorService,
)


class _StubProvider:
    def __init__(self, name, status):
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
        self.assertEqual(profile.detection_method, "snapshot")

    def test_provider_registry_is_deterministic(self):
        registry = ProviderRegistry(
            adapters=[
                _StubProvider("zeta", ProviderStatus(name="zeta", available=False, endpoint="n/a", reason="test", capabilities=[])),
                _StubProvider("alpha", ProviderStatus(name="alpha", available=True, endpoint="http://127.0.0.1", reason="ok", capabilities=[])),
            ]
        )
        self.assertEqual([p.name for p in registry.discover_providers()], ["alpha", "zeta"])

    def test_recommendation_contains_required_schema(self):
        profile = HardwareAdvisor.profile_from_snapshot(
            gpu_available=True,
            gpu_name="RTX 4060",
            vram_total_mb=8192,
            ram_total_mb=16384,
            os_name="nt",
        )
        providers = [ProviderStatus(name="lm_studio", available=True, endpoint="http://127.0.0.1:1234", reason="reachable", capabilities=["chat_completions"])]
        rec = RecommendationEngine.recommend(profile, providers)
        self.assertEqual(rec["recommended_profile_class"], "BALANCED")
        self.assertEqual(rec["recommended_runtime_posture"], "local_balanced")
        self.assertEqual(rec["recommended_model_posture"], "balanced_7b_quantized")

    def test_runtime_advisory_service_smoke_output(self):
        class _Cfg:
            def get_section(self, name):
                return {"enabled": False, "url": "http://127.0.0.1:1234"} if name == "lm_studio" else {}

        with patch("src.infra.services.runtime_advisor.get_machine_hardware_snapshot", return_value={
            "gpu_available": True,
            "gpu_name": "RTX 4060 Laptop GPU",
            "vram_total_mb": 8192,
            "vram_free_mb": 4096,
            "ram_total_mb": 16384,
            "os_name": "nt",
            "detection_method": "torch",
        }):
            advisory = RuntimeAdvisorService(_Cfg()).get_advisory()

        self.assertEqual(advisory["hardware_profile"]["hardware_class"], "BALANCED")
        self.assertEqual(advisory["action_plan"]["status"], "provider_disabled_in_config")
        self.assertTrue(advisory["action_plan"]["consent_required"])
        caps = advisory["runtime_control_capability"]
        self.assertFalse(caps["runtime_control_supported"])
        self.assertFalse(caps["lms_cli_detected"])
        blocker_seams = [b["seam"] for b in caps["blockers"]]
        self.assertIn("LMStudioService._ensure_server_running", blocker_seams)
        self.assertIn("LMStudioControlAdapter.detect_cli", blocker_seams)

    def test_lmstudio_disabled_in_config_is_unavailable(self):
        provider = LMStudioProviderAdapter(enabled=False, url="http://127.0.0.1:1234")
        st = provider.discover()
        self.assertFalse(st.available)
        self.assertEqual(st.reason, "disabled_in_config")

    def test_lmstudio_non_success_http_is_not_available(self):
        provider = LMStudioProviderAdapter(enabled=True, url="http://127.0.0.1:1234")

        class _Resp:
            status = 401
            def __enter__(self): return self
            def __exit__(self, exc_type, exc, tb): return False

        with patch("src.infra.services.runtime_advisor.request.urlopen", return_value=_Resp()):
            st = provider.discover()
        self.assertFalse(st.available)
        self.assertEqual(st.reason, "http_401")

    def test_hardware_snapshot_without_gpu_does_not_fake_free_vram(self):
        fake_torch = type("FakeTorch", (), {"cuda": type("Cuda", (), {"is_available": staticmethod(lambda: False)})()})
        with patch("src.infra.services.benchmark_service._get_free_vram_mb", return_value=9999), patch.dict("sys.modules", {"torch": fake_torch}):
            snap = get_machine_hardware_snapshot()
        self.assertFalse(snap["gpu_available"])
        self.assertEqual(snap["vram_total_mb"], 0)
        self.assertEqual(snap["vram_free_mb"], 0)

    def test_action_plan_no_action_needed_when_provider_reachable(self):
        class _Cfg:
            def get_section(self, name):
                return {"enabled": True, "url": "http://127.0.0.1:1234"} if name == "lm_studio" else {}

        with patch("src.infra.services.runtime_advisor.get_machine_hardware_snapshot", return_value={
            "gpu_available": True,
            "gpu_name": "RTX 4060",
            "vram_total_mb": 8192,
            "ram_total_mb": 16384,
            "os_name": "nt",
            "detection_method": "torch",
        }), patch("src.infra.services.runtime_advisor.request.urlopen") as mock_urlopen:
            class _Resp:
                status = 200
                def __enter__(self): return self
                def __exit__(self, exc_type, exc, tb): return False
            mock_urlopen.return_value = _Resp()
            advisory = RuntimeAdvisorService(_Cfg()).get_advisory()

        self.assertEqual(advisory["action_plan"]["status"], "no_action_needed")
        self.assertFalse(advisory["action_plan"]["consent_required"])

    def test_execute_probe_health_with_confirmation_returns_diagnostics(self):
        class _Cfg:
            def get_section(self, name):
                return {"enabled": True, "url": "http://127.0.0.1:1234"} if name == "lm_studio" else {}

        svc = RuntimeAdvisorService(_Cfg())
        with patch("src.infra.services.runtime_advisor.request.urlopen") as mock_urlopen:
            class _Resp:
                status = 200
                def __enter__(self): return self
                def __exit__(self, exc_type, exc, tb): return False
            mock_urlopen.return_value = _Resp()
            out = svc.execute_safe_action("probe_provider_health", confirmed=True)
        self.assertTrue(out["executed"])
        self.assertIn("providers", out["diagnostics"])

    def test_execute_enable_action_with_confirmation_updates_local_config(self):
        class _Cfg:
            def __init__(self): self.writes = []
            def set(self, key, value, scope="local"): self.writes.append((key, value, scope))
            def save(self, scope="local"):
                self.writes.append(("save", scope))
                return "/tmp/local-config.yaml"
            def get_section(self, name): return {}

        cfg = _Cfg()
        svc = RuntimeAdvisorService(cfg)
        out = svc.execute_safe_action("enable_lm_studio_provider", confirmed=True)
        self.assertTrue(out["executed"])
        self.assertIn(("lm_studio.enabled", True, "local"), cfg.writes)

    def test_execute_start_action_uses_control_adapter_only_when_unreachable(self):
        class _Cfg:
            def get_section(self, name):
                return {"enabled": True, "url": "http://127.0.0.1:1234"} if name == "lm_studio" else {}

        svc = RuntimeAdvisorService(_Cfg())
        with patch("src.infra.services.runtime_advisor.request.urlopen", side_effect=error.URLError("offline")), patch.object(
            svc._control_adapter, "detect_cli", return_value={"lms_cli_detected": True, "lms_cli_path": "/usr/bin/lms"}
        ), patch.object(
            svc._control_adapter, "start_server", return_value={"executed": True, "reason": "ok", "install_attempted": False}
        ) as mock_start:
            out = svc.execute_safe_action("start_lm_studio_server", confirmed=True)
        self.assertTrue(out["executed"])
        self.assertEqual(out["execution_path"], "LMStudioControlAdapter.start_server")
        mock_start.assert_called_once()

    def test_execute_start_action_blocked_when_already_reachable(self):
        class _Cfg:
            def get_section(self, name):
                return {"enabled": True, "url": "http://127.0.0.1:1234"} if name == "lm_studio" else {}

        svc = RuntimeAdvisorService(_Cfg())
        with patch("src.infra.services.runtime_advisor.request.urlopen") as mock_urlopen, patch.object(
            svc._control_adapter,
            "detect_cli",
            return_value={"lms_cli_detected": True, "lms_cli_path": "/usr/bin/lms", "install_attempted": False},
        ):
            class _Resp:
                status = 200
                def __enter__(self): return self
                def __exit__(self, exc_type, exc, tb): return False
            mock_urlopen.return_value = _Resp()
            out = svc.execute_safe_action("start_lm_studio_server", confirmed=True)
        self.assertFalse(out["executed"])
        self.assertEqual(out["latest_control_status"]["last_control_dispatch_reason"], "blocked_by_gating_truth")

    def test_execute_stop_action_blocked_when_already_unreachable(self):
        class _Cfg:
            def get_section(self, name):
                return {"enabled": True, "url": "http://127.0.0.1:1234"} if name == "lm_studio" else {}

        svc = RuntimeAdvisorService(_Cfg())
        with patch("src.infra.services.runtime_advisor.request.urlopen", side_effect=error.URLError("offline")), patch.object(
            svc._control_adapter,
            "detect_cli",
            return_value={"lms_cli_detected": True, "lms_cli_path": "/usr/bin/lms", "install_attempted": False},
        ):
            out = svc.execute_safe_action("stop_lm_studio_server", confirmed=True)
        self.assertFalse(out["executed"])
        self.assertEqual(out["latest_control_status"]["last_control_dispatch_reason"], "blocked_by_gating_truth")

    def test_stop_dispatched_and_recheck_unreachable_truth(self):
        class _Cfg:
            def get_section(self, name):
                return {"enabled": True, "url": "http://127.0.0.1:1234"} if name == "lm_studio" else {}

        svc = RuntimeAdvisorService(_Cfg())

        class _Resp:
            status = 200
            def __enter__(self): return self
            def __exit__(self, exc_type, exc, tb): return False

        with patch("src.infra.services.runtime_advisor.request.urlopen", side_effect=[_Resp(), error.URLError("offline")]), patch.object(
            svc._control_adapter,
            "detect_cli",
            return_value={"lms_cli_detected": True, "lms_cli_path": "/usr/bin/lms", "install_attempted": False},
        ), patch.object(
            svc._control_adapter,
            "stop_server",
            return_value={"executed": True, "reason": "ok", "install_attempted": False},
        ):
            out = svc.execute_safe_action("stop_lm_studio_server", confirmed=True)
        status = out["latest_control_status"]
        self.assertTrue(status["last_control_dispatch_executed"])
        self.assertFalse(status["last_control_recheck_reachable"])
        self.assertIn("provider unreachable on immediate re-check", status["last_control_message"])


if __name__ == "__main__":
    unittest.main()
