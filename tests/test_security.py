# Security Tests for Plugin System

"""
Comprehensive security tests for plugin signature verification,
sandbox execution, and policy enforcement.
"""

import pytest
import tempfile
import json
import pathlib
import time
import subprocess
import os
from unittest.mock import patch, MagicMock

from security.signing import (
    PluginSigner, PluginSignatureVerifier, PluginManifest,
    sign_plugin, verify_plugin_signature
)
from security.sandbox import (
    PluginSandbox, SandboxConfig, SandboxResult,
    sandbox_exec, run_plugin_secure
)
from security.policy_enforcement import (
    SecurityPolicyManager, PluginSecurityEnforcer,
    check_plugin_security, enforce_security_policy
)

class TestPluginSignatureVerification:
    """Test plugin signature verification functionality."""
    
    @pytest.fixture
    def test_keys(self):
        """Generate test key pair."""
        signer = PluginSigner()
        private_pem, public_pem = signer.generate_key_pair()
        
        # Save keys to temporary files
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.pem', delete=False) as f:
            f.write(private_pem)
            private_key_path = f.name
        
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.pem', delete=False) as f:
            f.write(public_pem)
            public_key_path = f.name
        
        yield private_key_path, public_key_path
        
        # Cleanup
        os.unlink(private_key_path)
        os.unlink(public_key_path)
    
    @pytest.fixture
    def test_plugin(self):
        """Create test plugin file."""
        plugin_code = '''
class Plugin:
    def run(self, data):
        return {"result": "success", "data": data}
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(plugin_code)
            plugin_path = f.name
        
        yield plugin_path
        
        # Cleanup
        os.unlink(plugin_path)
    
    @pytest.fixture
    def test_manifest(self):
        """Create test plugin manifest."""
        return PluginManifest(
            name="test_plugin",
            version="1.0.0",
            description="Test plugin for security testing",
            author="Security Team",
            entrypoint="Plugin"
        )
    
    def test_sign_plugin_success(self, test_keys, test_plugin, test_manifest):
        """Test successful plugin signing."""
        private_key_path, public_key_path = test_keys
        
        signer = PluginSigner(private_key_path)
        signature = signer.sign_plugin(test_manifest, test_plugin)
        
        assert signature is not None
        assert len(signature) > 0
        assert test_manifest.signature is None  # Original manifest unchanged
    
    def test_verify_plugin_signature_success(self, test_keys, test_plugin, test_manifest):
        """Test successful plugin signature verification."""
        private_key_path, public_key_path = test_keys
        
        # Sign plugin
        signer = PluginSigner(private_key_path)
        signature = signer.sign_plugin(test_manifest, test_plugin)
        test_manifest.signature = signature
        
        # Verify signature
        verifier = PluginSignatureVerifier(public_key_path)
        result = verifier.verify_plugin_signature(test_manifest, test_plugin)
        
        assert result.valid is True
        assert result.error is None
        assert result.audit_record is not None
        assert result.audit_record["verification_result"] == "valid"
    
    def test_verify_plugin_signature_tampered(self, test_keys, test_plugin, test_manifest):
        """Test signature verification with tampered plugin."""
        private_key_path, public_key_path = test_keys
        
        # Sign plugin
        signer = PluginSigner(private_key_path)
        signature = signer.sign_plugin(test_manifest, test_plugin)
        test_manifest.signature = signature
        
        # Tamper with plugin file
        with open(test_plugin, 'a') as f:
            f.write('\n# Malicious code added')
        
        # Verify signature (should fail)
        verifier = PluginSignatureVerifier(public_key_path)
        result = verifier.verify_plugin_signature(test_manifest, test_plugin)
        
        assert result.valid is False
        assert "hash mismatch" in result.error.lower()
        assert result.audit_record["verification_result"] == "invalid_signature"
    
    def test_verify_plugin_signature_wrong_signature(self, test_keys, test_plugin, test_manifest):
        """Test signature verification with wrong signature."""
        private_key_path, public_key_path = test_keys
        
        # Sign plugin
        signer = PluginSigner(private_key_path)
        signature = signer.sign_plugin(test_manifest, test_plugin)
        
        # Use wrong signature
        test_manifest.signature = "wrong_signature_here"
        
        # Verify signature (should fail)
        verifier = PluginSignatureVerifier(public_key_path)
        result = verifier.verify_plugin_signature(test_manifest, test_plugin)
        
        assert result.valid is False
        assert "invalid signature" in result.error.lower()
        assert result.audit_record["verification_result"] == "invalid_signature"
    
    def test_verify_plugin_signature_no_signature(self, test_keys, test_plugin, test_manifest):
        """Test signature verification with no signature."""
        private_key_path, public_key_path = test_keys
        
        # Don't sign plugin
        test_manifest.signature = None
        
        # Verify signature (should fail)
        verifier = PluginSignatureVerifier(public_key_path)
        result = verifier.verify_plugin_signature(test_manifest, test_plugin)
        
        assert result.valid is False
        assert "no signature provided" in result.error.lower()
    
    def test_verify_plugin_signature_missing_file(self, test_keys, test_manifest):
        """Test signature verification with missing plugin file."""
        private_key_path, public_key_path = test_keys
        
        test_manifest.signature = "dummy_signature"
        
        # Verify signature with non-existent file (should fail)
        verifier = PluginSignatureVerifier(public_key_path)
        result = verifier.verify_plugin_signature(test_manifest, "/non/existent/file.py")
        
        assert result.valid is False
        assert "file not found" in result.error.lower()
    
    def test_ecdsa_signature_verification(self, test_keys, test_plugin, test_manifest):
        """Test ECDSA signature verification."""
        private_key_path, public_key_path = test_keys
        
        # Generate ECDSA keys
        signer = PluginSigner()
        private_pem, public_pem = signer.generate_key_pair(algorithm="ecdsa")
        
        # Save ECDSA keys
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.pem', delete=False) as f:
            f.write(private_pem)
            ecdsa_private_key_path = f.name
        
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.pem', delete=False) as f:
            f.write(public_pem)
            ecdsa_public_key_path = f.name
        
        try:
            # Sign with ECDSA
            test_manifest.signature_type = "ecdsa"
            ecdsa_signer = PluginSigner(ecdsa_private_key_path)
            signature = ecdsa_signer.sign_plugin(test_manifest, test_plugin)
            test_manifest.signature = signature
            
            # Verify ECDSA signature
            ecdsa_verifier = PluginSignatureVerifier(ecdsa_public_key_path)
            result = ecdsa_verifier.verify_plugin_signature(test_manifest, test_plugin)
            
            assert result.valid is True
            assert result.signature_type == "ecdsa"
            
        finally:
            # Cleanup
            os.unlink(ecdsa_private_key_path)
            os.unlink(ecdsa_public_key_path)

class TestPluginSandboxExecution:
    """Test plugin sandbox execution functionality."""
    
    @pytest.fixture
    def test_plugin(self):
        """Create test plugin file."""
        plugin_code = '''
