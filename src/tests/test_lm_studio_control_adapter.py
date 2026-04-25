import unittest
from unittest.mock import Mock

from src.infra.services.lm_studio_control_adapter import LMStudioControlAdapter


class TestLMStudioControlAdapter(unittest.TestCase):
    def test_constructor_has_no_control_side_effects(self):
        runner = Mock()
        which = Mock(return_value="/usr/bin/lms")
        LMStudioControlAdapter(url="http://127.0.0.1:1234", runner=runner, which=which)
        runner.assert_not_called()
        which.assert_not_called()

    def test_start_server_without_cli_is_blocked_without_install(self):
        runner = Mock()
        which = Mock(return_value=None)
        adapter = LMStudioControlAdapter(runner=runner, which=which)
        out = adapter.start_server()
        self.assertFalse(out["executed"])
        self.assertEqual(out["reason"], "lms_cli_not_found")
        self.assertFalse(out["install_attempted"])
        runner.assert_not_called()

    def test_detect_cli_reports_machine_ready_truth_without_install(self):
        which = Mock(return_value=None)
        adapter = LMStudioControlAdapter(which=which)
        out = adapter.detect_cli()
        self.assertFalse(out["lms_cli_detected"])
        self.assertEqual(out["lms_cli_path"], "")
        self.assertFalse(out["install_attempted"])

    def test_start_server_runs_only_explicit_commands(self):
        calls = []

        def _runner(cmd, timeout_s):
            calls.append((cmd, timeout_s))
            return 0, "ok"

        which = Mock(return_value="/usr/bin/lms")
        adapter = LMStudioControlAdapter(url="http://127.0.0.1:1234", runner=_runner, which=which)
        out = adapter.start_server(start_daemon=True, cors=True, timeout_s=7)
        self.assertTrue(out["executed"])
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][0], ["/usr/bin/lms", "daemon", "up"])
        self.assertEqual(calls[1][0], ["/usr/bin/lms", "server", "start", "--port", "1234", "--cors"])
        self.assertFalse(out["install_attempted"])

    def test_stop_server_runs_only_explicit_command(self):
        calls = []

        def _runner(cmd, timeout_s):
            calls.append((cmd, timeout_s))
            return 0, "ok"

        which = Mock(return_value="/usr/bin/lms")
        adapter = LMStudioControlAdapter(runner=_runner, which=which)
        out = adapter.stop_server(timeout_s=9)
        self.assertTrue(out["executed"])
        self.assertEqual(calls[0][0], ["/usr/bin/lms", "server", "stop"])
        self.assertFalse(out["install_attempted"])


if __name__ == "__main__":
    unittest.main()
