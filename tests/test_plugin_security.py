"""
Plugin security tests aligned to the current tools/* implementations.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

from plugin_sandbox import PluginSandbox, SandboxConfig
from plugin_signature_verifier import PluginSignatureVerifier


class TestPluginSignatureVerifier(unittest.TestCase):
    """Tests for the M1 hash-based plugin signature verifier."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.whitelist_path = os.path.join(self.temp_dir, "whitelist.json")
        self.verifier = PluginSignatureVerifier(self.whitelist_path)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_plugin_file(self, content: str = "def test_plugin():\n    return 'test'\n") -> str:
        plugin_path = os.path.join(self.temp_dir, "plugin.py")
        with open(plugin_path, "w", encoding="utf-8") as handle:
            handle.write(content)
        return plugin_path

    def test_verify_plugin_returns_false_for_unlisted_plugin(self):
        plugin_path = self._create_plugin_file()

        result = self.verifier.verify_plugin(plugin_path, "test_plugin", "1.0.0")

        self.assertFalse(result.verified)
        self.assertEqual(result.plugin_name, "test_plugin")
        self.assertEqual(result.version, "1.0.0")
        self.assertNotEqual(result.file_hash, "")

    def test_add_to_whitelist_allows_verification(self):
        plugin_path = self._create_plugin_file()

        added = self.verifier.add_to_whitelist("test_plugin", "1.0.0", plugin_path)
        result = self.verifier.verify_plugin(plugin_path, "test_plugin", "1.0.0")

        self.assertTrue(added)
        self.assertTrue(result.verified)
        self.assertIn(("test_plugin", "1.0.0"), self.verifier.list_whitelisted_plugins())

    def test_tampered_plugin_fails_verification(self):
        plugin_path = self._create_plugin_file()
        self.verifier.add_to_whitelist("test_plugin", "1.0.0", plugin_path)

        with open(plugin_path, "a", encoding="utf-8") as handle:
            handle.write("\n# tampered")

        result = self.verifier.verify_plugin(plugin_path, "test_plugin", "1.0.0")

        self.assertFalse(result.verified)


class TestPluginSandbox(unittest.TestCase):
    """Tests for the current lightweight sandbox wrapper."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config = SandboxConfig(
            max_memory_mb=128,
            max_cpu_time_seconds=2,
            temp_dir=self.temp_dir,
        )
        self.sandbox = PluginSandbox(self.config)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_sandbox_config_defaults_allowed_hosts(self):
        config = SandboxConfig()

        self.assertEqual(config.allowed_network_hosts, [])
        self.assertEqual(config.max_memory_mb, 100)
        self.assertEqual(config.max_cpu_time_seconds, 30)

    def test_execute_plugin_success(self):
        process = MagicMock()
        process.communicate.return_value = (b"plugin output", b"")
        process.returncode = 0
        process.pid = 123

        with patch("plugin_sandbox.subprocess.Popen", return_value=process) as popen:
            with patch.object(self.sandbox, "_get_memory_usage", return_value=12.5):
                with patch.object(self.sandbox, "_get_cpu_time", return_value=0.5):
                    result = self.sandbox.execute_plugin(sys.executable, ["-c", "print('ok')"])

        self.assertTrue(result.success)
        self.assertEqual(result.output, "plugin output")
        self.assertEqual(result.error, "")
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.memory_used_mb, 12.5)
        self.assertEqual(result.cpu_time_seconds, 0.5)
        popen.assert_called_once()

    def test_execute_plugin_timeout(self):
        process = MagicMock()
        process.communicate.side_effect = [
            subprocess.TimeoutExpired(cmd="python", timeout=2),
            (b"", b""),
        ]

        with patch("plugin_sandbox.subprocess.Popen", return_value=process):
            result = self.sandbox.execute_plugin(sys.executable, ["-c", "import time; time.sleep(10)"])

        self.assertFalse(result.success)
        self.assertEqual(result.exit_code, -1)
        self.assertIn("Timeout after 2s", result.error)
        process.kill.assert_called_once()

    def test_execute_plugin_reports_spawn_error(self):
        with patch("plugin_sandbox.subprocess.Popen", side_effect=OSError("spawn failed")):
            result = self.sandbox.execute_plugin(sys.executable, ["-c", "print('ok')"])

        self.assertFalse(result.success)
        self.assertEqual(result.exit_code, -1)
        self.assertIn("spawn failed", result.error)

    def test_cleanup_removes_temp_dir(self):
        sandbox = PluginSandbox(SandboxConfig(temp_dir=self.temp_dir))

        sandbox.cleanup()

        self.assertFalse(os.path.exists(self.temp_dir))


if __name__ == "__main__":
    unittest.main()