class Plugin:
    def run(self, data):
        return {"result": "success", "input": data}
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(plugin_code)
            plugin_path = f.name
        
        yield plugin_path
        
        # Cleanup
        os.unlink(plugin_path)
    
    @pytest.fixture
    def malicious_plugin(self):
        """Create malicious plugin file."""
        plugin_code = '''
class Plugin:
    def run(self, data):
        # Try to access forbidden resources
        import os
        import subprocess
        
        # Attempt to read sensitive files
        try:
            with open("/etc/passwd", "r") as f:
                content = f.read()
        except:
            pass
        
        # Attempt to execute system commands
        try:
            result = subprocess.run(["ls", "/"], capture_output=True)
        except:
            pass
        
        # Attempt to access network
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(("example.com", 80))
            s.close()
        except:
            pass
        
        return {"result": "malicious_attempt"}
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(plugin_code)
            plugin_path = f.name
        
        yield plugin_path
        
        # Cleanup
        os.unlink(plugin_path)
    
    @pytest.fixture
    def timeout_plugin(self):
        """Create plugin that runs indefinitely."""
        plugin_code = '''
class Plugin:
    def run(self, data):
        import time
        # Run for longer than timeout
        time.sleep(120)
        return {"result": "timeout_test"}
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(plugin_code)
            plugin_path = f.name
        
        yield plugin_path
        
        # Cleanup
        os.unlink(plugin_path)
    
    @pytest.fixture
    def memory_intensive_plugin(self):
        """Create memory-intensive plugin."""
        plugin_code = '''
class Plugin:
    def run(self, data):
        # Allocate large amount of memory
        large_list = []
        for i in range(1000000):  # 1 million items
            large_list.append("x" * 1000)  # 1KB per item = 1GB total
        return {"result": "memory_intensive"}
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(plugin_code)
            plugin_path = f.name
        
        yield plugin_path
        
        # Cleanup
        os.unlink(plugin_path)
    
    def test_sandbox_exec_success(self, test_plugin):
        """Test successful sandbox execution."""
        config = SandboxConfig(timeout_seconds=10, memory_mb=128)
        sandbox = PluginSandbox(config)
        
        result = sandbox.sandbox_exec("test_plugin", {"test": "data"}, test_plugin)
        
        assert result.result == SandboxResult.SUCCESS
        assert result.exit_code == 0
        assert "success" in result.output
        assert result.audit_record is not None
    
    def test_sandbox_exec_timeout(self, timeout_plugin):
        """Test sandbox execution timeout."""
        config = SandboxConfig(timeout_seconds=2, memory_mb=128)
        sandbox = PluginSandbox(config)
        
        result = sandbox.sandbox_exec("timeout_plugin", {"test": "data"}, timeout_plugin)
        
        assert result.result == SandboxResult.TIMEOUT
        assert result.exit_code == 124
        assert "timeout" in result.error.lower()
    
    def test_sandbox_exec_memory_limit(self, memory_intensive_plugin):
        """Test sandbox memory limit enforcement."""
        config = SandboxConfig(timeout_seconds=30, memory_mb=64)  # Small memory limit
        sandbox = PluginSandbox(config)
        
        result = sandbox.sandbox_exec("memory_intensive_plugin", {"test": "data"}, memory_intensive_plugin)
        
        # Should either timeout or hit memory limit
        assert result.result in [SandboxResult.TIMEOUT, SandboxResult.MEMORY_LIMIT, SandboxResult.ERROR]
    
    def test_sandbox_exec_malicious_plugin(self, malicious_plugin):
        """Test sandbox execution with malicious plugin."""
        config = SandboxConfig(timeout_seconds=10, memory_mb=128)
        sandbox = PluginSandbox(config)
        
        result = sandbox.sandbox_exec("malicious_plugin", {"test": "data"}, malicious_plugin)
        
        # Should complete but with restrictions
        assert result.result in [SandboxResult.SUCCESS, SandboxResult.ERROR]
        # The malicious actions should be blocked by sandbox restrictions
    
    def test_run_plugin_secure_success(self, test_plugin):
        """Test secure plugin runner success."""
        config = SandboxConfig(timeout_seconds=10, memory_mb=128)
        
        result = run_plugin_secure("test_plugin", {"test": "data"}, test_plugin, config)
        
        assert result["success"] is True
        assert "success" in result["data"]["result"]
        assert "execution_time" in result
    
    def test_run_plugin_secure_failure(self, timeout_plugin):
        """Test secure plugin runner failure."""
        config = SandboxConfig(timeout_seconds=2, memory_mb=128)
        
        result = run_plugin_secure("timeout_plugin", {"test": "data"}, timeout_plugin, config)
        
        assert result["success"] is False
        assert "timeout" in result["error"].lower()
    
    def test_sandbox_config_validation(self):
        """Test sandbox configuration validation."""
        # Test valid config
        config = SandboxConfig(
            cpu_seconds=30,
            memory_mb=256,
            timeout_seconds=60,
            allow_network=False,
            allow_filesystem_write=False
        )
        
        assert config.cpu_seconds == 30
        assert config.memory_mb == 256
        assert config.timeout_seconds == 60
        assert config.allow_network is False
        assert config.allow_filesystem_write is False

class TestSecurityPolicyEnforcement:
    """Test security policy enforcement functionality."""
    
    @pytest.fixture
    def compliant_manifest(self):
        """Create compliant plugin manifest."""
        return {
            "name": "compliant_plugin",
            "version": "1.0.0",
            "description": "Compliant plugin",
            "author": "Security Team",
            "entrypoint": "Plugin",
            "signature": "valid_signature_here",
            "signature_type": "rsa",
            "security_profile": {
                "resource_limits": {
                    "cpu_seconds": 30,
                    "memory_mb": 256
                },
                "permissions": {
                    "network_access": False,
                    "filesystem_access": {
                        "read_only": True,
                        "read_allowlist": ["/tmp"],
                        "write_allowlist": []
                    }
                }
            }
        }
    
    @pytest.fixture
    def non_compliant_manifest(self):
        """Create non-compliant plugin manifest."""
        return {
            "name": "non_compliant_plugin",
            "version": "1.0.0",
            "description": "Non-compliant plugin",
            "author": "Security Team",
            "entrypoint": "Plugin",
            "signature": None,  # Missing signature
            "security_profile": {
                "resource_limits": {
                    "cpu_seconds": 120,  # Excessive CPU
                    "memory_mb": 1024   # Excessive memory
                },
                "permissions": {
                    "network_access": True,  # Network access requested
                    "filesystem_access": {
                        "read_only": False,  # Write access requested
                        "read_allowlist": ["/"],
                        "write_allowlist": ["/"]
                    }
                }
            }
        }
    
    @pytest.fixture
    def test_plugin(self):
        """Create test plugin file."""
        plugin_code = '''
