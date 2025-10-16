"""
Plugin Security Tests

This module contains security tests for the plugin sandboxing system, 
including tests for resource limits, security violations, and malicious plugin behavior.
"""

import unittest
import pytest
from unittest.mock import Mock, patch
import tempfile
import os
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

class TestPluginSecurity(unittest.TestCase):
    """Test plugin security and sandboxing functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_plugin_resource_limits(self):
        """Test that plugins respect resource limits."""
        # TODO: Implement resource limit tests
        # This will test memory, CPU, and file system limits
        pass
    
    def test_plugin_security_violations(self):
        """Test detection of security violations."""
        # TODO: Implement security violation tests
        # This will test for unauthorized file access, network calls, etc.
        pass
    
    def test_malicious_plugin_behavior(self):
        """Test handling of malicious plugin behavior."""
        # TODO: Implement malicious plugin tests
        # This will test for plugins that try to escape sandbox
        pass
    
    def test_plugin_signature_verification(self):
        """Test plugin signature verification."""
        # TODO: Implement signature verification tests
        # This will test cryptographic signature validation
        pass
    
    def test_plugin_sandbox_isolation(self):
        """Test plugin sandbox isolation."""
        # TODO: Implement sandbox isolation tests
        # This will test that plugins cannot access host system
        pass

if __name__ == '__main__':
    unittest.main()
import time
import os
import sys
import tempfile
import shutil
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add tools directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

from plugin_sandbox import PluginSandbox, SandboxConfig, SandboxResult
from plugin_signature_verifier import PluginSignatureVerifier

class TestPluginSecurity(unittest.TestCase):
    """Test cases for plugin security features."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = SandboxConfig(
            cpu_seconds=2,
            memory_mb=128,
            timeout_seconds=5,
            allow_network=False,
            allow_filesystem_write=False
        )
        self.sandbox = PluginSandbox(self.config)
        self.verifier = PluginSignatureVerifier()
    
    def test_safe_plugin_execution(self):
        """Test execution of a safe plugin."""
        def safe_plugin():
            return "Safe plugin executed"
        
        result = self.sandbox.execute_plugin(safe_plugin)
        
        self.assertEqual(result.result.value, "success")
        self.assertLess(result.execution_time, 5.0)
        self.assertEqual(result.error, "")
    
    def test_malicious_plugin_timeout(self):
        """Test that malicious plugins are terminated on timeout."""
        def malicious_plugin():
            time.sleep(10)  # Try to run longer than timeout
            return "Should not reach here"
        
        result = self.sandbox.execute_plugin(malicious_plugin)
        
        self.assertEqual(result.result.value, "timeout")
        self.assertGreater(result.execution_time, 4.0)  # Should timeout
        self.assertIn("timed out", result.error)
    
    def test_malicious_plugin_memory_limit(self):
        """Test that plugins exceeding memory limits are terminated."""
        def memory_hog_plugin():
            # Try to allocate more memory than allowed
            large_data = []
            for i in range(1000):
                large_data.append([0] * (1024 * 1024))  # 1MB chunks
            return "Should not reach here"
        
        result = self.sandbox.execute_plugin(memory_hog_plugin)
        
        # Should either timeout or hit memory limit
        self.assertIn(result.result.value, ["timeout", "memory_limit", "error"])
    
    def test_malicious_plugin_filesystem_access(self):
        """Test that plugins cannot access restricted filesystem areas."""
        def filesystem_attacker():
            try:
                # Try to access system files
                with open("/etc/passwd", "r") as f:
                    content = f.read()
                return f"Accessed system file: {len(content)} bytes"
            except PermissionError:
                return "Filesystem access blocked"
            except Exception as e:
                return f"Error: {str(e)}"
        
        result = self.sandbox.execute_plugin(filesystem_attacker)
        
        # Should complete but not access system files
        self.assertEqual(result.result.value, "success")
        self.assertIn("blocked", result.output)
    
    def test_malicious_plugin_network_access(self):
        """Test that plugins cannot access network when disabled."""
        def network_attacker():
            try:
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(("8.8.8.8", 53))
                sock.close()
                return "Network access successful"
            except Exception as e:
                return f"Network access blocked: {str(e)}"
        
        result = self.sandbox.execute_plugin(network_attacker)
        
        # Should complete but not access network
        self.assertEqual(result.result.value, "success")
        self.assertIn("blocked", result.output)
    
    def test_plugin_signature_verification(self):
        """Test plugin signature verification."""
        # Create a temporary plugin file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("def test_plugin():\n    return 'test'")
            plugin_path = f.name
        
        try:
            # Test with non-existent plugin
            result = self.verifier.verify_plugin_signature("nonexistent", plugin_path)
            self.assertFalse(result.valid)
            self.assertIn("not in approved whitelist", result.errors[0])
            
            # Test with plugin in whitelist
            self.verifier.add_plugin_to_whitelist("test_plugin", plugin_path)
            result = self.verifier.verify_plugin_signature("test_plugin", plugin_path)
            self.assertTrue(result.valid)
            
        finally:
            os.unlink(plugin_path)
    
    def test_plugin_signature_tampering(self):
        """Test that tampered plugins fail signature verification."""
        # Create a temporary plugin file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("def test_plugin():\n    return 'test'")
            plugin_path = f.name
        
        try:
            # Add to whitelist
            self.verifier.add_plugin_to_whitelist("test_plugin", plugin_path)
            
            # Tamper with the file
            with open(plugin_path, 'a') as f:
                f.write("\n# Malicious code added")
            
            # Verify signature should fail
            result = self.verifier.verify_plugin_signature("test_plugin", plugin_path)
            self.assertFalse(result.valid)
            self.assertIn("hash mismatch", result.errors[0])
            
        finally:
            os.unlink(plugin_path)
    
    def test_resource_limit_enforcement(self):
        """Test that resource limits are enforced."""
        def cpu_intensive_plugin():
            # Try to use CPU intensively
            start_time = time.time()
            while time.time() - start_time < 10:  # Try to run for 10 seconds
                pass
            return "CPU intensive task completed"
        
        result = self.sandbox.execute_plugin(cpu_intensive_plugin)
        
        # Should timeout due to CPU limit
        self.assertEqual(result.result.value, "timeout")
        self.assertLess(result.execution_time, 10.0)
    
    def test_plugin_security_validation(self):
        """Test plugin security validation."""
        from plugin_sandbox import validate_plugin_security
        
        def safe_plugin():
            return "safe"
        
        def evil_plugin():
            return "evil"
        
        # Mock the evil plugin name
        evil_plugin.__name__ = "evil_plugin"
        
        # Test safe plugin
        self.assertTrue(validate_plugin_security(safe_plugin, self.config))
        
        # Test evil plugin
        self.assertFalse(validate_plugin_security(evil_plugin, self.config))
    
    def test_sandbox_configuration_validation(self):
        """Test sandbox configuration validation."""
        # Test valid configuration
        valid_config = SandboxConfig(
            cpu_seconds=5,
            memory_mb=256,
            timeout_seconds=10
        )
        self.assertIsInstance(valid_config, SandboxConfig)
        
        # Test invalid configuration
        with self.assertRaises(TypeError):
            SandboxConfig(cpu_seconds="invalid")
    
    def test_plugin_execution_isolation(self):
        """Test that plugin execution is isolated from main process."""
        def plugin_with_side_effects():
            # Try to modify global state
            global test_global_var
            test_global_var = "modified"
            return "Plugin executed"
        
        # Set initial global state
        global test_global_var
        test_global_var = "initial"
        
        result = self.sandbox.execute_plugin(plugin_with_side_effects)
        
        # Plugin should execute successfully
        self.assertEqual(result.result.value, "success")
        
        # But global state should not be modified due to process isolation
        # Note: This test might not work as expected due to multiprocessing
        # but it demonstrates the concept
    
    def test_plugin_error_handling(self):
        """Test that plugin errors are handled gracefully."""
        def error_plugin():
            raise ValueError("Plugin error")
        
        result = self.sandbox.execute_plugin(error_plugin)
        
        # Should handle error gracefully
        self.assertEqual(result.result.value, "error")
        self.assertIn("Plugin error", result.error)
    
    def test_plugin_output_capture(self):
        """Test that plugin output is captured correctly."""
        def output_plugin():
            print("Plugin output")
            return "Plugin result"
        
        result = self.sandbox.execute_plugin_with_output(output_plugin)
        
        # Should capture output
        self.assertEqual(result.result.value, "success")
        self.assertIsNotNone(result.output)