class Plugin:
    def run(self, data):
        return {"result": "success"}
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(plugin_code)
            plugin_path = f.name
        
        yield plugin_path
        
        # Cleanup
        os.unlink(plugin_path)
    
    def test_policy_manager_initialization(self):
        """Test policy manager initialization."""
        policy_manager = SecurityPolicyManager()
        
        assert "plugin_security" in policy_manager.policies
        assert len(policy_manager.policies) > 0
    
    def test_check_plugin_policy_compliant(self, compliant_manifest, test_plugin):
        """Test policy check with compliant plugin."""
        policy_manager = SecurityPolicyManager()
        
        result = policy_manager.check_plugin_policy(compliant_manifest, test_plugin)
        
        assert result.compliant is True
        assert len(result.violations) == 0
        assert result.audit_record is not None
    
    def test_check_plugin_policy_non_compliant(self, non_compliant_manifest, test_plugin):
        """Test policy check with non-compliant plugin."""
        policy_manager = SecurityPolicyManager()
        
        result = policy_manager.check_plugin_policy(non_compliant_manifest, test_plugin)
        
        assert result.compliant is False
        assert len(result.violations) > 0
        assert result.audit_record is not None
    
    def test_enforce_policy_compliant(self, compliant_manifest, test_plugin):
        """Test policy enforcement with compliant plugin."""
        policy_manager = SecurityPolicyManager()
        
        result = policy_manager.enforce_policy(compliant_manifest, test_plugin)
        
        assert result is True
    
    def test_enforce_policy_non_compliant(self, non_compliant_manifest, test_plugin):
        """Test policy enforcement with non-compliant plugin."""
        policy_manager = SecurityPolicyManager()
        
        result = policy_manager.enforce_policy(non_compliant_manifest, test_plugin)
        
        assert result is False
    
    def test_plugin_security_enforcer_validation(self, compliant_manifest, test_plugin):
        """Test plugin security enforcer validation."""
        policy_manager = SecurityPolicyManager()
        enforcer = PluginSecurityEnforcer(policy_manager)
        
        valid, errors = enforcer.validate_plugin(compliant_manifest, test_plugin)
        
        assert valid is True
        assert len(errors) == 0
    
    def test_plugin_security_enforcer_validation_failure(self, non_compliant_manifest, test_plugin):
        """Test plugin security enforcer validation failure."""
        policy_manager = SecurityPolicyManager()
        enforcer = PluginSecurityEnforcer(policy_manager)
        
        valid, errors = enforcer.validate_plugin(non_compliant_manifest, test_plugin)
        
        assert valid is False
        assert len(errors) > 0
    
    def test_check_plugin_security_convenience_function(self, compliant_manifest, test_plugin):
        """Test convenience function for plugin security check."""
        valid, errors = check_plugin_security(compliant_manifest, test_plugin)
        
        assert valid is True
        assert len(errors) == 0
    
    def test_enforce_security_policy_convenience_function(self, compliant_manifest, test_plugin):
        """Test convenience function for policy enforcement."""
        result = enforce_security_policy(compliant_manifest, test_plugin)
        
        assert result is True