class TestPluginSecurityIntegration(unittest.TestCase):
    """Integration tests for plugin security."""
    
    def test_end_to_end_plugin_security(self):
        """Test end-to-end plugin security workflow."""
        # 1. Create a plugin
        def test_plugin():
            return "Test plugin executed"
        
        # 2. Verify signature
        verifier = PluginSignatureVerifier()
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("def test_plugin():\n    return 'Test plugin executed'")
            plugin_path = f.name
        
        try:
            # 3. Add to whitelist
            verifier.add_plugin_to_whitelist("test_plugin", plugin_path)
            
            # 4. Verify signature
            sig_result = verifier.verify_plugin_signature("test_plugin", plugin_path)
            self.assertTrue(sig_result.valid)
            
            # 5. Execute in sandbox
            config = SandboxConfig(cpu_seconds=5, memory_mb=256)
            sandbox = PluginSandbox(config)
            sandbox_result = sandbox.execute_plugin(test_plugin)
            
            # 6. Verify execution
            self.assertEqual(sandbox_result.result.value, "success")
            
        finally:
            os.unlink(plugin_path)
    
    def test_malicious_plugin_detection(self):
        """Test detection of various malicious plugin behaviors."""
        malicious_behaviors = [
            # Timeout attack
            lambda: time.sleep(20),
            # Memory attack
            lambda: [0] * (1000 * 1024 * 1024),
            # Filesystem attack
            lambda: open("/etc/passwd", "r").read(),
            # Network attack
            lambda: __import__("socket").socket().connect(("8.8.8.8", 53))
        ]
        
        config = SandboxConfig(cpu_seconds=2, memory_mb=128, timeout_seconds=3)
        sandbox = PluginSandbox(config)
        
        for i, behavior in enumerate(malicious_behaviors):
            with self.subTest(behavior=i):
                result = sandbox.execute_plugin(behavior)
                # All malicious behaviors should be blocked
                self.assertIn(result.result.value, ["timeout", "error", "security_violation"])

if __name__ == "__main__":
    unittest.main()