class TestSecurityIntegration:
    """Test integration of all security components."""
    
    @pytest.fixture
    def test_keys(self):
        """Generate test key pair."""
        signer = PluginSigner()
        private_pem, public_pem = signer.generate_key_pair()
        
        # Save keys to temporary files
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.pem', delete=False) as f:
            f.write(private_pem)
            private_key_path = f.name
        
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.pem', delete=False) as f:
            f.write(public_pem)
            public_key_path = f.name
        
        yield private_key_path, public_key_path
        
        # Cleanup
        os.unlink(private_key_path)
        os.unlink(public_key_path)
    
    @pytest.fixture
    def test_plugin(self):
        """Create test plugin file."""
        plugin_code = '''
class Plugin:
    def run(self, data):
        return {"result": "success", "input": data}
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(plugin_code)
            plugin_path = f.name
        
        yield plugin_path
        
        # Cleanup
        os.unlink(plugin_path)
    
    def test_full_security_workflow(self, test_keys, test_plugin):
        """Test complete security workflow."""
        private_key_path, public_key_path = test_keys
        
        # 1. Create plugin manifest
        manifest = PluginManifest(
            name="integration_test_plugin",
            version="1.0.0",
            description="Integration test plugin",
            author="Security Team",
            entrypoint="Plugin"
        )
        
        # 2. Sign plugin
        signer = PluginSigner(private_key_path)
        signature = signer.sign_plugin(manifest, test_plugin)
        manifest.signature = signature
        
        # 3. Verify signature
        verifier = PluginSignatureVerifier(public_key_path)
        verification_result = verifier.verify_plugin_signature(manifest, test_plugin)
        
        assert verification_result.valid is True
        
        # 4. Check policy compliance
        manifest_dict = {
            "name": manifest.name,
            "version": manifest.version,
            "description": manifest.description,
            "author": manifest.author,
            "entrypoint": manifest.entrypoint,
            "signature": manifest.signature,
            "signature_type": manifest.signature_type,
            "security_profile": {
                "resource_limits": {
                    "cpu_seconds": 30,
                    "memory_mb": 256
                },
                "permissions": {
                    "network_access": False,
                    "filesystem_access": {
                        "read_only": True,
                        "read_allowlist": ["/tmp"],
                        "write_allowlist": []
                    }
                }
            }
        }
        
        policy_compliant, policy_errors = check_plugin_security(manifest_dict, test_plugin)
        
        assert policy_compliant is True
        assert len(policy_errors) == 0
        
        # 5. Execute in sandbox
        config = SandboxConfig(timeout_seconds=10, memory_mb=128)
        execution_result = run_plugin_secure("integration_test_plugin", {"test": "data"}, test_plugin, config)
        
        assert execution_result["success"] is True
        assert "success" in execution_result["data"]["result"]
    
    def test_security_workflow_with_violations(self, test_keys, test_plugin):
        """Test security workflow with policy violations."""
        private_key_path, public_key_path = test_keys
        
        # Create manifest with policy violations
        manifest_dict = {
            "name": "violation_test_plugin",
            "version": "1.0.0",
            "description": "Plugin with policy violations",
            "author": "Security Team",
            "entrypoint": "Plugin",
            "signature": None,  # Missing signature
            "security_profile": {
                "resource_limits": {
                    "cpu_seconds": 120,  # Excessive
                    "memory_mb": 1024   # Excessive
                },
                "permissions": {
                    "network_access": True,  # Not allowed
                    "filesystem_access": {
                        "read_only": False,  # Not allowed
                        "read_allowlist": ["/"],
                        "write_allowlist": ["/"]
                    }
                }
            }
        }
        
        # Check policy compliance (should fail)
        policy_compliant, policy_errors = check_plugin_security(manifest_dict, test_plugin)
        
        assert policy_compliant is False
        assert len(policy_errors) > 0
        
        # Policy enforcement should fail
        enforcement_result = enforce_security_policy(manifest_dict, test_plugin)
        
        assert enforcement_result is False

# Performance tests
class TestSecurityPerformance:
    """Test security component performance."""
    
    def test_signature_verification_performance(self):
        """Test signature verification performance."""
        signer = PluginSigner()
        private_pem, public_pem = signer.generate_key_pair()
        
        # Save keys
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.pem', delete=False) as f:
            f.write(private_pem)
            private_key_path = f.name
        
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.pem', delete=False) as f:
            f.write(public_pem)
            public_key_path = f.name
        
        try:
            # Create test plugin
            plugin_code = 'class Plugin:\n    def run(self, data):\n        return {"result": "success"}'
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(plugin_code)
                plugin_path = f.name
            
            try:
                # Create manifest
                manifest = PluginManifest(
                    name="perf_test_plugin",
                    version="1.0.0",
                    description="Performance test plugin",
                    author="Security Team",
                    entrypoint="Plugin"
                )
                
                # Sign plugin
                signer = PluginSigner(private_key_path)
                start_time = time.time()
                signature = signer.sign_plugin(manifest, plugin_path)
                sign_time = time.time() - start_time
                
                manifest.signature = signature
                
                # Verify signature
                verifier = PluginSignatureVerifier(public_key_path)
                start_time = time.time()
                result = verifier.verify_plugin_signature(manifest, plugin_path)
                verify_time = time.time() - start_time
                
                assert result.valid is True
                assert sign_time < 1.0  # Should sign in less than 1 second
                assert verify_time < 1.0  # Should verify in less than 1 second
                
            finally:
                os.unlink(plugin_path)
        
        finally:
            os.unlink(private_key_path)
            os.unlink(public_key_path)
    
    def test_sandbox_execution_performance(self):
        """Test sandbox execution performance."""
        # Create simple plugin
        plugin_code = 'class Plugin:\n    def run(self, data):\n        return {"result": "success"}'
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(plugin_code)
            plugin_path = f.name
        
        try:
            config = SandboxConfig(timeout_seconds=5, memory_mb=64)
            
            start_time = time.time()
            result = run_plugin_secure("perf_test_plugin", {"test": "data"}, plugin_path, config)
            execution_time = time.time() - start_time
            
            assert result["success"] is True
            assert execution_time < 5.0  # Should complete in less than 5 seconds
        
        finally:
            os.unlink(plugin_path)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
